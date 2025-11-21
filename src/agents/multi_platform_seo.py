"""
Multi-Platform SEO Agent - Optimizes for YouTube, Voice Search, and Visual Search.
"""

import re
from typing import Any
from urllib.parse import urlparse, quote_plus

import httpx
import structlog
from bs4 import BeautifulSoup

from src.agents.base import BaseAgent, AgentContext
from src.core.errors import AgentError, ErrorCode
from src.models.agents import (
    AgentTask, AgentResult, AgentType, Recommendation, Alert, Priority, Severity
)

logger = structlog.get_logger()


class MultiPlatformSEOAgent(BaseAgent):
    """
    Optimizes content for emerging search platforms beyond traditional Google.

    Capabilities:
    - YouTube SEO analysis and optimization
    - Voice search readiness assessment
    - Visual search optimization (images, Google Lens)
    - Video schema generation
    - Speakable content markup
    """

    agent_type = AgentType.MULTI_PLATFORM_SEO

    def __init__(self, context: AgentContext):
        self.context = context
        self.logger = logger.bind(agent="multi-platform-seo")

    async def execute(self, task: AgentTask) -> AgentResult:
        """Execute multi-platform SEO task."""
        task_handlers = {
            "youtube_audit": self._youtube_audit,
            "voice_search_readiness": self._voice_search_readiness,
            "visual_search_optimization": self._visual_search_optimization,
            "generate_video_schema": self._generate_video_schema,
            "generate_speakable_schema": self._generate_speakable_schema,
            "platform_opportunity_analysis": self._platform_opportunity_analysis,
        }

        handler = task_handlers.get(task.task_type)
        if not handler:
            raise AgentError(
                f"Unknown task type: {task.task_type}",
                agent_type="multi-platform-seo",
                task_type=task.task_type,
                code=ErrorCode.VALIDATION_ERROR,
            )

        result = await handler(task.parameters)

        return AgentResult(
            task_id=task.id,
            agent_type=self.agent_type,
            success=True,
            data=result["data"],
            recommendations=result.get("recommendations", []),
            alerts=result.get("alerts", []),
        )

    async def _youtube_audit(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Audit YouTube video or channel for SEO optimization.

        Note: Full YouTube API integration would require YouTube Data API.
        This provides guidance based on best practices.
        """
        video_url = params.get("video_url")
        channel_url = params.get("channel_url")
        keywords = params.get("keywords", [])

        recommendations = []
        checklist = []

        # YouTube SEO best practices checklist
        video_checklist = [
            {
                "item": "Title includes target keyword",
                "priority": "critical",
                "tip": "Place keyword in first 60 characters",
            },
            {
                "item": "Description is 200+ words",
                "priority": "high",
                "tip": "Include keywords naturally, add timestamps, and links",
            },
            {
                "item": "Tags include keyword variations",
                "priority": "high",
                "tip": "Use 5-8 relevant tags including long-tail variations",
            },
            {
                "item": "Custom thumbnail uploaded",
                "priority": "high",
                "tip": "Use high-contrast, face-forward thumbnails with text",
            },
            {
                "item": "Closed captions/subtitles added",
                "priority": "high",
                "tip": "Upload SRT files or edit auto-generated captions",
            },
            {
                "item": "Cards and end screens added",
                "priority": "medium",
                "tip": "Link to related videos and playlists",
            },
            {
                "item": "Video chapters (timestamps) added",
                "priority": "medium",
                "tip": "Add timestamps in description starting with 0:00",
            },
            {
                "item": "Pinned comment with CTA",
                "priority": "low",
                "tip": "Pin a comment with links or questions to boost engagement",
            },
        ]

        channel_checklist = [
            {
                "item": "Channel keywords set",
                "priority": "critical",
                "tip": "Add channel keywords in YouTube Studio > Settings",
            },
            {
                "item": "Channel description optimized",
                "priority": "high",
                "tip": "Include keywords in first 150 characters",
            },
            {
                "item": "Custom URL claimed",
                "priority": "medium",
                "tip": "Use your brand name in channel URL",
            },
            {
                "item": "Channel trailer uploaded",
                "priority": "medium",
                "tip": "Create a compelling 1-2 minute trailer",
            },
            {
                "item": "Playlists organized by topic",
                "priority": "high",
                "tip": "Group videos into keyword-rich playlist titles",
            },
            {
                "item": "About section complete",
                "priority": "medium",
                "tip": "Include contact info, social links, and posting schedule",
            },
        ]

        # If video URL provided, try to extract basic info
        video_data = {}
        if video_url and "youtube.com" in video_url or "youtu.be" in video_url:
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    response = await client.get(video_url)
                    soup = BeautifulSoup(response.text, "lxml")

                    # Extract available metadata
                    title_tag = soup.find("meta", {"name": "title"})
                    desc_tag = soup.find("meta", {"name": "description"})

                    video_data = {
                        "title": title_tag.get("content", "") if title_tag else "",
                        "description_preview": desc_tag.get("content", "")[:200] if desc_tag else "",
                        "url": video_url,
                    }

                    # Basic keyword check in title
                    if keywords:
                        title_lower = video_data["title"].lower()
                        keywords_in_title = [kw for kw in keywords if kw.lower() in title_lower]
                        video_data["keywords_in_title"] = keywords_in_title

                        if not keywords_in_title:
                            recommendations.append(Recommendation(
                                title="Target keyword missing from video title",
                                description=f"Add '{keywords[0]}' to the video title for better rankings",
                                priority=Priority.HIGH,
                                category="youtube_seo",
                            ))

            except Exception as e:
                self.logger.warning("YouTube video fetch failed", error=str(e))

        # Generate recommendations
        recommendations.append(Recommendation(
            title="Complete YouTube SEO checklist",
            description="Review the checklist items to maximize video visibility",
            priority=Priority.MEDIUM,
            category="youtube_seo",
        ))

        return {
            "data": {
                "video_url": video_url,
                "channel_url": channel_url,
                "video_data": video_data,
                "video_checklist": video_checklist,
                "channel_checklist": channel_checklist,
                "keywords_analyzed": keywords,
            },
            "recommendations": recommendations,
        }

    async def _voice_search_readiness(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Assess voice search optimization readiness.

        Voice search queries are typically:
        - Question-based (who, what, where, when, why, how)
        - Conversational/natural language
        - Local intent heavy
        - Seeking quick, direct answers
        """
        url = params.get("url", self.context.property_url)

        if not url:
            return {"data": {"error": "URL required"}, "recommendations": []}

        recommendations = []
        readiness_score = 0
        max_score = 100
        signals = []

        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(url)
                soup = BeautifulSoup(response.text, "lxml")

            text = soup.get_text()

            # 1. Featured snippet optimization (question-answer format)
            question_patterns = [
                r"what is", r"how to", r"why do", r"when should",
                r"where can", r"who is", r"which is",
            ]
            questions_found = sum(1 for p in question_patterns if re.search(p, text.lower()))

            if questions_found >= 3:
                readiness_score += 20
                signals.append({"signal": "Question-based content", "score": 20, "present": True})
            elif questions_found >= 1:
                readiness_score += 10
                signals.append({"signal": "Some question content", "score": 10, "present": True})
            else:
                signals.append({"signal": "Question-based content", "score": 0, "present": False})
                recommendations.append(Recommendation(
                    title="Add question-based content sections",
                    description="Include 'What is...', 'How to...' sections for voice search",
                    priority=Priority.HIGH,
                    category="voice_search",
                ))

            # 2. Concise answers (40-50 words ideal for voice)
            paragraphs = soup.find_all("p")
            concise_paragraphs = [p for p in paragraphs if 30 <= len(p.get_text().split()) <= 60]

            if len(concise_paragraphs) >= 3:
                readiness_score += 15
                signals.append({"signal": "Concise answer paragraphs", "score": 15, "present": True})
            else:
                signals.append({"signal": "Concise answer paragraphs", "score": 0, "present": False})
                recommendations.append(Recommendation(
                    title="Add concise answer paragraphs",
                    description="Voice assistants prefer 40-50 word direct answers",
                    priority=Priority.MEDIUM,
                    category="voice_search",
                ))

            # 3. FAQ schema
            faq_schema = soup.find("script", type="application/ld+json", string=re.compile(r'"@type"\s*:\s*"FAQPage"'))
            if faq_schema:
                readiness_score += 20
                signals.append({"signal": "FAQ schema present", "score": 20, "present": True})
            else:
                signals.append({"signal": "FAQ schema present", "score": 0, "present": False})
                recommendations.append(Recommendation(
                    title="Add FAQ schema markup",
                    description="FAQPage schema increases voice search visibility",
                    priority=Priority.HIGH,
                    category="voice_search",
                ))

            # 4. Speakable schema
            speakable_schema = soup.find("script", type="application/ld+json", string=re.compile(r'"speakable"'))
            if speakable_schema:
                readiness_score += 15
                signals.append({"signal": "Speakable schema present", "score": 15, "present": True})
            else:
                signals.append({"signal": "Speakable schema present", "score": 0, "present": False})
                recommendations.append(Recommendation(
                    title="Add Speakable schema markup",
                    description="Mark content sections suitable for text-to-speech",
                    priority=Priority.MEDIUM,
                    category="voice_search",
                ))

            # 5. Natural language / conversational tone
            conversational_patterns = [
                r"you (can|should|might|will)",
                r"let's",
                r"here's",
                r"we'll",
            ]
            conversational_found = sum(1 for p in conversational_patterns if re.search(p, text.lower()))

            if conversational_found >= 3:
                readiness_score += 10
                signals.append({"signal": "Conversational tone", "score": 10, "present": True})
            else:
                signals.append({"signal": "Conversational tone", "score": 0, "present": False})

            # 6. Page speed (critical for voice)
            # Would need Core Web Vitals API - simplified check
            readiness_score += 10  # Assume baseline
            signals.append({"signal": "Page speed (assumed baseline)", "score": 10, "present": True})

            # 7. Mobile-friendly (voice is mostly mobile)
            viewport_meta = soup.find("meta", {"name": "viewport"})
            if viewport_meta:
                readiness_score += 10
                signals.append({"signal": "Mobile viewport set", "score": 10, "present": True})
            else:
                signals.append({"signal": "Mobile viewport set", "score": 0, "present": False})

            # Calculate percentage
            percentage = (readiness_score / max_score) * 100

            return {
                "data": {
                    "url": url,
                    "readiness_score": readiness_score,
                    "max_score": max_score,
                    "percentage": round(percentage, 1),
                    "grade": self._score_to_grade(percentage),
                    "signals": signals,
                    "voice_search_tips": [
                        "Target question keywords (who, what, where, when, why, how)",
                        "Provide direct, concise answers (40-50 words)",
                        "Use natural, conversational language",
                        "Optimize for local searches if applicable",
                        "Ensure fast page load speed",
                        "Implement FAQ and Speakable schema",
                    ],
                },
                "recommendations": recommendations,
            }

        except Exception as e:
            self.logger.error("Voice search analysis failed", error=str(e))
            return {"data": {"error": str(e)}, "recommendations": []}

    def _score_to_grade(self, percentage: float) -> str:
        """Convert percentage to letter grade."""
        if percentage >= 90:
            return "A"
        elif percentage >= 80:
            return "B"
        elif percentage >= 70:
            return "C"
        elif percentage >= 60:
            return "D"
        else:
            return "F"

    async def _visual_search_optimization(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Optimize for visual search (Google Lens, Pinterest, etc.).

        Visual search is growing rapidly for:
        - Product discovery
        - Local business lookup
        - Plant/animal identification
        - Fashion/style matching
        """
        url = params.get("url", self.context.property_url)

        if not url:
            return {"data": {"error": "URL required"}, "recommendations": []}

        recommendations = []
        image_analysis = []
        score = 0
        max_score = 100

        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(url)
                soup = BeautifulSoup(response.text, "lxml")

            images = soup.find_all("img")

            # Analyze each image
            for img in images[:20]:  # Limit to 20 images
                src = img.get("src", "")
                alt = img.get("alt", "")
                title = img.get("title", "")
                width = img.get("width", "")
                height = img.get("height", "")
                loading = img.get("loading", "")

                analysis = {
                    "src": src[:100],
                    "issues": [],
                    "optimizations": [],
                }

                # Check alt text
                if not alt:
                    analysis["issues"].append("Missing alt text")
                elif len(alt) < 10:
                    analysis["issues"].append("Alt text too short")
                else:
                    analysis["optimizations"].append("Has descriptive alt text")

                # Check file name (would need full URL)
                if src and not any(c.isalpha() for c in src.split("/")[-1].split(".")[0]):
                    analysis["issues"].append("Non-descriptive filename (use keywords)")

                # Check dimensions
                if width and height:
                    analysis["optimizations"].append("Dimensions specified")
                else:
                    analysis["issues"].append("Missing width/height attributes")

                # Check lazy loading
                if loading == "lazy":
                    analysis["optimizations"].append("Lazy loading enabled")

                image_analysis.append(analysis)

            # Calculate image optimization score
            images_with_alt = sum(1 for img in images if img.get("alt"))
            if images:
                alt_percentage = (images_with_alt / len(images)) * 100
                if alt_percentage >= 90:
                    score += 30
                elif alt_percentage >= 70:
                    score += 20
                elif alt_percentage >= 50:
                    score += 10

            # Check for image schema
            image_schema = soup.find("script", type="application/ld+json", string=re.compile(r'"@type"\s*:\s*"ImageObject"'))
            product_schema = soup.find("script", type="application/ld+json", string=re.compile(r'"@type"\s*:\s*"Product"'))

            if image_schema or product_schema:
                score += 20
            else:
                recommendations.append(Recommendation(
                    title="Add ImageObject or Product schema",
                    description="Schema markup helps visual search understand your images",
                    priority=Priority.MEDIUM,
                    category="visual_search",
                ))

            # Check for high-quality images
            # This would need actual image analysis - simplified check
            score += 20  # Baseline

            # Check for image sitemap reference
            # Would need robots.txt check
            score += 10  # Baseline

            # OpenGraph images
            og_image = soup.find("meta", {"property": "og:image"})
            if og_image:
                score += 10
            else:
                recommendations.append(Recommendation(
                    title="Add Open Graph image",
                    description="og:image helps with social and visual search sharing",
                    priority=Priority.LOW,
                    category="visual_search",
                ))

            # Generate recommendations based on analysis
            images_without_alt = sum(1 for a in image_analysis if "Missing alt text" in a["issues"])
            if images_without_alt > 0:
                recommendations.append(Recommendation(
                    title=f"{images_without_alt} images missing alt text",
                    description="Add descriptive, keyword-rich alt text to all images",
                    priority=Priority.HIGH,
                    category="visual_search",
                ))

            percentage = (score / max_score) * 100

            return {
                "data": {
                    "url": url,
                    "total_images": len(images),
                    "images_with_alt": images_with_alt,
                    "optimization_score": score,
                    "max_score": max_score,
                    "percentage": round(percentage, 1),
                    "image_analysis": image_analysis[:10],  # First 10
                    "visual_search_tips": [
                        "Use high-quality, clear images",
                        "Add descriptive, keyword-rich alt text",
                        "Use descriptive file names (product-name.jpg not IMG_1234.jpg)",
                        "Implement Product or ImageObject schema",
                        "Create an image sitemap",
                        "Optimize image file size for fast loading",
                        "Use structured data for products",
                    ],
                },
                "recommendations": recommendations,
            }

        except Exception as e:
            self.logger.error("Visual search analysis failed", error=str(e))
            return {"data": {"error": str(e)}, "recommendations": []}

    async def _generate_video_schema(self, params: dict[str, Any]) -> dict[str, Any]:
        """Generate VideoObject schema markup."""
        import json

        schema = {
            "@context": "https://schema.org",
            "@type": "VideoObject",
            "name": params.get("name", ""),
            "description": params.get("description", ""),
            "thumbnailUrl": params.get("thumbnail_url", ""),
            "uploadDate": params.get("upload_date", ""),
            "duration": params.get("duration", ""),  # ISO 8601 format: PT1H30M
            "contentUrl": params.get("content_url", ""),
            "embedUrl": params.get("embed_url", ""),
        }

        # Add optional fields
        if params.get("transcript"):
            schema["transcript"] = params["transcript"]

        if params.get("publication_date"):
            schema["datePublished"] = params["publication_date"]

        if params.get("interactionCount"):
            schema["interactionStatistic"] = {
                "@type": "InteractionCounter",
                "interactionType": {"@type": "WatchAction"},
                "userInteractionCount": params["interactionCount"],
            }

        # Add clip markup for key moments
        if params.get("clips"):
            schema["hasPart"] = [
                {
                    "@type": "Clip",
                    "name": clip.get("name", ""),
                    "startOffset": clip.get("start_offset", 0),
                    "endOffset": clip.get("end_offset", 0),
                    "url": f"{params.get('content_url', '')}?t={clip.get('start_offset', 0)}",
                }
                for clip in params["clips"]
            ]

        # Clean empty values
        schema = {k: v for k, v in schema.items() if v}

        return {
            "data": {
                "schema": schema,
                "schema_json": json.dumps(schema, indent=2),
            },
            "recommendations": [
                Recommendation(
                    title="Add VideoObject schema to video pages",
                    description="This enables rich video results in Google Search",
                    priority=Priority.HIGH,
                    category="video_seo",
                ),
            ],
        }

    async def _generate_speakable_schema(self, params: dict[str, Any]) -> dict[str, Any]:
        """Generate Speakable schema for voice search."""
        import json

        url = params.get("url", "")
        speakable_sections = params.get("sections", [])

        # If no sections provided, use CSS selectors for common speakable elements
        if not speakable_sections:
            speakable_sections = [
                {"cssSelector": "article h1"},
                {"cssSelector": "article > p:first-of-type"},
                {"cssSelector": ".summary, .tldr, .key-takeaways"},
            ]

        schema = {
            "@context": "https://schema.org",
            "@type": "WebPage",
            "name": params.get("page_title", ""),
            "url": url,
            "speakable": {
                "@type": "SpeakableSpecification",
                "cssSelector": [s.get("cssSelector") for s in speakable_sections if s.get("cssSelector")],
            },
        }

        # Alternative: use xpath
        xpaths = [s.get("xpath") for s in speakable_sections if s.get("xpath")]
        if xpaths:
            schema["speakable"]["xpath"] = xpaths

        return {
            "data": {
                "schema": schema,
                "schema_json": json.dumps(schema, indent=2),
                "note": "Speakable markup helps Google Assistant read your content aloud",
            },
            "recommendations": [
                Recommendation(
                    title="Implement Speakable schema",
                    description="Mark sections that are suitable for text-to-speech (TTS)",
                    priority=Priority.MEDIUM,
                    category="voice_search",
                ),
            ],
        }

    async def _platform_opportunity_analysis(self, params: dict[str, Any]) -> dict[str, Any]:
        """Analyze opportunities across different search platforms."""
        keywords = params.get("keywords", [])
        industry = params.get("industry", "")

        # Platform opportunity matrix
        opportunities = {
            "youtube": {
                "potential": "high",
                "audience": "2B+ monthly users",
                "best_for": ["tutorials", "reviews", "entertainment", "how-to"],
                "key_actions": [
                    "Create video versions of top blog content",
                    "Optimize titles with target keywords",
                    "Add chapters and timestamps",
                    "Create playlists around topics",
                ],
            },
            "voice_search": {
                "potential": "growing",
                "audience": "40%+ of adults use daily",
                "best_for": ["local queries", "quick answers", "FAQs", "definitions"],
                "key_actions": [
                    "Optimize for question keywords",
                    "Create FAQ pages with schema",
                    "Target featured snippets",
                    "Improve page speed",
                ],
            },
            "visual_search": {
                "potential": "high for e-commerce",
                "audience": "Growing rapidly, esp. Gen Z",
                "best_for": ["products", "fashion", "home decor", "food", "travel"],
                "key_actions": [
                    "Optimize all image alt text",
                    "Use high-quality product images",
                    "Implement Product schema",
                    "Create image sitemaps",
                ],
            },
            "tiktok_search": {
                "potential": "emerging",
                "audience": "40% of Gen Z prefer TikTok over Google",
                "best_for": ["lifestyle", "fashion", "food", "entertainment", "tutorials"],
                "key_actions": [
                    "Create short-form video content",
                    "Use trending sounds and hashtags",
                    "Add keywords to captions",
                    "Post consistently",
                ],
            },
            "pinterest": {
                "potential": "high for visual industries",
                "audience": "450M+ monthly users",
                "best_for": ["DIY", "recipes", "fashion", "home decor", "weddings"],
                "key_actions": [
                    "Create pinnable images",
                    "Optimize pin descriptions",
                    "Use Rich Pins",
                    "Create boards around topics",
                ],
            },
            "amazon_search": {
                "potential": "critical for e-commerce",
                "audience": "Product searches often start on Amazon",
                "best_for": ["physical products", "books", "electronics"],
                "key_actions": [
                    "Optimize product titles",
                    "Use backend keywords",
                    "Get reviews",
                    "A+ content",
                ],
            },
        }

        # Score relevance based on industry
        industry_platform_fit = {
            "e-commerce": ["visual_search", "pinterest", "amazon_search", "youtube"],
            "retail": ["visual_search", "pinterest", "amazon_search", "youtube"],
            "fashion": ["visual_search", "pinterest", "tiktok_search", "youtube"],
            "food": ["youtube", "pinterest", "tiktok_search", "visual_search"],
            "travel": ["youtube", "visual_search", "pinterest", "voice_search"],
            "tech": ["youtube", "voice_search", "tiktok_search"],
            "healthcare": ["youtube", "voice_search"],
            "finance": ["youtube", "voice_search"],
            "education": ["youtube", "voice_search", "tiktok_search"],
            "local": ["voice_search", "visual_search"],
        }

        recommended_platforms = industry_platform_fit.get(
            industry.lower(),
            ["youtube", "voice_search", "visual_search"]  # Default
        )

        recommendations = []

        for platform in recommended_platforms[:3]:
            if platform in opportunities:
                opp = opportunities[platform]
                recommendations.append(Recommendation(
                    title=f"Prioritize {platform.replace('_', ' ').title()} optimization",
                    description=f"Potential: {opp['potential']}. Best for: {', '.join(opp['best_for'][:3])}",
                    priority=Priority.HIGH if opp["potential"] == "high" else Priority.MEDIUM,
                    category="multi_platform",
                    data={"key_actions": opp["key_actions"]},
                ))

        return {
            "data": {
                "industry": industry,
                "keywords": keywords,
                "platform_opportunities": opportunities,
                "recommended_platforms": recommended_platforms,
            },
            "recommendations": recommendations,
        }
