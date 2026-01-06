#!/bin/bash
# Quick Commands for EV Battery Management System

# ============================================================================
# STARTUP COMMANDS
# ============================================================================

# Start entire system (easiest)
echo "=== STARTUP ==="
echo "cd docker_deploy/Cloud && chmod +x startup.sh && ./startup.sh"

# Start with docker-compose only
echo "docker-compose up -d && sleep 60"

# Start data generator
echo "python3 spark-apps/kafka_data_generator.py &"

# ============================================================================
# MONITORING COMMANDS
# ============================================================================

echo ""
echo "=== MONITORING ==="

# View application logs
echo "docker-compose logs -f spark-app"

# View specific service logs
echo "docker-compose logs -f kafka"
echo "docker-compose logs -f spark-master"
echo "docker-compose logs -f spark-worker-1"

# Check container status
echo "docker-compose ps"

# ============================================================================
# VERIFICATION COMMANDS
# ============================================================================

echo ""
echo "=== VERIFICATION ==="

# Check Spark Cluster
echo "curl http://localhost:8888  # Spark Master UI - should show 2 workers ALIVE"

# List Kafka topics
echo "docker exec kafka kafka-topics.sh --bootstrap-server localhost:9092 --list"

# Create topics if missing
echo "docker exec kafka kafka-topics.sh --bootstrap-server localhost:9092 --create --topic ev_raw --partitions 4 --replication-factor 1 --if-not-exists"
echo "docker exec kafka kafka-topics.sh --bootstrap-server localhost:9092 --create --topic ev_processed --partitions 4 --replication-factor 1 --if-not-exists"
echo "docker exec kafka kafka-topics.sh --bootstrap-server localhost:9092 --create --topic ev_alerts --partitions 4 --replication-factor 1 --if-not-exists"

# ============================================================================
# DATA MONITORING COMMANDS
# ============================================================================

echo ""
echo "=== DATA MONITORING ==="

# Check raw input data
echo "docker exec kafka kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic ev_raw --max-messages 1"

# Check processed data
echo "docker exec kafka kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic ev_processed --max-messages 1"

# Check alerts
echo "docker exec kafka kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic ev_alerts --max-messages 1"

# ============================================================================
# TROUBLESHOOTING COMMANDS
# ============================================================================

echo ""
echo "=== TROUBLESHOOTING ==="

# Check if workers are registered
echo "docker exec spark-master curl -s localhost:8080/api/v1/workers | jq '.'"

# Check if Kafka is running
echo "docker exec kafka kafka-broker-api-versions.sh --bootstrap-server localhost:9092"

# Check network connectivity
echo "docker exec spark-app bash -c 'nc -zv kafka 9092'"
echo "docker exec spark-app bash -c 'nc -zv spark-master 7077'"

# Check data generator status
echo "ps aux | grep kafka_data_generator.py"

# Restart specific services
echo "docker-compose restart spark-worker-1"
echo "docker-compose restart spark-worker-2"
echo "docker-compose restart kafka"

# ============================================================================
# CLEANUP COMMANDS
# ============================================================================

echo ""
echo "=== CLEANUP ==="

# Stop everything
echo "docker-compose down"

# Stop and remove volumes
echo "docker-compose down -v"

# Kill data generator
echo "kill $(pgrep -f kafka_data_generator.py)"

# ============================================================================
# WEB UI URLS
# ============================================================================

echo ""
echo "=== WEB UI URLs ==="
echo "Spark Master: http://localhost:8888"
echo "Spark Worker 1: http://localhost:8881"
echo "Spark Worker 2: http://localhost:8882"
echo "Kafka Broker: localhost:9092"

# ============================================================================
# SYSTEM STATUS CHECK
# ============================================================================

echo ""
echo "=== QUICK STATUS CHECK ==="

echo "#!/bin/bash"
echo "echo 'Spark Cluster:'"
echo "curl -s http://localhost:8888 | grep -o 'Alive Workers: [0-9]*' || echo 'Not responding'"
echo ""
echo "echo 'Kafka Topics:'"
echo "docker exec kafka kafka-topics.sh --bootstrap-server localhost:9092 --list 2>/dev/null || echo 'Not responding'"
echo ""
echo "echo 'Container Status:'"
echo "docker-compose ps --format table"
echo ""
echo "echo 'Message Count:'"
echo "docker exec kafka kafka-run-class.sh kafka.tools.JmxTool --object-name 'kafka.server:type=BrokerTopicMetrics,name=MessagesInPerSec' --attributes 'Count' 2>/dev/null || echo 'Cannot retrieve'"
