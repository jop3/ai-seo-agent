# AI SEO Agent

AI-powered SEO optimization platform for the AI Overview era. Helps businesses diagnose, respond to, and stay ahead of traffic changes caused by Google's AI Overviews and prepare for the future of AI agent-driven search.

**🆓 Now with FREE local AI models** - Run 100% free using Docker Model Runner (no API costs!)

## ✨ Features

### 1. SEO Analysis
- **AI Overview Detection**: Identify which queries trigger AI Overviews
- **Citation Tracking**: Monitor if you're being cited in AI Overviews
- **Traffic Attribution**: Correlate traffic drops with AIO introduction
- **Query Classification**: Classify queries by intent and AIO risk

### 2. Agent Simulator
- **Page Interpretation**: Test how AI agents understand your pages
- **Checkout Flow Testing**: Verify AI agents can complete purchases
- **Schema Validation**: Validate and improve structured data
- **Competitive Analysis**: Compare agent-friendliness vs competitors

### 3. Monitoring & Alerts
- **Traffic Anomaly Detection**: Real-time alerts for significant drops
- **AIO Status Changes**: Notifications when AIOs appear/change
- **Algorithm Update Tracking**: Stay informed about Google updates
- **Microsoft Teams Integration**: Alerts delivered to your team

### 4. Optimization Engine
- **Schema Generation**: Auto-generate optimized JSON-LD markup
- **FAQ Creation**: Generate FAQs targeting your queries
- **Content Recommendations**: AI-powered content optimization
- **Bulk Processing**: Optimize many pages at once

### 5. Performance Optimizations (40-60% Faster)
- **LRU Cache Eviction**: Keep popular pages cached
- **Request Deduplication**: Prevent duplicate API calls
- **HTTP Connection Pooling**: Reuse connections, HTTP/2 support
- **Workflow Result Caching**: Cache analysis results
- **Agent Memoization**: Remember agent outputs
- **Smart Retry with Jitter**: Prevent thundering herd
- **Background Cache Refresh**: Proactive cache warming
- **Bloom Filters**: Fast cache lookups
- **Sitemap Preloading**: Auto-discover and cache pages

### 6. Multi-Framework Agent Support

Choose the agent framework that best fits your needs - all with the same unified API:

| Framework | Best For | Platform |
|-----------|----------|----------|
| **Direct LLM** | Simple workflows, rapid prototyping | Any |
| **Google ADK** | Google Cloud users, Gemini models | Vertex AI |
| **LangGraph** | Complex state management, graphs | LangGraph Cloud |
| **Microsoft Agent** | Enterprise, Azure users | Azure |
| **AWS Bedrock** | AWS users, production scale | AWS |
| **CrewAI** | Role-based collaboration | Docker/K8s |

**Unified API Example:**

```python
from src.frameworks import get_framework, FrameworkType, AgentConfig

# Switch frameworks by changing just one line!
framework = get_framework(FrameworkType.GOOGLE_ADK)  # or LANGGRAPH, CREWAI, etc.

agent = framework.create_agent(AgentConfig(
    name="SEO Analyzer",
    role="analyst",
    goal="Analyze SEO performance"
))

result = framework.execute_agent(agent, {"description": "Analyze example.com"})
```

See [Framework Examples](/examples/frameworks/) and [Deployment Guides](/docs/deployment/FRAMEWORK_DEPLOYMENT.md) for details.

## 🚀 Getting Started

Choose your deployment path based on your needs:

```
┌─────────────────────────────────────────────────────────────┐
│                 Choose Your Setup Path                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │  What's your goal?  │
                    └─────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
  │   Testing   │     │ Development │     │ Production  │
  │ Quick Start │     │   & Teams   │     │ Enterprise  │
  └─────────────┘     └─────────────┘     └─────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
  Docker Model         Docker Model         Azure / AWS
  Runner (FREE)        Runner (FREE)        (Scalable)
  5 min setup          10 min setup         30 min setup
```

