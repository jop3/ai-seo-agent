"""
Settings Assistant Agent (Orchestrator)

A helper agent that:
- Assists users with configuring the system
- Explains available agents and their capabilities
- Helps compose multi-agent workflows
- Provides guidance on LLM settings
- Assists with writing style configuration
"""

from typing import Any

import structlog

from src.config import get_settings

logger = structlog.get_logger()


class SettingsAssistantAgent:
    """
    Orchestrator/helper agent that assists with:
    - System configuration
    - Understanding available agents
    - Coordinating multi-agent tasks
    - LLM model selection
    - Writing style setup
    """

    name = "settings-assistant"
    description = "Helps configure the system and coordinates work between agents"

    def __init__(self):
        self.settings = get_settings()

    def get_all_agents_info(self, include_tools: bool = True) -> dict[str, Any]:
        """Get information about all available agents."""
        from src.agent_runner.definitions import ALL_AGENTS

        agents_info = []
        for agent in ALL_AGENTS:
            info = {
                "name": agent.name,
                "description": agent.description,
                "capabilities": self._extract_capabilities(agent.instructions),
                "use_cases": self._extract_use_cases(agent.instructions),
            }
            if include_tools:
                info["tools"] = [t.name for t in agent.tools]
            agents_info.append(info)

        return {"agents": agents_info, "count": len(agents_info)}

    def _extract_capabilities(self, instructions: str) -> list[str]:
        """Extract capabilities from agent instructions."""
        capabilities = []
        lines = instructions.split("\n")
        in_capabilities = False

        for line in lines:
            stripped = line.strip()
            if "your role is to:" in stripped.lower():
                in_capabilities = True
                continue
            if in_capabilities:
                if stripped.startswith(("1.", "2.", "3.", "4.", "5.")):
                    # Extract the capability
                    cap = stripped.split(".", 1)[1].strip() if "." in stripped else stripped
                    capabilities.append(cap)
                elif stripped and not stripped.startswith(("1", "2", "3", "4", "5", "-")):
                    in_capabilities = False

        return capabilities[:5]  # Limit to 5 main capabilities

    def _extract_use_cases(self, instructions: str) -> list[str]:
        """Generate use cases from agent description."""
        # This would be enhanced with LLM to generate specific use cases
        return []

    async def explain_agent(self, agent_name: str) -> dict[str, Any]:
        """Explain what a specific agent does and how to use it."""
        from src.agent_runner.definitions import ALL_AGENTS

        agent = next((a for a in ALL_AGENTS if a.name == agent_name), None)
        if not agent:
            return {
                "error": f"Unknown agent: {agent_name}",
                "available_agents": [a.name for a in ALL_AGENTS],
            }

        return {
            "name": agent.name,
            "description": agent.description,
            "instructions_summary": agent.instructions[:500] + "..." if len(agent.instructions) > 500 else agent.instructions,
            "tools": [
                {
                    "name": t.name,
                    "description": t.description,
                }
                for t in agent.tools
            ],
            "example_questions": self._generate_example_questions(agent),
            "best_model_for": self._recommend_model_for_agent(agent),
        }

    def _generate_example_questions(self, agent) -> list[str]:
        """Generate example questions for an agent."""
        examples = {
            "seo-analyst": [
                "What are my top performing queries?",
                "Which queries are triggering AI Overviews?",
                "Show me any traffic drops this week",
            ],
            "trend-analyzer": [
                "Generate a weekly content opportunities report",
                "What topics are trending in health right now?",
                "What seasonal content should I prepare for next month?",
            ],
            "content-writer": [
                "Analyze our blog writing style",
                "Write a blog post about [topic]",
                "Improve this draft to match our brand voice",
            ],
            "agent-tester": [
                "How would an AI agent interpret this page?",
                "Test if a shopping agent could complete a purchase",
                "Validate the schema markup on our product pages",
            ],
            "monitoring-agent": [
                "Run a monitoring cycle",
                "Alert me to any traffic anomalies",
                "Check if our AIO status has changed",
            ],
            "optimizer": [
                "Generate FAQ schema for our products",
                "How can I optimize this page for AI Overviews?",
                "Create schema markup for this product page",
            ],
            "settings-assistant": [
                "What agents are available?",
                "Help me configure the LLM settings",
                "What model should I use for content writing?",
            ],
        }
        return examples.get(agent.name, [
            f"What can the {agent.name} agent do?",
            f"Run analysis with {agent.name}",
        ])

    def _recommend_model_for_agent(self, agent) -> dict[str, str]:
        """Recommend the best model for an agent's tasks."""
        recommendations = {
            "seo-analyst": {
                "recommended": "gpt-4o or claude-3-sonnet",
                "reason": "Good reasoning for data analysis, fast enough for interactive use",
            },
            "trend-analyzer": {
                "recommended": "gpt-4o-mini or local phi-4",
                "reason": "Simpler analysis tasks, cost-effective for frequent reports",
            },
            "content-writer": {
                "recommended": "claude-3-opus or gpt-4o",
                "reason": "Best writing quality, essential for matching brand voice",
            },
            "agent-tester": {
                "recommended": "gpt-4o",
                "reason": "Good at simulating agent behavior and technical analysis",
            },
            "optimizer": {
                "recommended": "gpt-4o-mini or claude-3-haiku",
                "reason": "Schema generation is straightforward, doesn't need most capable model",
            },
            "settings-assistant": {
                "recommended": "gpt-4o-mini or local phi-4",
                "reason": "Conversational help doesn't require advanced reasoning",
            },
        }
        return recommendations.get(agent.name, {
            "recommended": "gpt-4o",
            "reason": "Good general-purpose model for most tasks",
        })

    async def get_llm_configuration_help(self) -> dict[str, Any]:
        """Get help with LLM configuration."""
        return {
            "overview": """
The SEO Agent supports multiple LLM providers. You can assign different models to different agents
based on their needs - use powerful models for complex tasks and cheaper/faster models for simpler ones.
            """.strip(),
            "providers": {
                "local": {
                    "description": "Docker Model Runner with local models like Phi-4",
                    "pros": ["Free to run", "Fast for light tasks", "Private data stays local"],
                    "cons": ["Limited capabilities", "Requires GPU for good performance"],
                    "best_for": ["Testing", "Simple analysis", "High-volume low-complexity tasks"],
                },
                "openai": {
                    "description": "OpenAI GPT models via API",
                    "pros": ["Best overall quality", "Wide model range", "Good function calling"],
                    "cons": ["Costs per token", "Rate limits"],
                    "best_for": ["Production use", "Complex analysis", "Content generation"],
                },
                "anthropic": {
                    "description": "Anthropic Claude models via API",
                    "pros": ["Excellent writing quality", "Long context", "Safety-focused"],
                    "cons": ["Premium pricing for Opus"],
                    "best_for": ["Content writing", "Style matching", "Long-form analysis"],
                },
                "azure": {
                    "description": "Azure OpenAI Service",
                    "pros": ["Enterprise features", "Data residency", "Same as OpenAI models"],
                    "cons": ["Requires Azure subscription", "Setup complexity"],
                    "best_for": ["Enterprise deployments", "Compliance requirements"],
                },
                "openrouter": {
                    "description": "Access multiple providers through one API",
                    "pros": ["Many models", "Fallback options", "Cost comparison"],
                    "cons": ["Additional abstraction layer"],
                    "best_for": ["Model experimentation", "Flexibility"],
                },
            },
            "model_recommendations": {
                "cost_conscious": {
                    "simple_tasks": "phi-4 (local) or gpt-4o-mini",
                    "complex_tasks": "gpt-4o or claude-3-sonnet",
                    "content_writing": "claude-3-sonnet",
                },
                "quality_focused": {
                    "simple_tasks": "gpt-4o-mini",
                    "complex_tasks": "gpt-4o or claude-3-opus",
                    "content_writing": "claude-3-opus",
                },
                "speed_focused": {
                    "all_tasks": "gpt-4o-mini or claude-3-haiku",
                },
            },
        }

    async def get_writing_style_help(self) -> dict[str, Any]:
        """Get help with setting up writing style configuration."""
        return {
            "overview": """
The Content Writer agent can analyze your existing articles to learn your brand's voice and style.
This allows it to generate new content that sounds like your team wrote it.
            """.strip(),
            "steps": [
                {
                    "step": 1,
                    "title": "Gather Reference Articles",
                    "description": "Collect 3-5 URLs of your best blog posts that represent your brand voice",
                    "tips": [
                        "Choose articles written by your best writers",
                        "Include different types (guides, news, listicles)",
                        "Avoid guest posts or outsourced content",
                    ],
                },
                {
                    "step": 2,
                    "title": "Run Style Analysis",
                    "description": "Use the Content Writer agent to analyze these articles",
                    "example": "Analyze the writing style of these articles: [URLs]",
                },
                {
                    "step": 3,
                    "title": "Review Generated Style Guide",
                    "description": "The agent will extract tone, voice, vocabulary, and patterns",
                    "what_to_check": [
                        "Does the tone description match your brand?",
                        "Are the common phrases accurate?",
                        "Is the vocabulary appropriate?",
                    ],
                },
                {
                    "step": 4,
                    "title": "Save Style Guide",
                    "description": "Save the style guide in Settings for future content generation",
                },
                {
                    "step": 5,
                    "title": "Test Generation",
                    "description": "Generate a test article and compare to your existing content",
                    "tips": [
                        "Start with a topic similar to your reference articles",
                        "Have your team review for voice matching",
                        "Iterate on the style guide if needed",
                    ],
                },
            ],
            "troubleshooting": {
                "content_too_generic": "Add more specific reference articles, use a stronger model like Claude Opus",
                "wrong_tone": "Review and manually adjust the style guide, add specific tone descriptors",
                "vocabulary_mismatch": "Add industry-specific terms to the style guide manually",
            },
        }

    async def suggest_agent_for_task(self, task_description: str) -> dict[str, Any]:
        """Suggest which agent(s) to use for a task."""
        # Keywords to agent mapping
        task_keywords = {
            "seo-analyst": ["search console", "queries", "traffic", "ranking", "performance", "aio", "ai overview"],
            "trend-analyzer": ["trending", "trends", "opportunities", "weekly report", "seasonal", "keywords"],
            "content-writer": ["write", "blog", "article", "content", "style", "voice", "draft"],
            "agent-tester": ["test", "page", "schema", "checkout", "interpret", "validate"],
            "monitoring-agent": ["monitor", "alert", "anomaly", "watch", "track"],
            "optimizer": ["optimize", "faq", "schema markup", "improve", "recommendation"],
            "competitor-monitor": ["competitor", "competition", "benchmark"],
            "content-generator": ["generate content", "faq", "howto", "listicle"],
        }

        task_lower = task_description.lower()
        scores = {}

        for agent_name, keywords in task_keywords.items():
            score = sum(1 for kw in keywords if kw in task_lower)
            if score > 0:
                scores[agent_name] = score

        if not scores:
            return {
                "suggestion": "seo-analyst",
                "confidence": "low",
                "reason": "No clear match found. The SEO Analyst is a good starting point for general SEO questions.",
                "alternatives": ["settings-assistant", "optimizer"],
            }

        # Sort by score
        sorted_agents = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        best_agent = sorted_agents[0][0]
        alternatives = [a[0] for a in sorted_agents[1:3]]

        return {
            "suggestion": best_agent,
            "confidence": "high" if sorted_agents[0][1] >= 2 else "medium",
            "reason": f"Based on keywords in your task, the {best_agent} agent is best suited.",
            "alternatives": alternatives,
        }

    async def create_workflow(self, goal: str) -> dict[str, Any]:
        """Create a multi-agent workflow for a complex goal."""
        # Pre-defined workflows for common goals
        workflows = {
            "content_creation": {
                "name": "Content Creation Pipeline",
                "description": "Find trending topics, analyze style, and generate content",
                "steps": [
                    {
                        "agent": "trend-analyzer",
                        "action": "Generate weekly content opportunities report",
                        "output": "List of trending topics with keywords",
                    },
                    {
                        "agent": "content-writer",
                        "action": "Analyze existing articles for brand style",
                        "output": "Style guide for content generation",
                    },
                    {
                        "agent": "content-writer",
                        "action": "Generate articles for top trending topics",
                        "output": "Draft articles matching brand voice",
                    },
                    {
                        "agent": "optimizer",
                        "action": "Generate FAQ schema for new content",
                        "output": "Schema markup to add to pages",
                    },
                ],
            },
            "aio_optimization": {
                "name": "AI Overview Optimization",
                "description": "Analyze current AIO status and optimize for better citation",
                "steps": [
                    {
                        "agent": "seo-analyst",
                        "action": "Get top queries and check AIO status",
                        "output": "List of queries with AIO presence info",
                    },
                    {
                        "agent": "agent-tester",
                        "action": "Test how AI agents interpret your pages",
                        "output": "Agent interpretation report",
                    },
                    {
                        "agent": "optimizer",
                        "action": "Generate optimizations for high-value queries",
                        "output": "Specific recommendations and schema",
                    },
                    {
                        "agent": "monitoring-agent",
                        "action": "Set up monitoring for AIO changes",
                        "output": "Monitoring configuration",
                    },
                ],
            },
            "competitive_analysis": {
                "name": "Competitive Analysis",
                "description": "Understand how competitors are performing in AI search",
                "steps": [
                    {
                        "agent": "competitor-monitor",
                        "action": "Analyze competitor AIO citations",
                        "output": "Competitor citation report",
                    },
                    {
                        "agent": "seo-analyst",
                        "action": "Compare your queries to competitor queries",
                        "output": "Gap analysis",
                    },
                    {
                        "agent": "agent-tester",
                        "action": "Compare agent interpretation of your pages vs competitors",
                        "output": "Competitive comparison report",
                    },
                ],
            },
        }

        # Match goal to workflow
        goal_lower = goal.lower()
        if any(kw in goal_lower for kw in ["content", "write", "blog", "article"]):
            return workflows["content_creation"]
        elif any(kw in goal_lower for kw in ["aio", "ai overview", "optimize", "citation"]):
            return workflows["aio_optimization"]
        elif any(kw in goal_lower for kw in ["competitor", "competitive", "compare"]):
            return workflows["competitive_analysis"]
        else:
            return {
                "name": "Custom Workflow Needed",
                "description": "I'll help you design a custom workflow for your goal.",
                "available_workflows": list(workflows.keys()),
                "suggestion": "Please describe your goal in more detail, or choose from the available workflows.",
            }

    async def run(
        self,
        task: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Run the settings assistant.

        Supported tasks:
        - "list_agents": Show all available agents
        - "explain [agent_name]": Explain a specific agent
        - "llm_help": Help with LLM configuration
        - "style_help": Help with writing style setup
        - "suggest [task]": Suggest agent for a task
        - "workflow [goal]": Create a workflow for a goal
        """
        logger.info("Running settings assistant", task=task)
        task_lower = task.lower()

        if "list" in task_lower and "agent" in task_lower:
            agents = self.get_all_agents_info()
            return {
                "type": "agent_list",
                "agents": [
                    {
                        "name": a.name,
                        "description": a.description,
                        "tools": a.tools,
                    }
                    for a in agents
                ],
            }

        elif "explain" in task_lower:
            # Extract agent name from task
            parts = task.split()
            agent_name = parts[-1] if len(parts) > 1 else "seo-analyst"
            return await self.explain_agent(agent_name)

        elif "llm" in task_lower or "model" in task_lower:
            return await self.get_llm_configuration_help()

        elif "style" in task_lower or "writing" in task_lower:
            return await self.get_writing_style_help()

        elif "suggest" in task_lower:
            task_description = task.replace("suggest", "").strip()
            return await self.suggest_agent_for_task(task_description)

        elif "workflow" in task_lower:
            goal = task.replace("workflow", "").strip()
            return await self.create_workflow(goal)

        else:
            return {
                "type": "help",
                "message": "I'm the Settings Assistant. I can help you with:",
                "available_tasks": [
                    "list agents - Show all available agents",
                    "explain [agent-name] - Learn about a specific agent",
                    "llm help - Get help configuring LLM providers and models",
                    "style help - Get help setting up writing style analysis",
                    "suggest [task description] - Get agent recommendations for a task",
                    "workflow [goal] - Create a multi-agent workflow",
                ],
                "quick_tips": [
                    "Use the trend-analyzer for weekly content opportunity reports",
                    "Use the content-writer to generate articles matching your brand voice",
                    "Configure different models for different agents in Settings",
                ],
            }
