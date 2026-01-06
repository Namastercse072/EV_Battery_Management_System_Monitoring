# Multi-Node Architecture Diagrams

## 1. High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        EV BATTERY MANAGEMENT SYSTEM v2.0                    │
│                         Multi-Node Architecture                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│         EDGE TIER (Multi-Node)          │
├─────────────────────────────────────────┤
│                                         │
│  ┌─────────────┐  ┌─────────────────┐  │
│  │  EDGE NODE 1│  │  EDGE NODE 2    │  │
│  ├─────────────┤  ├─────────────────┤  │
│  │ Sensors     │  │ Sensors         │  │
│  │ Data (2.0/s)│  │ Data (2.0/s)    │  │
│  └──────┬──────┘  └────────┬────────┘  │
│         │                  │           │
│         │ MQTT             │ MQTT      │
│         │ (ev/metrics/1)   │ (ev/metrics/2)
│         │                  │           │
│  ┌──────▼──────┐  ┌────────▼────────┐  │
│  │ML-Inference │  │ ML-Inference    │  │
│  │(Anomaly Det)│  │ (Anomaly Det)   │  │
│  └──────┬──────┘  └────────┬────────┘  │
│         │                  │           │
│         │ MQTT             │ MQTT      │
│         │ (ev/alerts/1)    │ (ev/alerts/2)
│         │                  │           │
│         └──────────┬───────┘           │
│                    │                   │
│         ┌──────────▼──────────┐        │
│         │ Alert Aggregator    │        │
│         │ (Central Service)   │        │
│         └──────────┬──────────┘        │
│                    │                   │
│                    │ MQTT              │
│                    │ (ev/alerts/aggregated)
│                    │                   │
│    ┌───────────────┼───────────────┐   │
│    │               │               │   │
│    │  ┌────────────▼────────────┐  │   │
│    │  │ MQTT Broker (Central)   │  │   │
│    │  │ (eclipse-mosquitto)     │  │   │
│    │  └────────────┬────────────┘  │   │
│    │               │               │   │
│    │  ┌────────────▼────────────┐  │   │
│    │  │ etcd Service Discovery  │  │   │
│    │  │ (Cluster Coordination)  │  │   │
│    │  └──────────────────────────  │   │
│    │                               │   │
│    │  ┌────────────────────────┐   │   │
│    │  │ Node Health Monitor     │   │   │
│    │  │ (Continuous Monitoring) │   │   │
│    │  └──────────┬─────────────┘   │   │
│    └─────────────┼───────────────┘   │
│                  │                   │
└──────────────────┼───────────────────┘
                   │
              MQTT Bridge
              (mqtt-kafka-bridge)
                   │
                   │ Kafka Protocol
                   │
┌──────────────────▼───────────────────┐
│       CLOUD TIER (Enhanced)           │
├──────────────────────────────────────┤
│                                      │
│  ┌──────────────────────────────┐   │
│  │   Load Balancer (Nginx)      │   │
│  │  ┌─────┐  ┌─────┐  ┌─────┐  │   │
│  │  │ :80 │  │:443 │  │:9092│  │   │
│  │  └──┬──┘  └──┬──┘  └──┬──┘  │   │
│  └─────┼────────┼────────┼─────┘   │
│        │        │        │         │
│  ┌─────▼────────▼────────▼──────┐  │
│  │   Kafka Cluster (KRaft)      │  │
│  │  ┌─────┐  ┌─────┐  ┌─────┐   │  │
│  │  │ B1  │  │ B2  │  │ B3  │   │  │
│  │  │:9092│  │:9094│  │:9096│   │  │
│  │  └─────┘  └─────┘  └─────┘   │  │
│  └──────┬────────────────┬───────┘  │
│         │                │          │
│         │ Topics         │          │
│         │ (3x replicas)  │          │
│         │ • ev_raw       │          │
│         │ • ev_alerts    │          │
│         │ • ev_alerts_agg│          │
└─────────┼────────────────┼──────────┘
          │                │
    ┌─────▼─────┐    ┌─────▼─────┐
    │   NiFi    │    │   Spark   │
    │ (Orc)     │    │ (Process) │
    │           │    │ Master    │
    │           │    │ +3Workers │
    └─────┬─────┘    └─────┬─────┘
          │                │
    ┌─────▼─────────────────▼─────┐
    │  PostgreSQL (HA Primary+R)   │
    │  ┌────────────┐              │
    │  │ Primary    │◄──Replica──┐ │
    │  │ (Read/Write)│             │ │
    │  └────────────┘              │ │
    │         │                    │ │
    │         │ Data               │ │
    │         │                    │ │
    │  ┌──────▼─────┐   ┌──────────┘ │
    │  │  Redis     │   │  Replica   │
    │  │  (Cache)   │   │(Read-Only) │
    │  └────────────┘   └────────────┘
    └────────┬────────────────────────┘
             │
    ┌────────▼──────────┐
    │   Superset        │
    │ (Analytics GUI)   │
    │ Port: 8088        │
    └───────────────────┘

    ┌──────────────────┐
    │  Consul          │
    │  (Discovery)     │
    │  Port: 8500      │
    └──────────────────┘
