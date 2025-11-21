# AI Visibility Audit (Synlighetsgranskning)

## Overview

The **AI Visibility Audit** workflow provides comprehensive analysis of your brand's presence across all major AI assistants, directly matching the service offering described in the Swedish AI visibility audit service.

This workflow answers the critical question: **"How visible is my brand in AI-generated responses?"**

## What It Analyzes

### 1. **Analys av varumärkesomnämnanden** (Brand Mention Analysis)
- Tracks your brand presence in ChatGPT, Claude, Gemini, Perplexity, and Bing Copilot
- Analyzes how AI engines describe your brand
- Identifies product perception and digital reputation in AI responses
- Compares brand sentiment vs competitors

### 2. **Auktoritetsbedömning** (Authority Assessment)
- E-E-A-T signal analysis (Experience, Expertise, Authoritativeness, Trust)
- Content authority scoring
- Author credential validation
- Trust indicators assessment
- Citation quality analysis

### 3. **Identifiering av luckor/marknadsgap** (Gap Identification)
- Competitive positioning in AI-generated answers
- Market share analysis across AI engines
- Competitor citation rates vs your brand
- Opportunity identification for AI visibility improvement

### 4. **On-page-optimering för AI** (On-Page Optimization for AI)
- Schema markup optimization recommendations
- Knowledge graph visibility improvements
- Structured data enhancements
- Semantic SEO opportunities
- Content structuring for AI comprehension

### 5. **Strategiska åtgärder** (Strategic Actions)
- Prioritized recommendations for AI search ranking improvements
- Content authority building tactics
- Brand mention optimization strategies
- User-generated content leverage opportunities
- Query targeting for AI engines

## Workflow Steps

The workflow runs in 5 coordinated phases:

```
Phase 1: AI Engine Scan
├─ Multi-Engine Tracker: Scan all 5 major AI assistants
└─ Track brand mentions and citations

Phase 2: Competitive Analysis (Parallel)
├─ Competitor Monitor: Compare your presence vs competitors
└─ SERP Features: Analyze AI Overview citations

Phase 3: Authority Assessment
└─ E-E-A-T Analyzer: Evaluate trust and authority signals

Phase 4: Optimization Opportunities (Parallel)
├─ Schema Generator: Knowledge graph optimization
├─ AI Content Analyzer: Content structure analysis
└─ Multi-Platform SEO: Semantic optimization

Phase 5: Strategic Recommendations
└─ Optimization Recommender: Actionable improvement plan
```

## Duration

**Estimated runtime:** 15-25 minutes

## How to Run

### Via CLI

```bash
# With your saved configuration
python -m src.cli run-workflow ai_visibility_audit --config default

# Or with inline config
python -m src.cli run-workflow ai_visibility_audit \
  --domain mystore.com \
  --competitors competitor1.com,competitor2.com
```

### Via API

```bash
curl -X POST "https://your-api.com/api/v1/workflows/ai_visibility_audit/run" \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_input": {
      "targets": {
        "primary_domain": "mystore.com",
        "property_url": "https://mystore.com",
        "competitors": [
          {"domain": "competitor1.com", "priority": "high"},
          {"domain": "competitor2.com", "priority": "medium"}
        ]
      },
      "business_info": {
        "name": "My Store",
        "url": "https://mystore.com",
        "description": "Leading provider of widgets"
      },
      "default_author": {
        "name": "Expert Author",
        "credentials": ["Industry Expert", "Published Author"]
      }
    }
  }'
```

## What You Get

### Executive Summary

A markdown-formatted summary including:

```markdown
## AI Visibility Audit Results

✅ Completed 8/8 analysis steps in 18 minutes

### Brand Presence Overview
- **ChatGPT**: Mentioned in 45% of relevant queries
- **Claude**: Mentioned in 38% of relevant queries
- **Gemini**: Mentioned in 52% of relevant queries
- **Perplexity**: Mentioned in 41% of relevant queries
- **Bing Copilot**: Mentioned in 48% of relevant queries

### Competitive Position
- Market share in AI: 32% (vs top competitor at 51%)
- Citation quality score: 7.8/10
- 18 gap opportunities identified

### Authority Score
- E-E-A-T Score: 68/100
- Trust signals: Strong
- Author credentials: Moderate
- Content authority: Good

### Top Priority Actions
1. Add FAQ schema to 12 high-traffic pages (High Impact, Low Effort)
2. Strengthen author credentials with certifications (High Impact, Medium Effort)
3. Target 8 competitor gap queries for AI visibility (Medium Impact, Low Effort)
```

