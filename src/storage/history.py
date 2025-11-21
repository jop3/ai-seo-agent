"""
Historical data storage for SEO metrics and trends.

Supports multiple backends:
- Local SQLite (development)
- Azure Cosmos DB (production)
- In-memory (testing)
"""

import json
import sqlite3
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

import structlog
from pydantic import BaseModel

logger = structlog.get_logger()


class StorageBackend(str, Enum):
    """Storage backend options."""

    SQLITE = "sqlite"
    COSMOS = "cosmos"
    MEMORY = "memory"


class MetricRecord(BaseModel):
    """A single metric data point."""

    id: str = ""
    metric_type: str  # aio_status, traffic, ranking, citation, etc.
    entity: str  # query, url, domain
    entity_value: str
    value: float | dict[str, Any]
    timestamp: datetime
    metadata: dict[str, Any] = {}


class TrendData(BaseModel):
    """Aggregated trend data."""

    metric_type: str
    entity: str
    entity_value: str
    period_start: datetime
    period_end: datetime
    data_points: list[dict[str, Any]]
    trend: str  # up, down, stable
    change_percent: float


class StorageBase(ABC):
    """Abstract base for storage backends."""

    @abstractmethod
    async def store(self, record: MetricRecord) -> str:
        """Store a metric record."""
        pass

    @abstractmethod
    async def query(
        self,
        metric_type: str,
        entity: str | None = None,
        entity_value: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 1000,
    ) -> list[MetricRecord]:
        """Query metric records."""
        pass

    @abstractmethod
    async def get_trend(
        self,
        metric_type: str,
        entity: str,
        entity_value: str,
        days: int = 30,
    ) -> TrendData | None:
        """Get trend data for a metric."""
        pass


