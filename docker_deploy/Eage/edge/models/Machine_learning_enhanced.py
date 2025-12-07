#!/usr/bin/env python3
"""
ML Inference Service - Anomaly Detection & RUL/SOH Prediction
Multiple models with comprehensive evaluation metrics
"""

import json
import logging
import os
import time
import numpy as np
import paho.mqtt.client as mqtt
from sklearn.ensemble import (
    IsolationForest, RandomForestRegressor, GradientBoostingRegressor,
    ExtraTreesRegressor, AdaBoostRegressor
)
from sklearn.neural_network import MLPRegressor
from sklearn.svm import SVC, SVR
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    mean_squared_error, mean_absolute_error, r2_score,
    mean_absolute_percentage_error
)
import joblib
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List
import socket
import warnings

warnings.filterwarnings('ignore', category=DeprecationWarning)

# ============================
# Logging Configuration
# ============================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

# ============================
# Configuration
# ============================
MQTT_HOST = os.getenv("MQTT_HOST", "mqtt-broker")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_INPUT_TOPIC = os.getenv("MQTT_INPUT_TOPIC", "ev/metrics")
MQTT_OUTPUT_TOPIC = os.getenv("MQTT_OUTPUT_TOPIC", "ev/alerts")

MODEL_DIR = os.getenv("MODEL_DIR", "/app/models")
ANOMALY_MODEL_PATH = os.path.join(MODEL_DIR, "isoforest.pkl")
RUL_MODELS_DIR = os.path.join(MODEL_DIR, "rul_models")
SOH_MODELS_DIR = os.path.join(MODEL_DIR, "soh_models")
SCALER_PATH = os.path.join(MODEL_DIR, "scaler.pkl")
METRICS_PATH = os.path.join(MODEL_DIR, "model_metrics.json")

CONTAMINATION = float(os.getenv("CONTAMINATION", 0.1))
ANOMALY_SCORE_THRESHOLD = float(os.getenv("ANOMALY_THRESHOLD", -0.5))

FEATURE_NAMES = ["voltage", "temperature", "soc", "soh", "current"]
FEATURE_COUNT = len(FEATURE_NAMES)

EXTENDED_FEATURES = ["voltage", "temperature", "soc", "soh", "current", 
                     "voltage_variance", "temperature_variance", "cycle_count"]
EXTENDED_FEATURE_COUNT = len(EXTENDED_FEATURES)

FEATURE_RANGES = {
    "voltage": (2.5, 4.5),
    "temperature": (-40, 80),
    "soc": (0, 100),
    "soh": (0, 100),
    "current": (-500, 500)
}

# ============================
# Global State
# ============================
mqtt_connected = False
anomaly_model: Optional[IsolationForest] = None
rul_models: Dict[str, Any] = {}
soh_models: Dict[str, Any] = {}
scaler: Optional[StandardScaler] = None
model_metrics: Dict[str, Dict] = {}
message_count = 0
anomaly_count = 0
voltage_history = []
temperature_history = []
cycle_count = 0

# ============================
# Evaluation Metrics Calculator
# ============================
class ModelEvaluator:
    """Calculate comprehensive evaluation metrics for models"""
    
    @staticmethod
    def calculate_regression_metrics(y_true: np.ndarray, y_pred: np.ndarray, 
                                    model_name: str) -> Dict[str, float]:
        """Calculate regression evaluation metrics"""
        try:
            metrics = {
                "model": model_name,
                "mse": float(mean_squared_error(y_true, y_pred)),
                "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
                "mae": float(mean_absolute_error(y_true, y_pred)),
                "r2": float(r2_score(y_true, y_pred)),
                "mape": float(mean_absolute_percentage_error(y_true, y_pred)),
            }
            
            # Calculate additional metrics
            residuals = y_true - y_pred
            metrics["mean_residual"] = float(np.mean(residuals))
            metrics["std_residual"] = float(np.std(residuals))
            metrics["max_error"] = float(np.max(np.abs(residuals)))
            metrics["median_error"] = float(np.median(np.abs(residuals)))
            
            # Calculate explained variance
            ss_res = np.sum(residuals ** 2)
            ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
            metrics["explained_variance"] = float(1 - (ss_res / ss_tot)) if ss_tot != 0 else 0
            
            # Calculate correlation
            if len(y_true) > 1:
                metrics["correlation"] = float(np.corrcoef(y_true, y_pred)[0, 1])
            
            return metrics
        
        except Exception as e:
            log.error(f"❌ Error calculating metrics for {model_name}: {e}")
            return {}

