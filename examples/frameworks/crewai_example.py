"""
Example: Using CrewAI for SEO Analysis

This example shows how to use CrewAI for role-based multi-agent SEO workflows
with sequential task execution.
"""

from src.frameworks import (
    AgentConfig,
    FrameworkType,
    WorkflowConfig,
    get_framework,
)


def main():
    """Run CrewAI SEO analysis example."""

    # Initialize CrewAI framework
    framework = get_framework(
        FrameworkType.CREWAI,
        config={
            "llm_provider": "openai",
            "api_key": "sk-...",  # Your OpenAI API key
            "model": "gpt-4o",
            "temperature": 0.7,
        },
    )

    # Create SEO crew members with clear roles
    researcher_config = AgentConfig(
        name="SEO Researcher",
        role="Senior SEO Research Specialist",
        goal="Research SEO trends, keywords, and best practices",
        backstory="""You are a Senior SEO Research Specialist with 10+ years of experience.
        You excel at discovering emerging trends, high-value keywords, and competitive insights.
        Your research forms the foundation for successful SEO strategies.""",
        tools=["search", "google_trends", "keyword_tool"],
        verbose=True,
    )

    analyst_config = AgentConfig(
        name="SEO Analyst",
        role="SEO Data Analyst",
        goal="Analyze SEO data and identify optimization opportunities",
        backstory="""You are an expert SEO Data Analyst who transforms research into actionable insights.
        You analyze metrics, identify patterns, and prioritize optimization opportunities
        based on potential impact and effort required.""",
        tools=["analytics", "competitor_analyzer"],
        verbose=True,
    )

    strategist_config = AgentConfig(
        name="SEO Strategist",
        role="SEO Strategy Director",
        goal="Develop comprehensive SEO strategies",
        backstory="""You are a seasoned SEO Strategy Director who creates winning SEO campaigns.
        You synthesize research and analysis into clear, actionable strategies that drive
        organic traffic and improve search rankings.""",
        tools=["strategy_planner"],
        verbose=True,
    )

    writer_config = AgentConfig(
        name="Content Writer",
        role="SEO Content Writer",
        goal="Create SEO-optimized, high-quality content",
        backstory="""You are an expert SEO Content Writer who crafts engaging, optimized content.
        You balance search engine requirements with reader experience, creating content
        that ranks well and converts visitors.""",
        tools=["content_generator", "seo_optimizer"],
        verbose=True,
    )

    # Create CrewAI sequential workflow
    workflow_config = WorkflowConfig(
        name="SEO Content Strategy Crew",
        description="End-to-end SEO content strategy development",
        agents=[researcher_config, analyst_config, strategist_config, writer_config],
        tasks=[
            {
                "description": """Research the topic 'AI-powered SEO tools' and identify:
                - Top 20 relevant keywords with search volume
                - Current ranking content for these keywords
                - Emerging trends in the space
                - Content gaps and opportunities""",
                "agent": "SEO Researcher",
                "expected_output": "Comprehensive keyword and trend research report",
            },
            {
                "description": """Analyze the research findings and:
                - Prioritize keywords by potential impact
                - Identify quick wins vs long-term opportunities
                - Analyze competitor content strategies
                - Recommend content types and formats""",
                "agent": "SEO Analyst",
                "expected_output": "Prioritized SEO opportunities analysis",
            },
            {
                "description": """Develop a comprehensive SEO content strategy including:
                - Content calendar for next 3 months
                - Keyword targeting for each piece
                - Internal linking strategy
                - Content distribution plan""",
                "agent": "SEO Strategist",
                "expected_output": "Complete SEO content strategy document",
            },
            {
                "description": """Write a pillar article on 'AI-powered SEO tools' that:
                - Targets primary and secondary keywords naturally
                - Includes 2000+ words of valuable content
                - Features proper heading structure (H1, H2, H3)
                - Incorporates relevant internal/external links
                - Optimizes for featured snippets""",
                "agent": "Content Writer",
                "expected_output": "SEO-optimized pillar article",
            },
        ],
        max_iterations=15,
        cache_results=True,
    )

    workflow = framework.create_workflow(workflow_config)

    # Execute CrewAI crew
    result = framework.execute_workflow(
        workflow,
        inputs={
            "topic": "AI-powered SEO tools",
            "target_audience": "digital marketers and SEO professionals",
            "content_type": "pillar content",
            "primary_keyword": "AI SEO tools",
            "secondary_keywords": [
                "automated SEO",
                "AI content optimization",
                "machine learning SEO",
            ],
        },
    )

    # Print results
    if result.success:
        print("✓ CrewAI crew completed their mission!")
        print(f"\nProcess: {result.output['process']}")

        print(f"\nTask Results:")
        for i, task_result in enumerate(result.output["task_results"], 1):
            print(f"\n{i}. {task_result['task']}")
            print(f"   Agent: {task_result['agent_role']}")
            print(f"   Status: {'✓ Completed' if task_result['success'] else '✗ Failed'}")
    else:
        print(f"✗ Crew mission failed: {result.error}")

    # Get metrics
    metrics = framework.get_metrics()
    print(f"\nCrew Performance:")
    print(f"- Total missions: {metrics['total_executions']}")
    print(f"- Success rate: {metrics['successful_executions']}/{metrics['total_executions']}")


if __name__ == "__main__":
    main()
