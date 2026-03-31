# Docker Compose Quick Start Guide

This guide will help you get the AI SEO Agent running locally with Docker Compose.

## Prerequisites

- Docker Desktop 4.0+ (includes Docker Compose)
- At least 4GB RAM available
- 10GB free disk space

## Quick Start (5 minutes)

### 1. Environment Setup

The `.env` file has been created from `.env.example`. Update the required configuration:

```bash
# Edit .env with your settings
nano .env  # or use your preferred editor
```

**Minimum required settings for local development:**
- `REDIS_URL=redis://redis:6379/0` (already set)
- Azure OpenAI credentials (if using Azure OpenAI)
- Or set up local LLM with Docker Model Runner (see README.md)

### 2. Start Services

```bash
# Start all services (API, Worker, Redis)
docker-compose up -d

# View logs
docker-compose logs -f

# Check service status
docker-compose ps
```

### 3. Verify It's Working

```bash
# Check API health
curl http://localhost:8000/health

# View API documentation
open http://localhost:8000/docs
```

## Services Overview

| Service | Port | Description |
|---------|------|-------------|
| **api** | 8000 | FastAPI REST API server |
| **worker** | - | Background worker with Playwright for browser automation |
| **redis** | 6379 | Redis cache and task queue |
| **scheduler** | - | (Optional) Celery beat for scheduled tasks |

## Common Commands

### Start/Stop Services

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Stop and remove volumes (clean slate)
docker-compose down -v

# Restart a specific service
docker-compose restart api
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f worker

# Last 100 lines
docker-compose logs --tail=100 api
```

### Rebuild After Code Changes

```bash
# Rebuild images
docker-compose build

# Rebuild without cache (if having issues)
docker-compose build --no-cache

# Rebuild and restart
docker-compose up -d --build
```

### Access Service Shells

```bash
# Access API container shell
docker-compose exec api bash

# Access worker container shell
docker-compose exec worker bash

# Run Python in API container
docker-compose exec api python
```

## Optional: Scheduled Tasks

To enable the scheduler for automated tasks:

```bash
# Start with scheduler profile
docker-compose --profile with-scheduler up -d

# Stop including scheduler
docker-compose --profile with-scheduler down
```

## Development Workflow

The docker-compose setup is optimized for development:

1. **Hot Reload**: Source code is mounted as a volume, so changes are reflected immediately
2. **Health Checks**: Services wait for dependencies to be ready
3. **Persistent Data**: Redis data is stored in a volume and persists between restarts

### Making Code Changes

1. Edit files in `src/` directory
2. API will auto-reload (FastAPI's built-in reload)
3. Worker may need restart: `docker-compose restart worker`

### Adding Python Dependencies

1. Update `pyproject.toml`
2. Rebuild images: `docker-compose build`
3. Restart services: `docker-compose up -d`

## Troubleshooting

### Port Already in Use

```bash
# Check what's using port 8000
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Change port in docker-compose.yml:
ports:
  - "8001:8000"  # Use 8001 instead
```

### Services Won't Start

```bash
# Check logs for errors
docker-compose logs

# Verify configuration
docker-compose config

# Clean rebuild
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

### Container Crashes Immediately

```bash
# Check specific service logs
docker-compose logs api

# Common issues:
# - Missing .env file → Ensure .env exists
# - Invalid configuration → Check .env values
# - Missing credentials → Add files to credentials/
```

### API Health Check Failing

```bash
# Check if API is actually running
docker-compose exec api curl http://localhost:8000/health

# Check API logs
docker-compose logs api

# Verify dependencies are ready
docker-compose ps
```

### Redis Connection Issues

```bash
# Test Redis connectivity
docker-compose exec api redis-cli -h redis ping

# Should return: PONG
```

### Worker Issues

```bash
# Check worker logs
docker-compose logs worker

# Restart worker
docker-compose restart worker

# Check if Playwright is installed
docker-compose exec worker playwright --version
```

## Network Configuration

All services run on the `seo-agent-network` bridge network. Services can reach each other by service name:

- API can reach Redis at: `redis://redis:6379/0`
- Worker can reach API at: `http://api:8000`

## Volumes

### Redis Data Volume

Redis data persists in the `redis_data` volume:

```bash
# List volumes
docker volume ls | grep ai-seo-agent

# Inspect volume
docker volume inspect ai-seo-agent_redis_data

# Remove volume (WARNING: deletes all cached data)
docker-compose down -v
```

### Credentials Volume

The `credentials/` directory is mounted read-only into containers for service account credentials:

```
credentials/
├── gsc-service-account.json
└── ga4-service-account.json
```

## Performance Tips

### Resource Limits

Add resource limits to services if needed:

```yaml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
```

### Build Cache

Docker layer caching speeds up rebuilds. To maximize:

1. Don't change `pyproject.toml` unnecessarily
2. Use `.dockerignore` to exclude unnecessary files
3. Only rebuild when dependencies change

## Production Considerations

This docker-compose setup is optimized for development. For production:

1. **Remove volume mounts** (use built image code)
2. **Use production environment variables**
3. **Enable HTTPS** (use reverse proxy like nginx)
4. **Set up monitoring** (logs, metrics, alerts)
5. **Use Docker secrets** for sensitive data
6. **Consider orchestration** (Kubernetes, Docker Swarm)

See [AZURE_DEPLOYMENT.md](AZURE_DEPLOYMENT.md) for production deployment.

## Next Steps

1. ✅ Services running locally
2. 📚 Read [README.md](README.md) for feature overview
3. 🧪 Test endpoints: http://localhost:8000/docs
4. 🔧 Configure integrations (GSC, Teams, etc.)
5. 🚀 Deploy to production when ready

## Need Help?

- 📖 Full documentation: See README.md
- 🐛 Issues: GitHub Issues
- 💬 Questions: GitHub Discussions
