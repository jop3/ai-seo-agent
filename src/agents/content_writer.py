"""
Content Writer Agent

Generates high-quality blog posts and product news articles that match
the site's existing tone and style.

Key features:
- Analyzes existing articles to extract style/tone guidelines
- Generates content that sounds like it was written by the same team
- Incorporates trending topics and product recommendations
- Produces publish-ready content (not drafts that need heavy editing)
- PHARMA AWARE: Automatically fact-checks pharmaceutical content and flags items needing review
"""

import asyncio
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import httpx
import structlog
from bs4 import BeautifulSoup

from src.agents.base import BaseAgent, AgentCapability
from src.config import get_settings
from src.integrations.openai_client import AzureOpenAIClient

logger = structlog.get_logger()


@dataclass
class StyleGuide:
    """Extracted style guide from existing content."""
    tone: str = ""  # e.g., "friendly and professional", "expert but approachable"
    voice: str = ""  # e.g., "first person plural (we)", "second person (you)"
    sentence_style: str = ""  # e.g., "short and punchy", "detailed and thorough"
    vocabulary_level: str = ""  # e.g., "accessible", "technical", "mixed"
    common_phrases: list[str] = field(default_factory=list)
    formatting_patterns: list[str] = field(default_factory=list)
    avg_paragraph_length: int = 0
    uses_subheadings: bool = True
    uses_bullet_points: bool = True
    calls_to_action_style: str = ""
    example_intros: list[str] = field(default_factory=list)
    example_conclusions: list[str] = field(default_factory=list)
    brand_terms: list[str] = field(default_factory=list)  # Terms the brand always uses


@dataclass
class ArticleReference:
    """Reference article for style analysis."""
    url: str
    title: str
    content: str
    word_count: int
    publish_date: str | None = None
    category: str = ""


@dataclass
class GeneratedArticle:
    """A generated article ready for review."""
    title: str
    slug: str
    meta_description: str
    content: str  # Full HTML/Markdown content
    word_count: int
    target_keywords: list[str] = field(default_factory=list)
    featured_products: list[dict[str, Any]] = field(default_factory=list)
    suggested_images: list[str] = field(default_factory=list)
    internal_links: list[dict[str, str]] = field(default_factory=list)
    schema_markup: dict[str, Any] = field(default_factory=dict)
    style_match_score: float = 0.0  # How well it matches the style guide
    # Pharma review fields
    needs_pharma_review: bool = False
    pharma_review_reasons: list[str] = field(default_factory=list)
    pharma_fact_checks: list[dict[str, Any]] = field(default_factory=list)
    suggested_citations: list[dict[str, str]] = field(default_factory=list)


class ContentWriterAgent(BaseAgent):
    """
    Agent that generates blog posts and product news matching the site's style.

    Unlike generic content generators, this agent:
    1. First analyzes existing content to understand the brand voice
    2. Generates content that matches that voice exactly
    3. Incorporates SEO best practices and product placements naturally
    4. Produces content that needs minimal editing
    """

    name = "content-writer"
    description = "Generates blog posts and product news in your brand's voice"
    capabilities = [
        AgentCapability.CONTENT_GENERATION,
        AgentCapability.ANALYSIS,
    ]

    def __init__(self):
        super().__init__()
        self.settings = get_settings()
        self.llm_client = AzureOpenAIClient(self.settings)
        self._style_guide: StyleGuide | None = None
        self._reference_articles: list[ArticleReference] = []
        self._pharma_checker = None  # Lazy load

    def _get_pharma_checker(self):
        """Lazy load the pharma fact checker."""
        if self._pharma_checker is None:
            from src.agents.pharma_fact_checker import PharmaFactCheckerAgent
            self._pharma_checker = PharmaFactCheckerAgent()
        return self._pharma_checker

    async def fetch_article(self, url: str) -> ArticleReference | None:
        """Fetch and parse an article from a URL."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, follow_redirects=True)
                response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Try to find the main article content
            # Common selectors for article content
            content_selectors = [
                "article",
                ".article-content",
                ".post-content",
                ".entry-content",
                ".blog-content",
                "main",
                "#content",
            ]

            content_elem = None
            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    break

            if not content_elem:
                content_elem = soup.body

            # Extract text content
            # Remove script, style, nav, footer elements
            for tag in content_elem.find_all(["script", "style", "nav", "footer", "aside"]):
                tag.decompose()

            content = content_elem.get_text(separator="\n", strip=True)

            # Get title
            title_elem = soup.find("h1") or soup.find("title")
            title = title_elem.get_text(strip=True) if title_elem else "Untitled"

            return ArticleReference(
                url=url,
                title=title,
                content=content,
                word_count=len(content.split()),
            )

        except Exception as e:
            logger.error("Failed to fetch article", url=url, error=str(e))
            return None

    async def analyze_style(
        self,
        article_urls: list[str] | None = None,
        article_contents: list[str] | None = None,
        num_examples: int = 5,
    ) -> StyleGuide:
        """
        Analyze existing articles to extract a style guide.

        Can take either:
        - URLs to fetch and analyze
        - Raw article contents directly

        Returns a comprehensive style guide that can be used for generation.
        """
        logger.info("Analyzing content style", num_urls=len(article_urls or []))

        articles_text = []

        # Fetch articles from URLs
        if article_urls:
            tasks = [self.fetch_article(url) for url in article_urls[:num_examples]]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, ArticleReference):
                    articles_text.append(f"TITLE: {result.title}\n\n{result.content}")
                    self._reference_articles.append(result)

        # Add raw content if provided
        if article_contents:
            articles_text.extend(article_contents[:num_examples])

        if not articles_text:
            logger.warning("No articles available for style analysis")
            return StyleGuide()

        # Use LLM to analyze the style
        analysis_prompt = f"""Analyze these {len(articles_text)} articles and extract a detailed style guide.

