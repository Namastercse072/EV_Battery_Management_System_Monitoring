# EV_Battery_Management_System_Monitoring

**Real-time battery monitoring & anomaly detection** for electric vehicles using edge computing, stream processing, and cloud analytics.

**MSc Thesis Project** — Data Science | Data Analysis | AI Engineering

---

## 📋 Overview

Complete end-to-end system for monitoring EV battery health:
- **Edge (`Eage`)**: Real-time sensor simulation + ML anomaly detection (MQTT)
- **Cloud (`Cloud`)**: Data streaming (Kafka) → Processing (NiFi/Spark) → Storage (PostgreSQL) → Visualization (Superset)
- **Local (`CALCE_BATT_INR`)**: Battery data preprocessing & feature engineering

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  EV Battery Monitoring System               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  EDGE DEVICES (docker_deploy/Eage)                         │
│  ├─ Sensor Simulator (MQTT Publisher)                      │
│  ├─ ML Inference (Anomaly Detection - IsolationForest)     │
│  └─ Fault Alerts (ev/fault topic)                          │
│           ↓ MQTT Protocol                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  MQTT ↔ KAFKA BRIDGE (mqtt-kafka-bridge)            │   │
│  │  Converts MQTT messages to Kafka topics             │   │
│  └─────────────────────────────────────────────────────┘   │
│           ↓ Kafka ev_raw topic                             │
│                                                             │
│  CLOUD PLATFORM (docker_deploy/Cloud)                      │
│  ├─ Kafka (Message Broker) ........................ 9092    │
│  ├─ NiFi (Data Orchestration) ..................... 8080    │
│  │  └─ ConsumeKafka → Transform → Route → PublishKafka    │
│  │                                                          │
│  ├─ Spark (Real-time Processing) ................. 7077    │
│  │  └─ Consume ev_raw → Anomaly Detection → ev_processed  │
│  │                                                          │
│  ├─ PostgreSQL (Data Warehouse) .................. 5432    │
│  │  └─ battery_metrics table (time-series data)           │
│  │                                                          │
│  ├─ Superset (Analytics Dashboard) ............... 8088    │
│  │  └─ Query PostgreSQL + Visualize metrics              │
│  │                                                          │
│  ├─ Redis (Cache) ............................... 6379    │
│  └─ Nginx (Reverse Proxy + Auth) ................. 80/443  │
│                                                             │
│  LOCAL PREPROCESSING (CALCE_BATT_INR)                      │
│  ├─ Feature Engineering                                    │
│  ├─ Data Cleaning                                          │
│  └─ Export to Cloud                                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 📁 Directory Structure

```
EV_Battery_Management_System_Monitoring/
│
├── README.md                          # This file
├── LICENSE                            # BSD 3-Clause
├── .gitignore                         # Version control
│
├── CALCE_BATT_INR.py                 # Root preprocessing script
├── CALCE_Preprocessed.csv            # Output data
├── CALCE_Preprocessed.ipynb          # Jupyter analysis
│
├── calce_batt/                        # Docker-packaged preprocessing
│   └── calce-batt-inr/
│       ├── Dockerfile
│       ├── docker-compose.yml
│       ├── requirements.txt
│       ├── .dockerignore
│       └── src/
│           └── CALCE_BATT_INR.py
│
├── data/                              # Sample battery data
│   ├── sample1/
│   └── sample2/
│
└── docker_deploy/                     # Edge-Cloud Infrastructure
    ├── docker-compose.yml             # Unified orchestration
    │
    ├── Cloud/                         # ☁️ Cloud Platform
    │   ├── docker-compose.yml
    │   ├── .env.example               # Environment template
    │   ├── README.md
    │   ├── SECURITY.md
    │   ├── SECURITY_FIXES.md
    │   ├── DEPLOYMENT_CHECKLIST.md
    │   ├── SERVICES.md
    │   ├── TLS_SETUP.md
    │   │
    │   ├── kafka/
    │   │   ├── Dockerfile
    │   │   ├── entrypoint.sh
    │   │   └── server.properties
    │   │
    │   ├── nifi/
    │   │   ├── Dockerfile
    │   │   ├── nifi-dataflow.xml       # Data flow template
    │   │   ├── nifi.properties
    │   │   └── init-flow.sh
    │   │
    │   ├── spark-apps/
    │   │   ├── Dockerfile
    │   │   ├── battery_processor.py    # Real-time processing
    │   │   └── store_to_postgres.py    # Database persistence
    │   │
    │   ├── postgres/
    │   │   ├── 01-init-dbs.sql
    │   │   ├── 02-init-tables.sh
    │   │   └── postgresql.conf
    │   │
    │   ├── superset/
    │   │   ├── Dockerfile
    │   │   └── entrypoint.sh
    │   │
    │   ├── bridge/                     # MQTT ↔ Kafka Bridge
    │   │   ├── Dockerfile
    │   │   ├── mqtt_to_kafka.py
    │   │   └── requirements.txt
    │   │
    │   ├── nginx/
    │   │   └── nginx.conf
    │   │
    │   └── TLS/                        # SSL Certificates
    │       ├── generate-certs.sh
    │       └── tls.conf
    │
    ├── Eage/                           # 📍 Edge Gateway
    │   ├── docker-compose.yml
    │   ├── Dockerfile
    │   ├── README.md
    │   │
    │   ├── mosquitto/
    │   │   └── config/
    │   │       └── mosquitto.conf
    │   │
    │   └── edge/
    │       ├── app/
    │       │   └── sensor_simulate.py  # MQTT publisher
    │       └── models/
    │           └── Machine_learning.py # ML inference
    │
    └── kafka-data/                    # Docker volumes
        spark/
        superset/
```

