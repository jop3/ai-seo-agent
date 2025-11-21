"""
Predefined workflows for common SEO analysis scenarios.

Each workflow defines a sequence of agent tasks with dependencies
and parallel execution groups.
"""

from src.models.agents import AgentType
from src.orchestrator.engine import Workflow


# =============================================================================
# Full Comprehensive Audit
# =============================================================================
FULL_AUDIT_WORKFLOW = Workflow(
    id="full_audit",
    name="Full SEO Audit",
    description="Comprehensive analysis using all agents - best for monthly reviews",
    steps=[
        # Phase 1: Data Collection (parallel)
        {
            "agent_type": AgentType.MONITORING.value,
            "task_type": "check_traffic_anomalies",
            "name": "traffic_check",
            "description": "Check for traffic anomalies",
            "parallel_group": "phase1_data",
        },
        {
            "agent_type": AgentType.SERP_FEATURES.value,
            "task_type": "analyze_serp_landscape",
            "name": "serp_analysis",
            "description": "Analyze SERP features and AIO presence",
            "parallel_group": "phase1_data",
        },
        {
            "agent_type": AgentType.MULTI_ENGINE_TRACKER.value,
            "task_type": "check_all_engines",
            "name": "multi_engine_check",
            "description": "Check presence across AI engines",
            "parallel_group": "phase1_data",
        },
        {
            "agent_type": AgentType.COMPETITOR_MONITOR.value,
            "task_type": "full_competitor_analysis",
            "name": "competitor_analysis",
            "description": "Analyze competitor performance",
            "parallel_group": "phase1_data",
        },
        # Phase 2: Technical Analysis (parallel, after phase 1)
        {
            "agent_type": AgentType.TECHNICAL_AUDITOR.value,
            "task_type": "full_audit",
            "name": "technical_audit",
            "description": "Full technical SEO audit",
            "depends_on": ["traffic_check"],
            "parallel_group": "phase2_technical",
        },
        {
            "agent_type": AgentType.LINK_ANALYZER.value,
            "task_type": "full_link_audit",
            "name": "link_audit",
            "description": "Comprehensive link analysis",
            "depends_on": ["traffic_check"],
            "parallel_group": "phase2_technical",
        },
        {
            "agent_type": AgentType.SCHEMA_GENERATOR.value,
            "task_type": "audit_existing_schema",
            "name": "schema_audit",
            "description": "Audit existing schema markup",
            "depends_on": ["traffic_check"],
            "parallel_group": "phase2_technical",
        },
        # Phase 3: Content Analysis (parallel, after phase 1)
        {
            "agent_type": AgentType.CONTENT_DECAY.value,
            "task_type": "full_decay_analysis",
            "name": "content_decay",
            "description": "Identify decaying content",
            "depends_on": ["traffic_check"],
            "parallel_group": "phase3_content",
        },
        {
            "agent_type": AgentType.EEAT_ANALYZER.value,
            "task_type": "full_eeat_audit",
            "name": "eeat_audit",
            "description": "E-E-A-T signals analysis",
            "depends_on": ["traffic_check"],
            "parallel_group": "phase3_content",
        },
        {
            "agent_type": AgentType.AI_CONTENT_ANALYZER.value,
            "task_type": "analyze_site_content",
            "name": "ai_content_check",
            "description": "Check for AI content patterns",
            "depends_on": ["traffic_check"],
            "parallel_group": "phase3_content",
            "optional": True,
        },
        # Phase 4: Predictive & Strategic (after technical and content)
        {
            "agent_type": AgentType.PREDICTIVE_SEO.value,
            "task_type": "trend_analysis",
            "name": "predictive_analysis",
            "description": "Forecast trends and identify opportunities",
            "depends_on": ["content_decay", "traffic_check"],
        },
        # Phase 5: Generate Recommendations (after all analysis)
        {
            "agent_type": AgentType.OPTIMIZATION_RECOMMENDER.value,
            "task_type": "generate_recommendations",
            "name": "optimization_recs",
            "description": "Generate prioritized recommendations",
            "depends_on": [
                "technical_audit",
                "link_audit",
                "content_decay",
                "eeat_audit",
                "predictive_analysis",
            ],
        },
    ],
)


