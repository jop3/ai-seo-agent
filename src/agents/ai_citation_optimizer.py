"""
AI Citation Optimizer - Optimize content to increase AI citations.

Based on Swedish AI Mode launch insights:
- Deep expert content gets cited (not generic content)
- E-E-A-T signals critical
- Technical stability matters
- Sites ranking position 4-10 can still get citations

Focus: Optimize FOR being cited, not just FOR ranking.
"""

from datetime import datetime
from typing import Any

import structlog

from src.agents.base import BaseAgent, AgentContext
from src.models.agents import AgentTask, AgentResult, Recommendation, Alert, Priority, Severity

logger = structlog.get_logger()


class AICitationOptimizerAgent(BaseAgent):
    """
    Optimizes content for maximum AI citation likelihood.

    Key optimization factors for AI citations:
    1. Expert depth (detailed, authoritative)
    2. E-E-A-T signals (Experience, Expertise, Authoritativeness, Trust)
    3. Content structure (easy for AI to extract)
    4. Unique insights (not available elsewhere)
    5. Source credibility (citations, references)
    6. Question coverage (answers common questions)
    7. Technical quality (fast, accessible)
    """

    # Citation likelihood factors
    CITATION_FACTORS = {
        "expert_depth": {
            "weight": 0.25,
            "description": "Comprehensive, authoritative content",
            "indicators": ["word_count >1500", "technical_detail", "case_studies"],
        },
        "eeat_signals": {
            "weight": 0.20,
            "description": "E-E-A-T signals present",
            "indicators": ["author_bio", "credentials", "references", "citations"],
        },
        "content_structure": {
            "weight": 0.15,
            "description": "AI-friendly structure",
            "indicators": ["clear_headings", "bullet_points", "tables", "summaries"],
        },
        "unique_insights": {
            "weight": 0.15,
            "description": "Original research or insights",
            "indicators": ["original_data", "unique_perspective", "new_information"],
        },
        "source_credibility": {
            "weight": 0.10,
            "description": "Credible sources cited",
            "indicators": ["external_citations", "data_sources", "expert_quotes"],
        },
        "question_coverage": {
            "weight": 0.10,
            "description": "Answers common questions",
            "indicators": ["faq_section", "question_headings", "comprehensive_answers"],
        },
        "technical_quality": {
            "weight": 0.05,
            "description": "Technical excellence",
            "indicators": ["fast_load", "mobile_friendly", "schema_markup"],
        },
    }

    def __init__(self, context: AgentContext):
        super().__init__(
            agent_type="ai-citation-optimizer",
            description="Optimizes content to increase likelihood of AI citations",
            context=context,
        )

    async def run(self, task: AgentTask) -> AgentResult:
        """Execute AI citation optimization task."""
        start_time = datetime.utcnow()

        try:
            if task.task_type == "optimize_for_citations":
                result = await self._optimize_for_citations(task.parameters)
            elif task.task_type == "analyze_citation_potential":
                result = await self._analyze_citation_potential(task.parameters)
            elif task.task_type == "optimize_content_structure":
                result = await self._optimize_content_structure(task.parameters)
            elif task.task_type== "enhance_expert_signals":
                result = await self._enhance_expert_signals(task.parameters)
            elif task.task_type == "full_citation_optimization":
                result = await self._full_citation_optimization(task.parameters)
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
            logger.error("AI citation optimization failed", error=str(e))
            return AgentResult(
                task_id=task.id,
                agent_type=self.agent_type,
                success=False,
                data={"error": str(e)},
            )

    async def _full_citation_optimization(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Complete AI citation optimization analysis.

        Analyzes all factors affecting citation likelihood and provides
        prioritized optimization recommendations.
        """
        url = params.get("url", self.context.property_url)

        results = {
            "analyzed_at": datetime.utcnow().isoformat(),
            "url": url,
            "overall_citation_potential": 0,
            "factor_scores": {},
            "current_citations": 0,
            "predicted_citations": 0,
            "optimization_opportunities": [],
        }

        recommendations = []
        alerts = []

        # Analyze each citation factor
        factor_scores = {}
        for factor_id, factor_info in self.CITATION_FACTORS.items():
            score = await self._analyze_factor(url, factor_id)
            factor_scores[factor_id] = {
                "score": score,
                "weight": factor_info["weight"],
                "description": factor_info["description"],
                "weighted_score": score * factor_info["weight"],
            }

        results["factor_scores"] = factor_scores

        # Calculate overall citation potential
        overall_potential = sum(f["weighted_score"] for f in factor_scores.values()) * 100
        results["overall_citation_potential"] = round(overall_potential, 1)

        # Predict citation increase with optimizations
        current_citations = params.get("current_citations", 0)
        predicted_increase = self._predict_citation_increase(overall_potential, factor_scores)
        results["current_citations"] = current_citations
        results["predicted_citations"] = current_citations + predicted_increase

        # Generate recommendations for each weak factor
        for factor_id, factor_data in factor_scores.items():
            if factor_data["score"] < 0.7:  # Below 70%
                rec = self._generate_factor_recommendation(factor_id, factor_data)
                if rec:
                    recommendations.append(rec)

        # Identify top opportunities
        opportunities = self._identify_opportunities(factor_scores)
        results["optimization_opportunities"] = opportunities

        # Alert if citation potential is low
        if overall_potential < 50:
            alerts.append(Alert(
                title="Low AI Citation Potential",
                message=f"Citation potential score is {overall_potential:.1f}/100. Significant optimization needed.",
                severity=Severity.WARNING,
                source=self.agent_type,
                affected_urls=[url],
            ))

        return {
            "data": results,
            "recommendations": recommendations,
            "alerts": alerts,
        }

    async def _analyze_citation_potential(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Analyze current citation potential of content.

        Scores content on all citation factors.
        """
        url = params.get("url")

        # In production, this would analyze actual content
        citation_analysis = {
            "url": url,
            "citation_potential_score": 68.5,  # 0-100
            "factors": {
                "expert_depth": {
                    "score": 72,
                    "status": "good",
                    "issues": ["Could add more technical detail", "Add case studies"],
                },
                "eeat_signals": {
                    "score": 65,
                    "status": "moderate",
                    "issues": ["Missing author credentials", "No external citations"],
                },
                "content_structure": {
                    "score": 78,
                    "status": "good",
                    "issues": ["Add more tables for data"],
                },
                "unique_insights": {
                    "score": 55,
                    "status": "weak",
                    "issues": ["Add original research", "Include unique data"],
                },
                "source_credibility": {
                    "score": 62,
                    "status": "moderate",
                    "issues": ["Cite more authoritative sources"],
                },
                "question_coverage": {
                    "score": 70,
                    "status": "good",
                    "issues": ["Expand FAQ section"],
                },
                "technical_quality": {
                    "score": 85,
                    "status": "excellent",
                    "issues": [],
                },
            },
            "estimated_citation_uplift": "+35-50% with optimizations",
        }

        recommendations = [
            Recommendation(
                title="Add Unique Insights and Original Data",
                description="Citation potential is limited by lack of unique insights. Add original research or data analysis.",
                category="AI Citations - Content Uniqueness",
                priority=Priority.HIGH,
                estimated_impact="+15-20% citation likelihood",
                implementation_effort="high",
            ),
        ]

        return {
            "data": citation_analysis,
            "recommendations": recommendations,
        }

    async def _analyze_factor(self, url: str, factor_id: str) -> float:
        """Analyze a specific citation factor (0-1 score)."""
        # Simulated scoring - in production, would analyze actual content
        scores = {
            "expert_depth": 0.72,
            "eeat_signals": 0.65,
            "content_structure": 0.78,
            "unique_insights": 0.55,
            "source_credibility": 0.62,
            "question_coverage": 0.70,
            "technical_quality": 0.85,
        }
        return scores.get(factor_id, 0.50)

    async def _optimize_for_citations(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Provide optimization recommendations to increase citations.

        Focus on highest-impact improvements.
        """
        url = params.get("url")

        optimization_plan = {
            "url": url,
            "current_citation_score": 68.5,
            "target_citation_score": 85.0,
            "optimizations": [
                {
                    "priority": "critical",
                    "optimization": "Add author credentials and bio",
                    "factor": "E-E-A-T signals",
                    "impact": "+8-12% citation likelihood",
                    "effort": "low",
                },
                {
                    "priority": "high",
                    "optimization": "Include original data or research",
                    "factor": "Unique insights",
                    "impact": "+10-15% citation likelihood",
                    "effort": "high",
                },
                {
                    "priority": "high",
                    "optimization": "Add expert quotes and external citations",
                    "factor": "Source credibility",
                    "impact": "+6-10% citation likelihood",
                    "effort": "medium",
                },
                {
                    "priority": "medium",
                    "optimization": "Expand content depth (current: 1200 words, target: 2000+)",
                    "factor": "Expert depth",
                    "impact": "+5-8% citation likelihood",
                    "effort": "medium",
                },
                {
                    "priority": "medium",
                    "optimization": "Add comprehensive FAQ section",
                    "factor": "Question coverage",
                    "impact": "+4-7% citation likelihood",
                    "effort": "medium",
                },
            ],
            "estimated_total_uplift": "+35-50% citation likelihood",
        }

        recommendations = [
            Recommendation(
                title="Implement Critical E-E-A-T Enhancements",
                description="Add author credentials, bio, and expertise indicators. This is critical for AI citation.",
                category="AI Citations - E-E-A-T",
                priority=Priority.CRITICAL,
                estimated_impact="+8-12% citation likelihood",
                implementation_effort="low",
                auto_implementable=False,
            ),
        ]

        return {
            "data": optimization_plan,
            "recommendations": recommendations,
        }

    async def _optimize_content_structure(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Optimize content structure for AI extraction.

        AI engines favor well-structured, scannable content.
        """
        url = params.get("url")

        structure_analysis = {
            "url": url,
            "current_structure_score": 68,
            "target_structure_score": 85,
            "structure_elements": {
                "headings": {
                    "present": True,
                    "quality": "good",
                    "recommendations": ["Use more question-based headings"],
                },
                "bullet_points": {
                    "present": True,
                    "quality": "good",
                    "recommendations": ["Add bullet points in methodology section"],
                },
                "tables": {
                    "present": False,
                    "quality": "missing",
                    "recommendations": ["Add comparison table", "Add data tables"],
                },
                "summaries": {
                    "present": False,
                    "quality": "missing",
                    "recommendations": ["Add executive summary at top", "Add key takeaways section"],
                },
                "schema_markup": {
                    "present": True,
                    "quality": "basic",
                    "recommendations": ["Add HowTo schema", "Add FAQ schema"],
                },
            },
        }

        recommendations = [
            Recommendation(
                title="Add Data Tables for AI Extraction",
                description="AI engines extract structured data from tables more effectively. Add comparison and data tables.",
                category="AI Citations - Structure",
                priority=Priority.MEDIUM,
                estimated_impact="+5-8% better AI comprehension",
                implementation_effort="low",
            ),
            Recommendation(
                title="Add Executive Summary",
                description="Add a clear summary at the top. AI often cites summary sections directly.",
                category="AI Citations - Structure",
                priority=Priority.MEDIUM,
                estimated_impact="+6-10% citation likelihood",
                implementation_effort="low",
            ),
        ]

        return {
            "data": structure_analysis,
            "recommendations": recommendations,
        }

    async def _enhance_expert_signals(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Enhance expert and authority signals.

        Critical for being cited as authoritative source in AI Mode.
        """
        url = params.get("url")

        expert_signal_analysis = {
            "url": url,
            "expert_signal_score": 62,
            "signals_present": [
                "Author name",
                "Publishing date",
                "Basic content quality",
            ],
            "signals_missing": [
                "Author credentials",
                "Author photo",
                "Author bio",
                "External citations",
                "Expert quotes",
                "Data sources",
                "Case studies",
                "Professional affiliations",
            ],
            "eeat_breakdown": {
                "experience": 55,
                "expertise": 60,
                "authoritativeness": 65,
                "trustworthiness": 68,
            },
        }

        recommendations = [
            Recommendation(
                title="Add Comprehensive Author Credentials",
                description="Add author bio with credentials, expertise, and professional background. Critical for E-E-A-T.",
                category="AI Citations - E-E-A-T",
                priority=Priority.CRITICAL,
                estimated_impact="Required for expert source citations",
                implementation_effort="low",
            ),
            Recommendation(
                title="Include Expert Quotes and Citations",
                description="Reference industry experts and cite authoritative sources. Increases source credibility.",
                category="AI Citations - Authority",
                priority=Priority.HIGH,
                estimated_impact="+10-15% citation likelihood",
                implementation_effort="medium",
            ),
            Recommendation(
                title="Add Case Studies or Examples",
                description="Include real-world examples and case studies. Demonstrates practical expertise.",
                category="AI Citations - Experience",
                priority=Priority.MEDIUM,
                estimated_impact="+8-12% expert recognition",
                implementation_effort="high",
            ),
        ]

        return {
            "data": expert_signal_analysis,
            "recommendations": recommendations,
        }

    def _predict_citation_increase(
        self, current_potential: float, factor_scores: dict[str, Any]
    ) -> int:
        """Predict citation increase with optimizations."""
        # Simple prediction model
        weak_factors = sum(1 for f in factor_scores.values() if f["score"] < 0.7)
        potential_uplift = weak_factors * 8  # ~8% per weak factor improved
        return int(potential_uplift)

    def _generate_factor_recommendation(
        self, factor_id: str, factor_data: dict[str, Any]
    ) -> Recommendation | None:
        """Generate recommendation for a weak factor."""
        if factor_id == "expert_depth":
            return Recommendation(
                title="Increase Content Depth and Detail",
                description="Content lacks depth. Expand to 2000+ words with technical detail and examples.",
                category="AI Citations - Expert Depth",
                priority=Priority.HIGH,
                estimated_impact="+10-15% citation likelihood",
                implementation_effort="high",
            )
        elif factor_id == "eeat_signals":
            return Recommendation(
                title="Add E-E-A-T Signals",
                description="Missing author credentials and citations. Add author bio, credentials, and cite sources.",
                category="AI Citations - E-E-A-T",
                priority=Priority.CRITICAL,
                estimated_impact="+12-18% citation likelihood",
                implementation_effort="low",
            )
        elif factor_id == "unique_insights":
            return Recommendation(
                title="Add Original Research or Data",
                description="Content lacks unique insights. Include original research, data analysis, or unique perspective.",
                category="AI Citations - Uniqueness",
                priority=Priority.HIGH,
                estimated_impact="+15-20% citation likelihood",
                implementation_effort="very_high",
            )
        # Add more as needed
        return None

    def _identify_opportunities(self, factor_scores: dict[str, Any]) -> list[dict[str, Any]]:
        """Identify top optimization opportunities."""
        opportunities = []

        for factor_id, factor_data in factor_scores.items():
            if factor_data["score"] < 0.7:
                gap = (0.85 - factor_data["score"]) * 100  # Target 85%
                opportunities.append({
                    "factor": factor_id,
                    "current_score": round(factor_data["score"] * 100, 1),
                    "target_score": 85.0,
                    "gap": round(gap, 1),
                    "priority": "high" if gap > 20 else "medium",
                })

        # Sort by gap (biggest opportunities first)
        opportunities.sort(key=lambda x: x["gap"], reverse=True)

        return opportunities[:5]  # Top 5 opportunities
