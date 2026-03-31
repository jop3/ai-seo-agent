"""
Agent and Tool Definitions

These definitions are compatible with both:
- Local execution (our custom runner)
- Azure AI Agent Service (Azure SDK)

The format mirrors Azure AI Agent Service's agent/tool schema.
"""

from dataclasses import dataclass, field
from typing import Any, Callable
from enum import Enum


class ToolType(str, Enum):
    """Tool types supported by Azure AI Agent Service."""
    FUNCTION = "function"
    CODE_INTERPRETER = "code_interpreter"
    FILE_SEARCH = "file_search"


@dataclass
class ParameterProperty:
    """Schema for a tool parameter property."""
    type: str
    description: str
    enum: list[str] | None = None
    items: dict[str, Any] | None = None  # For array types


@dataclass
class ToolParameters:
    """Schema for tool parameters (OpenAPI-style)."""
    type: str = "object"
    properties: dict[str, ParameterProperty] = field(default_factory=dict)
    required: list[str] = field(default_factory=list)


@dataclass
class ToolDefinition:
    """
    Definition of a tool that an agent can use.

    Compatible with Azure AI Agent Service function tools.
    """
    name: str
    description: str
    parameters: ToolParameters

    # Local execution
    handler: str | None = None  # "module.path:function_name" or API endpoint
    api_endpoint: str | None = None  # "/api/v1/analysis/full"

    def to_azure_format(self) -> dict[str, Any]:
        """Convert to Azure AI Agent Service format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": self.parameters.type,
                    "properties": {
                        name: {
                            "type": prop.type,
                            "description": prop.description,
                            **({"enum": prop.enum} if prop.enum else {}),
                            **({"items": prop.items} if prop.items else {}),
                        }
                        for name, prop in self.parameters.properties.items()
                    },
                    "required": self.parameters.required,
                }
            }
        }

    def to_openai_format(self) -> dict[str, Any]:
        """Convert to OpenAI function calling format (for local use)."""
        return self.to_azure_format()["function"]


@dataclass
class AgentDefinition:
    """
    Definition of an AI agent.

    Compatible with Azure AI Agent Service agent schema.
    """
    name: str
    description: str
    instructions: str
    model: str = "gpt-4o"
    tools: list[ToolDefinition] = field(default_factory=list)

    # Local execution mapping
    local_class: str | None = None  # "src.agents.seo_analyst:SEOAnalystAgent"

    # Metadata
    version: str = "1.0.0"
    tags: dict[str, str] = field(default_factory=dict)

    def to_azure_format(self) -> dict[str, Any]:
        """Convert to Azure AI Agent Service creation format."""
        return {
            "model": self.model,
            "name": self.name,
            "description": self.description,
            "instructions": self.instructions,
            "tools": [tool.to_azure_format() for tool in self.tools],
            "metadata": {
                "version": self.version,
                **self.tags,
            }
        }


# =============================================================================
# TOOL DEFINITIONS
# =============================================================================

TOOL_GET_TOP_QUERIES = ToolDefinition(
    name="get_top_queries",
    description="Fetch top performing queries from Google Search Console for a property",
    parameters=ToolParameters(
        properties={
            "limit": ParameterProperty(
                type="integer",
                description="Maximum number of queries to return (default: 500)"
            ),
            "days": ParameterProperty(
                type="integer",
                description="Number of days to analyze (default: 30)"
            ),
        },
        required=[],
    ),
    api_endpoint="/api/v1/analysis/full",
    handler="src.agents.seo_analyst:SEOAnalystAgent.get_top_queries",
)

TOOL_CHECK_AIO_STATUS = ToolDefinition(
    name="check_aio_status",
    description="Check if specific search queries trigger Google AI Overviews and whether the client is cited",
    parameters=ToolParameters(
        properties={
            "queries": ParameterProperty(
                type="array",
                description="List of search queries to check",
                items={"type": "string"},
            ),
        },
        required=["queries"],
    ),
    api_endpoint="/api/v1/analysis/aio-check",
    handler="src.agents.seo_analyst:SEOAnalystAgent.check_aio_status",
)

TOOL_ANALYZE_TRAFFIC_DROPS = ToolDefinition(
    name="analyze_traffic_drops",
    description="Detect and analyze significant traffic drops, correlating them with AI Overview introduction",
    parameters=ToolParameters(
        properties={
            "threshold_percent": ParameterProperty(
                type="number",
                description="Minimum percentage change to flag as significant (default: 20)"
            ),
            "comparison_days": ParameterProperty(
                type="integer",
                description="Days in each comparison period (default: 7)"
            ),
        },
        required=[],
    ),
    api_endpoint="/api/v1/analysis/traffic-drops",
    handler="src.agents.seo_analyst:SEOAnalystAgent.analyze_traffic_drops",
)

TOOL_CLASSIFY_QUERIES = ToolDefinition(
    name="classify_queries",
    description="Classify search queries by intent (informational, transactional, etc.) and AI Overview risk level",
    parameters=ToolParameters(
        properties={
            "queries": ParameterProperty(
                type="array",
                description="List of queries to classify",
                items={"type": "string"},
            ),
        },
        required=["queries"],
    ),
    api_endpoint="/api/v1/analysis/classify-queries",
    handler="src.agents.seo_analyst:SEOAnalystAgent.classify_queries",
)

TOOL_INTERPRET_PAGE = ToolDefinition(
    name="interpret_page",
    description="Analyze how an AI agent would interpret and understand a webpage, including extractable data and actionability",
    parameters=ToolParameters(
        properties={
            "url": ParameterProperty(
                type="string",
                description="URL of the page to analyze"
            ),
        },
        required=["url"],
    ),
    api_endpoint="/api/v1/agents/interpret-page",
    handler="src.agents.agent_tester:AgentTesterAgent.interpret_page",
)

TOOL_TEST_CHECKOUT_FLOW = ToolDefinition(
    name="test_checkout_flow",
    description="Test if an AI shopping agent could complete a purchase flow on a product page",
    parameters=ToolParameters(
        properties={
            "product_url": ParameterProperty(
                type="string",
                description="URL of the product page to test"
            ),
            "product_query": ParameterProperty(
                type="string",
                description="Search query the user might use to find this product"
            ),
        },
        required=["product_url"],
    ),
    api_endpoint="/api/v1/agents/test-checkout",
    handler="src.agents.agent_tester:AgentTesterAgent.test_checkout_flow",
)

TOOL_VALIDATE_SCHEMA = ToolDefinition(
    name="validate_schema",
    description="Validate Schema.org markup on a page and check for completeness",
    parameters=ToolParameters(
        properties={
            "url": ParameterProperty(
                type="string",
                description="URL of the page to validate"
            ),
        },
        required=["url"],
    ),
    api_endpoint="/api/v1/agents/validate-schema",
    handler="src.agents.agent_tester:AgentTesterAgent.validate_schema",
)

TOOL_COMPETITIVE_TEST = ToolDefinition(
    name="competitive_agent_test",
    description="Compare how an AI agent would evaluate your page vs competitors for a given query",
    parameters=ToolParameters(
        properties={
            "query": ParameterProperty(
                type="string",
                description="The search query to test"
            ),
            "client_url": ParameterProperty(
                type="string",
                description="Your page URL"
            ),
            "competitor_urls": ParameterProperty(
                type="array",
                description="List of competitor URLs to compare against",
                items={"type": "string"},
            ),
        },
        required=["query", "client_url"],
    ),
    api_endpoint="/api/v1/agents/competitive-test",
    handler="src.agents.agent_tester:AgentTesterAgent.competitive_test",
)

TOOL_RUN_MONITORING = ToolDefinition(
    name="run_monitoring_cycle",
    description="Run a full monitoring cycle: check traffic anomalies, algorithm updates, and AIO changes",
    parameters=ToolParameters(
        properties={
            "tracked_queries": ParameterProperty(
                type="array",
                description="Specific queries to monitor for AIO changes",
                items={"type": "string"},
            ),
            "traffic_threshold": ParameterProperty(
                type="number",
                description="Traffic change threshold for alerts (default: 25%)"
            ),
        },
        required=[],
    ),
    api_endpoint="/api/v1/agents/monitoring/run-cycle",
    handler="src.agents.monitoring:MonitoringAgent.run_monitoring_cycle",
)

TOOL_GENERATE_SCHEMA = ToolDefinition(
    name="generate_schema",
    description="Generate optimized Schema.org JSON-LD markup for a page",
    parameters=ToolParameters(
        properties={
            "url": ParameterProperty(
                type="string",
                description="URL of the page"
            ),
            "page_type": ParameterProperty(
                type="string",
                description="Type of page",
                enum=["product", "category", "article", "faq", "location"],
            ),
            "page_data": ParameterProperty(
                type="object",
                description="Page data to include in schema (name, price, description, etc.)"
            ),
        },
        required=["page_type", "page_data"],
    ),
    api_endpoint="/api/v1/optimizations/generate-schema",
    handler="src.agents.optimizer:OptimizationRecommenderAgent.generate_schema",
)

TOOL_GENERATE_FAQ = ToolDefinition(
    name="generate_faq",
    description="Generate FAQ content and FAQPage schema targeting specific search queries",
    parameters=ToolParameters(
        properties={
            "topic": ParameterProperty(
                type="string",
                description="Topic for the FAQ"
            ),
            "target_queries": ParameterProperty(
                type="array",
                description="Search queries the FAQ should address",
                items={"type": "string"},
            ),
            "num_faqs": ParameterProperty(
                type="integer",
                description="Number of FAQ items to generate (default: 5)"
            ),
        },
        required=["topic"],
    ),
    api_endpoint="/api/v1/optimizations/generate-faq",
    handler="src.agents.optimizer:OptimizationRecommenderAgent.generate_faq",
)

TOOL_OPTIMIZE_FOR_QUERY = ToolDefinition(
    name="optimize_for_query",
    description="Generate specific optimizations for a page to rank in AI Overviews for a query",
    parameters=ToolParameters(
        properties={
            "query": ParameterProperty(
                type="string",
                description="Target search query"
            ),
            "url": ParameterProperty(
                type="string",
                description="Page URL to optimize"
            ),
            "page_content": ParameterProperty(
                type="string",
                description="Current page content"
            ),
        },
        required=["query", "url", "page_content"],
    ),
    api_endpoint="/api/v1/optimizations/optimize-for-query",
    handler="src.agents.optimizer:OptimizationRecommenderAgent.optimize_for_query",
)


# =============================================================================
# AGENT DEFINITIONS
# =============================================================================

SEO_ANALYST_AGENT = AgentDefinition(
    name="seo-analyst",
    description="Analyzes search performance data to identify AI Overview impact and optimization opportunities",
    instructions="""You are an expert SEO analyst specializing in AI Overview optimization.

