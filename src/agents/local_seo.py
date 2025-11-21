"""
Local SEO Agent - Manages Google Business Profile optimization and local citations.
"""

import re
from typing import Any
from urllib.parse import urlparse, quote_plus

import httpx
import structlog
from bs4 import BeautifulSoup

from src.agents.base import BaseAgent, AgentContext
from src.core.errors import AgentError, ErrorCode
from src.models.agents import (
    AgentTask, AgentResult, AgentType, Recommendation, Alert, Priority, Severity
)

logger = structlog.get_logger()


class LocalSEOAgent(BaseAgent):
    """
    Optimizes local SEO presence and NAP consistency.

    Capabilities:
    - Audit NAP (Name, Address, Phone) consistency
    - Generate LocalBusiness schema
    - Find local citation opportunities
    - Analyze local SERP presence
    - Monitor Google Business Profile optimization
    - Check local keyword rankings
    """

    agent_type = AgentType.LOCAL_SEO

    def __init__(self, context: AgentContext):
        self.context = context
        self.logger = logger.bind(agent="local-seo")

    async def execute(self, task: AgentTask) -> AgentResult:
        """Execute local SEO task."""
        task_handlers = {
            "audit_nap_consistency": self._audit_nap_consistency,
            "generate_local_schema": self._generate_local_schema,
            "find_citation_opportunities": self._find_citation_opportunities,
            "analyze_local_serp": self._analyze_local_serp,
            "audit_gbp_optimization": self._audit_gbp_optimization,
            "check_local_rankings": self._check_local_rankings,
        }

        handler = task_handlers.get(task.task_type)
        if not handler:
            raise AgentError(
                f"Unknown task type: {task.task_type}",
                agent_type="local-seo",
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

    async def _audit_nap_consistency(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Audit NAP consistency across the web.

        Checks if Name, Address, and Phone are consistent across
        your website, citations, and directories.
        """
        business_name = params.get("business_name", "")
        address = params.get("address", {})
        phone = params.get("phone", "")
        website = params.get("website", self.context.property_url)
        citation_urls = params.get("citation_urls", [])

        if not business_name:
            return {"data": {"error": "business_name is required"}, "recommendations": []}

        recommendations = []
        alerts = []
        inconsistencies = []
        checked_sources = []

        # Normalize expected values
        expected_nap = {
            "name": self._normalize_business_name(business_name),
            "address": self._normalize_address(address),
            "phone": self._normalize_phone(phone),
        }

        # Check website
        if website:
            website_nap = await self._extract_nap_from_url(website)
            checked_sources.append({
                "source": "own_website",
                "url": website,
                "nap_found": website_nap,
                "matches": self._compare_nap(expected_nap, website_nap),
            })

        # Check provided citation URLs
        for url in citation_urls[:10]:  # Limit to 10
            try:
                citation_nap = await self._extract_nap_from_url(url)
                match_result = self._compare_nap(expected_nap, citation_nap)

                checked_sources.append({
                    "source": urlparse(url).netloc,
                    "url": url,
                    "nap_found": citation_nap,
                    "matches": match_result,
                })

                if not match_result["all_match"]:
                    inconsistencies.append({
                        "url": url,
                        "issues": match_result["differences"],
                    })

            except Exception as e:
                self.logger.warning("Failed to check citation", url=url, error=str(e))

        # Calculate consistency score
        total_checked = len(checked_sources)
        consistent_count = sum(1 for s in checked_sources if s["matches"]["all_match"])
        consistency_score = (consistent_count / total_checked * 100) if total_checked > 0 else 0

        # Generate recommendations
        if inconsistencies:
            alerts.append(Alert(
                title=f"NAP inconsistencies found on {len(inconsistencies)} sites",
                message="Inconsistent business information can hurt local rankings",
                severity=Severity.WARNING,
                source="local-seo",
            ))
            recommendations.append(Recommendation(
                title="Fix NAP inconsistencies",
                description=f"Update business information on {len(inconsistencies)} sites to match your official NAP",
                priority=Priority.HIGH,
                category="local_seo",
                data={"sites_to_fix": [i["url"] for i in inconsistencies]},
            ))

        if consistency_score < 80:
            recommendations.append(Recommendation(
                title="Improve NAP consistency score",
                description=f"Current score: {consistency_score:.0f}%. Aim for 95%+ for best local SEO.",
                priority=Priority.HIGH,
                category="local_seo",
            ))

        return {
            "data": {
                "expected_nap": expected_nap,
                "sources_checked": total_checked,
                "consistent_sources": consistent_count,
                "consistency_score": round(consistency_score, 1),
                "checked_sources": checked_sources,
                "inconsistencies": inconsistencies,
            },
            "recommendations": recommendations,
            "alerts": alerts,
        }

    def _normalize_business_name(self, name: str) -> str:
        """Normalize business name for comparison."""
        # Remove common suffixes and normalize
        name = name.lower().strip()
        for suffix in [" inc", " inc.", " llc", " ltd", " corp", " corporation"]:
            name = name.replace(suffix, "")
        return name

    def _normalize_address(self, address: dict | str) -> str:
        """Normalize address for comparison."""
        if isinstance(address, dict):
            parts = [
                address.get("street", ""),
                address.get("city", ""),
                address.get("state", ""),
                address.get("zip", ""),
                address.get("country", ""),
            ]
            address_str = " ".join(p for p in parts if p)
        else:
            address_str = str(address)

        # Normalize common variations
        address_str = address_str.lower().strip()
        replacements = [
            ("street", "st"), ("avenue", "ave"), ("boulevard", "blvd"),
            ("drive", "dr"), ("road", "rd"), ("lane", "ln"),
            ("  ", " "),
        ]
        for old, new in replacements:
            address_str = address_str.replace(old, new)

        return address_str

    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone number for comparison."""
        # Remove all non-digits
        return re.sub(r'\D', '', phone)

    async def _extract_nap_from_url(self, url: str) -> dict[str, str]:
        """Extract NAP information from a webpage."""
        nap = {"name": "", "address": "", "phone": ""}

        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                response = await client.get(url)
                soup = BeautifulSoup(response.text, "lxml")

                # Try to find structured data first
                for script in soup.find_all("script", type="application/ld+json"):
                    try:
                        import json
                        data = json.loads(script.string)

                        if isinstance(data, dict):
                            if data.get("@type") in ["LocalBusiness", "Organization", "Store"]:
                                nap["name"] = data.get("name", "")
                                if "address" in data:
                                    addr = data["address"]
                                    if isinstance(addr, dict):
                                        nap["address"] = self._normalize_address(addr)
                                    else:
                                        nap["address"] = str(addr)
                                nap["phone"] = self._normalize_phone(data.get("telephone", ""))
                                return nap
                    except Exception:
                        pass

                # Fallback: try to extract from page content
                # Look for phone patterns
                text = soup.get_text()
                phone_match = re.search(r'[\+]?[(]?[0-9]{1,3}[)]?[-\s\.]?[(]?[0-9]{1,4}[)]?[-\s\.]?[0-9]{1,4}[-\s\.]?[0-9]{1,9}', text)
                if phone_match:
                    nap["phone"] = self._normalize_phone(phone_match.group())

                # Look for address patterns (simplified)
                address_patterns = soup.find_all(["address", "div", "p"], class_=re.compile(r'address|location', re.I))
                if address_patterns:
                    nap["address"] = self._normalize_address(address_patterns[0].get_text(strip=True))

        except Exception as e:
            self.logger.warning("NAP extraction failed", url=url, error=str(e))

        return nap

    def _compare_nap(self, expected: dict, found: dict) -> dict[str, Any]:
        """Compare expected NAP with found NAP."""
        differences = []

        name_match = not expected["name"] or not found["name"] or \
                     expected["name"] in found["name"].lower() or \
                     found["name"].lower() in expected["name"]

        phone_match = not expected["phone"] or not found["phone"] or \
                      expected["phone"] == found["phone"]

        address_match = not expected["address"] or not found["address"] or \
                        self._address_similarity(expected["address"], found["address"]) > 0.7

        if not name_match:
            differences.append({"field": "name", "expected": expected["name"], "found": found["name"]})
        if not phone_match:
            differences.append({"field": "phone", "expected": expected["phone"], "found": found["phone"]})
        if not address_match:
            differences.append({"field": "address", "expected": expected["address"], "found": found["address"]})

        return {
            "all_match": len(differences) == 0,
            "name_match": name_match,
            "phone_match": phone_match,
            "address_match": address_match,
            "differences": differences,
        }

    def _address_similarity(self, addr1: str, addr2: str) -> float:
        """Calculate similarity between two addresses."""
        words1 = set(addr1.lower().split())
        words2 = set(addr2.lower().split())

        if not words1 or not words2:
            return 0

        intersection = words1 & words2
        union = words1 | words2

        return len(intersection) / len(union)

    async def _generate_local_schema(self, params: dict[str, Any]) -> dict[str, Any]:
        """Generate LocalBusiness schema markup."""
        import json

        business_type = params.get("business_type", "LocalBusiness")
        business_name = params.get("business_name", "")
        address = params.get("address", {})
        phone = params.get("phone", "")
        website = params.get("website", "")
        opening_hours = params.get("opening_hours", [])
        geo = params.get("geo", {})
        price_range = params.get("price_range", "")
        description = params.get("description", "")
        images = params.get("images", [])

        # Build schema
        schema = {
            "@context": "https://schema.org",
            "@type": business_type,
            "name": business_name,
            "url": website,
            "telephone": phone,
            "description": description,
        }

        # Add address
        if address:
            schema["address"] = {
                "@type": "PostalAddress",
                "streetAddress": address.get("street", ""),
                "addressLocality": address.get("city", ""),
                "addressRegion": address.get("state", ""),
                "postalCode": address.get("zip", ""),
                "addressCountry": address.get("country", ""),
            }

        # Add geo coordinates
        if geo and geo.get("lat") and geo.get("lng"):
            schema["geo"] = {
                "@type": "GeoCoordinates",
                "latitude": geo["lat"],
                "longitude": geo["lng"],
            }

        # Add opening hours
        if opening_hours:
            schema["openingHoursSpecification"] = [
                {
                    "@type": "OpeningHoursSpecification",
                    "dayOfWeek": hours.get("days", []),
                    "opens": hours.get("opens", ""),
                    "closes": hours.get("closes", ""),
                }
                for hours in opening_hours
            ]

        # Add price range
        if price_range:
            schema["priceRange"] = price_range

        # Add images
        if images:
            schema["image"] = images

        # Clean empty values
        schema = {k: v for k, v in schema.items() if v}

        return {
            "data": {
                "schema": schema,
                "schema_json": json.dumps(schema, indent=2),
                "business_type": business_type,
            },
            "recommendations": [
                Recommendation(
                    title="Add LocalBusiness schema to your website",
                    description="Insert this JSON-LD in a <script type='application/ld+json'> tag on every local landing page",
                    priority=Priority.HIGH,
                    category="local_seo",
                ),
            ],
        }

    async def _find_citation_opportunities(self, params: dict[str, Any]) -> dict[str, Any]:
        """Find local citation and directory opportunities."""
        business_name = params.get("business_name", "")
        location = params.get("location", "")  # City, State
        industry = params.get("industry", "")

        # Major citation sources by category
        citation_sources = {
            "general": [
                {"name": "Google Business Profile", "url": "https://business.google.com", "priority": "critical"},
                {"name": "Bing Places", "url": "https://www.bingplaces.com", "priority": "high"},
                {"name": "Apple Maps", "url": "https://mapsconnect.apple.com", "priority": "high"},
                {"name": "Yelp", "url": "https://biz.yelp.com", "priority": "high"},
                {"name": "Facebook Business", "url": "https://www.facebook.com/business", "priority": "high"},
                {"name": "LinkedIn Company", "url": "https://www.linkedin.com/company", "priority": "medium"},
                {"name": "Yellow Pages", "url": "https://www.yellowpages.com", "priority": "medium"},
                {"name": "BBB", "url": "https://www.bbb.org", "priority": "medium"},
                {"name": "Foursquare", "url": "https://foursquare.com", "priority": "low"},
            ],
            "healthcare": [
                {"name": "Healthgrades", "url": "https://www.healthgrades.com", "priority": "high"},
                {"name": "Zocdoc", "url": "https://www.zocdoc.com", "priority": "high"},
                {"name": "Vitals", "url": "https://www.vitals.com", "priority": "medium"},
            ],
            "restaurant": [
                {"name": "TripAdvisor", "url": "https://www.tripadvisor.com", "priority": "high"},
                {"name": "OpenTable", "url": "https://www.opentable.com", "priority": "high"},
                {"name": "Zomato", "url": "https://www.zomato.com", "priority": "medium"},
            ],
            "retail": [
                {"name": "Google Shopping", "url": "https://merchants.google.com", "priority": "high"},
                {"name": "Amazon", "url": "https://sellercentral.amazon.com", "priority": "high"},
            ],
            "legal": [
                {"name": "Avvo", "url": "https://www.avvo.com", "priority": "high"},
                {"name": "FindLaw", "url": "https://www.findlaw.com", "priority": "high"},
                {"name": "Martindale", "url": "https://www.martindale.com", "priority": "medium"},
            ],
            "real_estate": [
                {"name": "Zillow", "url": "https://www.zillow.com", "priority": "high"},
                {"name": "Realtor.com", "url": "https://www.realtor.com", "priority": "high"},
            ],
        }

        # Collect relevant sources
        opportunities = citation_sources["general"].copy()

        # Add industry-specific sources
        industry_lower = industry.lower()
        for category, sources in citation_sources.items():
            if category != "general" and category in industry_lower:
                opportunities.extend(sources)

        # Group by priority
        critical = [o for o in opportunities if o["priority"] == "critical"]
        high = [o for o in opportunities if o["priority"] == "high"]
        medium = [o for o in opportunities if o["priority"] == "medium"]
        low = [o for o in opportunities if o["priority"] == "low"]

        recommendations = []

        if critical:
            recommendations.append(Recommendation(
                title=f"{len(critical)} critical citations to claim",
                description="These are must-have citations for any local business",
                priority=Priority.CRITICAL,
                category="local_citations",
                data={"citations": critical},
            ))

        if high:
            recommendations.append(Recommendation(
                title=f"{len(high)} high-priority citation opportunities",
                description="Claiming these will significantly boost local visibility",
                priority=Priority.HIGH,
                category="local_citations",
            ))

        return {
            "data": {
                "total_opportunities": len(opportunities),
                "by_priority": {
                    "critical": critical,
                    "high": high,
                    "medium": medium,
                    "low": low,
                },
                "industry": industry,
                "location": location,
            },
            "recommendations": recommendations,
        }

    async def _analyze_local_serp(self, params: dict[str, Any]) -> dict[str, Any]:
        """Analyze local SERP features for target queries."""
        queries = params.get("queries", [])
        location = params.get("location", "")

        if not self.context.serp_client:
            return {"data": {"error": "SERP client not configured"}, "recommendations": []}

        results = []
        recommendations = []

        for query in queries[:10]:
            try:
                # Add location to query if not present
                local_query = f"{query} {location}" if location and location.lower() not in query.lower() else query

                serp = await self.context.serp_client.get_serp(local_query)

                result = {
                    "query": query,
                    "local_query": local_query,
                    "has_local_pack": False,
                    "has_maps": False,
                    "local_pack_position": None,
                    "organic_position": None,
                }

                if serp:
                    # Check for local pack
                    if hasattr(serp, 'local_pack') and serp.local_pack:
                        result["has_local_pack"] = True
                        result["local_pack_count"] = len(serp.local_pack)

                        # Check if client is in local pack
                        if self.context.client_domain:
                            for i, listing in enumerate(serp.local_pack):
                                if self.context.client_domain in str(listing):
                                    result["local_pack_position"] = i + 1
                                    break

                    # Check organic position
                    if hasattr(serp, 'organic_results'):
                        for i, r in enumerate(serp.organic_results[:10]):
                            if self.context.client_domain and self.context.client_domain in r.get("url", ""):
                                result["organic_position"] = i + 1
                                break

                results.append(result)

            except Exception as e:
                self.logger.warning("Local SERP analysis failed", query=query, error=str(e))

        # Analyze results
        queries_with_local_pack = [r for r in results if r["has_local_pack"]]
        in_local_pack = [r for r in results if r.get("local_pack_position")]

        if queries_with_local_pack and not in_local_pack:
            recommendations.append(Recommendation(
                title="Not appearing in Local Pack",
                description=f"{len(queries_with_local_pack)} queries show Local Pack but you're not in it. Optimize GMB.",
                priority=Priority.HIGH,
                category="local_seo",
            ))

        return {
            "data": {
                "queries_analyzed": len(results),
                "queries_with_local_pack": len(queries_with_local_pack),
                "appearing_in_local_pack": len(in_local_pack),
                "results": results,
            },
            "recommendations": recommendations,
        }

    async def _audit_gbp_optimization(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Audit Google Business Profile optimization.

        Note: Full GBP audit requires Google Business Profile API access.
        This provides a checklist-based audit.
        """
        business_info = params.get("business_info", {})

        # GBP optimization checklist
        checklist = [
            {"item": "Business name claimed", "field": "name", "weight": 10},
            {"item": "Primary category set", "field": "category", "weight": 10},
            {"item": "Secondary categories added", "field": "secondary_categories", "weight": 5},
            {"item": "Complete address", "field": "address", "weight": 10},
            {"item": "Phone number added", "field": "phone", "weight": 8},
            {"item": "Website URL added", "field": "website", "weight": 8},
            {"item": "Business hours set", "field": "hours", "weight": 7},
            {"item": "Business description (750+ chars)", "field": "description", "weight": 8},
            {"item": "Logo uploaded", "field": "logo", "weight": 5},
            {"item": "Cover photo uploaded", "field": "cover_photo", "weight": 5},
            {"item": "Interior photos (3+)", "field": "interior_photos", "weight": 5},
            {"item": "Exterior photos (3+)", "field": "exterior_photos", "weight": 5},
            {"item": "Product/service photos", "field": "product_photos", "weight": 5},
            {"item": "Services listed", "field": "services", "weight": 7},
            {"item": "Products listed", "field": "products", "weight": 5},
            {"item": "Attributes completed", "field": "attributes", "weight": 5},
            {"item": "Q&A section monitored", "field": "qa_active", "weight": 3},
            {"item": "Posts published regularly", "field": "posts_active", "weight": 5},
            {"item": "Reviews responded to", "field": "reviews_responded", "weight": 8},
        ]

        completed = []
        missing = []
        total_weight = sum(item["weight"] for item in checklist)
        earned_weight = 0

        for item in checklist:
            field = item["field"]
            value = business_info.get(field)

            # Special checks
            if field == "description":
                is_complete = value and len(str(value)) >= 750
            elif field in ["interior_photos", "exterior_photos"]:
                is_complete = value and len(value) >= 3
            elif field == "secondary_categories":
                is_complete = value and len(value) >= 2
            else:
                is_complete = bool(value)

            if is_complete:
                completed.append(item["item"])
                earned_weight += item["weight"]
            else:
                missing.append({
                    "item": item["item"],
                    "priority": "high" if item["weight"] >= 8 else "medium" if item["weight"] >= 5 else "low",
                })

        optimization_score = (earned_weight / total_weight * 100) if total_weight > 0 else 0

        recommendations = []
        high_priority_missing = [m for m in missing if m["priority"] == "high"]

        if high_priority_missing:
            recommendations.append(Recommendation(
                title=f"{len(high_priority_missing)} high-priority GBP items missing",
                description="Complete these items to significantly improve local visibility",
                priority=Priority.HIGH,
                category="gbp_optimization",
                data={"items": [m["item"] for m in high_priority_missing]},
            ))

        if optimization_score < 80:
            recommendations.append(Recommendation(
                title=f"GBP optimization score: {optimization_score:.0f}%",
                description="Aim for 90%+ optimization for best local ranking potential",
                priority=Priority.MEDIUM,
                category="gbp_optimization",
            ))

        return {
            "data": {
                "optimization_score": round(optimization_score, 1),
                "completed_items": len(completed),
                "missing_items": len(missing),
                "completed": completed,
                "missing": missing,
            },
            "recommendations": recommendations,
        }

    async def _check_local_rankings(self, params: dict[str, Any]) -> dict[str, Any]:
        """Check rankings for local keywords."""
        keywords = params.get("keywords", [])
        location = params.get("location", "")

        if not self.context.gsc_client:
            return {"data": {"error": "GSC client not configured"}, "recommendations": []}

        try:
            from datetime import datetime, timedelta

            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=28)

            # Add location modifiers to keywords
            local_keywords = []
            for kw in keywords:
                local_keywords.append(kw)
                if location:
                    local_keywords.append(f"{kw} {location}")
                    local_keywords.append(f"{kw} near me")

            # Get ranking data
            data = await self.context.gsc_client.get_performance(
                property_url=self.context.property_url,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                dimensions=["query"],
            )

            # Filter for local keywords
            rankings = []
            for row in data.get("rows", []):
                query = row.get("query", "").lower()
                for kw in local_keywords:
                    if kw.lower() in query or query in kw.lower():
                        rankings.append({
                            "query": row.get("query"),
                            "position": round(row.get("position", 0), 1),
                            "clicks": row.get("clicks", 0),
                            "impressions": row.get("impressions", 0),
                            "ctr": round(row.get("clicks", 0) / max(row.get("impressions", 1), 1) * 100, 2),
                        })
                        break

            # Sort by impressions
            rankings.sort(key=lambda x: x["impressions"], reverse=True)

            recommendations = []

            # Check for "near me" queries
            near_me = [r for r in rankings if "near me" in r["query"].lower()]
            if not near_me and keywords:
                recommendations.append(Recommendation(
                    title="Optimize for 'near me' searches",
                    description="No 'near me' queries found. Add local signals and schema markup.",
                    priority=Priority.MEDIUM,
                    category="local_seo",
                ))

            # Check average position
            if rankings:
                avg_position = sum(r["position"] for r in rankings) / len(rankings)
                if avg_position > 10:
                    recommendations.append(Recommendation(
                        title=f"Local keyword average position: {avg_position:.1f}",
                        description="Average position is outside page 1. Focus on local optimization.",
                        priority=Priority.HIGH,
                        category="local_seo",
                    ))

            return {
                "data": {
                    "keywords_checked": len(local_keywords),
                    "rankings_found": len(rankings),
                    "rankings": rankings[:30],
                    "location": location,
                },
                "recommendations": recommendations,
            }

        except Exception as e:
            self.logger.error("Local ranking check failed", error=str(e))
            return {"data": {"error": str(e)}, "recommendations": []}