# ============================
# Model Management - Anomaly Detection
# ============================
def create_anomaly_model() -> IsolationForest:
    """Create and train IsolationForest for anomaly detection"""
    log.info(f"🤖 Training IsolationForest with {FEATURE_COUNT} features...")
    
    try:
        normal_data = []
        for _ in range(1000):
            voltage = np.random.normal(3.8, 0.2)
            temperature = np.random.normal(35, 5)
            soc = np.random.normal(75, 15)
            soh = np.random.normal(90, 5)
            current = np.random.normal(50, 20)
            normal_data.append([voltage, temperature, soc, soh, current])
        
        normal_data = np.array(normal_data)
        log.info(f"📊 Training data shape: {normal_data.shape}")
        
        model = IsolationForest(
            contamination=CONTAMINATION,
            random_state=42,
            n_estimators=100,
            max_samples='auto',
            n_jobs=-1
        )
        model.fit(normal_data)
        
        n_features = model.n_features_in_
        log.info(f"✅ IsolationForest trained: {n_features} features")
        
        return model
    
    except Exception as e:
        log.error(f"❌ Failed to train anomaly model: {e}", exc_info=True)
        raise

# ============================
# RUL Prediction Models
# ============================
def create_rul_models() -> Dict[str, Any]:
    """Create and train multiple RUL prediction models"""
    log.info(f"🤖 Training RUL prediction models with {EXTENDED_FEATURE_COUNT} features...")
    
    try:
        # Generate synthetic training data
        training_data = []
        labels = []
        
        for cycle in range(100, 2000, 50):
            for _ in range(20):
                voltage = np.random.normal(3.8 - (cycle / 5000), 0.15)
                temperature = np.random.normal(35 + (cycle / 500), 4)
                soc = np.random.normal(70, 12)
                soh = 100 - (cycle / 20)
                current = np.random.normal(50, 15)
                voltage_var = np.random.uniform(0.01, 0.3)
                temp_var = np.random.uniform(0.5, 5)
                cycle_c = cycle
                
                training_data.append([voltage, temperature, soc, soh, current, 
                                    voltage_var, temp_var, cycle_c])
                rul = max(0, 2500 - cycle)
                labels.append(rul)
        
        X = np.array(training_data)
        y = np.array(labels)
        log.info(f"📊 RUL training data shape: {X.shape}, labels shape: {y.shape}")
        
        models = {}
        
        # Random Forest Regressor
        log.info("🔧 Training Random Forest RUL model...")
        rf_model = RandomForestRegressor(
            n_estimators=100,
            max_depth=20,
            random_state=42,
            n_jobs=-1
        )
        rf_model.fit(X, y)
        rf_pred = rf_model.predict(X)
        models["RandomForest"] = {
            "model": rf_model,
            "metrics": ModelEvaluator.calculate_regression_metrics(y, rf_pred, "RandomForest-RUL")
        }
        log.info(f"✅ RF-RUL R²: {models['RandomForest']['metrics']['r2']:.4f}, RMSE: {models['RandomForest']['metrics']['rmse']:.2f}")
        
        # Gradient Boosting Regressor
        log.info("🔧 Training Gradient Boosting RUL model...")
        gb_model = GradientBoostingRegressor(
            n_estimators=150,
            max_depth=8,
            learning_rate=0.1,
            random_state=42
        )
        gb_model.fit(X, y)
        gb_pred = gb_model.predict(X)
        models["GradientBoosting"] = {
            "model": gb_model,
            "metrics": ModelEvaluator.calculate_regression_metrics(y, gb_pred, "GradientBoosting-RUL")
        }
        log.info(f"✅ GB-RUL R²: {models['GradientBoosting']['metrics']['r2']:.4f}, RMSE: {models['GradientBoosting']['metrics']['rmse']:.2f}")
        
        # Extra Trees Regressor
        log.info("🔧 Training Extra Trees RUL model...")
        et_model = ExtraTreesRegressor(
            n_estimators=100,
            max_depth=20,
            random_state=42,
            n_jobs=-1
        )
        et_model.fit(X, y)
        et_pred = et_model.predict(X)
        models["ExtraTrees"] = {
            "model": et_model,
            "metrics": ModelEvaluator.calculate_regression_metrics(y, et_pred, "ExtraTrees-RUL")
        }
        log.info(f"✅ ET-RUL R²: {models['ExtraTrees']['metrics']['r2']:.4f}, RMSE: {models['ExtraTrees']['metrics']['rmse']:.2f}")
        
        # AdaBoost Regressor
        log.info("🔧 Training AdaBoost RUL model...")
        ada_model = AdaBoostRegressor(
            n_estimators=100,
            random_state=42
        )
        ada_model.fit(X, y)
        ada_pred = ada_model.predict(X)
        models["AdaBoost"] = {
            "model": ada_model,
            "metrics": ModelEvaluator.calculate_regression_metrics(y, ada_pred, "AdaBoost-RUL")
        }
        log.info(f"✅ ADA-RUL R²: {models['AdaBoost']['metrics']['r2']:.4f}, RMSE: {models['AdaBoost']['metrics']['rmse']:.2f}")
        
        # Neural Network Regressor
        log.info("🔧 Training MLP RUL model...")
        mlp_model = MLPRegressor(
            hidden_layer_sizes=(128, 64, 32),
            activation='relu',
            max_iter=1000,
            random_state=42,
            early_stopping=True,
            validation_fraction=0.1
        )
        mlp_model.fit(X, y)
        mlp_pred = mlp_model.predict(X)
        models["MLP"] = {
            "model": mlp_model,
            "metrics": ModelEvaluator.calculate_regression_metrics(y, mlp_pred, "MLP-RUL")
        }
        log.info(f"✅ MLP-RUL R²: {models['MLP']['metrics']['r2']:.4f}, RMSE: {models['MLP']['metrics']['rmse']:.2f}")
        
        # Ensemble approach (weighted average)
        log.info("🔧 Creating Ensemble RUL model...")
        ensemble_pred = (rf_pred * 0.3 + gb_pred * 0.3 + et_pred * 0.2 + mlp_pred * 0.2)
        models["Ensemble"] = {
            "model": None,  # Ensemble doesn't need separate model object
            "metrics": ModelEvaluator.calculate_regression_metrics(y, ensemble_pred, "Ensemble-RUL")
        }
        log.info(f"✅ ENS-RUL R²: {models['Ensemble']['metrics']['r2']:.4f}, RMSE: {models['Ensemble']['metrics']['rmse']:.2f}")
        
        return models
    
    except Exception as e:
        log.error(f"❌ Failed to train RUL models: {e}", exc_info=True)
        raise

