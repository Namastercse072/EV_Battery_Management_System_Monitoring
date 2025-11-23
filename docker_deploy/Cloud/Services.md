# Service Details & Ports

## Complete Data Flow

```
IoT Sensors
    ↓
[Kafka: ev_raw]
    ↓
[NiFi: ConsumeKafka → Transform → RouteOnAttribute]
    ↓
[Kafka: ev_processed] ← (Normal)  [Kafka: ev_alerts] ← (Anomalies)
    ↓
[Spark: Consume ev_processed]
    ↓
[PostgreSQL: battery_metrics table]
    ↓
[Superset: Dashboard & Visualization]
```

## Services & Ports

| Service | Port | Type | Purpose |
|---------|------|------|---------|
| Kafka Broker | 9092 | PLAINTEXT | Message streaming |
| Kafka Controller | 9093 | Controller | KRaft coordination |
| NiFi | 8080 | HTTP | Data flow orchestration |
| Spark Master | 7077 | TCP | Job submission |
| Spark Master UI | 8888 | HTTP | Spark monitoring |
| Spark Worker | 8081 | HTTP | Worker UI |
| PostgreSQL | 5432 | TCP | Data warehouse |
| Superset | 8088 | HTTP | Analytics dashboard |
| Redis | 6379 | TCP | Caching & sessions |

## Kafka Topics

| Topic | Partitions | Purpose | Source | Sink |
|-------|-----------|---------|--------|------|
| ev_raw | 1 | Raw sensor input | IoT / Test | NiFi |
| ev_processed | 1 | Cleaned & enriched | NiFi | Spark + Superset |
| ev_alerts | 1 | Anomalies detected | NiFi | Monitoring |

## Spark Applications

| App | Input | Output | Purpose |
|-----|-------|--------|---------|
| battery_processor.py | ev_raw | ev_processed + ev_alerts | Real-time processing & anomaly detection |
| store_to_postgres.py | ev_processed | PostgreSQL | Persist data for analytics |

## Data Pipeline Stages

### Stage 1: NiFi Processing
- **Input:** Kafka `ev_raw`
- **Processors:** ConsumeKafka → LogAttribute → JoltTransformJSON → EvaluateJsonPath → RouteOnAttribute
- **Output:** 
  - Normal data → `ev_processed`
  - Anomalies → `ev_alerts`

### Stage 2: Spark Real-time Processing
- **Input:** Kafka `ev_raw` (via battery_processor.py)
- **Processing:**
  - Parse JSON
  - Transform & enrich
  - Detect anomalies (voltage, temperature, SOC, SOH thresholds)
  - Split normal vs alert
- **Output:**
  - Normal → `ev_processed`
  - Alerts → `ev_alerts`
  - Console debug logs

### Stage 3: Spark PostgreSQL Storage
- **Input:** Kafka `ev_processed`
- **Processing:** Batch writes to database
- **Output:** PostgreSQL `battery_metrics` table

### Stage 4: Superset Visualization
- **Input:** PostgreSQL `battery_metrics`
- **Processing:** SQL queries, dashboard creation
- **Output:** Interactive dashboards & reports

## Anomaly Detection Rules

| Condition | Type | Severity |
|-----------|------|----------|
| voltage > 4.2V | HIGH_VOLTAGE | CRITICAL |
| voltage < 2.5V | LOW_VOLTAGE | WARNING |
| temperature > 50°C | OVERHEAT | CRITICAL |
| temperature < 0°C | UNDERCOOL | WARNING |
| SOC < 20% | CRITICAL_LOW_SOC | CRITICAL |
| SOH < 50% | DEGRADED_BATTERY | WARNING |

## Example Message Format

### Input (ev_raw)
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

### Output (ev_processed)
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

### Alert Example (ev_alerts)
```json
{
  "voltage": 4.5,
  "temperature": 55,
  "current": 120,
  "soc": 15,
  "soh": 45,
  "timestamp": "2025-11-18T02:35:00Z",
  "processing_timestamp": "2025-11-18T02:35:01Z",
  "is_anomaly": true,
  "anomaly_type": "OVERHEAT,CRITICAL_LOW_SOC",
  "severity": "CRITICAL"
}
```

## Environment Variables

```bash
# PostgreSQL
POSTGRES_USER=superset
POSTGRES_PASSWORD=superset_pass

# Superset
SUPERSET_SECRET_KEY=your-secret-key-12345
SUPERSET_LOAD_EXAMPLES=no

# Kafka
KAFKA_CLUSTER_ID=xB7zK9pL5mN2qR8vT4wX9Y

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# Spark
SPARK_MASTER_HOST=spark-master
SPARK_MASTER_PORT=7077
```