### Option 1: 🆓 Docker Model Runner (Recommended for Getting Started)

**100% Free • 100% Local • No API Keys Needed • 5 Minutes**

Perfect for testing, development, and small-scale production.

```bash
# 1. Clone the repository
git clone https://github.com/your-org/ai-seo-agent.git
cd ai-seo-agent

# 2. Run the interactive setup wizard
python3 scripts/setup.py

# Choose:
# - Platform: Docker Compose
# - LLM Provider: Docker Model Runner
# - Model: (wizard will recommend based on your hardware)

# 3. Start everything
docker-compose up -d

# 4. Access your API
open http://localhost:8000/docs
```

**What you get:**
- ✅ Local AI model (Phi-3, Llama 3.2, or SmolLM2)
- ✅ PostgreSQL database
- ✅ Redis cache
- ✅ OpenAI-compatible API
- ✅ Zero API costs
- ✅ Full privacy (data never leaves your machine)

**Requirements:**
- Docker Desktop 4.41+ (includes Model Runner)
- 4GB+ RAM (8GB recommended)
- 10GB free disk space

See [Docker Model Runner Guide](DOCKER_MODEL_RUNNER.md) for details.

### Option 2: ☁️ Cloud Deployment (Production)

**For:** Production workloads, enterprise scale, team collaboration

Choose from **7 deployment platforms**:

```bash
# Run interactive setup
python3 scripts/setup.py

# Choose your platform:
# 1. Azure - Full enterprise features
# 2. Vercel - Instant deployment
# 3. AWS - Maximum control
# 4. Google Cloud - AI/ML integration
# 5. Railway - Simple PaaS
# 6. Fly.io - Global edge
# 7. Docker Compose - Self-hosted
```

See deployment guides:
- [Azure Deployment Guide](AZURE_DEPLOYMENT.md) - Complete Azure setup with OpenAI, Cosmos DB
- [Multi-Platform Guide](DEPLOYMENT_BACKENDS.md) - Vercel, AWS, GCP, and others

## 📊 Deployment Options Comparison

| Platform | Cost/Month | Setup Time | Difficulty | Best For | LLM Options |
|----------|------------|------------|------------|----------|-------------|
| **Docker Model Runner** | **$0** | 5 min | ⭐ Easy | Testing, dev, small prod | Local models (free) |
| **Vercel** | $20-200 | 5 min | ⭐ Easy | Quick MVP, serverless | Cloud APIs |
| **Railway** | $5-100 | 5 min | ⭐ Easy | Simple deployment | Cloud APIs |
| **Docker Self-Hosted** | $10-50 | 10 min | ⭐⭐ Medium | Full control | Local or cloud |
| **Fly.io** | $10-100 | 15 min | ⭐⭐ Medium | Global edge deployment | Cloud APIs |
| **Azure** | $92-340 | 20 min | ⭐⭐⭐ Advanced | Enterprise, integrated AI | Azure OpenAI |
| **AWS** | $100-500 | 30 min | ⭐⭐⭐ Advanced | Maximum control | Any API |
| **Google Cloud** | $100-500 | 30 min | ⭐⭐⭐ Advanced | AI/ML integration | Gemini, Vertex AI |

**Cost Savings with Docker Model Runner:**
- OpenAI GPT-4o: **$50-500/month** → **$0** (Docker Model Runner)
- Anthropic Claude: **$60-600/month** → **$0** (Docker Model Runner)
- **Save $600-6000/year!**

## 🤖 LLM Model Comparison (Docker Model Runner)

Check what your system can run:

```bash
python3 scripts/analyze_hardware.py
```

### Available Models