Your role is to:
1. Analyze Google Search Console data to understand search performance
2. Identify which queries trigger AI Overviews
3. Detect traffic drops and correlate them with AI Overview introduction
4. Classify queries by intent and AI Overview risk
5. Provide actionable insights to improve AI Overview citation rates

When analyzing data:
- Focus on high-traffic queries first
- Prioritize informational queries (highest AIO risk)
- Look for patterns in traffic drops
- Compare client citation rates vs competitors

Always provide specific, actionable recommendations with estimated impact.""",
    model="gpt-4o",
    tools=[
        TOOL_GET_TOP_QUERIES,
        TOOL_CHECK_AIO_STATUS,
        TOOL_ANALYZE_TRAFFIC_DROPS,
        TOOL_CLASSIFY_QUERIES,
    ],
    local_class="src.agents.seo_analyst:SEOAnalystAgent",
    tags={"category": "analysis", "priority": "high"},
)

AGENT_TESTER_AGENT = AgentDefinition(
    name="agent-tester",
    description="Simulates AI agents interacting with pages to test comprehension and actionability",
    instructions="""You are an AI agent simulator that tests how other AI agents would interact with webpages.

Your role is to:
1. Analyze pages from an AI agent's perspective
2. Test if autonomous shopping agents could complete purchases
3. Validate structured data (Schema.org) for AI comprehension
4. Compare agent-friendliness against competitors
5. Identify barriers that prevent AI agents from taking action