# ============================
# SOH Prediction Models
# ============================
def create_soh_models() -> Dict[str, Any]:
    """Create and train multiple SOH prediction models"""
    log.info(f"🤖 Training SOH prediction models with {EXTENDED_FEATURE_COUNT} features...")
    
    try:
        # Generate synthetic training data
        training_data = []
        labels = []
        
        for cycle in range(0, 2000, 50):
            for _ in range(20):
                voltage = np.random.normal(3.8 - (cycle / 8000), 0.15)
                temperature = np.random.normal(35 + (cycle / 500), 4)
                soc = np.random.normal(70, 12)
                soh = 100 - (cycle / 25) + np.random.normal(0, 2)
                current = np.random.normal(50, 15)
                voltage_var = np.random.uniform(0.01, 0.3)
                temp_var = np.random.uniform(0.5, 5)
                cycle_c = cycle
                
                training_data.append([voltage, temperature, soc, soh, current,
                                    voltage_var, temp_var, cycle_c])
                labels.append(max(0, soh))
        
        X = np.array(training_data)
        y = np.array(labels)
        log.info(f"📊 SOH training data shape: {X.shape}, labels shape: {y.shape}")
        
        models = {}
        
        # Random Forest
        log.info("🔧 Training Random Forest SOH model...")
        rf_model = RandomForestRegressor(
            n_estimators=100,
            max_depth=20,
            random_state=42,
            n_jobs=-1
        )
        rf_model.fit(X, y)
        rf_pred = np.clip(rf_model.predict(X), 0, 100)
        models["RandomForest"] = {
            "model": rf_model,
            "metrics": ModelEvaluator.calculate_regression_metrics(y, rf_pred, "RandomForest-SOH")
        }
        log.info(f"✅ RF-SOH R²: {models['RandomForest']['metrics']['r2']:.4f}, RMSE: {models['RandomForest']['metrics']['rmse']:.2f}")
        
        # Gradient Boosting
        log.info("🔧 Training Gradient Boosting SOH model...")
        gb_model = GradientBoostingRegressor(
            n_estimators=150,
            max_depth=10,
            learning_rate=0.1,
            random_state=42
        )
        gb_model.fit(X, y)
        gb_pred = np.clip(gb_model.predict(X), 0, 100)
        models["GradientBoosting"] = {
            "model": gb_model,
            "metrics": ModelEvaluator.calculate_regression_metrics(y, gb_pred, "GradientBoosting-SOH")
        }
        log.info(f"✅ GB-SOH R²: {models['GradientBoosting']['metrics']['r2']:.4f}, RMSE: {models['GradientBoosting']['metrics']['rmse']:.2f}")
        
        # Extra Trees
        log.info("🔧 Training Extra Trees SOH model...")
        et_model = ExtraTreesRegressor(
            n_estimators=100,
            max_depth=20,
            random_state=42,
            n_jobs=-1
        )
        et_model.fit(X, y)
        et_pred = np.clip(et_model.predict(X), 0, 100)
        models["ExtraTrees"] = {
            "model": et_model,
            "metrics": ModelEvaluator.calculate_regression_metrics(y, et_pred, "ExtraTrees-SOH")
        }
        log.info(f"✅ ET-SOH R²: {models['ExtraTrees']['metrics']['r2']:.4f}, RMSE: {models['ExtraTrees']['metrics']['rmse']:.2f}")
        
        # Neural Network
        log.info("🔧 Training MLP SOH model...")
        mlp_model = MLPRegressor(
            hidden_layer_sizes=(128, 64, 32),
            activation='relu',
            max_iter=1000,
            random_state=42,
            early_stopping=True,
            validation_fraction=0.1
        )
        mlp_model.fit(X, y)
        mlp_pred = np.clip(mlp_model.predict(X), 0, 100)
        models["MLP"] = {
            "model": mlp_model,
            "metrics": ModelEvaluator.calculate_regression_metrics(y, mlp_pred, "MLP-SOH")
        }
        log.info(f"✅ MLP-SOH R²: {models['MLP']['metrics']['r2']:.4f}, RMSE: {models['MLP']['metrics']['rmse']:.2f}")
        
        # Ensemble
        log.info("🔧 Creating Ensemble SOH model...")
        ensemble_pred = np.clip(rf_pred * 0.3 + gb_pred * 0.3 + et_pred * 0.2 + mlp_pred * 0.2, 0, 100)
        models["Ensemble"] = {
            "model": None,
            "metrics": ModelEvaluator.calculate_regression_metrics(y, ensemble_pred, "Ensemble-SOH")
        }
        log.info(f"✅ ENS-SOH R²: {models['Ensemble']['metrics']['r2']:.4f}, RMSE: {models['Ensemble']['metrics']['rmse']:.2f}")
        
        return models
    
    except Exception as e:
        log.error(f"❌ Failed to train SOH models: {e}", exc_info=True)
        raise

