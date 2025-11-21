"""
Link Analysis Agent - Identifies citation and link building opportunities.
"""

from datetime import datetime
from typing import Any

import httpx
import structlog
from bs4 import BeautifulSoup

from src.agents.base import BaseAgent, AgentContext
from src.models.agents import AgentTask, AgentResult, Recommendation, Alert, Priority, Severity

logger = structlog.get_logger()


class LinkAnalysisAgent(BaseAgent):
    """
    Analyzes link profile and identifies opportunities.

    Capabilities:
    - Find unlinked brand mentions
    - Identify citation opportunities from AIO sources
    - Analyze competitor backlinks
    - Find broken link opportunities
    - Suggest internal linking improvements
    """

    def __init__(self, context: AgentContext):
        super().__init__(
            agent_type="link-analysis",
            description="Analyzes link opportunities and citation sources",
            context=context,
        )

    async def run(self, task: AgentTask) -> AgentResult:
        """Execute link analysis task."""
        start_time = datetime.utcnow()

        try:
            if task.task_type == "find_citation_opportunities":
                result = await self._find_citation_opportunities(task.parameters)
            elif task.task_type == "analyze_aio_sources":
                result = await self._analyze_aio_sources(task.parameters)
            elif task.task_type == "find_unlinked_mentions":
                result = await self._find_unlinked_mentions(task.parameters)
            elif task.task_type == "internal_link_analysis":
                result = await self._internal_link_analysis(task.parameters)
            elif task.task_type == "competitor_backlinks":
                result = await self._analyze_competitor_backlinks(task.parameters)
            else:
                return AgentResult(
                    task_id=task.id,
                    agent_type=self.agent_type,
                    success=False,
                    data={"error": f"Unknown task type: {task.task_type}"},
                )

            return AgentResult(
                task_id=task.id,
                agent_type=self.agent_type,
                success=True,
                data=result["data"],
                recommendations=result.get("recommendations", []),
                alerts=result.get("alerts", []),
                execution_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
            )

        except Exception as e:
            logger.error("Link analysis failed", error=str(e))
            return AgentResult(
                task_id=task.id,
                agent_type=self.agent_type,
                success=False,
                data={"error": str(e)},
            )

    async def _find_citation_opportunities(self, params: dict[str, Any]) -> dict[str, Any]:
        """Find opportunities to get cited in AI Overviews."""
        queries = params.get("queries", [])

        opportunities = []
        recommendations = []

        if not self.context.serp_client:
            return {
                "data": {"error": "SERP client not configured"},
                "recommendations": [],
            }

        for query in queries:
            try:
                serp = await self.context.serp_client.get_serp(query)

                if serp and serp.ai_overview:
                    # Analyze current citations
                    current_citations = serp.ai_overview.get("citations", [])
                    client_cited = any(
                        self.context.client_domain in c
                        for c in current_citations
                    ) if self.context.client_domain else False

                    if not client_cited and current_citations:
                        # Analyze what type of content is being cited
                        opportunity = {
                            "query": query,
                            "current_citations": current_citations,
                            "citation_types": self._analyze_citation_types(current_citations),
                            "content_suggestions": [],
                        }

                        # Use LLM to suggest content improvements
                        if self.context.openai_client:
                            suggestions = await self._get_content_suggestions(
                                query,
                                serp.ai_overview.get("content", ""),
                                current_citations,
                            )
                            opportunity["content_suggestions"] = suggestions

                        opportunities.append(opportunity)

            except Exception as e:
                logger.warning("Citation analysis failed", query=query, error=str(e))

        # Generate recommendations
        if opportunities:
            recommendations.append(Recommendation(
                title=f"Found {len(opportunities)} AIO citation opportunities",
                description="Create or optimize content matching the citation patterns of current AIO sources",
                priority=Priority.HIGH,
                category="link_building",
                estimated_impact="high",
            ))

        return {
            "data": {
                "opportunities": opportunities,
                "total_found": len(opportunities),
            },
            "recommendations": recommendations,
        }

    def _analyze_citation_types(self, citations: list[str]) -> dict[str, int]:
        """Categorize citation sources."""
        types = {
            "government": 0,
            "medical": 0,
            "news": 0,
            "educational": 0,
            "commercial": 0,
            "wikipedia": 0,
            "other": 0,
        }

        for url in citations:
            url_lower = url.lower()
            if ".gov" in url_lower:
                types["government"] += 1
            elif any(d in url_lower for d in [".edu", "university", "college"]):
                types["educational"] += 1
            elif "wikipedia" in url_lower:
                types["wikipedia"] += 1
            elif any(d in url_lower for d in ["news", "bbc", "cnn", "reuters", "nytimes"]):
                types["news"] += 1
            elif any(d in url_lower for d in ["nih.gov", "webmd", "mayoclinic", "healthline"]):
                types["medical"] += 1
            else:
                types["commercial"] += 1

        return {k: v for k, v in types.items() if v > 0}

    async def _get_content_suggestions(
        self,
        query: str,
        aio_content: str,
        citations: list[str],
    ) -> list[str]:
        """Get AI-powered content suggestions."""
        if not self.context.openai_client:
            return []

        prompt = f"""Analyze this AI Overview and its citations to suggest how a website could get cited:

Query: {query}

AI Overview content:
{aio_content[:1000]}

Current citations:
{chr(10).join(citations[:5])}

Suggest 3-5 specific content improvements or new content pieces that could earn a citation.
Focus on:
1. Content format (FAQ, how-to, statistics, etc.)
2. Authority signals needed
3. Specific information gaps to fill

Be concise and actionable."""

        try:
            response = await self.context.openai_client.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
            )
            return response.split("\n") if response else []
        except Exception:
            return []

    async def _analyze_aio_sources(self, params: dict[str, Any]) -> dict[str, Any]:
        """Analyze what sources are being cited in AIOs for target queries."""
        queries = params.get("queries", [])

        all_sources = {}
        domain_frequency = {}

        if self.context.serp_client:
            for query in queries:
                try:
                    serp = await self.context.serp_client.get_serp(query)
                    if serp and serp.ai_overview:
                        for citation in serp.ai_overview.get("citations", []):
                            # Extract domain
                            from urllib.parse import urlparse
                            domain = urlparse(citation).netloc

                            if domain not in all_sources:
                                all_sources[domain] = {"urls": [], "queries": []}

                            all_sources[domain]["urls"].append(citation)
                            all_sources[domain]["queries"].append(query)

                            domain_frequency[domain] = domain_frequency.get(domain, 0) + 1

                except Exception as e:
                    logger.warning("AIO source analysis failed", query=query, error=str(e))

        # Sort by frequency
        top_sources = sorted(
            domain_frequency.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:20]

        return {
            "data": {
                "sources": all_sources,
                "top_cited_domains": top_sources,
                "total_unique_domains": len(all_sources),
            },
            "recommendations": [],
        }

    async def _find_unlinked_mentions(self, params: dict[str, Any]) -> dict[str, Any]:
        """Find unlinked brand mentions (would integrate with brand monitoring API)."""
        brand_name = params.get("brand_name", "")

        # This would integrate with services like:
        # - Google Alerts
        # - Mention.com
        # - Brand24
        # - Ahrefs Content Explorer

        return {
            "data": {
                "message": "Unlinked mention detection requires brand monitoring API integration",
                "suggestion": "Integrate with Ahrefs Content Explorer or similar service",
                "brand_searched": brand_name,
            },
            "recommendations": [
                Recommendation(
                    title="Set up brand monitoring",
                    description="Configure alerts for brand mentions to find unlinked citation opportunities",
                    priority=Priority.MEDIUM,
                    category="link_building",
                ),
            ],
        }

    async def _internal_link_analysis(self, params: dict[str, Any]) -> dict[str, Any]:
        """Analyze internal linking structure."""
        url = params.get("url", self.context.property_url)
        max_pages = params.get("max_pages", 100)

        if not url:
            return {"data": {"error": "URL required"}}

        pages = {}
        internal_links = []

        async with httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={"User-Agent": "SEOAgentBot/1.0"},
        ) as client:
            from urllib.parse import urljoin, urlparse
            base_domain = urlparse(url).netloc
            to_visit = [url]
            visited = set()

            while to_visit and len(visited) < max_pages:
                current_url = to_visit.pop(0)
                if current_url in visited:
                    continue

                visited.add(current_url)

                try:
                    response = await client.get(current_url)
                    if response.status_code != 200:
                        continue

                    soup = BeautifulSoup(response.text, "lxml")

                    # Track page info
                    pages[current_url] = {
                        "title": soup.title.text if soup.title else "",
                        "inbound_links": 0,
                        "outbound_internal": 0,
                        "outbound_external": 0,
                    }

                    # Find links
                    for link in soup.find_all("a", href=True):
                        href = link["href"]
                        full_url = urljoin(current_url, href)
                        link_domain = urlparse(full_url).netloc

                        if link_domain == base_domain:
                            pages[current_url]["outbound_internal"] += 1
                            internal_links.append({
                                "from": current_url,
                                "to": full_url,
                                "anchor": link.text.strip()[:100],
                            })

                            if full_url not in visited and full_url not in to_visit:
                                to_visit.append(full_url)
                        else:
                            pages[current_url]["outbound_external"] += 1

                except Exception as e:
                    logger.warning("Page analysis failed", url=current_url, error=str(e))

        # Calculate inbound links
        for link in internal_links:
            if link["to"] in pages:
                pages[link["to"]]["inbound_links"] += 1

        # Find orphan pages (low inbound links)
        orphan_pages = [
            {"url": url, **data}
            for url, data in pages.items()
            if data["inbound_links"] < 2
        ]

        # Find hub pages (high outbound)
        hub_pages = sorted(
            [{"url": url, **data} for url, data in pages.items()],
            key=lambda x: x["outbound_internal"],
            reverse=True,
        )[:10]

        recommendations = []
        if orphan_pages:
            recommendations.append(Recommendation(
                title=f"Found {len(orphan_pages)} orphan/under-linked pages",
                description="Add more internal links to these pages to improve their authority",
                priority=Priority.MEDIUM,
                category="internal_linking",
            ))

        return {
            "data": {
                "pages_analyzed": len(pages),
                "total_internal_links": len(internal_links),
                "orphan_pages": orphan_pages[:20],
                "hub_pages": hub_pages,
            },
            "recommendations": recommendations,
        }

    async def _analyze_competitor_backlinks(self, params: dict[str, Any]) -> dict[str, Any]:
        """Analyze competitor backlinks (would integrate with Ahrefs/Moz API)."""
        competitors = params.get("competitors", [])

        # This would integrate with:
        # - Ahrefs API
        # - Moz API
        # - Majestic API

        return {
            "data": {
                "message": "Competitor backlink analysis requires SEO tool API integration",
                "suggestion": "Integrate with Ahrefs, Moz, or Majestic API",
                "competitors": competitors,
            },
            "recommendations": [
                Recommendation(
                    title="Set up backlink analysis",
                    description="Configure Ahrefs or similar API to analyze competitor backlinks",
                    priority=Priority.MEDIUM,
                    category="link_building",
                ),
            ],
        }