When testing pages:
- Check if product information is clearly extractable
- Verify prices, availability, and descriptions are machine-readable
- Test if checkout flows are agent-accessible
- Look for missing or incomplete schema markup

Provide specific technical recommendations to improve agent accessibility.""",
    model="gpt-4o",
    tools=[
        TOOL_INTERPRET_PAGE,
        TOOL_TEST_CHECKOUT_FLOW,
        TOOL_VALIDATE_SCHEMA,
        TOOL_COMPETITIVE_TEST,
    ],
    local_class="src.agents.agent_tester:AgentTesterAgent",
    tags={"category": "testing", "priority": "high"},
)

MONITORING_AGENT = AgentDefinition(
    name="monitoring-agent",
    description="Monitors for traffic anomalies, algorithm updates, and AI Overview changes",
    instructions="""You are a vigilant monitoring agent that watches for SEO-relevant changes.

Your role is to:
1. Detect significant traffic anomalies (drops or spikes)
2. Monitor for Google algorithm updates
3. Track AI Overview status changes for important queries
4. Send timely alerts when issues are detected
5. Generate daily/weekly summary reports

When monitoring:
- Flag any traffic drop > 25% as significant
- Correlate drops with AI Overview introduction
- Check industry news for algorithm update announcements
- Track competitor citation changes

Always provide context with alerts - not just what changed, but likely why.""",
    model="gpt-4o",
    tools=[
        TOOL_RUN_MONITORING,
        TOOL_CHECK_AIO_STATUS,
        TOOL_ANALYZE_TRAFFIC_DROPS,
    ],
    local_class="src.agents.monitoring:MonitoringAgent",
    tags={"category": "monitoring", "priority": "medium"},
)

OPTIMIZER_AGENT = AgentDefinition(
    name="optimizer",
    description="Generates optimization recommendations, schema markup, and content improvements",
    instructions="""You are an SEO optimization expert that generates actionable improvements.

Your role is to:
1. Generate Schema.org markup optimized for AI Overviews
2. Create FAQ content targeting search queries
3. Recommend content structure improvements
4. Provide specific code/markup that can be implemented
5. Prioritize optimizations by potential impact

When generating optimizations:
- Ensure all schema is valid and complete
- Target queries with high traffic AND high AIO risk
- Make recommendations specific and implementable
- Include the actual code/markup to add
- Estimate potential traffic impact