| Model | Size | RAM | Speed | Quality | Best For |
|-------|------|-----|-------|---------|----------|
| **SmolLM2 135M** | 135M | 1GB | ⚡⚡⚡ Very Fast | ⭐⭐ Good | Quick testing |
| **SmolLM2 360M** | 360M | 2GB | ⚡⚡⚡ Very Fast | ⭐⭐⭐ Better | Development |
| **Llama 3.2 1B** | 1B | 2GB | ⚡⚡⚡ Very Fast | ⭐⭐⭐ Better | Fast responses |
| **Phi-3 Mini** ⭐ | 3.8B | 4GB | ⚡⚡ Fast | ⭐⭐⭐⭐ Great | **Recommended** |
| **Llama 3.2 3B** | 3B | 4GB | ⚡⚡ Fast | ⭐⭐⭐⭐ Great | Balanced |
| **Gemma 2 2B** | 2B | 3GB | ⚡⚡ Fast | ⭐⭐⭐ Better | Google model |

**Recommendation by System:**
- **2-4GB RAM**: SmolLM2 360M, Llama 3.2 1B
- **4-8GB RAM**: Phi-3 Mini ⭐, Llama 3.2 3B (best balance)
- **8GB+ RAM**: Any model, consider larger models for best quality

**With GPU (5-10x faster):**
- Enable in `docker-compose.yml` (see GPU Setup below)
- Requires NVIDIA GPU with CUDA support

## 🎯 Quick Start Examples

### Example 1: Analyze Your Website (Local AI)

```bash
# 1. Set up with Docker Model Runner
python3 scripts/setup.py  # Choose Docker + Model Runner

# 2. Start everything
docker-compose up -d

# 3. Analyze your site
curl -X POST http://localhost:8000/api/v1/analysis/full \
  -H "Content-Type: application/json" \
  -d '{"domain": "example.com", "limit": 100}'

# 4. Check for AI Overviews
curl -X POST http://localhost:8000/api/v1/analysis/aio-check \
  -d '{"queries": ["best pizza near me", "how to tie a tie"]}'
```

### Example 2: Test Page Agent-Friendliness

```bash
curl -X POST http://localhost:8000/api/v1/agents/interpret-page \
  -d '{"url": "https://example.com/product/123"}'
```

### Example 3: Generate Optimized Schema

```bash
curl -X POST http://localhost:8000/api/v1/optimizations/generate-schema \
  -d '{"url": "https://example.com/article", "type": "Article"}'
```

## 🖥️ Hardware Analysis & Model Selection

Before setup, check your system capabilities:

```bash
# Analyze your hardware
python3 scripts/analyze_hardware.py
```

**Output:**
```
System Analysis
 Platform         Linux
 CPU Cores        8
 Total RAM        16.0 GB
 Available RAM    12.0 GB
 GPU              ✅ NVIDIA RTX 3080
 GPU Memory       10.0 GB

Model Recommendations

⚡ Fast Models - Quick responses, good for development
┌─────────────────────┬──────────────────┬─────────────┬─────────────┬───────┐
│ Model               │ Provider         │ Speed       │ Quality     │ RAM   │
├─────────────────────┼──────────────────┼─────────────┼─────────────┼───────┤
│ SmolLM2 360M        │ Docker Model     │ ⚡⚡⚡ Very│ ⭐⭐⭐      │ 2.0   │
│                     │ Runner           │ Fast        │ Better      │ GB    │
│ Llama 3.2 1B        │ Docker Model     │ ⚡⚡⚡ Very│ ⭐⭐⭐      │ 2.0   │
│                     │ Runner           │ Fast        │ Better      │ GB    │
└─────────────────────┴──────────────────┴─────────────┴─────────────┴───────┘

⚖️  Balanced Models (Recommended)
┌─────────────────────┬──────────────────┬─────────────┬─────────────┬───────┐
│ Phi-3 Mini          │ Docker Model     │ ⚡⚡ Fast   │ ⭐⭐⭐⭐    │ 4.0   │
│                     │ Runner           │             │ Great       │ GB    │
│ Llama 3.2 3B        │ Docker Model     │ ⚡⚡ Fast   │ ⭐⭐⭐⭐    │ 4.0   │
│                     │ Runner           │             │ Great       │ GB    │
└─────────────────────┴──────────────────┴─────────────┴─────────────┴───────┘

Recommendation: Your system can run high-quality models!
```

