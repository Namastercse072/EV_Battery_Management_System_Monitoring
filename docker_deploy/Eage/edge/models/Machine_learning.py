#!/usr/bin/env python3
"""
ML Inference Service - Anomaly Detection
Consumes battery metrics from MQTT, detects anomalies, publishes alerts
"""

import json
import logging
import os
import time
import numpy as np
import paho.mqtt.client as mqtt
from sklearn.ensemble import IsolationForest
import joblib
from datetime import datetime
from typing import Dict, Any, Optional
import socket
import warnings

# Suppress deprecated warnings
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

MODEL_PATH = os.getenv("MODEL_PATH", "/app/models/isoforest.pkl")
MODEL_DIR = os.path.dirname(MODEL_PATH) or "/app/models"

# Anomaly detection thresholds
CONTAMINATION = float(os.getenv("CONTAMINATION", 0.1))
ANOMALY_SCORE_THRESHOLD = float(os.getenv("ANOMALY_THRESHOLD", -0.5))

# ⚠️ IMPORTANT: Define features ONCE and use consistently
FEATURE_NAMES = ["voltage", "temperature", "soc", "soh", "current"]
FEATURE_COUNT = len(FEATURE_NAMES)

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
model: Optional[IsolationForest] = None
message_count = 0
anomaly_count = 0

# ============================
# Model Management
# ============================
def create_model() -> IsolationForest:
    """
    Create and train a new IsolationForest model with synthetic data
    ⚠️ MUST use EXACTLY FEATURE_COUNT features
    """
    log.info(f"🤖 Training new IsolationForest model with {FEATURE_COUNT} features...")
    
    try:
        # Generate synthetic training data (normal battery behavior)
        # IMPORTANT: Use same feature order as FEATURE_NAMES
        normal_data = []
        
        for _ in range(1000):
            voltage = np.random.normal(3.8, 0.2)      # voltage
            temperature = np.random.normal(35, 5)      # temperature
            soc = np.random.normal(75, 15)             # soc
            soh = np.random.normal(90, 5)              # soh
            current = np.random.normal(50, 20)         # current
            
            # CRITICAL: Same order as FEATURE_NAMES
            normal_data.append([voltage, temperature, soc, soh, current])
        
        normal_data = np.array(normal_data)
        
        log.info(f"📊 Training data shape: {normal_data.shape}")
        
        # Train model
        model = IsolationForest(
            contamination=CONTAMINATION,
            random_state=42,
            n_estimators=100,
            max_samples='auto',
            n_jobs=-1  # Use all CPU cores
        )
        model.fit(normal_data)
        
        # Verify model expects correct number of features
        n_features = model.n_features_in_
        log.info(f"✅ Model trained successfully")
        log.info(f"   - Contamination: {CONTAMINATION}")
        log.info(f"   - Features expected: {n_features}")
        log.info(f"   - Features provided: {FEATURE_COUNT}")
        
        if n_features != FEATURE_COUNT:
            raise ValueError(
                f"Feature mismatch! Model expects {n_features} but "
                f"FEATURE_COUNT is {FEATURE_COUNT}"
            )
        
        return model
    
    except Exception as e:
        log.error(f"❌ Failed to train model: {e}", exc_info=True)
        raise