ARTICLES TO ANALYZE:
{chr(10).join(f"--- Article {i+1} ---{chr(10)}{text[:3000]}" for i, text in enumerate(articles_text))}

---

Extract and provide a comprehensive style guide in the following format:

1. TONE: Describe the overall tone (e.g., "friendly and professional", "expert but approachable", "casual and conversational")

2. VOICE: What grammatical person is used? (e.g., "first person plural - we/our", "second person - you/your", "third person")

3. SENTENCE STYLE: Describe the sentence structure (e.g., "short and punchy sentences", "longer explanatory sentences", "mixed")

4. VOCABULARY LEVEL: How technical is the language? (e.g., "accessible to general public", "assumes some domain knowledge", "highly technical")

5. COMMON PHRASES: List 5-10 phrases or expressions that appear frequently or characterize the writing

6. FORMATTING PATTERNS: Describe how content is structured (use of subheadings, bullet points, numbered lists, etc.)

7. PARAGRAPH LENGTH: Typical paragraph length (short 1-2 sentences, medium 3-4, long 5+)

8. INTRO STYLE: How do articles typically begin? Provide 2-3 example patterns.

9. CONCLUSION STYLE: How do articles typically end? (call to action, summary, question to reader, etc.)

10. BRAND TERMS: Any specific terminology, product names, or phrases that should always be used

11. THINGS TO AVOID: Any patterns, words, or styles that should NOT be used based on these examples

