-- Create Superset database
CREATE DATABASE superset_db OWNER superset;

-- Create battery metrics database (for NiFi/Spark data)
CREATE DATABASE battery_metrics OWNER superset;

-- Connect to battery_metrics and create tables
\c battery_metrics;

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

-- Create indexes
CREATE INDEX idx_metrics_timestamp ON battery_metrics(timestamp);
CREATE INDEX idx_faults_severity ON battery_faults(severity);

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE battery_metrics TO superset;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO superset;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO superset;