def load_or_create_model() -> IsolationForest:
    """Load existing model or create new one"""
    global model
    
    # Ensure model directory exists
    try:
        os.makedirs(MODEL_DIR, exist_ok=True)
        # Try to write test file to verify permissions
        test_file = os.path.join(MODEL_DIR, '.write_test')
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
        log.info(f"✅ Model directory is writable: {MODEL_DIR}")
    except (OSError, PermissionError) as e:
        log.warning(f"⚠️  Model directory not writable: {e}")
        log.info("💾 Models will not be persisted (in-memory only)")
    
    # Try to load existing model
    if os.path.exists(MODEL_PATH):
        try:
            log.info(f"📂 Loading model from {MODEL_PATH}")
            model = joblib.load(MODEL_PATH)
            
            # Verify loaded model has correct feature count
            n_features = model.n_features_in_
            if n_features != FEATURE_COUNT:
                log.warning(
                    f"⚠️  Feature mismatch! Model has {n_features} features "
                    f"but FEATURE_COUNT is {FEATURE_COUNT}. Retraining..."
                )
                raise ValueError("Feature count mismatch")
            
            log.info(f"✅ Model loaded successfully ({n_features} features)")
            return model
        except Exception as e:
            log.warning(f"⚠️  Failed to load model: {e}. Training new model...")
    
    # Create new model
    model = create_model()
    
    # Save model for future use (with error handling)
    try:
        if os.access(MODEL_DIR, os.W_OK):
            joblib.dump(model, MODEL_PATH)
            log.info(f"💾 Model saved to {MODEL_PATH}")
        else:
            log.warning(
                f"⚠️  Cannot save model (directory not writable). "
                f"Using in-memory model only."
            )
    except (OSError, PermissionError) as e:
        log.warning(f"⚠️  Failed to save model: {e}. Using in-memory model only.")
    
    return model

# ============================
# Anomaly Detection
# ============================
def validate_data(data: Dict[str, Any]) -> bool:
    """Validate incoming sensor data"""
    try:
        for feature in FEATURE_NAMES:
            if feature not in data:
                log.debug(f"❌ Missing feature: {feature}")
                return False
            
            value = data[feature]
            
            # Type check
            if not isinstance(value, (int, float)):
                log.debug(f"❌ Invalid type for {feature}: {type(value)}")
                return False
            
            min_val, max_val = FEATURE_RANGES[feature]
            
            if not (min_val <= value <= max_val):
                log.debug(
                    f"❌ Out of range: {feature}={value} "
                    f"(expected {min_val}-{max_val})"
                )
                return False
        
        return True
    
    except Exception as e:
        log.error(f"❌ Data validation error: {e}", exc_info=True)
        return False

