#!/bin/bash
set -e

echo "Starting Kafka broker..."

# Clean up stale data (only on first run)
if [ ! -f /var/lib/kafka/data/__cluster_metadata-0/00000000000000000000.log ]; then
  echo "First run detected. Cleaning data directory..."
  rm -rf /var/lib/kafka/data/*
  mkdir -p /var/lib/kafka/data
fi

# Generate or use provided cluster ID
CLUSTER_ID_FILE="/var/lib/kafka/cluster.id"
if [ ! -f "$CLUSTER_ID_FILE" ]; then
  KAFKA_CLUSTER_ID=$(kafka-storage.sh random-uuid)
  echo "$KAFKA_CLUSTER_ID" > "$CLUSTER_ID_FILE"
  echo "Generated new Kafka Cluster ID: $KAFKA_CLUSTER_ID"
else
  KAFKA_CLUSTER_ID=$(cat "$CLUSTER_ID_FILE")
  echo "Using existing Kafka Cluster ID: $KAFKA_CLUSTER_ID"
fi

# Format storage if needed
if [ ! -f /var/lib/kafka/data/__cluster_metadata-0/00000000000000000000.log ]; then
  echo "Formatting Kafka storage..."
  kafka-storage.sh format \
    --config /opt/kafka/config/kraft/server.properties \
    --cluster-id "$KAFKA_CLUSTER_ID" \
    --ignore-formatted || true
fi

echo "Starting Kafka server..."
exec kafka-server-start.sh /opt/kafka/config/kraft/server.properties
