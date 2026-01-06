#!/usr/bin/env python3
"""
MQTT to Kafka Bridge
Forwards sensor data from Edge (MQTT) → Cloud (Kafka)
Demo version (no TLS/SSL)
"""

import paho.mqtt.client as mqtt
from kafka import KafkaProducer
import json
import logging
import time
import os
from datetime import datetime

# ============================
# Logging Setup
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
MQTT_TOPICS = ["ev/metrics", "ev/status", "ev/alerts"]

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka-broker-1:29092")
KAFKA_TOPIC = "ev_raw"

# ============================
# Global State
# ============================
mqtt_connected = False
kafka_producer = None
message_count = 0

# ============================
# Kafka Producer Setup
# ============================
def init_kafka_producer():
    """Initialize Kafka producer with retry logic"""
    global kafka_producer
    
    retry_count = 0
    max_retries = 10
    
    while retry_count < max_retries:
        try:
            log.info(f"🔌 Connecting to Kafka broker: {KAFKA_BROKER}")
            kafka_producer = KafkaProducer(
                bootstrap_servers=KAFKA_BROKER,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                acks='all',
                retries=3,
                max_in_flight_requests_per_connection=1
            )
            log.info("✅ Kafka producer initialized successfully")
            return True
        except Exception as e:
            retry_count += 1
            log.warning(f"⚠️  Kafka connection failed (attempt {retry_count}/{max_retries}): {e}")
            if retry_count < max_retries:
                time.sleep(5)
            else:
                log.error("❌ Failed to connect to Kafka after max retries")
                return False
    
    return False

# ============================
# MQTT Callbacks
# ============================
def on_connect(client, userdata, flags, rc):
    """MQTT connection callback"""
    global mqtt_connected
    
    if rc == 0:
        log.info("✅ Connected to MQTT broker")
        mqtt_connected = True
        
        # Subscribe to topics
        for topic in MQTT_TOPICS:
            client.subscribe(topic, qos=1)
            log.info(f"📡 Subscribed to topic: {topic}")
    else:
        mqtt_connected = False
        log.error(f"❌ MQTT connection failed with code {rc}")

def on_disconnect(client, userdata, rc):
    """MQTT disconnect callback"""
    global mqtt_connected
    mqtt_connected = False
    
    if rc != 0:
        log.warning(f"⚠️  Unexpected MQTT disconnection (code: {rc})")
    else:
        log.info("📴 Disconnected from MQTT broker")

def on_message(client, userdata, msg):
    """MQTT message callback - forward to Kafka"""
    global message_count
    
    try:
        # Decode payload
        payload = msg.payload.decode('utf-8')
        
        # Parse JSON
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            log.warning(f"⚠️  Invalid JSON from {msg.topic}: {payload}")
            return
        
        # Add metadata
        data['_source_topic'] = msg.topic
        data['_bridge_timestamp'] = datetime.utcnow().isoformat()
        data['_qos'] = msg.qos
        
        # Send to Kafka
        future = kafka_producer.send(KAFKA_TOPIC, value=data)
        record_metadata = future.get(timeout=5)
        
        message_count += 1
        log.info(
            f"📨 [{message_count}] MQTT:{msg.topic} → Kafka:{KAFKA_TOPIC} | "
            f"Partition:{record_metadata.partition} | "
            f"Offset:{record_metadata.offset}"
        )
        
    except Exception as e:
        log.error(f"❌ Error processing message from {msg.topic}: {e}", exc_info=True)

def on_subscribe(client, userdata, mid, granted_qos):
    """MQTT subscription callback"""
    log.info(f"🔔 Subscription acknowledged with QoS: {granted_qos}")

# ============================
# MQTT Client Setup
# ============================
def init_mqtt_client():
    """Initialize MQTT client"""
    client = mqtt.Client(client_id="mqtt-kafka-bridge", clean_session=True)
    
    # Set callbacks
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    client.on_subscribe = on_subscribe
    
    return client

# ============================
# Main Loop
# ============================
def main():
    """Main application loop"""
    
    log.info("=" * 70)
    log.info("🌉 MQTT to Kafka Bridge - Demo Version (No TLS/SSL)")
    log.info("=" * 70)
    log.info(f"MQTT Broker: {MQTT_HOST}:{MQTT_PORT}")
    log.info(f"Kafka Broker: {KAFKA_BROKER}")
    log.info(f"Topics: {', '.join(MQTT_TOPICS)}")
    log.info("=" * 70 + "\n")
    
    # Initialize Kafka producer
    if not init_kafka_producer():
        log.error("Failed to initialize Kafka producer")
        return 1
    
    # Initialize MQTT client
    mqtt_client = init_mqtt_client()
    
    # Connect to MQTT broker
    retry_count = 0
    max_retries = 10
    
    while retry_count < max_retries:
        try:
            log.info(f"🔌 Connecting to MQTT broker: {MQTT_HOST}:{MQTT_PORT}")
            mqtt_client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
            mqtt_client.loop_start()
            log.info("✅ MQTT client started")
            break
        except Exception as e:
            retry_count += 1
            log.warning(f"⚠️  MQTT connection failed (attempt {retry_count}/{max_retries}): {e}")
            if retry_count < max_retries:
                time.sleep(5)
            else:
                log.error("❌ Failed to connect to MQTT broker after max retries")
                return 1
    
    # Keep running
    try:
        log.info("🟢 Bridge is running... Press Ctrl+C to stop\n")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("\n⏹️  Shutting down bridge...")
    finally:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        if kafka_producer:
            kafka_producer.close()
        log.info("✅ Bridge stopped cleanly")
        log.info(f"Total messages forwarded: {message_count}")
    
    return 0

if __name__ == "__main__":
    exit(main())