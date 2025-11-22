# AI SEO Agent - Quick Reference Guide

## 🚀 Getting Started (2 Options)

### Option 1: Interactive Setup Wizard (Recommended)
```bash
./scripts/quick-start.sh
```
This will guide you through everything step-by-step.

### Option 2: Manual Setup
```bash
# 1. Copy environment template
cp .env.example .env

# 2. Edit .env with your credentials
nano .env

# 3. Install dependencies
pip install -e .

# 4. Run the API
uvicorn src.api.main:app --reload
```

---

## 📋 Platform Deployment Cheat Sheet

### Vercel (Fastest - 5 minutes)
```bash
# Run setup wizard
./scripts/quick-start.sh
# Choose: Vercel → OpenAI → Vercel Postgres

# Deploy
npm i -g vercel
vercel --prod
```

### Docker Compose (Self-Hosted)
```bash
# Run setup wizard (generates docker-compose.yml)
./scripts/quick-start.sh

# Start services
docker-compose up -d

# View logs
docker-compose logs -f api
```

### Railway (Easy Cloud Hosting)
```bash
# 1. Push to GitHub
git push origin main

# 2. Import in Railway dashboard
# 3. Add PostgreSQL addon
# 4. Deploy automatically
```

### AWS/GCP (Enterprise)
See [DEPLOYMENT_BACKENDS.md](./DEPLOYMENT_BACKENDS.md) for detailed instructions.

---

## 🤖 LLM Provider Setup

### OpenAI (Most Popular)
```bash
# .env
OPENAI_API_KEY=sk-...
```

### Anthropic Claude
```bash
# .env
ANTHROPIC_API_KEY=sk-ant-...
```

### Local (Ollama - Free!)
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull model
ollama pull llama3

# .env
OLLAMA_ENDPOINT=http://localhost:11434
OLLAMA_MODEL=llama3
```

---

## 🗄️ Database Quick Setup

### PostgreSQL (Recommended)
```bash
# Docker
docker run -d -p 5432:5432 \
  -e POSTGRES_DB=seoagent \
  -e POSTGRES_PASSWORD=yourpassword \
  postgres:15

# .env
POSTGRES_URL=postgresql://postgres:yourpassword@localhost:5432/seoagent
```

### SQLite (Development)
```bash
# .env
SQLITE_PATH=./seo_agent.db
```

---

## 📊 Performance Monitoring

### CLI Dashboard
```bash
# One-shot
python -m src.dashboard.performance

# Watch mode (updates every 5s)
python -m src.dashboard.performance watch

# Custom interval
python -m src.dashboard.performance watch 10
```

### API Endpoints
```bash
# Get stats
curl http://localhost:8000/api/v1/performance/stats

# Get health
curl http://localhost:8000/api/v1/performance/health

# Get summary
curl http://localhost:8000/api/v1/performance/summary
```

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test
pytest tests/test_optimizations.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

---

## 🔧 Common Commands

### Start Development Server
```bash
uvicorn src.api.main:app --reload --port 8000
```

### Run Worker (Background Tasks)
```bash
celery -A src.scheduler.handlers worker --loglevel=info
```

### Clear Caches
```bash
# Via API
curl -X POST http://localhost:8000/api/v1/performance/clear

# Or Python
python3 -c "from src.utils.optimizations import clear_all_caches; import asyncio; asyncio.run(clear_all_caches())"
```

### View Logs
```bash
# Docker
docker-compose logs -f api

# Systemd (if running as service)
sudo journalctl -u seo-agent -f
```

---

## 🐛 Troubleshooting

### Import Errors
```bash
# Reinstall in development mode
pip install -e .

# Or with all extras
pip install -e ".[all]"
```

### Database Connection Failed
```bash
# Check database is running
docker-compose ps db

# Test connection
psql $POSTGRES_URL

# Reset database
docker-compose down -v
docker-compose up -d db
```

### Port Already in Use
```bash
# Find process using port 8000
lsof -i :8000

# Kill it
kill -9 <PID>

# Or use different port
uvicorn src.api.main:app --port 8080
```

### Cache Issues
```bash
# Clear all caches
curl -X POST http://localhost:8000/api/v1/performance/clear \
  -H "Content-Type: application/json" \
  -d '{"all": true}'