Focus on quick wins first, then longer-term structural improvements.""",
    model="gpt-4o",
    tools=[
        TOOL_GENERATE_SCHEMA,
        TOOL_GENERATE_FAQ,
        TOOL_OPTIMIZE_FOR_QUERY,
    ],
    local_class="src.agents.optimizer:OptimizationRecommenderAgent",
    tags={"category": "optimization", "priority": "high"},
)

# =============================================================================
# NEW AGENTS (Competitor, Content, Multi-Engine, Technical, Link)
# =============================================================================

TOOL_ANALYZE_COMPETITORS = ToolDefinition(
    name="analyze_competitors",
    description="Analyze competitor AIO citations, rankings, and content strategy",
    parameters=ToolParameters(
        properties={
            "competitors": ParameterProperty(
                type="array",
                description="List of competitor domains to analyze",
                items={"type": "string"},
            ),
        },
        required=[],
    ),
    handler="src.agents.competitor_monitor:CompetitorMonitorAgent.analyze",
)

TOOL_GENERATE_CONTENT = ToolDefinition(
    name="generate_content",
    description="Generate AIO-optimized content (FAQ, HowTo, listicles)",
    parameters=ToolParameters(
        properties={
            "topic": ParameterProperty(type="string", description="Topic for content"),
            "content_type": ParameterProperty(
                type="string",
                description="Type of content",
                enum=["faq", "howto", "listicle", "brief"],
            ),
            "queries": ParameterProperty(
                type="array",
                description="Target search queries",
                items={"type": "string"},
            ),
        },
        required=["topic", "content_type"],
    ),
    handler="src.agents.content_generator:ContentGeneratorAgent.generate",
)

TOOL_CHECK_AI_ENGINES = ToolDefinition(
    name="check_ai_engines",
    description="Check presence across AI search engines (Google AIO, Perplexity, Bing Copilot)",
    parameters=ToolParameters(
        properties={
            "queries": ParameterProperty(
                type="array",
                description="Queries to check across engines",
                items={"type": "string"},
            ),
            "engines": ParameterProperty(
                type="array",
                description="Engines to check",
                items={"type": "string"},
            ),
        },
        required=["queries"],
    ),
    handler="src.agents.multi_engine_tracker:MultiEngineTrackerAgent.check",
)

TOOL_TECHNICAL_AUDIT = ToolDefinition(
    name="technical_audit",
    description="Run technical SEO audit (broken links, redirects, meta tags)",
    parameters=ToolParameters(
        properties={
            "url": ParameterProperty(type="string", description="URL to audit"),
            "max_pages": ParameterProperty(type="integer", description="Max pages to crawl"),
        },
        required=["url"],
    ),
    handler="src.agents.technical_seo:TechnicalSEOAgent.audit",
)

TOOL_FIND_LINK_OPPORTUNITIES = ToolDefinition(
    name="find_link_opportunities",
    description="Find citation and link building opportunities",
    parameters=ToolParameters(
        properties={
            "queries": ParameterProperty(
                type="array",
                description="Queries to analyze for citation opportunities",
                items={"type": "string"},
            ),
        },
        required=["queries"],
    ),
    handler="src.agents.link_analysis:LinkAnalysisAgent.find_opportunities",
)

# =============================================================================
# TREND ANALYZER & CONTENT WRITER TOOLS
# =============================================================================

TOOL_FETCH_TRENDS = ToolDefinition(
    name="fetch_trends",
    description="Fetch trending search topics from Google Trends and Search Console for content opportunities",
    parameters=ToolParameters(
        properties={
            "category": ParameterProperty(
                type="string",
                description="Category to focus on (e.g., health, beauty, pharmacy)",
            ),
            "geo": ParameterProperty(
                type="string",
                description="Geographic region (default: SE for Sweden)",
            ),
            "days": ParameterProperty(
                type="integer",
                description="Days of data to analyze (default: 30)",
            ),
        },
        required=[],
    ),
    handler="src.agents.trend_analyzer:TrendAnalyzerAgent.fetch_google_trends",
)

TOOL_GENERATE_WEEKLY_REPORT = ToolDefinition(
    name="generate_weekly_report",
    description="Generate a weekly content opportunities report with trending topics and recommended blog posts",
    parameters=ToolParameters(
        properties={
            "num_opportunities": ParameterProperty(
                type="integer",
                description="Number of content opportunities to include (default: 10)",
            ),
            "include_products": ParameterProperty(
                type="boolean",
                description="Whether to include product recommendations (default: true)",
            ),
        },
        required=[],
    ),
    handler="src.agents.trend_analyzer:TrendAnalyzerAgent.generate_weekly_report",
)

TOOL_GET_SEASONAL_TOPICS = ToolDefinition(
    name="get_seasonal_topics",
    description="Get seasonal content opportunities based on upcoming events, holidays, and health seasons",
    parameters=ToolParameters(
        properties={
            "months_ahead": ParameterProperty(
                type="integer",
                description="How many months ahead to look (default: 2)",
            ),
        },
        required=[],
    ),
    handler="src.agents.trend_analyzer:TrendAnalyzerAgent.analyze_seasonal_opportunities",
)

TOOL_ANALYZE_WRITING_STYLE = ToolDefinition(
    name="analyze_writing_style",
    description="Analyze existing articles to extract the brand's writing style and tone guide",
    parameters=ToolParameters(
        properties={
            "article_urls": ParameterProperty(
                type="array",
                description="URLs of existing articles to analyze for style",
                items={"type": "string"},
            ),
            "num_examples": ParameterProperty(
                type="integer",
                description="Number of articles to analyze (default: 5)",
            ),
        },
        required=["article_urls"],
    ),
    handler="src.agents.content_writer:ContentWriterAgent.analyze_style",
)

TOOL_WRITE_ARTICLE = ToolDefinition(
    name="write_article",
    description="Generate a full blog post or product news article matching the brand's style",
    parameters=ToolParameters(
        properties={
            "topic": ParameterProperty(
                type="string",
                description="The topic or title idea for the article",
            ),
            "keywords": ParameterProperty(
                type="array",
                description="Target SEO keywords to incorporate",
                items={"type": "string"},
            ),
            "article_type": ParameterProperty(
                type="string",
                description="Type of content",
                enum=["blog", "product-news", "guide", "listicle"],
            ),
            "word_count": ParameterProperty(
                type="integer",
                description="Target word count (default: 800)",
            ),
            "reference_urls": ParameterProperty(
                type="array",
                description="URLs of similar articles for style reference",
                items={"type": "string"},
            ),
        },
        required=["topic"],
    ),
    handler="src.agents.content_writer:ContentWriterAgent.generate_article",
)

TOOL_IMPROVE_DRAFT = ToolDefinition(
    name="improve_draft",
    description="Improve an existing draft to better match the brand style and quality standards",
    parameters=ToolParameters(
        properties={
            "draft_content": ParameterProperty(
                type="string",
                description="The draft content to improve",
            ),
            "feedback": ParameterProperty(
                type="string",
                description="Specific feedback or areas to improve",
            ),
            "reference_urls": ParameterProperty(
                type="array",
                description="URLs of articles to use as style reference",
                items={"type": "string"},
            ),
        },
        required=["draft_content"],
    ),
    handler="src.agents.content_writer:ContentWriterAgent.improve_draft",
)

TOOL_SUGGEST_PRODUCTS = ToolDefinition(
    name="suggest_products",
    description="Suggest relevant products to feature in an article based on the topic",
    parameters=ToolParameters(
        properties={
            "topic": ParameterProperty(
                type="string",
                description="The article topic to find matching products for",
            ),
            "category": ParameterProperty(
                type="string",
                description="Optional category hint (e.g., 'hudvård', 'kosttillskott')",
            ),
            "max_products": ParameterProperty(
                type="integer",
                description="Maximum number of products to suggest (default: 5)",
            ),
        },
        required=["topic"],
    ),
    handler="src.agents.content_writer:ContentWriterAgent.suggest_products_for_topic",
)

# =============================================================================
# SETTINGS ASSISTANT TOOLS
# =============================================================================

TOOL_LIST_AGENTS = ToolDefinition(
    name="list_agents",
    description="List all available agents with their capabilities and tools",
    parameters=ToolParameters(
        properties={
            "include_tools": ParameterProperty(
                type="boolean",
                description="Whether to include tool details (default: true)",
            ),
        },
        required=[],
    ),
    handler="src.agents.settings_assistant:SettingsAssistantAgent.get_all_agents_info",
)

TOOL_EXPLAIN_AGENT = ToolDefinition(
    name="explain_agent",
    description="Get detailed explanation of what a specific agent does and how to use it",
    parameters=ToolParameters(
        properties={
            "agent_name": ParameterProperty(
                type="string",
                description="Name of the agent to explain",
            ),
        },
        required=["agent_name"],
    ),
    handler="src.agents.settings_assistant:SettingsAssistantAgent.explain_agent",
)

TOOL_SUGGEST_AGENT = ToolDefinition(
    name="suggest_agent",
    description="Suggest which agent to use for a specific task",
    parameters=ToolParameters(
        properties={
            "task_description": ParameterProperty(
                type="string",
                description="Description of the task you want to accomplish",
            ),
        },
        required=["task_description"],
    ),
    handler="src.agents.settings_assistant:SettingsAssistantAgent.suggest_agent_for_task",
)

TOOL_CREATE_WORKFLOW = ToolDefinition(
    name="create_workflow",
    description="Create a multi-agent workflow for a complex goal",
    parameters=ToolParameters(
        properties={
            "goal": ParameterProperty(
                type="string",
                description="The goal you want to achieve (e.g., 'content creation', 'AIO optimization')",
            ),
        },
        required=["goal"],
    ),
    handler="src.agents.settings_assistant:SettingsAssistantAgent.create_workflow",
)

TOOL_GET_LLM_HELP = ToolDefinition(
    name="get_llm_help",
    description="Get help with configuring LLM providers and models",
    parameters=ToolParameters(
        properties={},
        required=[],
    ),
    handler="src.agents.settings_assistant:SettingsAssistantAgent.get_llm_configuration_help",
)

TOOL_GET_STYLE_HELP = ToolDefinition(
    name="get_style_help",
    description="Get help with setting up writing style configuration",
    parameters=ToolParameters(
        properties={},
        required=[],
    ),
    handler="src.agents.settings_assistant:SettingsAssistantAgent.get_writing_style_help",
)

COMPETITOR_MONITOR_AGENT = AgentDefinition(
    name="competitor-monitor",
    description="Monitors competitor SEO performance and AI Overview presence",
    instructions="""You are a competitive intelligence agent specializing in SEO and AI Overview analysis.