# =============================================================================
# Quick Daily Check
# =============================================================================
QUICK_CHECK_WORKFLOW = Workflow(
    id="quick_check",
    name="Quick SEO Check",
    description="Fast daily check for critical issues - 5 minute runtime",
    steps=[
        {
            "agent_type": AgentType.MONITORING.value,
            "task_type": "check_traffic_anomalies",
            "name": "traffic_check",
            "description": "Check for traffic drops",
            "parameters": {"threshold_percent": 20},
            "parallel_group": "quick",
        },
        {
            "agent_type": AgentType.SERP_FEATURES.value,
            "task_type": "check_aio_status",
            "name": "aio_check",
            "description": "Check AIO presence for top queries",
            "parameters": {"query_limit": 20},
            "parallel_group": "quick",
        },
        {
            "agent_type": AgentType.TECHNICAL_AUDITOR.value,
            "task_type": "check_critical_issues",
            "name": "critical_tech_check",
            "description": "Check for critical technical issues",
            "parameters": {"max_pages": 50},
            "parallel_group": "quick",
        },
    ],
)


# =============================================================================
# Content-Focused Workflow
# =============================================================================
CONTENT_WORKFLOW = Workflow(
    id="content_analysis",
    name="Content Analysis",
    description="Deep content analysis for content teams",
    steps=[
        {
            "agent_type": AgentType.CONTENT_DECAY.value,
            "task_type": "full_decay_analysis",
            "name": "decay_analysis",
            "description": "Find content that needs refreshing",
        },
        {
            "agent_type": AgentType.EEAT_ANALYZER.value,
            "task_type": "full_eeat_audit",
            "name": "eeat_audit",
            "description": "Analyze E-E-A-T signals",
            "depends_on": ["decay_analysis"],
            "parallel_group": "content_quality",
        },
        {
            "agent_type": AgentType.AI_CONTENT_ANALYZER.value,
            "task_type": "analyze_site_content",
            "name": "ai_detection",
            "description": "Detect AI-generated content patterns",
            "depends_on": ["decay_analysis"],
            "parallel_group": "content_quality",
        },
        {
            "agent_type": AgentType.SCHEMA_GENERATOR.value,
            "task_type": "recommend_content_schema",
            "name": "schema_recommendations",
            "description": "Recommend schema for content",
            "depends_on": ["eeat_audit"],
        },
        {
            "agent_type": AgentType.CONTENT_GENERATOR.value,
            "task_type": "generate_refresh_plan",
            "name": "refresh_plan",
            "description": "Generate content refresh plan",
            "depends_on": ["decay_analysis", "eeat_audit"],
        },
    ],
)


# =============================================================================
# Technical SEO Workflow
# =============================================================================
TECHNICAL_WORKFLOW = Workflow(
    id="technical_analysis",
    name="Technical SEO Analysis",
    description="Deep technical audit for development teams",
    steps=[
        {
            "agent_type": AgentType.TECHNICAL_AUDITOR.value,
            "task_type": "full_audit",
            "name": "full_tech_audit",
            "description": "Comprehensive technical audit",
        },
        {
            "agent_type": AgentType.LINK_ANALYZER.value,
            "task_type": "full_link_audit",
            "name": "link_audit",
            "description": "Internal and external link analysis",
            "depends_on": ["full_tech_audit"],
            "parallel_group": "tech_details",
        },
        {
            "agent_type": AgentType.SCHEMA_GENERATOR.value,
            "task_type": "audit_existing_schema",
            "name": "schema_audit",
            "description": "Schema markup audit",
            "depends_on": ["full_tech_audit"],
            "parallel_group": "tech_details",
        },
        {
            "agent_type": AgentType.MULTI_PLATFORM_SEO.value,
            "task_type": "voice_search_readiness",
            "name": "voice_readiness",
            "description": "Voice search optimization check",
            "depends_on": ["full_tech_audit"],
            "parallel_group": "tech_details",
            "optional": True,
        },
    ],
)


