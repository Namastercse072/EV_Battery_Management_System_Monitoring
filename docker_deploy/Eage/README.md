# 🔋 EV Battery Edge Gateway (Eage)

Real-time battery monitoring and fault detection at the edge using MQTT, Python ML models, and Docker Compose.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Docker Compose Network                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  sensor-sim              MQTT Broker           ml_inference      │
│  (Python)          (Eclipse Mosquitto)         (TensorFlow)      │
│     │                       │                        │           │
│     │──publish───>│         │                        │           │
│     │    ev/metrics         │                        │           │
│     │                       │<──subscribe────────────│           │
│     │                       │   ev/metrics           │           │
│     │                       │                        │           │
│     │                       │<──publish──────────────│           │
│     │                       │  ev/fault              │           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Services

### 1. **mqtt-broker** (Eclipse Mosquitto)
- Lightweight MQTT message broker
- Default port: 1883
- Topics:
  - `ev/metrics` — raw sensor data (voltage, temperature, SOC, etc.)
  - `ev/fault` — detected anomalies/faults

### 2. **sensor-sim** (Python)
- Simulates battery sensor data
- Publishes simulated metrics to `ev/metrics` every 2 seconds
- Image: `local/sensor-sim:latest` (built from Dockerfile)

### 3. **ml_inference** (TensorFlow)
- Runs IsolationForest anomaly detection model
- Subscribes to `ev/metrics`
- Publishes fault alerts to `ev/fault` when anomalies detected
- Image: `tensorflow/tensorflow:2.14.0`

## Quick Start

### Prerequisites
- Docker & Docker Compose installed
- Windows: run from WSL2 or PowerShell with Docker Desktop running
- Linux/macOS: standard docker-compose

### Build & Run

```bash
# Clone / navigate to the Eage folder
cd docker_deploy/Eage

# Build images and start services
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### PowerShell (Windows)

```powershell
cd "..\EV_Battery_Management_System_Monitoring\docker_deploy\Eage"
docker-compose up -d --build
docker-compose logs -f
```

## File Structure

```
Eage/
├── docker-compose.yml          # Compose configuration
├── Dockerfile                  # Build sensor-sim image
├── mosquitto/
│   ├── config/
│   │   └── mosquitto.conf      # MQTT broker config
│   └── data/                   # MQTT persisted data (volume)
├── edge/
│   ├── app/
│   │   └── sensor_simulate.py  # Sensor simulator (publishes to MQTT)
│   └── models/
│       └── Machine_learning.py # ML inference (subscribes & detects faults)
├── README.md                   # This file
└── .dockerignore               # Docker build context exclusions
```

## Configuration

### MQTT Topics & Message Format

**Publish to `ev/metrics` (sensor-sim)**
```json
{
  "voltage": 3.8,
  "temperature": 35.5,
  "current": 45.2,
  "soh": 92.1,
  "remaining_capacity": 60.3,
  "soc": 75.0,
  "timestamp": 1634567890.123
}
```

**Subscribe to `ev/fault` (ml_inference alerts)**
```json
{
  "voltage": 2.1,
  "temperature": 55.0,
  "current": 120.0,
  "soh": 45.0,
  "remaining_capacity": 15.0,
  "soc": 10.0,
  "timestamp": 1634567900.456,
  "fault_detected": true
}
```

### Adjust Sensor Publish Interval
Edit `edge/app/sensor_simulate.py`, line ~20:
```python
time.sleep(2)  # Change to desired interval (seconds)
```

### Train Custom Model
Edit `edge/models/Machine_learning.py`, lines ~11–30 to load your trained model instead of downloading from MODEL_URL.

## Monitoring & Debugging

### View Real-Time Logs

```bash
# All services
docker-compose logs -f

# Single service
docker-compose logs -f sensor-sim
docker-compose logs -f ml_inference
docker-compose logs -f mqtt-broker
```

### Monitor MQTT Traffic

```bash
# In a new terminal, subscribe to all topics
docker run --rm --network eage_edge_net eclipse-mosquitto \
  mosquitto_sub -h mqtt-broker -t "ev/#" -v
```

### Exec into Running Container

```bash
# Debug sensor-sim
docker exec -it sensor-sim bash

# Debug ml_inference
docker exec -it ml_inference bash

# Check MQTT broker
docker exec -it mqtt-broker sh
```

### Check Container Health

```bash
docker-compose ps
docker inspect sensor-sim | grep -i status
docker logs mqtt-broker --tail 50
```

## Troubleshooting

### Issue: "Connection refused" to mqtt-broker

**Solution:**
- Ensure mqtt-broker service is running: `docker-compose ps`
- Check network: `docker network ls | grep eage`
- Verify hostname resolves: `docker exec sensor-sim ping mqtt-broker`

### Issue: MQTT topic not receiving messages

**Solution:**
- Check sensor-sim is publishing: `docker-compose logs sensor-sim | grep "Published"`
- Verify subscription topic matches: `ev/metrics` vs `ev/sensor`
- Use mosquitto_sub to monitor: see "Monitor MQTT Traffic" above

### Issue: Model download fails

**Solution:**
- Set MODEL_URL to a valid endpoint or comment out the download
- The script trains a dummy model on first run if download fails
- Place your trained model at `/app/models/isoforest.pkl` before startup

### Issue: Permission denied on volumes (Windows/WSL)

**Solution:**
- Run docker-compose from WSL2 (recommended)
- Or grant Docker Desktop access to your drive: Settings > Resources > File Sharing
- Rebuild without cache: `docker-compose build --no-cache`

### Issue: Out of memory or slow inference

**Solution:**
- Reduce sensor publish frequency: `time.sleep(5)` or higher
- Reduce batch size in model training or inference
- Increase Docker memory limits in docker-compose: `mem_limit: 2g`

## Development Workflow

### Quick Rebuild After Code Changes

```bash
# Rebuild sensor-sim only (if you edited sensor_simulate.py or Dockerfile)
docker-compose build --no-cache sensor-sim
docker-compose up -d sensor-sim

# Rebuild ml_inference (if you edited Machine_learning.py)
docker-compose build --no-cache ml_inference
docker-compose up -d ml_inference

# Full rebuild
docker-compose down && docker-compose up -d --build
```

### Local Testing (without Docker)

```bash
# Install dependencies
pip install paho-mqtt numpy scikit-learn joblib requests tensorflow

# Run sensor simulator
python edge/app/sensor_simulate.py

# In another terminal, run ML inference
python edge/models/Machine_learning.py
```

(Requires local MQTT broker running on localhost:1883 or adjust connection in scripts.)

## Next Steps

- [ ] Integrate with upstream NiFi for data pipeline
- [ ] Add persistent logging to a database (e.g., InfluxDB, PostgreSQL)
- [ ] Deploy trained model from centralized model registry
- [ ] Add Prometheus metrics for monitoring
- [ ] Implement edge-to-cloud sync via MQTT bridge
- [ ] Add REST API for model retraining

## References

- [MQTT Protocol](http://mqtt.org/)
- [Paho Python MQTT Client](https://pypi.org/project/paho-mqtt/)
- [IsolationForest (scikit-learn)](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.IsolationForest.html)
- [Docker Compose Documentation](https://docs.docker.com/compose/)

## License

See LICENSE file in repository root.

## Support

For issues or questions, check logs first:
```bash
docker-compose logs -f --tail 100
```

Then open an issue in the repository.