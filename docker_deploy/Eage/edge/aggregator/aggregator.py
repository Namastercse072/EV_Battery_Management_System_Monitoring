#!/usr/bin/env python3
"""
Alert Aggregator Service
Consolidates alerts from multiple edge nodes and forwards to cloud
"""
import paho.mqtt.client as mqtt
import json
import etcd
import logging
from datetime import datetime
import os

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
MQTT_HOST = os.getenv("MQTT_HOST", "mqtt-broker-central")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
INPUT_TOPICS = os.getenv("MQTT_INPUT_TOPICS", "ev/alerts/node1,ev/alerts/node2").split(",")
OUTPUT_TOPIC = os.getenv("MQTT_OUTPUT_TOPIC", "ev/alerts/aggregated")
ETCD_HOST = os.getenv("ETCD_HOST", "etcd")
ETCD_PORT = int(os.getenv("ETCD_PORT", 2379))

# MQTT Client
client = mqtt.Client(client_id="alert-aggregator")

# etcd Client
try:
    etcd_client = etcd.Client(host=ETCD_HOST, port=ETCD_PORT)
except Exception as e:
    logger.error(f"Failed to connect to etcd: {e}")
    etcd_client = None

def register_service():
    """Register aggregator service with etcd"""
    if etcd_client:
        try:
            etcd_client.write(
                "/services/alert-aggregator/status",
                json.dumps({
                    "status": "active",
                    "timestamp": datetime.now().isoformat(),
                    "mqtt_host": MQTT_HOST,
                    "mqtt_port": MQTT_PORT
                }),
                ttl=60
            )
            logger.info("Registered alert aggregator service with etcd")
        except Exception as e:
            logger.error(f"Failed to register with etcd: {e}")

def on_connect(client, userdata, flags, rc):
    logger.info(f"Alert Aggregator connected with code {rc}")
    if rc == 0:
        # Subscribe to all input topics
        for topic in INPUT_TOPICS:
            client.subscribe(topic)
            logger.info(f"Subscribed to {topic}")
        register_service()
    else:
        logger.error(f"Connection failed with code {rc}")

def on_disconnect(client, userdata, rc):
    if rc != 0:
        logger.warning(f"Unexpected disconnection: {rc}")

def on_message(client, userdata, msg):
    """Process alert from node and forward to aggregated topic"""
    try:
        # Check for empty payload
        if not msg.payload or len(msg.payload) == 0:
            logger.error(f"❌ Empty payload received from topic '{msg.topic}'")
            logger.debug(f"   Payload length: {len(msg.payload) if msg.payload else 0} bytes")
            return
        
        payload_str = msg.payload.decode('utf-8')
        
        # Check for empty string after decode
        if not payload_str or payload_str.strip() == '':
            logger.error(f"❌ Empty string after UTF-8 decode from topic '{msg.topic}'")
            logger.debug(f"   Raw payload (hex): {msg.payload[:50].hex() if msg.payload else 'empty'}")
            logger.debug(f"   Payload length: {len(msg.payload)} bytes")
            return
        
        payload = json.loads(payload_str)
        
        # Add node info and timestamp
        aggregated_alert = {
            "original_topic": msg.topic,
            "node_id": msg.topic.split("/")[-1],
            "alert": payload,
            "aggregated_at": datetime.now().isoformat(),
            "timestamp": payload.get("timestamp", datetime.now().isoformat())
        }
        
        # Publish to aggregated topic
        client.publish(OUTPUT_TOPIC, json.dumps(aggregated_alert), qos=1)
        logger.info(f"✅ Aggregated alert from {aggregated_alert['node_id']}")
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ Invalid JSON format: {e}")
        if msg.payload:
            logger.debug(f"   Raw payload (hex): {msg.payload[:50].hex()}")
            logger.debug(f"   Payload length: {len(msg.payload)} bytes")
            try:
                payload_str = msg.payload.decode('utf-8', errors='ignore')
                logger.debug(f"   Payload preview (first 100 chars): {payload_str[:100]!r}")
            except:
                pass
    except Exception as e:
        logger.error(f"❌ Error processing message: {e}", exc_info=True)
        logger.debug(f"   Topic: {msg.topic}")
        logger.debug(f"   Payload length: {len(msg.payload) if msg.payload else 0} bytes")

if __name__ == "__main__":
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    
    logger.info(f"Connecting to MQTT broker at {MQTT_HOST}:{MQTT_PORT}")
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    
    logger.info("Alert Aggregator started - listening for alerts")
    client.loop_forever()
