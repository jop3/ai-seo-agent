#!/bin/bash
# Docker Compose Test Script
# Tests the docker-compose setup and verifies all services are working

set -e

echo "============================================"
echo "Docker Compose Setup Test"
echo "============================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if .env exists
echo "1. Checking environment configuration..."
if [ -f .env ]; then
    echo -e "${GREEN}✓${NC} .env file found"
else
    echo -e "${RED}✗${NC} .env file not found"
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo -e "${YELLOW}⚠${NC} Please edit .env with your configuration"
    exit 1
fi
echo ""

# Check if credentials directory exists
echo "2. Checking credentials directory..."
if [ -d credentials ]; then
    echo -e "${GREEN}✓${NC} credentials/ directory found"
else
    echo "Creating credentials/ directory..."
    mkdir -p credentials
    echo -e "${YELLOW}⚠${NC} Add your service account credentials to credentials/"
fi
echo ""

# Validate docker-compose.yml
echo "3. Validating docker-compose configuration..."
if docker-compose config > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} docker-compose.yml is valid"
else
    echo -e "${RED}✗${NC} docker-compose.yml has errors"
    docker-compose config
    exit 1
fi
echo ""

# Check if services are already running
echo "4. Checking for running services..."
if docker-compose ps | grep -q "Up"; then
    echo -e "${YELLOW}⚠${NC} Services are already running"
    docker-compose ps
    echo ""
    read -p "Stop and restart services? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Stopping services..."
        docker-compose down
    else
        echo "Skipping restart"
        exit 0
    fi
fi
echo ""

# Start services
echo "5. Starting services..."
docker-compose up -d
echo -e "${GREEN}✓${NC} Services started"
echo ""

# Wait for services to be ready
echo "6. Waiting for services to be ready..."
echo "This may take 30-60 seconds on first run..."
sleep 10

# Check Redis
echo ""
echo "Checking Redis..."
for i in {1..30}; do
    if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Redis is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}✗${NC} Redis failed to start"
        docker-compose logs redis
        exit 1
    fi
    sleep 1
done

# Check API
echo ""
echo "Checking API..."
for i in {1..60}; do
    if curl -s -f http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} API is ready"
        break
    fi
    if [ $i -eq 60 ]; then
        echo -e "${RED}✗${NC} API failed to start"
        echo "API logs:"
        docker-compose logs api | tail -20
        exit 1
    fi
    sleep 1
done
echo ""

# Test API endpoints
echo "7. Testing API endpoints..."
echo ""

# Health check
echo "Testing /health..."
HEALTH_RESPONSE=$(curl -s http://localhost:8000/health)
if echo "$HEALTH_RESPONSE" | grep -q "ok\|healthy\|status"; then
    echo -e "${GREEN}✓${NC} Health check passed"
else
    echo -e "${RED}✗${NC} Health check failed"
    echo "Response: $HEALTH_RESPONSE"
fi

# API docs
echo "Testing /docs..."
if curl -s -f http://localhost:8000/docs > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} API documentation accessible"
else
    echo -e "${YELLOW}⚠${NC} API documentation not accessible"
fi
echo ""

# Show service status
echo "8. Service Status:"
echo ""
docker-compose ps
echo ""

# Show resource usage
echo "9. Resource Usage:"
echo ""
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" \
    $(docker-compose ps -q) 2>/dev/null || echo "Unable to get stats"
echo ""

# Success!
echo "============================================"
echo -e "${GREEN}✓ Docker Compose Setup Complete!${NC}"
echo "============================================"
echo ""
echo "Access points:"
echo "  • API: http://localhost:8000"
echo "  • API Docs: http://localhost:8000/docs"
echo "  • Redis: localhost:6379"
echo ""
echo "Useful commands:"
echo "  • View logs: docker-compose logs -f"
echo "  • Stop services: docker-compose down"
echo "  • Restart API: docker-compose restart api"
echo ""
echo "Next steps:"
echo "  1. Configure your .env file with API keys"
echo "  2. Add credentials to credentials/ directory"
echo "  3. Test endpoints: http://localhost:8000/docs"
echo ""
