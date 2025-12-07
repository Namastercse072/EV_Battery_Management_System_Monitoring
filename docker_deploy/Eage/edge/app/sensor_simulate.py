#!/usr/bin/env python3
"""
EV Battery Sensor Simulator with Optimization Techniques
- Bloom Filter for duplicate detection
- Zstandard compression for payload optimization
- Detailed metrics logging for performance evaluation
- Memory and CPU optimization
"""

import json
import time
import logging
import socket
import random
import numpy as np
import paho.mqtt.client as mqtt
import psutil
import os
import zstandard as zstd
from datetime import datetime
from typing import Dict, Any, Tuple
from pybloom_live import BloomFilter
from collections import deque
import sys

# ============================
# Enhanced Logging Configuration
# ============================
class MetricsFormatter(logging.Formatter):
    """Custom formatter for detailed metrics logging"""
    
    def format(self, record):
        if hasattr(record, 'metrics'):
            return f"{record.asctime} - {record.name} - {record.levelname} - {record.getMessage()}\n  Metrics: {record.metrics}"
        return super().format(record)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/sensor_simulator.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger(__name__)

# ============================
# Configuration
# ============================
MQTT_HOST = os.getenv("MQTT_HOST", "mqtt-broker")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "ev/metrics")
PUBLISH_INTERVAL = int(os.getenv("PUBLISH_INTERVAL", 2))
ENABLE_COMPRESSION = os.getenv("ENABLE_COMPRESSION", "true").lower() == "true"
ENABLE_BLOOM_FILTER = os.getenv("ENABLE_BLOOM_FILTER", "true").lower() == "true"
METRICS_LOG_INTERVAL = int(os.getenv("METRICS_LOG_INTERVAL", 50))

# Battery simulation parameters
VOLTAGE_RANGE = (3.0, 4.2)
TEMPERATURE_RANGE = (20, 45)
CURRENT_RANGE = (0, 150)
SOC_RANGE = (20, 100)
SOH_RANGE = (50, 100)