Be specific and provide examples from the articles where possible."""

        try:
            analysis = await self.llm_client.chat(
                messages=[
                    {"role": "system", "content": "You are an expert content analyst specializing in brand voice and style guide extraction."},
                    {"role": "user", "content": analysis_prompt},
                ],
                temperature=0.3,
                max_tokens=2000,
            )

            # Parse the analysis into a StyleGuide
            # For now, store the raw analysis and use it in generation
            style_guide = StyleGuide(
                tone=self._extract_section(analysis, "TONE"),
                voice=self._extract_section(analysis, "VOICE"),
                sentence_style=self._extract_section(analysis, "SENTENCE STYLE"),
                vocabulary_level=self._extract_section(analysis, "VOCABULARY LEVEL"),
                common_phrases=self._extract_list(analysis, "COMMON PHRASES"),
                formatting_patterns=self._extract_list(analysis, "FORMATTING PATTERNS"),
                example_intros=self._extract_list(analysis, "INTRO STYLE"),
                example_conclusions=self._extract_list(analysis, "CONCLUSION STYLE"),
                brand_terms=self._extract_list(analysis, "BRAND TERMS"),
            )

            # Store for later use
            self._style_guide = style_guide
            self._raw_style_analysis = analysis

            logger.info("Style analysis complete", tone=style_guide.tone)
            return style_guide

        except Exception as e:
            logger.error("Style analysis failed", error=str(e))
            return StyleGuide()

    def _extract_section(self, text: str, section_name: str) -> str:
        """Extract a section from the analysis text."""
        pattern = rf"{section_name}:\s*(.+?)(?=\n\d+\.|$)"
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""

    def _extract_list(self, text: str, section_name: str) -> list[str]:
        """Extract a list from the analysis text."""
        section = self._extract_section(text, section_name)
        if not section:
            return []

        # Split by common list patterns
        items = re.split(r'\n[-•*]|\n\d+\.', section)
        return [item.strip() for item in items if item.strip()]

    async def suggest_products_for_topic(
        self,
        topic: str,
        category: str | None = None,
        max_products: int = 5,
    ) -> dict[str, Any]:
        """
        Suggest relevant products that could be featured in an article about a topic.

        Uses LLM to match topic to product categories and suggest specific products
        that would naturally fit the content.

        Args:
            topic: The article topic
            category: Optional category hint (e.g., "hudvård", "kosttillskott")
            max_products: Maximum number of products to suggest

        Returns:
            Dict with suggested products and reasoning
        """
        logger.info("Suggesting products for topic", topic=topic, category=category)

        # Product categories and example products (would be replaced with real catalog API)
        product_catalog = {
            "smärta_värk": [
                {"name": "Alvedon 500mg", "type": "otc", "use": "smärtlindring, feber"},
                {"name": "Ipren 400mg", "type": "otc", "use": "smärta, inflammation"},
                {"name": "Voltaren Gel", "type": "otc", "use": "muskelsmärta, ledvärk"},
                {"name": "Treo", "type": "otc", "use": "huvudvärk, migrän"},
            ],
            "förkylning": [
                {"name": "Nezeril nässpray", "type": "otc", "use": "nästäppa"},
                {"name": "Strepsils", "type": "otc", "use": "halsont"},
                {"name": "Nipaxon", "type": "otc", "use": "hosta"},
                {"name": "Alvedon", "type": "otc", "use": "feber, värk"},
            ],
            "allergi": [
                {"name": "Zyrtec", "type": "otc", "use": "allergisymtom"},
                {"name": "Clarityn", "type": "otc", "use": "hösnuva, allergi"},
                {"name": "Nasonex", "type": "rx", "use": "allergisk rinit"},
                {"name": "Lomudal ögondroppar", "type": "otc", "use": "ögonallergi"},
            ],
            "mage_tarm": [
                {"name": "Omeprazol", "type": "otc", "use": "halsbränna, sura uppstötningar"},
                {"name": "Imodium", "type": "otc", "use": "diarré"},
                {"name": "Laktulos", "type": "otc", "use": "förstoppning"},
                {"name": "Dimor", "type": "otc", "use": "illamående"},
            ],
            "hudvård": [
                {"name": "CeraVe Moisturizing Cream", "type": "cosmetic", "use": "torr hud"},
                {"name": "La Roche-Posay Cicaplast", "type": "cosmetic", "use": "irriterad hud"},
                {"name": "Eucerin AtopiControl", "type": "cosmetic", "use": "eksem, atopisk hud"},
                {"name": "ACO Spotless", "type": "cosmetic", "use": "acne, oren hy"},
            ],
            "kosttillskott": [
                {"name": "D-vitamin 50μg", "type": "supplement", "use": "D-vitaminbrist"},
                {"name": "Omega-3", "type": "supplement", "use": "hjärta, hjärna"},
                {"name": "Magnesium", "type": "supplement", "use": "muskler, sömn"},
                {"name": "Järn", "type": "supplement", "use": "blodbrist, trötthet"},
            ],
            "munvård": [
                {"name": "Sensodyne", "type": "cosmetic", "use": "känsliga tänder"},
                {"name": "Corsodyl", "type": "otc", "use": "tandköttsbesvär"},
                {"name": "Flux", "type": "cosmetic", "use": "fluorskydd"},
            ],
            "solskydd": [
                {"name": "La Roche-Posay Anthelios SPF50", "type": "cosmetic", "use": "solskydd ansikte"},
                {"name": "ACO Sol SPF30", "type": "cosmetic", "use": "solskydd kropp"},
                {"name": "Aloe Vera Gel", "type": "cosmetic", "use": "efter sol"},
            ],
            "barn": [
                {"name": "Alvedon Munsönderfallande", "type": "otc", "use": "barn feber/smärta"},
                {"name": "Nezeril Barn", "type": "otc", "use": "barn nästäppa"},
                {"name": "Miniderm", "type": "cosmetic", "use": "barn torr hud"},
            ],
        }

        prompt = f"""Given this article topic, suggest which product categories and specific products would naturally fit.

