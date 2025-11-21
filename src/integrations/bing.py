"""Bing Web Search API integration for multi-engine tracking."""

import asyncio
from typing import Any

import httpx
import structlog
from pydantic import BaseModel, SecretStr
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger()


class BingSettings(BaseModel):
    """Bing API configuration."""
    api_key: SecretStr | None = None
    endpoint: str = "https://api.bing.microsoft.com/v7.0"


class BingSearchResult(BaseModel):
    """Bing search result."""
    position: int
    url: str
    title: str
    snippet: str
    display_url: str = ""
    date_published: str | None = None


class BingWebAnswer(BaseModel):
    """Bing web answer (similar to featured snippet)."""
    type: str
    content: str
    source_url: str | None = None


class BingSearchResponse(BaseModel):
    """Complete Bing search response."""
    query: str
    total_estimated_matches: int = 0
    results: list[BingSearchResult] = []
    web_answers: list[BingWebAnswer] = []
    related_searches: list[str] = []
    has_instant_answer: bool = False
    instant_answer_content: str | None = None


class BingClient:
    """
    Bing Web Search API client.

    Gracefully degrades if API key is not configured.
    """

    def __init__(self, settings: BingSettings | None = None):
        self.settings = settings or BingSettings()
        self._available = self.settings.api_key is not None
        self.logger = logger.bind(integration="bing")

    @property
    def available(self) -> bool:
        """Check if the client is properly configured."""
        return self._available

    def _get_headers(self) -> dict[str, str]:
        """Get API headers."""
        if not self._available:
            return {}
        return {
            "Ocp-Apim-Subscription-Key": self.settings.api_key.get_secret_value(),
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def _request(
        self,
        endpoint: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Make API request with retry logic."""
        if not self._available:
            return {"error": "Bing API key not configured"}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.settings.endpoint}{endpoint}",
                headers=self._get_headers(),
                params=params,
            )
            response.raise_for_status()
            return response.json()

    async def search(
        self,
        query: str,
        market: str = "en-US",
        count: int = 10,
        safe_search: str = "Moderate",
    ) -> BingSearchResponse:
        """
        Perform a Bing web search.

        Args:
            query: Search query
            market: Market code (e.g., "en-US", "sv-SE")
            count: Number of results to return
            safe_search: "Off", "Moderate", or "Strict"
        """
        if not self._available:
            return BingSearchResponse(
                query=query,
                results=[],
            )

        try:
            data = await self._request(
                "/search",
                params={
                    "q": query,
                    "mkt": market,
                    "count": count,
                    "safeSearch": safe_search,
                    "responseFilter": "Webpages,RelatedSearches,Computation",
                },
            )

            # Parse web results
            web_pages = data.get("webPages", {})
            results = []

            for i, item in enumerate(web_pages.get("value", [])):
                results.append(BingSearchResult(
                    position=i + 1,
                    url=item.get("url", ""),
                    title=item.get("name", ""),
                    snippet=item.get("snippet", ""),
                    display_url=item.get("displayUrl", ""),
                    date_published=item.get("dateLastCrawled"),
                ))

            # Parse related searches
            related = data.get("relatedSearches", {})
            related_queries = [r.get("text", "") for r in related.get("value", [])]

            # Check for instant answers / computation
            has_instant = False
            instant_content = None
            web_answers = []

            if "computation" in data:
                has_instant = True
                instant_content = data["computation"].get("value", "")
                web_answers.append(BingWebAnswer(
                    type="computation",
                    content=instant_content,
                ))

            # Check for other answer types
            if "entities" in data:
                for entity in data["entities"].get("value", []):
                    web_answers.append(BingWebAnswer(
                        type="entity",
                        content=entity.get("description", ""),
                        source_url=entity.get("webSearchUrl"),
                    ))

            return BingSearchResponse(
                query=query,
                total_estimated_matches=web_pages.get("totalEstimatedMatches", 0),
                results=results,
                web_answers=web_answers,
                related_searches=related_queries,
                has_instant_answer=has_instant,
                instant_answer_content=instant_content,
            )

        except httpx.HTTPStatusError as e:
            self.logger.error("Bing API error", status=e.response.status_code)
            return BingSearchResponse(query=query)
        except Exception as e:
            self.logger.error("Bing search failed", error=str(e))
            return BingSearchResponse(query=query)

    async def check_ranking(
        self,
        query: str,
        target_domain: str,
        market: str = "en-US",
        max_results: int = 50,
    ) -> dict[str, Any]:
        """
        Check ranking position for a domain on a specific query.
        """
        if not self._available:
            return {
                "available": False,
                "error": "Bing API key not configured. Add BING_API_KEY to your environment.",
                "query": query,
                "position": None,
            }

        try:
            response = await self.search(query, market=market, count=max_results)

            position = None
            matching_url = None

            for result in response.results:
                if target_domain in result.url:
                    position = result.position
                    matching_url = result.url
                    break

            return {
                "available": True,
                "query": query,
                "target_domain": target_domain,
                "position": position,
                "matching_url": matching_url,
                "total_results": response.total_estimated_matches,
                "has_instant_answer": response.has_instant_answer,
            }

        except Exception as e:
            self.logger.error("Ranking check failed", error=str(e))
            return {
                "available": True,
                "error": str(e),
                "query": query,
                "position": None,
            }

    async def track_queries(
        self,
        queries: list[str],
        target_domain: str,
        market: str = "en-US",
        concurrency: int = 5,
    ) -> dict[str, Any]:
        """
        Track rankings for multiple queries.
        """
        if not self._available:
            return {
                "available": False,
                "error": "Bing API key not configured. Add BING_API_KEY to your environment.",
                "results": [],
            }

        semaphore = asyncio.Semaphore(concurrency)

        async def check_one(query: str) -> dict[str, Any]:
            async with semaphore:
                return await self.check_ranking(query, target_domain, market)

        results = await asyncio.gather(*[check_one(q) for q in queries])

        # Calculate summary stats
        ranked_queries = [r for r in results if r.get("position")]
        avg_position = (
            sum(r["position"] for r in ranked_queries) / len(ranked_queries)
            if ranked_queries else None
        )

        return {
            "available": True,
            "target_domain": target_domain,
            "queries_tracked": len(queries),
            "queries_ranked": len(ranked_queries),
            "average_position": round(avg_position, 1) if avg_position else None,
            "results": results,
        }

    async def compare_with_google(
        self,
        query: str,
        target_domain: str,
        google_position: int | None,
        market: str = "en-US",
    ) -> dict[str, Any]:
        """
        Compare Bing ranking with Google ranking.
        """
        bing_result = await self.check_ranking(query, target_domain, market)

        bing_position = bing_result.get("position")

        comparison = {
            "query": query,
            "target_domain": target_domain,
            "google_position": google_position,
            "bing_position": bing_position,
            "position_difference": None,
            "status": "unknown",
        }

        if google_position and bing_position:
            diff = bing_position - google_position
            comparison["position_difference"] = diff

            if abs(diff) <= 2:
                comparison["status"] = "consistent"
            elif diff > 0:
                comparison["status"] = "bing_lower"  # Worse on Bing
            else:
                comparison["status"] = "bing_higher"  # Better on Bing
        elif google_position and not bing_position:
            comparison["status"] = "not_ranked_bing"
        elif bing_position and not google_position:
            comparison["status"] = "not_ranked_google"

        return comparison

    async def get_related_searches(
        self,
        query: str,
        market: str = "en-US",
    ) -> dict[str, Any]:
        """Get related searches for keyword research."""
        if not self._available:
            return {
                "available": False,
                "error": "Bing API key not configured",
                "related_searches": [],
            }

        try:
            response = await self.search(query, market=market)

            return {
                "available": True,
                "query": query,
                "related_searches": response.related_searches,
            }

        except Exception as e:
            return {
                "available": True,
                "error": str(e),
                "related_searches": [],
            }


def get_bing_client(api_key: str | None = None) -> BingClient:
    """Factory function to create Bing client."""
    settings = BingSettings(
        api_key=SecretStr(api_key) if api_key else None
    )
    return BingClient(settings)
