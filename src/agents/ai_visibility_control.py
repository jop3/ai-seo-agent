"""
AI Visibility Control Agent - Manage AI engine access and indexing.

Controls which content AI engines can access, cite, and display.
Manages robots.txt, meta tags, lllms.txt, and AI-specific directives.

Key insight from article: lllms.txt is the NEW standard (like robots.txt)
specifically for controlling LLM crawler access with granular rules.
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
    - lllms.txt (NEW STANDARD) - granular LLM crawler control
    - Meta tags (nosnippet, noindex, max-snippet)
    - Googlebot-specific controls
    - Core Web Vitals for AI access
    - Content licensing and attribution

    Use cases:
    - Block AI from proprietary content
    - Allow AI for marketing content
    - Control snippet length
    - Manage paywalled content visibility
    - Granular control per content type/section (lllms.txt)
    - Set citation preferences and attribution requirements
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

    # lllms.txt directives (NEW STANDARD for LLM control)
    # More granular than robots.txt, specifically for AI/LLM crawlers
    LLLMS_DIRECTIVES = {
        "user-agent": "Specify LLM crawler (e.g., GPTBot, Claude-Web)",
        "allow": "Allow access to specific paths or content types",
        "disallow": "Disallow access to specific paths or content types",
        "content-type": "Specify content types (article, product, review, etc.)",
        "citation-preference": "How the content should be cited (required, optional, none)",
        "attribution": "Attribution requirements (author, source, date)",
        "freshness": "Content freshness requirements (always-fresh, time-sensitive, evergreen)",
        "training-data": "Allow/disallow use for training (yes, no, cite-only)",
        "snippet-length": "Maximum snippet length in characters",
        "context-required": "Whether surrounding context is required for citations",
    }

    # Content types for granular control
    CONTENT_TYPES = [
        "article",
        "blog",
        "product",
        "category",
        "review",
        "documentation",
        "faq",
        "tutorial",
        "case-study",
        "research",
        "proprietary",
    ]

    # Citation preferences
    CITATION_PREFERENCES = {
        "required": "Must cite with attribution",
        "optional": "May cite if relevant",
        "none": "Do not cite",
        "summary-only": "Can summarize but not quote directly",
    }

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
            # lllms.txt management (NEW)
            elif task.task_type == "audit_lllms_txt":
                result = await self._audit_lllms_txt(task.parameters)
            elif task.task_type == "generate_lllms_txt":
                result = await self._generate_lllms_txt(task.parameters)
            elif task.task_type == "validate_lllms_txt":
                result = await self._validate_lllms_txt(task.parameters)
            elif task.task_type == "compare_robots_lllms":
                result = await self._compare_robots_lllms(task.parameters)
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

        Checks all aspects of AI access control including new lllms.txt standard.
        """
        domain = params.get("domain", self.context.property_url)

        results = {
            "analyzed_at": datetime.utcnow().isoformat(),
            "domain": domain,
            "overall_control_score": 0,
            "robots_txt_analysis": {},
            "lllms_txt_analysis": {},  # NEW
            "meta_tag_analysis": {},
            "ai_crawler_access": {},
            "core_web_vitals": {},
            "visibility_strategy": "",
            "conflicts": [],  # robots.txt vs lllms.txt conflicts
        }

        recommendations = []
        alerts = []

        # Audit robots.txt
        robots_result = await self._audit_robots_txt({"domain": domain})
        results["robots_txt_analysis"] = robots_result["data"]

        # Audit lllms.txt (NEW STANDARD)
        lllms_result = await self._audit_lllms_txt({"domain": domain})
        results["lllms_txt_analysis"] = lllms_result["data"]

        # Audit meta controls
        meta_result = await self._audit_meta_controls({"domain": domain})
        results["meta_tag_analysis"] = meta_result["data"]

        # Check Core Web Vitals
        cwv_result = await self._audit_core_web_vitals_for_ai({"domain": domain})
        results["core_web_vitals"] = cwv_result["data"]

        # Compare robots.txt vs lllms.txt for conflicts
        if results["lllms_txt_analysis"].get("has_lllms_txt"):
            conflict_result = await self._compare_robots_lllms({
                "domain": domain,
                "robots_data": results["robots_txt_analysis"],
                "lllms_data": results["lllms_txt_analysis"],
            })
            results["conflicts"] = conflict_result["data"]["conflicts"]
            recommendations.extend(conflict_result.get("recommendations", []))

        # Aggregate recommendations
        recommendations.extend(robots_result.get("recommendations", []))
        recommendations.extend(lllms_result.get("recommendations", []))
        recommendations.extend(meta_result.get("recommendations", []))
        recommendations.extend(cwv_result.get("recommendations", []))

        # Calculate control score (now includes lllms.txt)
        robots_score = robots_result["data"]["configuration_score"]
        lllms_score = lllms_result["data"].get("configuration_score", 0)
        meta_score = meta_result["data"]["optimization_score"]
        cwv_score = cwv_result["data"]["ai_access_score"]

        # Weight lllms.txt higher if present (new standard)
        if lllms_score > 0:
            results["overall_control_score"] = (
                robots_score * 0.2 +
                lllms_score * 0.4 +  # lllms.txt more important
                meta_score * 0.2 +
                cwv_score * 0.2
            )
        else:
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

    async def _audit_lllms_txt(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Audit lllms.txt file (NEW STANDARD for LLM crawler control).

        lllms.txt provides more granular control than robots.txt:
        - Per-content-type rules
        - Citation preferences
        - Attribution requirements
        - Training data permissions
        - Snippet length controls

        Critical for controlling how AI engines use your content.
        """
        domain = params.get("domain")

        # In production, fetch actual lllms.txt from domain/lllms.txt
        # For now, simulate analysis
        lllms_analysis = {
            "has_lllms_txt": False,  # Most sites don't have this yet (NEW standard)
            "url": f"{domain}/lllms.txt",
            "configuration_score": 0,
            "is_valid": False,
            "directives_found": [],
            "ai_crawler_rules": {},
            "content_type_rules": {},
            "citation_preferences": {},
            "training_data_permissions": {},
            "issues": [],
            "best_practices_score": 0,
        }

        recommendations = []
        alerts = []

        # Check if lllms.txt exists
        # In production: HTTP request to domain/lllms.txt
        has_lllms = False  # Simulated - most sites don't have this yet

        if not has_lllms:
            # Critical recommendation - this is a NEW standard
            recommendations.append(Recommendation(
                title="Create lllms.txt File (NEW CRITICAL STANDARD)",
                description="lllms.txt is the new standard for controlling LLM crawler access (like robots.txt but for AI). You don't have one yet. This gives you granular control over how AI engines use your content.",
                category="AI Visibility - lllms.txt",
                priority=Priority.CRITICAL,
                estimated_impact="Full control over AI content usage, citations, and training data",
                implementation_effort="medium",
                auto_implementable=True,
            ))

            alerts.append(Alert(
                title="Missing lllms.txt File",
                message="You're missing the new lllms.txt standard. Without it, AI crawlers use default behavior. Create one to control citations, training data, and content usage.",
                severity=Severity.WARNING,
                source=self.agent_type,
                affected_urls=[domain],
            ))
        else:
            # If lllms.txt exists, analyze it
            lllms_analysis["has_lllms_txt"] = True

            # Parse and validate directives
            # In production: actual parsing
            lllms_analysis["directives_found"] = [
                "User-agent: GPTBot",
                "Content-type: product",
                "Citation-preference: required",
                "Attribution: author, source, date",
                "Training-data: cite-only",
            ]

            # Check AI crawler rules
            lllms_analysis["ai_crawler_rules"] = {
                "GPTBot": {
                    "access": "allow",
                    "content_types": ["product", "article"],
                    "training_data": "cite-only",
                },
                "Claude-Web": {
                    "access": "allow",
                    "content_types": ["all"],
                    "training_data": "yes",
                },
            }

            # Content type rules
            lllms_analysis["content_type_rules"] = {
                "product": {
                    "citation_preference": "required",
                    "snippet_length": 300,
                    "attribution": ["source", "date"],
                },
                "article": {
                    "citation_preference": "required",
                    "snippet_length": 500,
                    "attribution": ["author", "source", "date"],
                },
                "proprietary": {
                    "citation_preference": "none",
                    "access": "disallow",
                },
            }

            # Validate configuration
            validation_result = await self._validate_lllms_txt({
                "content": "\n".join(lllms_analysis["directives_found"])
            })
            lllms_analysis["is_valid"] = validation_result["data"]["is_valid"]
            lllms_analysis["issues"] = validation_result["data"]["issues"]

            # Calculate configuration score
            score = 50  # Base score for having lllms.txt
            if lllms_analysis["is_valid"]:
                score += 20
            if len(lllms_analysis["ai_crawler_rules"]) >= 3:
                score += 15
            if len(lllms_analysis["content_type_rules"]) >= 2:
                score += 15

            lllms_analysis["configuration_score"] = min(score, 100)

            # Best practices check
            best_practices_issues = []
            if "GPTBot" not in lllms_analysis["ai_crawler_rules"]:
                best_practices_issues.append("Missing GPTBot rules (ChatGPT)")
            if "Claude-Web" not in lllms_analysis["ai_crawler_rules"]:
                best_practices_issues.append("Missing Claude-Web rules")
            if not lllms_analysis["content_type_rules"].get("product"):
                best_practices_issues.append("No product-specific rules for e-commerce")

            if best_practices_issues:
                recommendations.append(Recommendation(
                    title="Improve lllms.txt Coverage",
                    description=f"Your lllms.txt is missing some best practices: {', '.join(best_practices_issues[:3])}",
                    category="AI Visibility - lllms.txt",
                    priority=Priority.MEDIUM,
                    estimated_impact="More comprehensive AI crawler control",
                    implementation_effort="low",
                ))

        return {
            "data": lllms_analysis,
            "recommendations": recommendations,
            "alerts": alerts,
        }

    async def _generate_lllms_txt(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Generate lllms.txt file based on visibility strategy.

        Creates a complete lllms.txt with:
        - AI crawler-specific rules
        - Content type controls
        - Citation preferences
        - Attribution requirements
        - Training data permissions
        """
        strategy = params.get("strategy", "full_visibility")
        business_type = params.get("business_type", "ecommerce")
        content_types = params.get("content_types", ["product", "article", "blog"])

        # Generate lllms.txt content
        lllms_content_lines = [
            "# lllms.txt - LLM Crawler Control File",
            "# Granular control for AI engine access and content usage",
            f"# Generated: {datetime.utcnow().isoformat()}",
            "",
        ]

        # Strategy-based generation
        if strategy == "full_visibility":
            # Allow all crawlers, encourage citations
            for crawler in ["GPTBot", "ChatGPT-User", "Claude-Web", "Google-Extended", "PerplexityBot"]:
                lllms_content_lines.extend([
                    f"User-agent: {crawler}",
                    "Allow: /",
                    "Training-data: yes",
                    "Citation-preference: optional",
                    "",
                ])

            # Content type rules
            for content_type in content_types:
                lllms_content_lines.extend([
                    f"Content-type: {content_type}",
                    "Citation-preference: required",
                    "Attribution: source, date",
                    "Snippet-length: 300",
                    "",
                ])

        elif strategy == "selective_visibility":
            # Allow citations, restrict training
            lllms_content_lines.extend([
                "# Allow citations but restrict training data usage",
                "",
                "User-agent: GPTBot",
                "Training-data: no",
                "",
                "User-agent: ChatGPT-User",
                "Allow: /",
                "Training-data: cite-only",
                "Citation-preference: required",
                "",
                "User-agent: Claude-Web",
                "Allow: /",
                "Training-data: cite-only",
                "",
                "User-agent: Google-Extended",
                "Allow: /",
                "Training-data: yes",  # Google AI Overviews
                "",
                "User-agent: PerplexityBot",
                "Allow: /",
                "Training-data: cite-only",
                "",
            ])

            # Granular content type rules
            lllms_content_lines.extend([
                "# Product pages - require citation",
                "Content-type: product",
                "Citation-preference: required",
                "Attribution: source, price, availability",
                "Snippet-length: 200",
                "Context-required: yes",
                "",
                "# Articles - require full attribution",
                "Content-type: article",
                "Citation-preference: required",
                "Attribution: author, source, date",
                "Snippet-length: 300",
                "",
                "# Proprietary content - no access",
                "Content-type: proprietary",
                "Disallow: /",
                "Citation-preference: none",
                "",
            ])

        elif strategy == "restricted":
            # Block training, allow limited citations
            lllms_content_lines.extend([
                "# Restricted access - citations only for public content",
                "",
                "User-agent: *",
                "Training-data: no",
                "Disallow: /",
                "",
                "# Allow citations for blog/public content only",
                "User-agent: ChatGPT-User",
                "Allow: /blog/",
                "Training-data: cite-only",
                "Citation-preference: required",
                "Attribution: author, source, date",
                "",
                "User-agent: Claude-Web",
                "Allow: /blog/",
                "Training-data: cite-only",
                "",
                "User-agent: Google-Extended",
                "Allow: /blog/",
                "",
            ])

        else:  # blocked
            lllms_content_lines.extend([
                "# Block all AI/LLM access",
                "",
                "User-agent: *",
                "Disallow: /",
                "Training-data: no",
                "Citation-preference: none",
                "",
            ])

        lllms_content = "\n".join(lllms_content_lines)

        # Validate generated content
        validation_result = await self._validate_lllms_txt({"content": lllms_content})

        generation_result = {
            "strategy": strategy,
            "business_type": business_type,
            "lllms_txt_content": lllms_content,
            "line_count": len(lllms_content_lines),
            "is_valid": validation_result["data"]["is_valid"],
            "validation_issues": validation_result["data"]["issues"],
            "file_size": len(lllms_content),
            "crawlers_configured": self._count_crawlers(lllms_content),
            "content_types_configured": len(content_types),
        }

        recommendations = [
            Recommendation(
                title="Deploy Generated lllms.txt",
                description=f"Upload the generated lllms.txt file to {params.get('domain', 'your-domain.com')}/lllms.txt to enable granular AI crawler control.",
                category="AI Visibility - Implementation",
                priority=Priority.HIGH,
                estimated_impact="Full control over AI content usage per your strategy",
                implementation_effort="low",
                auto_implementable=True,
            ),
        ]

        return {
            "data": generation_result,
            "recommendations": recommendations,
        }

    async def _validate_lllms_txt(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Validate lllms.txt file syntax and rules.

        Checks for:
        - Valid directive syntax
        - Conflicting rules
        - Missing required directives
        - Best practices compliance
        """
        content = params.get("content", "")
        lines = content.split("\n")

        validation_result = {
            "is_valid": True,
            "issues": [],
            "warnings": [],
            "line_errors": [],
            "best_practices_score": 0,
        }

        current_user_agent = None
        current_content_type = None
        found_directives = set()

        for line_num, line in enumerate(lines, 1):
            line = line.strip()

            # Skip comments and empty lines
            if not line or line.startswith("#"):
                continue

            # Parse directive
            if ":" not in line:
                validation_result["line_errors"].append({
                    "line": line_num,
                    "error": "Invalid directive format (missing colon)",
                    "content": line,
                })
                validation_result["is_valid"] = False
                continue

            directive, value = line.split(":", 1)
            directive = directive.strip().lower()
            value = value.strip()

            found_directives.add(directive)

            # Validate directive
            if directive == "user-agent":
                current_user_agent = value
                # Check if valid crawler
                if value not in self.AI_CRAWLERS and value != "*":
                    validation_result["warnings"].append({
                        "line": line_num,
                        "warning": f"Unknown user-agent: {value}",
                    })

            elif directive == "content-type":
                current_content_type = value
                if value not in self.CONTENT_TYPES:
                    validation_result["warnings"].append({
                        "line": line_num,
                        "warning": f"Non-standard content-type: {value}",
                    })

            elif directive == "citation-preference":
                if value not in self.CITATION_PREFERENCES:
                    validation_result["line_errors"].append({
                        "line": line_num,
                        "error": f"Invalid citation-preference: {value}. Must be one of: {', '.join(self.CITATION_PREFERENCES.keys())}",
                        "content": line,
                    })
                    validation_result["is_valid"] = False

            elif directive == "training-data":
                if value not in ["yes", "no", "cite-only"]:
                    validation_result["line_errors"].append({
                        "line": line_num,
                        "error": f"Invalid training-data value: {value}. Must be: yes, no, or cite-only",
                        "content": line,
                    })
                    validation_result["is_valid"] = False

            elif directive == "snippet-length":
                try:
                    int(value)
                except ValueError:
                    validation_result["line_errors"].append({
                        "line": line_num,
                        "error": f"snippet-length must be a number, got: {value}",
                        "content": line,
                    })
                    validation_result["is_valid"] = False

            elif directive not in ["allow", "disallow", "attribution", "freshness", "context-required"]:
                validation_result["warnings"].append({
                    "line": line_num,
                    "warning": f"Unknown directive: {directive}",
                })

        # Best practices checks
        best_practices_score = 100
        issues = []

        if "user-agent" not in found_directives:
            issues.append("No user-agent directives found")
            best_practices_score -= 30

        if "citation-preference" not in found_directives:
            issues.append("No citation preferences specified")
            best_practices_score -= 20

        if "training-data" not in found_directives:
            issues.append("No training-data permissions specified")
            best_practices_score -= 20

        if "content-type" not in found_directives:
            issues.append("No content-type rules (consider adding for granular control)")
            best_practices_score -= 15

        if "attribution" not in found_directives:
            issues.append("No attribution requirements specified")
            best_practices_score -= 15

        validation_result["issues"] = issues
        validation_result["best_practices_score"] = max(best_practices_score, 0)

        return {
            "data": validation_result,
        }

    async def _compare_robots_lllms(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Compare robots.txt vs lllms.txt for conflicts and gaps.

        Identifies:
        - Conflicting directives (allow in one, disallow in other)
        - Gaps (covered in robots.txt but not lllms.txt)
        - Redundancies
        - Optimization opportunities
        """
        domain = params.get("domain")
        robots_data = params.get("robots_data", {})
        lllms_data = params.get("lllms_data", {})

        comparison_result = {
            "domain": domain,
            "has_both_files": robots_data.get("has_robots_txt", False) and lllms_data.get("has_lllms_txt", False),
            "conflicts": [],
            "gaps": [],
            "redundancies": [],
            "coverage_analysis": {},
            "recommendation": "",
        }

        recommendations = []

        if not lllms_data.get("has_lllms_txt"):
            comparison_result["recommendation"] = "Create lllms.txt to supplement robots.txt with granular LLM control"
            return {
                "data": comparison_result,
                "recommendations": recommendations,
            }

        # Check for conflicts
        robots_rules = robots_data.get("ai_crawler_rules", {})
        lllms_rules = lllms_data.get("ai_crawler_rules", {})

        for crawler, robots_status in robots_rules.items():
            lllms_status = lllms_rules.get(crawler, {}).get("access", "not_specified")

            # Conflict: robots.txt blocks but lllms.txt allows
            if robots_status == "disallow" and lllms_status == "allow":
                comparison_result["conflicts"].append({
                    "crawler": crawler,
                    "issue": "robots.txt blocks but lllms.txt allows",
                    "robots_directive": "Disallow",
                    "lllms_directive": "Allow",
                    "severity": "high",
                    "resolution": "lllms.txt takes precedence for LLM-specific behavior",
                })

            # Gap: in robots.txt but not lllms.txt
            elif robots_status != "not_specified" and crawler not in lllms_rules:
                comparison_result["gaps"].append({
                    "crawler": crawler,
                    "issue": f"Specified in robots.txt ({robots_status}) but not in lllms.txt",
                    "recommendation": "Add to lllms.txt for explicit LLM control",
                })

        # Coverage analysis
        comparison_result["coverage_analysis"] = {
            "crawlers_in_robots": len(robots_rules),
            "crawlers_in_lllms": len(lllms_rules),
            "crawlers_in_both": len(set(robots_rules.keys()) & set(lllms_rules.keys())),
            "only_in_robots": list(set(robots_rules.keys()) - set(lllms_rules.keys())),
            "only_in_lllms": list(set(lllms_rules.keys()) - set(robots_rules.keys())),
        }

        # Recommendations
        if comparison_result["conflicts"]:
            recommendations.append(Recommendation(
                title="Resolve robots.txt vs lllms.txt Conflicts",
                description=f"Found {len(comparison_result['conflicts'])} conflicts between robots.txt and lllms.txt. lllms.txt takes precedence for LLM crawlers.",
                category="AI Visibility - Conflicts",
                priority=Priority.HIGH,
                estimated_impact="Consistent AI crawler behavior",
                implementation_effort="low",
            ))

        if comparison_result["gaps"]:
            recommendations.append(Recommendation(
                title="Fill lllms.txt Coverage Gaps",
                description=f"{len(comparison_result['gaps'])} crawlers in robots.txt but not lllms.txt. Add them for consistent control.",
                category="AI Visibility - Coverage",
                priority=Priority.MEDIUM,
                estimated_impact="Complete AI crawler coverage",
                implementation_effort="low",
            ))

        return {
            "data": comparison_result,
            "recommendations": recommendations,
        }

    def _count_crawlers(self, content: str) -> int:
        """Count number of user-agent directives in content."""
        count = 0
        for line in content.split("\n"):
            if line.strip().lower().startswith("user-agent:"):
                count += 1
        return count