TOPIC: {topic}
{f"CATEGORY HINT: {category}" if category else ""}

Available product categories:
{chr(10).join(f"- {cat}: {', '.join(p['name'] for p in prods[:2])}, ..." for cat, prods in product_catalog.items())}

Respond with:
1. Which categories are most relevant (rank top 3)
2. Why these products fit the topic naturally
3. How to mention them without being salesy

Be specific - don't suggest products that don't genuinely fit the topic."""

        try:
            response = await self.llm_client.chat(
                messages=[
                    {"role": "system", "content": "You are a content strategist who helps match products to article topics naturally."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.5,
                max_tokens=1000,
            )

            # Extract suggested categories from response
            suggested_products = []
            response_lower = response.lower()

            for cat, products in product_catalog.items():
                if cat.replace("_", " ") in response_lower or cat in response_lower:
                    for product in products[:2]:  # Top 2 from each matching category
                        suggested_products.append({
                            "name": product["name"],
                            "type": product["type"],
                            "use_case": product["use"],
                            "category": cat,
                        })

            # Limit to max_products
            suggested_products = suggested_products[:max_products]

            return {
                "topic": topic,
                "suggested_products": suggested_products,
                "reasoning": response,
                "product_count": len(suggested_products),
            }

        except Exception as e:
            logger.error("Product suggestion failed", error=str(e))
            return {
                "topic": topic,
                "suggested_products": [],
                "reasoning": f"Could not generate suggestions: {str(e)}",
                "product_count": 0,
            }

    async def generate_article(
        self,
        topic: str,
        keywords: list[str] | None = None,
        products_to_feature: list[dict[str, Any]] | None = None,
        article_type: str = "blog",  # blog, product-news, guide, listicle
        word_count_target: int = 800,
        additional_context: str = "",
        reference_urls: list[str] | None = None,
    ) -> GeneratedArticle:
        """
        Generate a full article matching the site's style.

        Args:
            topic: The main topic/title idea
            keywords: Target SEO keywords to incorporate
            products_to_feature: Products to naturally mention/link
            article_type: Type of content to generate
            word_count_target: Approximate word count
            additional_context: Any additional context or requirements
            reference_urls: URLs to similar articles for style reference

        Returns:
            A complete, publish-ready article
        """
        logger.info(
            "Generating article",
            topic=topic,
            type=article_type,
            target_words=word_count_target,
        )

        # If no style guide yet and we have reference URLs, analyze them first
        if not self._style_guide and reference_urls:
            await self.analyze_style(article_urls=reference_urls)

        # Build the generation prompt
        style_instructions = ""
        if self._style_guide:
            style_instructions = f"""
STYLE GUIDE TO FOLLOW:
- Tone: {self._style_guide.tone}
- Voice: {self._style_guide.voice}
- Sentence style: {self._style_guide.sentence_style}
- Vocabulary: {self._style_guide.vocabulary_level}
- Common phrases to use: {', '.join(self._style_guide.common_phrases[:5])}
- Brand terms: {', '.join(self._style_guide.brand_terms[:5])}

INTRO STYLE EXAMPLES:
{chr(10).join(self._style_guide.example_intros[:2])}

CONCLUSION STYLE:
{chr(10).join(self._style_guide.example_conclusions[:2])}
"""
        elif hasattr(self, '_raw_style_analysis'):
            style_instructions = f"""
STYLE GUIDE TO FOLLOW:
{self._raw_style_analysis}
"""

        products_section = ""
        if products_to_feature:
            products_section = f"""
PRODUCTS TO NATURALLY FEATURE:
{chr(10).join(f"- {p.get('name', 'Product')}: {p.get('description', '')}" for p in products_to_feature[:5])}

Mention these products naturally where relevant. Don't force them in - only include where they genuinely fit the topic.
"""

        keywords_section = ""
        if keywords:
            keywords_section = f"""
TARGET KEYWORDS (incorporate naturally):
Primary: {keywords[0] if keywords else topic}
Secondary: {', '.join(keywords[1:5]) if len(keywords) > 1 else 'none'}
"""

        generation_prompt = f"""Write a {article_type} article about: {topic}

