"""
Example: Using Google Agent Development Kit (ADK) for SEO Analysis

This example shows how to use Google ADK with Vertex AI for SEO analysis.
"""

from src.frameworks import (
    AgentConfig,
    FrameworkType,
    WorkflowConfig,
    get_framework,
)


def main():
    """Run Google ADK SEO analysis example."""

    # Initialize Google ADK framework
    framework = get_framework(
        FrameworkType.GOOGLE_ADK,
        config={
            "project_id": "my-gcp-project",
            "location": "us-central1",
            "credentials_path": "/path/to/service-account.json",  # Optional
        },
    )

    # Create SEO analysis agents
    analyzer_config = AgentConfig(
        name="SEO Analyzer",
        role="SEO Performance Analyst",
        goal="Analyze website SEO metrics and identify issues",
        backstory="Expert SEO analyst with deep knowledge of technical SEO",
        tools=["search", "web_scraper", "analytics"],
        llm_config={
            "model": "gemini-2.0-flash-exp",
            "temperature": 0.7,
        },
        memory=True,
        verbose=True,
    )

    optimizer_config = AgentConfig(
        name="SEO Optimizer",
        role="SEO Optimization Specialist",
        goal="Generate actionable SEO improvement recommendations",
        backstory="Specialist in on-page and technical SEO optimization",
        tools=["content_analyzer", "keyword_research"],
        llm_config={
            "model": "gemini-2.0-flash-exp",
            "temperature": 0.8,
        },
        memory=True,
        verbose=True,
    )

    # Create workflow
    workflow_config = WorkflowConfig(
        name="SEO Analysis Pipeline",
        description="Complete SEO analysis and optimization workflow",
        agents=[analyzer_config, optimizer_config],
        tasks=[
            {
                "description": "Analyze current SEO performance and identify issues",
                "agent": "SEO Analyzer",
            },
            {
                "description": "Generate optimization recommendations based on analysis",
                "agent": "SEO Optimizer",
            },
        ],
        max_iterations=10,
        cache_results=True,
    )

    workflow = framework.create_workflow(workflow_config)

    # Execute workflow
    result = framework.execute_workflow(
        workflow,
        inputs={
            "url": "https://example.com",
            "target_keywords": ["AI SEO", "automated optimization", "content analysis"],
        },
    )

    # Print results
    if result.success:
        print("✓ Workflow completed successfully!")
        print(f"\nResults:")
        for task_result in result.output["task_results"]:
            print(f"\n- {task_result['task']}")
            print(f"  Agent: {task_result['agent']}")
            print(f"  Success: {task_result['success']}")
    else:
        print(f"✗ Workflow failed: {result.error}")

    # Get metrics
    metrics = framework.get_metrics()
    print(f"\nMetrics:")
    print(f"- Total executions: {metrics['total_executions']}")
    print(f"- Success rate: {metrics['successful_executions']}/{metrics['total_executions']}")
    print(f"- Average duration: {metrics['average_duration_ms']:.2f}ms")


if __name__ == "__main__":
    main()
