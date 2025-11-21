"""
Link Analysis Agent - Identifies citation and link building opportunities.
"""

from datetime import datetime
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
import structlog
from bs4 import BeautifulSoup

from src.agents.base import BaseAgent, AgentContext
from src.core.errors import AgentError, ErrorCode
from src.models.agents import AgentTask, AgentResult, AgentType, Recommendation, Alert, Priority, Severity

logger = structlog.get_logger()


class LinkAnalysisAgent(BaseAgent):
    """
    Analyzes link profile and identifies opportunities.

    Capabilities:
    - Find unlinked brand mentions
    - Identify citation opportunities from AIO sources
    - Analyze competitor backlinks
    - Find broken link opportunities on authority sites
    - Suggest internal linking improvements
    - Analyze anchor text distribution
    """

    agent_type = AgentType.LINK_ANALYZER

    def __init__(self, context: AgentContext):
        self.context = context
        self.logger = logger.bind(agent="link-analysis")

    async def execute(self, task: AgentTask) -> AgentResult:
        """Execute link analysis task - called by base class run() with error handling."""
        task_handlers = {
            "find_citation_opportunities": self._find_citation_opportunities,
            "analyze_aio_sources": self._analyze_aio_sources,
            "find_unlinked_mentions": self._find_unlinked_mentions,
            "internal_link_analysis": self._internal_link_analysis,
            "competitor_backlinks": self._analyze_competitor_backlinks,
            "find_broken_link_opportunities": self._find_broken_link_opportunities,
            "analyze_anchor_text": self._analyze_anchor_text,
        }

        handler = task_handlers.get(task.task_type)
        if not handler:
            raise AgentError(
                f"Unknown task type: {task.task_type}",
                agent_type="link-analysis",
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

    async def _find_broken_link_opportunities(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Find broken link building opportunities.

        Scans authority pages that link to competitors or related topics,
        finds broken outbound links, and suggests replacements with your content.
        """
        target_urls = params.get("urls", [])  # Pages to scan for broken links
        topics = params.get("topics", [])  # Topics to find relevant pages
        max_pages = params.get("max_pages", 50)

        broken_opportunities = []
        recommendations = []
        pages_scanned = 0

        # If no URLs provided, try to find relevant pages from AIO citations
        if not target_urls and topics and self.context.serp_client:
            self.logger.info("Finding authority pages from AIO citations")
            for topic in topics[:5]:
                try:
                    serp = await self.context.serp_client.get_serp(topic)
                    if serp and serp.ai_overview:
                        target_urls.extend(serp.ai_overview.get("citations", [])[:10])
                except Exception as e:
                    self.logger.warning("Failed to get SERP", topic=topic, error=str(e))

        # Deduplicate
        target_urls = list(set(target_urls))[:max_pages]

        async with httpx.AsyncClient(
            timeout=15.0,
            follow_redirects=False,  # We want to detect redirects
            headers={"User-Agent": "SEOAgentBot/1.0 (checking links)"},
        ) as client:
            for page_url in target_urls:
                pages_scanned += 1

                try:
                    # Fetch the page
                    response = await client.get(page_url, follow_redirects=True)
                    if response.status_code != 200:
                        continue

                    soup = BeautifulSoup(response.text, "lxml")
                    page_domain = urlparse(page_url).netloc

                    # Find all external links
                    for link in soup.find_all("a", href=True):
                        href = link["href"]

                        # Skip internal, anchor, and javascript links
                        if href.startswith(("#", "javascript:", "mailto:", "tel:")):
                            continue

                        full_url = urljoin(page_url, href)
                        link_domain = urlparse(full_url).netloc

                        # Only check external links
                        if link_domain == page_domain:
                            continue

                        # Check if the link is broken
                        try:
                            link_response = await client.head(full_url, timeout=10.0)

                            if link_response.status_code in (404, 410, 500, 502, 503):
                                anchor_text = link.text.strip()[:100]
                                context_text = self._get_link_context(link, soup)

                                broken_opportunities.append({
                                    "source_page": page_url,
                                    "source_domain": page_domain,
                                    "broken_url": full_url,
                                    "status_code": link_response.status_code,
                                    "anchor_text": anchor_text,
                                    "context": context_text,
                                    "opportunity_score": self._calculate_opportunity_score(page_domain, anchor_text),
                                })

                        except httpx.TimeoutException:
                            # Timeout might indicate a broken link
                            broken_opportunities.append({
                                "source_page": page_url,
                                "source_domain": page_domain,
                                "broken_url": full_url,
                                "status_code": "timeout",
                                "anchor_text": link.text.strip()[:100],
                                "context": self._get_link_context(link, soup),
                                "opportunity_score": 50,
                            })
                        except Exception:
                            # Skip links we can't check
                            pass

                except httpx.TimeoutException:
                    self.logger.warning("Page fetch timeout", url=page_url)
                except Exception as e:
                    self.logger.warning("Page scan failed", url=page_url, error=str(e))

        # Sort by opportunity score
        broken_opportunities.sort(key=lambda x: x.get("opportunity_score", 0), reverse=True)

        # Generate recommendations
        if broken_opportunities:
            high_value = [o for o in broken_opportunities if o.get("opportunity_score", 0) >= 70]
            recommendations.append(Recommendation(
                title=f"Found {len(broken_opportunities)} broken link opportunities",
                description=f"{len(high_value)} high-value opportunities on authority sites. "
                           f"Create content matching the broken link topics and reach out to site owners.",
                priority=Priority.HIGH if high_value else Priority.MEDIUM,
                category="link_building",
                estimated_impact="high" if high_value else "medium",
            ))

        return {
            "data": {
                "pages_scanned": pages_scanned,
                "broken_links_found": len(broken_opportunities),
                "opportunities": broken_opportunities[:50],  # Top 50
                "top_source_domains": self._get_top_domains(broken_opportunities),
            },
            "recommendations": recommendations,
        }

    def _get_link_context(self, link_element, soup) -> str:
        """Extract context around a link for understanding its purpose."""
        # Try to get parent paragraph or list item
        parent = link_element.find_parent(["p", "li", "td", "div"])
        if parent:
            text = parent.get_text(strip=True)[:200]
            return text
        return ""

    def _calculate_opportunity_score(self, domain: str, anchor_text: str) -> int:
        """Calculate opportunity score based on domain authority signals."""
        score = 50  # Base score

        # Authority domain indicators
        authority_signals = [
            (".edu", 30),
            (".gov", 30),
            (".org", 15),
            ("university", 20),
            ("institute", 15),
            ("research", 10),
            ("foundation", 10),
        ]

        domain_lower = domain.lower()
        for signal, bonus in authority_signals:
            if signal in domain_lower:
                score += bonus
                break

        # Anchor text relevance (longer = more specific = better)
        if anchor_text and len(anchor_text) > 20:
            score += 10

        return min(score, 100)

    def _get_top_domains(self, opportunities: list[dict]) -> list[dict]:
        """Get top source domains from opportunities."""
        domain_counts = {}
        for opp in opportunities:
            domain = opp.get("source_domain", "")
            if domain:
                domain_counts[domain] = domain_counts.get(domain, 0) + 1

        sorted_domains = sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)
        return [{"domain": d, "count": c} for d, c in sorted_domains[:10]]

    async def _analyze_anchor_text(self, params: dict[str, Any]) -> dict[str, Any]:
        """Analyze internal link anchor text distribution."""
        url = params.get("url", self.context.property_url)
        max_pages = params.get("max_pages", 100)

        if not url:
            return {"data": {"error": "URL required"}, "recommendations": []}

        anchor_stats = {
            "exact_match": [],  # Anchor matches page title/h1
            "partial_match": [],
            "branded": [],
            "generic": [],  # "click here", "read more", etc.
            "naked_url": [],
            "image": [],
        }

        generic_anchors = {"click here", "read more", "learn more", "here", "link", "this", "more"}
        all_anchors = []

        async with httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={"User-Agent": "SEOAgentBot/1.0"},
        ) as client:
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

                    for link in soup.find_all("a", href=True):
                        href = link["href"]
                        full_url = urljoin(current_url, href)
                        link_domain = urlparse(full_url).netloc

                        # Only analyze internal links
                        if link_domain != base_domain:
                            continue

                        # Check if it's an image link
                        if link.find("img"):
                            anchor_type = "image"
                            anchor_text = link.find("img").get("alt", "") or "[image]"
                        else:
                            anchor_text = link.get_text(strip=True)

                            if not anchor_text:
                                anchor_type = "naked_url"
                                anchor_text = href
                            elif anchor_text.lower() in generic_anchors:
                                anchor_type = "generic"
                            elif base_domain.split(".")[0] in anchor_text.lower():
                                anchor_type = "branded"
                            else:
                                anchor_type = "partial_match"  # Default

                        anchor_data = {
                            "text": anchor_text[:100],
                            "from_url": current_url,
                            "to_url": full_url,
                            "type": anchor_type,
                        }

                        anchor_stats[anchor_type].append(anchor_data)
                        all_anchors.append(anchor_data)

                        # Queue internal links for crawling
                        if full_url not in visited and full_url not in to_visit:
                            to_visit.append(full_url)

                except Exception as e:
                    self.logger.warning("Anchor analysis failed", url=current_url, error=str(e))

        # Calculate distribution
        total = len(all_anchors) or 1
        distribution = {
            anchor_type: {
                "count": len(anchors),
                "percentage": round(len(anchors) / total * 100, 1),
            }
            for anchor_type, anchors in anchor_stats.items()
        }

        recommendations = []

        # Check for over-optimization or issues
        generic_pct = distribution["generic"]["percentage"]
        if generic_pct > 20:
            recommendations.append(Recommendation(
                title=f"High generic anchor text usage ({generic_pct}%)",
                description="Replace generic anchors like 'click here' with descriptive keyword-rich anchors",
                priority=Priority.MEDIUM,
                category="internal_linking",
            ))

        image_pct = distribution["image"]["percentage"]
        if image_pct > 15 and any(not a["text"] or a["text"] == "[image]" for a in anchor_stats["image"]):
            recommendations.append(Recommendation(
                title="Image links missing alt text",
                description="Add descriptive alt text to images used as links",
                priority=Priority.MEDIUM,
                category="internal_linking",
            ))

        return {
            "data": {
                "pages_analyzed": len(visited),
                "total_internal_links": len(all_anchors),
                "distribution": distribution,
                "top_anchors": self._get_top_anchor_texts(all_anchors),
                "generic_anchors": anchor_stats["generic"][:20],
            },
            "recommendations": recommendations,
        }

    def _get_top_anchor_texts(self, anchors: list[dict]) -> list[dict]:
        """Get most common anchor texts."""
        counts = {}
        for a in anchors:
            text = a["text"].lower().strip()
            if text and len(text) > 2:
                counts[text] = counts.get(text, 0) + 1

        sorted_anchors = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        return [{"text": t, "count": c} for t, c in sorted_anchors[:20]]