TARGET LENGTH: Approximately {word_count_target} words

{style_instructions}

{keywords_section}

{products_section}

{f"ADDITIONAL CONTEXT: {additional_context}" if additional_context else ""}

REQUIREMENTS:
1. Follow the style guide exactly - the article should sound like it was written by the same person who wrote the reference articles
2. Include a compelling headline/title
3. Include a meta description (150-160 characters)
4. Use proper formatting with subheadings (H2, H3)
5. Make it genuinely useful and informative - not generic filler content
6. Include a clear structure: intro, main content sections, conclusion
7. End with a subtle call to action that fits the brand voice
8. If featuring products, weave them in naturally as solutions/recommendations

FORMAT YOUR RESPONSE AS:
TITLE: [Your headline]

META_DESCRIPTION: [150-160 character description]

CONTENT:
[Full article content in Markdown format]

SUGGESTED_SLUG: [url-friendly-slug]

INTERNAL_LINK_OPPORTUNITIES: [List any topics that could link to other articles]
"""

        try:
            response = await self.llm_client.chat(
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert content writer who perfectly matches brand voice and style. You write engaging, useful content that readers love and that performs well in search.",
                    },
                    {"role": "user", "content": generation_prompt},
                ],
                temperature=0.7,
                max_tokens=3000,
            )

            # Parse the response
            article = self._parse_generated_article(response, topic, keywords or [])

            if products_to_feature:
                article.featured_products = products_to_feature

            # Run pharmaceutical fact-checking on the generated content
            try:
                pharma_checker = self._get_pharma_checker()
                pharma_analysis = await pharma_checker.analyze_content(article.content)

                article.needs_pharma_review = pharma_analysis.get("needs_pharma_review", False)
                article.pharma_review_reasons = pharma_analysis.get("review_reasons", [])
                article.pharma_fact_checks = pharma_analysis.get("fact_checks", [])
                article.suggested_citations = pharma_analysis.get("suggested_citations", [])

                if article.needs_pharma_review:
                    logger.info(
                        "Article flagged for pharma review",
                        title=article.title,
                        reasons=article.pharma_review_reasons,
                    )
            except Exception as e:
                logger.warning("Pharma check failed, continuing without", error=str(e))

            logger.info(
                "Article generated",
                title=article.title,
                word_count=article.word_count,
                needs_pharma_review=article.needs_pharma_review,
            )

            return article

        except Exception as e:
            logger.error("Article generation failed", error=str(e))
            return GeneratedArticle(
                title=f"Draft: {topic}",
                slug=self._slugify(topic),
                meta_description="",
                content=f"Generation failed: {str(e)}",
                word_count=0,
            )

    def _parse_generated_article(
        self,
        response: str,
        topic: str,
        keywords: list[str],
    ) -> GeneratedArticle:
        """Parse the LLM response into a structured article."""
        # Extract title
        title_match = re.search(r'TITLE:\s*(.+?)(?=\n|META)', response, re.IGNORECASE)
        title = title_match.group(1).strip() if title_match else topic

        # Extract meta description
        meta_match = re.search(r'META_DESCRIPTION:\s*(.+?)(?=\n|CONTENT)', response, re.IGNORECASE | re.DOTALL)
        meta_description = meta_match.group(1).strip()[:160] if meta_match else ""

        # Extract content
        content_match = re.search(r'CONTENT:\s*(.+?)(?=SUGGESTED_SLUG|INTERNAL_LINK|$)', response, re.IGNORECASE | re.DOTALL)
        content = content_match.group(1).strip() if content_match else response

        # Extract slug
        slug_match = re.search(r'SUGGESTED_SLUG:\s*(.+?)(?=\n|$)', response, re.IGNORECASE)
        slug = slug_match.group(1).strip() if slug_match else self._slugify(title)

        # Extract internal link opportunities
        links_match = re.search(r'INTERNAL_LINK_OPPORTUNITIES:\s*(.+?)(?=$)', response, re.IGNORECASE | re.DOTALL)
        internal_links = []
        if links_match:
            link_text = links_match.group(1)
            link_items = re.findall(r'[-•*]\s*(.+)', link_text)
            internal_links = [{"topic": item.strip()} for item in link_items]

        return GeneratedArticle(
            title=title,
            slug=slug,
            meta_description=meta_description,
            content=content,
            word_count=len(content.split()),
            target_keywords=keywords,
            internal_links=internal_links,
        )

    def _slugify(self, text: str) -> str:
        """Convert text to URL-friendly slug."""
        # Convert to lowercase
        slug = text.lower()
        # Replace spaces and special chars with hyphens
        slug = re.sub(r'[^a-z0-9åäö]+', '-', slug)
        # Remove leading/trailing hyphens
        slug = slug.strip('-')
        # Collapse multiple hyphens
        slug = re.sub(r'-+', '-', slug)
        return slug

    async def improve_draft(
        self,
        draft_content: str,
        feedback: str | None = None,
        reference_urls: list[str] | None = None,
    ) -> GeneratedArticle:
        """
        Improve an existing draft to better match the brand style.

        Useful when marketing has a rough draft that needs polish.
        """
        logger.info("Improving draft content")

        # Analyze style if needed
        if not self._style_guide and reference_urls:
            await self.analyze_style(article_urls=reference_urls)

        improvement_prompt = f"""Improve this draft article to better match our brand voice and style.

