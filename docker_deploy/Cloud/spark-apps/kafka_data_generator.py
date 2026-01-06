#!/usr/bin/env python3
"""
Kafka Data Generator for EV Battery Management System
Generates realistic battery telemetry data and sends to Kafka
"""

import json
import time
import random
from datetime import datetime
from kafka import KafkaProducer
import sys

def generate_battery_data():
    """Generate realistic EV battery telemetry data"""
    return {
        "voltage": round(random.uniform(3.0, 4.2), 2),
        "temperature": round(random.uniform(15, 45), 1),
        "current": round(random.uniform(10, 100), 2),
        "soc": random.randint(20, 100),  # State of Charge
        "soh": random.randint(70, 100),  # State of Health
        "timestamp": datetime.now().isoformat()
    }

def main():
    kafka_broker = "kafka:9092"
    topic = "ev_raw"
    batch_size = 10
    interval = 2  # seconds
    
    print(f"🔌 Kafka Data Generator")
    print(f"  Broker: {kafka_broker}")
    print(f"  Topic: {topic}")
    print(f"  Batch size: {batch_size}")
    print(f"  Interval: {interval}s\n")
    
    # Retry logic for Kafka connection
    max_retries = 10
    retry_count = 0
    producer = None
    
    while retry_count < max_retries and producer is None:
        try:
            print(f"📡 Connecting to Kafka broker ({retry_count + 1}/{max_retries})...")
            producer = KafkaProducer(
                bootstrap_servers=kafka_broker,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                acks='all',
                retries=3,
                request_timeout_ms=10000,
                connections_max_idle_ms=30000
            )
            print("✓ Connected to Kafka successfully\n")
        except Exception as e:
            retry_count += 1
            print(f"✗ Connection failed: {e}")
            if retry_count < max_retries:
                print(f"  Retrying in {interval}s...")
                time.sleep(interval)
            else:
                print("✗ Max retries exceeded. Exiting.")
                sys.exit(1)
    
    message_count = 0
    batch_count = 0
    
    try:
        print("📤 Generating and sending battery data...\n")
        while True:
            batch_count += 1
            batch_data = []
            
            # Generate batch
            for i in range(batch_size):
                data = generate_battery_data()
                batch_data.append(data)
                message_count += 1
            
            # Send batch to Kafka
            try:
                for data in batch_data:
                    future = producer.send(topic, value=data)
                    # Wait for confirmation
                    record_metadata = future.get(timeout=10)
                    
                print(f"✓ Batch {batch_count}: Sent {batch_size} messages ({message_count} total)")
                print(f"  Sample: V={batch_data[0]['voltage']}V, "
                      f"T={batch_data[0]['temperature']}°C, "
                      f"SOC={batch_data[0]['soc']}%, "
                      f"SOH={batch_data[0]['soh']}%")
                
            except Exception as e:
                print(f"✗ Error sending batch {batch_count}: {e}")
                # Try to reconnect
                try:
                    producer.close()
                    producer = KafkaProducer(
                        bootstrap_servers=kafka_broker,
                        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                        acks='all',
                        retries=3
                    )
                    print("✓ Reconnected to Kafka")
                except Exception as reconnect_error:
                    print(f"✗ Reconnection failed: {reconnect_error}")
                    sys.exit(1)
            
            # Wait before next batch
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Stopping data generator...")
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if producer:
            producer.flush()
            producer.close()
        print(f"✓ Generator stopped. Total messages sent: {message_count}")
        sys.exit(0)

if __name__ == "__main__":
    main()
