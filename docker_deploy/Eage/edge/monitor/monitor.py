#!/usr/bin/env python3
"""
Node Health Monitor Service
Monitors node health and registers nodes with etcd service discovery
"""
import os
import etcd
import json
import paho.mqtt.client as mqtt
import logging
from datetime import datetime
import time
import socket

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
ETCD_HOST = os.getenv("ETCD_HOST", "etcd")
ETCD_PORT = int(os.getenv("ETCD_PORT", 2379))
MQTT_HOST = os.getenv("MQTT_HOST", "mqtt-broker-central")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 5))
NODES = ["node1", "node2"]  # Add more nodes as needed

# etcd Client
try:
    etcd_client = etcd.Client(host=ETCD_HOST, port=ETCD_PORT)
    logger.info(f"Connected to etcd at {ETCD_HOST}:{ETCD_PORT}")
except Exception as e:
    logger.error(f"Failed to connect to etcd: {e}")
    etcd_client = None

# MQTT Client
mqtt_client = mqtt.Client(client_id="node-monitor")

def on_mqtt_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info(f"✅ MQTT connected successfully")
        register_all_nodes()
    else:
        logger.error(f"❌ MQTT connection failed with code {rc}")

def on_mqtt_disconnect(client, userdata, rc):
    if rc != 0:
        logger.warning(f"⚠️  Unexpected MQTT disconnection (code: {rc})")

def check_node_health(node_id):
    """Check if a node is healthy"""
    try:
        # Try to resolve DNS or check service
        # This is a basic check - extend as needed
        return True
    except Exception as e:
        logger.error(f"Health check failed for {node_id}: {e}")
        return False

def register_all_nodes():
    """Register all nodes in the cluster with etcd"""
    if not etcd_client:
        logger.warning("⚠️  etcd client not available")
        return
    
    for node_id in NODES:
        try:
            node_info = {
                "node_id": node_id,
                "status": "active",
                "registered_at": datetime.now().isoformat(),
                "hostname": socket.gethostname(),
                "mqtt_host": MQTT_HOST,
                "mqtt_port": MQTT_PORT,
                "services": [
                    f"sensor-simulator-{node_id}",
                    f"ml-inference-{node_id}"
                ]
            }
            
            # Write node info to etcd with TTL
            etcd_client.write(
                f"/nodes/{node_id}/info",
                json.dumps(node_info),
                ttl=60
            )
            
            logger.info(f"✅ Registered node {node_id} with etcd")
            
            # Publish to MQTT - ensure payload is not empty
            payload = json.dumps(node_info)
            if payload and len(payload) > 0:
                result = mqtt_client.publish(
                    f"cluster/nodes/{node_id}/status",
                    payload,
                    qos=1
                )
                if result.rc != mqtt.MQTT_ERR_SUCCESS:
                    logger.error(f"❌ Failed to publish node {node_id} status: {result.rc}")
            else:
                logger.error(f"❌ Empty payload for node {node_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to register node {node_id}: {e}")

def monitor_cluster():
    """Continuously monitor and update cluster state"""
    logger.info("🟢 Starting cluster health monitor")
    
    while True:
        try:
            for node_id in NODES:
                is_healthy = check_node_health(node_id)
                
                if is_healthy:
                    register_all_nodes()
                    logger.info(f"✅ Health check passed for node {node_id}")
                else:
                    logger.warning(f"⚠️  Node {node_id} health check failed")
                    
                    # Update node status in etcd
                    if etcd_client:
                        try:
                            etcd_client.write(
                                f"/nodes/{node_id}/status",
                                "unhealthy",
                                ttl=60
                            )
                        except Exception as e:
                            logger.error(f"❌ Failed to update status for {node_id}: {e}")
            
            time.sleep(CHECK_INTERVAL)
            
        except Exception as e:
            logger.error(f"❌ Monitor error: {e}", exc_info=True)
            time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    # Connect to MQTT
    mqtt_client.on_connect = on_mqtt_connect
    mqtt_client.on_disconnect = on_mqtt_disconnect
    
    logger.info(f"🔌 Connecting to MQTT at {MQTT_HOST}:{MQTT_PORT}")
    
    try:
        mqtt_client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
        mqtt_client.loop_start()
        
        # Start monitoring
        try:
            monitor_cluster()
        except KeyboardInterrupt:
            logger.info("⏹️  Shutting down monitor")
        except Exception as e:
            logger.error(f"❌ Fatal error in monitor: {e}", exc_info=True)
        finally:
            mqtt_client.loop_stop()
    except Exception as e:
        logger.error(f"❌ Failed to connect to MQTT: {e}", exc_info=True)
