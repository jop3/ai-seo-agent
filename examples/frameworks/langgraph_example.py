"""
Example: Using LangGraph for SEO Analysis

This example shows how to use LangGraph with state management for SEO workflows.
"""

from src.frameworks import (
    AgentConfig,
    FrameworkType,
    WorkflowConfig,
    get_framework,
)


def main():
    """Run LangGraph SEO analysis example."""

    # Initialize LangGraph framework
    framework = get_framework(
        FrameworkType.LANGGRAPH,
        config={
            "llm_provider": "openai",
            "api_key": "sk-...",  # Your OpenAI API key
            "checkpointer": {
                "type": "memory",  # or "redis" for production
            },
        },
    )

    # Create SEO agents with graph-based workflow
    researcher_config = AgentConfig(
        name="Keyword Researcher",
        role="SEO Keyword Research Specialist",
        goal="Discover high-value keywords and search trends",
        backstory="Expert in keyword research and competitive analysis",
        tools=["google_trends", "keyword_planner", "serp_analyzer"],
        llm_config={
            "model": "gpt-4o",
            "temperature": 0.6,
        },
        memory=True,
    )

    analyst_config = AgentConfig(
        name="Content Analyst",
        role="Content Quality Analyst",
        goal="Analyze content quality and relevance",
        backstory="Specialist in content analysis and optimization",
        tools=["readability_checker", "content_scorer"],
        llm_config={
            "model": "gpt-4o",
            "temperature": 0.7,
        },
        memory=True,
    )

    writer_config = AgentConfig(
        name="Content Writer",
        role="SEO Content Writer",
        goal="Create SEO-optimized content",
        backstory="Expert content writer with SEO expertise",
        tools=["content_generator", "seo_optimizer"],
        llm_config={
            "model": "gpt-4o",
            "temperature": 0.8,
        },
        memory=True,
    )

    # Create LangGraph workflow with state management
    workflow_config = WorkflowConfig(
        name="SEO Content Creation Pipeline",
        description="Multi-stage SEO content creation with state tracking",
        agents=[researcher_config, analyst_config, writer_config],
        tasks=[
            {
                "description": "Research keywords and identify opportunities",
                "agent": "Keyword Researcher",
            },
            {
                "description": "Analyze existing content and competition",
                "agent": "Content Analyst",
            },
            {
                "description": "Write optimized content based on research",
                "agent": "Content Writer",
            },
        ],
        max_iterations=15,
        cache_results=True,
    )

    workflow = framework.create_workflow(workflow_config)

    # Execute workflow with state
    result = framework.execute_workflow(
        workflow,
        inputs={
            "topic": "AI-powered SEO automation",
            "target_audience": "digital marketers",
            "word_count": 1500,
            "keywords": ["AI SEO", "automation", "content optimization"],
        },
    )

    # Print results
    if result.success:
        print("✓ LangGraph workflow completed!")
        print(f"\nFinal State:")
        final_state = result.output.get("final_state", {})
        for key, value in final_state.items():
            print(f"  {key}: {value}")

        print(f"\nNode Results:")
        for node_result in result.output["node_results"]:
            print(f"\n- {node_result['description']}")
            print(f"  Agent: {node_result['agent']}")
            print(f"  Status: {'✓' if node_result['success'] else '✗'}")
    else:
        print(f"✗ Workflow failed: {result.error}")


if __name__ == "__main__":
    main()
