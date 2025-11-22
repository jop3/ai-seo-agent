"""
AI Visibility Control Agent - Manage AI engine access and indexing.

Controls which content AI engines can access, cite, and display.
Manages robots.txt, meta tags, and AI-specific directives.
"""

from datetime import datetime
from typing import Any

import structlog

from src.agents.base import BaseAgent, AgentContext
from src.models.agents import AgentTask, AgentResult, Recommendation, Alert, Priority, Severity

logger = structlog.get_logger()


class AIVisibilityControlAgent(BaseAgent):
    """
    Manages AI engine access and visibility controls.

    Controls:
    - Robots.txt directives for AI crawlers
    - Meta tags (nosnippet, noindex, max-snippet)
    - Googlebot-specific controls
    - Core Web Vitals for AI access
    - Content licensing and attribution

    Use cases:
    - Block AI from proprietary content
    - Allow AI for marketing content
    - Control snippet length
    - Manage paywalled content visibility
    """

    # Known AI crawler user agents
    AI_CRAWLERS = {
        "GPTBot": {
            "name": "OpenAI GPTBot",
            "purpose": "ChatGPT training and responses",
            "user_agent": "GPTBot",
            "robots_directive": "User-agent: GPTBot",
        },
        "ChatGPT-User": {
            "name": "ChatGPT Browse",
            "purpose": "Real-time browsing for ChatGPT",
            "user_agent": "ChatGPT-User",
            "robots_directive": "User-agent: ChatGPT-User",
        },
        "Claude-Web": {
            "name": "Anthropic Claude",
            "purpose": "Claude AI responses",
            "user_agent": "Claude-Web",
            "robots_directive": "User-agent: Claude-Web",
        },
        "Google-Extended": {
            "name": "Google Bard/Gemini",
            "purpose": "Gemini AI training (separate from Search)",
            "user_agent": "Google-Extended",
            "robots_directive": "User-agent: Google-Extended",
        },
        "CCBot": {
            "name": "Common Crawl",
            "purpose": "Training data for various AI models",
            "user_agent": "CCBot",
            "robots_directive": "User-agent: CCBot",
        },
        "PerplexityBot": {
            "name": "Perplexity AI",
            "purpose": "Perplexity search responses",
            "user_agent": "PerplexityBot",
            "robots_directive": "User-agent: PerplexityBot",
        },
        "anthropic-ai": {
            "name": "Anthropic AI",
            "purpose": "Claude training and research",
            "user_agent": "anthropic-ai",
            "robots_directive": "User-agent: anthropic-ai",
        },
    }

    # Meta tag controls
    META_CONTROLS = [
        "robots",
        "googlebot",
        "max-snippet",
        "max-image-preview",
        "max-video-preview",
        "nosnippet",
        "noimageindex",
        "notranslate",
    ]

    def __init__(self, context: AgentContext):
        super().__init__(
            agent_type="ai-visibility-control",
            description="Manages AI engine access, indexing, and content visibility controls",
            context=context,
        )

    async def run(self, task: AgentTask) -> AgentResult:
        """Execute AI visibility control task."""
        start_time = datetime.utcnow()

        try:
            if task.task_type == "audit_ai_access":
                result = await self._audit_ai_access(task.parameters)
            elif task.task_type == "audit_robots_txt":
                result = await self._audit_robots_txt(task.parameters)
            elif task.task_type == "audit_meta_controls":
                result = await self._audit_meta_controls(task.parameters)
            elif task.task_type == "recommend_visibility_strategy":
                result = await self._recommend_visibility_strategy(task.parameters)
            elif task.task_type == "core_web_vitals_ai":
                result = await self._audit_core_web_vitals_for_ai(task.parameters)
            elif task.task_type == "full_visibility_audit":
                result = await self._full_visibility_audit(task.parameters)
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
            logger.error("AI visibility control analysis failed", error=str(e))
            return AgentResult(
                task_id=task.id,
                agent_type=self.agent_type,
                success=False,
                data={"error": str(e)},
            )

    async def _full_visibility_audit(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Complete AI visibility audit.

        Checks all aspects of AI access control.
        """
        domain = params.get("domain", self.context.property_url)

        results = {
            "analyzed_at": datetime.utcnow().isoformat(),
            "domain": domain,
            "overall_control_score": 0,
            "robots_txt_analysis": {},
            "meta_tag_analysis": {},
            "ai_crawler_access": {},
            "core_web_vitals": {},
            "visibility_strategy": "",
        }

        recommendations = []
        alerts = []

        # Audit robots.txt
        robots_result = await self._audit_robots_txt({"domain": domain})
        results["robots_txt_analysis"] = robots_result["data"]

        # Audit meta controls
        meta_result = await self._audit_meta_controls({"domain": domain})
        results["meta_tag_analysis"] = meta_result["data"]

        # Check Core Web Vitals
        cwv_result = await self._audit_core_web_vitals_for_ai({"domain": domain})
        results["core_web_vitals"] = cwv_result["data"]

        # Aggregate recommendations
        recommendations.extend(robots_result.get("recommendations", []))
        recommendations.extend(meta_result.get("recommendations", []))
        recommendations.extend(cwv_result.get("recommendations", []))

        # Calculate control score
        robots_score = robots_result["data"]["configuration_score"]
        meta_score = meta_result["data"]["optimization_score"]
        cwv_score = cwv_result["data"]["ai_access_score"]

        results["overall_control_score"] = (robots_score + meta_score + cwv_score) / 3

        # Recommend visibility strategy
        strategy_result = await self._recommend_visibility_strategy({
            "domain": domain,
            "current_strategy": params.get("current_strategy", "default"),
        })
        results["visibility_strategy"] = strategy_result["data"]["recommended_strategy"]
        recommendations.extend(strategy_result.get("recommendations", []))

        return {
            "data": results,
            "recommendations": recommendations,
            "alerts": alerts,
        }

    async def _audit_robots_txt(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Audit robots.txt for AI crawler directives.

        Checks:
        - Presence of robots.txt
        - AI crawler-specific rules
        - Conflicting directives
        - Best practices
        """
        domain = params.get("domain")

        # In production, fetch actual robots.txt
        # For now, simulate analysis
        robots_analysis = {
            "has_robots_txt": True,
            "url": f"{domain}/robots.txt",
            "configuration_score": 65.0,
            "ai_crawler_rules": {
                "GPTBot": "not_specified",
                "ChatGPT-User": "not_specified",
                "Claude-Web": "not_specified",
                "Google-Extended": "disallow",
                "CCBot": "not_specified",
                "PerplexityBot": "not_specified",
            },
            "default_behavior": "allow",  # If not specified, most crawlers are allowed
            "detected_directives": [
                "User-agent: *",
                "Disallow: /admin/",
                "Disallow: /checkout/",
                "User-agent: Google-Extended",
                "Disallow: /",
            ],
            "issues": [
                "No directives for GPTBot (ChatGPT training)",
                "No directives for PerplexityBot",
                "No directives for Claude-Web",
                "Consider allowing Google-Extended for Google AI Overviews",
            ],
        }

        recommendations = []

        # Check for missing AI crawler rules
        unspecified_count = sum(
            1 for status in robots_analysis["ai_crawler_rules"].values()
            if status == "not_specified"
        )

        if unspecified_count > 0:
            recommendations.append(Recommendation(
                title=f"Add AI Crawler Directives to robots.txt",
                description=f"{unspecified_count} AI crawlers lack explicit rules. Add directives to control access to your content.",
                category="AI Visibility - Access Control",
                priority=Priority.HIGH,
                estimated_impact="Explicit control over AI training data usage",
                implementation_effort="low",
                auto_implementable=True,
            ))

        # Google-Extended specific
        if robots_analysis["ai_crawler_rules"]["Google-Extended"] == "disallow":
            recommendations.append(Recommendation(
                title="Review Google-Extended Block",
                description="You're blocking Google-Extended, which prevents Gemini AI (but not Google Search) from using your content. This may reduce visibility in Google AI Overviews.",
                category="AI Visibility - Google AI",
                priority=Priority.MEDIUM,
                estimated_impact="May affect Google AI Overview citations",
                implementation_effort="low",
            ))

        return {
            "data": robots_analysis,
            "recommendations": recommendations,
        }

    async def _audit_meta_controls(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Audit meta tag controls for AI visibility.

        Checks:
        - robots meta tags
        - max-snippet length
        - max-image-preview
        - Page-level overrides
        """
        domain = params.get("domain")
        urls = params.get("urls", [f"{domain}/"])

        # In production, fetch and parse meta tags from actual pages
        meta_analysis = {
            "pages_analyzed": len(urls),
            "optimization_score": 58.0,
            "meta_tag_usage": {
                "robots": 45,  # % of pages
                "max-snippet": 12,
                "max-image-preview": 8,
                "nosnippet": 5,
                "googlebot": 23,
            },
            "snippet_control": {
                "avg_max_snippet": 160,  # characters
                "pages_with_control": 12,
                "pages_without_control": 88,
            },
            "image_preview_control": {
                "unrestricted": 8,
                "standard": 2,
                "large": 0,
                "none": 90,
            },
            "issues": [
                "88% of pages lack snippet length control",
                "90% of pages don't specify image preview preference",
                "No strategic use of max-snippet for different page types",
            ],
        }

        recommendations = [
            Recommendation(
                title="Add max-snippet Control to Key Pages",
                description="Control how much content AI engines can display in snippets. Recommended: 200-300 chars for marketing, 100 for proprietary content.",
                category="AI Visibility - Content Control",
                priority=Priority.MEDIUM,
                estimated_impact="Control content exposure in AI responses",
                implementation_effort="low",
                auto_implementable=True,
            ),
            Recommendation(
                title="Set max-image-preview for Product Pages",
                description="Allow 'large' image previews for product pages to improve visual search, 'standard' for other content.",
                category="AI Visibility - Image Control",
                priority=Priority.LOW,
                estimated_impact="Better control of image usage in AI responses",
                implementation_effort="low",
            ),
        ]

        return {
            "data": meta_analysis,
            "recommendations": recommendations,
        }

    async def _recommend_visibility_strategy(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Recommend AI visibility strategy based on business type and goals.

        Strategies:
        - Full Visibility: Allow all AI engines (e-commerce, content sites)
        - Selective Visibility: Allow some, block others (publishers)
        - Restricted: Block AI training, allow citations (proprietary content)
        - Blocked: Block all AI access (sensitive/confidential)
        """
        business_type = params.get("business_type", "ecommerce")
        content_type = params.get("content_type", "product")

        # Determine recommended strategy
        if business_type == "ecommerce":
            strategy = "full_visibility"
            rationale = "E-commerce benefits from AI citations and shopping assistants"
        elif business_type == "publisher":
            strategy = "selective_visibility"
            rationale = "Publishers should allow citations but may restrict training data usage"
        elif business_type == "saas":
            strategy = "selective_visibility"
            rationale = "SaaS should allow marketing content, restrict documentation"
        elif business_type == "enterprise":
            strategy = "restricted"
            rationale = "Enterprise content often proprietary, allow limited citations only"
        else:
            strategy = "full_visibility"
            rationale = "Default strategy for maximum AI discovery"

        strategy_config = {
            "recommended_strategy": strategy,
            "rationale": rationale,
            "robots_txt_config": self._get_robots_config(strategy),
            "meta_tag_config": self._get_meta_config(strategy),
            "ai_crawler_rules": self._get_crawler_rules(strategy),
        }

        recommendations = [
            Recommendation(
                title=f"Implement {strategy.replace('_', ' ').title()} Strategy",
                description=f"{rationale}. Configure robots.txt and meta tags accordingly.",
                category="AI Visibility - Strategy",
                priority=Priority.HIGH,
                estimated_impact="Optimized AI engine access aligned with business goals",
                implementation_effort="medium",
                auto_implementable=True,
            ),
        ]

        return {
            "data": strategy_config,
            "recommendations": recommendations,
        }

    def _get_robots_config(self, strategy: str) -> dict[str, str]:
        """Get robots.txt configuration for strategy."""
        if strategy == "full_visibility":
            return {
                "GPTBot": "Allow",
                "ChatGPT-User": "Allow",
                "Claude-Web": "Allow",
                "Google-Extended": "Allow",
                "PerplexityBot": "Allow",
                "CCBot": "Allow",
            }
        elif strategy == "selective_visibility":
            return {
                "GPTBot": "Disallow",  # Block training
                "ChatGPT-User": "Allow",  # Allow citations
                "Claude-Web": "Allow",
                "Google-Extended": "Allow",  # Allow Google AI
                "PerplexityBot": "Allow",
                "CCBot": "Disallow",  # Block Common Crawl
            }
        elif strategy == "restricted":
            return {
                "GPTBot": "Disallow",
                "ChatGPT-User": "Allow: /blog/\nDisallow: /",
                "Claude-Web": "Allow: /blog/\nDisallow: /",
                "Google-Extended": "Allow",
                "PerplexityBot": "Allow: /blog/\nDisallow: /",
                "CCBot": "Disallow",
            }
        else:  # blocked
            return {
                "GPTBot": "Disallow",
                "ChatGPT-User": "Disallow",
                "Claude-Web": "Disallow",
                "Google-Extended": "Disallow",
                "PerplexityBot": "Disallow",
                "CCBot": "Disallow",
            }

    def _get_meta_config(self, strategy: str) -> dict[str, Any]:
        """Get meta tag configuration for strategy."""
        if strategy == "full_visibility":
            return {
                "robots": "index, follow",
                "max-snippet": -1,  # No limit
                "max-image-preview": "large",
                "max-video-preview": -1,
            }
        elif strategy == "selective_visibility":
            return {
                "robots": "index, follow",
                "max-snippet": 300,  # Limit snippet length
                "max-image-preview": "standard",
                "max-video-preview": 60,
            }
        elif strategy == "restricted":
            return {
                "robots": "index, follow",
                "max-snippet": 100,  # Short snippets only
                "max-image-preview": "none",
                "max-video-preview": 0,
            }
        else:  # blocked
            return {
                "robots": "noindex, nofollow",
                "max-snippet": 0,
                "max-image-preview": "none",
                "max-video-preview": 0,
            }

    def _get_crawler_rules(self, strategy: str) -> dict[str, Any]:
        """Get detailed crawler access rules."""
        configs = {
            "full_visibility": {
                "training_data": "Allow all crawlers",
                "citations": "Allow all crawlers",
                "snippets": "Unrestricted",
                "images": "Full preview allowed",
            },
            "selective_visibility": {
                "training_data": "Block GPTBot, CCBot",
                "citations": "Allow ChatGPT-User, Claude, Gemini, Perplexity",
                "snippets": "Limited to 300 characters",
                "images": "Standard preview",
            },
            "restricted": {
                "training_data": "Block all training crawlers",
                "citations": "Allow citations for public content only",
                "snippets": "Limited to 100 characters",
                "images": "No preview",
            },
            "blocked": {
                "training_data": "Block all",
                "citations": "Block all",
                "snippets": "None",
                "images": "None",
            },
        }
        return configs.get(strategy, configs["full_visibility"])

    async def _audit_core_web_vitals_for_ai(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Audit Core Web Vitals specifically for AI crawler access.

        AI crawlers may be affected by:
        - LCP (Largest Contentful Paint) - affects content discovery
        - CLS (Cumulative Layout Shift) - affects content extraction
        - INP (Interaction to Next Paint) - affects crawl efficiency
        """
        domain = params.get("domain")

        # In production, fetch actual CWV data from CrUX or Lighthouse
        cwv_analysis = {
            "domain": domain,
            "ai_access_score": 72.0,
            "core_web_vitals": {
                "lcp": {
                    "value": 2.3,  # seconds
                    "status": "good",  # < 2.5s
                    "ai_impact": "Good - AI can quickly access main content",
                },
                "cls": {
                    "value": 0.08,
                    "status": "good",  # < 0.1
                    "ai_impact": "Good - Stable layout aids content extraction",
                },
                "inp": {
                    "value": 180,  # ms
                    "status": "good",  # < 200ms
                    "ai_impact": "Good - Responsive for AI interactions",
                },
            },
            "crawl_efficiency": {
                "page_load_time": 2.1,  # seconds
                "time_to_interactive": 2.8,
                "render_blocking_resources": 4,
                "ai_accessibility": "good",
            },
            "recommendations_for_ai": [
                "Maintain good CWV to ensure AI crawlers efficiently access content",
                "Consider server-side rendering for better AI content extraction",
            ],
        }

        recommendations = []

        if cwv_analysis["core_web_vitals"]["lcp"]["value"] > 2.5:
            recommendations.append(Recommendation(
                title="Improve LCP for AI Crawler Access",
                description="Slow LCP affects AI crawler's ability to quickly access main content. Optimize for faster content delivery.",
                category="AI Visibility - Performance",
                priority=Priority.HIGH,
                estimated_impact="Faster AI content discovery and indexing",
                implementation_effort="medium",
            ))

        return {
            "data": cwv_analysis,
            "recommendations": recommendations,
        }
