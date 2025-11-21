"""SERP API integration with provider abstraction."""

import asyncio
import re
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any
from urllib.parse import quote_plus

import httpx
import structlog
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import SerpSettings
from src.models.seo import AIOverviewResult, SERPResult

logger = structlog.get_logger()


class SerpProvider(ABC):
    """Abstract base for SERP data providers."""

    @abstractmethod
    async def search(
        self,
        query: str,
        location: str = "Sweden",
        language: str = "sv",
        device: str = "desktop",
    ) -> dict[str, Any]:
        """Execute a search and return raw results."""
        pass

    @abstractmethod
    async def check_ai_overview(
        self,
        query: str,
        client_domain: str,
        location: str = "Sweden",
    ) -> AIOverviewResult:
        """Check if query triggers AI Overview and analyze citations."""
        pass


class SerpAPIProvider(SerpProvider):
    """SerpAPI.com provider."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://serpapi.com/search"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def search(
        self,
        query: str,
        location: str = "Sweden",
        language: str = "sv",
        device: str = "desktop",
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                self.base_url,
                params={
                    "q": query,
                    "location": location,
                    "hl": language,
                    "gl": "se",
                    "device": device,
                    "api_key": self.api_key,
                },
            )
            response.raise_for_status()
            return response.json()

    async def check_ai_overview(
        self,
        query: str,
        client_domain: str,
        location: str = "Sweden",
    ) -> AIOverviewResult:
        data = await self.search(query, location)

        # Check for AI Overview in response
        ai_overview = data.get("ai_overview", {})
        has_aio = bool(ai_overview)

        citations = []
        client_cited = False
        client_position = None

        if has_aio:
            # Extract citations from AI Overview
            for i, source in enumerate(ai_overview.get("sources", [])):
                url = source.get("link", "")
                citations.append(url)
                if client_domain in url:
                    client_cited = True
                    client_position = i + 1

        # Parse organic results
        organic_results = []
        for result in data.get("organic_results", [])[:10]:
            organic_results.append(
                SERPResult(
                    position=result.get("position", 0),
                    url=result.get("link", ""),
                    title=result.get("title", ""),
                    snippet=result.get("snippet", ""),
                    is_featured=result.get("featured_snippet", False),
                )
            )

        # Identify competitor citations
        competitor_citations = [c for c in citations if client_domain not in c]

        return AIOverviewResult(
            query=query,
            has_aio=has_aio,
            aio_content=ai_overview.get("text"),
            citations=citations,
            client_cited=client_cited,
            client_citation_position=client_position,
            competitor_citations=competitor_citations,
            organic_results=organic_results,
        )


class DataForSEOProvider(SerpProvider):
    """DataForSEO provider."""

    def __init__(self, login: str, password: str):
        self.login = login
        self.password = password
        self.base_url = "https://api.dataforseo.com/v3"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def search(
        self,
        query: str,
        location: str = "Sweden",
        language: str = "sv",
        device: str = "desktop",
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/serp/google/organic/live/advanced",
                auth=(self.login, self.password),
                json=[
                    {
                        "keyword": query,
                        "location_name": location,
                        "language_code": language,
                        "device": device,
                    }
                ],
            )
            response.raise_for_status()
            return response.json()

    async def check_ai_overview(
        self,
        query: str,
        client_domain: str,
        location: str = "Sweden",
    ) -> AIOverviewResult:
        data = await self.search(query, location)

        # Parse DataForSEO response structure
        tasks = data.get("tasks", [])
        if not tasks:
            return AIOverviewResult(query=query, has_aio=False)

        result = tasks[0].get("result", [{}])[0]
        items = result.get("items", [])

        has_aio = False
        aio_content = None
        citations = []
        client_cited = False
        client_position = None
        organic_results = []

        for item in items:
            item_type = item.get("type")

            if item_type == "ai_overview":
                has_aio = True
                aio_content = item.get("text", "")
                for i, ref in enumerate(item.get("references", [])):
                    url = ref.get("url", "")
                    citations.append(url)
                    if client_domain in url:
                        client_cited = True
                        client_position = i + 1

            elif item_type == "organic":
                organic_results.append(
                    SERPResult(
                        position=item.get("rank_absolute", 0),
                        url=item.get("url", ""),
                        title=item.get("title", ""),
                        snippet=item.get("description", ""),
                    )
                )

        competitor_citations = [c for c in citations if client_domain not in c]

        return AIOverviewResult(
            query=query,
            has_aio=has_aio,
            aio_content=aio_content,
            citations=citations,
            client_cited=client_cited,
            client_citation_position=client_position,
            competitor_citations=competitor_citations,
            organic_results=organic_results[:10],
        )


class ScraperProvider(SerpProvider):
    """
    Free scraper-based provider (for development/testing).
    Note: For production, use a proper API to avoid rate limits and blocks.
    """

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=20))
    async def search(
        self,
        query: str,
        location: str = "Sweden",
        language: str = "sv",
        device: str = "desktop",
    ) -> dict[str, Any]:
        """
        Basic Google scraping - use sparingly and only for development.
        """
        encoded_query = quote_plus(query)
        url = f"https://www.google.se/search?q={encoded_query}&hl={language}"

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url, headers=self.headers)

            # Add delay to avoid rate limiting
            await asyncio.sleep(2)

            return {"html": response.text, "query": query}

    async def check_ai_overview(
        self,
        query: str,
        client_domain: str,
        location: str = "Sweden",
    ) -> AIOverviewResult:
        """Parse scraped results for AI Overview presence."""
        data = await self.search(query, location)
        html = data.get("html", "")

        soup = BeautifulSoup(html, "lxml")

        # Look for AI Overview indicators (these selectors may need updating)
        aio_selectors = [
            'div[data-attrid="AIOverview"]',
            'div[class*="ai-overview"]',
            'div[data-hveid] div[data-async-context]',
        ]

        has_aio = False
        aio_content = None

        for selector in aio_selectors:
            aio_element = soup.select_one(selector)
            if aio_element:
                has_aio = True
                aio_content = aio_element.get_text(strip=True)[:500]
                break

        # Parse organic results
        organic_results = []
        search_results = soup.select("div.g")[:10]

        for i, result in enumerate(search_results):
            link = result.select_one("a")
            title = result.select_one("h3")
            snippet = result.select_one("div.VwiC3b")

            if link and title:
                organic_results.append(
                    SERPResult(
                        position=i + 1,
                        url=link.get("href", ""),
                        title=title.get_text(strip=True),
                        snippet=snippet.get_text(strip=True) if snippet else "",
                    )
                )

        # Check if client is in results
        client_cited = any(client_domain in r.url for r in organic_results)

        return AIOverviewResult(
            query=query,
            has_aio=has_aio,
            aio_content=aio_content,
            citations=[],  # Hard to extract reliably from scraping
            client_cited=client_cited,
            organic_results=organic_results,
        )


class SerpClient:
    """Unified SERP client with provider abstraction."""

    def __init__(self, provider: SerpProvider, client_domain: str):
        self.provider = provider
        self.client_domain = client_domain

    async def check_queries_for_aio(
        self,
        queries: list[str],
        concurrency: int = 5,
    ) -> list[AIOverviewResult]:
        """Check multiple queries for AI Overview presence."""
        semaphore = asyncio.Semaphore(concurrency)

        async def check_one(query: str) -> AIOverviewResult:
            async with semaphore:
                try:
                    return await self.provider.check_ai_overview(
                        query, self.client_domain
                    )
                except Exception as e:
                    logger.error("Failed to check query", query=query, error=str(e))
                    return AIOverviewResult(query=query, has_aio=False)

        results = await asyncio.gather(*[check_one(q) for q in queries])
        return list(results)

    async def get_aio_impact_report(
        self,
        queries: list[str],
    ) -> dict[str, Any]:
        """Generate a report on AI Overview impact."""
        results = await self.check_queries_for_aio(queries)

        aio_queries = [r for r in results if r.has_aio]
        cited_queries = [r for r in aio_queries if r.client_cited]
        not_cited = [r for r in aio_queries if not r.client_cited]

        return {
            "total_queries": len(queries),
            "queries_with_aio": len(aio_queries),
            "aio_percentage": len(aio_queries) / len(queries) * 100 if queries else 0,
            "client_cited_count": len(cited_queries),
            "client_not_cited_count": len(not_cited),
            "citation_rate": len(cited_queries) / len(aio_queries) * 100 if aio_queries else 0,
            "high_risk_queries": [r.query for r in not_cited],
            "results": results,
        }


def get_serp_client(settings: SerpSettings, client_domain: str) -> SerpClient:
    """Factory function to create SERP client based on configuration."""
    if settings.provider == "serpapi":
        provider = SerpAPIProvider(settings.api_key.get_secret_value())
    elif settings.provider == "dataforseo":
        # DataForSEO uses login:password format in API key
        creds = settings.api_key.get_secret_value().split(":")
        provider = DataForSEOProvider(creds[0], creds[1] if len(creds) > 1 else "")
    else:
        # Default to scraper for development
        provider = ScraperProvider()

    return SerpClient(provider, client_domain)