```

---

## 2. Edge Node Cluster (Detailed)

```
┌────────────────────────────────────────────────────────────┐
│              EDGE CLUSTER (Docker Network)                 │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │              SERVICE DISCOVERY                       │ │
│  │                   etcd                               │ │
│  │  ┌────────────────────────────────────────────────┐ │ │
│  │  │ /nodes/node1/info ──► Status: Active          │ │ │
│  │  │ /nodes/node2/info ──► Status: Active          │ │ │
│  │  │ /services/aggregator ──► Status: Running      │ │ │
│  │  │ /services/monitor ──► Status: Running         │ │ │
│  │  └────────────────────────────────────────────────┘ │ │
│  │  Port: 2379, 2380                                   │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │         MQTT BROKER (Central Hub)                    │ │
│  │         eclipse-mosquitto:2.0                        │ │
│  │                                                      │ │
│  │  Ports: 1883 (MQTT), 9001 (WebSocket)               │ │
│  │                                                      │ │
│  │  Topics:                                            │ │
│  │  ├─ ev/metrics/node1  ◄─ Sensor-Sim-N1            │ │
│  │  ├─ ev/metrics/node2  ◄─ Sensor-Sim-N2            │ │
│  │  ├─ ev/alerts/node1   ◄─ ML-Inference-N1          │ │
│  │  ├─ ev/alerts/node2   ◄─ ML-Inference-N2          │ │
│  │  └─ ev/alerts/aggregated ◄─ Alert-Aggregator      │ │
│  │  └─ $SYS/#  ◄─ Health & Status                     │ │
│  │                                                      │ │
│  │  Persistence: /mosquitto/data                       │ │
│  │  Logs: /mosquitto/log                               │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│  ┌──────────────────┐    ┌──────────────────┐            │
│  │  EDGE NODE 1     │    │  EDGE NODE 2     │            │
│  ├──────────────────┤    ├──────────────────┤            │
│  │                  │    │                  │            │
│  │ ┌──────────────┐ │    │ ┌──────────────┐ │            │
│  │ │ Sensor Sim   │ │    │ │ Sensor Sim   │ │            │
│  │ │  (Python)    │ │    │ │  (Python)    │ │            │
│  │ │ NODE_ID=1    │─┼────┼─│ NODE_ID=2    │ │            │
│  │ │ 2.0/sec      │ │    │ │ 2.0/sec      │ │            │
│  │ └──────┬───────┘ │    │ └──────┬───────┘ │            │
│  │        │ pub     │    │        │ pub     │            │
│  │        └─────────┼────┼────────┘         │            │
│  │                  │    │                  │            │
│  │ ┌──────────────┐ │    │ ┌──────────────┐ │            │
│  │ │ ML Inference │ │    │ │ ML Inference │ │            │
│  │ │ TensorFlow   │─┼────┼─│ TensorFlow   │ │            │
│  │ │ NODE_ID=1    │ │    │ │ NODE_ID=2    │ │            │
│  │ │ Anomaly Det  │ │    │ │ Anomaly Det  │ │            │
│  │ └──────┬───────┘ │    │ └──────┬───────┘ │            │
│  │        │ pub     │    │        │ pub     │            │
│  │        └─────────┼────┼────────┘         │            │
│  │                  │    │                  │            │
│  └──────────────────┘    └──────────────────┘            │
│          ▲                      ▲                         │
│          │ sub all ev/alerts/*  │ sub all ev/alerts/*     │
│          │ pub to aggregated    │ pub to aggregated      │
│          └──────────┬───────────┘                        │
│                     │                                    │
│  ┌──────────────────▼──────────────────────┐            │
│  │    ALERT AGGREGATOR                     │            │
│  │  Consolidates all node alerts           │            │
│  │                                          │            │
│  │  Input:  ev/alerts/node1,2               │            │
│  │  Output: ev/alerts/aggregated            │            │
│  │  Function: Add metadata + timestamp      │            │
│  └──────────────────┬───────────────────────┘            │
│                     │                                    │
│  ┌──────────────────▼──────────────────────┐            │
│  │    NODE HEALTH MONITOR                   │            │
│  │  Tracks cluster health                   │            │
│  │                                          │            │
│  │  • Check node status every 5s            │            │
│  │  • Register with etcd                    │            │
│  │  • Publish to cluster/nodes/*/status     │            │
│  │  • Detect failures & recovery            │            │
│  └──────────────────────────────────────────┘            │
│                                                            │
│  NETWORK: edge_net (Docker bridge)                       │
│  VOLUMES:                                                │
│  • etcd-data          ──► etcd persistence               │
│  • mosquitto/data     ──► MQTT messages                  │
│  • ./edge/models      ──► ML model files                 │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

