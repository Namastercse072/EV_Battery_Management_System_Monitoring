#!/bin/bash
# Complete EV Battery Management System Startup Script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "════════════════════════════════════════════════════════════════"
echo "  EV Battery Management System - Cluster Startup"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

# Step 1: Clean up old containers and volumes (optional)
log_info "Checking for existing containers..."
if docker ps -a | grep -q "spark-master"; then
    log_warning "Found existing Spark containers"
    read -p "  Clean up old containers? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "Stopping and removing old containers..."
        docker-compose down -v
        sleep 2
        log_success "Old containers removed"
    fi
fi

# Step 2: Start Docker Compose services
log_info "Starting Docker services..."
docker-compose up -d

echo ""
log_success "Docker services started"
echo ""

# Step 3: Wait for critical services
log_info "Waiting for services to be healthy..."

wait_for_service() {
    local service=$1
    local port=$2
    local max_attempts=30
    local attempt=0
    
    echo -n "  Waiting for $service..."
    while [ $attempt -lt $max_attempts ]; do
        if docker exec $service nc -z localhost $port 2>/dev/null || \
           curl -s -o /dev/null -w "%{http_code}" http://localhost:$port 2>/dev/null | grep -q "200\|302"; then
            echo -e " ${GREEN}✓${NC}"
            return 0
        fi
        echo -n "."
        sleep 2
        ((attempt++))
    done
    echo -e " ${RED}✗${NC}"
    return 1
}

wait_for_service "kafka" "9092"
wait_for_service "spark-master" "8080"
wait_for_service "spark-worker-1" "8081"
wait_for_service "spark-worker-2" "8082"

echo ""

# Step 4: Display service status
log_info "Checking cluster status..."
echo ""

# Kafka status
if docker exec kafka kafka-broker-api-versions.sh --bootstrap-server localhost:9092 &>/dev/null; then
    log_success "Kafka is ready"
else
    log_error "Kafka is not responding"
fi

# Spark Master
if curl -s http://localhost:8888 &>/dev/null; then
    log_success "Spark Master (http://localhost:8888)"
else
    log_error "Spark Master is not responding"
fi

# Spark Worker 1
if curl -s http://localhost:8881 &>/dev/null; then
    log_success "Spark Worker 1 (http://localhost:8881)"
else
    log_error "Spark Worker 1 is not responding"
fi

# Spark Worker 2
if curl -s http://localhost:8882 &>/dev/null; then
    log_success "Spark Worker 2 (http://localhost:8882)"
else
    log_error "Spark Worker 2 is not responding"
fi

echo ""

# Step 5: Create Kafka topics
log_info "Ensuring Kafka topics exist..."

create_topic() {
    local topic=$1
    local partitions=$2
    local replication=$3
    
    if docker exec kafka kafka-topics.sh \
        --bootstrap-server localhost:9092 \
        --list | grep -q "^${topic}$"; then
        log_success "Topic '$topic' exists"
    else
        log_info "Creating topic '$topic'..."
        docker exec kafka kafka-topics.sh \
            --bootstrap-server localhost:9092 \
            --create \
            --topic "$topic" \
            --partitions "$partitions" \
            --replication-factor "$replication" \
            --if-not-exists
        log_success "Topic '$topic' created"
    fi
}

create_topic "ev_raw" 4 1
create_topic "ev_processed" 4 1
create_topic "ev_alerts" 4 1

echo ""

# Step 6: Start data generator
log_info "Starting Kafka data generator..."
echo ""

# Check if kafka_data_generator.py exists
if [ -f "spark-apps/kafka_data_generator.py" ]; then
    # Install kafka-python if not already installed
    if ! python3 -c "import kafka" 2>/dev/null; then
        log_warning "Installing kafka-python..."
        pip install -q kafka-python
    fi
    
    # Run generator in background
    nohup python3 spark-apps/kafka_data_generator.py > /tmp/kafka_generator.log 2>&1 &
    GEN_PID=$!
    log_success "Data generator started (PID: $GEN_PID)"
    echo "  Logs: /tmp/kafka_generator.log"
else
    log_warning "kafka_data_generator.py not found, skipping..."
fi

echo ""

# Step 7: Display web UI URLs
log_info "System is ready! Access the following:"
echo ""
echo "  📊 Spark Master UI:"
echo "     http://localhost:8888"
echo ""
echo "  🔧 Spark Worker 1:"
echo "     http://localhost:8881"
echo ""
echo "  🔧 Spark Worker 2:"
echo "     http://localhost:8882"
echo ""
echo "  📉 Kafka UI (if installed):"
echo "     http://localhost:8080"
echo ""
echo "  📋 View logs:"
echo "     docker-compose logs -f spark-app"
echo "     docker-compose logs -f kafka"
echo ""

echo "════════════════════════════════════════════════════════════════"
echo "  🚀 System startup complete!"
echo "════════════════════════════════════════════════════════════════"
echo ""

log_info "Monitoring Spark application logs..."
sleep 3
docker-compose logs -f spark-app
