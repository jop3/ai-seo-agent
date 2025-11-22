"""
Rapid Indexing Agent - Solve "Crawled - Not Indexed" problem.

Key insight from article: Large e-commerce sites struggle with indexing delays.
Use Google/Bing IndexNow API to submit URLs immediately.

Critical for:
- New product pages
- Updated content
- Time-sensitive content
- Large catalogs (1000s of products)

Problem: "Crawled - Not Indexed" means Google saw your page but didn't add it.
Solution: Instant submission + quality monitoring + auto-fix technicals.
"""

from datetime import datetime, timedelta
from typing import Any

import structlog

from src.agents.base import BaseAgent, AgentContext
from src.models.agents import AgentTask, AgentResult, Recommendation, Alert, Priority, Severity

logger = structlog.get_logger()


class RapidIndexingAgent(BaseAgent):
    """
    Ensures rapid indexing of new and updated content.

    Solves the "Crawled - Not Indexed" problem common in e-commerce sites.

    Features:
    - Instant URL submission via IndexNow API
    - Indexing status monitoring
    - Priority queue for important pages
    - Auto-detection of indexing issues
    - Technical fix suggestions

    APIs used:
    - Google Search Console API (indexing status)
    - IndexNow API (Bing, Yandex)
    - Google Indexing API (for specific use cases)
    """

    # Indexing status categories
    INDEXING_STATUSES = {
        "indexed": "Successfully indexed",
        "crawled_not_indexed": "Crawled but not indexed (problem)",
        "discovered_not_crawled": "Discovered but not yet crawled",
        "excluded": "Excluded (soft 404, duplicate, etc.)",
        "error": "Error during crawling",
        "submitted": "Submitted for indexing",
        "pending": "Pending crawl/index",
    }

    # Common reasons for "Crawled - Not Indexed"
    NOT_INDEXED_REASONS = {
        "low_quality": "Content deemed low quality",
        "duplicate": "Duplicate content",
        "thin_content": "Thin content (too short)",
        "no_value": "No added value",
        "crawl_budget": "Crawl budget limitations",
        "technical": "Technical issues (slow, broken)",
    }

    def __init__(self, context: AgentContext):
        super().__init__(
            agent_type="rapid-indexing",
            description="Solves 'Crawled - Not Indexed' problem with rapid URL submission and monitoring",
            context=context,
        )

    async def run(self, task: AgentTask) -> AgentResult:
        """Execute rapid indexing task."""
        start_time = datetime.utcnow()

        try:
            if task.task_type == "submit_urls":
                result = await self._submit_urls(task.parameters)
            elif task.task_type == "check_indexing_status":
                result = await self._check_indexing_status(task.parameters)
            elif task.task_type == "find_not_indexed":
                result = await self._find_not_indexed(task.parameters)
            elif task.task_type == "prioritize_pages":
                result = await self._prioritize_pages(task.parameters)
            elif task.task_type == "full_indexing_audit":
                result = await self._full_indexing_audit(task.parameters)
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
            logger.error("Rapid indexing failed", error=str(e))
            return AgentResult(
                task_id=task.id,
                agent_type=self.agent_type,
                success=False,
                data={"error": str(e)},
            )

    async def _full_indexing_audit(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Complete indexing audit.

        Identifies all indexing issues and provides fix recommendations.
        """
        domain = params.get("domain", self.context.property_url)

        results = {
            "analyzed_at": datetime.utcnow().isoformat(),
            "domain": domain,
            "total_pages": 0,
            "indexing_stats": {},
            "not_indexed_pages": [],
            "priority_pages": [],
            "indexing_health_score": 0,
            "crawl_budget_analysis": {},
        }

        recommendations = []
        alerts = []

        # Get indexing status for all pages
        indexing_stats = await self._get_indexing_stats(domain)
        results["indexing_stats"] = indexing_stats
        results["total_pages"] = indexing_stats["total_pages"]

        # Find "Crawled - Not Indexed" pages
        not_indexed_result = await self._find_not_indexed({"domain": domain})
        results["not_indexed_pages"] = not_indexed_result["data"]["not_indexed_pages"]

        # Prioritize which pages to fix first
        priority_result = await self._prioritize_pages({
            "pages": results["not_indexed_pages"]
        })
        results["priority_pages"] = priority_result["data"]["priority_pages"]

        # Calculate indexing health score
        health_score = self._calculate_indexing_health(indexing_stats)
        results["indexing_health_score"] = health_score

        # Crawl budget analysis
        crawl_analysis = self._analyze_crawl_budget(indexing_stats, results["total_pages"])
        results["crawl_budget_analysis"] = crawl_analysis

        # Generate recommendations
        if indexing_stats["crawled_not_indexed"] > 100:
            recommendations.append(Recommendation(
                title=f"Fix {indexing_stats['crawled_not_indexed']} Not-Indexed Pages",
                description=f"{indexing_stats['crawled_not_indexed']} pages are crawled but not indexed. This wastes crawl budget.",
                category="Indexing - Crawled Not Indexed",
                priority=Priority.CRITICAL,
                estimated_impact="Improve crawl budget efficiency + get pages indexed",
                implementation_effort="high",
            ))

        if health_score < 70:
            alerts.append(Alert(
                title="Low Indexing Health Score",
                message=f"Indexing health score is {health_score:.1f}/100. Significant indexing issues detected.",
                severity=Severity.CRITICAL,
                source=self.agent_type,
                affected_urls=[domain],
            ))

        # Submit priority pages for indexing
        if len(results["priority_pages"]) > 0:
            recommendations.append(Recommendation(
                title=f"Submit {len(results['priority_pages'])} Priority Pages",
                description="Use IndexNow API to submit high-value pages for immediate indexing.",
                category="Indexing - Priority Submission",
                priority=Priority.HIGH,
                estimated_impact="Faster indexing of important pages",
                implementation_effort="low",
                auto_implementable=True,
            ))

        return {
            "data": results,
            "recommendations": recommendations,
            "alerts": alerts,
        }

    async def _submit_urls(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Submit URLs for rapid indexing.

        Uses IndexNow API for instant submission to Bing/Yandex.
        """
        urls = params.get("urls", [])
        api_type = params.get("api", "indexnow")  # indexnow or google

        # In production, this would call actual API
        submission_result = {
            "api_used": api_type,
            "urls_submitted": len(urls),
            "submission_status": "success",
            "submitted_at": datetime.utcnow().isoformat(),
            "urls": urls[:10],  # Show first 10
            "estimated_index_time": "24-48 hours",
        }

        if api_type == "indexnow":
            submission_result["platforms"] = ["Bing", "Yandex", "Seznam"]
        elif api_type == "google":
            submission_result["platforms"] = ["Google"]

        recommendations = [
            Recommendation(
                title="Monitor Indexing Status in 24-48 Hours",
                description=f"{len(urls)} URLs submitted. Check indexing status in 1-2 days.",
                category="Indexing - Monitoring",
                priority=Priority.MEDIUM,
                estimated_impact="Ensure submission was successful",
                implementation_effort="low",
            ),
        ]

        return {
            "data": submission_result,
            "recommendations": recommendations,
        }

    async def _get_indexing_stats(self, domain: str) -> dict[str, Any]:
        """Get indexing statistics for domain."""
        # Simulated stats - in production, from Search Console API
        return {
            "total_pages": 1247,
            "indexed": 892,
            "crawled_not_indexed": 235,
            "discovered_not_crawled": 67,
            "excluded": 43,
            "error": 10,
            "indexing_rate": 71.5,  # %
        }

    async def _check_indexing_status(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Check indexing status of specific URLs.

        Monitors whether submitted URLs are indexed.
        """
        urls = params.get("urls", [])

        # In production, query Search Console API
        status_check = {
            "checked_at": datetime.utcnow().isoformat(),
            "urls_checked": len(urls),
            "status_breakdown": {
                "indexed": 8,
                "crawled_not_indexed": 3,
                "discovered_not_crawled": 1,
                "excluded": 1,
            },
            "url_statuses": [
                {
                    "url": urls[0] if urls else "example.com/page1",
                    "status": "indexed",
                    "last_crawled": (datetime.utcnow() - timedelta(days=2)).isoformat(),
                    "indexed_at": (datetime.utcnow() - timedelta(days=1)).isoformat(),
                },
                {
                    "url": urls[1] if len(urls) > 1 else "example.com/page2",
                    "status": "crawled_not_indexed",
                    "last_crawled": (datetime.utcnow() - timedelta(days=5)).isoformat(),
                    "reason": "Low quality content detected",
                    "fix_suggestion": "Expand content, add unique value",
                },
            ],
        }

        return {
            "data": status_check,
            "recommendations": [],
        }

    async def _find_not_indexed(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Find all "Crawled - Not Indexed" pages.

        These are pages Google saw but chose not to index.
        """
        domain = params.get("domain")

        # In production, query Search Console API for this specific status
        not_indexed_analysis = {
            "domain": domain,
            "total_not_indexed": 235,
            "not_indexed_pages": [
                {
                    "url": f"{domain}/product/item-123",
                    "last_crawled": "2025-01-10",
                    "reason": "Low quality content",
                    "word_count": 87,
                    "fix": "Expand to 300+ words with unique details",
                },
                {
                    "url": f"{domain}/product/item-456",
                    "last_crawled": "2025-01-12",
                    "reason": "Duplicate content",
                    "similar_to": f"{domain}/product/item-789",
                    "fix": "Add unique product details and differentiation",
                },
                {
                    "url": f"{domain}/category/accessories",
                    "last_crawled": "2025-01-13",
                    "reason": "Thin content",
                    "word_count": 45,
                    "fix": "Add category description, buying guide",
                },
            ],
            "common_reasons": {
                "low_quality": 98,
                "duplicate": 67,
                "thin_content": 45,
                "crawl_budget": 25,
            },
        }

        recommendations = [
            Recommendation(
                title="Fix Low Quality Content Issues",
                description="98 pages marked as low quality. Expand content, add unique value, improve depth.",
                category="Indexing - Content Quality",
                priority=Priority.CRITICAL,
                estimated_impact="Get 98 pages indexed",
                implementation_effort="very_high",
            ),
            Recommendation(
                title="Resolve Duplicate Content",
                description="67 pages flagged as duplicates. Add unique differentiators and canonicals.",
                category="Indexing - Duplicate Content",
                priority=Priority.HIGH,
                estimated_impact="Get 67 pages indexed",
                implementation_effort="high",
            ),
        ]

        return {
            "data": not_indexed_analysis,
            "recommendations": recommendations,
        }

    async def _prioritize_pages(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Prioritize which not-indexed pages to fix first.

        Based on:
        - Traffic potential
        - Business value
        - Fix difficulty
        - Competitive importance
        """
        pages = params.get("pages", [])

        # Score each page by priority
        priority_pages = []
        for page in pages[:10]:  # Limit to prevent long processing
            priority_score = self._calculate_page_priority(page)
            priority_pages.append({
                **page,
                "priority_score": priority_score,
                "priority_level": self._get_priority_level(priority_score),
            })

        # Sort by priority
        priority_pages.sort(key=lambda x: x["priority_score"], reverse=True)

        priority_analysis = {
            "total_pages": len(pages),
            "priority_pages": priority_pages[:20],  # Top 20
            "priority_breakdown": {
                "critical": len([p for p in priority_pages if p["priority_level"] == "critical"]),
                "high": len([p for p in priority_pages if p["priority_level"] == "high"]),
                "medium": len([p for p in priority_pages if p["priority_level"] == "medium"]),
                "low": len([p for p in priority_pages if p["priority_level"] == "low"]),
            },
        }

        return {
            "data": priority_analysis,
            "recommendations": [],
        }

    def _calculate_page_priority(self, page: dict[str, Any]) -> float:
        """Calculate priority score for a page (0-100)."""
        score = 0

        # Traffic potential (0-40 points)
        if "search_volume" in page:
            score += min(page["search_volume"] / 100, 40)

        # Business value (0-30 points)
        if "page_type" in page:
            if page["page_type"] == "product":
                score += 30
            elif page["page_type"] == "category":
                score += 25
            elif page["page_type"] == "blog":
                score += 15

        # Fix difficulty (0-20 points, inverse - easier = higher score)
        if "fix" in page:
            if "expand" in page["fix"].lower():
                score += 15  # Easy fix
            elif "duplicate" in page["fix"].lower():
                score += 10  # Medium difficulty
            else:
                score += 5  # Hard fix

        # Competitive importance (0-10 points)
        if "competitive_value" in page:
            score += page["competitive_value"]

        return min(score, 100)

    def _get_priority_level(self, score: float) -> str:
        """Get priority level from score."""
        if score >= 80:
            return "critical"
        elif score >= 60:
            return "high"
        elif score >= 40:
            return "medium"
        else:
            return "low"

    def _calculate_indexing_health(self, stats: dict[str, Any]) -> float:
        """Calculate overall indexing health score (0-100)."""
        total_pages = stats["total_pages"]
        if total_pages == 0:
            return 0

        indexed_rate = (stats["indexed"] / total_pages) * 100
        crawled_not_indexed_penalty = (stats["crawled_not_indexed"] / total_pages) * 50
        error_penalty = (stats.get("error", 0) / total_pages) * 30

        health_score = indexed_rate - crawled_not_indexed_penalty - error_penalty

        return max(min(health_score, 100), 0)

    def _analyze_crawl_budget(self, stats: dict[str, Any], total_pages: int) -> dict[str, Any]:
        """Analyze crawl budget efficiency."""
        crawled_not_indexed = stats["crawled_not_indexed"]
        indexed = stats["indexed"]

        efficiency = (indexed / (indexed + crawled_not_indexed)) * 100 if (indexed + crawled_not_indexed) > 0 else 0

        return {
            "crawl_efficiency": round(efficiency, 1),
            "wasted_crawls": crawled_not_indexed,
            "status": "good" if efficiency > 80 else "needs_improvement" if efficiency > 60 else "poor",
            "recommendation": "Reduce crawled-not-indexed pages to improve crawl budget efficiency" if efficiency < 80 else "Crawl budget usage is efficient",
        }
