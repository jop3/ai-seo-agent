# Workflow Orchestrator Guide

The Agent Orchestrator coordinates all 17 SEO agents to deliver comprehensive analysis with proper dependency management, parallel execution, and unified reporting.

## Quick Start

### Minimal Configuration

The simplest way to run a workflow:

```python
from src.orchestrator import AgentOrchestrator, get_workflow, create_minimal_config

# Create minimal config
config = create_minimal_config(
    domain="example.com",
    property_url="https://example.com"
)

# Get workflow
workflow = get_workflow("quick_check")

# Run it
orchestrator = AgentOrchestrator(context)
result = await orchestrator.run_workflow(workflow, config.to_params())
```

### Full Configuration

For complete control:

```python
from src.orchestrator import AgentOrchestrator, WorkflowInput, WorkflowTargets, BusinessInfo

# Define what to analyze
targets = WorkflowTargets(
    primary_domain="mystore.com",
    property_url="https://mystore.com",
    competitors=[
        {"domain": "competitor1.com", "priority": "high"},
        {"domain": "competitor2.com", "priority": "medium"},
    ],
    target_queries=["best widgets", "buy widgets online"],
    query_limit=200,
    max_pages=5000,
)

# Business context
business_info = BusinessInfo(
    name="My Store",
    url="https://mystore.com",
    description="Leading online store for widgets",
    phone="+1-555-0100",
    street_address="123 Main St",
    city="San Francisco",
    state="CA",
    postal_code="94102",
    country="US",
)

# Complete input
workflow_input = WorkflowInput(
    targets=targets,
    business_info=business_info,
)

# Run full audit
workflow = get_workflow("full_audit")
result = await orchestrator.run_workflow(workflow, workflow_input.to_params())
```

## Required Configuration

### 1. **Domain Information** (REQUIRED)
```python
targets = WorkflowTargets(
    primary_domain="example.com",      # Your domain
    property_url="https://example.com" # Full URL
)
```

### 2. **Competitors** (Recommended)
```python
competitors=[
    CompetitorConfig(
        domain="competitor1.com",
        name="Competitor A",
        priority="high"  # high, medium, low
    ),
    CompetitorConfig(
        domain="competitor2.com",
        name="Competitor B",
        priority="medium"
    ),
]
```

### 3. **Business Information** (Recommended for Local SEO)
```python
business_info = BusinessInfo(
    # Required
    name="Business Name",
    url="https://example.com",

    # Highly Recommended
    description="What your business does",
    phone="+1-555-0100",

    # For Local SEO
    street_address="123 Main St",
    city="San Francisco",
    state="CA",
    postal_code="94102",
    country="US",
    latitude=37.7749,
    longitude=-122.4194,

    # For Schema & E-E-A-T
    logo_url="https://example.com/logo.png",
    publisher_logo_url="https://example.com/publisher-logo.png",

    # Social signals
    facebook_url="https://facebook.com/mybusiness",
    twitter_url="https://twitter.com/mybusiness",
    linkedin_url="https://linkedin.com/company/mybusiness",
)
```

### 4. **Author Information** (Recommended for Content/E-E-A-T)
```python
default_author = AuthorInfo(
    name="John Smith",
    url="https://example.com/authors/john-smith",
    email="john@example.com",
    bio="Senior content expert with 10 years experience",
    credentials=[
        "Certified Expert",
        "Published Author",
        "Industry Speaker"
    ],
    social_profiles={
        "twitter": "https://twitter.com/johnsmith",
        "linkedin": "https://linkedin.com/in/johnsmith"
    }
)
```

### 5. **Target Queries** (Optional - uses GSC top queries if empty)
```python
targets = WorkflowTargets(
    # ... other fields ...
    target_queries=[
        "primary keyword",
        "secondary keyword",
        "brand keyword"
    ],
    query_limit=100  # If target_queries empty, fetch top N from GSC
)
```

### 6. **Thresholds** (Optional - sensible defaults provided)
```python
thresholds = WorkflowThresholds(
    traffic_drop_threshold_pct=30.0,    # Alert if traffic drops >30%
    content_decay_days=90,               # Flag content declining for 90+ days
    min_eeat_score=60.0,                # Alert if E-E-A-T score < 60
    ranking_drop_threshold=5,            # Alert if position drops >5
    min_mobile_score=90,                 # Alert if mobile score < 90
)
```