---

## 3. Cloud Infrastructure (Detailed)

```
┌────────────────────────────────────────────────────────────────────┐
│             CLOUD INFRASTRUCTURE (Docker Network)                  │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │           LOAD BALANCER (Nginx)                              │ │
│  │  ┌────────────────────────────────────────────────────────┐ │ │
│  │  │                                                        │ │ │
│  │  │  Port 80 (HTTP)  ──────►  NiFi UI, Superset          │ │ │
│  │  │  Port 443 (HTTPS) ─────►  TLS Termination            │ │ │
│  │  │  Port 9092 (Kafka) ─────►  Kafka Brokers Load Balance│ │ │
│  │  │  Port 1883 (MQTT) ──────►  MQTT Bridge               │ │ │
│  │  │                                                        │ │ │
│  │  │  Upstream Groups:                                      │ │ │
│  │  │  • kafka_cluster: Round-robin among brokers          │ │ │
│  │  │  • mqtt_backend: To bridge                            │ │ │
│  │  │  • nifi_backend: HTTP reverse proxy                   │ │ │
│  │  │  • superset_backend: HTTP reverse proxy               │ │ │
│  │  └────────────────────────────────────────────────────────┘ │ │
│  └────────────┬──────────────────────────────────────────────────┘ │
│               │                                                    │
│  ┌────────────▼──────────────────────────────────────────────────┐ │
│  │          KAFKA CLUSTER (KRaft Mode - HA)                      │ │
│  │  ┌──────────────────────────────────────────────────────────┐ │ │
│  │  │                                                          │ │ │
│  │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │ │ │
│  │  │  │ Kafka B1     │  │ Kafka B2     │  │ Kafka B3     │  │ │ │
│  │  │  │ Node ID: 1   │  │ Node ID: 2   │  │ Node ID: 3   │  │ │ │
│  │  │  │ :9092        │  │ :9094        │  │ :9096        │  │ │ │
│  │  │  │              │  │              │  │              │  │ │ │
│  │  │  │ KRaft        │  │ KRaft        │  │ KRaft        │  │ │ │
│  │  │  │ Controller   │  │ Controller   │  │ Controller   │  │ │ │
│  │  │  │ Broker       │  │ Broker       │  │ Broker       │  │ │ │
│  │  │  │              │  │              │  │              │  │ │ │
│  │  │  │ Replication: │  │ Replication: │  │ Replication: │  │ │ │
│  │  │  │ Factor: 3    │  │ Factor: 3    │  │ Factor: 3    │  │ │ │
│  │  │  │ Min ISR: 2   │  │ Min ISR: 2   │  │ Min ISR: 2   │  │ │ │
│  │  │  └──────────────┘  └──────────────┘  └──────────────┘  │ │ │
│  │  │         │                    │                 │        │ │ │
│  │  │         └────────┬───────────┴─────────────┬──┘        │ │ │
│  │  │                  │ Cluster Communication   │            │ │ │
│  │  │                  ▼                         │            │ │ │
│  │  │  Topics (All with 3 replicas, 7-day TTL):             │ │ │
│  │  │  ┌─────────────────────────────────────────┐          │ │ │
│  │  │  │ ev_raw              (raw sensor data)    │          │ │ │
│  │  │  │   Partitions: 3 | Replicas: 3           │          │ │ │
│  │  │  │   Retention: 604800000ms (7 days)       │          │ │ │
│  │  │  │                                         │          │ │ │
│  │  │  │ ev_alerts           (node alerts)       │          │ │ │
│  │  │  │   Partitions: 3 | Replicas: 3           │          │ │ │
│  │  │  │                                         │          │ │ │
│  │  │  │ ev_alerts_aggregated (consolidated)    │          │ │ │
│  │  │  │   Partitions: 3 | Replicas: 3           │          │ │ │
│  │  │  └─────────────────────────────────────────┘          │ │ │
│  │  │                                                          │ │ │
│  │  │  Cluster ID: xB7zK9pL5mN2qR8vT4wX9Y                   │ │ │
│  │  │  Quorum Voters: B1, B2, B3                             │ │ │
│  │  │  Persistence: kafka/data per broker                    │ │ │
│  │  │                                                          │ │ │
│  │  └──────────────────────────────────────────────────────────┘ │ │
│  └────────┬────────────────────────────────────────────────────────┘ │
│           │                                                          │
│           │ Kafka Topics Feed Into:                                │
│           │                                                          │
│  ┌────────┴──────────────┐        ┌───────────────────────────┐   │
│  │       NIFI            │        │   SPARK CLUSTER           │   │
│  │  Data Flow Orc.       │        │ Real-time Processing      │   │
│  │                       │        │                           │   │
│  │  • Data routing       │        │  ┌─────────────────────┐ │   │
│  │  • Transformation     │        │  │ Spark Master        │ │   │
│  │  • Enrichment         │        │  │ :8080, :7077        │ │   │
│  │  • Flow control       │        │  │                     │ │   │
│  │  • Web UI: :8080      │        │  │ Config:             │ │   │
│  │                       │        │  │ • Master threads: ∞ │ │   │
│  └────────┬──────────────┘        │  │ • Executor cores: 2 │ │   │
│           │                        │  │ • Executor mem: 2GB │ │   │
│           │                        │  └────────────┬────────┘ │   │
│           │                        │               │          │   │
│           │                        │  ┌────────────┴─────────┐│   │
│           │                        │  │                      ││   │
│           │                        │  │ ┌──────────────────┐ ││   │
│           │                        │  │ │ Worker 1         │ ││   │
│           │                        │  │ │ Cores: 2         │ ││   │
│           │                        │  │ │ Memory: 2GB      │ ││   │
│           │                        │  │ └──────────────────┘ ││   │
│           │                        │  │                      ││   │
│           │                        │  │ ┌──────────────────┐ ││   │
│           │                        │  │ │ Worker 2         │ ││   │
│           │                        │  │ │ Cores: 2         │ ││   │
│           │                        │  │ │ Memory: 2GB      │ ││   │
│           │                        │  │ └──────────────────┘ ││   │
│           │                        │  │                      ││   │
│           │                        │  └──────────────────────┘│   │
│           │                        └───────────────┬──────────┘   │
│           │                                       │               │
│  ┌────────▼───────────────────────────────────────▼──────────┐   │
│  │         DATA WAREHOUSE & CACHE                            │   │
│  │                                                           │   │
│  │  ┌──────────────────────┐    ┌─────────────────────┐   │   │
│  │  │ PostgreSQL Primary   │    │    Redis Cache      │   │   │
│  │  │ (Read/Write)         │    │                     │   │   │
│  │  │                      │    │ • Query cache (DB0) │   │   │
│  │  │ Port: 5432           │    │ • Session store(DB1)│   │   │
│  │  │ Databases:           │    │ • TTL: 300s         │   │   │
│  │  │  • superset_db       │    │ Port: 6379          │   │   │
│  │  │  • ev_metrics        │    │ Memory: 2GB         │   │   │
│  │  │  • analytics         │    │ Persistence: AOF    │   │   │
│  │  │                      │    │ Password: Secured   │   │   │
│  │  │ Replication:         │    └─────────────────────┘   │   │
│  │  │ • WAL Streaming      │                              │   │
│  │  │ • Sync replication   │                              │   │
│  │  │ • Hot standby        │                              │   │
│  │  └──────────┬───────────┘                              │   │
│  │             │ WAL                                       │   │
│  │             │                                           │   │
│  │  ┌──────────▼───────────┐                              │   │
│  │  │ PostgreSQL Replica   │                              │   │
│  │  │ (Read-Only)          │                              │   │
│  │  │                      │                              │   │
│  │  │ Port: 5433           │                              │   │
│  │  │ Status: Hot Standby  │                              │   │
│  │  │ Lag: < 100ms         │                              │   │
│  │  └──────────────────────┘                              │   │
│  │                                                           │   │
│  └────────────┬──────────────────────────────────────────────┘   │
│               │                                                   │
│  ┌────────────▼────────────────────────────────────────────────┐ │
│  │         ANALYTICS & MONITORING                              │ │
│  │                                                             │ │
│  │  ┌──────────────────────────────────────────────────────┐ │ │
│  │  │ Superset (Analytics Dashboard)                       │ │ │
│  │  │                                                      │ │ │
│  │  │ • Port: 8088                                         │ │ │
│  │  │ • DataSources: PostgreSQL Primary + Replica         │ │ │
│  │  │ • Caching: Redis                                    │ │ │
│  │  │ • Gunicorn: 4 workers                               │ │ │
│  │  │ • Dashboards: Real-time metrics, alerts, status     │ │ │
│  │  │ • Admin: admin/admin (change in production)         │ │ │
│  │  └──────────────────────────────────────────────────────┘ │ │
│  │                                                             │ │
│  │  ┌──────────────────────────────────────────────────────┐ │ │
│  │  │ Consul (Service Discovery & Health Checks)          │ │ │
│  │  │                                                      │ │ │
│  │  │ • Port: 8500                                         │ │ │
│  │  │ • Services registered: All containers               │ │ │
│  │  │ • Health checks: Every 10s                          │ │ │
│  │  │ • Failure detection: Automatic                      │ │ │
│  │  │ • Web UI: Dashboard for service status              │ │ │
│  │  └──────────────────────────────────────────────────────┘ │ │
│  │                                                             │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                    │
│  NETWORK: cloud_net (Docker bridge)                              │
│  VOLUMES (Named):                                                │
│  • kafka-broker-{1,2,3}-data     ──► Kafka persistence          │
│  • postgres-primary-data          ──► Primary DB                 │
│  • postgres-replica-data          ──► Replica DB                 │
│  • redis-data                     ──► Cache                      │
│  • nifi-conf, nifi-logs           ──► NiFi state                 │
│  • spark-data, spark-worker-{1,2} ──► Spark jobs                │
│  • superset-config, superset-logs ──► Dashboards & configs      │
│  • consul-data                    ──► Service registry           │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## 4. Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        DATA FLOW ARCHITECTURE                       │
└─────────────────────────────────────────────────────────────────────┘

PHASE 1: DATA GENERATION (EDGE)
─────────────────────────────────

┌─────────────────────┐     ┌──────────────────────┐
│  Sensor Sim Node 1  │     │  Sensor Sim Node 2   │
│  (Generate data)    │     │  (Generate data)     │
│  2.0 msg/sec        │     │  2.0 msg/sec         │
└──────────┬──────────┘     └──────────┬───────────┘
           │ MQTT                      │ MQTT
           │ publish                   │ publish
           ▼ ev/metrics/node1          ▼ ev/metrics/node2
        
        ┌──────────────────────────────────────────┐
        │  MQTT Broker (Central)                   │
        │  • Aggregates messages                   │
        │  • Distributes to subscribers            │
        │  • Maintains queues                      │
        └──────────────────────────────────────────┘
                         ▲
                    ▲    │    ▲
                    │    │    │
        ┌───────────┴────┼────┴──────────┐
        │                │               │
        │ MQTT           │ MQTT          │ MQTT
        │ subscribe      │ subscribe     │ subscribe
        │                │               │


PHASE 2: ANOMALY DETECTION (EDGE)
──────────────────────────────────

┌─────────────────────────────────┐  ┌──────────────────────────┐
│ ML Inference Node 1             │  │ ML Inference Node 2      │
│ • Subscribe: ev/metrics/node1   │  │ • Subscribe: ev/metrics/2│
│ • Run model (IsolationForest)   │  │ • Run model              │
│ • Detect anomalies              │  │ • Detect anomalies       │
│ • Publish: ev/alerts/node1      │  │ • Publish: ev/alerts/node2
└──────────┬──────────────────────┘  └──────────┬───────────────┘
           │ MQTT                              │ MQTT
           │ ev/alerts/node1                   │ ev/alerts/node2
           └────────────────┬────────────────┘
                            │ MQTT
                            ▼
        ┌──────────────────────────────────────┐
        │  Alert Aggregator                    │
        │  • Subscribe: ev/alerts/node1,2,...  │
        │  • Add timestamp & node_id metadata  │
        │  • Deduplication logic               │
        │  • Publish: ev/alerts/aggregated     │
        └──────────────────┬───────────────────┘
                           │ MQTT
                           │ ev/alerts/aggregated
                           ▼


PHASE 3: EDGE TO CLOUD BRIDGE
──────────────────────────────

                    ┌────────────────────────┐
                    │  MQTT Broker (Central) │
                    │  Topics Monitored:     │
                    │  • ev/metrics/*        │
                    │  • ev/alerts/*         │
                    │  • ev/alerts/agg.      │
                    └──────────┬─────────────┘
                               │
                               │ Topic Match
                               │
                    ┌──────────▼──────────────┐
                    │ MQTT Bridge            │
                    │ (mqtt-kafka-bridge)    │
                    │                        │
                    │ • Subscribe to MQTT    │
                    │ • Convert to Kafka     │
                    │ • Batch messages       │
                    │ • Publish to Kafka     │
                    │                        │
                    │ Topic Mapping:         │
                    │ ev/metrics → ev_raw    │
                    │ ev/alerts → ev_alerts  │
                    │ ev/alerts/agg → ...    │
                    └──────────┬─────────────┘
                               │
                 ┌─────────────┼─────────────┐
                 │             │             │
              Kafka Protocol   │             │


PHASE 4: CLOUD DATA PROCESSING
───────────────────────────────

     ┌────────────┐  ┌────────────┐  ┌────────────┐
     │  Broker 1  │  │  Broker 2  │  │  Broker 3  │
     │ev_raw (3R) │  │ev_raw (3R) │  │ev_raw (3R) │
     └─────┬──────┘  └─────┬──────┘  └─────┬──────┘
           │               │              │
           └───────────┬───┴──────────┬───┘
                       │ Kafka Cluster
                       │
        ┌──────────────┴─────────────┐
        │                            │
        │ ┌───────────────┐    ┌────▼────────────┐
        │ │   NiFi        │    │  Spark Streaming│
        │ │ Routing &     │    │ • Connect Kafka │
        │ │ Transform     │    │ • Parse data    │
        │ │               │    │ • Aggregate     │
        │ │ ┌───────────┐ │    │ • Enrich        │
        │ │ │ Routes    │ │    │ • Anomaly Score │
        │ │ │ • Routes  │─┼────┤ • Write to DB   │
        │ │ │ • Filters │ │    └────┬────────────┘
        │ │ │ • Enrich  │ │         │
        │ │ │ • Monitor │ │         │
        │ │ └───────────┘ │         │
        │ └───────────────┘         │
        │                           │
        └───────────┬───────────────┘
                    │ Processed Data
                    ▼
        
        ┌──────────────────────────────┐
        │ PostgreSQL Primary           │
        │ • ev_metrics table           │
        │ • ev_alerts table            │
        │ • event_logs table           │
        │ • Real-time writes           │
        │ • Indexes on timestamps      │
        └──────────┬───────────────────┘
                   │ WAL Replication
                   │ (Continuous)
                   ▼
        
        ┌──────────────────────────────┐
        │ PostgreSQL Replica           │
        │ • Read-only copy             │
        │ • For reporting              │
        │ • Backup location            │
        └──────────────────────────────┘
                   │
                   │ Query
                   ▼


PHASE 5: ANALYTICS & VISUALIZATION
────────────────────────────────────

     ┌───────────────────────────────────┐
     │  Superset (Analytics Dashboard)   │
     │                                   │
     │  ┌─────────────────────────────┐  │
     │  │ Real-time Dashboard         │  │
     │  │ • Current metrics           │  │
     │  │ • Alerts summary            │  │
     │  │ • Node status               │  │
     │  │ • System health             │  │
     │  └─────────────────────────────┘  │
     │                                   │
     │  ┌─────────────────────────────┐  │
     │  │ Historical Analysis         │  │
     │  │ • Trend graphs              │  │
     │  │ • Anomaly patterns          │  │
     │  │ • Predictive models         │  │
     │  │ • Reports                   │  │
     │  └─────────────────────────────┘  │
     │                                   │
     │  ┌─────────────────────────────┐  │
     │  │ Cached by Redis             │  │
     │  │ • Query results             │  │
     │  │ • Dashboard state           │  │
     │  │ • User sessions             │  │
     │  └─────────────────────────────┘  │
     │                                   │
     │  http://localhost:8088            │
     └───────────────────────────────────┘
           ▲
           │ HTTP
           │ Queries PostgreSQL
           │


MESSAGE LATENCY ESTIMATES
──────────────────────────

Edge Generation → MQTT Broker:     0-5ms
MQTT Broker → ML Inference:        0-5ms
ML Processing → Alert Publish:     50-200ms
Alert → Alert Aggregator:          0-5ms
Aggregator → MQTT Bridge:          0-5ms
MQTT → Kafka:                      10-50ms
Kafka → Spark:                     100-500ms (batch dependent)
Spark → PostgreSQL:                10-50ms
PostgreSQL → Superset:             100-1000ms (depends on query)
─────────────────────────────────────────
Total Edge → Dashboard:            ~300-2000ms (varies with load)

```

