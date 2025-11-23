# EV Battery Management System - Docker Deployment

Complete containerized stack for real-time EV battery monitoring, data processing, and visualization.

## 📋 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    EV Battery Management Stack              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Kafka (9092)          NiFi (8080)         Spark (8888)   │
│  ├─ ev_raw             ├─ Consume Kafka   ├─ Processing   │
│  ├─ ev_processed       ├─ Transform       └─ Analytics    │
│  └─ ev_alerts          ├─ Route Anomalies                │
│                        └─ Publish Alerts                  │
│                                                             │
│  PostgreSQL (5432)     Redis (6379)       Superset (8088) │
│  ├─ superset_db        ├─ Caching        ├─ Dashboard    │
│  └─ battery_metrics    └─ Session Store  └─ Visualization│
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose 3.8+
- 8GB+ RAM
- 20GB+ Disk space
- Windows/Linux/Mac

### Installation

```bash
# 1. Clone repository
cd docker_deploy/Cloud

# 2. Create required directories
mkdir -p postgres nifi kafka superset spark

# 3. Create init files (if not exists)
# See below: Init Files Section

# 4. Start all services
docker-compose up -d

# 5. Wait for services to be healthy
docker-compose ps

# 6. Access services
# NiFi UI:      http://localhost:8080/nifi
# Superset UI:  http://localhost:8088 (admin/admin)
# Kafka:        localhost:9092
# PostgreSQL:   localhost:5432
# Spark:        localhost:8888
```

## 🔧 Service Configuration

### Kafka (Message Broker)
- **Port:** 9092 (PLAINTEXT), 9093 (CONTROLLER)
- **Topics:**
  - `ev_raw` — Raw battery sensor data
  - `ev_processed` — Processed metrics
  - `ev_alerts` — Anomaly alerts
- **Mode:** KRaft (no Zookeeper)

### NiFi (Data Flow Orchestrator)
- **Port:** 8080 (HTTP)
- **Features:**
  - Consumes from Kafka `ev_raw`
  - Transforms & enriches data (JoltTransformJSON)
  - Extracts fields (EvaluateJsonPath)
  - Routes anomalies (RouteOnAttribute)
  - Publishes to `ev_processed` & `ev_alerts`
- **Flow:** Saved in `conf/flow.xml.gz` (auto-persisted)

### PostgreSQL (Data Warehouse)
- **Port:** 5432
- **Databases:**
  - `superset_db` — Superset metadata
  - `battery_metrics` — Battery telemetry data
- **Tables:**
  - `battery_metrics` — Voltage, temperature, SOC, SOH readings
  - `battery_faults` — Detected anomalies
- **User:** superset / superset_pass

### Superset (Visualization)
- **Port:** 8088
- **Login:** admin / admin
- **Features:**
  - Real-time dashboards
  - SQL queries
  - Chart creation
  - Export reports
- ** Database:** Connects to `battery_metrics` in PostgreSQL handeling (troubleshooting below)
  - Caches sessions in Redis  
  - if it errors like no driver found, ensure PostgreSQL is reachable from Superset container (no module name psycopg2)
  - then check which python, and which pip inside the superset container, and install psycopg2-binary if missing
  - if no pip, install pip first:
    - run apt-get update && apt-get install -y python3-pip
  - run python -m pip install psycopg2-binary
  - then check import psycopg2 in python shell inside superset container
  - if successful, restart superset service
  - Now be ready to connect to the battery_metrics database

### Spark (Stream Processing)
- **Port:** 8888 (Master UI)
- **Port:** 7077 (Master), 8081 (Worker)
- **Features:**
  - Real-time analytics
  - Machine learning models
  - Batch processing

### Redis (Cache & Session Store)
- **Port:** 6379
- **Purpose:**
  - Superset session caching
  - Temporary data storage

## 📁 Directory Structure

