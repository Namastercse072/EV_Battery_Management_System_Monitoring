#!/bin/bash
# Complete Infrastructure Rebuild - Bridge, Kafka, Spark Job

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  EV Battery System - Complete Infrastructure Reset         ║"
echo "║  Fixing: Bridge → Kafka → Spark Job Connection Issues      ║"
echo "╚════════════════════════════════════════════════════════════╝"

cd "$(dirname "$0")"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Step 1: Stop all services
echo -e "\n${BLUE}[1/6] Stopping all services...${NC}"
docker-compose -f docker-compose-enhanced.yml down 2>/dev/null || true

echo -e "${GREEN}✓ Services stopped${NC}"

# Step 2: Remove Kafka volumes to reset cluster state
echo -e "\n${BLUE}[2/6] Cleaning Kafka cluster data (fresh start)...${NC}"
docker volume rm cloud_kafka-broker-1-data cloud_kafka-broker-2-data cloud_kafka-broker-3-data 2>/dev/null || true
docker volume rm cloud_postgres-primary-data cloud_postgres-replica-data 2>/dev/null || true

echo -e "${GREEN}✓ Kafka volumes cleaned${NC}"

# Step 3: Rebuild images
echo -e "\n${BLUE}[3/6] Rebuilding Docker images...${NC}"
docker-compose -f docker-compose-enhanced.yml build --no-cache kafka-broker-1 kafka-broker-2 kafka-broker-3 mqtt-kafka-bridge spark-master spark-job

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Build failed!${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Images built successfully${NC}"

# Step 4: Start Kafka cluster first
echo -e "\n${BLUE}[4/6] Starting Kafka cluster (3 brokers + KRaft)...${NC}"
docker-compose -f docker-compose-enhanced.yml up -d kafka-broker-1 kafka-broker-2 kafka-broker-3

echo -e "${YELLOW}⏳ Waiting for Kafka brokers to be healthy (60 seconds)...${NC}"
sleep 60

# Check broker health
for i in 1 2 3; do
  container="kafka-broker-$i"
  health=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "unknown")
  echo "   Broker $i health: $health"
done

echo -e "${GREEN}✓ Kafka cluster started${NC}"

# Step 5: Start Bridge
echo -e "\n${BLUE}[5/6] Starting MQTT-Kafka Bridge...${NC}"
docker-compose -f docker-compose-enhanced.yml up -d mqtt-kafka-bridge

sleep 10

echo -e "${GREEN}✓ Bridge started${NC}"

# Step 6: Start Spark
echo -e "\n${BLUE}[6/6] Starting Spark (Master + Job)...${NC}"
docker-compose -f docker-compose-enhanced.yml up -d spark-master spark-job

sleep 15

echo -e "\n${GREEN}✓ All services started${NC}"

# Status check
echo -e "\n╔════════════════════════════════════════════════════════════╗"
echo -e "║  Service Status                                             ║"
echo -e "╚════════════════════════════════════════════════════════════╝"

docker-compose -f docker-compose-enhanced.yml ps

echo -e "\n${BLUE}📝 Next Steps:${NC}"
echo "1. Verify Kafka brokers are HEALTHY:"
echo "   ${GREEN}docker-compose -f docker-compose-enhanced.yml ps kafka-broker-1${NC}"
echo ""
echo "2. Check bridge logs:"
echo "   ${GREEN}docker-compose -f docker-compose-enhanced.yml logs mqtt-kafka-bridge -f${NC}"
echo ""
echo "3. Check Spark logs:"
echo "   ${GREEN}docker-compose -f docker-compose-enhanced.yml logs spark-job -f${NC}"
echo ""
echo "4. Test Kafka topics:"
echo "   ${GREEN}docker-compose -f docker-compose-enhanced.yml exec kafka-broker-1 kafka-topics.sh --list --bootstrap-server localhost:9092${NC}"
echo ""
echo "5. Publish test message to MQTT:"
echo "   ${GREEN}mosquitto_pub -h localhost -p 1883 -t 'ev/metrics' -m '{\"test\": true}'${NC}"