# =============================================================================
# Competitive Analysis Workflow
# =============================================================================
COMPETITIVE_WORKFLOW = Workflow(
    id="competitive_analysis",
    name="Competitive Analysis",
    description="Deep competitor analysis",
    steps=[
        {
            "agent_type": AgentType.COMPETITOR_MONITOR.value,
            "task_type": "full_competitor_analysis",
            "name": "competitor_overview",
            "description": "Full competitor analysis",
        },
        {
            "agent_type": AgentType.SERP_FEATURES.value,
            "task_type": "analyze_competitor_serp",
            "name": "competitor_serp",
            "description": "Competitor SERP feature analysis",
            "depends_on": ["competitor_overview"],
            "parallel_group": "comp_details",
        },
        {
            "agent_type": AgentType.LINK_ANALYZER.value,
            "task_type": "analyze_competitor_backlinks",
            "name": "competitor_links",
            "description": "Competitor backlink analysis",
            "depends_on": ["competitor_overview"],
            "parallel_group": "comp_details",
        },
        {
            "agent_type": AgentType.MULTI_ENGINE_TRACKER.value,
            "task_type": "compare_ai_visibility",
            "name": "ai_visibility_compare",
            "description": "Compare AI engine visibility",
            "depends_on": ["competitor_overview"],
            "parallel_group": "comp_details",
        },
    ],
)


# =============================================================================
# Local SEO Workflow
# =============================================================================
LOCAL_SEO_WORKFLOW = Workflow(
    id="local_seo",
    name="Local SEO Analysis",
    description="Local business SEO optimization",
    steps=[
        {
            "agent_type": AgentType.LOCAL_SEO.value,
            "task_type": "audit_nap_consistency",
            "name": "nap_audit",
            "description": "NAP consistency check",
        },
        {
            "agent_type": AgentType.LOCAL_SEO.value,
            "task_type": "analyze_local_serp",
            "name": "local_serp",
            "description": "Local SERP analysis",
            "depends_on": ["nap_audit"],
            "parallel_group": "local_details",
        },
        {
            "agent_type": AgentType.LOCAL_SEO.value,
            "task_type": "audit_gbp_optimization",
            "name": "gbp_audit",
            "description": "Google Business Profile audit",
            "depends_on": ["nap_audit"],
            "parallel_group": "local_details",
        },
        {
            "agent_type": AgentType.SCHEMA_GENERATOR.value,
            "task_type": "generate_local_schema",
            "name": "local_schema",
            "description": "Generate LocalBusiness schema",
            "depends_on": ["nap_audit"],
            "parallel_group": "local_details",
        },
    ],
)


# =============================================================================
# AI Readiness Workflow
# =============================================================================
AI_READINESS_WORKFLOW = Workflow(
    id="ai_readiness",
    name="AI Search Readiness",
    description="Optimize for AI-powered search engines",
    steps=[
        {
            "agent_type": AgentType.SERP_FEATURES.value,
            "task_type": "analyze_serp_landscape",
            "name": "serp_landscape",
            "description": "Current SERP and AIO analysis",
        },
        {
            "agent_type": AgentType.MULTI_ENGINE_TRACKER.value,
            "task_type": "check_all_engines",
            "name": "ai_engine_presence",
            "description": "Check presence in AI engines",
            "depends_on": ["serp_landscape"],
        },
        {
            "agent_type": AgentType.SCHEMA_GENERATOR.value,
            "task_type": "optimize_for_ai",
            "name": "ai_schema",
            "description": "Schema optimization for AI",
            "depends_on": ["ai_engine_presence"],
            "parallel_group": "ai_optimize",
        },
        {
            "agent_type": AgentType.EEAT_ANALYZER.value,
            "task_type": "full_eeat_audit",
            "name": "eeat_for_ai",
            "description": "E-E-A-T for AI citation",
            "depends_on": ["ai_engine_presence"],
            "parallel_group": "ai_optimize",
        },
        {
            "agent_type": AgentType.MULTI_PLATFORM_SEO.value,
            "task_type": "voice_search_readiness",
            "name": "voice_search",
            "description": "Voice search optimization",
            "depends_on": ["ai_engine_presence"],
            "parallel_group": "ai_optimize",
        },
    ],
)