---

## 5. Service Interaction Diagram

```
┌────────────────────────────────────────────────────────────────┐
│            SERVICE COMMUNICATION PATTERNS                       │
└────────────────────────────────────────────────────────────────┘

EDGE TIER INTERACTIONS
──────────────────────

Sensor Sim Node X
    │
    ├─► MQTT (PUB) ──────────► MQTT Broker
    │
    └─► etcd (REGISTER) ────► etcd
            └─► GET /nodes/*

ML Inference Node X
    │
    ├─► MQTT (SUB) ◄──────── MQTT Broker
    │
    ├─► MQTT (PUB) ──────────► MQTT Broker
    │
    └─► etcd (WATCH) ──────► etcd
            └─► GET /services/*

Alert Aggregator
    │
    ├─► MQTT (SUB) ◄──────── MQTT Broker
    │
    ├─► MQTT (PUB) ──────────► MQTT Broker
    │
    └─► etcd (CHECK) ───────► etcd
            └─► GET /nodes/*/status

Node Monitor
    │
    ├─► etcd (WRITE) ──────► etcd
    │
    ├─► MQTT (PUB) ──────────► MQTT Broker
    │
    └─► etcd (WATCH) ──────► etcd
            └─► GET /nodes/*/health


EDGE-TO-CLOUD INTERACTIONS
───────────────────────────

MQTT Broker (Edge)
    │
    └─► MQTT (SUBSCRIBE) ──────► MQTT Bridge
            │
            ├─ ev/metrics/*
            ├─ ev/alerts/*
            └─ ev/alerts/aggregated

MQTT Bridge (Bridge)
    │
    ├─► MQTT (SUB) ◄──────── MQTT Broker (Edge)
    │
    └─► Kafka (PUB) ──────────► Kafka Brokers (Cloud)
            │
            ├─ ev_raw
            ├─ ev_alerts
            └─ ev_alerts_aggregated


CLOUD TIER INTERACTIONS
───────────────────────

NiFi Data Flow
    │
    ├─► Kafka (CONSUME) ◄────── Kafka Cluster
    │
    ├─► Transform/Route
    │
    └─► PostgreSQL (WRITE) ──► PostgreSQL Primary
            └─► Replication ──► PostgreSQL Replica

Spark Cluster
    │
    ├─► Kafka (SUBSCRIBE) ◄──── Kafka Cluster
    │
    ├─► Process Streams
    │
    └─► PostgreSQL (WRITE) ──► PostgreSQL Primary
            └─► Distributed Write

Superset
    │
    ├─► PostgreSQL (QUERY) ───► PostgreSQL Primary
    │
    ├─► Redis (CACHE) ◄─────── Redis
    │
    └─► Consul (DISCOVER) ────► Consul


HEALTH & MONITORING
───────────────────

All Services
    │
    ├─► Docker Health Checks
    │
    ├─► etcd/Consul (Register)
    │
    ├─► MQTT (Publish Status)
    │
    └─► Logs (Structured JSON)

Consul (Service Registry)
    │
    ├─► Health Checks (Every 10s)
    │
    ├─► Service Catalog
    │
    └─► Nginx (Upstream Discovery)

```