### Detailed Reports

1. **AI Engine Presence Report**
   - Per-engine visibility metrics
   - Brand mention frequency
   - Citation context analysis
   - Sentiment in AI responses

2. **Competitive Positioning Report**
   - Competitor citation rates
   - Market share by AI engine
   - Gap analysis (queries where competitors dominate)
   - Strategic opportunities

3. **Authority Assessment Report**
   - E-E-A-T component scores
   - Trust indicator inventory
   - Author credential analysis
   - Content authority gaps

4. **Optimization Recommendations**
   - Schema markup gaps
   - Knowledge graph improvements
   - Semantic SEO opportunities
   - Content structure enhancements

5. **Strategic Action Plan**
   - Prioritized recommendations (high/medium/low)
   - Estimated impact per action
   - Implementation effort
   - Auto-implementable quick wins

## Recommended Configuration

For best results, provide:

### Required
- Domain and URL
- 3-5 competitor domains

### Highly Recommended
- Business information (name, description, logo)
- Author credentials (for E-E-A-T scoring)
- Target queries (or let it use GSC data)

### Optional but Valuable
- Social profiles (Twitter, LinkedIn, Facebook)
- Industry/category
- Brand positioning statement

### Example Configuration

```python
from src.orchestrator import OnboardingFlow, get_workflow, AgentOrchestrator

# Run onboarding with AI visibility focus
flow = OnboardingFlow()
flow.site_type = "ecommerce"  # or "content", "saas", etc.
config = flow.start(interactive=True)

# Run the audit
orchestrator = AgentOrchestrator(context)
workflow = get_workflow("ai_visibility_audit")
result = await orchestrator.run_workflow(workflow, config.to_params())

# Access results
print(result.executive_summary)
print(f"Total recommendations: {len(result.all_recommendations)}")
print(f"Priority actions: {len(result.priority_actions)}")
```

## Use Cases

### 1. Initial Baseline Assessment
**When:** Starting AI visibility optimization
**Frequency:** One-time setup
**Focus:** Understanding current state

### 2. Competitive Benchmarking
**When:** Quarterly business reviews
**Frequency:** Quarterly
**Focus:** Market position vs competitors

### 3. Campaign Effectiveness
**When:** After major content/SEO campaigns
**Frequency:** Post-campaign
**Focus:** Measuring AI visibility improvements

### 4. Reputation Monitoring
**When:** Managing brand reputation
**Frequency:** Monthly
**Focus:** Brand perception in AI responses

### 5. Strategic Planning
**When:** Planning SEO/content strategy
**Frequency:** Quarterly/bi-annually
**Focus:** Identifying opportunities

## Interpretation Guide

### Brand Presence Metrics

| Mention Rate | Interpretation | Action |
|--------------|----------------|--------|
| 60%+ | Excellent | Maintain & expand |
| 40-60% | Good | Optimize key gaps |
| 20-40% | Moderate | Strategic improvement needed |
| <20% | Poor | Urgent optimization required |

### E-E-A-T Scores

| Score | Level | Priority |
|-------|-------|----------|
| 80+ | Excellent | Maintain signals |
| 60-80 | Good | Selective improvements |
| 40-60 | Moderate | Systematic enhancement |
| <40 | Poor | Critical improvement needed |

### Competitive Position

| Market Share | Status | Strategy |
|--------------|--------|----------|
| Leader (>50%) | Dominant | Defend position |
| Strong (30-50%) | Competitive | Target gaps |
| Moderate (15-30%) | Challenger | Aggressive optimization |
| Weak (<15%) | Underdog | Focus on niches |

