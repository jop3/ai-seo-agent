"""Ahrefs API integration for backlink analysis."""

import asyncio
from typing import Any

import httpx
import structlog
from pydantic import BaseModel, SecretStr
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger()


class AhrefsSettings(BaseModel):
    """Ahrefs API configuration."""
    api_key: SecretStr | None = None
    base_url: str = "https://api.ahrefs.com/v3"


class BacklinkData(BaseModel):
    """Backlink information."""
    url_from: str
    url_to: str
    anchor: str
    domain_rating: int = 0
    url_rating: int = 0
    is_dofollow: bool = True
    first_seen: str | None = None
    last_seen: str | None = None


class BrokenBacklink(BaseModel):
    """Broken backlink opportunity."""
    source_url: str
    source_domain: str
    broken_url: str
    anchor_text: str
    domain_rating: int = 0
    traffic: int = 0


class UnlinkedMention(BaseModel):
    """Unlinked brand mention."""
    page_url: str
    page_title: str
    domain: str
    domain_rating: int = 0
    mention_context: str
    discovered_date: str | None = None


class AhrefsClient:
    """
    Ahrefs API client for backlink and content analysis.

    Gracefully degrades if API key is not configured.
    """

    def __init__(self, settings: AhrefsSettings | None = None):
        self.settings = settings or AhrefsSettings()
        self._available = self.settings.api_key is not None
        self.logger = logger.bind(integration="ahrefs")

    @property
    def available(self) -> bool:
        """Check if the client is properly configured."""
        return self._available

    def _get_headers(self) -> dict[str, str]:
        """Get API headers."""
        if not self._available:
            return {}
        return {
            "Authorization": f"Bearer {self.settings.api_key.get_secret_value()}",
            "Content-Type": "application/json",
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make API request with retry logic."""
        if not self._available:
            return {"error": "Ahrefs API key not configured"}

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.request(
                method,
                f"{self.settings.base_url}{endpoint}",
                headers=self._get_headers(),
                params=params,
                json=json_data,
            )
            response.raise_for_status()
            return response.json()

    async def get_backlinks(
        self,
        target: str,
        mode: str = "domain",
        limit: int = 100,
    ) -> dict[str, Any]:
        """
        Get backlinks for a target URL or domain.

        Args:
            target: URL or domain to analyze
            mode: "domain", "subdomains", "prefix", or "exact"
            limit: Maximum number of backlinks to return
        """
        if not self._available:
            return {
                "available": False,
                "error": "Ahrefs API key not configured. Add AHREFS_API_KEY to your environment.",
                "backlinks": [],
            }

        try:
            data = await self._request(
                "GET",
                "/site-explorer/all-backlinks",
                params={
                    "target": target,
                    "mode": mode,
                    "limit": limit,
                    "select": "url_from,url_to,anchor,domain_rating,url_rating,is_dofollow,first_seen,last_seen",
                },
            )

            backlinks = [
                BacklinkData(
                    url_from=item.get("url_from", ""),
                    url_to=item.get("url_to", ""),
                    anchor=item.get("anchor", ""),
                    domain_rating=item.get("domain_rating", 0),
                    url_rating=item.get("url_rating", 0),
                    is_dofollow=item.get("is_dofollow", True),
                    first_seen=item.get("first_seen"),
                    last_seen=item.get("last_seen"),
                ).model_dump()
                for item in data.get("backlinks", [])
            ]

            return {
                "available": True,
                "target": target,
                "total_backlinks": data.get("total", len(backlinks)),
                "backlinks": backlinks,
            }

        except httpx.HTTPStatusError as e:
            self.logger.error("Ahrefs API error", status=e.response.status_code)
            return {"available": True, "error": f"API error: {e.response.status_code}", "backlinks": []}
        except Exception as e:
            self.logger.error("Ahrefs request failed", error=str(e))
            return {"available": True, "error": str(e), "backlinks": []}

    async def get_broken_backlinks(
        self,
        target: str,
        limit: int = 100,
    ) -> dict[str, Any]:
        """
        Find broken backlinks (links pointing to 404 pages on target).

        Useful for reclaiming lost link equity.
        """
        if not self._available:
            return {
                "available": False,
                "error": "Ahrefs API key not configured. Add AHREFS_API_KEY to your environment.",
                "broken_backlinks": [],
            }

        try:
            data = await self._request(
                "GET",
                "/site-explorer/broken-backlinks",
                params={
                    "target": target,
                    "mode": "domain",
                    "limit": limit,
                },
            )

            broken = [
                BrokenBacklink(
                    source_url=item.get("url_from", ""),
                    source_domain=item.get("domain_from", ""),
                    broken_url=item.get("url_to", ""),
                    anchor_text=item.get("anchor", ""),
                    domain_rating=item.get("domain_rating", 0),
                    traffic=item.get("traffic", 0),
                ).model_dump()
                for item in data.get("backlinks", [])
            ]

            return {
                "available": True,
                "target": target,
                "total_broken": len(broken),
                "broken_backlinks": broken,
            }

        except Exception as e:
            self.logger.error("Broken backlinks request failed", error=str(e))
            return {"available": True, "error": str(e), "broken_backlinks": []}

    async def find_competitor_backlinks(
        self,
        competitors: list[str],
        your_domain: str,
        limit_per_competitor: int = 50,
    ) -> dict[str, Any]:
        """
        Find backlinks that competitors have but you don't.

        Great for finding link building opportunities.
        """
        if not self._available:
            return {
                "available": False,
                "error": "Ahrefs API key not configured. Add AHREFS_API_KEY to your environment.",
                "opportunities": [],
            }

        try:
            # Get your backlinks first
            your_data = await self.get_backlinks(your_domain, limit=1000)
            your_linking_domains = set()

            if your_data.get("backlinks"):
                for bl in your_data["backlinks"]:
                    from urllib.parse import urlparse
                    domain = urlparse(bl.get("url_from", "")).netloc
                    your_linking_domains.add(domain)

            # Find competitor-exclusive backlinks
            opportunities = []

            for competitor in competitors:
                comp_data = await self.get_backlinks(competitor, limit=limit_per_competitor)

                for bl in comp_data.get("backlinks", []):
                    from urllib.parse import urlparse
                    source_domain = urlparse(bl.get("url_from", "")).netloc

                    if source_domain not in your_linking_domains:
                        opportunities.append({
                            "source_url": bl.get("url_from", ""),
                            "source_domain": source_domain,
                            "links_to_competitor": competitor,
                            "anchor_text": bl.get("anchor", ""),
                            "domain_rating": bl.get("domain_rating", 0),
                        })

            # Sort by domain rating
            opportunities.sort(key=lambda x: x.get("domain_rating", 0), reverse=True)

            return {
                "available": True,
                "your_domain": your_domain,
                "competitors_analyzed": competitors,
                "total_opportunities": len(opportunities),
                "opportunities": opportunities[:100],  # Top 100
            }

        except Exception as e:
            self.logger.error("Competitor backlink analysis failed", error=str(e))
            return {"available": True, "error": str(e), "opportunities": []}

    async def find_unlinked_mentions(
        self,
        brand_name: str,
        domain: str,
        limit: int = 100,
    ) -> dict[str, Any]:
        """
        Find pages that mention your brand but don't link to you.

        Uses Ahrefs Content Explorer API.
        """
        if not self._available:
            return {
                "available": False,
                "error": "Ahrefs API key not configured. Add AHREFS_API_KEY to your environment.",
                "mentions": [],
            }

        try:
            # Search for brand mentions excluding your own domain
            data = await self._request(
                "GET",
                "/content-explorer/search",
                params={
                    "query": f'"{brand_name}" -site:{domain}',
                    "limit": limit,
                    "select": "url,title,domain,domain_rating,content",
                },
            )

            mentions = []
            for item in data.get("results", []):
                # Check if they already link to us (would need additional check)
                mentions.append(
                    UnlinkedMention(
                        page_url=item.get("url", ""),
                        page_title=item.get("title", ""),
                        domain=item.get("domain", ""),
                        domain_rating=item.get("domain_rating", 0),
                        mention_context=item.get("content", "")[:200],
                        discovered_date=item.get("date"),
                    ).model_dump()
                )

            return {
                "available": True,
                "brand_name": brand_name,
                "total_mentions": len(mentions),
                "mentions": mentions,
            }

        except Exception as e:
            self.logger.error("Unlinked mentions search failed", error=str(e))
            return {"available": True, "error": str(e), "mentions": []}

    async def get_domain_rating(self, domain: str) -> dict[str, Any]:
        """Get domain rating and basic metrics."""
        if not self._available:
            return {
                "available": False,
                "error": "Ahrefs API key not configured",
                "domain_rating": None,
            }

        try:
            data = await self._request(
                "GET",
                "/site-explorer/domain-rating",
                params={"target": domain},
            )

            return {
                "available": True,
                "domain": domain,
                "domain_rating": data.get("domain_rating", 0),
                "ahrefs_rank": data.get("ahrefs_rank"),
            }

        except Exception as e:
            self.logger.error("Domain rating request failed", error=str(e))
            return {"available": True, "error": str(e), "domain_rating": None}

    async def get_referring_domains(
        self,
        target: str,
        limit: int = 100,
    ) -> dict[str, Any]:
        """Get list of referring domains with metrics."""
        if not self._available:
            return {
                "available": False,
                "error": "Ahrefs API key not configured",
                "referring_domains": [],
            }

        try:
            data = await self._request(
                "GET",
                "/site-explorer/refdomains",
                params={
                    "target": target,
                    "mode": "domain",
                    "limit": limit,
                    "select": "domain,domain_rating,backlinks,first_seen,last_seen",
                },
            )

            domains = [
                {
                    "domain": item.get("domain", ""),
                    "domain_rating": item.get("domain_rating", 0),
                    "backlinks": item.get("backlinks", 0),
                    "first_seen": item.get("first_seen"),
                    "last_seen": item.get("last_seen"),
                }
                for item in data.get("refdomains", [])
            ]

            return {
                "available": True,
                "target": target,
                "total_referring_domains": data.get("total", len(domains)),
                "referring_domains": domains,
            }

        except Exception as e:
            self.logger.error("Referring domains request failed", error=str(e))
            return {"available": True, "error": str(e), "referring_domains": []}


def get_ahrefs_client(api_key: str | None = None) -> AhrefsClient:
    """Factory function to create Ahrefs client."""
    settings = AhrefsSettings(
        api_key=SecretStr(api_key) if api_key else None
    )
    return AhrefsClient(settings)
