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

# All agents for easy iteration
ALL_AGENTS = [
    SEO_ANALYST_AGENT,
    AGENT_TESTER_AGENT,
    MONITORING_AGENT,
    OPTIMIZER_AGENT,
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
]