def detect_anomaly(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Detect anomalies using IsolationForest
    Returns enriched data with anomaly flags
    ⚠️ MUST extract features in EXACT order as FEATURE_NAMES
    """
    global model, anomaly_count
    
    try:
        # Validate input
        if not validate_data(data):
            log.debug("⚠️  Invalid data skipped")
            return None
        
        # ⚠️ CRITICAL: Extract features in EXACT same order as FEATURE_NAMES
        # Use list [[...]] for 2D array, not set {...}
        try:
            X = np.array([[
                float(data['voltage']),      # Feature 0
                float(data['temperature']),  # Feature 1
                float(data['soc']),          # Feature 2
                float(data['soh']),          # Feature 3
                float(data['current'])       # Feature 4
            ]])
        except (KeyError, ValueError, TypeError) as e:
            log.error(f"❌ Failed to extract features: {e}")
            return None
        
        # Verify shape before prediction
        if X.shape[0] != 1 or X.shape[1] != FEATURE_COUNT:
            log.error(
                f"❌ Feature shape mismatch! "
                f"Expected (1, {FEATURE_COUNT}), got {X.shape}"
            )
            return None
        
        # Get prediction and anomaly score (with error handling)
        try:
            predictions = model.predict(X)
            if not isinstance(predictions, np.ndarray) or len(predictions) == 0:
                log.error(f"❌ Invalid prediction result: {predictions}")
                return None
            
            prediction = int(predictions[0])  # -1 = anomaly, 1 = normal
            
            anomaly_scores = model.score_samples(X)
            if not isinstance(anomaly_scores, np.ndarray) or len(anomaly_scores) == 0:
                log.error(f"❌ Invalid anomaly score result: {anomaly_scores}")
                return None
            
            anomaly_score = float(anomaly_scores[0])
        
        except (IndexError, TypeError, ValueError) as e:
            log.error(f"❌ Prediction error: {e}", exc_info=True)
            return None
        
        # Determine anomaly type
        is_anomaly = prediction == -1
        anomaly_type = "NORMAL"
        severity = "INFO"
        
        if is_anomaly:
            anomaly_count += 1
            
            # Classify anomaly type based on feature values
            try:
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
            except (KeyError, ValueError, TypeError) as e:
                log.error(f"❌ Failed to classify anomaly: {e}")
                anomaly_type = "UNKNOWN"
                severity = "WARNING"
        
        # Enrich data with results
        try:
            enriched_data = {
                **data,
                "is_anomaly": is_anomaly,
                "anomaly_type": anomaly_type,
                "anomaly_score": round(anomaly_score, 4),
                "severity": severity,
                "detection_timestamp": datetime.utcnow().isoformat(),
                "model_version": "1.0",
                "features_used": FEATURE_COUNT
            }
            
            return enriched_data
        
        except Exception as e:
            log.error(f"❌ Failed to enrich data: {e}", exc_info=True)
            return None
    
    except Exception as e:
        log.error(f"❌ Unexpected error in anomaly detection: {e}", exc_info=True)
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
                log.error(f"❌ Subscription failed: {result[0]}")
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
        else:
            log.info("📴 Disconnected from MQTT broker")
    except Exception as e:
        log.error(f"❌ Error in on_disconnect: {e}", exc_info=True)

def on_message(client, userdata, msg):
    """MQTT message callback - process sensor data"""
    global message_count
    
    try:
        # Decode payload
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
            log.debug(f"⏭️  Message {message_count} skipped (detection failed)")
            return
        
        # Log result
        try:
            if enriched_data['is_anomaly']:
                log.warning(
                    f"⚠️  [{message_count}] ANOMALY: {enriched_data['anomaly_type']} | "
                    f"Score: {enriched_data['anomaly_score']} | "
                    f"Severity: {enriched_data['severity']}"
                )
            else:
                log.info(
                    f"✅ [{message_count}] NORMAL | "
                    f"V={data.get('voltage', 'N/A')}V | "
                    f"T={data.get('temperature', 'N/A')}°C | "
                    f"SOC={data.get('soc', 'N/A')}%"
                )
        except Exception as e:
            log.error(f"❌ Error in logging result: {e}")
        
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

def on_log(client, userdata, level, buf):
    """MQTT logger callback"""
    try:
        if level == mqtt.MQTT_LOG_DEBUG:
            log.debug(f"MQTT: {buf}")
        elif level == mqtt.MQTT_LOG_INFO:
            log.info(f"MQTT: {buf}")
        elif level == mqtt.MQTT_LOG_WARNING:
            log.warning(f"MQTT: {buf}")
        elif level == mqtt.MQTT_LOG_ERR:
            log.error(f"MQTT: {buf}")
    except Exception as e:
        log.error(f"❌ Error in on_log: {e}", exc_info=True)

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
        
        # Set callbacks
        client.on_connect = on_connect
        client.on_disconnect = on_disconnect
        client.on_message = on_message
        client.on_subscribe = on_subscribe
        client.on_log = on_log
        
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
            
            # Wait for connection
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
    log.info("🤖 ML Inference Service - Anomaly Detection")
    log.info("=" * 70)
    log.info(f"MQTT Broker: {MQTT_HOST}:{MQTT_PORT}")
    log.info(f"Input Topic: {MQTT_INPUT_TOPIC}")
    log.info(f"Output Topic: {MQTT_OUTPUT_TOPIC}")
    log.info(f"Model Path: {MODEL_PATH}")
    log.info(f"Features: {FEATURE_NAMES}")
    log.info(f"Feature Count: {FEATURE_COUNT}")
    log.info(f"Contamination: {CONTAMINATION}")
    log.info("=" * 70 + "\n")
    
    # Load or create model
    try:
        global model
        model = load_or_create_model()
        if model is None:
            log.error("❌ Model is None after initialization")
            return 1
    except Exception as e:
        log.error(f"❌ Failed to initialize model: {e}", exc_info=True)
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