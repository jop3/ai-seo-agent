"""
GEO (Generative Engine Optimization) Analyzer Agent.

Analyzes and scores content for citation likelihood in AI-generated answers.
Inspired by the shift from SEO to GEO in AI-powered search.
"""

import re
from datetime import datetime
from typing import Any

import structlog

from src.agents.base import BaseAgent, AgentContext
from src.models.agents import AgentTask, AgentResult, Recommendation, Alert, Priority, Severity

logger = structlog.get_logger()


class GEOAnalyzerAgent(BaseAgent):
    """
    Analyzes content for GEO (Generative Engine Optimization).

    GEO = Optimizing content to be cited in AI-generated answers from
    ChatGPT, Claude, Gemini, Perplexity, and other generative AI engines.

    Key principle: "Bra SEO är bra GEO" (Good SEO is good GEO)

    Capabilities:
    - Citation worthiness scoring
    - Question coverage analysis
    - Answer directness evaluation
    - FAQ completeness assessment
    - Source credibility signals
    - Content structure optimization
    """

    def __init__(self, context: AgentContext):
        super().__init__(
            agent_type="geo-analyzer",
            description="Analyzes content for Generative Engine Optimization (GEO)",
            context=context,
        )

    async def run(self, task: AgentTask) -> AgentResult:
        """Execute GEO analysis task."""
        start_time = datetime.utcnow()

        try:
            if task.task_type == "full_geo_audit":
                result = await self._full_geo_audit(task.parameters)
            elif task.task_type == "geo_score":
                result = await self._calculate_geo_score(task.parameters)
            elif task.task_type == "question_coverage":
                result = await self._analyze_question_coverage(task.parameters)
            elif task.task_type == "citation_prediction":
                result = await self._predict_citation_likelihood(task.parameters)
            elif task.task_type == "geo_vs_seo":
                result = await self._compare_geo_vs_seo(task.parameters)
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
            logger.error("GEO analysis failed", error=str(e))
            return AgentResult(
                task_id=task.id,
                agent_type=self.agent_type,
                success=False,
                data={"error": str(e)},
            )

    async def _full_geo_audit(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Full GEO audit of content.

        Analyzes all GEO factors and provides comprehensive scoring.
        """
        urls = params.get("urls", [])
        if not urls and self.context.property_url:
            urls = [self.context.property_url]

        results = {
            "analyzed_at": datetime.utcnow().isoformat(),
            "urls_analyzed": len(urls),
            "overall_geo_score": 0,
            "pages": [],
        }

        recommendations = []
        alerts = []

        # For each URL, analyze GEO factors
        for url in urls[:10]:  # Limit to 10 for demo
            page_score = await self._analyze_page_geo(url)
            results["pages"].append(page_score)

            # Generate recommendations
            if page_score["question_score"] < 50:
                recommendations.append(Recommendation(
                    title=f"Add Question-Based Headings - {url}",
                    description=f"Only {page_score['questions_found']} question-based headings found. Convert {page_score['conversion_opportunities']} headings to questions.",
                    category="GEO - Content Structure",
                    priority=Priority.HIGH,
                    estimated_impact="15-25% increase in AI citation likelihood",
                    implementation_effort="low",
                    auto_implementable=False,
                ))

            if not page_score["has_faq"]:
                recommendations.append(Recommendation(
                    title=f"Add FAQ Section - {url}",
                    description="No FAQ section detected. Add FAQ schema with 5-10 common questions.",
                    category="GEO - FAQ",
                    priority=Priority.HIGH,
                    estimated_impact="20-30% increase in AI citation likelihood",
                    implementation_effort="low",
                    auto_implementable=True,
                ))

            if page_score["direct_answer_score"] < 60:
                recommendations.append(Recommendation(
                    title=f"Add Direct Answers - {url}",
                    description="Content lacks direct answers in opening paragraphs. Add concise answers before detailed explanations.",
                    category="GEO - Answer Directness",
                    priority=Priority.MEDIUM,
                    estimated_impact="10-15% increase in AI comprehension",
                    implementation_effort="medium",
                ))

            if page_score["source_credibility"] < 70:
                alerts.append(Alert(
                    title=f"Weak Source Citations - {url}",
                    message=f"Only {page_score['sources_cited']} sources cited. Add citations to authoritative sources.",
                    severity=Severity.WARNING,
                    source=self.agent_type,
                    affected_urls=[url],
                ))

        # Calculate overall score
        if results["pages"]:
            results["overall_geo_score"] = sum(p["geo_score"] for p in results["pages"]) / len(results["pages"])

        # Scoring breakdown
        results["score_breakdown"] = {
            "citation_worthiness": sum(p["citation_worthiness"] for p in results["pages"]) / len(results["pages"]) if results["pages"] else 0,
            "question_coverage": sum(p["question_score"] for p in results["pages"]) / len(results["pages"]) if results["pages"] else 0,
            "answer_directness": sum(p["direct_answer_score"] for p in results["pages"]) / len(results["pages"]) if results["pages"] else 0,
            "faq_completeness": sum(p["faq_score"] for p in results["pages"]) / len(results["pages"]) if results["pages"] else 0,
            "source_credibility": sum(p["source_credibility"] for p in results["pages"]) / len(results["pages"]) if results["pages"] else 0,
        }

        return {
            "data": results,
            "recommendations": recommendations,
            "alerts": alerts,
        }

    async def _analyze_page_geo(self, url: str) -> dict[str, Any]:
        """Analyze a single page for GEO factors."""
        # In production, this would fetch and parse the page
        # For now, return scoring structure

        # Simulated analysis (replace with actual scraping/parsing)
        content_analysis = {
            "headings_count": 15,
            "question_headings": 6,
            "has_faq": False,
            "faq_items": 0,
            "sources_cited": 3,
            "has_author_bio": True,
            "has_dates": True,
            "has_schema": False,
            "text_clarity": 78,
            "semantic_relevance": 82,
        }

        # Score each factor
        question_score = (content_analysis["question_headings"] / max(content_analysis["headings_count"], 1)) * 100
        faq_score = 100 if content_analysis["has_faq"] else 0
        direct_answer_score = 65  # Would analyze actual content
        source_credibility = min(content_analysis["sources_cited"] * 20, 100)

        citation_worthiness = (
            question_score * 0.25 +
            faq_score * 0.20 +
            direct_answer_score * 0.20 +
            source_credibility * 0.20 +
            content_analysis["text_clarity"] * 0.15
        )

        geo_score = (
            citation_worthiness * 0.4 +
            question_score * 0.2 +
            faq_score * 0.2 +
            source_credibility * 0.2
        )

        return {
            "url": url,
            "geo_score": round(geo_score, 1),
            "citation_worthiness": round(citation_worthiness, 1),
            "question_score": round(question_score, 1),
            "faq_score": faq_score,
            "direct_answer_score": direct_answer_score,
            "source_credibility": source_credibility,
            "questions_found": content_analysis["question_headings"],
            "conversion_opportunities": content_analysis["headings_count"] - content_analysis["question_headings"],
            "has_faq": content_analysis["has_faq"],
            "sources_cited": content_analysis["sources_cited"],
            "has_author": content_analysis["has_author_bio"],
            "has_dates": content_analysis["has_dates"],
        }

    async def _calculate_geo_score(self, params: dict[str, Any]) -> dict[str, Any]:
        """Calculate GEO score for content."""
        url = params.get("url")
        if not url:
            return {"data": {"error": "URL required"}}

        page_analysis = await self._analyze_page_geo(url)

        return {
            "data": {
                "url": url,
                "geo_score": page_analysis["geo_score"],
                "breakdown": {
                    "citation_worthiness": page_analysis["citation_worthiness"],
                    "question_coverage": page_analysis["question_score"],
                    "answer_directness": page_analysis["direct_answer_score"],
                    "faq_completeness": page_analysis["faq_score"],
                    "source_credibility": page_analysis["source_credibility"],
                },
                "interpretation": self._interpret_geo_score(page_analysis["geo_score"]),
            }
        }

    def _interpret_geo_score(self, score: float) -> dict[str, Any]:
        """Interpret GEO score and provide guidance."""
        if score >= 80:
            return {
                "level": "Excellent",
                "description": "High likelihood of AI citation",
                "action": "Maintain current optimization level",
            }
        elif score >= 60:
            return {
                "level": "Good",
                "description": "Moderate likelihood of AI citation",
                "action": "Selective improvements in weak areas",
            }
        elif score >= 40:
            return {
                "level": "Moderate",
                "description": "Low-moderate AI citation likelihood",
                "action": "Systematic GEO enhancement needed",
            }
        else:
            return {
                "level": "Poor",
                "description": "Very low AI citation likelihood",
                "action": "Critical GEO optimization required",
            }

    async def _analyze_question_coverage(self, params: dict[str, Any]) -> dict[str, Any]:
        """Analyze how well content covers questions."""
        url = params.get("url")

        # Simulated analysis
        analysis = {
            "total_headings": 15,
            "question_headings": 6,
            "question_coverage_pct": 40.0,
            "detected_questions": [
                "What is SEO?",
                "How does GEO work?",
                "Why is AI search important?",
                "When should I optimize for AI?",
                "Where do AI engines get data?",
                "Who benefits from GEO?",
            ],
            "recommended_questions": [
                "What's the difference between SEO and GEO?",
                "How can I measure GEO success?",
                "Which AI engines should I optimize for?",
                "What are the key GEO ranking factors?",
            ],
        }

        recommendations = []

        if analysis["question_coverage_pct"] < 50:
            recommendations.append(Recommendation(
                title="Increase Question-Based Headings",
                description=f"Convert {9 - analysis['question_headings']} headings to questions for better AI comprehension",
                category="GEO - Questions",
                priority=Priority.HIGH,
                estimated_impact="15-22% increase in AI citation rate",
                implementation_effort="low",
            ))

        return {
            "data": analysis,
            "recommendations": recommendations,
        }

    async def _predict_citation_likelihood(self, params: dict[str, Any]) -> dict[str, Any]:
        """Predict likelihood of being cited by AI engines."""
        url = params.get("url")

        page_analysis = await self._analyze_page_geo(url)

        # Citation likelihood factors
        factors = {
            "has_sources": page_analysis["sources_cited"] > 0,
            "has_dates": page_analysis["has_dates"],
            "has_author_bio": page_analysis["has_author"],
            "has_faq": page_analysis["has_faq"],
            "question_coverage": page_analysis["question_score"],
            "text_clarity": 78,
            "topic_authority": 75,  # Would come from E-E-A-T analyzer
        }

        # Calculate likelihood (0-100)
        base_score = page_analysis["geo_score"]

        # Boost for specific factors
        boosts = 0
        if factors["has_sources"]:
            boosts += 10
        if factors["has_dates"]:
            boosts += 5
        if factors["has_author_bio"]:
            boosts += 8
        if factors["has_faq"]:
            boosts += 12

        citation_likelihood = min(base_score + boosts, 100)

        return {
            "data": {
                "url": url,
                "citation_likelihood": round(citation_likelihood, 1),
                "confidence": "high" if citation_likelihood > 70 else "medium" if citation_likelihood > 40 else "low",
                "factors": factors,
                "recommendations": self._get_citation_improvements(factors, citation_likelihood),
            }
        }

    def _get_citation_improvements(self, factors: dict[str, Any], current_score: float) -> list[dict[str, Any]]:
        """Get recommendations to improve citation likelihood."""
        improvements = []

        if not factors["has_sources"]:
            improvements.append({
                "action": "Add source citations",
                "impact": "+10-15% citation likelihood",
                "effort": "Low",
            })

        if not factors["has_dates"]:
            improvements.append({
                "action": "Add publication/update dates",
                "impact": "+5-8% citation likelihood",
                "effort": "Low",
            })

        if not factors["has_author_bio"]:
            improvements.append({
                "action": "Add author bio with credentials",
                "impact": "+8-12% citation likelihood",
                "effort": "Low",
            })

        if not factors["has_faq"]:
            improvements.append({
                "action": "Add FAQ section with schema",
                "impact": "+12-18% citation likelihood",
                "effort": "Low",
            })

        if factors["question_coverage"] < 50:
            improvements.append({
                "action": "Convert headings to questions",
                "impact": "+10-15% citation likelihood",
                "effort": "Low",
            })

        return improvements

    async def _compare_geo_vs_seo(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Compare GEO performance vs SEO performance.

        Shows the complementary nature of both.
        """
        # This would integrate with SEO analysis and traffic data

        comparison = {
            "seo_metrics": {
                "organic_traffic": params.get("organic_traffic", 0),
                "avg_position": params.get("avg_position", 0),
                "click_through_rate": params.get("ctr", 0),
                "seo_score": params.get("seo_score", 0),
            },
            "geo_metrics": {
                "ai_citations_detected": params.get("ai_citations", 0),
                "ai_referrer_traffic": params.get("ai_traffic", 0),
                "citation_rate": params.get("citation_rate", 0),
                "geo_score": params.get("geo_score", 0),
            },
            "opportunities": {
                "high_seo_low_geo": [],  # Good SEO but poor GEO - optimize for AI
                "high_geo_low_seo": [],  # Good GEO but poor SEO - improve rankings
                "low_both": [],           # Poor both - priority optimization
                "high_both": [],          # Excellent both - maintain
            },
            "strategic_focus": "",
        }

        # Determine strategy
        seo_score = comparison["seo_metrics"]["seo_score"]
        geo_score = comparison["geo_metrics"]["geo_score"]

        if seo_score > 70 and geo_score < 50:
            comparison["strategic_focus"] = "Optimize for GEO while maintaining SEO strength"
        elif geo_score > 70 and seo_score < 50:
            comparison["strategic_focus"] = "Improve SEO rankings to boost AI citation sources"
        elif seo_score < 50 and geo_score < 50:
            comparison["strategic_focus"] = "Dual optimization - both SEO and GEO need improvement"
        else:
            comparison["strategic_focus"] = "Maintain excellent performance in both channels"

        return {
            "data": comparison,
            "recommendations": self._generate_geo_seo_recommendations(seo_score, geo_score),
        }

    def _generate_geo_seo_recommendations(self, seo_score: float, geo_score: float) -> list[Recommendation]:
        """Generate recommendations based on SEO vs GEO performance."""
        recommendations = []

        if seo_score > 70 and geo_score < 60:
            recommendations.append(Recommendation(
                title="Leverage SEO Strength for GEO Gains",
                description="You have strong SEO. Add FAQ sections, question-based headings, and source citations to boost AI citations.",
                category="GEO Strategy",
                priority=Priority.HIGH,
                estimated_impact="20-30% increase in AI citations within 2-3 months",
                implementation_effort="low",
            ))

        if geo_score > 70 and seo_score < 60:
            recommendations.append(Recommendation(
                title="Improve SEO to Maximize GEO Value",
                description="Your content is AI-citation-ready, but low rankings limit visibility. Focus on technical SEO and backlinks.",
                category="SEO Foundation",
                priority=Priority.HIGH,
                estimated_impact="Higher rankings will increase AI engine data source quality",
                implementation_effort="medium",
            ))

        return recommendations