## Comparison to Swedish Service Offering

| Swedish Service Component | AI SEO Agent Workflow Step |
|---------------------------|----------------------------|
| **Synlighetsgranskning** (Visibility Audit) | Multi-Engine Tracker + SERP Features |
| **Analys av varumärkesomnämnanden** | Competitor Monitor + Multi-Engine Tracker |
| **Digitalt anseende, produktuppfattning** | E-E-A-T Analyzer + AI Content Analyzer |
| **Auktoritetsbedömning** | E-E-A-T Analyzer |
| **Identifiering av luckor/marknadsgap** | Competitor Monitor |
| **Optimering av schema-markup** | Schema Generator |
| **Synliggörande av kunskapsgraf** | Schema Generator (knowledge graph optimization) |
| **Strukturering av innehåll** | AI Content Analyzer + Multi-Platform SEO |
| **Semantisk SEO** | Multi-Platform SEO (semantic optimization) |
| **Uppbyggnad av innehållsauktoritet** | E-E-A-T Analyzer + Recommendations |
| **Marknadsandelsanalys** | Competitor Monitor |
| **Konkurrenspositionering** | Competitor Monitor + Multi-Engine Tracker |
| **Strategiska insikter** | Optimization Recommender |
| **Resultatuppföljning** | Full workflow result tracking |

## Integration with Other Workflows

The AI Visibility Audit works well with:

- **Full Audit** - For comprehensive site-wide analysis
- **Content Analysis** - For deep content optimization
- **Competitive Analysis** - For ongoing competitor tracking
- **AI Readiness** - For implementation of recommendations

## Scheduling

Recommended frequencies:

```bash
# Monthly audit
python -m src.cli schedule add \
  --workflow ai_visibility_audit \
  --config production \
  --cron "0 1 1 * *"  # 1am on 1st of month

# Quarterly competitor benchmark
python -m src.cli schedule add \
  --workflow ai_visibility_audit \
  --config production \
  --cron "0 1 1 */3 *"  # 1am on 1st of quarter
```

## Export and Reporting

Results can be exported in multiple formats:

```python
# JSON export
with open("ai_visibility_report.json", "w") as f:
    json.dump(result.model_dump(), f, indent=2)

# Executive summary (Markdown)
with open("executive_summary.md", "w") as f:
    f.write(result.executive_summary)

# Recommendations CSV
import csv
with open("recommendations.csv", "w") as f:
    writer = csv.DictWriter(f, fieldnames=["title", "priority", "category", "impact"])
    writer.writeheader()
    for rec in result.all_recommendations:
        writer.writerow(rec.model_dump())
```

## Next Steps After Audit

1. **Review executive summary** - Understand overall position
2. **Check priority actions** - Focus on high-impact, low-effort wins
3. **Analyze competitor gaps** - Identify strategic opportunities
4. **Implement quick wins** - Start with auto-implementable items
5. **Create action plan** - Prioritize medium-term improvements
6. **Schedule follow-up** - Set monthly/quarterly audits
7. **Track improvements** - Monitor metrics over time

## Questions & Support

### Common Questions

**Q: How often should I run this?**
A: Monthly for active optimization, quarterly for maintenance.

**Q: Do I need all 5 competitors?**
A: No, 2-3 main competitors give good insights. More is better for comprehensive analysis.

**Q: What if my E-E-A-T score is low?**
A: Focus on author credentials, citations to authoritative sources, and trust signals first.

**Q: Can I track specific queries?**
A: Yes! Add them to `targets.target_queries` in your configuration.

**Q: How long until I see improvements?**
A: Schema/structured data: 2-4 weeks. Content authority: 2-3 months. Competitive positioning: 3-6 months.

### Get Help

```bash
# View workflow details
curl https://your-api.com/api/v1/workflows/ai_visibility_audit

# Test your configuration
python -m src.cli_onboarding test production

# View example configurations
curl https://your-api.com/api/v1/workflows/config/examples
```

---

This workflow provides everything you need for **comprehensive AI visibility auditing** - exactly matching the Swedish service offering you shared! 🚀