Your role is to:
1. Track competitor AIO citation rates
2. Monitor competitor ranking changes
3. Detect content and schema updates
4. Identify competitive threats and opportunities
5. Provide actionable competitive insights

Focus on understanding WHY competitors are getting cited and how to replicate their success.""",
    model="gpt-4o",
    tools=[TOOL_ANALYZE_COMPETITORS, TOOL_CHECK_AIO_STATUS],
    local_class="src.agents.competitor_monitor:CompetitorMonitorAgent",
    tags={"category": "competitive", "priority": "high"},
)

CONTENT_GENERATOR_AGENT = AgentDefinition(
    name="content-generator",
    description="Generates AIO-optimized content including FAQs, HowTos, and listicles",
    instructions="""You are a content creation specialist focused on AI Overview optimization.

Your role is to:
1. Generate FAQ content targeting specific queries
2. Create HowTo guides with proper schema
3. Write listicle content optimized for citation
4. Produce content briefs for writers
5. Optimize existing content for AIO

All content should be factual, authoritative, and structured for AI citation.""",
    model="gpt-4o",
    tools=[TOOL_GENERATE_CONTENT, TOOL_GENERATE_FAQ],
    local_class="src.agents.content_generator:ContentGeneratorAgent",
    tags={"category": "content", "priority": "high"},
)

MULTI_ENGINE_TRACKER_AGENT = AgentDefinition(
    name="multi-engine-tracker",
    description="Tracks presence across AI search engines (Perplexity, ChatGPT, Bing Copilot)",
    instructions="""You are a multi-engine tracking specialist.

Your role is to:
1. Monitor presence across Google AIO, Perplexity, Bing Copilot, ChatGPT
2. Compare citation rates across engines
3. Identify engine-specific optimization opportunities
4. Track emerging AI search platforms
5. Provide cross-engine visibility reports

