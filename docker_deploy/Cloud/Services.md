# Service Details & Ports

| Service | Port | Type | Purpose |
|---------|------|------|---------|
| Kafka Broker | 9092 | PLAINTEXT | Message streaming |
| Kafka Controller | 9093 | Controller | KRaft coordination |
| NiFi | 8080 | HTTP | Data flow UI & REST API |
| PostgreSQL | 5432 | TCP | Data warehouse |
| Superset | 8088 | HTTP | Analytics dashboard |
| Redis | 6379 | TCP | Caching & sessions |
| Spark Master | 8888 | HTTP | Spark UI |
| Spark Master | 7077 | TCP | Spark worker registration |
| Spark Worker | 8081 | HTTP | Worker UI |

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
```

## Kafka Topics

| Topic | Partitions | Purpose |
|-------|-----------|---------|
| ev_raw | 1 | Raw sensor data input |
| ev_processed | 1 | Processed & enriched data |
| ev_alerts | 1 | Anomaly alerts |

## PostgreSQL Databases

| Database | Owner | Purpose |
|----------|-------|---------|
| superset_db | superset | Superset metadata |
| battery_metrics | superset | Battery telemetry storage |

## NiFi Processors

| Processor | Type | Input | Output | Purpose |
|-----------|------|-------|--------|---------|
| ConsumeKafka_1_0 | Source | - | ev_raw | Read from Kafka |
| LogAttribute | Utility | any | passthrough | Debug logging |
| JoltTransformJSON | Transformation | JSON | JSON | Enrich metadata |
| EvaluateJsonPath | Extraction | JSON | attributes | Extract fields |
| RouteOnAttribute | Router | any | split | Route by conditions |
| PublishKafka_1_0 | Sink | any | Kafka | Publish to topic |
| PutSQL | Sink | any | PostgreSQL | Store to database |