"""
Schema Agent - Generates and validates structured data (JSON-LD) for SEO.
"""

import json
import re
from typing import Any
from urllib.parse import urlparse

import httpx
import structlog
from bs4 import BeautifulSoup

from src.agents.base import BaseAgent, AgentContext
from src.core.errors import AgentError, ErrorCode
from src.models.agents import (
    AgentTask, AgentResult, AgentType, Recommendation, Alert, Priority, Severity
)

logger = structlog.get_logger()


class SchemaAgent(BaseAgent):
    """
    Generates and validates structured data for improved SERP visibility.

    Capabilities:
    - Audit existing structured data
    - Generate JSON-LD for common schema types
    - Validate schema against Google requirements
    - Identify missing schema opportunities
    - Generate FAQ schema from content
    """

    agent_type = AgentType.SCHEMA_GENERATOR

    def __init__(self, context: AgentContext):
        self.context = context
        self.logger = logger.bind(agent="schema")

    async def execute(self, task: AgentTask) -> AgentResult:
        """Execute schema task."""
        task_handlers = {
            "audit_schema": self._audit_schema,
            "generate_faq_schema": self._generate_faq_schema,
            "generate_article_schema": self._generate_article_schema,
            "generate_product_schema": self._generate_product_schema,
            "generate_howto_schema": self._generate_howto_schema,
            "generate_organization_schema": self._generate_organization_schema,
            "validate_schema": self._validate_schema,
            "find_schema_opportunities": self._find_schema_opportunities,
        }

        handler = task_handlers.get(task.task_type)
        if not handler:
            raise AgentError(
                f"Unknown task type: {task.task_type}",
                agent_type="schema",
                task_type=task.task_type,
                code=ErrorCode.VALIDATION_ERROR,
            )

        result = await handler(task.parameters)

        return AgentResult(
            task_id=task.id,
            agent_type=self.agent_type,
            success=True,
            data=result["data"],
            recommendations=result.get("recommendations", []),
            alerts=result.get("alerts", []),
        )

    async def _audit_schema(self, params: dict[str, Any]) -> dict[str, Any]:
        """Audit existing structured data on a page or site."""
        urls = params.get("urls", [])
        if not urls and self.context.property_url:
            urls = [self.context.property_url]

        audit_results = []
        recommendations = []
        total_schemas = 0
        schema_types_found = {}

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            for url in urls[:20]:
                try:
                    response = await client.get(url)
                    if response.status_code != 200:
                        continue

                    soup = BeautifulSoup(response.text, "lxml")
                    page_schemas = []

                    # Find JSON-LD scripts
                    for script in soup.find_all("script", type="application/ld+json"):
                        try:
                            schema_data = json.loads(script.string)

                            # Handle @graph format
                            if isinstance(schema_data, dict) and "@graph" in schema_data:
                                schemas_list = schema_data["@graph"]
                            elif isinstance(schema_data, list):
                                schemas_list = schema_data
                            else:
                                schemas_list = [schema_data]

                            for schema in schemas_list:
                                if isinstance(schema, dict):
                                    schema_type = schema.get("@type", "Unknown")
                                    if isinstance(schema_type, list):
                                        schema_type = ", ".join(schema_type)

                                    validation = self._validate_schema_structure(schema)

                                    page_schemas.append({
                                        "type": schema_type,
                                        "valid": validation["valid"],
                                        "issues": validation["issues"],
                                        "warnings": validation["warnings"],
                                    })

                                    schema_types_found[schema_type] = schema_types_found.get(schema_type, 0) + 1
                                    total_schemas += 1

                        except json.JSONDecodeError as e:
                            page_schemas.append({
                                "type": "Invalid JSON",
                                "valid": False,
                                "issues": [f"JSON parse error: {str(e)}"],
                                "warnings": [],
                            })

                    audit_results.append({
                        "url": url,
                        "schemas_found": len(page_schemas),
                        "schemas": page_schemas,
                        "has_issues": any(not s["valid"] for s in page_schemas),
                    })

                except Exception as e:
                    self.logger.warning("Schema audit failed", url=url, error=str(e))

        # Generate recommendations
        pages_with_issues = [r for r in audit_results if r["has_issues"]]
        pages_without_schema = [r for r in audit_results if r["schemas_found"] == 0]

        if pages_with_issues:
            recommendations.append(Recommendation(
                title=f"{len(pages_with_issues)} pages have schema issues",
                description="Fix structured data errors to ensure rich results eligibility",
                priority=Priority.HIGH,
                category="structured_data",
            ))

        if pages_without_schema:
            recommendations.append(Recommendation(
                title=f"{len(pages_without_schema)} pages missing structured data",
                description="Add relevant schema markup to improve SERP visibility",
                priority=Priority.MEDIUM,
                category="structured_data",
            ))

        return {
            "data": {
                "pages_audited": len(audit_results),
                "total_schemas_found": total_schemas,
                "schema_types": schema_types_found,
                "pages_with_issues": len(pages_with_issues),
                "pages_without_schema": len(pages_without_schema),
                "audit_results": audit_results,
            },
            "recommendations": recommendations,
        }

    def _validate_schema_structure(self, schema: dict) -> dict[str, Any]:
        """Validate schema structure against common requirements."""
        issues = []
        warnings = []

        schema_type = schema.get("@type", "")

        # Common required fields by type
        required_fields = {
            "Article": ["headline", "author", "datePublished"],
            "NewsArticle": ["headline", "author", "datePublished"],
            "BlogPosting": ["headline", "author", "datePublished"],
            "Product": ["name"],
            "FAQPage": ["mainEntity"],
            "HowTo": ["name", "step"],
            "Organization": ["name"],
            "LocalBusiness": ["name", "address"],
            "Person": ["name"],
            "WebPage": ["name"],
            "BreadcrumbList": ["itemListElement"],
        }

        # Check required fields
        if schema_type in required_fields:
            for field in required_fields[schema_type]:
                if field not in schema:
                    issues.append(f"Missing required field: {field}")

        # Check for @context
        if "@context" not in schema and "@type" in schema:
            warnings.append("Missing @context (should be 'https://schema.org')")

        # Type-specific validations
        if schema_type == "FAQPage":
            main_entity = schema.get("mainEntity", [])
            if main_entity:
                for i, qa in enumerate(main_entity):
                    if not qa.get("name"):
                        issues.append(f"FAQ item {i+1} missing question (name)")
                    if not qa.get("acceptedAnswer", {}).get("text"):
                        issues.append(f"FAQ item {i+1} missing answer text")

        if schema_type in ["Article", "NewsArticle", "BlogPosting"]:
            if "image" not in schema:
                warnings.append("Missing image - required for rich results")
            if "author" in schema:
                author = schema["author"]
                if isinstance(author, dict) and "name" not in author:
                    issues.append("Author missing name")

        if schema_type == "Product":
            if "offers" not in schema:
                warnings.append("Missing offers - recommended for product rich results")
            if "review" not in schema and "aggregateRating" not in schema:
                warnings.append("Missing reviews/ratings - recommended for visibility")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
        }

    async def _generate_faq_schema(self, params: dict[str, Any]) -> dict[str, Any]:
        """Generate FAQ schema from Q&A pairs or page content."""
        faqs = params.get("faqs", [])  # List of {"question": ..., "answer": ...}
        url = params.get("url")

        # If URL provided, try to extract FAQs from page
        if url and not faqs:
            faqs = await self._extract_faqs_from_page(url)

        if not faqs:
            return {
                "data": {"error": "No FAQs provided or found"},
                "recommendations": [],
            }

        # Generate schema
        faq_schema = {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": faq["question"],
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": faq["answer"],
                    },
                }
                for faq in faqs
            ],
        }

        return {
            "data": {
                "schema": faq_schema,
                "schema_json": json.dumps(faq_schema, indent=2),
                "faq_count": len(faqs),
            },
            "recommendations": [
                Recommendation(
                    title="Add FAQ schema to your page",
                    description="Insert this JSON-LD in a <script type='application/ld+json'> tag",
                    priority=Priority.MEDIUM,
                    category="structured_data",
                ),
            ],
        }

    async def _extract_faqs_from_page(self, url: str) -> list[dict]:
        """Extract FAQ-like content from a page."""
        faqs = []

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                soup = BeautifulSoup(response.text, "lxml")

                # Look for FAQ patterns
                # Pattern 1: Definition lists
                for dl in soup.find_all("dl"):
                    dts = dl.find_all("dt")
                    dds = dl.find_all("dd")
                    for dt, dd in zip(dts, dds):
                        faqs.append({
                            "question": dt.get_text(strip=True),
                            "answer": dd.get_text(strip=True),
                        })

                # Pattern 2: Accordion/FAQ sections
                faq_containers = soup.find_all(
                    ["div", "section"],
                    class_=re.compile(r"faq|accordion|qa", re.I)
                )
                for container in faq_containers:
                    questions = container.find_all(
                        ["h2", "h3", "h4", "button"],
                        class_=re.compile(r"question|title|header", re.I)
                    )
                    answers = container.find_all(
                        ["div", "p"],
                        class_=re.compile(r"answer|content|body", re.I)
                    )
                    for q, a in zip(questions, answers):
                        q_text = q.get_text(strip=True)
                        a_text = a.get_text(strip=True)
                        if q_text and a_text and "?" in q_text:
                            faqs.append({"question": q_text, "answer": a_text})

        except Exception as e:
            self.logger.warning("FAQ extraction failed", url=url, error=str(e))

        return faqs[:20]  # Limit to 20

    async def _generate_article_schema(self, params: dict[str, Any]) -> dict[str, Any]:
        """Generate Article schema."""
        article_schema = {
            "@context": "https://schema.org",
            "@type": params.get("article_type", "Article"),
            "headline": params.get("headline", ""),
            "description": params.get("description", ""),
            "image": params.get("image", []),
            "author": {
                "@type": params.get("author_type", "Person"),
                "name": params.get("author_name", ""),
                "url": params.get("author_url", ""),
            },
            "publisher": {
                "@type": "Organization",
                "name": params.get("publisher_name", ""),
                "logo": {
                    "@type": "ImageObject",
                    "url": params.get("publisher_logo", ""),
                },
            },
            "datePublished": params.get("date_published", ""),
            "dateModified": params.get("date_modified", params.get("date_published", "")),
        }

        # Clean empty values
        article_schema = self._clean_schema(article_schema)

        return {
            "data": {
                "schema": article_schema,
                "schema_json": json.dumps(article_schema, indent=2),
            },
            "recommendations": [],
        }

    async def _generate_product_schema(self, params: dict[str, Any]) -> dict[str, Any]:
        """Generate Product schema."""
        product_schema = {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": params.get("name", ""),
            "description": params.get("description", ""),
            "image": params.get("image", ""),
            "brand": {
                "@type": "Brand",
                "name": params.get("brand", ""),
            },
            "sku": params.get("sku", ""),
            "offers": {
                "@type": "Offer",
                "url": params.get("url", ""),
                "priceCurrency": params.get("currency", "USD"),
                "price": params.get("price", ""),
                "availability": params.get("availability", "https://schema.org/InStock"),
            },
        }

        # Add reviews if provided
        if params.get("rating_value"):
            product_schema["aggregateRating"] = {
                "@type": "AggregateRating",
                "ratingValue": params.get("rating_value"),
                "reviewCount": params.get("review_count", 1),
            }

        product_schema = self._clean_schema(product_schema)

        return {
            "data": {
                "schema": product_schema,
                "schema_json": json.dumps(product_schema, indent=2),
            },
            "recommendations": [],
        }

    async def _generate_howto_schema(self, params: dict[str, Any]) -> dict[str, Any]:
        """Generate HowTo schema."""
        steps = params.get("steps", [])

        howto_schema = {
            "@context": "https://schema.org",
            "@type": "HowTo",
            "name": params.get("name", ""),
            "description": params.get("description", ""),
            "totalTime": params.get("total_time", ""),
            "step": [
                {
                    "@type": "HowToStep",
                    "name": step.get("name", f"Step {i+1}"),
                    "text": step.get("text", ""),
                    "image": step.get("image", ""),
                }
                for i, step in enumerate(steps)
            ],
        }

        if params.get("supplies"):
            howto_schema["supply"] = [
                {"@type": "HowToSupply", "name": s} for s in params["supplies"]
            ]

        if params.get("tools"):
            howto_schema["tool"] = [
                {"@type": "HowToTool", "name": t} for t in params["tools"]
            ]

        howto_schema = self._clean_schema(howto_schema)

        return {
            "data": {
                "schema": howto_schema,
                "schema_json": json.dumps(howto_schema, indent=2),
            },
            "recommendations": [],
        }

    async def _generate_organization_schema(self, params: dict[str, Any]) -> dict[str, Any]:
        """Generate Organization schema."""
        org_schema = {
            "@context": "https://schema.org",
            "@type": params.get("org_type", "Organization"),
            "name": params.get("name", ""),
            "url": params.get("url", ""),
            "logo": params.get("logo", ""),
            "description": params.get("description", ""),
            "sameAs": params.get("social_profiles", []),
        }

        if params.get("address"):
            org_schema["address"] = {
                "@type": "PostalAddress",
                "streetAddress": params["address"].get("street", ""),
                "addressLocality": params["address"].get("city", ""),
                "addressRegion": params["address"].get("region", ""),
                "postalCode": params["address"].get("postal_code", ""),
                "addressCountry": params["address"].get("country", ""),
            }

        if params.get("contact_phone"):
            org_schema["contactPoint"] = {
                "@type": "ContactPoint",
                "telephone": params.get("contact_phone"),
                "contactType": params.get("contact_type", "customer service"),
            }

        org_schema = self._clean_schema(org_schema)

        return {
            "data": {
                "schema": org_schema,
                "schema_json": json.dumps(org_schema, indent=2),
            },
            "recommendations": [],
        }

    async def _validate_schema(self, params: dict[str, Any]) -> dict[str, Any]:
        """Validate provided schema JSON."""
        schema_json = params.get("schema")

        if isinstance(schema_json, str):
            try:
                schema_data = json.loads(schema_json)
            except json.JSONDecodeError as e:
                return {
                    "data": {
                        "valid": False,
                        "errors": [f"Invalid JSON: {str(e)}"],
                    },
                    "recommendations": [],
                }
        else:
            schema_data = schema_json

        validation = self._validate_schema_structure(schema_data)

        return {
            "data": {
                "valid": validation["valid"],
                "issues": validation["issues"],
                "warnings": validation["warnings"],
                "schema_type": schema_data.get("@type", "Unknown"),
            },
            "recommendations": [],
        }

    async def _find_schema_opportunities(self, params: dict[str, Any]) -> dict[str, Any]:
        """Analyze page content to suggest schema opportunities."""
        url = params.get("url")

        if not url:
            return {"data": {"error": "URL required"}, "recommendations": []}

        opportunities = []
        recommendations = []

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                soup = BeautifulSoup(response.text, "lxml")

                # Check for existing schema
                existing_types = set()
                for script in soup.find_all("script", type="application/ld+json"):
                    try:
                        data = json.loads(script.string)
                        if isinstance(data, dict):
                            existing_types.add(data.get("@type", ""))
                    except Exception:
                        pass

                # Analyze page content for opportunities

                # 1. FAQ content
                if "FAQPage" not in existing_types:
                    faq_indicators = soup.find_all(
                        ["h2", "h3", "h4"],
                        string=re.compile(r"(FAQ|frequently asked|questions)", re.I)
                    )
                    if faq_indicators or soup.find_all("dt"):
                        opportunities.append({
                            "type": "FAQPage",
                            "reason": "FAQ-style content detected",
                            "priority": "high",
                        })

                # 2. How-to content
                if "HowTo" not in existing_types:
                    howto_indicators = soup.find_all(
                        ["h1", "h2"],
                        string=re.compile(r"(how to|guide|tutorial|steps)", re.I)
                    )
                    if howto_indicators:
                        opportunities.append({
                            "type": "HowTo",
                            "reason": "How-to/guide content detected",
                            "priority": "high",
                        })

                # 3. Article content
                if not any(t in existing_types for t in ["Article", "NewsArticle", "BlogPosting"]):
                    article_tag = soup.find("article")
                    if article_tag or soup.find("meta", property="article:published_time"):
                        opportunities.append({
                            "type": "Article",
                            "reason": "Article content structure detected",
                            "priority": "medium",
                        })

                # 4. Product content
                if "Product" not in existing_types:
                    price_indicators = soup.find_all(
                        class_=re.compile(r"price|cost", re.I)
                    )
                    add_to_cart = soup.find(
                        string=re.compile(r"add to cart|buy now", re.I)
                    )
                    if price_indicators and add_to_cart:
                        opportunities.append({
                            "type": "Product",
                            "reason": "E-commerce product page detected",
                            "priority": "high",
                        })

                # 5. Local business
                if "LocalBusiness" not in existing_types:
                    address_indicators = soup.find_all(
                        string=re.compile(r"\d{5}(-\d{4})?")  # ZIP code pattern
                    )
                    phone_pattern = soup.find_all(
                        string=re.compile(r"\(\d{3}\)\s*\d{3}-\d{4}")
                    )
                    if address_indicators and phone_pattern:
                        opportunities.append({
                            "type": "LocalBusiness",
                            "reason": "Local business information detected",
                            "priority": "medium",
                        })

                # 6. Breadcrumbs
                if "BreadcrumbList" not in existing_types:
                    breadcrumb = soup.find(
                        class_=re.compile(r"breadcrumb", re.I)
                    )
                    if breadcrumb:
                        opportunities.append({
                            "type": "BreadcrumbList",
                            "reason": "Breadcrumb navigation detected",
                            "priority": "low",
                        })

        except Exception as e:
            self.logger.warning("Schema opportunity scan failed", url=url, error=str(e))

        if opportunities:
            high_priority = [o for o in opportunities if o["priority"] == "high"]
            recommendations.append(Recommendation(
                title=f"Found {len(opportunities)} schema opportunities",
                description=f"{len(high_priority)} high-priority schemas could improve SERP visibility",
                priority=Priority.HIGH if high_priority else Priority.MEDIUM,
                category="structured_data",
                data={"opportunities": opportunities},
            ))

        return {
            "data": {
                "url": url,
                "existing_schemas": list(existing_types),
                "opportunities": opportunities,
            },
            "recommendations": recommendations,
        }

    def _clean_schema(self, schema: dict) -> dict:
        """Remove empty values from schema."""
        cleaned = {}
        for key, value in schema.items():
            if isinstance(value, dict):
                cleaned_value = self._clean_schema(value)
                if cleaned_value:
                    cleaned[key] = cleaned_value
            elif isinstance(value, list):
                cleaned_list = [
                    self._clean_schema(item) if isinstance(item, dict) else item
                    for item in value
                    if item
                ]
                if cleaned_list:
                    cleaned[key] = cleaned_list
            elif value not in (None, "", []):
                cleaned[key] = value
        return cleaned