## Available Workflows

### 1. **Full Audit** (`full_audit`)
Comprehensive monthly review using 12 agents in 5 phases.

**Best for:** Monthly reviews, major site changes, recovery plans
**Duration:** 15-30 minutes
**Agents:** All agents in optimized order

```python
workflow = get_workflow("full_audit")
```

### 2. **Quick Check** (`quick_check`)
Fast daily health check.

**Best for:** Daily monitoring, CI/CD pipelines
**Duration:** 3-5 minutes
**Agents:** Monitoring, SERP Features, Technical (critical only)

```python
workflow = get_workflow("quick_check")
```

### 3. **Content Analysis** (`content`)
Deep content review for content teams.

**Best for:** Content audits, refresh planning
**Duration:** 10-15 minutes
**Agents:** Content Decay, E-E-A-T, AI Content, Schema, Content Generator

```python
workflow = get_workflow("content")
```

### 4. **Technical Analysis** (`technical`)
Technical SEO audit for dev teams.

**Best for:** Pre-launch checks, technical debt assessment
**Duration:** 10-20 minutes
**Agents:** Technical SEO, Link Analysis, Schema, Multi-Platform

```python
workflow = get_workflow("technical")
```

### 5. **Competitive Analysis** (`competitive`)
Competitor deep-dive.

**Best for:** Competitive research, gap analysis
**Duration:** 10-15 minutes
**Agents:** Competitor Monitor, SERP Features, Link Analysis, Multi-Engine

```python
workflow = get_workflow("competitive")
```

### 6. **Local SEO** (`local_seo`)
Local business optimization.

**Best for:** Local businesses, multi-location brands
**Duration:** 5-10 minutes
**Agents:** Local SEO, Schema (LocalBusiness)

**Requires:** `business_info` with address details

```python
workflow = get_workflow("local_seo")
```

### 7. **AI Readiness** (`ai_readiness`)
Optimize for AI-powered search.

**Best for:** AI Overview optimization, future-proofing
**Duration:** 10-15 minutes
**Agents:** SERP Features, Multi-Engine, Schema, E-E-A-T, Voice Search

```python
workflow = get_workflow("ai_readiness")
```

## API Usage

### REST API Endpoints

```bash
# List workflows
GET /api/v1/workflows/

# Get configuration schema
GET /api/v1/workflows/config/schema

# Get example configurations
GET /api/v1/workflows/config/examples

# Run workflow (synchronous)
POST /api/v1/workflows/{workflow_id}/run
{
  "workflow_input": {
    "targets": {
      "primary_domain": "example.com",
      "property_url": "https://example.com",
      "competitors": [
        {"domain": "competitor.com", "priority": "high"}
      ]
    },
    "business_info": {
      "name": "My Business",
      "url": "https://example.com"
    }
  }
}

# Run workflow (asynchronous - for long workflows)
POST /api/v1/workflows/{workflow_id}/run/async
# Returns: {"job_id": "uuid", "status": "running"}

# Check job status
GET /api/v1/workflows/jobs/{job_id}

# Get recommendations
GET /api/v1/workflows/jobs/{job_id}/recommendations

# Get alerts
GET /api/v1/workflows/jobs/{job_id}/alerts
```

### Example: Full Audit via API

```bash
curl -X POST "https://your-api.com/api/v1/workflows/full_audit/run" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_input": {
      "targets": {
        "primary_domain": "mystore.com",
        "property_url": "https://mystore.com",
        "competitors": [
          {"domain": "competitor1.com", "priority": "high"},
          {"domain": "competitor2.com", "priority": "medium"}
        ],
        "target_queries": ["widgets", "best widgets", "buy widgets"],
        "query_limit": 200
      },
      "business_info": {
        "name": "My Store",
        "url": "https://mystore.com",
        "description": "Leading widget retailer",
        "phone": "+1-555-0100",
        "city": "San Francisco",
        "state": "CA"
      },
      "thresholds": {
        "traffic_drop_threshold_pct": 25.0,
        "min_eeat_score": 70.0
      },
      "options": {
        "days_back": 90,
        "analysis_depth": "deep"
      }
    }
  }'
```

## What You Get Back

### Workflow Result Structure