class SQLiteStorage(StorageBase):
    """SQLite storage backend for local development."""

    def __init__(self, db_path: str = "data/seo_history.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    id TEXT PRIMARY KEY,
                    metric_type TEXT NOT NULL,
                    entity TEXT NOT NULL,
                    entity_value TEXT NOT NULL,
                    value TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_metrics_type
                ON metrics(metric_type, entity, timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_metrics_entity
                ON metrics(entity_value, timestamp)
            """)

    async def store(self, record: MetricRecord) -> str:
        """Store a metric record."""
        import uuid

        record_id = record.id or str(uuid.uuid4())

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO metrics (id, metric_type, entity, entity_value, value, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record_id,
                    record.metric_type,
                    record.entity,
                    record.entity_value,
                    json.dumps(record.value) if isinstance(record.value, dict) else str(record.value),
                    record.timestamp.isoformat(),
                    json.dumps(record.metadata),
                ),
            )

        return record_id

    async def query(
        self,
        metric_type: str,
        entity: str | None = None,
        entity_value: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 1000,
    ) -> list[MetricRecord]:
        """Query metric records."""
        query = "SELECT * FROM metrics WHERE metric_type = ?"
        params: list[Any] = [metric_type]

        if entity:
            query += " AND entity = ?"
            params.append(entity)

        if entity_value:
            query += " AND entity_value = ?"
            params.append(entity_value)

        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time.isoformat())

        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time.isoformat())

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        records = []
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)

            for row in cursor.fetchall():
                value = row["value"]
                try:
                    value = json.loads(value)
                except:
                    try:
                        value = float(value)
                    except:
                        pass

                records.append(MetricRecord(
                    id=row["id"],
                    metric_type=row["metric_type"],
                    entity=row["entity"],
                    entity_value=row["entity_value"],
                    value=value,
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                ))

        return records

    async def get_trend(
        self,
        metric_type: str,
        entity: str,
        entity_value: str,
        days: int = 30,
    ) -> TrendData | None:
        """Calculate trend for a metric."""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)

        records = await self.query(
            metric_type=metric_type,
            entity=entity,
            entity_value=entity_value,
            start_time=start_time,
            end_time=end_time,
        )

        if not records:
            return None

        # Build data points
        data_points = [
            {
                "timestamp": r.timestamp.isoformat(),
                "value": r.value,
            }
            for r in sorted(records, key=lambda x: x.timestamp)
        ]

        # Calculate trend
        if len(records) >= 2:
            first_values = [r.value for r in records[-5:] if isinstance(r.value, (int, float))]
            last_values = [r.value for r in records[:5] if isinstance(r.value, (int, float))]

            if first_values and last_values:
                first_avg = sum(first_values) / len(first_values)
                last_avg = sum(last_values) / len(last_values)

                if first_avg > 0:
                    change_percent = ((last_avg - first_avg) / first_avg) * 100
                else:
                    change_percent = 0

                if change_percent > 5:
                    trend = "up"
                elif change_percent < -5:
                    trend = "down"
                else:
                    trend = "stable"
            else:
                trend = "stable"
                change_percent = 0
        else:
            trend = "insufficient_data"
            change_percent = 0

        return TrendData(
            metric_type=metric_type,
            entity=entity,
            entity_value=entity_value,
            period_start=start_time,
            period_end=end_time,
            data_points=data_points,
            trend=trend,
            change_percent=change_percent,
        )


class MemoryStorage(StorageBase):
    """In-memory storage for testing."""

    def __init__(self):
        self.records: list[MetricRecord] = []

    async def store(self, record: MetricRecord) -> str:
        """Store a metric record."""
        import uuid

        record.id = record.id or str(uuid.uuid4())
        self.records.append(record)
        return record.id

    async def query(
        self,
        metric_type: str,
        entity: str | None = None,
        entity_value: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 1000,
    ) -> list[MetricRecord]:
        """Query metric records."""
        results = [r for r in self.records if r.metric_type == metric_type]

        if entity:
            results = [r for r in results if r.entity == entity]
        if entity_value:
            results = [r for r in results if r.entity_value == entity_value]
        if start_time:
            results = [r for r in results if r.timestamp >= start_time]
        if end_time:
            results = [r for r in results if r.timestamp <= end_time]

        return sorted(results, key=lambda x: x.timestamp, reverse=True)[:limit]

    async def get_trend(
        self,
        metric_type: str,
        entity: str,
        entity_value: str,
        days: int = 30,
    ) -> TrendData | None:
        """Get trend data."""
        # Simplified - use same logic as SQLite
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)

        records = await self.query(
            metric_type=metric_type,
            entity=entity,
            entity_value=entity_value,
            start_time=start_time,
            end_time=end_time,
        )

        if not records:
            return None

        return TrendData(
            metric_type=metric_type,
            entity=entity,
            entity_value=entity_value,
            period_start=start_time,
            period_end=end_time,
            data_points=[{"timestamp": r.timestamp.isoformat(), "value": r.value} for r in records],
            trend="stable",
            change_percent=0,
        )


class CosmosStorage(StorageBase):
    """Azure Cosmos DB storage backend for production."""

    def __init__(self, endpoint: str, key: str, database: str = "seo-agent"):
        self.endpoint = endpoint
        self.key = key
        self.database_name = database
        self.container_name = "metrics"
        self._client = None

    def _get_container(self):
        """Get Cosmos DB container."""
        if self._client is None:
            from azure.cosmos import CosmosClient

            self._client = CosmosClient(self.endpoint, credential=self.key)
            database = self._client.get_database_client(self.database_name)
            self._container = database.get_container_client(self.container_name)

        return self._container

    async def store(self, record: MetricRecord) -> str:
        """Store a metric record in Cosmos DB."""
        import uuid

        container = self._get_container()

        doc = {
            "id": record.id or str(uuid.uuid4()),
            "metric_type": record.metric_type,
            "entity": record.entity,
            "entity_value": record.entity_value,
            "value": record.value,
            "timestamp": record.timestamp.isoformat(),
            "metadata": record.metadata,
            "partition_key": f"{record.metric_type}_{record.entity}",
        }

        result = container.upsert_item(doc)
        return result["id"]

    async def query(
        self,
        metric_type: str,
        entity: str | None = None,
        entity_value: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 1000,
    ) -> list[MetricRecord]:
        """Query metrics from Cosmos DB."""
        container = self._get_container()

        query = "SELECT * FROM c WHERE c.metric_type = @metric_type"
        params = [{"name": "@metric_type", "value": metric_type}]

        if entity:
            query += " AND c.entity = @entity"
            params.append({"name": "@entity", "value": entity})

        if entity_value:
            query += " AND c.entity_value = @entity_value"
            params.append({"name": "@entity_value", "value": entity_value})

        if start_time:
            query += " AND c.timestamp >= @start_time"
            params.append({"name": "@start_time", "value": start_time.isoformat()})

        if end_time:
            query += " AND c.timestamp <= @end_time"
            params.append({"name": "@end_time", "value": end_time.isoformat()})

        query += " ORDER BY c.timestamp DESC"

        items = container.query_items(
            query=query,
            parameters=params,
            max_item_count=limit,
        )

        records = []
        for item in items:
            records.append(MetricRecord(
                id=item["id"],
                metric_type=item["metric_type"],
                entity=item["entity"],
                entity_value=item["entity_value"],
                value=item["value"],
                timestamp=datetime.fromisoformat(item["timestamp"]),
                metadata=item.get("metadata", {}),
            ))

        return records

    async def get_trend(
        self,
        metric_type: str,
        entity: str,
        entity_value: str,
        days: int = 30,
    ) -> TrendData | None:
        """Get trend from Cosmos DB."""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)

        records = await self.query(
            metric_type=metric_type,
            entity=entity,
            entity_value=entity_value,
            start_time=start_time,
            end_time=end_time,
        )

        if not records:
            return None

        # Calculate trend (same as SQLite)
        data_points = [{"timestamp": r.timestamp.isoformat(), "value": r.value} for r in records]

        return TrendData(
            metric_type=metric_type,
            entity=entity,
            entity_value=entity_value,
            period_start=start_time,
            period_end=end_time,
            data_points=data_points,
            trend="stable",
            change_percent=0,
        )


class HistoricalStorage:
    """
    Main interface for historical data storage.

    Automatically selects backend based on configuration.
    """

    def __init__(self, backend: StorageBackend = StorageBackend.SQLITE, **kwargs):
        self.backend_type = backend

        if backend == StorageBackend.SQLITE:
            self._storage = SQLiteStorage(kwargs.get("db_path", "data/seo_history.db"))
        elif backend == StorageBackend.COSMOS:
            self._storage = CosmosStorage(
                endpoint=kwargs["endpoint"],
                key=kwargs["key"],
                database=kwargs.get("database", "seo-agent"),
            )
        else:
            self._storage = MemoryStorage()

        logger.info("Initialized historical storage", backend=backend.value)

    async def store_metric(
        self,
        metric_type: str,
        entity: str,
        entity_value: str,
        value: float | dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Store a metric value."""
        record = MetricRecord(
            metric_type=metric_type,
            entity=entity,
            entity_value=entity_value,
            value=value,
            timestamp=datetime.utcnow(),
            metadata=metadata or {},
        )
        return await self._storage.store(record)

    async def store_aio_status(
        self,
        query: str,
        has_aio: bool,
        client_cited: bool,
        citation_position: int | None = None,
    ) -> str:
        """Store AIO status for a query."""
        return await self.store_metric(
            metric_type="aio_status",
            entity="query",
            entity_value=query,
            value={
                "has_aio": has_aio,
                "client_cited": client_cited,
                "citation_position": citation_position,
            },
        )

    async def store_traffic(
        self,
        query: str,
        clicks: int,
        impressions: int,
        position: float,
    ) -> str:
        """Store traffic metrics."""
        return await self.store_metric(
            metric_type="traffic",
            entity="query",
            entity_value=query,
            value={
                "clicks": clicks,
                "impressions": impressions,
                "position": position,
            },
        )

    async def store_ranking(self, query: str, position: float, url: str) -> str:
        """Store ranking position."""
        return await self.store_metric(
            metric_type="ranking",
            entity="query",
            entity_value=query,
            value=position,
            metadata={"url": url},
        )

    async def get_metrics(
        self,
        metric_type: str,
        entity_value: str | None = None,
        days: int = 30,
    ) -> list[MetricRecord]:
        """Get metrics for a time period."""
        start_time = datetime.utcnow() - timedelta(days=days)
        return await self._storage.query(
            metric_type=metric_type,
            entity_value=entity_value,
            start_time=start_time,
        )

    async def get_trend(
        self,
        metric_type: str,
        entity: str,
        entity_value: str,
        days: int = 30,
    ) -> TrendData | None:
        """Get trend data for a metric."""
        return await self._storage.get_trend(metric_type, entity, entity_value, days)

    async def get_aio_trend(self, query: str, days: int = 30) -> TrendData | None:
        """Get AIO status trend for a query."""
        return await self.get_trend("aio_status", "query", query, days)

    async def get_traffic_trend(self, query: str, days: int = 30) -> TrendData | None:
        """Get traffic trend for a query."""
        return await self.get_trend("traffic", "query", query, days)


# Global storage instance
_storage: HistoricalStorage | None = None


def get_storage(
    backend: StorageBackend = StorageBackend.SQLITE,
    **kwargs,
) -> HistoricalStorage:
    """Get or create global storage instance."""
    global _storage
    if _storage is None:
        _storage = HistoricalStorage(backend=backend, **kwargs)
    return _storage
