# Onboarding Guide - Getting Started in 5 Minutes

The AI SEO Agent includes an interactive onboarding system that asks questions and sets up your configuration automatically.

## Option 1: Interactive Setup (Recommended)

Run the setup wizard:

```bash
python -m src.cli_onboarding setup
```

The wizard will ask questions about:

1. **Site Type** - E-commerce, local business, content site, SaaS, etc.
2. **Basic Info** - Your domain and URL
3. **Competitors** - 3-5 main competitors to track
4. **Business Info** - Name, description, contact details
5. **Location** - Address (for local businesses)
6. **Author Info** - Default author credentials (for content sites)
7. **Social Profiles** - Facebook, Twitter, LinkedIn, etc.
8. **Target Queries** - Specific keywords to monitor
9. **Thresholds** - When to send alerts
10. **Options** - Analysis depth and settings

### Example Session

```
🚀 Starting AI SEO Agent setup wizard...

======================================================================
  AI SEO Agent - Workflow Configuration
======================================================================

What type of site are you setting up?

1. E-commerce / Online Store
2. Local Business (restaurant, shop, service)
3. Content / Blog / News Site
4. SaaS / Software Product
5. Corporate / Brand Site
6. Other

Enter your choice (1-6) [1]: 1

✓ Site type: Ecommerce

──────────────────────────────────────────────────────────────────────
BASIC INFORMATION
──────────────────────────────────────────────────────────────────────

Your domain (e.g., example.com): mystore.com
Full site URL [https://mystore.com]:

✓ Domain: mystore.com
✓ URL: https://mystore.com

──────────────────────────────────────────────────────────────────────
COMPETITORS (Recommended - enables competitive analysis)
──────────────────────────────────────────────────────────────────────

Do you want to track competitors? (y/n) [y]: y

Competitor #1 domain (or Enter to finish): competitor1.com
  Priority for competitor1.com (high/medium/low) [high]: high

Competitor #2 domain (or Enter to finish): competitor2.com
  Priority for competitor2.com (high/medium/low) [high]: medium

Competitor #3 domain (or Enter to finish):

✓ Added 2 competitors

[... continues with more questions ...]

======================================================================
  CONFIGURATION SUMMARY
======================================================================

📍 Domain: mystore.com
🔗 URL: https://mystore.com
🎯 Competitors: 2
   - competitor1.com (high priority)
   - competitor2.com (medium priority)
🏢 Business: My Store

⚡ Analysis Depth: standard
📅 Lookback: 30 days

======================================================================
✅ Configuration complete!
======================================================================

💾 Configuration saved to: ~/.seo-agent/workflow-config.json
📝 Config name: 'default'

📋 Recommended workflows for your site:

  • Full Audit: Monthly comprehensive review
  • Content Analysis: Product content optimization
  • Competitive Analysis: Track competitors
  • Quick Check: Daily monitoring

✨ Setup complete! You're ready to run workflows.

Next steps:
  1. Test your config: python -m src.cli_onboarding test
  2. Run a workflow: python -m src.cli run-workflow full_audit --config default
```

## Option 2: Quick Setup

For fast non-interactive setup:

```bash
# Basic
python -m src.cli_onboarding quick mystore.com

# With competitors
python -m src.cli_onboarding quick mystore.com \
  --competitors "competitor1.com,competitor2.com" \
  --business "My Store"

# With custom name
python -m src.cli_onboarding quick mystore.com \
  --competitors "competitor1.com,competitor2.com" \
  --business "My Store" \
  --name production
```

## Option 3: API-Based Onboarding

For web applications, use the REST API:

### Get Onboarding Questions

```bash
curl https://your-api.com/api/v1/onboarding/questions
```

Returns structured questions for building a web form.

### Quick Setup via API

```bash
curl -X POST "https://your-api.com/api/v1/onboarding/quick-setup" \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "mystore.com",
    "competitors": ["competitor1.com", "competitor2.com"],
    "business_name": "My Store"
  }'
```

### Save Full Configuration

```bash
curl -X POST "https://your-api.com/api/v1/onboarding/configs" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "production",
    "config": {
      "targets": {
        "primary_domain": "mystore.com",
        "property_url": "https://mystore.com",
        "competitors": [
          {"domain": "competitor1.com", "priority": "high"}
        ]
      },
      "business_info": {
        "name": "My Store",
        "url": "https://mystore.com",
        "description": "Leading widget retailer"
      }
    }
  }'
```

## Managing Configurations

### List All Configurations

```bash
python -m src.cli_onboarding list
```

Or via API:
```bash
curl https://your-api.com/api/v1/onboarding/configs
```

### View Configuration Details

```bash
# Summary format
python -m src.cli_onboarding show default

# JSON format
python -m src.cli_onboarding show default --format json

# YAML format (requires pyyaml)
python -m src.cli_onboarding show default --format yaml
```

Or via API:
```bash
curl https://your-api.com/api/v1/onboarding/configs/default
```

### Test Configuration

Validates configuration and shows what features are enabled:

```bash
python -m src.cli_onboarding test default
```

```
🧪 Testing configuration: default

✅ Configuration is valid

📊 Feature Availability:

  ✅ Traffic Monitoring
  ✅ Technical SEO Audit
  ✅ SERP Analysis
  ✅ Competitor Analysis
  ✅ Citation Tracking
  ⊘  Local SEO
  ✅ E-E-A-T Analysis
  ✅ Author Schema
  ⊘  LocalBusiness Schema
  ✅ Organization Schema
  ✅ Social Signals

💡 Recommendations:

  • Add business address for local SEO features
```

