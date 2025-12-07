#!/bin/bash

echo "🧹 Cleaning up Docker resources..."

# Stop all containers
docker-compose -f Cloud/docker-compose.yml down -v 2>/dev/null || true
docker-compose -f Eage/docker-compose.yml down -v 2>/dev/null || true

# Remove conflicting networks
docker network rm cloud_default 2>/dev/null || true
docker network rm cloud_net 2>/dev/null || true
docker network rm edge_net 2>/dev/null || true

# Remove dangling resources
docker network prune -f
docker volume prune -f
docker image prune -f

echo "✅ Cleanup complete!"
echo ""
echo "Starting fresh..."
cd Cloud
docker-compose up -d --build
docker-compose logs -f kafka