Different AI engines have different citation patterns - understand and leverage these differences.""",
    model="gpt-4o",
    tools=[TOOL_CHECK_AI_ENGINES, TOOL_CHECK_AIO_STATUS],
    local_class="src.agents.multi_engine_tracker:MultiEngineTrackerAgent",
    tags={"category": "tracking", "priority": "medium"},
)

TECHNICAL_SEO_AGENT = AgentDefinition(
    name="technical-seo",
    description="Audits technical SEO issues like broken links, redirects, and page speed",
    instructions="""You are a technical SEO auditor.

Your role is to:
1. Crawl sites for broken links and errors
2. Check redirect chains and status codes
3. Validate robots.txt and sitemaps
4. Audit meta tags and canonicals
5. Identify technical barriers to AI crawling

Focus on issues that impact both traditional SEO and AI agent accessibility.""",
    model="gpt-4o",
    tools=[TOOL_TECHNICAL_AUDIT, TOOL_VALIDATE_SCHEMA],
    local_class="src.agents.technical_seo:TechnicalSEOAgent",
    tags={"category": "technical", "priority": "medium"},
)

LINK_ANALYSIS_AGENT = AgentDefinition(
    name="link-analysis",
    description="Analyzes link opportunities and AIO citation sources",
    instructions="""You are a link analysis and citation opportunity specialist.

Your role is to:
1. Find AIO citation opportunities based on current sources
2. Identify unlinked brand mentions
3. Analyze competitor backlink profiles
4. Suggest internal linking improvements
5. Find broken link building opportunities

Focus on opportunities that could lead to AIO citations, not just traditional backlinks.""",
    model="gpt-4o",
    tools=[TOOL_FIND_LINK_OPPORTUNITIES, TOOL_ANALYZE_COMPETITORS],
    local_class="src.agents.link_analysis:LinkAnalysisAgent",
    tags={"category": "links", "priority": "medium"},
)

TREND_ANALYZER_AGENT = AgentDefinition(
    name="trend-analyzer",
    description="Discovers trending topics and content opportunities from search data and trends",
    instructions="""You are a trend analysis expert that helps marketing teams find content opportunities.

Your role is to:
1. Analyze Google Search Console data to find rising queries
2. Identify trending topics relevant to the business
3. Discover seasonal content opportunities
4. Match trending topics to product catalog
5. Generate weekly content opportunity reports

When analyzing trends:
- Focus on topics with growing search interest
- Identify seasonal patterns (health seasons, holidays, events)
- Look for topics that align with products you can feature
- Prioritize topics where you can provide genuine value
- Consider both short-term trends and evergreen opportunities

Your output should be actionable - specific topic recommendations with:
- Suggested headlines
- Target keywords
- Products to feature
- Recommended publish timing
- Content type (blog, guide, listicle, product news)

Think like the SEO firm that sends weekly keyword reports - but better and automated.""",
    model="gpt-4o",
    tools=[
        TOOL_FETCH_TRENDS,
        TOOL_GENERATE_WEEKLY_REPORT,
        TOOL_GET_SEASONAL_TOPICS,
        TOOL_GET_TOP_QUERIES,
    ],
    local_class="src.agents.trend_analyzer:TrendAnalyzerAgent",
    tags={"category": "trends", "priority": "high"},
)

CONTENT_WRITER_AGENT = AgentDefinition(
    name="content-writer",
    description="Generates blog posts and product news that match your brand's voice and style",
    instructions="""You are an expert content writer who creates articles that perfectly match the brand's voice.

Your role is to:
1. Analyze existing articles to understand the brand's writing style
2. Generate new content that sounds like it was written by the same team
3. Incorporate trending topics and SEO keywords naturally
4. Feature relevant products without being salesy
5. Produce publish-ready content that needs minimal editing

Before writing:
- ALWAYS analyze existing articles first to understand the style
- Extract the tone, voice, vocabulary, and formatting patterns
- Note common phrases and brand terminology

When writing:
- Match the exact tone and voice of existing content
- Use the same sentence structure and paragraph length
- Include proper formatting (subheadings, bullets where appropriate)
- Weave in products naturally as solutions, not advertisements
- Create genuinely useful content, not generic filler
- Include compelling intros and clear calls-to-action

Your goal is to eliminate the problem of AI-generated content that "doesn't sound like us" and requires heavy editing. The content you produce should be indistinguishable from what the human team writes.

You can also improve existing drafts to better match the brand style.""",
    model="gpt-4o",
    tools=[
        TOOL_ANALYZE_WRITING_STYLE,
        TOOL_WRITE_ARTICLE,
        TOOL_IMPROVE_DRAFT,
        TOOL_GENERATE_FAQ,
        TOOL_SUGGEST_PRODUCTS,
    ],
    local_class="src.agents.content_writer:ContentWriterAgent",
    tags={"category": "content", "priority": "high"},
)

SETTINGS_ASSISTANT_AGENT = AgentDefinition(
    name="settings-assistant",
    description="Your helpful guide to configuring the system, understanding agents, and creating workflows",
    instructions="""You are a friendly and knowledgeable assistant that helps users get the most out of the SEO Agent system.

Your role is to:
1. Explain what each agent does and when to use it
2. Help configure LLM providers and model assignments
3. Guide users through setting up writing style analysis
4. Suggest which agent to use for different tasks
5. Create multi-agent workflows for complex goals

You have deep knowledge about:
- All available agents and their capabilities
- LLM providers (OpenAI, Anthropic, Azure, local models, OpenRouter)
- How to optimize model choices for different tasks (cost vs quality)
- Writing style configuration for brand-consistent content
- Multi-agent workflows for common SEO goals