```
Cloud/
├── docker-compose.yml          # Main compose file
├── .dockerignore               # Build context exclusions
├── README.md                   # This file
│
├── kafka/
│   ├── Dockerfile              # Kafka image build
│   ├── entrypoint.sh           # KRaft initialization
│   └── server.properties       # Kafka broker config
│
├── nifi/
│   ├── Dockerfile              # NiFi image build
│   ├── init-flow.sh            # Flow initialization
│   └── conf/                   # NiFi configuration (auto-created)
│       ├── flow.xml.gz         # Saved data flows
│       ├── nifi.properties     # NiFi settings
│       └── logback.xml         # Logging config
│
├── postgres/
│   ├── 01-init-dbs.sql         # Database creation
│   ├── 02-init-tables.sh       # Table schema
│   └── postgresql.conf         # PostgreSQL tuning (optional)
│
├── superset/
│   ├── Dockerfile              # Superset image build
│   └── entrypoint.sh           # Superset initialization
│
└── spark/
    ├── Dockerfile              # Spark image build
    ├── conf/                   # Spark configuration
    └── apps/                   # PySpark jobs
        └── battery_analysis.py
```

## 🔌 Init Files

### postgres/01-init-dbs.sql
```sql
CREATE DATABASE superset_db OWNER superset;
CREATE DATABASE battery_metrics OWNER superset;
GRANT ALL PRIVILEGES ON DATABASE superset_db TO superset;
GRANT ALL PRIVILEGES ON DATABASE battery_metrics TO superset;
```

### postgres/02-init-tables.sh
```bash
#!/bin/bash
psql -U superset -d battery_metrics <<EOF
CREATE TABLE battery_metrics (
  id SERIAL PRIMARY KEY,
  voltage DECIMAL(5,2),
  temperature DECIMAL(5,2),
  current DECIMAL(7,2),
  soc DECIMAL(5,2),
  soh DECIMAL(5,2),
  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE battery_faults (
  id SERIAL PRIMARY KEY,
  fault_type VARCHAR(50),
  severity VARCHAR(20),
  description TEXT,
  metric_id INTEGER REFERENCES battery_metrics(id),
  detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
EOF
```

## 📊 Data Flow

### 1. Data Ingestion (Kafka)
```
IoT Sensor → Kafka Topic (ev_raw)
{
  "voltage": 3.8,
  "temperature": 35,
  "soc": 75,
  "soh": 95,
  "timestamp": "2025-11-18T02:30:00Z"
}
```

### 2. Data Processing (NiFi)
```
ConsumeKafka → LogAttribute → JoltTransformJSON 
→ EvaluateJsonPath → RouteOnAttribute
```

### 3. Anomaly Detection
```
RouteOnAttribute:
  - voltage > 4.2V → ALERT
  - temperature > 50°C → ALERT
  - soc < 20% → ALERT
  - soh < 50% → ALERT
```

### 4. Storage & Visualization
```
Normal Data → PostgreSQL (battery_metrics)
           → Superset Dashboard
           
Alerts → Kafka (ev_alerts) → NiFi Logging
```

## 🎯 Common Tasks

### Start All Services
```bash
docker-compose up -d
docker-compose logs -f
```

### Stop All Services
```bash
docker-compose down
```

### Clean Volumes (WARNING: Deletes data)
```bash
docker-compose down -v
docker volume prune -f
```

### View Service Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f nifi
docker-compose logs -f kafka
docker-compose logs -f postgres
```

### Access Service Shells
```bash
# PostgreSQL
docker exec -it postgres psql -U superset -d battery_metrics

# Kafka
docker exec -it kafka bash

# NiFi
docker exec -it nifi bash
```

### Create Kafka Topic
```bash
docker exec kafka kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --create --topic ev_raw \
  --partitions 1 --replication-factor 1 --if-not-exists
```

### Publish Test Data to Kafka
```bash
docker exec -i kafka kafka-console-producer.sh \
  --bootstrap-server localhost:9092 \
  --topic ev_raw \
  <<EOF
{"voltage": 3.8, "temperature": 35, "soc": 75, "soh": 95}
{"voltage": 4.5, "temperature": 55, "soc": 20, "soh": 45}
EOF
```

### Monitor Kafka Messages
```bash
docker exec kafka kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic ev_processed \
  --from-beginning