# =============================================================================
# AI Visibility Audit (Inspired by Swedish AI visibility service)
# =============================================================================
AI_VISIBILITY_AUDIT_WORKFLOW = Workflow(
    id="ai_visibility_audit",
    name="AI Visibility Audit (Synlighetsgranskning)",
    description="Comprehensive brand presence analysis across all major AI assistants",
    steps=[
        # Phase 1: AI Engine Presence Analysis
        {
            "agent_type": AgentType.MULTI_ENGINE_TRACKER.value,
            "task_type": "check_all_engines",
            "name": "ai_engine_scan",
            "description": "Scan ChatGPT, Claude, Gemini, Perplexity for brand presence",
            "parameters": {
                "engines": ["chatgpt", "claude", "gemini", "perplexity", "bing_copilot"],
                "track_brand_mentions": True,
            },
        },
        # Phase 2: Competitive Positioning (parallel after phase 1)
        {
            "agent_type": AgentType.COMPETITOR_MONITOR.value,
            "task_type": "full_competitor_analysis",
            "name": "competitor_ai_presence",
            "description": "Compare brand vs competitor presence in AI",
            "depends_on": ["ai_engine_scan"],
            "parallel_group": "analysis",
        },
        {
            "agent_type": AgentType.SERP_FEATURES.value,
            "task_type": "analyze_serp_landscape",
            "name": "aio_citation_analysis",
            "description": "Analyze AI Overview citations and ranking",
            "depends_on": ["ai_engine_scan"],
            "parallel_group": "analysis",
        },
        # Phase 3: Authority & Trust Assessment
        {
            "agent_type": AgentType.EEAT_ANALYZER.value,
            "task_type": "full_eeat_audit",
            "name": "authority_assessment",
            "description": "E-E-A-T signals for AI trust/authority",
            "depends_on": ["competitor_ai_presence", "aio_citation_analysis"],
        },
        # Phase 4: Optimization Opportunities (parallel)
        {
            "agent_type": AgentType.SCHEMA_GENERATOR.value,
            "task_type": "optimize_for_ai",
            "name": "knowledge_graph_optimization",
            "description": "Schema optimization for knowledge graphs",
            "depends_on": ["authority_assessment"],
            "parallel_group": "optimization",
        },
        {
            "agent_type": AgentType.AI_CONTENT_ANALYZER.value,
            "task_type": "analyze_site_content",
            "name": "content_ai_readiness",
            "description": "Content structure and semantic SEO analysis",
            "depends_on": ["authority_assessment"],
            "parallel_group": "optimization",
        },
        {
            "agent_type": AgentType.MULTI_PLATFORM_SEO.value,
            "task_type": "voice_search_readiness",
            "name": "semantic_optimization",
            "description": "Voice search and semantic SEO optimization",
            "depends_on": ["authority_assessment"],
            "parallel_group": "optimization",
        },
        # Phase 5: Strategic Recommendations
        {
            "agent_type": AgentType.OPTIMIZATION_RECOMMENDER.value,
            "task_type": "generate_recommendations",
            "name": "ai_visibility_strategy",
            "description": "Strategic actions for AI visibility improvement",
            "depends_on": [
                "knowledge_graph_optimization",
                "content_ai_readiness",
                "semantic_optimization",
            ],
        },
    ],
)


# =============================================================================
# Workflow Registry
# =============================================================================
WORKFLOWS: dict[str, Workflow] = {
    "full_audit": FULL_AUDIT_WORKFLOW,
    "quick_check": QUICK_CHECK_WORKFLOW,
    "content": CONTENT_WORKFLOW,
    "technical": TECHNICAL_WORKFLOW,
    "competitive": COMPETITIVE_WORKFLOW,
    "local_seo": LOCAL_SEO_WORKFLOW,
    "ai_readiness": AI_READINESS_WORKFLOW,
    "ai_visibility_audit": AI_VISIBILITY_AUDIT_WORKFLOW,
}


def get_workflow(workflow_id: str) -> Workflow | None:
    """Get a workflow by ID."""
    return WORKFLOWS.get(workflow_id)


def list_workflows() -> list[dict[str, str]]:
    """List all available workflows."""
    return [
        {
            "id": w.id,
            "name": w.name,
            "description": w.description,
            "steps": len(w.steps),
        }
        for w in WORKFLOWS.values()
    ]