# ============================
# Scaler Management
# ============================
def create_scaler() -> StandardScaler:
    """Create and fit StandardScaler"""
    log.info("🤖 Training StandardScaler...")
    
    try:
        data = []
        for _ in range(1000):
            data.append([
                np.random.normal(3.8, 0.2),
                np.random.normal(35, 5),
                np.random.normal(75, 15),
                np.random.normal(90, 5),
                np.random.normal(50, 20),
                np.random.uniform(0.01, 0.3),
                np.random.uniform(0.5, 5),
                np.random.uniform(0, 2000)
            ])
        
        X = np.array(data)
        scaler = StandardScaler()
        scaler.fit(X)
        
        log.info(f"✅ StandardScaler fitted on {EXTENDED_FEATURE_COUNT} features")
        return scaler
    
    except Exception as e:
        log.error(f"❌ Failed to create scaler: {e}", exc_info=True)
        raise

# ============================
# Load or Create All Models
# ============================
def load_or_create_all_models():
    """Load or create all models"""
    global anomaly_model, rul_models, soh_models, scaler, model_metrics
    
    try:
        os.makedirs(MODEL_DIR, exist_ok=True)
        os.makedirs(RUL_MODELS_DIR, exist_ok=True)
        os.makedirs(SOH_MODELS_DIR, exist_ok=True)
    except Exception as e:
        log.warning(f"⚠️  Could not create model directories: {e}")
    
    # Anomaly model
    if os.path.exists(ANOMALY_MODEL_PATH):
        try:
            log.info(f"📂 Loading anomaly model...")
            anomaly_model = joblib.load(ANOMALY_MODEL_PATH)
            log.info(f"✅ Anomaly model loaded")
        except Exception as e:
            log.warning(f"⚠️  Failed to load anomaly model: {e}")
            anomaly_model = create_anomaly_model()
    else:
        anomaly_model = create_anomaly_model()
    
    # Save anomaly model
    try:
        joblib.dump(anomaly_model, ANOMALY_MODEL_PATH)
    except Exception as e:
        log.warning(f"⚠️  Could not save anomaly model: {e}")
    
    # RUL models
    log.info("\n" + "="*70)
    log.info("🎯 TRAINING RUL PREDICTION MODELS")
    log.info("="*70)
    rul_models = create_rul_models()
    
    # Save RUL models
    for model_name, model_data in rul_models.items():
        try:
            if model_data["model"] is not None:
                path = os.path.join(RUL_MODELS_DIR, f"{model_name}.pkl")
                joblib.dump(model_data["model"], path)
        except Exception as e:
            log.warning(f"⚠️  Could not save {model_name} RUL model: {e}")
    
    # SOH models
    log.info("\n" + "="*70)
    log.info("🎯 TRAINING SOH PREDICTION MODELS")
    log.info("="*70)
    soh_models = create_soh_models()
    
    # Save SOH models
    for model_name, model_data in soh_models.items():
        try:
            if model_data["model"] is not None:
                path = os.path.join(SOH_MODELS_DIR, f"{model_name}.pkl")
                joblib.dump(model_data["model"], path)
        except Exception as e:
            log.warning(f"⚠️  Could not save {model_name} SOH model: {e}")
    
    # Scaler
    scaler = create_scaler()
    try:
        joblib.dump(scaler, SCALER_PATH)
    except Exception as e:
        log.warning(f"⚠️  Could not save scaler: {e}")
    
    # Log model metrics
    log.info("\n" + "="*70)
    log.info("📊 MODEL EVALUATION METRICS SUMMARY")
    log.info("="*70)
    
    model_metrics = {
        "timestamp": datetime.utcnow().isoformat(),
        "rul_models": {name: data["metrics"] for name, data in rul_models.items()},
        "soh_models": {name: data["metrics"] for name, data in soh_models.items()},
    }
    
    # Print RUL metrics
    log.info("\n🎯 RUL PREDICTION MODELS:")
    for model_name, metrics in model_metrics["rul_models"].items():
        log.info(f"\n  {model_name}:")
        log.info(f"    R² Score:        {metrics.get('r2', 0):.4f}")
        log.info(f"    RMSE:            {metrics.get('rmse', 0):.2f}")
        log.info(f"    MAE:             {metrics.get('mae', 0):.2f}")
        log.info(f"    MAPE:            {metrics.get('mape', 0):.4f}")
        log.info(f"    Correlation:     {metrics.get('correlation', 0):.4f}")
        log.info(f"    Max Error:       {metrics.get('max_error', 0):.2f}")
    
    # Print SOH metrics
    log.info("\n🎯 SOH PREDICTION MODELS:")
    for model_name, metrics in model_metrics["soh_models"].items():
        log.info(f"\n  {model_name}:")
        log.info(f"    R² Score:        {metrics.get('r2', 0):.4f}")
        log.info(f"    RMSE:            {metrics.get('rmse', 0):.2f}")
        log.info(f"    MAE:             {metrics.get('mae', 0):.2f}")
        log.info(f"    MAPE:            {metrics.get('mape', 0):.4f}")
        log.info(f"    Correlation:     {metrics.get('correlation', 0):.4f}")
        log.info(f"    Max Error:       {metrics.get('max_error', 0):.2f}")
    
    # Find best models
    best_rul = max(model_metrics["rul_models"].items(), 
                   key=lambda x: x[1].get('r2', 0))
    best_soh = max(model_metrics["soh_models"].items(), 
                   key=lambda x: x[1].get('r2', 0))
    
    log.info(f"\n✨ Best RUL Model:  {best_rul[0]} (R²: {best_rul[1]['r2']:.4f})")
    log.info(f"✨ Best SOH Model:  {best_soh[0]} (R²: {best_soh[1]['r2']:.4f})")
    log.info("="*70 + "\n")
    
    # Save metrics to file
    try:
        with open(METRICS_PATH, 'w') as f:
            json.dump(model_metrics, f, indent=2)
        log.info(f"💾 Model metrics saved to {METRICS_PATH}")
    except Exception as e:
        log.warning(f"⚠️  Could not save metrics file: {e}")

