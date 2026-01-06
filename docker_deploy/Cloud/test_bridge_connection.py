#!/usr/bin/env python3
"""
Test MQTT to Kafka Bridge Connection
Diagnostic script to verify connectivity
"""

import socket
import json
import time
from kafka import KafkaProducer, KafkaAdminClient, NewTopic
from kafka.admin import ConfigResource, ConfigResourceType
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# Test configuration
KAFKA_BROKERS = [
    "kafka-broker-1:29092",
    "kafka-broker-2:29092",
    "kafka-broker-3:29092"
]
MQTT_HOST = "mqtt-broker"
MQTT_PORT = 1883

print("=" * 60)
print("🧪 MQTT-Kafka Bridge Connectivity Test")
print("=" * 60)

# ============================
# 1. Test Kafka Broker Connectivity
# ============================
print("\n1️⃣  Testing Kafka Broker Connectivity...")
for broker in KAFKA_BROKERS:
    host, port = broker.split(":")
    try:
        sock = socket.create_connection((host, int(port)), timeout=5)
        sock.close()
        print(f"   ✅ {broker} - Connection successful")
    except Exception as e:
        print(f"   ❌ {broker} - Connection failed: {e}")

# ============================
# 2. Test Kafka Producer
# ============================
print("\n2️⃣  Testing Kafka Producer...")
try:
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BROKERS,
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        acks='all',
        request_timeout_ms=10000
    )
    print("   ✅ Kafka Producer initialized successfully")
    
    # Send test message
    test_msg = {
        "test": True,
        "timestamp": time.time(),
        "message": "Bridge test message"
    }
    future = producer.send('test-topic', value=test_msg)
    record_metadata = future.get(timeout=10)
    print(f"   ✅ Test message sent to topic: {record_metadata.topic}")
    print(f"      Partition: {record_metadata.partition}")
    print(f"      Offset: {record_metadata.offset}")
    producer.close()
except Exception as e:
    print(f"   ❌ Kafka Producer failed: {e}")

# ============================
# 3. Test Kafka Admin Client
# ============================
print("\n3️⃣  Testing Kafka Admin Client...")
try:
    admin_client = KafkaAdminClient(
        bootstrap_servers=KAFKA_BROKERS,
        request_timeout_ms=10000
    )
    
    # Get cluster metadata
    cluster_metadata = admin_client.describe_cluster()
    print(f"   ✅ Connected to cluster")
    print(f"      Cluster ID: {cluster_metadata[0]}")
    print(f"      Brokers: {len(cluster_metadata[1])} active")
    
    # List topics
    topics = admin_client.list_topics()
    print(f"   ✅ Available topics: {len(topics)}")
    for topic in list(topics.keys())[:5]:
        print(f"      - {topic}")
    
    admin_client.close()
except Exception as e:
    print(f"   ❌ Kafka Admin Client failed: {e}")

# ============================
# 4. Test MQTT Connectivity
# ============================
print("\n4️⃣  Testing MQTT Broker Connectivity...")
try:
    sock = socket.create_connection((MQTT_HOST, MQTT_PORT), timeout=5)
    sock.close()
    print(f"   ✅ MQTT broker {MQTT_HOST}:{MQTT_PORT} - Connection successful")
except Exception as e:
    print(f"   ❌ MQTT broker {MQTT_HOST}:{MQTT_PORT} - Connection failed: {e}")

print("\n" + "=" * 60)
print("✅ Diagnostic test completed")
print("=" * 60)
