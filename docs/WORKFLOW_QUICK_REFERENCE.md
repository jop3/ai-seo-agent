# Workflow Configuration - Quick Reference

## Minimum Required for Basic Operation

```python
{
  "workflow_input": {
    "targets": {
      "primary_domain": "example.com",
      "property_url": "https://example.com"
    }
  }
}
```

**What this enables:**
- Traffic monitoring
- Technical SEO audit
- SERP analysis (for queries in Google Search Console)
- Basic schema recommendations

**Limitations:**
- No competitor analysis
- Generic E-E-A-T analysis
- No local SEO features
- Limited schema personalization

---

## Recommended Configuration

```python
{
  "workflow_input": {
    "targets": {
      "primary_domain": "mystore.com",
      "property_url": "https://mystore.com",
      "competitors": [
        {"domain": "competitor1.com", "priority": "high"},
        {"domain": "competitor2.com", "priority": "medium"}
      ],
      "target_queries": ["keyword 1", "keyword 2", "keyword 3"]
    },
    "business_info": {
      "name": "My Store",
      "url": "https://mystore.com",
      "description": "What we do",
      "logo_url": "https://mystore.com/logo.png"
    }
  }
}
```

**What this adds:**
- Competitor gap analysis
- Citation comparison in AI engines
- Better schema recommendations
- Branded content analysis

---

## Full Configuration (All Features)

### For E-commerce Sites

```python
{
  "workflow_input": {
    "targets": {
      "primary_domain": "mystore.com",
      "property_url": "https://mystore.com",
      "competitors": [
        {"domain": "competitor1.com", "name": "Competitor A", "priority": "high"},
        {"domain": "competitor2.com", "name": "Competitor B", "priority": "medium"}
      ],
      "target_queries": ["product keyword 1", "product keyword 2"],
      "query_limit": 200,
      "max_pages": 5000
    },
    "business_info": {
      "name": "My Store",
      "legal_name": "My Store Inc.",
      "url": "https://mystore.com",
      "description": "Leading retailer of widgets",
      "logo_url": "https://mystore.com/logo.png",
      "publisher_logo_url": "https://mystore.com/publisher-logo.png",
      "phone": "+1-555-0100",
      "email": "support@mystore.com",
      "industry": "E-commerce",
      "facebook_url": "https://facebook.com/mystore",
      "twitter_url": "https://twitter.com/mystore",
      "instagram_url": "https://instagram.com/mystore"
    },
    "default_author": {
      "name": "John Smith",
      "url": "https://mystore.com/authors/john-smith",
      "bio": "Senior product reviewer with 10 years experience",
      "credentials": ["Certified Expert", "Published Author"]
    },
    "thresholds": {
      "traffic_drop_threshold_pct": 25.0,
      "content_decay_days": 60,
      "min_eeat_score": 70.0
    },
    "options": {
      "analysis_depth": "deep",
      "days_back": 90,
      "forecast_days": 30
    }
  }
}
```

### For Local Businesses

```python
{
  "workflow_input": {
    "targets": {
      "primary_domain": "mypizzeria.com",
      "property_url": "https://mypizzeria.com",
      "competitors": [
        {"domain": "competitor-pizza.com", "priority": "high"}
      ],
      "target_queries": ["pizza near me", "best pizza delivery"]
    },
    "business_info": {
      "name": "Mario's Pizzeria",
      "url": "https://mypizzeria.com",
      "description": "Authentic Italian pizza since 1985",
      "business_type": "Restaurant",
      "phone": "+1-555-7777",
      "email": "info@mypizzeria.com",
      "street_address": "456 Pizza Ave",
      "city": "Chicago",
      "state": "IL",
      "postal_code": "60601",
      "country": "US",
      "latitude": 41.8781,
      "longitude": -87.6298,
      "logo_url": "https://mypizzeria.com/logo.png",
      "facebook_url": "https://facebook.com/mariospizzeria",
      "instagram_url": "https://instagram.com/mariospizzeria"
    }
  }
}
```

---

## Parameter Reference

### Must Have
- `targets.primary_domain` - Your domain
- `targets.property_url` - Full site URL

### Should Have
- `targets.competitors` - 3-5 competitor domains
- `business_info.name` - Company name
- `business_info.description` - What you do
- `business_info.logo_url` - For Organization schema

### Nice to Have (by use case)

**For Local SEO:**
- `business_info.street_address`
- `business_info.city`, `state`, `postal_code`, `country`
- `business_info.phone`
- `business_info.latitude`, `longitude`
- `business_info.business_type` (Restaurant, LocalBusiness, etc.)

**For E-E-A-T / Content:**
- `default_author.name`
- `default_author.credentials`
- `default_author.bio`
- `default_author.url`
- `business_info.publisher_logo_url`

**For Competitive Analysis:**
- `targets.competitors` with priority levels
- `targets.target_queries` (specific keywords to compare)

**For Social Signals:**
- `business_info.facebook_url`
- `business_info.twitter_url`
- `business_info.linkedin_url`
- `business_info.instagram_url`
- `business_info.youtube_url`

---

## Configuration by Workflow

| Workflow | Minimum Config | Recommended Additions |
|----------|----------------|----------------------|
| **quick_check** | domain + URL | competitors |
| **full_audit** | domain + URL | business_info + competitors + author |
| **content** | domain + URL | business_info + author |
| **technical** | domain + URL | none (works standalone) |
| **competitive** | domain + URL + competitors | target_queries |
| **local_seo** | domain + URL + business address | phone + business_type |
| **ai_readiness** | domain + URL | business_info + author credentials |

---

## How to Get Started

1. **Start with minimal config** to verify everything works
2. **Add competitors** for competitive insights
3. **Add business info** for better schema/local SEO
4. **Add author info** if you publish content
5. **Tune thresholds** based on your site's patterns

## API Endpoints for Help

```bash
# Get full schema with all options
GET /api/v1/workflows/config/schema

# Get example configurations
GET /api/v1/workflows/config/examples

# List all workflows
GET /api/v1/workflows/
```

## Example: Curl Command

```bash
curl -X POST "https://api.example.com/api/v1/workflows/full_audit/run" \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
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
  }'
```
