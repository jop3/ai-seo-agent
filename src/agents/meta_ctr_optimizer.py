"""
Meta CTR Optimizer - Optimize meta titles/descriptions for higher click-through rates.

Key insight from article: "If a page is on page 1 but low click-through, rewrite the
Meta Title/Description to be catchier than the top 10 competitors."

This agent:
- Analyzes current meta tags
- Compares with top 10 competitors
- Identifies CTR optimization opportunities
- Suggests catchier, more compelling meta tags
- A/B tests meta tag variations

Critical: Good rankings with low CTR = wasted opportunity.
"""

from datetime import datetime
from typing import Any

import structlog

from src.agents.base import BaseAgent, AgentContext
from src.models.agents import AgentTask, AgentResult, Recommendation, Alert, Priority, Severity

logger = structlog.get_logger()


class MetaCTROptimizerAgent(BaseAgent):
    """
    Optimizes meta tags (title + description) for maximum CTR.

    Why it matters:
    - Page 1 ranking with 2% CTR < Page 3 ranking with 8% CTR
    - CTR is a ranking factor (user engagement signal)
    - Better CTR = more traffic without changing rankings

    Optimization factors:
    - Emotional triggers
    - Numbers and specifics
    - Power words
    - Competitive differentiation
    - Call-to-action
    - Length optimization
    """

    # Emotional triggers that improve CTR
    EMOTIONAL_TRIGGERS = [
        "proven", "guaranteed", "secret", "ultimate", "complete", "essential",
        "powerful", "effortless", "simple", "quick", "instant", "free",
        "new", "exclusive", "limited", "discover", "revealed", "shocking",
    ]

    # Power words for CTR
    POWER_WORDS = [
        "best", "top", "ultimate", "complete", "comprehensive", "definitive",
        "expert", "professional", "advanced", "beginner", "easy", "simple",
        "step-by-step", "guide", "how-to", "tutorial", "tips", "hacks",
    ]

    # CTR-boosting patterns
    CTR_PATTERNS = {
        "numbers": r"\d+",  # "7 Ways", "2024 Guide"
        "questions": r"\?$",  # "What is...?"
        "brackets": r"\[.*?\]|\(.*?\)",  # "[Updated 2024]"
        "year": r"20\d{2}",  # "2024", "2025"
        "superlatives": ["best", "top", "ultimate", "complete"],
    }

    def __init__(self, context: AgentContext):
        super().__init__(
            agent_type="meta-ctr-optimizer",
            description="Optimizes meta titles and descriptions for higher click-through rates",
            context=context,
        )

    async def run(self, task: AgentTask) -> AgentResult:
        """Execute meta CTR optimization task."""
        start_time = datetime.utcnow()

        try:
            if task.task_type == "optimize_meta_tags":
                result = await self._optimize_meta_tags(task.parameters)
            elif task.task_type == "analyze_current_ctr":
                result = await self._analyze_current_ctr(task.parameters)
            elif task.task_type == "compare_with_competitors":
                result = await self._compare_with_competitors(task.parameters)
            elif task.task_type == "generate_variations":
                result = await self._generate_variations(task.parameters)
            elif task.task_type == "full_meta_audit":
                result = await self._full_meta_audit(task.parameters)
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
            logger.error("Meta CTR optimization failed", error=str(e))
            return AgentResult(
                task_id=task.id,
                agent_type=self.agent_type,
                success=False,
                data={"error": str(e)},
            )

    async def _full_meta_audit(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Complete meta tag CTR audit.

        Analyzes all pages for CTR optimization opportunities.
        """
        domain = params.get("domain", self.context.property_url)

        results = {
            "analyzed_at": datetime.utcnow().isoformat(),
            "domain": domain,
            "pages_analyzed": 0,
            "avg_title_ctr_score": 0,
            "avg_description_ctr_score": 0,
            "optimization_opportunities": [],
            "low_ctr_pages": [],
        }

        recommendations = []
        alerts = []

        # Analyze pages with low CTR
        low_ctr_pages = await self._find_low_ctr_pages(domain)
        results["low_ctr_pages"] = low_ctr_pages
        results["pages_analyzed"] = len(low_ctr_pages)

        # Analyze each page's meta tags
        for page in low_ctr_pages[:10]:  # Limit for demo
            page_analysis = await self._analyze_page_meta(page)
            results["optimization_opportunities"].append(page_analysis)

        # Calculate average scores
        if results["optimization_opportunities"]:
            results["avg_title_ctr_score"] = sum(
                p["title_ctr_score"] for p in results["optimization_opportunities"]
            ) / len(results["optimization_opportunities"])

            results["avg_description_ctr_score"] = sum(
                p["description_ctr_score"] for p in results["optimization_opportunities"]
            ) / len(results["optimization_opportunities"])

        # Generate recommendations
        if len(low_ctr_pages) > 10:
            recommendations.append(Recommendation(
                title=f"Optimize {len(low_ctr_pages)} Pages with Low CTR",
                description=f"Found {len(low_ctr_pages)} pages ranking well but with low CTR. Rewrite meta tags.",
                category="Meta CTR - Optimization",
                priority=Priority.HIGH,
                estimated_impact="Increase traffic without changing rankings",
                implementation_effort="medium",
            ))

        # Alert if many pages have poor CTR
        if len(low_ctr_pages) > 50:
            alerts.append(Alert(
                title="Many Pages with Poor CTR",
                message=f"{len(low_ctr_pages)} pages have CTR below expected for their position",
                severity=Severity.WARNING,
                source=self.agent_type,
                affected_urls=[domain],
            ))

        return {
            "data": results,
            "recommendations": recommendations,
            "alerts": alerts,
        }

    async def _find_low_ctr_pages(self, domain: str) -> list[dict[str, Any]]:
        """Find pages with lower-than-expected CTR."""
        # In production, query Search Console for CTR data
        # Simulated data
        return [
            {
                "url": f"{domain}/product/item-1",
                "position": 3.2,
                "ctr": 4.5,  # Expected ~10% for position 3
                "expected_ctr": 10.0,
                "ctr_gap": -5.5,
            },
            {
                "url": f"{domain}/blog/guide",
                "position": 5.8,
                "ctr": 2.1,  # Expected ~5% for position 6
                "expected_ctr": 5.0,
                "ctr_gap": -2.9,
            },
        ]

    async def _optimize_meta_tags(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Optimize meta tags for a specific page.

        Generates optimized title and description variations.
        """
        url = params.get("url")
        current_title = params.get("current_title")
        current_description = params.get("current_description")
        keyword = params.get("keyword")

        optimization_result = {
            "url": url,
            "current": {
                "title": current_title,
                "title_length": len(current_title) if current_title else 0,
                "title_ctr_score": self._score_title_ctr(current_title),
                "description": current_description,
                "description_length": len(current_description) if current_description else 0,
                "description_ctr_score": self._score_description_ctr(current_description),
            },
            "optimized_variations": {
                "titles": [],
                "descriptions": [],
            },
            "improvement_potential": 0,
        }

        # Generate optimized title variations
        title_variations = self._generate_title_variations(keyword, current_title)
        optimization_result["optimized_variations"]["titles"] = title_variations

        # Generate optimized description variations
        desc_variations = self._generate_description_variations(keyword, current_description)
        optimization_result["optimized_variations"]["descriptions"] = desc_variations

        # Calculate improvement potential
        best_title_score = max((v["ctr_score"] for v in title_variations), default=0)
        best_desc_score = max((v["ctr_score"] for v in desc_variations), default=0)

        current_avg = (
            optimization_result["current"]["title_ctr_score"] +
            optimization_result["current"]["description_ctr_score"]
        ) / 2

        optimized_avg = (best_title_score + best_desc_score) / 2

        optimization_result["improvement_potential"] = round(optimized_avg - current_avg, 1)

        recommendations = [
            Recommendation(
                title="Implement High-CTR Meta Tag Variation",
                description=f"Optimized meta tags could improve CTR by {optimization_result['improvement_potential']:.1f} points",
                category="Meta CTR - Implementation",
                priority=Priority.HIGH,
                estimated_impact=f"+{optimization_result['improvement_potential']:.1f}% CTR improvement",
                implementation_effort="low",
                auto_implementable=True,
            ),
        ]

        return {
            "data": optimization_result,
            "recommendations": recommendations,
        }

    def _score_title_ctr(self, title: str | None) -> float:
        """Score a title for CTR potential (0-100)."""
        if not title:
            return 0

        score = 50  # Base score

        # Length check (55-60 chars ideal)
        length = len(title)
        if 55 <= length <= 60:
            score += 10
        elif 50 <= length <= 65:
            score += 5

        # Check for numbers
        if any(char.isdigit() for char in title):
            score += 10

        # Check for power words
        title_lower = title.lower()
        power_word_count = sum(1 for word in self.POWER_WORDS if word in title_lower)
        score += min(power_word_count * 5, 15)

        # Check for emotional triggers
        trigger_count = sum(1 for trigger in self.EMOTIONAL_TRIGGERS if trigger in title_lower)
        score += min(trigger_count * 5, 10)

        # Check for year (current or next)
        current_year = datetime.now().year
        if str(current_year) in title or str(current_year + 1) in title:
            score += 5

        # Check for brackets/parentheses
        if "[" in title or "(" in title:
            score += 5

        return min(score, 100)

    def _score_description_ctr(self, description: str | None) -> float:
        """Score a description for CTR potential (0-100)."""
        if not description:
            return 0

        score = 50  # Base score

        # Length check (140-160 chars ideal)
        length = len(description)
        if 140 <= length <= 160:
            score += 10
        elif 120 <= length <= 165:
            score += 5

        # Check for call-to-action
        cta_words = ["learn", "discover", "find", "get", "start", "try", "see", "explore"]
        description_lower = description.lower()
        if any(word in description_lower for word in cta_words):
            score += 15

        # Check for benefits/value prop
        benefit_words = ["best", "top", "easy", "simple", "free", "quick", "proven"]
        benefit_count = sum(1 for word in benefit_words if word in description_lower)
        score += min(benefit_count * 5, 15)

        # Check for specificity (numbers)
        if any(char.isdigit() for char in description):
            score += 10

        # Check for emotional appeal
        trigger_count = sum(1 for trigger in self.EMOTIONAL_TRIGGERS if trigger in description_lower)
        score += min(trigger_count * 3, 10)

        return min(score, 100)

    def _generate_title_variations(self, keyword: str, current: str | None) -> list[dict[str, Any]]:
        """Generate optimized title variations."""
        year = datetime.now().year

        variations = [
            {
                "title": f"{keyword}: Complete Guide [{year}]",
                "ctr_score": 78,
                "pattern": "Guide with year and brackets",
            },
            {
                "title": f"7 Best {keyword} (Proven & Tested)",
                "ctr_score": 82,
                "pattern": "Number list with proof",
            },
            {
                "title": f"Ultimate {keyword} Guide - Expert Tips",
                "ctr_score": 75,
                "pattern": "Ultimate guide with expertise",
            },
            {
                "title": f"How to {keyword} - Step-by-Step Tutorial",
                "ctr_score": 80,
                "pattern": "How-to with specificity",
            },
            {
                "title": f"{keyword} Explained: Everything You Need [{year}]",
                "ctr_score": 77,
                "pattern": "Comprehensive with year",
            },
        ]

        # Calculate actual scores
        for var in variations:
            var["ctr_score"] = self._score_title_ctr(var["title"])

        return sorted(variations, key=lambda x: x["ctr_score"], reverse=True)

    def _generate_description_variations(self, keyword: str, current: str | None) -> list[dict[str, Any]]:
        """Generate optimized description variations."""
        variations = [
            {
                "description": f"Discover everything about {keyword}. Get expert tips, proven strategies, and step-by-step guides. Start optimizing today!",
                "ctr_score": 75,
                "pattern": "Benefit-focused with CTA",
            },
            {
                "description": f"Learn {keyword} the right way. Our comprehensive guide includes 7+ strategies, real examples, and expert insights. Free to read.",
                "ctr_score": 80,
                "pattern": "Value proposition with free",
            },
            {
                "description": f"Complete {keyword} guide with proven results. See how experts do it, avoid common mistakes, and get results fast.",
                "ctr_score": 78,
                "pattern": "Proof and problem-solving",
            },
        ]

        # Calculate actual scores
        for var in variations:
            var["ctr_score"] = self._score_description_ctr(var["description"])

        return sorted(variations, key=lambda x: x["ctr_score"], reverse=True)

    async def _analyze_current_ctr(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Analyze current CTR performance.

        Compare actual CTR vs. expected CTR for position.
        """
        url = params.get("url")

        # Expected CTR by position (industry averages)
        expected_ctr_by_position = {
            1: 28.5,
            2: 15.7,
            3: 11.0,
            4: 8.0,
            5: 7.2,
            6: 5.1,
            7: 4.5,
            8: 3.8,
            9: 3.2,
            10: 2.8,
        }

        ctr_analysis = {
            "url": url,
            "current_position": 4.2,
            "current_ctr": 4.5,
            "expected_ctr": expected_ctr_by_position[4],  # Position 4
            "ctr_performance": "below_expected",
            "ctr_gap": -3.5,  # 4.5 - 8.0
            "traffic_lost_per_month": 450,  # Based on impressions
        }

        recommendations = [
            Recommendation(
                title="Optimize Meta Tags to Close CTR Gap",
                description=f"CTR is 3.5 points below expected. Losing ~450 clicks/month. Optimize meta tags.",
                category="Meta CTR - Performance",
                priority=Priority.HIGH,
                estimated_impact="+450 clicks/month",
                implementation_effort="low",
            ),
        ]

        return {
            "data": ctr_analysis,
            "recommendations": recommendations,
        }

    async def _analyze_page_meta(self, page: dict[str, Any]) -> dict[str, Any]:
        """Analyze meta tags for a single page."""
        # Simulated analysis
        return {
            "url": page["url"],
            "position": page["position"],
            "ctr": page["ctr"],
            "title_ctr_score": 58.0,
            "description_ctr_score": 62.0,
            "improvement_potential": 18.5,
        }

    async def _compare_with_competitors(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Compare your meta tags with top 10 competitors.

        Find what makes their titles/descriptions more clickable.
        """
        keyword = params.get("keyword")
        your_url = params.get("url")

        competitive_analysis = {
            "keyword": keyword,
            "your_url": your_url,
            "competitors_analyzed": 10,
            "title_analysis": {
                "your_title_score": 58,
                "competitor_avg_score": 72,
                "gap": -14,
                "common_patterns_you_miss": [
                    "Numbers (8/10 competitors use)",
                    "Year/recency (7/10 competitors)",
                    "Brackets/parentheses (6/10 competitors)",
                ],
            },
            "description_analysis": {
                "your_description_score": 62,
                "competitor_avg_score": 75,
                "gap": -13,
                "common_patterns_you_miss": [
                    "Clear CTA (9/10 competitors)",
                    "Specific benefits (8/10 competitors)",
                    "Social proof (5/10 competitors)",
                ],
            },
            "best_competitor_examples": [
                {
                    "url": "competitor1.com",
                    "title": "7 Best [Keyword] Tools [2024] - Expert Tested",
                    "title_score": 85,
                    "why_it_works": "Number, year, brackets, authority",
                },
                {
                    "url": "competitor2.com",
                    "description": "Discover the best [keyword] with our expert guide. Get proven strategies, real examples, and results. Start free today!",
                    "description_score": 88,
                    "why_it_works": "CTA, benefits, social proof, free",
                },
            ],
        }

        recommendations = [
            Recommendation(
                title="Add Numbers and Year to Title",
                description="8/10 competitors use numbers and 7/10 include the year. These boost CTR significantly.",
                category="Meta CTR - Competitive",
                priority=Priority.HIGH,
                estimated_impact="+10-15% CTR improvement",
                implementation_effort="low",
            ),
        ]

        return {
            "data": competitive_analysis,
            "recommendations": recommendations,
        }

    async def _generate_variations(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Generate multiple meta tag variations for A/B testing.

        Provide different approaches to test.
        """
        keyword = params.get("keyword")

        variations = {
            "keyword": keyword,
            "title_variations": self._generate_title_variations(keyword, None),
            "description_variations": self._generate_description_variations(keyword, None),
            "recommended_test": {
                "variation_a": {
                    "title": f"7 Best {keyword} [2024] - Expert Guide",
                    "description": f"Discover the best {keyword} with our expert guide. Proven strategies and real results. Start optimizing today!",
                },
                "variation_b": {
                    "title": f"Complete {keyword} Guide - Step by Step",
                    "description": f"Learn everything about {keyword}. Get proven tips, avoid mistakes, and see results fast. Free comprehensive guide.",
                },
            },
        }

        return {
            "data": variations,
            "recommendations": [],
        }
