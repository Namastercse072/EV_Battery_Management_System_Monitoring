#!/bin/bash
set -e

echo "Starting Kafka broker..."

# Ensure data directory exists
mkdir -p /var/lib/kafka/data

# Generate or use provided cluster ID
CLUSTER_ID_FILE="/var/lib/kafka/cluster.id"
if [ ! -f "$CLUSTER_ID_FILE" ]; then
  echo "Generating new Kafka Cluster ID..."
  KAFKA_CLUSTER_ID=$(kafka-storage.sh random-uuid)
  echo "$KAFKA_CLUSTER_ID" > "$CLUSTER_ID_FILE"
  echo "✓ Generated Kafka Cluster ID: $KAFKA_CLUSTER_ID"
else
  KAFKA_CLUSTER_ID=$(cat "$CLUSTER_ID_FILE")
  echo "✓ Using existing Kafka Cluster ID: $KAFKA_CLUSTER_ID"
fi

# Format storage only if not already formatted
METADATA_LOG="/var/lib/kafka/data/__cluster_metadata-0/00000000000000000000.log"
if [ ! -f "$METADATA_LOG" ]; then
  echo "Formatting Kafka storage with Cluster ID: $KAFKA_CLUSTER_ID"
  kafka-storage.sh format \
    --config /opt/kafka/config/kraft/server.properties \
    --cluster-id "$KAFKA_CLUSTER_ID" \
    --ignore-formatted

  if [ $? -ne 0 ]; then
    echo "❌ Kafka storage formatting failed!"
    exit 1
  fi
  echo "✓ Kafka storage formatted successfully"
else
  echo "✓ Kafka storage already formatted, skipping format step"
fi

echo "✓ Starting Kafka broker..."
echo "Kafka will listen on: 0.0.0.0:9092 (advertised: kafka:9092)"
echo "Controller will listen on: 0.0.0.0:9093"

# Start Kafka server
exec kafka-server-start.sh /opt/kafka/config/kraft/server.properties