Or via API:
```bash
curl -X POST "https://your-api.com/api/v1/onboarding/configs/default/validate"
```

### Delete Configuration

```bash
# With confirmation
python -m src.cli_onboarding delete old-config

# Skip confirmation
python -m src.cli_onboarding delete old-config --yes
```

Or via API:
```bash
curl -X DELETE "https://your-api.com/api/v1/onboarding/configs/old-config"
```

## Configuration Files

Configurations are saved to:

```
~/.seo-agent/workflow-config.json
```

Format:
```json
{
  "default": {
    "targets": {
      "primary_domain": "mystore.com",
      "property_url": "https://mystore.com",
      "competitors": [...]
    },
    "business_info": {...},
    "default_author": {...},
    "thresholds": {...},
    "options": {...}
  },
  "production": {...},
  "staging": {...}
}
```

## Using Configurations with Workflows

After onboarding, use your configuration with workflows:

```bash
# Run workflow with saved config
python -m src.cli run-workflow full_audit --config default

# Or via API
curl -X POST "https://your-api.com/api/v1/workflows/full_audit/run" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_input": <config from onboarding>
  }'
```

## Onboarding Flow by Site Type

### E-commerce Sites
**Questions focus on:**
- Product catalog
- Competitor tracking
- Author credentials for reviews
- Social proof

**Recommended workflows:**
- Full Audit (monthly)
- Content Analysis (weekly)
- Competitive Analysis (weekly)
- Quick Check (daily)

### Local Businesses
**Questions focus on:**
- Business address
- NAP (Name, Address, Phone)
- Google Business Profile
- Local citations

**Recommended workflows:**
- Local SEO (weekly)
- Quick Check (daily)
- Full Audit (monthly)

### Content/Blog Sites
**Questions focus on:**
- Author credentials
- E-E-A-T signals
- Content decay
- AI content detection

**Recommended workflows:**
- Content Analysis (weekly)
- AI Readiness (weekly)
- Full Audit (monthly)

### SaaS Products
**Questions focus on:**
- Technical SEO
- Competitor tracking
- Documentation
- Feature pages

**Recommended workflows:**
- Technical Analysis (weekly)
- AI Readiness (weekly)
- Competitive Analysis (weekly)

## Tips for Best Onboarding

1. **Be Comprehensive** - The more info you provide, the better the analysis
2. **Add Competitors** - Enables 40% more features
3. **Complete Business Info** - Critical for schema and local SEO
4. **Author Credentials** - Boosts E-E-A-T scoring significantly
5. **Social Profiles** - Validates authenticity and authority
6. **Realistic Thresholds** - Don't set too tight or you'll get alert fatigue

## What Happens Next?

After onboarding:

1. **Configuration Saved** - Stored in `~/.seo-agent/workflow-config.json`
2. **Validation** - Run `test` command to check setup
3. **Run Workflows** - Use recommended workflows for your site type
4. **Review Results** - Check recommendations and alerts
5. **Refine Config** - Update configuration based on learnings

## Getting Help

### View All CLI Commands
```bash
python -m src.cli_onboarding --help
```

### View Command Help
```bash
python -m src.cli_onboarding setup --help
python -m src.cli_onboarding quick --help
python -m src.cli_onboarding test --help
```

### API Documentation
```bash
# Start API server
uvicorn src.api.main:app --reload

# Visit interactive docs
http://localhost:8000/docs
```

Look for the "Onboarding" section in the API docs.

## Example: Complete Onboarding to First Workflow

```bash
# 1. Run onboarding
python -m src.cli_onboarding setup

# 2. Test configuration
python -m src.cli_onboarding test default

# 3. View recommended workflows
python -m src.cli_onboarding workflows

# 4. Run your first workflow
python -m src.cli run-workflow quick_check --config default

# 5. Review results
# (workflow returns recommendations and alerts)

# 6. Schedule regular runs
python -m src.cli schedule add \
  --workflow quick_check \
  --config default \
  --cron "0 9 * * *"  # Daily at 9am
```

## Programmatic Usage

For integration into other tools:

```python
from src.orchestrator import OnboardingFlow, ConfigManager

# Run interactive setup
flow = OnboardingFlow()
config = flow.start(interactive=True)

# Save it
manager = ConfigManager()
manager.save(config, "my-config")

# Load and use
config = manager.load("my-config")
params = config.to_params()

# Use with orchestrator
from src.orchestrator import AgentOrchestrator, get_workflow

orchestrator = AgentOrchestrator(context)
workflow = get_workflow("full_audit")
result = await orchestrator.run_workflow(workflow, params)
```

## Quick Reference

| Command | Purpose |
|---------|---------|
| `setup` | Interactive onboarding wizard |
| `quick <domain>` | Fast non-interactive setup |
| `list` | Show all saved configurations |
| `show <name>` | View configuration details |
| `test <name>` | Validate and check features |
| `delete <name>` | Remove configuration |
| `workflows` | List available workflows |

| API Endpoint | Purpose |
|--------------|---------|
| `GET /api/v1/onboarding/questions` | Get form questions |
| `POST /api/v1/onboarding/quick-setup` | Quick setup |
| `GET /api/v1/onboarding/configs` | List configs |
| `POST /api/v1/onboarding/configs` | Save config |
| `GET /api/v1/onboarding/configs/{name}` | Get config |
| `POST /api/v1/onboarding/configs/{name}/validate` | Test config |
| `DELETE /api/v1/onboarding/configs/{name}` | Delete config |
| `GET /api/v1/onboarding/recommendations/{site_type}` | Get workflow recommendations |
