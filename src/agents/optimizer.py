"""Optimization Recommender Agent - Generates and manages optimization suggestions."""

import json
from typing import Any

import structlog

from src.agents.base import AgentContext, BaseAgent
from src.models.agents import (
    AgentResult,
    AgentTask,
    AgentType,
    Recommendation,
    RecommendationPriority,
    RecommendationType,
)
from src.models.content import OptimizationSuggestion, OptimizationStatus, OptimizationType, SchemaType

logger = structlog.get_logger()


class OptimizationRecommenderAgent(BaseAgent):
    """
    Generates optimization recommendations:
    1. Schema markup suggestions
    2. Content restructuring for AIO
    3. FAQ generation
    4. Meta tag optimization
    """

    agent_type = AgentType.OPTIMIZATION_RECOMMENDER

    async def execute(self, task: AgentTask) -> AgentResult:
        """Execute an optimization task."""
        task_type = task.task_type
        params = task.parameters

        if task_type == "generate_recommendations":
            return await self._generate_recommendations(params)
        elif task_type == "generate_schema":
            return await self._generate_schema(params)
        elif task_type == "generate_faq":
            return await self._generate_faq(params)
        elif task_type == "optimize_for_query":
            return await self._optimize_for_query(params)
        elif task_type == "bulk_optimize":
            return await self._bulk_optimize(params)
        else:
            return AgentResult(
                task_id=task.id,
                agent_type=self.agent_type,
                success=False,
                data={"error": f"Unknown task type: {task_type}"},
            )

    async def _generate_recommendations(self, params: dict[str, Any]) -> AgentResult:
        """Generate optimization recommendations for a page."""
        url = params.get("url")
        page_content = params.get("page_content")
        page_type = params.get("page_type", "product")
        target_queries = params.get("target_queries", [])

        if not url:
            return AgentResult(
                task_id="",
                agent_type=self.agent_type,
                success=False,
                data={"error": "URL is required"},
            )

        recommendations = []
        suggestions = []

        # Get current page analysis if content provided
        if page_content:
            # Analyze for AIO optimization
            aio_analysis = await self.context.openai_client.analyze_for_aio_optimization(
                query=target_queries[0] if target_queries else "",
                page_content=page_content,
            )

            # Generate schema recommendations
            for schema_rec in aio_analysis.get("schema_recommendations", []):
                schema_type = schema_rec.get("type", "WebPage")

                suggestion = OptimizationSuggestion(
                    page_id="",
                    page_url=url,
                    optimization_type=OptimizationType.ADD_SCHEMA,
                    title=f"Add {schema_type} schema",
                    description=f"Add {schema_type} schema markup to improve AI visibility",
                    rationale=f"This page type benefits from {schema_type} schema for AIO citations",
                    schema_type=SchemaType(schema_type) if schema_type in SchemaType.__members__.values() else None,
                    schema_json=schema_rec.get("content"),
                    estimated_aio_impact="High",
                    confidence=0.8,
                )
                suggestions.append(suggestion)

                recommendations.append(
                    Recommendation(
                        type=RecommendationType.SCHEMA_MARKUP,
                        priority=RecommendationPriority.HIGH,
                        title=f"Add {schema_type} schema",
                        description=suggestion.description,
                        affected_url=url,
                        implementation_code=json.dumps(schema_rec.get("content"), indent=2),
                        auto_implementable=True,
                    )
                )

            # Generate content recommendations
            for content_rec in aio_analysis.get("content_recommendations", []):
                recommendations.append(
                    Recommendation(
                        type=RecommendationType.CONTENT_STRUCTURE,
                        priority=RecommendationPriority.MEDIUM,
                        title=f"Improve content: {content_rec.get('section', 'general')}",
                        description=content_rec.get("rationale", ""),
                        affected_url=url,
                        current_state=content_rec.get("current"),
                        recommended_state=content_rec.get("suggested"),
                    )
                )

            # Quick wins
            for quick_win in aio_analysis.get("quick_wins", []):
                recommendations.append(
                    Recommendation(
                        type=RecommendationType.CONTENT_STRUCTURE,
                        priority=RecommendationPriority.HIGH,
                        title=f"Quick win: {quick_win[:50]}...",
                        description=quick_win,
                        affected_url=url,
                        implementation_effort="Easy",
                    )
                )

        # Generate page-type specific recommendations
        type_recommendations = await self._get_page_type_recommendations(page_type, url)
        recommendations.extend(type_recommendations)

        return AgentResult(
            task_id="",
            agent_type=self.agent_type,
            success=True,
            data={
                "url": url,
                "page_type": page_type,
                "total_recommendations": len(recommendations),
                "suggestions": [s.model_dump() for s in suggestions],
            },
            recommendations=recommendations,
        )

    async def _generate_schema(self, params: dict[str, Any]) -> AgentResult:
        """Generate Schema.org markup for a page."""
        page_type = params.get("page_type", "product")
        page_data = params.get("page_data", {})
        url = params.get("url", "")

        if not page_data:
            return AgentResult(
                task_id="",
                agent_type=self.agent_type,
                success=False,
                data={"error": "page_data is required"},
            )

        schema = await self.context.openai_client.generate_schema_markup(
            page_type=page_type,
            page_data=page_data,
        )

        if "error" in schema:
            return AgentResult(
                task_id="",
                agent_type=self.agent_type,
                success=False,
                data=schema,
            )

        # Wrap in JSON-LD script tag
        json_ld = f"""<script type="application/ld+json">
{json.dumps(schema, indent=2, ensure_ascii=False)}
</script>"""

        return AgentResult(
            task_id="",
            agent_type=self.agent_type,
            success=True,
            data={
                "url": url,
                "page_type": page_type,
                "schema": schema,
                "json_ld": json_ld,
            },
            recommendations=[
                Recommendation(
                    type=RecommendationType.SCHEMA_MARKUP,
                    priority=RecommendationPriority.HIGH,
                    title=f"Add {page_type} schema",
                    description="Generated Schema.org markup ready for implementation",
                    affected_url=url,
                    implementation_code=json_ld,
                    auto_implementable=True,
                )
            ],
        )

    async def _generate_faq(self, params: dict[str, Any]) -> AgentResult:
        """Generate FAQ content and schema for a page/topic."""
        topic = params.get("topic", "")
        page_content = params.get("page_content", "")
        target_queries = params.get("target_queries", [])
        url = params.get("url", "")
        num_faqs = params.get("num_faqs", 5)

        prompt = f"""Generate {num_faqs} FAQ items for a pharmacy website about: {topic}

Target search queries to address:
{chr(10).join(f'- {q}' for q in target_queries[:10])}

Existing page content:
{page_content[:5000]}

Requirements:
1. Questions should match how people actually search
2. Answers should be concise but complete (50-150 words)
3. Include relevant medical/pharmacy information
4. Be factually accurate and cite sources where appropriate

Return as JSON:
{{
    "faqs": [
        {{"question": "...", "answer": "..."}},
        ...
    ],
    "faq_schema": {{...}}  // FAQPage schema.org markup
}}"""

        response = await self.context.openai_client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            json_mode=True,
        )

        try:
            result = json.loads(response)
        except json.JSONDecodeError:
            return AgentResult(
                task_id="",
                agent_type=self.agent_type,
                success=False,
                data={"error": "Failed to generate FAQ", "raw": response},
            )

        faqs = result.get("faqs", [])
        faq_schema = result.get("faq_schema") or self._build_faq_schema(faqs)

        return AgentResult(
            task_id="",
            agent_type=self.agent_type,
            success=True,
            data={
                "topic": topic,
                "url": url,
                "faqs": faqs,
                "faq_schema": faq_schema,
            },
            recommendations=[
                Recommendation(
                    type=RecommendationType.FAQ_ADDITION,
                    priority=RecommendationPriority.HIGH,
                    title=f"Add FAQ section about {topic}",
                    description=f"Generated {len(faqs)} FAQ items targeting your search queries",
                    affected_url=url,
                    implementation_code=json.dumps(faq_schema, indent=2),
                    auto_implementable=True,
                )
            ],
        )

    async def _optimize_for_query(self, params: dict[str, Any]) -> AgentResult:
        """Generate optimizations for a specific query."""
        query = params.get("query", "")
        url = params.get("url", "")
        page_content = params.get("page_content", "")
        current_aio_content = params.get("aio_content")

        if not query or not page_content:
            return AgentResult(
                task_id="",
                agent_type=self.agent_type,
                success=False,
                data={"error": "query and page_content are required"},
            )

        # Analyze for AIO optimization
        analysis = await self.context.openai_client.analyze_for_aio_optimization(
            query=query,
            page_content=page_content,
            current_aio_content=current_aio_content,
        )

        recommendations = []

        # Priority based on current AIO alignment
        base_priority = (
            RecommendationPriority.CRITICAL
            if analysis.get("current_aio_alignment_score", 0) < 30
            else RecommendationPriority.HIGH
        )

        # Key issues
        for issue in analysis.get("key_issues", []):
            recommendations.append(
                Recommendation(
                    type=RecommendationType.CONTENT_STRUCTURE,
                    priority=base_priority,
                    title=f"Fix: {issue[:50]}...",
                    description=issue,
                    affected_url=url,
                    affected_query=query,
                )
            )

        # Schema recommendations
        for schema_rec in analysis.get("schema_recommendations", []):
            recommendations.append(
                Recommendation(
                    type=RecommendationType.SCHEMA_MARKUP,
                    priority=RecommendationPriority.HIGH,
                    title=f"Add {schema_rec.get('type', 'schema')}",
                    description=f"Add schema markup to improve AIO citation for '{query}'",
                    affected_url=url,
                    affected_query=query,
                    implementation_code=json.dumps(schema_rec.get("content"), indent=2),
                    auto_implementable=True,
                )
            )

        # Content changes
        for content_rec in analysis.get("content_recommendations", []):
            recommendations.append(
                Recommendation(
                    type=RecommendationType.CONTENT_STRUCTURE,
                    priority=RecommendationPriority.MEDIUM,
                    title=f"Update: {content_rec.get('section', 'content')}",
                    description=content_rec.get("rationale", ""),
                    affected_url=url,
                    affected_query=query,
                    current_state=content_rec.get("current"),
                    recommended_state=content_rec.get("suggested"),
                )
            )

        return AgentResult(
            task_id="",
            agent_type=self.agent_type,
            success=True,
            data={
                "query": query,
                "url": url,
                "current_aio_alignment_score": analysis.get("current_aio_alignment_score"),
                "analysis": analysis,
            },
            recommendations=recommendations,
        )

    async def _bulk_optimize(self, params: dict[str, Any]) -> AgentResult:
        """Generate optimizations for multiple pages."""
        pages = params.get("pages", [])  # List of {url, content, queries}

        if not pages:
            return AgentResult(
                task_id="",
                agent_type=self.agent_type,
                success=False,
                data={"error": "pages list is required"},
            )

        all_recommendations = []
        results = []

        for page in pages[:20]:  # Limit for API costs
            result = await self._generate_recommendations({
                "url": page.get("url"),
                "page_content": page.get("content"),
                "target_queries": page.get("queries", []),
            })

            results.append({
                "url": page.get("url"),
                "recommendations_count": len(result.recommendations),
            })

            all_recommendations.extend(result.recommendations)

        # Deduplicate and prioritize
        unique_recommendations = self._deduplicate_recommendations(all_recommendations)

        return AgentResult(
            task_id="",
            agent_type=self.agent_type,
            success=True,
            data={
                "pages_processed": len(pages),
                "total_recommendations": len(unique_recommendations),
                "by_page": results,
            },
            recommendations=unique_recommendations[:50],  # Top 50
        )

    async def _get_page_type_recommendations(
        self,
        page_type: str,
        url: str,
    ) -> list[Recommendation]:
        """Get standard recommendations for a page type."""
        recommendations = []

        type_recommendations = {
            "product": [
                ("Product schema with offers", "Add Product schema with price, availability, and reviews"),
                ("FAQ about usage", "Add FAQ section about product usage, dosage, side effects"),
                ("Breadcrumb navigation", "Add BreadcrumbList schema for navigation"),
            ],
            "category": [
                ("ItemList schema", "Add ItemList schema for category products"),
                ("FAQ about category", "Add FAQ section about the product category"),
                ("Filter structured data", "Mark up filters and sorting options"),
            ],
            "article": [
                ("Article schema", "Add Article or MedicalWebPage schema"),
                ("Author credentials", "Add author schema with medical credentials"),
                ("FAQ from content", "Extract FAQ from article content"),
            ],
            "location": [
                ("Pharmacy schema", "Add Pharmacy/LocalBusiness schema"),
                ("Opening hours", "Add OpeningHoursSpecification"),
                ("Contact information", "Ensure all contact details are marked up"),
            ],
        }

        for title, description in type_recommendations.get(page_type, []):
            recommendations.append(
                Recommendation(
                    type=RecommendationType.SCHEMA_MARKUP,
                    priority=RecommendationPriority.MEDIUM,
                    title=title,
                    description=description,
                    affected_url=url,
                )
            )

        return recommendations

    def _build_faq_schema(self, faqs: list[dict[str, str]]) -> dict[str, Any]:
        """Build FAQPage schema from FAQ items."""
        return {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": faq["question"],
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": faq["answer"],
                    },
                }
                for faq in faqs
            ],
        }

    def _deduplicate_recommendations(
        self,
        recommendations: list[Recommendation],
    ) -> list[Recommendation]:
        """Deduplicate and prioritize recommendations."""
        seen = set()
        unique = []

        for rec in recommendations:
            key = (rec.type, rec.title, rec.affected_url)
            if key not in seen:
                seen.add(key)
                unique.append(rec)

        # Sort by priority
        priority_order = {
            RecommendationPriority.CRITICAL: 0,
            RecommendationPriority.HIGH: 1,
            RecommendationPriority.MEDIUM: 2,
            RecommendationPriority.LOW: 3,
        }

        unique.sort(key=lambda r: priority_order.get(r.priority, 99))

        return unique