## 🎮 GPU Acceleration Setup

**5-10x faster inference with NVIDIA GPU**

If you have an NVIDIA GPU, enable GPU acceleration:

### 1. Check GPU Support

```bash
# Check if GPU is available
nvidia-smi
```

### 2. Enable in docker-compose.yml

Uncomment the GPU section:

```yaml
services:
  llm:
    image: ai/phi3-mini-4k-instruct
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

### 3. Restart Services

```bash
docker-compose down
docker-compose up -d
```

### 4. Verify GPU Usage

```bash
# Monitor GPU usage
nvidia-smi -l 1

# Check model logs
docker-compose logs -f llm
```

**Performance Impact:**
- CPU-only: ~2-5 seconds per request
- With GPU: ~0.3-1 second per request
- **5-10x speedup** 🚀

## 🔄 Migration Guide: Cloud → Local Models

Already using OpenAI or other cloud providers? Migrate to local models:

### Step 1: Test Locally First

```bash
# Set up Docker Model Runner
python3 scripts/setup.py  # Choose Docker + Model Runner
docker-compose up -d

# Test an endpoint
curl http://localhost:8000/api/v1/analysis/full \
  -d '{"domain": "example.com", "limit": 10}'
```

### Step 2: Compare Results

```bash
# Run same analysis with both providers
# OpenAI (current):
OPENAI_API_KEY=sk-... python test_analysis.py

# Local model:
OPENAI_API_BASE=http://localhost:8080/v1 python test_analysis.py
```

### Step 3: Gradual Migration

```yaml
# Option 1: Hybrid setup (cost optimization)
# Use local models for dev/testing
# Use cloud models for production

# Option 2: Full migration
# Switch docker-compose.yml to use local model
# Update .env to point to local endpoint
```

### Step 4: Monitor Performance

```bash
# Check performance dashboard
curl http://localhost:8000/api/v1/performance/stats
```

**Quality Comparison:**
- **GPT-4o**: ⭐⭐⭐⭐⭐ (excellent, expensive)
- **Claude 3.5**: ⭐⭐⭐⭐⭐ (excellent, expensive)
- **Phi-3 Mini**: ⭐⭐⭐⭐ (great, free)
- **Llama 3.2 3B**: ⭐⭐⭐⭐ (great, free)

**When to use cloud vs local:**
- **Cloud (GPT-4o, Claude)**: Critical analysis, best quality needed, low volume
- **Local (Phi-3, Llama)**: Development, testing, high volume, cost-sensitive

## 📖 Architecture

### Local Development (Docker Model Runner)

```
┌─────────────────────────────────────────────────────────────┐
│                      Your Computer                          │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────────┐│
│  │ API Server  │  │ Local LLM   │  │ PostgreSQL + Redis   ││
│  │ :8000       │  │ (Phi-3)     │  │ (Data + Cache)       ││
│  └──────┬──────┘  └──────┬──────┘  └──────────┬───────────┘│
│         │                │                    │            │
│         └────────────────┼────────────────────┘            │
│                          ▼                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              AI SEO Agent Core                        │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────┐  │  │
│  │  │ SEO        │  │ Agent      │  │ Optimizer      │  │  │
│  │  │ Analyst    │  │ Tester     │  │ Agent          │  │  │
│  │  └────────────┘  └────────────┘  └────────────────┘  │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Integrations (Optional)                  │  │
│  │  GSC API │ SERP APIs │ CMS │ Teams                    │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Production (Azure)

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Azure Cloud                                  │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────────────┐ │
│  │ Container Apps  │  │ Azure OpenAI    │  │ Cosmos DB            │ │
│  │ (API + Worker)  │  │ (GPT-4o)        │  │ (Serverless)         │ │
│  └────────┬────────┘  └────────┬────────┘  └──────────┬───────────┘ │
│           │                    │                      │             │
│           └────────────────────┼──────────────────────┘             │
│                                ▼                                    │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    AI SEO Agent Core                          │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐  │   │
│  │  │ SEO Analyst  │  │ Agent Tester │  │ Optimizer Agent    │  │   │
│  │  └──────────────┘  └──────────────┘  └────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    Integrations                                │  │
│  │  GSC API │ SERP APIs │ Optimizely CMS │ Microsoft Teams       │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

