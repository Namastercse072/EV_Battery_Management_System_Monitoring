#!/bin/bash
set -e

echo "========================================"
echo "🚀 Starting Kafka Broker (KRaft Mode)"
echo "========================================"
echo "Node ID: ${KAFKA_NODE_ID}"
echo "Listeners: ${KAFKA_LISTENERS}"
echo "Advertised: ${KAFKA_ADVERTISED_LISTENERS}"
echo "Quorum Voters: ${KAFKA_CONTROLLER_QUORUM_VOTERS}"
echo "========================================"

# Ensure data directory exists
mkdir -p /var/lib/kafka/data

# Validate required environment variables
if [ -z "$KAFKA_NODE_ID" ]; then
  echo "❌ ERROR: KAFKA_NODE_ID is not set!"
  exit 1
fi

if [ -z "$KAFKA_CLUSTER_ID" ]; then
  echo "⚠️  KAFKA_CLUSTER_ID not set, generating..."
  export KAFKA_CLUSTER_ID=$(kafka-storage.sh random-uuid)
  echo "Generated Cluster ID: $KAFKA_CLUSTER_ID"
else
  echo "Using provided Cluster ID: $KAFKA_CLUSTER_ID"
fi

# Substitute environment variables in server.properties
echo "📝 Substituting environment variables in server.properties..."
envsubst < /opt/kafka/config/server.properties > /tmp/server.properties.tmp
mv /tmp/server.properties.tmp /opt/kafka/config/server.properties
echo "✅ Environment variables substituted"

# Display the generated config (first 30 lines for verification)
echo "Generated server.properties (first 30 lines):"
head -30 /opt/kafka/config/server.properties

# Format storage only if not already formatted
METADATA_LOG="/var/lib/kafka/data/__cluster_metadata-0/00000000000000000000.log"
if [ ! -f "$METADATA_LOG" ]; then
  echo ""
  echo "📝 Formatting Kafka storage..."
  kafka-storage.sh format \
    --config /opt/kafka/config/server.properties \
    --cluster-id "$KAFKA_CLUSTER_ID" \
    --ignore-formatted

  if [ $? -ne 0 ]; then
    echo "❌ Kafka storage formatting failed!"
    exit 1
  fi
  echo "✅ Kafka storage formatted successfully"
else
  echo "✅ Kafka storage already formatted (skipping format)"
fi

echo ""
echo "========================================"
echo "✅ Starting Kafka Server"
echo "========================================"

# Start Kafka server with the dynamically configured properties
exec kafka-server-start.sh /opt/kafka/config/server.properties