---

## 6. Network Flows

```
Network Isolation: edge_net <--MQTT Bridge--> cloud_net

┌─────────────────────────┐          ┌─────────────────────────┐
│   EDGE NETWORK          │          │  CLOUD NETWORK          │
│   (edge_net)            │          │  (cloud_net)            │
│                         │          │                         │
│ Internal IPs:           │          │ Internal IPs:           │
│ • 172.17.0.x            │          │ • 172.18.0.x            │
│                         │          │                         │
│ Services:               │          │ Services:               │
│ • mqtt-broker           │          │ • nginx-lb              │
│ • etcd                  │          │ • kafka-broker-{1,2,3}  │
│ • sensor-sim-{1,2}      │          │ • nifi                  │
│ • ml-inference-{1,2}    │          │ • spark-master          │
│ • alert-aggregator      │          │ • spark-worker-{1,2}    │
│ • node-monitor          │          │ • postgres-primary      │
│                         │          │ • postgres-replica      │
│ External Ports:         │          │ • redis                 │
│ • 1883 (MQTT)           │          │ • superset              │
│ • 2379 (etcd API)       │          │ • consul                │
│ • 9001 (MQTT WS)        │          │                         │
│                         │          │ External Ports:         │
│                         │          │ • 80 (HTTP)             │
│                         │          │ • 443 (HTTPS)           │
│                         │          │ • 8080 (NiFi)           │
│                         │          │ • 8088 (Superset)       │
│                         │          │ • 8500 (Consul)         │
│                         │          │ • 8888 (Spark UI)       │
│                         │          │ • 9092 (Kafka)          │
│                         │          │ • 5432 (PostgreSQL)     │
│                         │          │ • 6379 (Redis)          │
│                         │          │ • 1883 (MQTT Bridge)    │
│                         │          │                         │
└─────────────────────────┘          └─────────────────────────┘
            │ Bridge Tunnels
            │ (1883 MQTT)
            │
     MQTT Bridge Proxy
     (mqtt-kafka-bridge)
            │
            │ Kafka Wire Protocol
            │ (Port 29092 Internal)
            │
        Kafka Cluster
```

---

This completes the multi-node architecture visualization. All diagrams show:

- ✅ Component relationships
- ✅ Data flows
- ✅ Network topology
- ✅ Replication patterns
- ✅ High availability setup
- ✅ Service communication

