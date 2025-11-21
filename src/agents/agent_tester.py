"""Agent Tester - Simulates how AI agents interpret and interact with pages."""

import asyncio
import json
from typing import Any

import structlog
from playwright.async_api import async_playwright, Page, Browser

from src.agents.base import AgentContext, BaseAgent
from src.models.agents import (
    AgentResult,
    AgentTask,
    AgentType,
    Recommendation,
    RecommendationPriority,
    RecommendationType,
)
from src.models.seo import PageAnalysis

logger = structlog.get_logger()


class AgentTesterAgent(BaseAgent):
    """
    Simulates AI agents interacting with pages to test:
    1. How LLMs interpret page content
    2. What data can be extracted (products, prices, etc.)
    3. Whether an agent could complete actions (add to cart, checkout)
    4. Schema.org markup validity and completeness
    """

    agent_type = AgentType.AGENT_TESTER

    async def execute(self, task: AgentTask) -> AgentResult:
        """Execute an agent testing task."""
        task_type = task.task_type
        params = task.parameters

        if task_type == "interpret_page":
            return await self._interpret_page(params)
        elif task_type == "test_checkout_flow":
            return await self._test_checkout_flow(params)
        elif task_type == "validate_schema":
            return await self._validate_schema(params)
        elif task_type == "bulk_page_test":
            return await self._bulk_page_test(params)
        elif task_type == "competitive_agent_test":
            return await self._competitive_agent_test(params)
        else:
            return AgentResult(
                task_id=task.id,
                agent_type=self.agent_type,
                success=False,
                data={"error": f"Unknown task type: {task_type}"},
            )

    async def _interpret_page(self, params: dict[str, Any]) -> AgentResult:
        """
        Test how an AI agent interprets a page.

        Fetches the page, extracts content, and asks LLM to analyze
        what it understands and can extract.
        """
        url = params.get("url")
        if not url:
            return AgentResult(
                task_id="",
                agent_type=self.agent_type,
                success=False,
                data={"error": "URL is required"},
            )

        # Fetch page content with Playwright
        page_data = await self._fetch_page(url)

        if "error" in page_data:
            return AgentResult(
                task_id="",
                agent_type=self.agent_type,
                success=False,
                data=page_data,
            )

        # Have LLM analyze the page
        analysis = await self.context.openai_client.analyze_page_for_agents(
            page_content=page_data["text_content"],
            page_url=url,
        )

        # Extract schema markup
        schema_data = page_data.get("schema_markup", [])

        # Calculate scores
        agent_friendliness_score = analysis.get("agent_friendliness_score", 0)

        # Generate recommendations
        recommendations = []

        if agent_friendliness_score < 70:
            for rec in analysis.get("recommendations", []):
                recommendations.append(
                    Recommendation(
                        type=RecommendationType.AGENT_ACCESSIBILITY,
                        priority=RecommendationPriority.MEDIUM,
                        title=rec,
                        description=f"Improve agent accessibility: {rec}",
                        affected_url=url,
                        estimated_impact="Medium",
                    )
                )

        # Check for missing schema
        if not schema_data:
            recommendations.append(
                Recommendation(
                    type=RecommendationType.SCHEMA_MARKUP,
                    priority=RecommendationPriority.HIGH,
                    title="Add Schema.org markup",
                    description="No structured data found. Add appropriate Schema.org markup for AI agent comprehension.",
                    affected_url=url,
                    estimated_impact="High",
                )
            )

        # Build page analysis
        page_analysis = PageAnalysis(
            url=url,
            title=page_data.get("title"),
            meta_description=page_data.get("meta_description"),
            h1=page_data.get("h1"),
            word_count=len(page_data.get("text_content", "").split()),
            schema_types=[s.get("@type", "Unknown") for s in schema_data],
            schema_valid=bool(schema_data),
            agent_summary=analysis.get("summary"),
            agent_extractable_data=analysis.get("extractable_data", {}),
            agent_actionable=analysis.get("can_complete_action", False),
            agent_friendliness_score=agent_friendliness_score,
        )

        return AgentResult(
            task_id="",
            agent_type=self.agent_type,
            success=True,
            data={
                "page_analysis": page_analysis.model_dump(),
                "llm_analysis": analysis,
                "schema_markup": schema_data,
                "action_blockers": analysis.get("action_blockers", []),
                "missing_information": analysis.get("missing_information", []),
            },
            recommendations=recommendations,
        )

    async def _test_checkout_flow(self, params: dict[str, Any]) -> AgentResult:
        """
        Test if an AI agent could complete a checkout flow.

        This simulates an autonomous shopping agent trying to:
        1. Find a product
        2. Add to cart
        3. Proceed to checkout

        Note: Does not actually complete purchases.
        """
        product_url = params.get("product_url")
        product_query = params.get("product_query", "")

        if not product_url:
            return AgentResult(
                task_id="",
                agent_type=self.agent_type,
                success=False,
                data={"error": "product_url is required"},
            )

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            flow_results = {
                "steps": [],
                "can_complete": False,
                "blockers": [],
            }

            try:
                # Step 1: Load product page
                await page.goto(product_url, wait_until="networkidle")
                await asyncio.sleep(1)

                flow_results["steps"].append({
                    "step": "load_product",
                    "success": True,
                    "url": product_url,
                })

                # Step 2: Try to find product information
                product_info = await self._extract_product_info(page)
                flow_results["product_info"] = product_info

                if not product_info.get("name"):
                    flow_results["blockers"].append("Could not extract product name")
                if not product_info.get("price"):
                    flow_results["blockers"].append("Could not extract price")

                flow_results["steps"].append({
                    "step": "extract_product_info",
                    "success": bool(product_info.get("name")),
                    "data": product_info,
                })

                # Step 3: Try to find add-to-cart button
                add_to_cart = await self._find_add_to_cart(page)

                flow_results["steps"].append({
                    "step": "find_add_to_cart",
                    "success": add_to_cart is not None,
                    "button_text": add_to_cart,
                })

                if not add_to_cart:
                    flow_results["blockers"].append("Could not find add to cart button")

                # Step 4: Check for checkout accessibility
                checkout_info = await self._check_checkout_requirements(page)
                flow_results["checkout_requirements"] = checkout_info

                if checkout_info.get("requires_login"):
                    flow_results["blockers"].append("Checkout requires login")

                # Overall assessment
                flow_results["can_complete"] = (
                    bool(product_info.get("name"))
                    and bool(product_info.get("price"))
                    and add_to_cart is not None
                    and not checkout_info.get("requires_login", True)
                )

            except Exception as e:
                flow_results["error"] = str(e)
                flow_results["steps"].append({
                    "step": "error",
                    "success": False,
                    "error": str(e),
                })

            finally:
                await browser.close()

        # Generate recommendations
        recommendations = []

        if not flow_results["can_complete"]:
            for blocker in flow_results["blockers"]:
                recommendations.append(
                    Recommendation(
                        type=RecommendationType.AGENT_ACCESSIBILITY,
                        priority=RecommendationPriority.HIGH,
                        title=f"Fix checkout blocker: {blocker}",
                        description=f"AI agents cannot complete checkout due to: {blocker}",
                        affected_url=product_url,
                        estimated_impact="High - Blocks AI agent conversions",
                    )
                )

        return AgentResult(
            task_id="",
            agent_type=self.agent_type,
            success=True,
            data=flow_results,
            recommendations=recommendations,
        )

    async def _validate_schema(self, params: dict[str, Any]) -> AgentResult:
        """Validate Schema.org markup on a page."""
        url = params.get("url")

        if not url:
            return AgentResult(
                task_id="",
                agent_type=self.agent_type,
                success=False,
                data={"error": "URL is required"},
            )

        page_data = await self._fetch_page(url)
        schema_data = page_data.get("schema_markup", [])

        validation_results = {
            "url": url,
            "schemas_found": len(schema_data),
            "schemas": [],
            "issues": [],
            "recommendations": [],
        }

        for schema in schema_data:
            schema_type = schema.get("@type", "Unknown")
            schema_result = {
                "type": schema_type,
                "valid": True,
                "completeness": 0,
                "missing_fields": [],
            }

            # Check required fields based on type
            required_fields = self._get_required_fields(schema_type)
            present_fields = set(schema.keys())
            missing = required_fields - present_fields

            schema_result["missing_fields"] = list(missing)
            schema_result["completeness"] = (
                (len(required_fields) - len(missing)) / len(required_fields) * 100
                if required_fields
                else 100
            )
            schema_result["valid"] = len(missing) == 0

            validation_results["schemas"].append(schema_result)

            if missing:
                validation_results["issues"].append(
                    f"{schema_type}: Missing required fields: {', '.join(missing)}"
                )

        # Generate recommendations
        recommendations = []

        for issue in validation_results["issues"]:
            recommendations.append(
                Recommendation(
                    type=RecommendationType.SCHEMA_MARKUP,
                    priority=RecommendationPriority.MEDIUM,
                    title=f"Fix schema: {issue.split(':')[0]}",
                    description=issue,
                    affected_url=url,
                )
            )

        # Check for missing schema types
        page_type = self._detect_page_type(page_data)
        recommended_schemas = self._get_recommended_schemas(page_type)
        existing_types = {s.get("@type") for s in schema_data}
        missing_schemas = recommended_schemas - existing_types

        for schema_type in missing_schemas:
            recommendations.append(
                Recommendation(
                    type=RecommendationType.SCHEMA_MARKUP,
                    priority=RecommendationPriority.HIGH,
                    title=f"Add {schema_type} schema",
                    description=f"Page appears to be a {page_type} but is missing {schema_type} schema markup",
                    affected_url=url,
                    auto_implementable=True,
                )
            )

        return AgentResult(
            task_id="",
            agent_type=self.agent_type,
            success=True,
            data=validation_results,
            recommendations=recommendations,
        )

    async def _bulk_page_test(self, params: dict[str, Any]) -> AgentResult:
        """Test multiple pages in batch."""
        urls = params.get("urls", [])
        concurrency = params.get("concurrency", 3)

        if not urls:
            return AgentResult(
                task_id="",
                agent_type=self.agent_type,
                success=False,
                data={"error": "URLs are required"},
            )

        semaphore = asyncio.Semaphore(concurrency)

        async def test_one(url: str) -> dict[str, Any]:
            async with semaphore:
                result = await self._interpret_page({"url": url})
                return {
                    "url": url,
                    "success": result.success,
                    "score": result.data.get("page_analysis", {}).get(
                        "agent_friendliness_score", 0
                    ),
                    "issues": len(result.recommendations),
                }

        results = await asyncio.gather(*[test_one(url) for url in urls])

        # Summary statistics
        scores = [r["score"] for r in results if r["success"]]
        avg_score = sum(scores) / len(scores) if scores else 0

        return AgentResult(
            task_id="",
            agent_type=self.agent_type,
            success=True,
            data={
                "pages_tested": len(urls),
                "successful_tests": len(scores),
                "average_agent_friendliness_score": avg_score,
                "results": results,
                "pages_needing_attention": [
                    r for r in results if r["score"] < 70
                ],
            },
        )

    async def _competitive_agent_test(self, params: dict[str, Any]) -> AgentResult:
        """
        Test how AI agents would compare client vs competitors for a query.

        Simulates: "An AI agent is asked to help buy [product].
        Who would it recommend?"
        """
        query = params.get("query")
        client_url = params.get("client_url")
        competitor_urls = params.get("competitor_urls", [])

        if not query or not client_url:
            return AgentResult(
                task_id="",
                agent_type=self.agent_type,
                success=False,
                data={"error": "query and client_url are required"},
            )

        all_urls = [client_url] + competitor_urls

        # Analyze each page
        analyses = {}
        for url in all_urls:
            page_data = await self._fetch_page(url)
            if "error" not in page_data:
                analysis = await self.context.openai_client.analyze_page_for_agents(
                    page_content=page_data["text_content"],
                    page_url=url,
                )
                analyses[url] = analysis

        # Ask LLM to compare and recommend
        comparison_prompt = f"""You are an AI shopping assistant. A user asked: "{query}"

I've analyzed these pages:

{json.dumps(analyses, indent=2)}

Based on which page:
1. Has the clearest product information
2. Makes it easiest to complete a purchase
3. Provides the most trustworthy information

Which would you recommend to the user and why?

Respond in JSON:
{{
    "recommended_url": "...",
    "recommendation_reason": "...",
    "rankings": [
        {{"url": "...", "score": 0-100, "pros": [...], "cons": [...]}}
    ],
    "client_competitive_position": "winning/competitive/losing"
}}"""

        comparison = await self.context.openai_client.chat(
            messages=[{"role": "user", "content": comparison_prompt}],
            temperature=0.3,
            json_mode=True,
        )

        try:
            comparison_data = json.loads(comparison)
        except json.JSONDecodeError:
            comparison_data = {"raw": comparison}

        return AgentResult(
            task_id="",
            agent_type=self.agent_type,
            success=True,
            data={
                "query": query,
                "client_url": client_url,
                "competitor_urls": competitor_urls,
                "comparison": comparison_data,
                "analyses": analyses,
            },
        )

    async def _fetch_page(self, url: str) -> dict[str, Any]:
        """Fetch a page and extract content using Playwright."""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                await page.goto(url, wait_until="networkidle", timeout=30000)
                await asyncio.sleep(1)  # Allow JS to settle

                # Extract data
                data = await page.evaluate("""() => {
                    // Get schema markup
                    const schemas = [];
                    document.querySelectorAll('script[type="application/ld+json"]').forEach(el => {
                        try {
                            schemas.push(JSON.parse(el.textContent));
                        } catch (e) {}
                    });

                    // Get meta description
                    const metaDesc = document.querySelector('meta[name="description"]');

                    // Get main content
                    const main = document.querySelector('main') || document.body;
                    const textContent = main.innerText.substring(0, 20000);

                    return {
                        title: document.title,
                        meta_description: metaDesc ? metaDesc.content : null,
                        h1: document.querySelector('h1')?.innerText || null,
                        text_content: textContent,
                        schema_markup: schemas.flat(),
                    };
                }""")

                await browser.close()
                return data

        except Exception as e:
            logger.error("Failed to fetch page", url=url, error=str(e))
            return {"error": str(e)}

    async def _extract_product_info(self, page: Page) -> dict[str, Any]:
        """Extract product information from a page."""
        return await page.evaluate("""() => {
            // Try schema first
            const schemas = document.querySelectorAll('script[type="application/ld+json"]');
            for (const el of schemas) {
                try {
                    const data = JSON.parse(el.textContent);
                    if (data['@type'] === 'Product' || data['@type'] === 'Drug') {
                        return {
                            name: data.name,
                            price: data.offers?.price || data.price,
                            currency: data.offers?.priceCurrency || 'SEK',
                            availability: data.offers?.availability,
                            description: data.description,
                            source: 'schema'
                        };
                    }
                } catch (e) {}
            }

            // Fallback to heuristics
            return {
                name: document.querySelector('h1')?.innerText ||
                      document.querySelector('[class*="product-name"]')?.innerText,
                price: document.querySelector('[class*="price"]')?.innerText,
                availability: document.querySelector('[class*="stock"], [class*="availability"]')?.innerText,
                source: 'heuristic'
            };
        }""")

    async def _find_add_to_cart(self, page: Page) -> str | None:
        """Find the add to cart button."""
        button = await page.evaluate("""() => {
            const selectors = [
                'button[class*="add-to-cart"]',
                'button[class*="buy"]',
                'button[class*="köp"]',
                'button[data-action="add-to-cart"]',
                'button:has-text("Lägg i varukorg")',
                'button:has-text("Köp")',
                'button:has-text("Add to cart")',
            ];

            for (const sel of selectors) {
                try {
                    const btn = document.querySelector(sel);
                    if (btn) return btn.innerText || btn.value || 'Found';
                } catch (e) {}
            }

            // Try any button with cart-related text
            const buttons = document.querySelectorAll('button');
            for (const btn of buttons) {
                const text = (btn.innerText || '').toLowerCase();
                if (text.includes('cart') || text.includes('köp') || text.includes('varukorg')) {
                    return btn.innerText;
                }
            }

            return null;
        }""")
        return button

    async def _check_checkout_requirements(self, page: Page) -> dict[str, Any]:
        """Check what's required for checkout."""
        return await page.evaluate("""() => {
            const hasLoginForm = !!document.querySelector('form[action*="login"], input[type="password"]');
            const hasGuestCheckout = !!(
                document.body.innerText.includes('guest') ||
                document.body.innerText.includes('gäst') ||
                document.querySelector('[class*="guest"]')
            );

            return {
                requires_login: hasLoginForm && !hasGuestCheckout,
                has_guest_checkout: hasGuestCheckout,
            };
        }""")

    def _get_required_fields(self, schema_type: str) -> set[str]:
        """Get required fields for a schema type."""
        required = {
            "Product": {"name", "offers"},
            "Drug": {"name", "activeIngredient"},
            "FAQPage": {"mainEntity"},
            "LocalBusiness": {"name", "address"},
            "Pharmacy": {"name", "address"},
            "Article": {"headline", "author", "datePublished"},
            "Organization": {"name"},
        }
        return required.get(schema_type, set())

    def _detect_page_type(self, page_data: dict[str, Any]) -> str:
        """Detect the type of page from content."""
        text = (page_data.get("text_content", "") + " " + (page_data.get("title") or "")).lower()

        if any(w in text for w in ["köp", "pris", "kr", "varukorg", "lägg i"]):
            return "product"
        elif any(w in text for w in ["hitta apotek", "öppettider", "adress"]):
            return "location"
        elif any(w in text for w in ["artikel", "guide", "tips", "hur"]):
            return "article"
        elif any(w in text for w in ["frågor", "faq", "vanliga"]):
            return "faq"
        else:
            return "other"

    def _get_recommended_schemas(self, page_type: str) -> set[str]:
        """Get recommended schema types for a page type."""
        recommendations = {
            "product": {"Product", "Offer", "BreadcrumbList"},
            "location": {"Pharmacy", "LocalBusiness", "OpeningHoursSpecification"},
            "article": {"Article", "MedicalWebPage", "BreadcrumbList"},
            "faq": {"FAQPage"},
            "other": {"WebPage", "BreadcrumbList"},
        }
        return recommendations.get(page_type, {"WebPage"})