---

## 🚀 Quick Start

### Prerequisites
- **Docker** & **Docker Compose** 3.8+
- **16GB RAM** (minimum)
- **50GB disk** space
- **Ubuntu 20.04+** or **Windows 10+** with **WSL2**

### 1️⃣ Start Cloud Stack

```bash
cd docker_deploy/Cloud

# Create secure environment file
cp .env.example .env
# Edit .env with your credentials

# Start all cloud services
docker-compose up -d

# Wait for services to be healthy
sleep 120
docker-compose ps
```

**Access Services:**
- **Superset Dashboard**: http://localhost:8088 (admin / admin)
- **NiFi UI**: http://localhost:8080/nifi
- **Spark UI**: http://localhost:8888
- **Kafka**: localhost:9092
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

### 2️⃣ Start Edge Stack

```bash
cd docker_deploy/Eage

# Start edge services (sensor simulator + ML inference)
docker-compose up -d

# View logs
docker-compose logs -f
```

**MQTT Topics:**
- `ev/metrics` — sensor data (published by sensor-sim)
- `ev/fault` — anomaly alerts (published by ml_inference)

### 3️⃣ Run Local Preprocessing

```bash
# Option A: Direct Python
python CALCE_BATT_INR.py --input data/sample1/battery.csv --output CALCE_Preprocessed.csv

# Option B: Docker
cd calce_batt/calce-batt-inr
docker-compose up

# Option C: PowerShell (Windows)
$f = Get-ChildItem -Path '.\data' -Include '*.csv','*.xlsx' -File -Recurse | Select-Object -First 1
python .\CALCE_BATT_INR.py --input $f.FullName --output '.\CALCE_Preprocessed.csv' --no-plot
```

---

## 📊 Data Flow

```
Sensor Data (Edge)
       ↓ MQTT
   ev/metrics
       ↓
  [mqtt-kafka-bridge]
       ↓ Kafka
   ev_raw topic
       ↓
   [NiFi]
   Transform & Route
       ├─ Normal ──→ ev_processed
       └─ Alerts ──→ ev_alerts
       ↓
   [Spark Streaming]
   - Parse JSON
   - Detect anomalies
   - Enrich data
       ↓
   [PostgreSQL]
   battery_metrics table
       ↓
   [Superset]
   Interactive Dashboard
```

---

## 🔋 Key Components

### Edge (Eage)
- **MQTT Broker** (Eclipse Mosquitto)
- **Sensor Simulator** (Python) — generates synthetic battery metrics
- **ML Inference** (TensorFlow + scikit-learn) — IsolationForest anomaly detection
- **Real-time fault alerts** via MQTT

### Cloud (Cloud)
- **Kafka** — distributed message broker (KRaft mode)
- **NiFi** — data flow orchestration & transformation
- **Spark** — real-time stream processing
- **PostgreSQL** — time-series data warehouse
- **Superset** — interactive analytics dashboards
- **Redis** — caching & session management
- **Nginx** — reverse proxy + authentication

### Local (CALCE_BATT_INR)
- **Data preprocessing** — CSV/Excel/ZIP support
- **Feature engineering** — Power, Energy, dV/dt, normalization
- **Archive extraction** — automatic ZIP/TAR handling
- **Robust error handling** — graceful fallbacks

---

## 🔐 Security

⚠️ **DEMO MODE** — See [`docker_deploy/Cloud/SECURITY.md`](docker_deploy/Cloud/SECURITY.md)

