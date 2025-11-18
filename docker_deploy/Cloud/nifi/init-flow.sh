#!/bin/bash
set -e

NIFI_HOME=/opt/nifi/nifi-current

# Wait for NiFi to start
echo "Waiting for NiFi to be ready..."
for i in {1..60}; do
  if curl -s http://localhost:8080/nifi-api/system-diagnostics > /dev/null; then
    echo "✓ NiFi is ready"
    break
  fi
  echo "Waiting... ($i/60)"
  sleep 2
done

# Import flow (via REST API if flow.json exists)
if [ -f "$NIFI_HOME/conf/flow.json" ]; then
  echo "Importing flow configuration..."
  curl -X POST \
    -H "Content-Type: application/json" \
    -d @"$NIFI_HOME/conf/flow.json" \
    http://localhost:8080/nifi-api/flow/process-groups/root \
    || echo "⚠️ Flow import failed (may already exist)"
fi

echo "✓ NiFi initialization complete"