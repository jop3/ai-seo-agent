"""Azure OpenAI / AI Foundry integration."""

from typing import Any

import structlog
from openai import AsyncAzureOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import AzureSettings

logger = structlog.get_logger()


class AzureOpenAIClient:
    """Client for Azure OpenAI / AI Foundry."""

    def __init__(self, settings: AzureSettings):
        self.settings = settings
        self._client = None

    def _get_client(self) -> AsyncAzureOpenAI:
        """Lazy initialization of Azure OpenAI client."""
        if self._client is None:
            self._client = AsyncAzureOpenAI(
                api_key=self.settings.openai_api_key.get_secret_value(),
                api_version=self.settings.openai_api_version,
                azure_endpoint=self.settings.openai_endpoint,
            )
        return self._client

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        json_mode: bool = False,
    ) -> str:
        """
        Send a chat completion request.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            json_mode: Whether to request JSON output

        Returns:
            The assistant's response content
        """
        client = self._get_client()

        kwargs: dict[str, Any] = {
            "model": self.settings.openai_deployment,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = await client.chat.completions.create(**kwargs)

        content = response.choices[0].message.content or ""

        logger.debug(
            "Azure OpenAI chat completed",
            tokens_prompt=response.usage.prompt_tokens if response.usage else 0,
            tokens_completion=response.usage.completion_tokens if response.usage else 0,
        )

        return content

    async def analyze_page_for_agents(
        self,
        page_content: str,
        page_url: str,
    ) -> dict[str, Any]:
        """
        Analyze how an AI agent would interpret a page.

        Returns structured analysis of what an agent can extract and do.
        """
        system_prompt = """You are an AI agent evaluating a webpage for "agent-friendliness".
Analyze the page as if you were an autonomous shopping agent trying to help a user.

Evaluate:
1. Can you clearly identify what products/services are available?
2. Can you extract structured data (prices, availability, descriptions)?
3. Could you complete a purchase or action on behalf of a user?
4. What information is missing or unclear?
5. How would you summarize this page to a user?

Respond in JSON format with these fields:
{
    "summary": "Brief summary of what this page offers",
    "extractable_data": {
        "products": [...],
        "prices": [...],
        "availability": "...",
        "other": {...}
    },
    "can_complete_action": true/false,
    "action_blockers": ["list of things preventing action completion"],
    "missing_information": ["list of missing info"],
    "agent_friendliness_score": 0-100,
    "recommendations": ["list of improvements for agent accessibility"]
}"""

        user_prompt = f"""Analyze this page:
URL: {page_url}

Page Content:
{page_content[:15000]}"""  # Truncate to fit context

        response = await self.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            json_mode=True,
        )

        import json
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            logger.error("Failed to parse agent analysis response")
            return {"error": "Failed to parse response", "raw": response}

    async def analyze_for_aio_optimization(
        self,
        query: str,
        page_content: str,
        current_aio_content: str | None = None,
    ) -> dict[str, Any]:
        """
        Analyze how to optimize a page to be cited in AI Overviews.
        """
        system_prompt = """You are an SEO expert specializing in AI Overview optimization.
Analyze the page content and suggest how to optimize it to be cited in Google's AI Overviews.

Consider:
1. Content structure (clear headings, concise answers)
2. Schema.org markup recommendations
3. FAQ opportunities
4. Authoritative signals (citations, expertise)
5. Content gaps compared to what the AI Overview needs

Respond in JSON format:
{
    "current_aio_alignment_score": 0-100,
    "key_issues": ["list of issues"],
    "schema_recommendations": [
        {"type": "FAQPage", "content": {...}},
        ...
    ],
    "content_recommendations": [
        {"section": "...", "current": "...", "suggested": "...", "rationale": "..."}
    ],
    "quick_wins": ["easy changes with high impact"],
    "estimated_improvement": "description of expected impact"
}"""

        user_prompt = f"""Query: {query}

Current AI Overview (if any): {current_aio_content or 'None detected'}

Page Content to Optimize:
{page_content[:12000]}"""

        response = await self.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.4,
            json_mode=True,
        )

        import json
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            logger.error("Failed to parse AIO optimization response")
            return {"error": "Failed to parse response", "raw": response}

    async def classify_queries(
        self,
        queries: list[str],
    ) -> list[dict[str, Any]]:
        """Classify a batch of queries by intent and AIO risk."""
        system_prompt = """Classify each search query by:
1. Intent: informational, navigational, transactional, commercial, local
2. AIO Risk: high (likely to trigger AI Overview), medium, low
3. Optimization Priority: high, medium, low

Return JSON array:
[
    {
        "query": "...",
        "intent": "...",
        "aio_risk": "high/medium/low",
        "optimization_priority": "high/medium/low",
        "rationale": "brief explanation"
    }
]"""

        user_prompt = f"Classify these queries:\n" + "\n".join(f"- {q}" for q in queries)

        response = await self.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            json_mode=True,
        )

        import json
        try:
            result = json.loads(response)
            return result if isinstance(result, list) else result.get("queries", [])
        except json.JSONDecodeError:
            logger.error("Failed to parse query classification response")
            return []

    async def generate_schema_markup(
        self,
        page_type: str,
        page_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate Schema.org markup for a page."""
        system_prompt = f"""Generate valid Schema.org JSON-LD markup for a {page_type} page.
The markup should be optimized for:
1. Google's rich results
2. AI Overview citations
3. Voice search / AI agent comprehension

Return only the JSON-LD object, properly formatted."""

        user_prompt = f"Page data:\n{page_data}"

        response = await self.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=3000,
        )

        # Try to extract JSON from response
        import json
        import re

        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        return {"error": "Failed to generate valid schema", "raw": response}