### Production Checklist
- [ ] Generate strong credentials (32+ chars)
- [ ] Enable TLS 1.3 on all services
- [ ] Implement network segmentation
- [ ] Add reverse proxy authentication (Nginx)
- [ ] Enable PostgreSQL SSL
- [ ] Scan Docker images for vulnerabilities
- [ ] Implement secrets management (Vault)
- [ ] Enable audit logging

**See [`SECURITY_FIXES.md`](docker_deploy/Cloud/SECURITY_FIXES.md) for implementation.**

---

## 📚 Documentation

| File | Purpose |
|------|---------|
| [`docker_deploy/Cloud/README.md`](docker_deploy/Cloud/README.md) | Cloud deployment guide |
| [`docker_deploy/Cloud/SECURITY.md`](docker_deploy/Cloud/SECURITY.md) | Security audit & risks |
| [`docker_deploy/Cloud/SECURITY_FIXES.md`](docker_deploy/Cloud/SECURITY_FIXES.md) | Security hardening |
| [`docker_deploy/Cloud/SERVICES.md`](docker_deploy/Cloud/SERVICES.md) | Service details & ports |
| [`docker_deploy/Cloud/DEPLOYMENT_CHECKLIST.md`](docker_deploy/Cloud/DEPLOYMENT_CHECKLIST.md) | Pre-production verification |
| [`docker_deploy/Eage/README.md`](docker_deploy/Eage/README.md) | Edge gateway setup |
| [`calce_batt/calce-batt-inr/README.md`](calce_batt/calce-batt-inr/README.md) | Preprocessing guide |

---

## 🧪 Testing & Validation

### Test 1: MQTT Bridge → Kafka
```bash
# Monitor bridge
docker-compose -f docker_deploy/Cloud/docker-compose.yml logs -f mqtt-kafka-bridge

# Send test message
mosquitto_pub -h localhost -p 1883 -t ev/metrics -m \
  '{"voltage":3.8,"temperature":35,"soc":75,"soh":95,"timestamp":"2025-11-18T02:30:00Z"}'

# Verify in Kafka
docker exec kafka kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic ev_raw --max-messages 1
```

### Test 2: End-to-End Flow
```bash
# Check NiFi processors
curl http://localhost:8080/nifi-api/system-diagnostics

# Query PostgreSQL
docker exec postgres psql -U superset -d battery_metrics -c \
  "SELECT COUNT(*) FROM battery_metrics;"

# Access Superset
open http://localhost:8088
```

---

## 📈 Performance Tuning

```bash
# Increase Kafka memory
export KAFKA_HEAP_OPTS="-Xmx2G -Xms2G"

# Increase Spark workers
docker-compose scale spark-worker=3

# Vacuum PostgreSQL
docker exec postgres psql -U superset -d battery_metrics -c "VACUUM ANALYZE;"
```

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| Bridge not connecting | Check `MQTT_HOST` & `KAFKA_BROKER` in `.env` |
| NiFi processors failing | Verify Kafka broker health: `docker-compose ps` |
| PostgreSQL init failed | Check init scripts exist in `postgres/` |
| Superset can't connect DB | Verify PostgreSQL running & accessible |
| Spark jobs failing | Check logs: `docker-compose logs spark-master` |
| MQTT messages not arriving | Test bridge: `docker-compose logs mqtt-kafka-bridge` |

---

## 📖 Data References

**Battery Data Source**: [CALCE Battery Database](https://calce.umd.edu/battery-data#INR)
- **Cell**: Samsung INR 18650-20R
- **Specifications**: 2000 mAh LiNiMnCo/Graphite
- **Parameters**: Voltage, Temperature, Current, SOC, SOH

---

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/xyz`)
3. Commit changes (`git commit -m 'Add xyz'`)
4. Push to branch (`git push origin feature/xyz`)
5. Open a Pull Request

---

## 📝 License

**BSD 3-Clause License** — See [`LICENSE`](LICENSE)

Copyright (c) 2025, Namastercse072

---

## 📞 Support

For issues or questions:

1. **Check logs first**:
   ```bash
   docker-compose logs -f --tail 100
   ```

2. **Verify health**:
   ```bash
   docker-compose ps
   ```

3. **Test connectivity**:
   ```bash
   docker exec [service] nc -zv [host] [port]
   ```

4. **Open an issue** in the repository with:
   - Docker version
   - OS/Environment
   - Error logs
   - Steps to reproduce

---

**Version**: 1.0 (MSc Thesis)  
**Last Updated**: December 5, 2025  
**Status**: ⚠️ DEMO - See SECURITY.md before production