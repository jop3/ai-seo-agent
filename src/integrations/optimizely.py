"""Optimizely CMS integration."""

from typing import Any

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import OptimizelySettings

logger = structlog.get_logger()


class OptimizelyClient:
    """
    Client for Optimizely CMS Content Delivery API.

    This integrates with Optimizely CMS (formerly Episerver) to:
    1. Read content for analysis
    2. Push optimized content/schema (with approval workflow)
    """

    def __init__(self, settings: OptimizelySettings):
        self.settings = settings
        self.base_url = settings.base_url
        self._client = None

    def _get_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.settings.api_key.get_secret_value()}",
            "Content-Type": "application/json",
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs,
    ) -> dict[str, Any]:
        """Make an authenticated request to Optimizely API."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method,
                f"{self.base_url}{endpoint}",
                headers=self._get_headers(),
                **kwargs,
            )
            response.raise_for_status()

            if response.status_code == 204:
                return {}

            return response.json()

    async def get_content(self, content_id: str) -> dict[str, Any]:
        """
        Get content item by ID.

        Args:
            content_id: The Optimizely content ID

        Returns:
            Content data including properties, metadata
        """
        return await self._request("GET", f"/api/episerver/v3/content/{content_id}")

    async def get_content_by_url(self, url: str) -> dict[str, Any]:
        """
        Get content item by URL.

        Args:
            url: The page URL

        Returns:
            Content data
        """
        return await self._request(
            "GET",
            "/api/episerver/v3/content",
            params={"filter": f"url eq '{url}'"},
        )

    async def search_content(
        self,
        query: str | None = None,
        content_type: str | None = None,
        limit: int = 100,
        skip: int = 0,
    ) -> list[dict[str, Any]]:
        """
        Search for content items.

        Args:
            query: Search query
            content_type: Filter by content type (e.g., "ProductPage")
            limit: Max results
            skip: Offset for pagination

        Returns:
            List of matching content items
        """
        params: dict[str, Any] = {
            "top": limit,
            "skip": skip,
        }

        filters = []
        if query:
            filters.append(f"contains(name, '{query}')")
        if content_type:
            filters.append(f"contentType eq '{content_type}'")

        if filters:
            params["filter"] = " and ".join(filters)

        response = await self._request("GET", "/api/episerver/v3/content", params=params)
        return response.get("items", [])

    async def get_all_product_pages(self, limit: int = 1000) -> list[dict[str, Any]]:
        """Get all product pages for analysis."""
        return await self.search_content(content_type="ProductPage", limit=limit)

    async def get_all_category_pages(self, limit: int = 500) -> list[dict[str, Any]]:
        """Get all category pages."""
        return await self.search_content(content_type="CategoryPage", limit=limit)

    async def get_all_article_pages(self, limit: int = 500) -> list[dict[str, Any]]:
        """Get all article/health info pages."""
        # Optimizely content types vary by implementation
        articles = await self.search_content(content_type="ArticlePage", limit=limit)
        health_pages = await self.search_content(content_type="HealthInfoPage", limit=limit)
        return articles + health_pages

    async def update_content_property(
        self,
        content_id: str,
        property_name: str,
        value: Any,
    ) -> dict[str, Any]:
        """
        Update a single property on a content item.

        Note: This creates a draft. Use publish_content() to make it live.
        """
        return await self._request(
            "PATCH",
            f"/api/episerver/v3/content/{content_id}",
            json={property_name: value},
        )

    async def update_schema_markup(
        self,
        content_id: str,
        schema_json: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Update the schema.org markup for a content item.

        Args:
            content_id: The content ID
            schema_json: The JSON-LD schema markup

        Returns:
            Updated content data
        """
        import json
        schema_string = json.dumps(schema_json)

        # Property name varies by Optimizely implementation
        # Common names: SchemaMarkup, StructuredData, JsonLd
        return await self.update_content_property(
            content_id,
            "SchemaMarkup",  # Adjust based on actual property name
            schema_string,
        )

    async def update_meta_description(
        self,
        content_id: str,
        description: str,
    ) -> dict[str, Any]:
        """Update meta description for a content item."""
        return await self.update_content_property(
            content_id,
            "MetaDescription",
            description,
        )

    async def add_faq_content(
        self,
        content_id: str,
        faqs: list[dict[str, str]],
    ) -> dict[str, Any]:
        """
        Add FAQ content to a page.

        Args:
            content_id: The content ID
            faqs: List of {"question": "...", "answer": "..."} dicts
        """
        return await self.update_content_property(
            content_id,
            "FAQItems",  # Adjust based on actual property name
            faqs,
        )

    async def publish_content(self, content_id: str) -> dict[str, Any]:
        """
        Publish a content item (make draft live).

        Note: Depending on workflow configuration, this might create
        an approval task instead of publishing directly.
        """
        return await self._request(
            "POST",
            f"/api/episerver/v3/content/{content_id}/publish",
        )

    async def create_approval_task(
        self,
        content_id: str,
        title: str,
        description: str,
        assignee: str | None = None,
    ) -> dict[str, Any]:
        """
        Create an approval task for content changes.

        This is used when we want human review before publishing.
        """
        return await self._request(
            "POST",
            "/api/episerver/v3/tasks",
            json={
                "contentId": content_id,
                "title": title,
                "description": description,
                "assignee": assignee,
                "type": "ApprovalTask",
            },
        )


class OptimizelyContentAnalyzer:
    """Analyze Optimizely content for SEO optimization opportunities."""

    def __init__(self, client: OptimizelyClient):
        self.client = client

    async def analyze_page(self, content_id: str) -> dict[str, Any]:
        """
        Analyze a page for optimization opportunities.

        Returns analysis including:
        - Current schema markup status
        - Meta tag completeness
        - Content structure assessment
        """
        content = await self.client.get_content(content_id)

        analysis = {
            "content_id": content_id,
            "name": content.get("name"),
            "url": content.get("url"),
            "content_type": content.get("contentType"),
            "issues": [],
            "opportunities": [],
        }

        # Check schema markup
        schema = content.get("schemaMarkup") or content.get("structuredData")
        if not schema:
            analysis["issues"].append("Missing schema markup")
            analysis["opportunities"].append({
                "type": "add_schema",
                "priority": "high",
                "description": "Add Schema.org markup for better AI Overview visibility",
            })

        # Check meta description
        meta_desc = content.get("metaDescription")
        if not meta_desc:
            analysis["issues"].append("Missing meta description")
            analysis["opportunities"].append({
                "type": "add_meta",
                "priority": "medium",
                "description": "Add meta description",
            })
        elif len(meta_desc) < 120:
            analysis["issues"].append("Meta description too short")
            analysis["opportunities"].append({
                "type": "improve_meta",
                "priority": "low",
                "description": "Expand meta description to 150-160 characters",
            })

        # Check for FAQ content
        faqs = content.get("faqItems") or content.get("frequentlyAskedQuestions")
        if not faqs:
            analysis["opportunities"].append({
                "type": "add_faq",
                "priority": "medium",
                "description": "Add FAQ section to improve AIO citation potential",
            })

        return analysis

    async def bulk_analyze(
        self,
        content_ids: list[str],
    ) -> list[dict[str, Any]]:
        """Analyze multiple pages."""
        import asyncio

        results = await asyncio.gather(
            *[self.analyze_page(cid) for cid in content_ids],
            return_exceptions=True,
        )

        return [r for r in results if isinstance(r, dict)]
