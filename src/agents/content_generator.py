"""
Content Generator Agent - Creates AIO-optimized content.
"""

from datetime import datetime
from typing import Any

import structlog

from src.agents.base import BaseAgent, AgentContext
from src.models.agents import AgentTask, AgentResult, Recommendation, Priority

logger = structlog.get_logger()


class ContentGeneratorAgent(BaseAgent):
    """
    Generates AIO-optimized content.

    Capabilities:
    - FAQ generation targeting AIO
    - How-to content creation
    - Listicle generation
    - Content briefs for writers
    - Schema-ready content structures
    """

    def __init__(self, context: AgentContext):
        super().__init__(
            agent_type="content-generator",
            description="Generates AI Overview optimized content",
            context=context,
        )

    async def run(self, task: AgentTask) -> AgentResult:
        """Execute content generation task."""
        start_time = datetime.utcnow()

        try:
            if task.task_type == "generate_faq":
                result = await self._generate_faq(task.parameters)
            elif task.task_type == "generate_howto":
                result = await self._generate_howto(task.parameters)
            elif task.task_type == "generate_listicle":
                result = await self._generate_listicle(task.parameters)
            elif task.task_type == "generate_content_brief":
                result = await self._generate_content_brief(task.parameters)
            elif task.task_type == "optimize_existing":
                result = await self._optimize_existing_content(task.parameters)
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
                execution_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
            )

        except Exception as e:
            logger.error("Content generation failed", error=str(e))
            return AgentResult(
                task_id=task.id,
                agent_type=self.agent_type,
                success=False,
                data={"error": str(e)},
            )

    async def _generate_faq(self, params: dict[str, Any]) -> dict[str, Any]:
        """Generate FAQ content optimized for AIO."""
        topic = params.get("topic", "")
        target_queries = params.get("queries", [])
        num_questions = params.get("num_questions", 10)

        if not self.context.openai_client:
            return {"data": {"error": "OpenAI client not configured"}}

        # Build prompt
        prompt = f"""Generate {num_questions} FAQ questions and answers about: {topic}

Target search queries to address:
{chr(10).join(f'- {q}' for q in target_queries[:10])}

Requirements:
1. Each answer should be 2-4 sentences - concise but complete
2. Start answers with the key information (AIO optimization)
3. Include specific data, numbers, or actionable advice where relevant
4. Questions should match natural language search patterns
5. Answers should be authoritative and factual

Format as JSON:
{{
  "faqs": [
    {{"question": "...", "answer": "..."}},
    ...
  ]
}}"""

        response = await self.context.openai_client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            response_format={"type": "json_object"},
        )

        try:
            import json
            faqs = json.loads(response)
        except:
            faqs = {"faqs": [], "raw_response": response}

        # Generate schema markup
        faq_schema = {
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
                for faq in faqs.get("faqs", [])
            ],
        }

        return {
            "data": {
                "topic": topic,
                "faqs": faqs.get("faqs", []),
                "schema_markup": faq_schema,
                "html_snippet": self._generate_faq_html(faqs.get("faqs", [])),
            },
            "recommendations": [
                Recommendation(
                    title="Add FAQ schema to page",
                    description="Include the generated FAQPage schema markup in your page's head",
                    priority=Priority.HIGH,
                    category="schema",
                ),
            ],
        }

    def _generate_faq_html(self, faqs: list[dict]) -> str:
        """Generate HTML for FAQ section."""
        html = '<div class="faq-section" itemscope itemtype="https://schema.org/FAQPage">\n'
        html += '  <h2>Frequently Asked Questions</h2>\n'

        for faq in faqs:
            html += f'''  <div class="faq-item" itemscope itemprop="mainEntity" itemtype="https://schema.org/Question">
    <h3 itemprop="name">{faq.get("question", "")}</h3>
    <div itemscope itemprop="acceptedAnswer" itemtype="https://schema.org/Answer">
      <p itemprop="text">{faq.get("answer", "")}</p>
    </div>
  </div>
'''
        html += '</div>'
        return html

    async def _generate_howto(self, params: dict[str, Any]) -> dict[str, Any]:
        """Generate HowTo content optimized for AIO."""
        topic = params.get("topic", "")
        target_query = params.get("query", topic)

        if not self.context.openai_client:
            return {"data": {"error": "OpenAI client not configured"}}

        prompt = f"""Create a step-by-step how-to guide for: {topic}
Target search query: {target_query}

Requirements:
1. 5-10 clear, actionable steps
2. Each step should be 1-2 sentences
3. Include estimated time for each step if relevant
4. Add any required tools/materials
5. Start with the most important action

Format as JSON:
{{
  "name": "How to ...",
  "description": "Brief overview",
  "totalTime": "PT30M",
  "estimatedCost": {{"currency": "USD", "value": "0"}},
  "supply": ["item1", "item2"],
  "tool": ["tool1", "tool2"],
  "steps": [
    {{"name": "Step title", "text": "Step description", "image": ""}}
  ]
}}"""

        response = await self.context.openai_client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            response_format={"type": "json_object"},
        )

        try:
            import json
            howto = json.loads(response)
        except:
            howto = {"name": topic, "steps": [], "raw_response": response}

        # Generate HowTo schema
        howto_schema = {
            "@context": "https://schema.org",
            "@type": "HowTo",
            "name": howto.get("name", ""),
            "description": howto.get("description", ""),
            "totalTime": howto.get("totalTime", ""),
            "supply": [{"@type": "HowToSupply", "name": s} for s in howto.get("supply", [])],
            "tool": [{"@type": "HowToTool", "name": t} for t in howto.get("tool", [])],
            "step": [
                {
                    "@type": "HowToStep",
                    "name": step.get("name", ""),
                    "text": step.get("text", ""),
                    "position": i + 1,
                }
                for i, step in enumerate(howto.get("steps", []))
            ],
        }

        return {
            "data": {
                "howto": howto,
                "schema_markup": howto_schema,
            },
        }

    async def _generate_listicle(self, params: dict[str, Any]) -> dict[str, Any]:
        """Generate listicle content."""
        topic = params.get("topic", "")
        list_type = params.get("type", "top")  # top, best, tips, reasons
        num_items = params.get("num_items", 10)

        if not self.context.openai_client:
            return {"data": {"error": "OpenAI client not configured"}}

        prompt = f"""Create a {list_type} {num_items} listicle about: {topic}

Requirements:
1. Each item needs a clear title and 2-3 sentence explanation
2. Order by importance/relevance
3. Be specific and actionable
4. Include data points where relevant

Format as JSON:
{{
  "title": "...",
  "introduction": "Brief intro paragraph",
  "items": [
    {{"title": "...", "description": "...", "key_point": "..."}}
  ],
  "conclusion": "Brief summary"
}}"""

        response = await self.context.openai_client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            response_format={"type": "json_object"},
        )

        try:
            import json
            listicle = json.loads(response)
        except:
            listicle = {"title": topic, "items": []}

        # Generate ItemList schema
        schema = {
            "@context": "https://schema.org",
            "@type": "ItemList",
            "name": listicle.get("title", ""),
            "description": listicle.get("introduction", ""),
            "numberOfItems": len(listicle.get("items", [])),
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": i + 1,
                    "name": item.get("title", ""),
                    "description": item.get("description", ""),
                }
                for i, item in enumerate(listicle.get("items", []))
            ],
        }

        return {
            "data": {
                "listicle": listicle,
                "schema_markup": schema,
            },
        }

    async def _generate_content_brief(self, params: dict[str, Any]) -> dict[str, Any]:
        """Generate a content brief for writers."""
        topic = params.get("topic", "")
        target_queries = params.get("queries", [])
        content_type = params.get("content_type", "article")

        if not self.context.openai_client:
            return {"data": {"error": "OpenAI client not configured"}}

        prompt = f"""Create a detailed content brief for a {content_type} about: {topic}

Target keywords/queries:
{chr(10).join(f'- {q}' for q in target_queries[:10])}

Include:
1. Recommended title (H1)
2. Meta description (150-160 chars)
3. Target word count
4. Suggested headings (H2, H3)
5. Key points to cover
6. Questions to answer
7. Internal linking suggestions
8. Schema types to include
9. AIO optimization tips

Format as JSON."""

        response = await self.context.openai_client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            response_format={"type": "json_object"},
        )

        try:
            import json
            brief = json.loads(response)
        except:
            brief = {"topic": topic, "raw_response": response}

        return {"data": {"brief": brief}}

    async def _optimize_existing_content(self, params: dict[str, Any]) -> dict[str, Any]:
        """Analyze and suggest optimizations for existing content."""
        content = params.get("content", "")
        target_query = params.get("query", "")

        if not self.context.openai_client or not content:
            return {"data": {"error": "Content and OpenAI client required"}}

        prompt = f"""Analyze this content for AI Overview optimization:

Target query: {target_query}

Content:
{content[:3000]}

Provide:
1. Current AIO-readiness score (0-100)
2. Key strengths
3. Specific improvements needed
4. Suggested additions (FAQs, steps, lists)
5. Schema recommendations
6. First paragraph rewrite optimized for AIO citation

Format as JSON."""

        response = await self.context.openai_client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            response_format={"type": "json_object"},
        )

        try:
            import json
            analysis = json.loads(response)
        except:
            analysis = {"raw_response": response}

        return {"data": {"analysis": analysis}}