```python
result = await orchestrator.run_workflow(workflow, params)

# Overall success
result.success  # bool

# Execution details
result.workflow_name       # "Full SEO Audit"
result.duration_ms         # 1234567
result.steps_completed     # 10
result.steps_failed        # 0

# Aggregated findings
result.all_recommendations  # List[Recommendation]
result.all_alerts          # List[Alert]
result.priority_actions    # Top 15 priority actions

# Executive summary
result.executive_summary   # Markdown formatted summary

# Per-agent details
result.agent_summaries     # Dict of results per agent
```

### Example Response

```json
{
  "workflow_id": "full_audit",
  "workflow_name": "Full SEO Audit",
  "success": true,
  "duration_ms": 892341,
  "steps_completed": 12,
  "steps_failed": 0,
  "total_recommendations": 47,
  "total_alerts": 8,
  "executive_summary": "## Full SEO Audit Results\n\nCompleted 12/12 analysis steps.\n\n**2 critical alerts** require immediate attention...",
  "priority_actions": [
    {
      "type": "alert",
      "priority": "critical",
      "title": "Traffic Drop Detected",
      "description": "30% traffic drop in last 7 days"
    },
    {
      "type": "recommendation",
      "priority": "high",
      "title": "Add FAQ Schema",
      "description": "Add FAQ schema to product pages",
      "estimated_impact": "15-25% CTR improvement",
      "effort": "low",
      "auto_implementable": true
    }
  ],
  "agent_summaries": {
    "traffic_check": {
      "agent_type": "monitoring",
      "status": "completed",
      "duration_ms": 45123,
      "recommendations": 5,
      "alerts": 2,
      "key_findings": [
        "Traffic down 30% week-over-week",
        "5 queries lost AI Overviews"
      ]
    }
  }
}
```

## Scheduled Jobs

The orchestrator integrates with the scheduler for automated monitoring:

```python
from src.scheduler import get_scheduler, ScheduledJob, JobType

scheduler = get_scheduler()

# Daily full audit at 6am
scheduler.add_job(ScheduledJob(
    id="daily_full_audit",
    job_type=JobType.FULL_ANALYSIS,  # Uses full_audit workflow
    name="Daily Comprehensive Audit",
    cron="0 6 * * *",
    parameters={
        "domain": "example.com",
        "competitors": ["competitor1.com", "competitor2.com"],
    }
))
```

## Best Practices

### 1. **Start Small**
- Begin with `quick_check` to validate setup
- Move to specific workflows (`content`, `technical`) for focused analysis
- Use `full_audit` monthly or after major changes

### 2. **Configure Competitors**
- Add 3-5 main competitors for best insights
- Mark top 1-2 as "high" priority
- Update quarterly

### 3. **Set Realistic Thresholds**
- Don't set traffic thresholds too tight (causes alert fatigue)
- Adjust based on your site's volatility
- Review and tune monthly

### 4. **Provide Business Context**
- Complete business info improves schema recommendations
- Author credentials boost E-E-A-T analysis
- Location data enables local SEO features

### 5. **Use Async for Full Audits**
- Full audits can take 15-30 minutes
- Use async API endpoint for better UX
- Poll for status or use webhooks

### 6. **Review Priority Actions**
- Focus on `priority_actions` first (top 15 items)
- Sort by auto-implementable for quick wins
- Critical alerts always require immediate action

## Troubleshooting

### "No data available"
- Verify Google Search Console is connected
- Check that `property_url` matches GSC property
- Ensure date range has data

### "Competitor analysis empty"
- Add competitors to configuration
- Verify competitor domains are correct
- Check that competitors rank for your queries

### "E-E-A-T score low"
- Add author credentials
- Provide social profile URLs
- Include professional bio

### "Schema recommendations generic"
- Provide business_info
- Specify article/product details
- Include author information

## Need Help?

Check example configurations:
```bash
curl https://your-api.com/api/v1/workflows/config/examples
```

View complete schema:
```bash
curl https://your-api.com/api/v1/workflows/config/schema
```

Or use the presets:
```python
from src.orchestrator import EXAMPLE_ECOMMERCE_CONFIG, EXAMPLE_LOCAL_BUSINESS_CONFIG

# Use as-is or modify
config = EXAMPLE_ECOMMERCE_CONFIG
config.targets.primary_domain = "your-domain.com"
```
