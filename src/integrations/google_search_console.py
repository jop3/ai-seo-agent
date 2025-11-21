"""Google Search Console API integration."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import structlog
from google.oauth2 import service_account
from googleapiclient.discovery import build
from tenacity import retry, stop_after_attempt, wait_exponential

from src.models.seo import Query, QueryClassification, TrafficData, TrafficChange

logger = structlog.get_logger()

SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]


class GoogleSearchConsoleClient:
    """Client for Google Search Console API."""

    def __init__(self, credentials_path: str, property_url: str):
        self.property_url = property_url
        self.credentials_path = Path(credentials_path)
        self._service = None

    def _get_service(self):
        """Lazy initialization of GSC service."""
        if self._service is None:
            if not self.credentials_path.exists():
                raise FileNotFoundError(
                    f"GSC credentials not found at {self.credentials_path}"
                )

            credentials = service_account.Credentials.from_service_account_file(
                str(self.credentials_path), scopes=SCOPES
            )
            self._service = build("searchconsole", "v1", credentials=credentials)

        return self._service

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def get_queries(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        dimensions: list[str] | None = None,
        row_limit: int = 25000,
        filters: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Fetch search analytics data from GSC.

        Args:
            start_date: Start of date range (default: 30 days ago)
            end_date: End of date range (default: yesterday)
            dimensions: Dimensions to group by (default: ["query"])
            row_limit: Maximum rows to return
            filters: Optional filters to apply

        Returns:
            List of query data rows
        """
        if start_date is None:
            start_date = datetime.utcnow() - timedelta(days=30)
        if end_date is None:
            end_date = datetime.utcnow() - timedelta(days=1)
        if dimensions is None:
            dimensions = ["query"]

        service = self._get_service()

        request_body = {
            "startDate": start_date.strftime("%Y-%m-%d"),
            "endDate": end_date.strftime("%Y-%m-%d"),
            "dimensions": dimensions,
            "rowLimit": row_limit,
        }

        if filters:
            request_body["dimensionFilterGroups"] = [{"filters": filters}]

        logger.info(
            "Fetching GSC data",
            property_url=self.property_url,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
        )

        response = (
            service.searchanalytics()
            .query(siteUrl=self.property_url, body=request_body)
            .execute()
        )

        return response.get("rows", [])

    async def get_top_queries(
        self,
        limit: int = 1000,
        days: int = 30,
    ) -> list[Query]:
        """Get top queries by clicks."""
        rows = await self.get_queries(
            start_date=datetime.utcnow() - timedelta(days=days),
            row_limit=limit,
            dimensions=["query"],
        )

        queries = []
        for row in rows:
            query = Query(
                query=row["keys"][0],
                property_url=self.property_url,
                clicks=int(row.get("clicks", 0)),
                impressions=int(row.get("impressions", 0)),
                ctr=float(row.get("ctr", 0)),
                avg_position=float(row.get("position", 0)),
                classification=self._classify_query(row["keys"][0]),
            )
            queries.append(query)

        return queries

    async def get_query_page_data(
        self,
        days: int = 30,
        limit: int = 10000,
    ) -> list[TrafficData]:
        """Get query + page level data."""
        rows = await self.get_queries(
            start_date=datetime.utcnow() - timedelta(days=days),
            row_limit=limit,
            dimensions=["query", "page"],
        )

        traffic_data = []
        for row in rows:
            data = TrafficData(
                property_url=self.property_url,
                date=datetime.utcnow(),
                query=row["keys"][0],
                page=row["keys"][1],
                clicks=int(row.get("clicks", 0)),
                impressions=int(row.get("impressions", 0)),
                ctr=float(row.get("ctr", 0)),
                position=float(row.get("position", 0)),
            )
            traffic_data.append(data)

        return traffic_data

    async def detect_traffic_changes(
        self,
        threshold_percent: float = 20.0,
        comparison_days: int = 7,
    ) -> list[TrafficChange]:
        """
        Detect significant traffic changes by comparing periods.

        Args:
            threshold_percent: Minimum change to flag
            comparison_days: Days in each comparison period

        Returns:
            List of significant traffic changes
        """
        now = datetime.utcnow()

        # Current period
        current_end = now - timedelta(days=1)
        current_start = current_end - timedelta(days=comparison_days)

        # Previous period
        previous_end = current_start - timedelta(days=1)
        previous_start = previous_end - timedelta(days=comparison_days)

        current_data = await self.get_queries(
            start_date=current_start,
            end_date=current_end,
            dimensions=["query"],
        )

        previous_data = await self.get_queries(
            start_date=previous_start,
            end_date=previous_end,
            dimensions=["query"],
        )

        # Index previous data by query
        previous_by_query = {row["keys"][0]: row for row in previous_data}

        changes = []
        for current_row in current_data:
            query = current_row["keys"][0]
            previous_row = previous_by_query.get(query)

            if previous_row is None:
                continue

            current_clicks = current_row.get("clicks", 0)
            previous_clicks = previous_row.get("clicks", 0)

            if previous_clicks == 0:
                continue

            change_percent = ((current_clicks - previous_clicks) / previous_clicks) * 100

            if abs(change_percent) >= threshold_percent:
                change = TrafficChange(
                    query=query,
                    metric="clicks",
                    previous_value=previous_clicks,
                    current_value=current_clicks,
                    change_percent=change_percent,
                    period_start=current_start,
                    period_end=current_end,
                    is_significant=True,
                )
                changes.append(change)

        # Sort by change magnitude
        changes.sort(key=lambda x: abs(x.change_percent), reverse=True)

        logger.info(
            "Detected traffic changes",
            total_changes=len(changes),
            threshold=threshold_percent,
        )

        return changes

    def _classify_query(self, query: str) -> QueryClassification:
        """Simple query intent classification."""
        query_lower = query.lower()

        # Local indicators
        local_terms = ["near me", "nearby", "closest", "öppettider", "stockholm", "göteborg", "malmö"]
        if any(term in query_lower for term in local_terms):
            return QueryClassification.LOCAL

        # Transactional indicators
        transactional_terms = ["buy", "köp", "order", "price", "pris", "cheap", "billig"]
        if any(term in query_lower for term in transactional_terms):
            return QueryClassification.TRANSACTIONAL

        # Commercial investigation
        commercial_terms = ["best", "bästa", "review", "vs", "compare", "jämför"]
        if any(term in query_lower for term in commercial_terms):
            return QueryClassification.COMMERCIAL

        # Navigational
        if "apoteket" in query_lower or "apotek" in query_lower:
            return QueryClassification.NAVIGATIONAL

        # Default to informational
        return QueryClassification.INFORMATIONAL
