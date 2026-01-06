#!/bin/bash
# Comprehensive Connectivity Diagnostics

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  Bridge → Kafka → Spark Connectivity Diagnostics           ║"
echo "╚════════════════════════════════════════════════════════════╝"

cd "$(dirname "$0")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "\n${BLUE}[1/5] Container Status${NC}"
echo "═════════════════════════════════════════════"
docker-compose -f docker-compose-enhanced.yml ps --format "table {{.Names}}\t{{.Status}}" 2>/dev/null | grep -E "kafka|bridge|spark"

echo -e "\n${BLUE}[2/5] Kafka Broker Health${NC}"
echo "═════════════════════════════════════════════"
for i in 1 2 3; do
  container="kafka-broker-$i"
  health=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "unknown")
  running=$(docker inspect --format='{{.State.Running}}' "$container" 2>/dev/null || echo "false")
  
  if [ "$health" = "healthy" ]; then
    echo -e "${GREEN}✓${NC} $container: $health (running: $running)"
  elif [ "$health" = "unhealthy" ]; then
    echo -e "${RED}✗${NC} $container: $health"
  else
    echo -e "${YELLOW}⚠${NC} $container: $health"
  fi
done

echo -e "\n${BLUE}[3/5] Kafka Broker Logs (Last 20 lines each)${NC}"
echo "═════════════════════════════════════════════"
for i in 1 2 3; do
  echo -e "\n${YELLOW}kafka-broker-$i:${NC}"
  docker-compose -f docker-compose-enhanced.yml logs kafka-broker-$i --tail 20 2>/dev/null | tail -10
done

echo -e "\n${BLUE}[4/5] Bridge Connectivity Tests${NC}"
echo "═════════════════════════════════════════════"

echo -e "\n${YELLOW}Bridge Container Status:${NC}"
docker-compose -f docker-compose-enhanced.yml ps mqtt-kafka-bridge 2>/dev/null

echo -e "\n${YELLOW}Bridge Logs (Last 30 lines):${NC}"
docker-compose -f docker-compose-enhanced.yml logs mqtt-kafka-bridge --tail 30 2>/dev/null

echo -e "\n${YELLOW}Test: Bridge → Kafka Connection${NC}"
docker-compose -f docker-compose-enhanced.yml exec -T mqtt-kafka-bridge python3 << 'EOF' 2>/dev/null
import socket
import sys

brokers = [
    ("kafka-broker-1", 29092),
    ("kafka-broker-2", 29092),
    ("kafka-broker-3", 29092)
]

for host, port in brokers:
    try:
        sock = socket.create_connection((host, port), timeout=5)
        sock.close()
        print(f"✓ {host}:{port} - Connection OK")
    except Exception as e:
        print(f"✗ {host}:{port} - {e}")
EOF

echo -e "\n${BLUE}[5/5] Spark Job Status${NC}"
echo "═════════════════════════════════════════════"

echo -e "\n${YELLOW}Spark Master:${NC}"
docker-compose -f docker-compose-enhanced.yml ps spark-master 2>/dev/null

echo -e "\n${YELLOW}Spark Job Container:${NC}"
docker-compose -f docker-compose-enhanced.yml ps spark-job 2>/dev/null

echo -e "\n${YELLOW}Spark Job Logs (Last 50 lines):${NC}"
docker-compose -f docker-compose-enhanced.yml logs spark-job --tail 50 2>/dev/null

echo -e "\n${BLUE}══════════════════════════════════════════════${NC}"
echo -e "\n${GREEN}Diagnostic Summary:${NC}"
echo "1. All Kafka brokers should show 'healthy' status"
echo "2. Bridge should be running and connected to Kafka"
echo "3. Spark job should be connected to Kafka and consuming messages"
echo ""
echo -e "${YELLOW}If issues persist:${NC}"
echo "  • Rebuild infrastructure: ./rebuild_infrastructure.sh"
echo "  • Check logs: docker-compose logs -f <service>"
echo "  • Verify network: docker network inspect cloud_cloud_net"