CURRENT DRAFT:
{draft_content}

{f"FEEDBACK TO ADDRESS: {feedback}" if feedback else ""}

{f"STYLE GUIDE: {self._raw_style_analysis}" if hasattr(self, '_raw_style_analysis') else ""}

IMPROVEMENTS TO MAKE:
1. Adjust tone and voice to match our brand
2. Improve flow and readability
3. Strengthen the intro and conclusion
4. Add better subheadings if needed
5. Make it more engaging and useful
6. Fix any factual or grammatical issues

Return the improved article in the same format as the original, with a brief summary of changes made."""

        try:
            response = await self.llm_client.chat(
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert editor who improves content while maintaining brand voice.",
                    },
                    {"role": "user", "content": improvement_prompt},
                ],
                temperature=0.5,
                max_tokens=3000,
            )

            return self._parse_generated_article(response, "Improved Draft", [])

        except Exception as e:
            logger.error("Draft improvement failed", error=str(e))
            return GeneratedArticle(
                title="Improvement Failed",
                slug="",
                meta_description="",
                content=draft_content,
                word_count=len(draft_content.split()),
            )

    async def run(
        self,
        task: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Run the content writer agent.

        Context can include:
        - topic: Main topic to write about
        - keywords: Target keywords
        - products: Products to feature
        - reference_urls: URLs to analyze for style
        - article_type: blog, product-news, guide, listicle
        - word_count: Target word count
        """
        logger.info("Running content writer", task=task)
        context = context or {}

        if "analyze" in task.lower() or "style" in task.lower():
            urls = context.get("reference_urls", [])
            style_guide = await self.analyze_style(article_urls=urls)
            return {
                "type": "style_analysis",
                "style_guide": {
                    "tone": style_guide.tone,
                    "voice": style_guide.voice,
                    "sentence_style": style_guide.sentence_style,
                    "vocabulary_level": style_guide.vocabulary_level,
                    "common_phrases": style_guide.common_phrases,
                },
            }

        elif "write" in task.lower() or "generate" in task.lower():
            topic = context.get("topic", task)
            article = await self.generate_article(
                topic=topic,
                keywords=context.get("keywords"),
                products_to_feature=context.get("products"),
                article_type=context.get("article_type", "blog"),
                word_count_target=context.get("word_count", 800),
                reference_urls=context.get("reference_urls"),
            )
            return {
                "type": "generated_article",
                "article": {
                    "title": article.title,
                    "slug": article.slug,
                    "meta_description": article.meta_description,
                    "content": article.content,
                    "word_count": article.word_count,
                    "target_keywords": article.target_keywords,
                },
            }

        elif "improve" in task.lower():
            draft = context.get("draft", "")
            improved = await self.improve_draft(
                draft_content=draft,
                feedback=context.get("feedback"),
                reference_urls=context.get("reference_urls"),
            )
            return {
                "type": "improved_article",
                "article": {
                    "title": improved.title,
                    "content": improved.content,
                    "word_count": improved.word_count,
                },
            }

        else:
            return {
                "type": "help",
                "available_tasks": [
                    "analyze style - Extract style guide from reference articles",
                    "write/generate - Create a new article",
                    "improve - Polish an existing draft",
                ],
            }