## 📡 API Endpoints

### Performance Monitoring
- `GET /api/v1/performance/stats` - View all optimization statistics
- `GET /api/v1/performance/health` - Health check and recommendations
- `GET /api/v1/performance/cache/stats` - Cache performance
- `GET /api/v1/performance/dedup/stats` - Request deduplication stats
- `POST /api/v1/performance/cache/clear` - Clear all caches
- `POST /api/v1/performance/cleanup` - Clean expired cache entries

### Analysis
- `POST /api/v1/analysis/full` - Run comprehensive SEO analysis
- `POST /api/v1/analysis/aio-check` - Check queries for AI Overviews
- `POST /api/v1/analysis/traffic-drops` - Analyze traffic changes
- `POST /api/v1/analysis/classify-queries` - Classify query intent

### Agents
- `POST /api/v1/agents/interpret-page` - AI agent page interpretation
- `POST /api/v1/agents/test-checkout` - Test checkout flow
- `POST /api/v1/agents/validate-schema` - Validate schema markup
- `POST /api/v1/agents/competitive-test` - Compare vs competitors
- `POST /api/v1/agents/monitoring/run-cycle` - Run monitoring checks

### Optimizations
- `POST /api/v1/optimizations/recommendations` - Generate recommendations
- `POST /api/v1/optimizations/generate-schema` - Generate schema markup
- `POST /api/v1/optimizations/generate-faq` - Generate FAQ content
- `POST /api/v1/optimizations/optimize-for-query` - Optimize for specific query

### Webhooks
- `POST /api/v1/webhooks/scheduled-task` - Trigger scheduled tasks
- `POST /api/v1/webhooks/test-teams` - Test Teams integration

## 🛠️ Configuration

### Docker Model Runner (Local)

```bash
# .env file (generated by setup wizard)
OPENAI_API_BASE=http://llm:8080/v1
OPENAI_API_KEY=not-needed
# Model: ai/phi3-mini-4k-instruct

POSTGRES_URL=postgresql://postgres:postgres@db:5432/seoagent
REDIS_URL=redis://redis:6379/0
```

### Cloud Providers

#### OpenAI
```bash
OPENAI_API_KEY=sk-...
```

#### Anthropic Claude
```bash
ANTHROPIC_API_KEY=sk-ant-...
```

#### Azure OpenAI
```bash
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_DEPLOYMENT=gpt-4o
```

#### Google Gemini
```bash
GOOGLE_AI_API_KEY=...
```

### Recommended Integrations
- `GSC_CREDENTIALS_PATH` - Google Search Console service account JSON
- `GSC_PROPERTY_URL` - Your website property URL in GSC
- `TEAMS_WEBHOOK_URL` - Microsoft Teams webhook for alerts

### Optional
- `SERP_PROVIDER` - SERP data provider (serpapi, dataforseo, scraper)
- `SERP_API_KEY` - SERP API credentials
- `OPTIMIZELY_API_KEY` - Optimizely CMS API key

## 📚 Documentation

- **[Docker Model Runner Guide](DOCKER_MODEL_RUNNER.md)** - Complete guide to free local AI models
- **[Azure Deployment Guide](AZURE_DEPLOYMENT.md)** - Deploy to Azure with OpenAI
- **[Multi-Platform Guide](DEPLOYMENT_BACKENDS.md)** - Vercel, AWS, GCP deployment
- **[Performance Optimizations](PERFORMANCE_OPTIMIZATIONS.md)** - 40-60% performance gains
- **[Quick Reference](QUICK_REFERENCE.md)** - Common commands and troubleshooting

## 🧪 Using the CLI