# ============================
# Anomaly Detection
# ============================
def validate_data(data: Dict[str, Any]) -> bool:
    """Validate incoming sensor data"""
    try:
        for feature in FEATURE_NAMES:
            if feature not in data:
                return False
            
            value = data[feature]
            if not isinstance(value, (int, float)):
                return False
            
            min_val, max_val = FEATURE_RANGES[feature]
            if not (min_val <= value <= max_val):
                return False
        
        return True
    
    except Exception as e:
        log.error(f"❌ Data validation error: {e}", exc_info=True)
        return False

def detect_anomaly(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Detect anomalies using IsolationForest"""
    global anomaly_model, anomaly_count
    
    try:
        if not validate_data(data):
            return None
        
        X = np.array([[
            float(data['voltage']),
            float(data['temperature']),
            float(data['soc']),
            float(data['soh']),
            float(data['current'])
        ]])
        
        predictions = anomaly_model.predict(X)
        anomaly_scores = anomaly_model.score_samples(X)
        
        prediction = int(predictions[0])
        anomaly_score = float(anomaly_scores[0])
        
        is_anomaly = prediction == -1
        anomaly_type = "NORMAL"
        severity = "INFO"
        
        if is_anomaly:
            anomaly_count += 1
            voltage = float(data['voltage'])
            temperature = float(data['temperature'])
            soc = float(data['soc'])
            soh = float(data['soh'])
            current = float(data['current'])
            
            if voltage > 4.3 or voltage < 2.5:
                anomaly_type = "VOLTAGE_FAULT"
                severity = "CRITICAL"
            elif temperature > 55:
                anomaly_type = "OVERHEAT"
                severity = "WARNING"
            elif soc < 10:
                anomaly_type = "LOW_SOC"
                severity = "WARNING"
            elif soh < 50:
                anomaly_type = "DEGRADATION"
                severity = "WARNING"
            elif current > 200:
                anomaly_type = "OVERCURRENT"
                severity = "CRITICAL"
            else:
                anomaly_type = "ANOMALY"
                severity = "WARNING"
        
        return {
            **data,
            "is_anomaly": is_anomaly,
            "anomaly_type": anomaly_type,
            "anomaly_score": round(anomaly_score, 4),
            "severity": severity,
            "detection_timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        log.error(f"❌ Anomaly detection error: {e}", exc_info=True)
        return None

# ============================
# RUL & SOH Prediction with Ensemble
# ============================
def predict_rul_and_soh(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Predict RUL and SOH using ensemble of models"""
    global rul_models, soh_models, scaler, cycle_count
    global voltage_history, temperature_history
    
    try:
        if not validate_data(data):
            return None
        
        # Update history
        voltage_history.append(float(data['voltage']))
        temperature_history.append(float(data['temperature']))
        
        if len(voltage_history) > 100:
            voltage_history.pop(0)
        if len(temperature_history) > 100:
            temperature_history.pop(0)
        
        voltage_var = np.var(voltage_history) if len(voltage_history) > 1 else 0.01
        temp_var = np.var(temperature_history) if len(temperature_history) > 1 else 0.5
        
        # Prepare features
        X = np.array([[
            float(data['voltage']),
            float(data['temperature']),
            float(data['soc']),
            float(data['soh']),
            float(data['current']),
            float(voltage_var),
            float(temp_var),
            float(cycle_count)
        ]])
        
        X_scaled = scaler.transform(X)
        
        # Predict RUL from all models
        rul_predictions = {}
        for model_name, model_data in rul_models.items():
            try:
                if model_data["model"] is not None:
                    pred = float(model_data["model"].predict(X_scaled)[0])
                    rul_predictions[model_name] = max(0, pred)
                elif model_name == "Ensemble":
                    # Calculate ensemble as weighted average
                    rf_pred = max(0, float(rul_models["RandomForest"]["model"].predict(X_scaled)[0]))
                    gb_pred = max(0, float(rul_models["GradientBoosting"]["model"].predict(X_scaled)[0]))
                    et_pred = max(0, float(rul_models["ExtraTrees"]["model"].predict(X_scaled)[0]))
                    mlp_pred = max(0, float(rul_models["MLP"]["model"].predict(X_scaled)[0]))
                    rul_predictions[model_name] = rf_pred * 0.3 + gb_pred * 0.3 + et_pred * 0.2 + mlp_pred * 0.2
            except Exception as e:
                log.error(f"❌ Error predicting RUL with {model_name}: {e}")
        
        # Predict SOH from all models
        soh_predictions = {}
        for model_name, model_data in soh_models.items():
            try:
                if model_data["model"] is not None:
                    pred = float(model_data["model"].predict(X_scaled)[0])
                    soh_predictions[model_name] = np.clip(pred, 0, 100)
                elif model_name == "Ensemble":
                    rf_pred = np.clip(float(soh_models["RandomForest"]["model"].predict(X_scaled)[0]), 0, 100)
                    gb_pred = np.clip(float(soh_models["GradientBoosting"]["model"].predict(X_scaled)[0]), 0, 100)
                    et_pred = np.clip(float(soh_models["ExtraTrees"]["model"].predict(X_scaled)[0]), 0, 100)
                    mlp_pred = np.clip(float(soh_models["MLP"]["model"].predict(X_scaled)[0]), 0, 100)
                    soh_predictions[model_name] = rf_pred * 0.3 + gb_pred * 0.3 + et_pred * 0.2 + mlp_pred * 0.2
            except Exception as e:
                log.error(f"❌ Error predicting SOH with {model_name}: {e}")
        
        # Use best model predictions (Ensemble)
        best_rul = rul_predictions.get("Ensemble", rul_predictions.get("RandomForest", 0))
        best_soh = soh_predictions.get("Ensemble", soh_predictions.get("RandomForest", 50))
        
        # Calculate health status
        if best_soh >= 80:
            health_status = "EXCELLENT"
        elif best_soh >= 60:
            health_status = "GOOD"
        elif best_soh >= 40:
            health_status = "FAIR"
        elif best_soh >= 20:
            health_status = "POOR"
        else:
            health_status = "CRITICAL"
        
        cycle_count += 1
        
        return {
            "rul_cycles": int(best_rul),
            "rul_days": int(best_rul / 10),
            "predicted_soh": round(best_soh, 2),
            "health_status": health_status,
            "model_predictions": {
                "rul": {k: round(v, 2) for k, v in rul_predictions.items()},
                "soh": {k: round(v, 2) for k, v in soh_predictions.items()}
            },
            "confidence": "HIGH",
            "prediction_timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        log.error(f"❌ RUL/SOH prediction error: {e}", exc_info=True)
        return None

# ============================
# MQTT Callbacks
# ============================
def on_connect(client, userdata, flags, rc):
    """MQTT connection callback"""
    global mqtt_connected
    
    try:
        if rc == 0:
            mqtt_connected = True
            log.info(f"✅ Connected to MQTT broker at {MQTT_HOST}:{MQTT_PORT}")
            result = client.subscribe(MQTT_INPUT_TOPIC, qos=1)
            if result[0] == mqtt.MQTT_ERR_SUCCESS:
                log.info(f"📡 Subscribed to topic: {MQTT_INPUT_TOPIC}")
        else:
            mqtt_connected = False
            log.error(f"❌ MQTT connection failed with code {rc}")
    except Exception as e:
        log.error(f"❌ Error in on_connect: {e}", exc_info=True)

def on_disconnect(client, userdata, rc):
    """MQTT disconnect callback"""
    global mqtt_connected
    mqtt_connected = False
    
    try:
        if rc != 0:
            log.warning(f"⚠️  Unexpected disconnection (code: {rc})")
    except Exception as e:
        log.error(f"❌ Error in on_disconnect: {e}", exc_info=True)

def on_message(client, userdata, msg):
    """MQTT message callback"""
    global message_count
    
    try:
        try:
            payload = msg.payload.decode('utf-8')
            data = json.loads(payload)
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            log.error(f"❌ Invalid message format: {e}")
            return
        
        message_count += 1
        
        # Detect anomaly
        enriched_data = detect_anomaly(data)
        if enriched_data is None:
            return
        
        # Predict RUL and SOH
        predictions = predict_rul_and_soh(data)
        if predictions:
            enriched_data.update(predictions)
        
        # Log result
        if enriched_data.get('is_anomaly'):
            log.warning(
                f"⚠️  [{message_count}] ANOMALY: {enriched_data.get('anomaly_type')} | "
                f"RUL: {enriched_data.get('rul_cycles')} cycles | "
                f"SOH: {enriched_data.get('predicted_soh')}%"
            )
        else:
            log.info(
                f"✅ [{message_count}] NORMAL | "
                f"RUL: {enriched_data.get('rul_cycles')} cycles | "
                f"SOH: {enriched_data.get('predicted_soh')}% | "
                f"Health: {enriched_data.get('health_status')}"
            )
        
        # Publish to output topic
        try:
            result = client.publish(
                MQTT_OUTPUT_TOPIC,
                json.dumps(enriched_data),
                qos=1
            )
            
            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                log.error(f"❌ Failed to publish alert: {result.rc}")
        
        except Exception as e:
            log.error(f"❌ Error publishing message: {e}", exc_info=True)
    
    except Exception as e:
        log.error(f"❌ Unexpected error in on_message: {e}", exc_info=True)

def on_subscribe(client, userdata, mid, granted_qos):
    """MQTT subscription callback"""
    try:
        log.info(f"🔔 Subscription acknowledged with QoS: {granted_qos}")
    except Exception as e:
        log.error(f"❌ Error in on_subscribe: {e}", exc_info=True)

# ============================
# MQTT Client Setup
# ============================
def init_mqtt_client():
    """Initialize MQTT client"""
    try:
        client = mqtt.Client(
            client_id="ml-inference",
            clean_session=True,
            protocol=mqtt.MQTTv311
        )
        
        client.on_connect = on_connect
        client.on_disconnect = on_disconnect
        client.on_message = on_message
        client.on_subscribe = on_subscribe
        
        return client
    except Exception as e:
        log.error(f"❌ Failed to initialize MQTT client: {e}", exc_info=True)
        raise

def connect_mqtt(client):
    """Connect to MQTT broker with retry logic"""
    retry_count = 0
    max_retries = 10
    
    while retry_count < max_retries:
        try:
            log.info(f"🔌 Connecting to MQTT broker: {MQTT_HOST}:{MQTT_PORT}")
            client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
            client.loop_start()
            
            timeout = 10
            start_time = time.time()
            while not mqtt_connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)
            
            if mqtt_connected:
                log.info("✅ MQTT client started successfully")
                return True
            else:
                log.warning("⚠️  Connection timeout")
                client.loop_stop()
                return False
        
        except socket.gaierror as e:
            retry_count += 1
            log.warning(f"⚠️  DNS resolution failed (attempt {retry_count}/{max_retries}): {e}")
            if retry_count < max_retries:
                time.sleep(5)
        except ConnectionRefusedError as e:
            retry_count += 1
            log.warning(f"⚠️  Connection refused (attempt {retry_count}/{max_retries}): {e}")
            if retry_count < max_retries:
                time.sleep(5)
        except Exception as e:
            retry_count += 1
            log.error(f"❌ Unexpected error (attempt {retry_count}/{max_retries}): {e}")
            if retry_count < max_retries:
                time.sleep(5)
    
    log.error("❌ Failed to connect after max retries")
    return False

# ============================
# Main Loop
# ============================
def main():
    """Main application loop"""
    
    log.info("=" * 70)
    log.info("🤖 ML Inference Service - Enhanced with Multiple Models")
    log.info("=" * 70)
    log.info(f"MQTT Broker: {MQTT_HOST}:{MQTT_PORT}")
    log.info(f"Input Topic: {MQTT_INPUT_TOPIC}")
    log.info(f"Output Topic: {MQTT_OUTPUT_TOPIC}")
    log.info(f"Model Directory: {MODEL_DIR}")
    log.info("=" * 70 + "\n")
    
    # Load or create all models
    try:
        load_or_create_all_models()
    except Exception as e:
        log.error(f"❌ Failed to initialize models: {e}", exc_info=True)
        return 1
    
    # Initialize MQTT client
    try:
        client = init_mqtt_client()
    except Exception as e:
        log.error(f"❌ Failed to initialize MQTT client: {e}", exc_info=True)
        return 1
    
    # Connect to broker
    if not connect_mqtt(client):
        log.error("❌ Failed to connect to MQTT broker")
        return 1
    
    # Keep running
    try:
        log.info("🟢 ML Inference running... Press Ctrl+C to stop\n")
        while True:
            time.sleep(1)
    
    except KeyboardInterrupt:
        log.info("\n⏹️  Shutting down ML inference service...")
    except Exception as e:
        log.error(f"❌ Fatal error in main loop: {e}", exc_info=True)
        return 1
    finally:
        try:
            client.loop_stop()
            client.disconnect()
        except Exception as e:
            log.error(f"❌ Error during cleanup: {e}")
        
        log.info("✅ ML Inference service stopped cleanly")
        log.info(f"Total messages processed: {message_count}")
        log.info(f"Total anomalies detected: {anomaly_count}")
    
    return 0

if __name__ == "__main__":
    exit(main())