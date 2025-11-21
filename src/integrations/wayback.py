"""Wayback Machine API integration for page change detection."""

import asyncio
from datetime import datetime, timedelta
from typing import Any

import httpx
import structlog
from pydantic import BaseModel

logger = structlog.get_logger()


class WaybackSnapshot(BaseModel):
    """A Wayback Machine snapshot."""
    timestamp: str
    url: str
    status_code: int = 200
    mime_type: str = "text/html"


class PageChange(BaseModel):
    """Detected change between snapshots."""
    url: str
    old_timestamp: str
    new_timestamp: str
    change_type: str  # "content", "title", "structure", "removed"
    change_summary: str


class WaybackClient:
    """
    Wayback Machine API client for detecting page changes.

    This is a free API, no key required.
    """

    def __init__(self):
        self.base_url = "https://web.archive.org"
        self.cdx_url = "https://web.archive.org/cdx/search/cdx"
        self.logger = logger.bind(integration="wayback")

    @property
    def available(self) -> bool:
        """Wayback Machine API is publicly available."""
        return True

    async def get_snapshots(
        self,
        url: str,
        from_date: str | None = None,
        to_date: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """
        Get available snapshots for a URL.

        Args:
            url: URL to check
            from_date: Start date (YYYYMMDD format)
            to_date: End date (YYYYMMDD format)
            limit: Maximum number of snapshots
        """
        try:
            params = {
                "url": url,
                "output": "json",
                "limit": limit,
                "fl": "timestamp,original,statuscode,mimetype",
            }

            if from_date:
                params["from"] = from_date
            if to_date:
                params["to"] = to_date

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.cdx_url, params=params)
                response.raise_for_status()
                data = response.json()

            # First row is headers
            if len(data) <= 1:
                return {
                    "url": url,
                    "snapshots": [],
                    "total": 0,
                }

            snapshots = []
            for row in data[1:]:  # Skip header row
                if len(row) >= 4:
                    snapshots.append(WaybackSnapshot(
                        timestamp=row[0],
                        url=row[1],
                        status_code=int(row[2]) if row[2].isdigit() else 200,
                        mime_type=row[3],
                    ).model_dump())

            return {
                "url": url,
                "snapshots": snapshots,
                "total": len(snapshots),
                "oldest": snapshots[-1]["timestamp"] if snapshots else None,
                "newest": snapshots[0]["timestamp"] if snapshots else None,
            }

        except httpx.HTTPStatusError as e:
            self.logger.error("Wayback API error", status=e.response.status_code)
            return {"url": url, "snapshots": [], "error": str(e)}
        except Exception as e:
            self.logger.error("Wayback request failed", error=str(e))
            return {"url": url, "snapshots": [], "error": str(e)}

    async def get_snapshot_content(
        self,
        url: str,
        timestamp: str,
    ) -> dict[str, Any]:
        """
        Get the content of a specific snapshot.

        Args:
            url: Original URL
            timestamp: Wayback timestamp (YYYYMMDDHHMMSS)
        """
        try:
            wayback_url = f"{self.base_url}/web/{timestamp}id_/{url}"

            async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                response = await client.get(wayback_url)

                return {
                    "url": url,
                    "timestamp": timestamp,
                    "content": response.text,
                    "status_code": response.status_code,
                }

        except Exception as e:
            self.logger.error("Failed to fetch snapshot", error=str(e))
            return {"url": url, "timestamp": timestamp, "error": str(e)}

    async def detect_changes(
        self,
        url: str,
        days_back: int = 90,
    ) -> dict[str, Any]:
        """
        Detect significant changes to a page over time.

        Compares recent snapshot with older snapshot.
        """
        try:
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y%m%d")

            # Get snapshots
            snapshot_data = await self.get_snapshots(
                url,
                from_date=start_date,
                to_date=end_date,
                limit=50,
            )

            snapshots = snapshot_data.get("snapshots", [])

            if len(snapshots) < 2:
                return {
                    "url": url,
                    "changes_detected": False,
                    "message": "Not enough snapshots for comparison",
                    "snapshots_found": len(snapshots),
                }

            # Get oldest and newest snapshots
            newest = snapshots[0]
            oldest = snapshots[-1]

            # Fetch content for both
            new_content = await self.get_snapshot_content(url, newest["timestamp"])
            old_content = await self.get_snapshot_content(url, oldest["timestamp"])

            if new_content.get("error") or old_content.get("error"):
                return {
                    "url": url,
                    "changes_detected": False,
                    "error": "Failed to fetch snapshot content",
                }

            # Analyze changes
            changes = self._analyze_content_changes(
                old_content.get("content", ""),
                new_content.get("content", ""),
                oldest["timestamp"],
                newest["timestamp"],
            )

            return {
                "url": url,
                "changes_detected": len(changes) > 0,
                "old_snapshot": oldest["timestamp"],
                "new_snapshot": newest["timestamp"],
                "total_snapshots": len(snapshots),
                "changes": changes,
            }

        except Exception as e:
            self.logger.error("Change detection failed", error=str(e))
            return {"url": url, "error": str(e)}

    def _analyze_content_changes(
        self,
        old_html: str,
        new_html: str,
        old_timestamp: str,
        new_timestamp: str,
    ) -> list[dict[str, Any]]:
        """Analyze differences between two HTML versions."""
        from bs4 import BeautifulSoup

        changes = []

        try:
            old_soup = BeautifulSoup(old_html, "lxml")
            new_soup = BeautifulSoup(new_html, "lxml")

            # Check title change
            old_title = old_soup.title.text.strip() if old_soup.title else ""
            new_title = new_soup.title.text.strip() if new_soup.title else ""

            if old_title != new_title:
                changes.append({
                    "type": "title_change",
                    "old_value": old_title[:200],
                    "new_value": new_title[:200],
                })

            # Check meta description change
            old_desc = old_soup.find("meta", {"name": "description"})
            new_desc = new_soup.find("meta", {"name": "description"})
            old_desc_content = old_desc.get("content", "") if old_desc else ""
            new_desc_content = new_desc.get("content", "") if new_desc else ""

            if old_desc_content != new_desc_content:
                changes.append({
                    "type": "meta_description_change",
                    "old_value": old_desc_content[:300],
                    "new_value": new_desc_content[:300],
                })

            # Check H1 changes
            old_h1s = [h.text.strip() for h in old_soup.find_all("h1")]
            new_h1s = [h.text.strip() for h in new_soup.find_all("h1")]

            if old_h1s != new_h1s:
                changes.append({
                    "type": "h1_change",
                    "old_value": old_h1s,
                    "new_value": new_h1s,
                })

            # Check content length change
            old_text_len = len(old_soup.get_text())
            new_text_len = len(new_soup.get_text())
            length_change_pct = (
                (new_text_len - old_text_len) / old_text_len * 100
                if old_text_len > 0 else 0
            )

            if abs(length_change_pct) > 20:
                changes.append({
                    "type": "content_length_change",
                    "old_length": old_text_len,
                    "new_length": new_text_len,
                    "change_percentage": round(length_change_pct, 1),
                })

            # Check schema changes
            old_schemas = old_soup.find_all("script", type="application/ld+json")
            new_schemas = new_soup.find_all("script", type="application/ld+json")

            if len(old_schemas) != len(new_schemas):
                changes.append({
                    "type": "schema_count_change",
                    "old_count": len(old_schemas),
                    "new_count": len(new_schemas),
                })

        except Exception as e:
            self.logger.warning("Content analysis failed", error=str(e))

        return changes

    async def check_competitor_changes(
        self,
        competitor_urls: list[str],
        days_back: int = 30,
    ) -> dict[str, Any]:
        """
        Check for changes on competitor pages.
        """
        results = []

        for url in competitor_urls[:10]:  # Limit to 10 URLs
            change_data = await self.detect_changes(url, days_back)
            results.append({
                "url": url,
                "has_changes": change_data.get("changes_detected", False),
                "changes": change_data.get("changes", []),
            })

            # Rate limiting
            await asyncio.sleep(1)

        pages_with_changes = [r for r in results if r["has_changes"]]

        return {
            "urls_checked": len(results),
            "pages_with_changes": len(pages_with_changes),
            "results": results,
        }

    async def get_historical_snapshots_summary(
        self,
        url: str,
    ) -> dict[str, Any]:
        """
        Get a summary of all historical snapshots.
        """
        try:
            params = {
                "url": url,
                "output": "json",
                "fl": "timestamp,statuscode",
                "collapse": "timestamp:6",  # Collapse to monthly
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.cdx_url, params=params)
                data = response.json()

            if len(data) <= 1:
                return {"url": url, "summary": []}

            # Group by year
            years = {}
            for row in data[1:]:
                if len(row) >= 2:
                    year = row[0][:4]
                    years[year] = years.get(year, 0) + 1

            return {
                "url": url,
                "total_snapshots": len(data) - 1,
                "years_covered": len(years),
                "snapshots_by_year": years,
                "first_snapshot": data[1][0] if len(data) > 1 else None,
                "last_snapshot": data[-1][0] if len(data) > 1 else None,
            }

        except Exception as e:
            return {"url": url, "error": str(e)}


def get_wayback_client() -> WaybackClient:
    """Factory function to create Wayback client."""
    return WaybackClient()
