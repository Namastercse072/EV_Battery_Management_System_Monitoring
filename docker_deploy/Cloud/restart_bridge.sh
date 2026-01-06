#!/bin/bash
# Quick restart script for MQTT-Kafka Bridge

echo "🔄 Restarting MQTT-Kafka Bridge..."

cd "$(dirname "$0")"

# Stop the bridge
echo "⏹️  Stopping bridge container..."
docker-compose -f docker-compose-enhanced.yml stop mqtt-kafka-bridge

# Remove the container to force rebuild
echo "🗑️  Removing bridge container..."
docker-compose -f docker-compose-enhanced.yml rm -f mqtt-kafka-bridge

# Rebuild the image
echo "🔨 Building bridge image..."
docker-compose -f docker-compose-enhanced.yml build mqtt-kafka-bridge

# Start the bridge
echo "🚀 Starting bridge container..."
docker-compose -f docker-compose-enhanced.yml up -d mqtt-kafka-bridge

# Show status
echo "📊 Checking bridge status..."
sleep 3
docker-compose -f docker-compose-enhanced.yml ps mqtt-kafka-bridge

echo ""
echo "📝 View logs with:"
echo "   docker-compose -f docker-compose-enhanced.yml logs mqtt-kafka-bridge -f"
