# EV Battery Management System - Cloud Deployment

> ⚠️ **DEMO VERSION** - See [`SECURITY.md`](SECURITY.md) before production

Complete containerized stack for real-time EV battery monitoring with edge-cloud integration.

## 📊 Architecture

```
┌──────────────────────────────────────────────────────┐
│              Edge-Cloud Infrastructure               │
├──────────────────────────────────────────────────────┤
│                                                      │
│  EDGE (docker_deploy/Eage)                          │
│  ├─ Sensor Simulator (MQTT)                         │
│  ├─ ML Inference                                    │
│  └─ Local Processing                                │
│           ↓ (MQTT Bridge)                           │
│  BRIDGE (mqtt-kafka-bridge)                         │
│           ↓                                          │
│  CLOUD (docker_deploy/Cloud)                        │
│  ├─ Kafka (Message Broker)                          │
│  ├─ NiFi (Data Orchestration)                       │
│  ├─ Spark (Stream Processing)                       │
│  ├─ PostgreSQL (Data Warehouse)                     │
│  ├─ Superset (Analytics & Dashboards)               │
│  └─ Redis (Caching)                                 │
│                                                      │
└──────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose 3.8+
- 16GB RAM (minimum)
- 50GB disk space
- Ubuntu 20.04+ or Windows 10+ with WSL2

### Installation

```bash
# 1. Navigate to Cloud deployment
cd docker_deploy/Cloud

# 2. Create environment file with secure credentials
cp .env.example .env
# Edit .env with strong passwords

# 3. Start all services
docker-compose up -d

# 4. Wait for services to be healthy
sleep 120
docker-compose ps

# 5. Access services
# Superset:    http://localhost:8088 (admin/admin by default)
# NiFi:        http://localhost:8080/nifi
# Kafka:       localhost:9092
# PostgreSQL:  localhost:5432
# Spark UI:    http://localhost:8888
# Redis:       localhost:6379
```

## 📁 Directory Structure

```
Cloud/
├── docker-compose.yml          # Main stack definition
├── .env                         # Credentials (⚠️ DO NOT COMMIT)
├── .gitignore                  # Version control exclusions
├── .dockerignore               # Docker build exclusions
├── README.md                   # This file
├── SECURITY.md                 # Security audit & risks
├── SECURITY_FIXES.md           # Security implementation
├── SERVICES.md                 # Service details
├── TLS_SETUP.md                # HTTPS/TLS configuration
│
├── kafka/
│   ├── Dockerfile              # Kafka build
│   ├── entrypoint.sh           # KRaft mode initialization
│   └── server.properties       # Broker configuration
│
├── nifi/
│   ├── Dockerfile              # NiFi build
│   ├── nifi-dataflow.xml       # Data flow template
│   └── init-flow.sh            # Flow initialization
│
├── postgres/
│   ├── 01-init-dbs.sql         # Database setup
│   ├── 02-init-tables.sh       # Table schema
│   └── postgresql.conf         # PostgreSQL config
│
├── superset/
│   ├── Dockerfile              # Superset build
│   ├── superset_config.py      # Configuration
│   └── entrypoint.sh           # Initialization
│
├── spark/
│   ├── Dockerfile              # Spark build
│   ├── conf/                   # Spark settings
│   └── apps/                   # PySpark jobs
│       ├── battery_processor.py
│       └── store_to_postgres.py
│
├── bridge/
│   ├── Dockerfile              # Bridge build
│   ├── mqtt_to_kafka.py        # MQTT → Kafka forwarder
│   └── requirements.txt        # Python dependencies
│
├── nginx/
│   ├── nginx.conf              # Reverse proxy config
│   └── .htpasswd               # Authentication
│
└── volumes/                    # (Auto-created)
    ├── postgres-data/
    ├── kafka-data/
    ├── redis-data/
    └── spark-data/
