# AI SEO Agent

AI-powered SEO optimization platform for the AI Overview era. Helps businesses diagnose, respond to, and stay ahead of traffic changes caused by Google's AI Overviews and prepare for the future of AI agent-driven search.

## Features

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

## Architecture

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

## Quick Start

### Prerequisites
- Python 3.11+
- Docker (optional, for containerized deployment)
- Azure subscription (for production deployment)

### Local Development

1. Clone and install:
```bash
git clone https://github.com/your-org/ai-seo-agent.git
cd ai-seo-agent
pip install -e ".[dev]"
```

2. Configure environment:
```bash
cp .env.example .env
# Edit .env with your credentials
```

3. Run the API:
```bash
# Using CLI
seo-agent serve --reload

# Or using Docker
docker-compose up
```

4. Access the API:
- API: http://localhost:8000
- Docs: http://localhost:8000/docs

### Using the CLI

```bash
# Check configuration
seo-agent config

# Run full SEO analysis
seo-agent analyze --full --limit 500

# Check specific queries for AI Overviews
seo-agent analyze -q "ibuprofen dosage" -q "pharmacy near me"

# Test a page for agent-friendliness
seo-agent test-page https://www.example.com/product/item-123/
```

## API Endpoints

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

## Configuration

### Required
- `AZURE_OPENAI_ENDPOINT` - Azure OpenAI endpoint
- `AZURE_OPENAI_API_KEY` - Azure OpenAI API key
- `AZURE_OPENAI_DEPLOYMENT` - Model deployment name (default: gpt-4o)

### Recommended
- `GSC_CREDENTIALS_PATH` - Path to Google Search Console service account JSON
- `GSC_PROPERTY_URL` - Your website property URL in GSC
- `TEAMS_WEBHOOK_URL` - Microsoft Teams webhook for alerts

### Optional
- `SERP_PROVIDER` - SERP data provider (serpapi, dataforseo, scraper)
- `SERP_API_KEY` - SERP API credentials
- `OPTIMIZELY_API_KEY` - Optimizely CMS API key

## Deployment to Azure

### 1. Deploy Infrastructure

```bash
# Login to Azure
az login

# Deploy infrastructure
az deployment sub create \
  --location swedencentral \
  --template-file infra/main.bicep \
  --parameters infra/parameters/dev.bicepparam
```

### 2. Configure Secrets

```bash
# Add secrets to Key Vault
az keyvault secret set --vault-name kv-ai-seo-agent-dev --name "azure-openai-key" --value "your-key"
az keyvault secret set --vault-name kv-ai-seo-agent-dev --name "teams-webhook-url" --value "your-webhook"
```

### 3. Deploy Application

```bash
# Build and push container images
az acr build --registry craiseoagentdev --image ai-seo-agent-api:latest .
az acr build --registry craiseoagentdev --image ai-seo-agent-worker:latest -f Dockerfile.worker .

# Update Container Apps (handled by CI/CD)
```

## Cost Estimation (Azure)

| Tier | Monthly Cost | Use Case |
|------|-------------|----------|
| MVP | ~$200-500 | Development, small sites |
| Production | ~$500-1,500 | Medium traffic, daily monitoring |
| Scale | $2,000+ | Large sites, real-time monitoring |

Main cost drivers:
- Azure OpenAI tokens
- Container Apps compute time
- Cosmos DB request units

## Roadmap

- [x] Core SEO analysis
- [x] AI Overview detection
- [x] Agent simulator
- [x] Teams integration
- [x] Azure deployment
- [ ] Multi-tenant support
- [ ] Dashboard UI
- [ ] Scheduled reports
- [ ] A/B testing integration
- [ ] Voice search optimization
- [ ] Real-time monitoring

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.
