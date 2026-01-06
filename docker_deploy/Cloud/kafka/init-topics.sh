#!/bin/bash
set -e

echo "⏳ Waiting for Kafka to be ready..."
sleep 10

BOOTSTRAP_SERVER="kafka-broker-1:29092"
TOPICS=("ev_raw" "ev_alerts" "ev_alerts_aggregated")

echo "📋 Creating Kafka topics..."

for TOPIC in "${TOPICS[@]}"; do
  echo "Creating topic: $TOPIC"
  kafka-topics.sh --create \
    --bootstrap-server "$BOOTSTRAP_SERVER" \
    --topic "$TOPIC" \
    --partitions 3 \
    --replication-factor 3 \
    --if-not-exists \
    --config min.insync.replicas=2

  if [ $? -eq 0 ]; then
    echo "✅ Topic '$TOPIC' created successfully"
  else
    echo "⚠️  Topic '$TOPIC' already exists or error occurred"
  fi
done

echo ""
echo "📊 Listing all topics:"
kafka-topics.sh --list --bootstrap-server "$BOOTSTRAP_SERVER"

echo ""
echo "✅ Topic initialization complete"