```

## 🔌 Data Flow

### Complete Pipeline

```
Eage (Edge Devices)
  └─ Sensor Data (MQTT)
      └─ ev/metrics topic
          └─ mqtt-kafka-bridge
              └─ Kafka ev_raw topic
                  └─ NiFi ConsumeKafka
                      ├─ LogAttribute (Debug)
                      ├─ JoltTransformJSON (Enrich)
                      ├─ EvaluateJsonPath (Extract)
                      └─ RouteOnAttribute (Anomaly Detection)
                          ├─ Normal Data → ev_processed
                          └─ Alerts → ev_alerts
                              └─ Spark Stream Processor
                                  └─ PostgreSQL (battery_metrics)
                                      └─ Superset Dashboard
```

### Message Format

**Input (ev_raw):**
```json
{
  "voltage": 3.8,
  "temperature": 35,
  "current": 50,
  "soc": 75,
  "soh": 95,
  "timestamp": "2025-11-18T02:30:00Z"
}
```

**Output (ev_processed):**
```json
{
  "voltage": 3.8,
  "temperature": 35,
  "current": 50,
  "soc": 75,
  "soh": 95,
  "timestamp": "2025-11-18T02:30:00Z",
  "processing_timestamp": "2025-11-18T02:30:01Z",
  "is_anomaly": false,
  "anomaly_type": "NORMAL",
  "severity": "INFO"
}
```

## 🔐 Security

### Demo Mode
- ⚠️ Default credentials (change before production)
- ⚠️ HTTP only (no HTTPS/TLS)
- ⚠️ No authentication on APIs
- ⚠️ All services accessible

### Production Requirements
- ✅ Use `.env` file with strong credentials
- ✅ Enable TLS 1.3 on all services
- ✅ Add reverse proxy with authentication
- ✅ Implement network segmentation
- ✅ Enable audit logging
- ✅ Regular security scanning

**See [`SECURITY.md`](SECURITY.md) & [`SECURITY_FIXES.md`](SECURITY_FIXES.md)**

## 📊 Service Configuration

| Service | Port | Type | Purpose |
|---------|------|------|---------|
| Kafka | 9092 | PLAINTEXT | Message broker |
| NiFi | 8080 | HTTP | Data orchestration |
| PostgreSQL | 5432 | TCP | Data warehouse |
| Superset | 8088 | HTTP | Analytics UI |
| Redis | 6379 | TCP | Caching |
| Spark Master | 7077 | TCP | Job submission |
| Spark UI | 8888 | HTTP | Monitoring |
| Nginx | 80/443 | HTTP/HTTPS | Reverse proxy |

**See [`SERVICES.md`](SERVICES.md) for details**

## 🎯 Common Operations

### Start Services
```bash
docker-compose up -d
docker-compose ps
```

### Stop Services
```bash
docker-compose down
```

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f mqtt-kafka-bridge
docker-compose logs -f nifi
docker-compose logs -f spark-master
```

### Access Shells
```bash
# PostgreSQL
docker exec -it postgres psql -U superset -d battery_metrics

# Kafka
docker exec -it kafka bash

# NiFi
docker exec -it nifi bash
```

### Create Kafka Topics
```bash
docker exec kafka kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --create --topic ev_raw \
  --partitions 1 --replication-factor 1 --if-not-exists
```

### Send Test Data
```bash
docker exec -i kafka kafka-console-producer.sh \
  --bootstrap-server localhost:9092 \
  --topic ev_raw \
  <<EOF
{"voltage": 3.8, "temperature": 35, "soc": 75, "soh": 95, "timestamp": "2025-11-18T02:30:00Z"}
{"voltage": 4.5, "temperature": 55, "soc": 15, "soh": 45, "timestamp": "2025-11-18T02:35:00Z"}
EOF
```

### Monitor Data Flow
```bash
# Kafka consumer
docker exec kafka kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic ev_processed \
  --from-beginning

# PostgreSQL
docker exec postgres psql -U superset -d battery_metrics -c "SELECT * FROM battery_metrics LIMIT 10;"

# Row count
docker exec postgres psql -U superset -d battery_metrics -c "SELECT COUNT(*) FROM battery_metrics;"
```

### Clean Rebuild
```bash
docker-compose down -v
docker volume prune -f
docker-compose build --no-cache
docker-compose up -d
```

