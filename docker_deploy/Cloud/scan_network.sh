#!/bin/bash

echo "================================"
echo "🔍 Docker Network Diagnostic"
echo "================================"

# Get network info
echo -e "\n📊 Network: cloud_default"
docker network inspect cloud_default --format='Gateway: {{index .IPAM.Config 0 "Gateway"}}'
docker network inspect cloud_default --format='Subnet: {{index .IPAM.Config 0 "Subnet"}}'

echo -e "\n🐳 Connected Containers:"
docker network inspect cloud_default --format='{{json .Containers}}' | python3 << 'EOF'
import json
import sys
data = json.load(sys.stdin)
for name, info in data.items():
    print(f"  - {info['Name']}: {info['IPv4Address']}")
EOF

echo -e "\n🔗 Container Connectivity Tests:"
containers=("kafka" "postgres" "redis" "nifi" "superset" "spark-master" "mqtt-kafka-bridge")

for container in "${containers[@]}"; do
    if docker ps --filter "name=$container" --format='{{.Names}}' | grep -q "$container"; then
        echo -e "\n  Testing $container:"
        
        # Ping other containers
        docker exec "$container" ping -c 1 postgres &>/dev/null && echo "    ✅ → postgres" || echo "    ❌ → postgres"
        docker exec "$container" ping -c 1 kafka &>/dev/null && echo "    ✅ → kafka" || echo "    ❌ → kafka"
        docker exec "$container" ping -c 1 redis &>/dev/null && echo "    ✅ → redis" || echo "    ❌ → redis"
    fi
done

echo -e "\n📡 Port Availability:"
docker exec kafka nc -zv localhost 9092 2>&1 | grep -q "succeeded" && echo "  ✅ Kafka (9092)" || echo "  ❌ Kafka (9092)"
docker exec postgres pg_isready -h localhost -p 5432 2>&1 | grep -q "accepting" && echo "  ✅ PostgreSQL (5432)" || echo "  ❌ PostgreSQL (5432)"
docker exec redis redis-cli ping 2>&1 | grep -q "PONG" && echo "  ✅ Redis (6379)" || echo "  ❌ Redis (6379)"

echo -e "\n================================\n"