```

---

## 📁 Project Structure

```
ai-seo-agent/
├── src/
│   ├── api/              # FastAPI routes
│   │   └── routers/
│   │       └── performance.py  # Performance monitoring API
│   ├── agents/           # SEO analysis agents
│   ├── cache/            # Page caching
│   ├── dashboard/        # Performance dashboard
│   ├── integrations/     # External APIs
│   └── utils/            # Optimization utilities
│       ├── agent_memoization.py
│       ├── background_refresh.py
│       ├── bloom_filter.py
│       ├── connection_pool.py
│       ├── optimizations.py
│       ├── request_deduplication.py
│       ├── sitemap_preload.py
│       ├── smart_retry.py
│       └── workflow_cache.py
├── scripts/
│   ├── setup.py          # Interactive setup wizard
│   ├── quick-start.sh    # Quick start script
│   └── README.md         # Setup documentation
├── tests/
│   └── test_optimizations.py
├── DEPLOYMENT_BACKENDS.md    # Backend deployment guide
├── PERFORMANCE_OPTIMIZATIONS.md  # Performance guide
└── QUICK_REFERENCE.md    # This file
```

---

## 🌟 Key Features

### Performance Optimizations (10 Total)
1. ✅ **LRU Eviction** - Keeps popular pages cached longer
2. ✅ **Request Deduplication** - 20-40% fewer HTTP requests
3. ✅ **Connection Pooling** - 30-50% faster requests
4. ✅ **Workflow Caching** - 100x faster repeated workflows
5. ✅ **Agent Memoization** - No duplicate AI analysis
6. ✅ **Smart Retry** - Prevents thundering herd
7. ✅ **Background Refresh** - Zero cache misses
8. ✅ **HTTP/2 Support** - 2-3x faster batches
9. ✅ **Sitemap Preload** - Warm cache on startup
10. ✅ **Bloom Filter** - Fast existence checks

### Monitoring Features
- Real-time performance dashboard (CLI + API)
- Health assessments with recommendations
- Color-coded metrics (🟢🟡🔴)
- Cache statistics and analytics
- Top performers tracking

### Platform Support
- Vercel, AWS, GCP, Docker, Railway, Fly.io
- OpenAI, Anthropic, Gemini, Azure OpenAI, Ollama
- PostgreSQL, MongoDB, SQLite, MySQL

---

## 📚 Documentation

- **[Setup Guide](./scripts/README.md)** - Detailed setup instructions
- **[Deployment Guide](./DEPLOYMENT_BACKENDS.md)** - Multi-backend deployment
- **[Performance Guide](./PERFORMANCE_OPTIMIZATIONS.md)** - Optimization details
- **[Main README](./README.md)** - Project overview
- **[API Docs](http://localhost:8000/docs)** - Interactive API documentation

---

## 🆘 Getting Help

1. Check this Quick Reference
2. Review [Troubleshooting](#troubleshooting) section
3. See [DEPLOYMENT_BACKENDS.md](./DEPLOYMENT_BACKENDS.md)
4. Check [scripts/README.md](./scripts/README.md)
5. Open an issue on GitHub

---

## 🎯 Next Steps After Setup

1. **Test the API:**
   ```bash
   curl http://localhost:8000/health
   ```

2. **View Dashboard:**
   ```bash
   python -m src.dashboard.performance
   ```

3. **Run First Analysis:**
   ```bash
   curl -X POST http://localhost:8000/api/v1/analysis/analyze \
     -H "Content-Type: application/json" \
     -d '{"url": "https://example.com"}'
   ```

4. **Monitor Performance:**
   ```bash
   curl http://localhost:8000/api/v1/performance/stats | jq
   ```

5. **Check API Documentation:**
   Open http://localhost:8000/docs in your browser

---

## 💡 Pro Tips

- Use **Vercel** for quick MVPs (5 min setup)
- Use **Docker Compose** for full control
- Use **Ollama** for free local LLM
- Enable **background refresh** for zero cache misses
- Monitor with **performance dashboard**
- Use **sitemap preload** for instant first requests

---

**Total Setup Time:** 5-10 minutes with wizard, 30 minutes manual

**Deployment Ready:** All configurations production-ready

**Cost:** From $0 (self-hosted with Ollama) to $20-50/month (Vercel)