# ============================
# Performance Metrics Tracker
# ============================
class PerformanceMetrics:
    """Track performance metrics before and after optimizations"""
    
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        
        # Payload metrics
        self.uncompressed_sizes = deque(maxlen=window_size)
        self.compressed_sizes = deque(maxlen=window_size)
        self.compression_times = deque(maxlen=window_size)
        
        # Duplicate detection
        self.duplicate_count = 0
        self.total_messages = 0
        self.bloom_filter_checks = deque(maxlen=window_size)
        
        # System metrics
        self.cpu_usage = deque(maxlen=window_size)
        self.memory_usage = deque(maxlen=window_size)
        self.mqtt_publish_times = deque(maxlen=window_size)
        
        # Counters
        self.messages_sent = 0
        self.messages_rejected = 0
        self.anomalies_sent = 0
        
        # Timestamps
        self.start_time = time.time()
        self.last_metrics_log = time.time()
    
    def add_uncompressed_payload(self, size: int):
        """Record uncompressed payload size"""
        self.uncompressed_sizes.append(size)
    
    def add_compressed_payload(self, size: int, compression_time: float):
        """Record compressed payload size and compression time"""
        self.compressed_sizes.append(size)
        self.compression_times.append(compression_time)
    
    def add_bloom_check(self, is_duplicate: bool, check_time: float):
        """Record Bloom filter check result"""
        self.bloom_filter_checks.append({
            'is_duplicate': is_duplicate,
            'check_time': check_time
        })
        if is_duplicate:
            self.duplicate_count += 1
    
    def add_system_metrics(self):
        """Record current system metrics"""
        self.cpu_usage.append(psutil.cpu_percent(interval=0.1))
        self.memory_usage.append(psutil.virtual_memory().percent)
    
    def add_publish_time(self, publish_time: float):
        """Record MQTT publish time"""
        self.mqtt_publish_times.append(publish_time)
    
    def get_compression_stats(self) -> Dict[str, Any]:
        """Calculate compression statistics"""
        if not self.uncompressed_sizes:
            return {}
        
        avg_uncompressed = np.mean(self.uncompressed_sizes)
        avg_compressed = np.mean(self.compressed_sizes)
        compression_ratio = (1 - avg_compressed / avg_uncompressed) * 100
        avg_compression_time = np.mean(self.compression_times)
        
        return {
            "avg_uncompressed_size_bytes": round(avg_uncompressed, 2),
            "avg_compressed_size_bytes": round(avg_compressed, 2),
            "compression_ratio_percent": round(compression_ratio, 2),
            "avg_compression_time_ms": round(avg_compression_time * 1000, 2),
            "total_compressed": sum(self.compressed_sizes),
            "total_uncompressed": sum(self.uncompressed_sizes)
        }
    
    def get_bloom_stats(self) -> Dict[str, Any]:
        """Calculate Bloom filter statistics"""
        if not self.bloom_filter_checks:
            return {}
        
        duplicate_rate = (self.duplicate_count / self.total_messages * 100) if self.total_messages > 0 else 0
        avg_check_time = np.mean([x['check_time'] for x in self.bloom_filter_checks])
        
        return {
            "total_messages": self.total_messages,
            "duplicates_detected": self.duplicate_count,
            "duplicate_rate_percent": round(duplicate_rate, 2),
            "avg_check_time_ms": round(avg_check_time * 1000, 4),
            "false_positive_rate": 0.001,
            "bloom_filter_capacity": 10000
        }
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Calculate system resource statistics"""
        if not self.cpu_usage or not self.memory_usage:
            return {}
        
        avg_cpu = np.mean(self.cpu_usage)
        avg_memory = np.mean(self.memory_usage)
        max_cpu = np.max(self.cpu_usage)
        max_memory = np.max(self.memory_usage)
        
        return {
            "avg_cpu_usage_percent": round(avg_cpu, 2),
            "avg_memory_usage_percent": round(avg_memory, 2),
            "peak_cpu_usage_percent": round(max_cpu, 2),
            "peak_memory_usage_percent": round(max_memory, 2),
            "uptime_seconds": round(time.time() - self.start_time, 1)
        }
    
    def get_mqtt_stats(self) -> Dict[str, Any]:
        """Calculate MQTT publish statistics"""
        if not self.mqtt_publish_times:
            return {}
        
        avg_publish_time = np.mean(self.mqtt_publish_times)
        max_publish_time = np.max(self.mqtt_publish_times)
        
        return {
            "messages_sent": self.messages_sent,
            "messages_rejected": self.messages_rejected,
            "anomalies_sent": self.anomalies_sent,
            "avg_publish_time_ms": round(avg_publish_time * 1000, 2),
            "max_publish_time_ms": round(max_publish_time * 1000, 2),
            "success_rate_percent": round((self.messages_sent / (self.messages_sent + self.messages_rejected) * 100) if (self.messages_sent + self.messages_rejected) > 0 else 0, 2)
        }
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all metrics for reporting"""
        return {
            "compression": self.get_compression_stats(),
            "bloom_filter": self.get_bloom_stats(),
            "system": self.get_system_stats(),
            "mqtt": self.get_mqtt_stats(),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def log_metrics_summary(self):
        """Log comprehensive metrics summary"""
        all_metrics = self.get_all_metrics()
        
        log.info("\n" + "="*80)
        log.info("📊 PERFORMANCE METRICS SUMMARY")
        log.info("="*80)
        
        # Compression Metrics
        comp = all_metrics.get('compression', {})
        if comp:
            log.info("\n🗜️  COMPRESSION ANALYSIS:")
            log.info(f"   Uncompressed Payload:    {comp.get('avg_uncompressed_size_bytes', 0):.2f} bytes")
            log.info(f"   Compressed Payload:      {comp.get('avg_compressed_size_bytes', 0):.2f} bytes")
            log.info(f"   Compression Ratio:       {comp.get('compression_ratio_percent', 0):.2f}%")
            log.info(f"   Avg Compression Time:    {comp.get('avg_compression_time_ms', 0):.2f} ms")
            log.info(f"   Total Data Saved:        {(comp.get('total_uncompressed', 0) - comp.get('total_compressed', 0)) / 1024:.2f} KB")
        
        # Bloom Filter Metrics
        bloom = all_metrics.get('bloom_filter', {})
        if bloom:
            log.info("\n🔍 BLOOM FILTER ANALYSIS:")
            log.info(f"   Total Messages:          {bloom.get('total_messages', 0)}")
            log.info(f"   Duplicates Detected:     {bloom.get('duplicates_detected', 0)}")
            log.info(f"   Duplicate Rate:          {bloom.get('duplicate_rate_percent', 0):.2f}%")
            log.info(f"   Avg Check Time:          {bloom.get('avg_check_time_ms', 0):.4f} ms")
            log.info(f"   False Positive Rate:     {bloom.get('false_positive_rate', 0):.4f}")
        
        # System Metrics
        sys_metrics = all_metrics.get('system', {})
        if sys_metrics:
            log.info("\n💻 SYSTEM RESOURCE USAGE:")
            log.info(f"   Avg CPU Usage:           {sys_metrics.get('avg_cpu_usage_percent', 0):.2f}%")
            log.info(f"   Avg Memory Usage:        {sys_metrics.get('avg_memory_usage_percent', 0):.2f}%")
            log.info(f"   Peak CPU Usage:          {sys_metrics.get('peak_cpu_usage_percent', 0):.2f}%")
            log.info(f"   Peak Memory Usage:       {sys_metrics.get('peak_memory_usage_percent', 0):.2f}%")
            log.info(f"   Uptime:                  {sys_metrics.get('uptime_seconds', 0):.1f} seconds")
        
        # MQTT Metrics
        mqtt_metrics = all_metrics.get('mqtt', {})
        if mqtt_metrics:
            log.info("\n📡 MQTT PUBLISHING:")
            log.info(f"   Messages Sent:           {mqtt_metrics.get('messages_sent', 0)}")
            log.info(f"   Messages Rejected:       {mqtt_metrics.get('messages_rejected', 0)}")
            log.info(f"   Anomalies Sent:          {mqtt_metrics.get('anomalies_sent', 0)}")
            log.info(f"   Avg Publish Time:        {mqtt_metrics.get('avg_publish_time_ms', 0):.2f} ms")
            log.info(f"   Max Publish Time:        {mqtt_metrics.get('max_publish_time_ms', 0):.2f} ms")
            log.info(f"   Success Rate:            {mqtt_metrics.get('success_rate_percent', 0):.2f}%")
        
        log.info("\n" + "="*80 + "\n")

# ============================
# Compression Handler
# ============================
class CompressionHandler:
    """Handle payload compression/decompression"""
    
    def __init__(self):
        self.compressor = zstd.ZstdCompressor(level=10)
        self.decompressor = zstd.ZstdDecompressor()
    
    def compress(self, data: str) -> Tuple[bytes, float]:
        """Compress data and return compressed data with compression time"""
        start_time = time.time()
        compressed = self.compressor.compress(data.encode('utf-8'))
        compression_time = time.time() - start_time
        return compressed, compression_time
    
    def decompress(self, data: bytes) -> str:
        """Decompress data"""
        return self.decompressor.decompress(data).decode('utf-8')

# ============================
# Global State
# ============================
mqtt_connected = False
message_count = 0
metrics = PerformanceMetrics(window_size=100)
compression_handler = CompressionHandler()

last_values = {
    "voltage": 3.8,
    "temperature": 35,
    "current": 50,
    "soc": 75,
    "soh": 95
}

# Initialize Bloom filter for duplicate detection
bloom_filter = BloomFilter(capacity=10000, error_rate=0.001)

# ============================
# MQTT Callbacks
# ============================
def on_connect(client, userdata, flags, rc):
    """MQTT connection callback"""
    global mqtt_connected
    
    if rc == 0:
        mqtt_connected = True
        log.info(f"✅ Connected to MQTT broker at {MQTT_HOST}:{MQTT_PORT}")
        log.info(f"   Client ID: {client._client_id.decode() if isinstance(client._client_id, bytes) else client._client_id}")
        log.info(f"   Protocol Version: MQTT 3.1.1")
        log.info(f"   Keep Alive: 60 seconds")
    else:
        mqtt_connected = False
        log.error(f"❌ MQTT connection failed with code {rc}")
        log.error(f"   Return Code Meaning:")
        log.error(f"   0 = Connection successful")
        log.error(f"   1 = Connection refused - incorrect protocol version")
        log.error(f"   2 = Connection refused - invalid client identifier")
        log.error(f"   3 = Connection refused - server unavailable")
        log.error(f"   4 = Connection refused - bad username or password")
        log.error(f"   5 = Connection refused - not authorised")

def on_disconnect(client, userdata, rc):
    """MQTT disconnect callback"""
    global mqtt_connected
    mqtt_connected = False
    
    if rc != 0:
        log.warning(f"⚠️  Unexpected disconnection (code: {rc}). Reconnecting...")
    else:
        log.info("📴 Gracefully disconnected from MQTT broker")

def on_publish(client, userdata, mid):
    """MQTT publish callback"""
    log.debug(f"📤 Message published successfully (MID: {mid})")

def on_log(client, userdata, level, buf):
    """MQTT logger callback"""
    if level == mqtt.MQTT_LOG_DEBUG:
        log.debug(f"MQTT: {buf}")
    elif level == mqtt.MQTT_LOG_INFO:
        log.info(f"MQTT: {buf}")
    elif level == mqtt.MQTT_LOG_WARNING:
        log.warning(f"MQTT: {buf}")
    elif level == mqtt.MQTT_LOG_ERR:
        log.error(f"MQTT: {buf}")

# ============================
# Sensor Data Generation with Bloom Filter
# ============================
def generate_sensor_data() -> Dict[str, Any]:
    """
    Generate synthetic battery sensor data with realistic variations
    Includes Bloom filter for duplicate detection
    """
    global last_values, metrics
    
    # Add small variations to last values
    voltage = last_values["voltage"] + random.uniform(-0.05, 0.05)
    voltage = max(VOLTAGE_RANGE[0], min(VOLTAGE_RANGE[1], voltage))
    
    temperature = last_values["temperature"] + random.uniform(-2, 2)
    temperature = max(TEMPERATURE_RANGE[0], min(TEMPERATURE_RANGE[1], temperature))
    
    current = last_values["current"] + random.uniform(-10, 10)
    current = max(CURRENT_RANGE[0], min(CURRENT_RANGE[1], current))
    
    soc = last_values["soc"] - random.uniform(0, 1)
    soc = max(SOC_RANGE[0], min(SOC_RANGE[1], soc))
    
    soh = last_values["soh"] - random.uniform(0, 0.1)
    soh = max(SOH_RANGE[0], min(SOH_RANGE[1], soh))
    
    # Update last values
    last_values = {
        "voltage": voltage,
        "temperature": temperature,
        "current": current,
        "soc": soc,
        "soh": soh
    }
    
    # Create message
    data = {
        "voltage": round(voltage, 2),
        "temperature": round(temperature, 1),
        "current": round(current, 1),
        "soc": round(soc, 1),
        "soh": round(soh, 1),
        "remaining_capacity": round(soc * 20, 1),
        "timestamp": datetime.utcnow().isoformat(),
        "device_id": "EV_001",
        "location": "charging_station_01"
    }
    
    return data

def generate_anomaly() -> Dict[str, Any]:
    """Generate anomalous battery data for testing"""
    return {
        "voltage": round(random.uniform(4.5, 5.0), 2),
        "temperature": round(random.uniform(55, 70), 1),
        "current": round(random.uniform(200, 300), 1),
        "soc": round(random.uniform(5, 15), 1),
        "soh": round(random.uniform(20, 40), 1),
        "remaining_capacity": 5,
        "timestamp": datetime.utcnow().isoformat(),
        "device_id": "EV_001",
        "location": "charging_station_01",
        "is_anomaly": True
    }

def is_duplicate(data: Dict[str, Any]) -> bool:
    """
    Check if data is duplicate using Bloom filter
    Returns True if likely duplicate, False otherwise
    """
    start_time = time.time()
    
    # Create hash key from critical fields
    hash_key = json.dumps({
        'v': data['voltage'],
        't': data['temperature'],
        'c': data['current'],
        's': data['soc'],
        'h': data['soh']
    }, sort_keys=True)
    
    # Check if in Bloom filter
    is_dup = hash_key in bloom_filter
    
    # Add to Bloom filter
    bloom_filter.add(hash_key)
    
    check_time = time.time() - start_time
    metrics.add_bloom_check(is_dup, check_time)
    
    return is_dup

# ============================
# Payload Processing
# ============================
def process_payload(data: Dict[str, Any]) -> Tuple[bytes, Dict[str, Any]]:
    """
    Process payload: JSON encode, compress, and track metrics
    """
    # JSON encode
    json_payload = json.dumps(data)
    uncompressed_size = len(json_payload.encode('utf-8'))
    metrics.add_uncompressed_payload(uncompressed_size)
    
    # Compress if enabled
    if ENABLE_COMPRESSION:
        compressed_payload, compression_time = compression_handler.compress(json_payload)
        compressed_size = len(compressed_payload)
        metrics.add_compressed_payload(compressed_size, compression_time)
        
        log.debug(
            f"Compression: {uncompressed_size} -> {compressed_size} bytes "
            f"({((1 - compressed_size/uncompressed_size) * 100):.1f}% reduction) "
            f"in {compression_time*1000:.2f}ms"
        )
        return compressed_payload, {
            "original_size": uncompressed_size,
            "compressed_size": compressed_size,
            "compression_ratio": round((1 - compressed_size/uncompressed_size) * 100, 2)
        }
    else:
        return json_payload.encode('utf-8'), {
            "original_size": uncompressed_size,
            "compressed_size": uncompressed_size,
            "compression_ratio": 0
        }

# ============================
# MQTT Connection & Publishing
# ============================
def init_mqtt_client():
    """Initialize MQTT client"""
    client = mqtt.Client(client_id="sensor-simulator", clean_session=True)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_publish = on_publish
    client.on_log = on_log
    return client

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
    global message_count, metrics
    
    log.info("=" * 80)
    log.info("🔋 EV Battery Sensor Simulator - Enhanced Edition")
    log.info("=" * 80)
    log.info(f"MQTT Broker:           {MQTT_HOST}:{MQTT_PORT}")
    log.info(f"Topic:                 {MQTT_TOPIC}")
    log.info(f"Publish Interval:      {PUBLISH_INTERVAL} seconds")
    log.info(f"Compression Enabled:   {ENABLE_COMPRESSION}")
    log.info(f"Bloom Filter Enabled:  {ENABLE_BLOOM_FILTER}")
    log.info(f"Metrics Log Interval:  {METRICS_LOG_INTERVAL} messages")
    log.info("=" * 80 + "\n")
    
    # Initialize MQTT client
    client = init_mqtt_client()
    
    # Connect to broker
    if not connect_mqtt(client):
        log.error("❌ Failed to initialize sensor simulator")
        return 1
    
    # Main publishing loop
    try:
        log.info("🟢 Sensor simulator running... Press Ctrl+C to stop\n")
        
        anomaly_counter = 0
        anomaly_frequency = 50
        
        while True:
            try:
                # Generate sensor data
                if anomaly_counter % anomaly_frequency == 0 and anomaly_counter > 0:
                    data = generate_anomaly()
                    log.warning(f"⚠️  ANOMALY generated for testing")
                    metrics.anomalies_sent += 1
                else:
                    data = generate_sensor_data()
                
                anomaly_counter += 1
                metrics.total_messages += 1
                
                # Check for duplicates using Bloom filter
                if ENABLE_BLOOM_FILTER:
                    if is_duplicate(data):
                        log.debug("🔄 Duplicate detected, skipping publish")
                        metrics.messages_rejected += 1
                        time.sleep(PUBLISH_INTERVAL)
                        continue
                
                # Process payload (compress + metrics)
                payload, payload_metrics = process_payload(data)
                
                # Publish to MQTT
                start_publish_time = time.time()
                result = client.publish(MQTT_TOPIC, payload, qos=1)
                publish_time = time.time() - start_publish_time
                metrics.add_publish_time(publish_time)
                
                message_count += 1
                
                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    metrics.messages_sent += 1
                    
                    log.info(
                        f"📤 [{message_count}] Published | "
                        f"V={data['voltage']}V | "
                        f"T={data['temperature']}°C | "
                        f"SOC={data['soc']}% | "
                        f"SOH={data['soh']}% | "
                        f"Size: {payload_metrics['original_size']}→{payload_metrics['compressed_size']}B "
                        f"({payload_metrics['compression_ratio']}%) | "
                        f"Publish: {publish_time*1000:.2f}ms"
                    )
                else:
                    metrics.messages_rejected += 1
                    log.error(f"❌ Publish failed with code {result.rc}")
                
                # Log metrics at interval
                if message_count % METRICS_LOG_INTERVAL == 0:
                    metrics.log_metrics_summary()
                
                # Collect system metrics
                metrics.add_system_metrics()
                
                # Wait before next publish
                time.sleep(PUBLISH_INTERVAL)
                
            except json.JSONEncodeError as e:
                log.error(f"❌ JSON encoding error: {e}")
                time.sleep(1)
            except Exception as e:
                log.error(f"❌ Error in publish loop: {e}", exc_info=True)
                time.sleep(1)
    
    except KeyboardInterrupt:
        log.info("\n⏹️  Shutting down sensor simulator...")
    except Exception as e:
        log.error(f"❌ Fatal error: {e}", exc_info=True)
        return 1
    finally:
        # Final metrics report
        log.info("\n" + "=" * 80)
        log.info("📊 FINAL SESSION REPORT")
        log.info("=" * 80)
        metrics.log_metrics_summary()
        
        client.loop_stop()
        client.disconnect()
        log.info("✅ Sensor simulator stopped cleanly")
        log.info(f"Total messages processed: {message_count}")
    
    return 0

if __name__ == "__main__":
    exit(main())