```bash
# Check configuration
seo-agent config

# Analyze your hardware for model selection
python3 scripts/analyze_hardware.py

# Run interactive setup
python3 scripts/setup.py

# View performance dashboard
python3 src/dashboard/performance.py

# Run full SEO analysis
seo-agent analyze --full --limit 500

# Check specific queries for AI Overviews
seo-agent analyze -q "ibuprofen dosage" -q "pharmacy near me"

# Test a page for agent-friendliness
seo-agent test-page https://www.example.com/product/item-123/
```

## 🚀 Deployment

### Quick Deployment with Setup Wizard

```bash
# Interactive setup for any platform
python3 scripts/setup.py
```

**Platforms supported:**
1. **Azure** - Full enterprise deployment with automated script
2. **Vercel** - One-command deployment
3. **AWS** - ECS/Fargate deployment
4. **Google Cloud** - Cloud Run deployment
5. **Docker Compose** - Self-hosted deployment
6. **Railway** - Simple PaaS deployment
7. **Fly.io** - Global edge deployment

### Azure Automated Deployment

```bash
# Run automated Azure deployment
./scripts/azure-deploy.sh

# Or deploy manually (see AZURE_DEPLOYMENT.md)
```

### Other Platforms

See platform-specific guides in [DEPLOYMENT_BACKENDS.md](DEPLOYMENT_BACKENDS.md).

## 💰 Cost Comparison

### Monthly Costs by Deployment Option

| Setup | Platform | LLM | Database | Total/Month | Requests/Month |
|-------|----------|-----|----------|-------------|----------------|
| **Free Tier** | Docker (local) | Free (Phi-3) | Free (local) | **$0** | Unlimited |
| **Startup** | Vercel | OpenAI ($50) | Vercel Postgres ($20) | **$70** | ~100K |
| **Professional** | Azure | Azure OpenAI ($200) | Cosmos DB ($92) | **$292** | ~500K |
| **Enterprise** | Azure | Azure OpenAI ($500) | Cosmos DB ($300) | **$800** | ~2M |

**Cost Savings:**
- Docker Model Runner saves **$70-800/month** vs cloud
- Annual savings: **$840-9,600**
- No vendor lock-in - switch anytime

## 🧪 Testing

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests (53 tests)
pytest tests/ -v

# Run specific test suites
pytest tests/test_optimizations.py -v
pytest tests/test_hardware_analysis.py -v
pytest tests/test_setup_wizard.py -v
pytest tests/test_docker_validation.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

**Test Coverage:**
- 21 optimization tests (LRU, deduplication, connection pool, etc.)
- 10 hardware analysis tests (model recommendations)
- 11 setup wizard integration tests
- 11 Docker validation tests
- **100% pass rate (53/53 tests passing)**

## 🗺️ Roadmap

### Completed ✅
- [x] Core SEO analysis
- [x] AI Overview detection
- [x] Agent simulator
- [x] Teams integration
- [x] Azure deployment
- [x] **Docker Model Runner integration (FREE local AI)**
- [x] **Multi-platform deployment support (7 platforms)**
- [x] **Performance optimizations (40-60% faster)**
- [x] **Interactive setup wizard**
- [x] **Hardware-aware model selection**
- [x] **Comprehensive test coverage**

### Planned 🚧
- [ ] Multi-tenant support
- [ ] Dashboard UI
- [ ] Scheduled reports
- [ ] A/B testing integration
- [ ] Voice search optimization
- [ ] Real-time monitoring dashboard
- [ ] Browser extension for quick analysis
- [ ] WordPress plugin
- [ ] Shopify app

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🙋 Support & Community

- 📖 **Documentation**: See guides in repository
- 🐛 **Bug Reports**: Open an issue on GitHub
- 💡 **Feature Requests**: Open an issue with enhancement label
- 💬 **Discussions**: GitHub Discussions

## ⭐ Star History

If you find this project helpful, please consider giving it a star!

---

**Made with ❤️ for the SEO community**