When helping users:
- Be friendly and approachable - marketing teams aren't developers
- Provide clear step-by-step guidance
- Offer specific recommendations, not just options
- Explain the "why" behind recommendations
- Use examples to illustrate concepts

You're the first stop for users who aren't sure where to start or need help with configuration.
Think of yourself as a knowledgeable colleague who knows the system inside out.""",
    model="gpt-4o",
    tools=[
        TOOL_LIST_AGENTS,
        TOOL_EXPLAIN_AGENT,
        TOOL_SUGGEST_AGENT,
        TOOL_CREATE_WORKFLOW,
        TOOL_GET_LLM_HELP,
        TOOL_GET_STYLE_HELP,
    ],
    local_class="src.agents.settings_assistant:SettingsAssistantAgent",
    tags={"category": "helper", "priority": "high"},
)

# =============================================================================
# PHARMACEUTICAL FACT CHECKER TOOLS & AGENT
# =============================================================================

TOOL_ANALYZE_PHARMA_CONTENT = ToolDefinition(
    name="analyze_pharma_content",
    description="Analyze content for pharmaceutical claims, drug mentions, and flag items needing review",
    parameters=ToolParameters(
        properties={
            "content": ParameterProperty(
                type="string",
                description="The content to analyze for pharmaceutical claims",
            ),
        },
        required=["content"],
    ),
    handler="src.agents.pharma_fact_checker:PharmaFactCheckerAgent.analyze_content",
)

TOOL_ENRICH_PHARMA_CONTENT = ToolDefinition(
    name="enrich_pharma_content",
    description="Enrich content with verified pharmaceutical facts and add citations from authoritative sources",
    parameters=ToolParameters(
        properties={
            "content": ParameterProperty(
                type="string",
                description="The content to enrich with citations",
            ),
            "add_citations": ParameterProperty(
                type="boolean",
                description="Whether to add citation links (default: true)",
            ),
        },
        required=["content"],
    ),
    handler="src.agents.pharma_fact_checker:PharmaFactCheckerAgent.enrich_content",
)

TOOL_CLASSIFY_CONTENT_TYPE = ToolDefinition(
    name="classify_content_type",
    description="Classify content by type and determine required review level (cosmetic, OTC drug, RX drug, health advice)",
    parameters=ToolParameters(
        properties={
            "content": ParameterProperty(
                type="string",
                description="The content to classify",
            ),
        },
        required=["content"],
    ),
    handler="src.agents.pharma_fact_checker:PharmaFactCheckerAgent.classify_content_type",
)

TOOL_FETCH_1177_INFO = ToolDefinition(
    name="fetch_1177_info",
    description="Fetch health information from 1177.se for a given topic",
    parameters=ToolParameters(
        properties={
            "topic": ParameterProperty(
                type="string",
                description="Health topic to search for on 1177.se",
            ),
        },
        required=["topic"],
    ),
    handler="src.agents.pharma_fact_checker:PharmaFactCheckerAgent.fetch_1177_info",
)

PHARMA_FACT_CHECKER_AGENT = AgentDefinition(
    name="pharma-fact-checker",
    description="Verifies pharmaceutical content against authoritative Swedish sources (FASS, 1177, Läkemedelsverket)",
    instructions="""You are a pharmaceutical content verification specialist for a Swedish pharmacy.

Your role is to:
1. Analyze content for drug mentions and medical claims
2. Verify claims against authoritative sources (FASS, 1177.se, Läkemedelsverket)
3. Flag content that needs pharmaceutical review before publishing
4. Add proper citations and source links
5. Classify content by review level (cosmetic vs OTC vs RX)

When analyzing content:
- Identify all drug/medication mentions (both brand names and substances)
- Extract health claims that need verification
- Check dosage information for accuracy
- Flag any pregnancy/nursing/children warnings
- Note content that mentions prescription medications (höjd granskning)

You help ensure pharmaceutical content is accurate and compliant before it reaches the Farmaceut for final review.

For Swedish pharmacy content, always reference:
- FASS.se for drug information
- 1177.se for general health information
- Läkemedelsverket for regulatory guidance""",
    model="gpt-4o",
    tools=[
        TOOL_ANALYZE_PHARMA_CONTENT,
        TOOL_ENRICH_PHARMA_CONTENT,
        TOOL_CLASSIFY_CONTENT_TYPE,
        TOOL_FETCH_1177_INFO,
    ],
    local_class="src.agents.pharma_fact_checker:PharmaFactCheckerAgent",
    tags={"category": "compliance", "priority": "high"},
)

# =============================================================================
# PRODUCT LIST PARSER TOOLS & AGENT
# =============================================================================

TOOL_PARSE_PRODUCT_CSV = ToolDefinition(
    name="parse_product_csv",
    description="Parse a CSV product list and extract structured product data with category suggestions",
    parameters=ToolParameters(
        properties={
            "csv_content": ParameterProperty(
                type="string",
                description="CSV content as a string",
            ),
        },
        required=["csv_content"],
    ),
    handler="src.agents.product_list_parser:ProductListParserAgent.parse_csv",
)

TOOL_PARSE_EMAIL_PRODUCTS = ToolDefinition(
    name="parse_email_products",
    description="Extract product information from email text (handles bullet lists, tables, etc.)",
    parameters=ToolParameters(
        properties={
            "email_text": ParameterProperty(
                type="string",
                description="Email text containing product list",
            ),
        },
        required=["email_text"],
    ),
    handler="src.agents.product_list_parser:ProductListParserAgent.parse_email_text",
)

TOOL_GENERATE_IMPORT_FORMAT = ToolDefinition(
    name="generate_import_format",
    description="Generate CMS import-ready format from parsed products (Optimizely or generic CSV)",
    parameters=ToolParameters(
        properties={
            "products": ParameterProperty(
                type="array",
                description="List of parsed products",
                items={"type": "object"},
            ),
            "format_type": ParameterProperty(
                type="string",
                description="Target format: 'optimizely' or 'generic'",
                enum=["optimizely", "generic"],
            ),
        },
        required=["products"],
    ),
    handler="src.agents.product_list_parser:ProductListParserAgent.generate_import_format",
)

TOOL_VALIDATE_PRODUCTS = ToolDefinition(
    name="validate_products",
    description="Validate product data for completeness, duplicates, and EAN code validity",
    parameters=ToolParameters(
        properties={
            "products": ParameterProperty(
                type="array",
                description="List of products to validate",
                items={"type": "object"},
            ),
        },
        required=["products"],
    ),
    handler="src.agents.product_list_parser:ProductListParserAgent.validate_products",
)

PRODUCT_LIST_PARSER_AGENT = AgentDefinition(
    name="product-list-parser",
    description="Parses product lists from Excel, CSV, or email text and prepares them for CMS import",
    instructions="""You are a product data specialist who helps the marketing team process product lists.

