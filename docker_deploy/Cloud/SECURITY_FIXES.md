# Security Fixes for Demo → Production

## 1. Update `.env` File (Replace hardcoded secrets)

Create `docker_deploy/Cloud/.env`:

```bash
# ============================
# SECURITY CREDENTIALS
# ============================

# PostgreSQL
POSTGRES_USER=admin_user_change_me
POSTGRES_PASSWORD=PleaseChangeMe_SecurePassword_123!@#
POSTGRES_DB=battery_metrics

# Superset
SUPERSET_ADMIN_USER=admin_secure
SUPERSET_ADMIN_PASSWORD=SupersetSecure_Pass_2025!@#
SUPERSET_SECRET_KEY=$(openssl rand -base64 32)

# Kafka
KAFKA_BROKER=kafka:9092
KAFKA_CLUSTER_ID=xB7zK9pL5mN2qR8vT4wX9Y

# Redis
REDIS_PASSWORD=RedisSecure_Pass_2025!@#
REDIS_HOST=redis
REDIS_PORT=6379

# MQTT Bridge
MQTT_HOST=mqtt-broker
MQTT_PORT=1883
MQTT_USER=mqtt_user
MQTT_PASSWORD=MqttSecure_Pass_2025!@#

# Spark
SPARK_MASTER_HOST=spark-master
SPARK_MASTER_PORT=7077
SPARK_WORKER_CORES=4
SPARK_WORKER_MEMORY=2G

# NiFi
NIFI_WEB_HTTP_PORT=8080
NIFI_SECURITY_NEEDCLIENTAUTH=false

# App Settings
ENVIRONMENT=production
LOG_LEVEL=WARN
DEBUG=false
```

Generate secure passwords:
```bash
# Generate 32-char random password
openssl rand -base64 32

# Use these values in .env
```

---

## 2. Update `docker-compose.yml` to Use `.env`

Replace hardcoded values:

```yaml
# BEFORE (Insecure)
postgres:
  environment:
    - POSTGRES_USER=superset
    - POSTGRES_PASSWORD=superset_pass

# AFTER (Secure)
postgres:
  environment:
    - POSTGRES_USER=${POSTGRES_USER}
    - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
  env_file:
    - .env
```

Full updated service example:

```yaml
postgres:
  image: postgres:15-alpine
  container_name: postgres
  environment:
    - POSTGRES_USER=${POSTGRES_USER}
    - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    - POSTGRES_DB=${POSTGRES_DB}
  env_file:
    - .env
  ports:
    - "5432:5432"
  volumes:
    - postgres-data:/var/lib/postgresql/data
    - ./postgres/01-init-dbs.sql:/docker-entrypoint-initdb.d/01-init-dbs.sql
  healthcheck:
    test: ["CMD", "pg_isready", "-U", "${POSTGRES_USER}"]
    interval: 10s
    timeout: 5s
    retries: 5
  restart: unless-stopped
  networks:
    - cloud_net
```

---

## 3. Add `.env` to `.gitignore` (NEVER COMMIT SECRETS)

Update `docker_deploy/Cloud/.gitignore`:

```bash
# Secrets & Credentials
.env
.env.local
.env.*.local
.env.production
secrets/
*.key
*.pem
*.pfx
*.crt

# Sensitive files
postgres-credentials.txt
superset-credentials.txt
kafka-secrets.yml

# Never commit these
config.secret.yml
docker-compose.override.yml
```

---

## 4. Container Resource Limits

Update `docker-compose.yml` for ALL services:

```yaml
postgres:
  deploy:
    resources:
      limits:
        cpus: '1.0'
        memory: 2G
      reservations:
        cpus: '0.5'
        memory: 1G

kafka:
  deploy:
    resources:
      limits:
        cpus: '2.0'
        memory: 4G
      reservations:
        cpus: '1.0'
        memory: 2G

nifi:
  deploy:
    resources:
      limits:
        cpus: '2.0'
        memory: 4G
      reservations:
        cpus: '1.0'
        memory: 2G

spark-master:
  deploy:
    resources:
      limits:
        cpus: '4.0'
        memory: 8G
      reservations:
        cpus: '2.0'
        memory: 4G

superset:
  deploy:
    resources:
      limits:
        cpus: '2.0'
        memory: 4G
      reservations:
        cpus: '1.0'
        memory: 2G
```

---

## 5. Run Containers as Non-Root

Update Dockerfiles:

**postgres/Dockerfile:**
```dockerfile
FROM postgres:15-alpine
RUN groupadd -r postgres_user && useradd -r -g postgres_user postgres_user
USER postgres_user
```

**superset/Dockerfile:**
```dockerfile
FROM apache/superset:latest
USER superset
# Avoid running as root
```

**spark/Dockerfile:**
```dockerfile
FROM bitnami/spark:3.5.0
USER 1000:1000  # Non-root UID:GID
```

---

## 6. Network Segmentation

Create separate networks for security:

```yaml
networks:
  # Frontend (public access)
  frontend_net:
    driver: bridge
  
  # Backend (internal only)
  backend_net:
    driver: bridge
    internal: true
  
  # Data layer (restricted)
  data_net:
    driver: bridge
    internal: true

services:
  # Public: Superset UI
  superset:
    networks:
      - frontend_net
      - backend_net

  # Internal: Kafka, NiFi, Spark
  kafka:
    networks:
      - backend_net
      - data_net

  # Data: PostgreSQL, Redis
  postgres:
    networks:
      - data_net
```

---

## 7. Add Nginx Reverse Proxy (Auth Layer)

Create `docker_deploy/Cloud/nginx/nginx.conf`:

```nginx
upstream superset {
    server superset:8088;
}

upstream nifi {
    server nifi:8080;
}

upstream spark {
    server spark-master:8080;
}

# Rate limiting
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=ui_limit:10m rate=30r/m;

# Basic authentication
auth_basic_user_file /etc/nginx/.htpasswd;

server {
    listen 80;
    server_name _;

    # Rate limiting
    limit_req zone=ui_limit burst=5 nodelay;

    # Superset
    location /superset/ {
        auth_basic "Restricted Access";
        proxy_pass http://superset/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # NiFi
    location /nifi/ {
        auth_basic "Restricted Access";
        proxy_pass http://nifi/nifi/;
        proxy_set_header Host $host;
        proxy_buffering off;
    }

    # Spark
    location /spark/ {
        auth_basic "Restricted Access";
        proxy_pass http://spark/;
    }
}
```

Add to `docker-compose.yml`:

```yaml
nginx:
  image: nginx:alpine
  container_name: nginx-proxy
  ports:
    - "80:80"
    - "443:443"
  volumes:
    - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    - ./nginx/.htpasswd:/etc/nginx/.htpasswd:ro
  networks:
    - frontend_net
    - backend_net
  depends_on:
    - superset
    - nifi
    - spark-master
```

Generate `.htpasswd`:
```bash
# Create htpasswd file
htpasswd -c nginx/.htpasswd admin_user
# Enter password when prompted
```

---

## 8. Input Validation for Bridge

Update `docker_deploy/Cloud/bridge/mqtt_to_kafka.py`:

```python
import json
import logging
from typing import Dict, Any

log = logging.getLogger(__name__)

# Schema validation
VALID_SCHEMA = {
    "voltage": float,
    "temperature": float,
    "current": float,
    "soc": float,
    "soh": float,
    "timestamp": str
}

VALID_RANGES = {
    "voltage": (0, 5),
    "temperature": (-40, 80),
    "current": (-500, 500),
    "soc": (0, 100),
    "soh": (0, 100)
}

def validate_message(data: Dict[str, Any]) -> bool:
    """Validate incoming MQTT message"""
    
    try:
        # Check required fields
        for field, dtype in VALID_SCHEMA.items():
            if field not in data:
                log.warning(f"Missing field: {field}")
                return False
            
            if not isinstance(data[field], (dtype, int)):
                log.warning(f"Invalid type for {field}: expected {dtype}, got {type(data[field])}")
                return False
        
        # Check value ranges
        for field, (min_val, max_val) in VALID_RANGES.items():
            if not (min_val <= data[field] <= max_val):
                log.warning(f"Out of range: {field}={data[field]} (expected {min_val}-{max_val})")
                return False
        
        return True
    
    except Exception as e:
        log.error(f"Validation error: {e}")
        return False

def sanitize_message(data: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize message data"""
    
    sanitized = {}
    
    for field in VALID_SCHEMA.keys():
        if field in data:
            sanitized[field] = float(data[field])
    
    # Add timestamp if missing
    if "timestamp" not in sanitized:
        from datetime import datetime
        sanitized["timestamp"] = datetime.utcnow().isoformat()
    
    return sanitized

# Update on_message callback
def on_message(client, userdata, msg):
    """MQTT message callback with validation"""
    
    try:
        payload = msg.payload.decode('utf-8')
        data = json.loads(payload)
        
        # Validate
        if not validate_message(data):
            log.warning(f"Invalid message rejected from {msg.topic}")
            return
        
        # Sanitize
        clean_data = sanitize_message(data)
        
        # Send to Kafka
        future = kafka_producer.send(KAFKA_TOPIC, value=clean_data)
        future.get(timeout=5)
        
        log.info(f"✅ Message validated and forwarded: {clean_data}")
    
    except json.JSONDecodeError:
        log.error(f"Invalid JSON from {msg.topic}")
    except Exception as e:
        log.error(f"Error processing message: {e}", exc_info=True)
```

---

## 9. PostgreSQL Security Hardening

Update `docker_deploy/Cloud/postgres/postgresql.conf`:

```conf
# SSL Connections
ssl = on
ssl_cert_file = 'server.crt'
ssl_key_file = 'server.key'

# Password policy
password_encryption = scram-sha-256

# Audit logging
log_connections = on
log_disconnections = on
log_statement = 'all'
log_min_duration_statement = 0

# Security
shared_preload_libraries = 'pg_stat_statements'
max_connections = 100
```

---

## 10. Implement Secrets Management (Docker Secrets)

For Docker Swarm:

```bash
# Create secrets
echo "PleaseChangeMe_SecurePassword_123!@#" | docker secret create db_password -
echo "SupersetSecure_Pass_2025!@#" | docker secret create superset_password -

# Update docker-compose.yml
postgres:
  secrets:
    - db_password
  environment:
    - POSTGRES_PASSWORD_FILE=/run/secrets/db_password
```

For production (Kubernetes/Vault):

```bash
# Use HashiCorp Vault instead
vault secrets enable -version=2 secret
vault kv put secret/battery-system/postgres password="..."
```

---

## ✅ Quick Deployment Checklist

```bash
cd docker_deploy/Cloud

# 1. Create .env file
cp .env.example .env
# Edit .env with secure values

# 2. Generate .htpasswd
htpasswd -c nginx/.htpasswd secure_admin_user

# 3. Set restrictive permissions
chmod 600 .env
chmod 600 nginx/.htpasswd

# 4. Scan images for vulnerabilities
trivy image postgres:15-alpine
trivy image kafka:3.8.0
trivy image nifi:2.0.0

# 5. Run security checks
docker-compose config > /dev/null
docker-compose build --no-cache

# 6. Deploy with security
docker-compose -f docker-compose.yml -f docker-compose.security.yml up -d

# 7. Verify
docker-compose ps
docker exec postgres psql -U admin_user -c "SHOW ssl;"
```

---

**Next:** See [`TLS_SETUP.md`](TLS_SETUP.md) for HTTPS/TLS implementation.