```

### Check Database Tables
```bash
# List all tables
docker exec postgres psql -U superset -d battery_metrics -c "\dt"

# Query metrics
docker exec postgres psql -U superset -d battery_metrics -c "SELECT * FROM battery_metrics LIMIT 10;"

# Count records
docker exec postgres psql -U superset -d battery_metrics -c "SELECT COUNT(*) FROM battery_metrics;"
```

### Rebuild Specific Service
```bash
docker-compose build --no-cache kafka
docker-compose up -d kafka
```

### View Service Health
```bash
docker-compose ps

# Expected output:
# NAME           STATUS              PORTS
# kafka          Up (healthy)        9092->9092/tcp
# nifi           Up (healthy)        8080->8080/tcp
# postgres       Up (healthy)        5432->5432/tcp
# superset       Up (healthy)        8088->8088/tcp
# redis          Up (healthy)        6379->6379/tcp
# spark-master   Up                  8888->8888/tcp
```

## 🔍 Troubleshooting

### NiFi Not Starting
```bash
# Check logs
docker-compose logs nifi | tail -50

# Verify Kafka connectivity
docker exec nifi nc -zv kafka 9092

# Restart with fresh volumes
docker-compose down nifi
docker volume rm nifi-conf nifi-logs || true
docker-compose up -d nifi
```

### PostgreSQL Init Failed
```bash
# Verify init files exist
ls -la postgres/01-init-dbs.sql postgres/02-init-tables.sh

# Check init script is executable
chmod +x postgres/02-init-tables.sh

# View initialization logs
docker-compose logs postgres | grep -i "creating\|error"
```

### Kafka Not Accepting Connections
```bash
# Check Kafka is running
docker-compose ps kafka

# Verify broker health
docker exec kafka kafka-broker-api-versions.sh --bootstrap-server localhost:9092

# Check Kafka logs
docker-compose logs kafka | tail -50
```

### Superset Connection Issues
```bash
# Verify PostgreSQL is accessible
docker exec superset psql -U superset -h postgres -d superset_db -c "\dt"

# Restart Superset
docker-compose restart superset
sleep 60

# Access UI
curl http://localhost:8088
```

## 📈 Performance Tuning

### Increase Resource Limits
Edit `docker-compose.yml`:

```yaml
services:
  kafka:
    environment:
      - KAFKA_HEAP_OPTS=-Xmx2G -Xms2G
  
  nifi:
    environment:
      - NIFI_JVM_HEAP_MAX=2G
      - NIFI_JVM_HEAP_MIN=512m
  
  spark-master:
    environment:
      - SPARK_MASTER_HOST=spark-master
      - SPARK_WORKER_CORES=4
      - SPARK_WORKER_MEMORY=2G
```

### Database Optimization
```bash
# Run VACUUM on PostgreSQL
docker exec postgres psql -U superset -d battery_metrics -c "VACUUM ANALYZE;"

# Create indexes
docker exec postgres psql -U superset -d battery_metrics -c "CREATE INDEX idx_soc ON battery_metrics(soc);"
```

## 🔐 Security Notes

⚠️ **For Production:**
- Change default passwords in `docker-compose.yml`
- Use environment variables for secrets
- Enable TLS/SSL for all services
- Restrict network access
- Use secrets management (Docker Secrets / HashiCorp Vault)
- Enable authentication on Kafka
- Configure PostgreSQL password authentication

**Development Only:**
- Default credentials: admin/admin (Superset), superset/superset_pass (PostgreSQL)
- Disable HTTPS for development (NiFi, Superset)

## 📞 Support

For issues:
1. Check logs: `docker-compose logs [service]`
2. Verify service health: `docker-compose ps`
3. Test connectivity: `docker exec [service] nc -zv [host] [port]`
4. Review init scripts: `postgres/01-init-dbs.sql`, `postgres/02-init-tables.sh`

## 📝 License

Part of MSc Thesis - EV Battery Management System Monitoring

---

**Last Updated:** November 18, 2025