Your role is to:
1. Parse product lists from various formats (CSV, Excel exports, email text)
2. Extract product information (name, SKU, EAN, brand, price)
3. Suggest appropriate category mappings based on product names
4. Validate product data (check EAN codes, find duplicates)
5. Generate import-ready formats for Optimizely Commerce

When processing product lists:
- Handle Swedish column names (Produktnamn, Artikelnummer, Pris, etc.)
- Detect common pharmacy product categories automatically
- Flag products with missing or invalid data
- Group products by suggested category for easy review

You help reduce the manual work when Emma Falk sends product lists from Commercial,
making it faster to get products into the correct categories in the CMS.""",
    model="gpt-4o",
    tools=[
        TOOL_PARSE_PRODUCT_CSV,
        TOOL_PARSE_EMAIL_PRODUCTS,
        TOOL_GENERATE_IMPORT_FORMAT,
        TOOL_VALIDATE_PRODUCTS,
    ],
    local_class="src.agents.product_list_parser:ProductListParserAgent",
    tags={"category": "data", "priority": "medium"},
)

# All agents for easy iteration
ALL_AGENTS = [
    SEO_ANALYST_AGENT,
    AGENT_TESTER_AGENT,
    MONITORING_AGENT,
    OPTIMIZER_AGENT,
    COMPETITOR_MONITOR_AGENT,
    CONTENT_GENERATOR_AGENT,
    MULTI_ENGINE_TRACKER_AGENT,
    TECHNICAL_SEO_AGENT,
    LINK_ANALYSIS_AGENT,
    TREND_ANALYZER_AGENT,
    CONTENT_WRITER_AGENT,
    SETTINGS_ASSISTANT_AGENT,
    PHARMA_FACT_CHECKER_AGENT,
    PRODUCT_LIST_PARSER_AGENT,
]

# All tools for easy iteration
ALL_TOOLS = [
    TOOL_GET_TOP_QUERIES,
    TOOL_CHECK_AIO_STATUS,
    TOOL_ANALYZE_TRAFFIC_DROPS,
    TOOL_CLASSIFY_QUERIES,
    TOOL_INTERPRET_PAGE,
    TOOL_TEST_CHECKOUT_FLOW,
    TOOL_VALIDATE_SCHEMA,
    TOOL_COMPETITIVE_TEST,
    TOOL_RUN_MONITORING,
    TOOL_GENERATE_SCHEMA,
    TOOL_GENERATE_FAQ,
    TOOL_OPTIMIZE_FOR_QUERY,
    TOOL_ANALYZE_COMPETITORS,
    TOOL_GENERATE_CONTENT,
    TOOL_CHECK_AI_ENGINES,
    TOOL_TECHNICAL_AUDIT,
    TOOL_FIND_LINK_OPPORTUNITIES,
    # Trend Analyzer tools
    TOOL_FETCH_TRENDS,
    TOOL_GENERATE_WEEKLY_REPORT,
    TOOL_GET_SEASONAL_TOPICS,
    # Content Writer tools
    TOOL_ANALYZE_WRITING_STYLE,
    TOOL_WRITE_ARTICLE,
    TOOL_IMPROVE_DRAFT,
    TOOL_SUGGEST_PRODUCTS,
    # Settings Assistant tools
    TOOL_LIST_AGENTS,
    TOOL_EXPLAIN_AGENT,
    TOOL_SUGGEST_AGENT,
    TOOL_CREATE_WORKFLOW,
    TOOL_GET_LLM_HELP,
    TOOL_GET_STYLE_HELP,
    # Pharma Fact Checker tools
    TOOL_ANALYZE_PHARMA_CONTENT,
    TOOL_ENRICH_PHARMA_CONTENT,
    TOOL_CLASSIFY_CONTENT_TYPE,
    TOOL_FETCH_1177_INFO,
    # Product List Parser tools
    TOOL_PARSE_PRODUCT_CSV,
    TOOL_PARSE_EMAIL_PRODUCTS,
    TOOL_GENERATE_IMPORT_FORMAT,
    TOOL_VALIDATE_PRODUCTS,
]