## 🧪 Integration Testing

### Test 1: MQTT Bridge → Kafka
```bash
# Monitor bridge
docker-compose logs -f mqtt-kafka-bridge

# Send MQTT test (from Eage or external)
mosquitto_pub -h localhost -p 1883 -t ev/metrics -m \
  '{"voltage":3.8,"temperature":35,"soc":75,"soh":95,"timestamp":"2025-11-18T02:30:00Z"}'

# Verify in Kafka
docker exec kafka kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic ev_raw \
  --max-messages 1
```

### Test 2: NiFi Data Processing
```bash
# Check NiFi web UI
curl http://localhost:8080/nifi-api/system-diagnostics

# Verify processors running
curl http://localhost:8080/nifi-api/process-groups/root/status
```

### Test 3: Spark Processing
```bash
# Submit test job
docker exec spark-master spark-submit \
  --master spark://spark-master:7077 \
  /opt/spark-apps/battery_processor.py

# Monitor
docker-compose logs -f spark-master
```

### Test 4: PostgreSQL Storage
```bash
# Query data
docker exec postgres psql -U superset -d battery_metrics -c "SELECT COUNT(*) FROM battery_metrics;"

# Check tables
docker exec postgres psql -U superset -d battery_metrics -c "\dt"
```

### Test 5: Superset Dashboard
```bash
# Access UI
open http://localhost:8088

# Login: admin / admin
# Create new data source → PostgreSQL
# Connect: battery_metrics database
# Create dashboard with battery metrics
```

## 📈 Performance Tuning

### Increase Resources
```yaml
services:
  kafka:
    environment:
      - KAFKA_HEAP_OPTS=-Xmx2G -Xms2G
  
  spark-master:
    environment:
      - SPARK_WORKER_MEMORY=4G
      - SPARK_WORKER_CORES=4
```

### Database Optimization
```bash
# Run VACUUM
docker exec postgres psql -U superset -d battery_metrics -c "VACUUM ANALYZE;"

# Create indexes
docker exec postgres psql -U superset -d battery_metrics -c "CREATE INDEX idx_soc ON battery_metrics(soc);"
```

### Cache Configuration
```bash
# Redis memory policy
docker exec redis redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| Bridge not connecting | Check `MQTT_HOST` & `KAFKA_BROKER` in `.env` |
| NiFi processors failing | Verify Kafka broker is healthy |
| PostgreSQL init failed | Check init scripts exist: `postgres/01-init-dbs.sql` |
| Superset can't connect DB | Verify PostgreSQL is running & accessible |
| Spark jobs failing | Check logs: `docker-compose logs spark-master` |
| MQTT messages not arriving | Test bridge: `docker-compose logs mqtt-kafka-bridge` |
| Memory issues | Increase Docker memory limit |

## 🔄 Integration with Edge (Eage)

```bash
# Terminal 1: Start Cloud
cd docker_deploy/Cloud
docker-compose up -d
sleep 60

# Terminal 2: Start Edge (pointing to Cloud bridge)
cd docker_deploy/Eage
docker-compose -f docker-compose.yml -f docker-compose.cloud-link.yml up -d

# Terminal 3: Monitor data flow
docker-compose logs -f mqtt-kafka-bridge
```

## 📚 Documentation

- [`SECURITY.md`](SECURITY.md) — Security audit & risks
- [`SECURITY_FIXES.md`](SECURITY_FIXES.md) — Security implementation
- [`SERVICES.md`](SERVICES.md) — Service details & ports
- [`TLS_SETUP.md`](TLS_SETUP.md) — HTTPS/TLS configuration

## 🤝 Support

For issues:
1. Check logs: `docker-compose logs [service]`
2. Verify health: `docker-compose ps`
3. Test connectivity: `docker exec [service] nc -zv [host] [port]`
4. Review docs: See files above

## 📝 License

MSc Thesis - EV Battery Management System Monitoring

---

**Version:** 1.0 (Demo)  
**Last Updated:** December 5, 2025  
**Status:** ⚠️ NOT PRODUCTION READY