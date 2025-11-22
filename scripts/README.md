# Setup Scripts

Collection of scripts to help set up and deploy the AI SEO Agent.

## Quick Start (Recommended)

The fastest way to get started:

```bash
./scripts/quick-start.sh
```

This will:
1. Check Python installation
2. Create virtual environment (if needed)
3. Install dependencies
4. Run interactive setup wizard
5. Generate all configuration files
6. Provide deployment instructions

## Interactive Setup Wizard

For a guided setup experience:

```bash
python3 scripts/setup.py
```

The wizard will help you:
- **Choose deployment platform** (Azure, Vercel, AWS, GCP, Docker, Railway, Fly.io)
- **Select LLM provider** (OpenAI, Anthropic, Gemini, Azure OpenAI, Ollama)
- **Configure database** (PostgreSQL, MongoDB, SQLite, MySQL, Cosmos DB)
- **Set up API keys** and credentials
- **Generate configuration files** (.env, docker-compose.yml, vercel.json, azure/parameters.json, etc.)
- **Initialize database schema**
- **Get deployment instructions** specific to your platform

### Features

#### Platform Support

| Platform | Difficulty | Best For | Setup Time |
|----------|-----------|----------|------------|
| **Azure** | ⭐⭐⭐ Advanced | Enterprise, integrated AI | 20-30 min |
| **Vercel** | ⭐ Easy | Quick MVP, serverless | 5 min |
| **Railway** | ⭐ Easy | Quick deployment | 5 min |
| **Docker Compose** | ⭐⭐ Medium | Self-hosted | 10 min |
| **Fly.io** | ⭐⭐ Medium | Global edge | 15 min |
| **AWS** | ⭐⭐⭐ Advanced | Enterprise | 30 min |
| **GCP** | ⭐⭐⭐ Advanced | Enterprise, AI/ML | 30 min |

#### LLM Provider Support

- **OpenAI** - GPT-4o, GPT-4, GPT-3.5-turbo
- **Anthropic** - Claude 3.5 Sonnet, Claude 3 Opus
- **Google Gemini** - Gemini Pro, Gemini Ultra
- **Azure OpenAI** - All OpenAI models via Azure
- **Local (Ollama)** - Llama 3, Mixtral, and others (free!)

#### Database Support

- **PostgreSQL** - Recommended for production
- **MongoDB** - NoSQL, flexible schema
- **SQLite** - File-based, perfect for development
- **MySQL** - Popular alternative

## Manual Setup

If you prefer manual setup or need custom configuration:

1. **Copy environment template:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` with your configuration:**
   ```bash
   # LLM Provider
   OPENAI_API_KEY=sk-...

   # Database
   POSTGRES_URL=postgresql://...

   # Redis
   REDIS_URL=redis://localhost:6379
   ```

3. **Install dependencies:**
   ```bash
   pip install -e .
   ```

4. **Run database migrations:**
   ```bash
   python scripts/init-db.py
   ```

5. **Start the API:**
   ```bash
   uvicorn src.api.main:app --reload
   ```

## Example Setups

### Azure + Azure OpenAI + Cosmos DB

```bash
# Run setup wizard
python3 scripts/setup.py

# Choose:
# 1. Platform: Azure
# 2. LLM: Azure OpenAI
# 3. Database: PostgreSQL or Cosmos DB

# Deploy with automation script
./scripts/azure-deploy.sh

# Or deploy manually - see AZURE_DEPLOYMENT.md
```

### Vercel + OpenAI + Vercel Postgres

```bash
# Run setup wizard
python3 scripts/setup.py

# Choose:
# 1. Platform: Vercel
# 2. LLM: OpenAI
# 3. Database: PostgreSQL (Vercel Postgres)

# Deploy
vercel --prod
```

### Docker + Local LLM + PostgreSQL

```bash
# Run setup wizard
python3 scripts/setup.py

# Choose:
# 1. Platform: Docker Compose
# 2. LLM: Ollama (local)
# 3. Database: PostgreSQL

# Deploy
docker-compose up -d
```

### AWS + Anthropic + RDS

```bash
# Run setup wizard
python3 scripts/setup.py

# Choose:
# 1. Platform: AWS
# 2. LLM: Anthropic Claude
# 3. Database: PostgreSQL (RDS)

# Follow AWS deployment instructions
```

## Configuration Files Generated

The setup wizard creates these files based on your choices:

| File | Purpose | Platform |
|------|---------|----------|
| `.env` | Environment variables | All |
| `vercel.json` | Vercel configuration | Vercel |
| `docker-compose.yml` | Docker services | Docker |
| `cloudbuild.yaml` | Build configuration | GCP |
| `fly.toml` | Fly.io configuration | Fly.io |
| `schema/postgres.sql` | Database schema | PostgreSQL |

## Troubleshooting

### Setup Wizard Won't Start

```bash
# Install rich library manually
pip install rich

# Run wizard
python3 scripts/setup.py
```

### Database Connection Fails

```bash
# Check database is running
docker-compose ps db

# Test connection
psql $POSTGRES_URL
```

### Import Errors

```bash
# Reinstall in development mode
pip install -e .

# Or full install
pip install -e ".[all]"
```

## Next Steps

After setup:

1. **Test your deployment:**
   ```bash
   curl http://localhost:8000/health
   ```

2. **View performance dashboard:**
   ```bash
   python -m src.dashboard.performance
   ```

3. **Run tests:**
   ```bash
   pytest tests/ -v
   ```

4. **Check the API docs:**
   ```
   http://localhost:8000/docs
   ```

## Additional Resources

- [Azure Deployment Guide](../AZURE_DEPLOYMENT.md) - Complete Azure setup guide
- [Deployment Backends Guide](../DEPLOYMENT_BACKENDS.md) - Detailed deployment instructions for other platforms
- [Performance Optimizations](../PERFORMANCE_OPTIMIZATIONS.md) - Performance tuning guide
- [Main README](../README.md) - Project overview

## Support

If you encounter issues:

1. Check the [Troubleshooting](#troubleshooting) section
2. Review [DEPLOYMENT_BACKENDS.md](../DEPLOYMENT_BACKENDS.md)
3. Open an issue on GitHub
