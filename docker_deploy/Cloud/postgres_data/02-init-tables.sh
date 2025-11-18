#!/bin/bash
set -e

echo "Creating tables in battery_metrics..."

psql -U superset -d battery_metrics <<EOF
CREATE TABLE IF NOT EXISTS battery_metrics (
  id SERIAL PRIMARY KEY,
  voltage DECIMAL(5,2),
  temperature DECIMAL(5,2),
  current DECIMAL(7,2),
  soc DECIMAL(5,2),
  soh DECIMAL(5,2),
  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS battery_faults (
  id SERIAL PRIMARY KEY,
  fault_type VARCHAR(50),
  severity VARCHAR(20),
  description TEXT,
  metric_id INTEGER REFERENCES battery_metrics(id),
  detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON battery_metrics(timestamp);
CREATE INDEX IF NOT EXISTS idx_faults_severity ON battery_faults(severity);

GRANT ALL PRIVILEGES ON DATABASE battery_metrics TO superset;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO superset;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO superset;

SELECT 'Tables created successfully' as status;
EOF

echo "✓ Database initialization complete"