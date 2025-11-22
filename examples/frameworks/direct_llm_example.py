"""
Example: Using Direct LLM (No Framework) for SEO Analysis

This example shows the simplest approach - direct LLM API calls without
any agent framework. Best for simple workflows and rapid prototyping.
"""

from src.frameworks import (
    AgentConfig,
    FrameworkType,
    WorkflowConfig,
    get_framework,
)


def main():
    """Run Direct LLM SEO analysis example."""

    # Example 1: OpenAI
    print("=== Example 1: OpenAI ===\n")
    framework_openai = get_framework(
        FrameworkType.DIRECT_LLM,
        config={
            "llm_provider": "openai",
            "api_key": "sk-...",
            "model": "gpt-4o",
            "temperature": 0.7,
        },
    )

    # Example 2: Docker Model Runner (Free!)
    print("=== Example 2: Docker Model Runner (Free) ===\n")
    framework_docker = get_framework(
        FrameworkType.DIRECT_LLM,
        config={
            "llm_provider": "docker_model_runner",
            "endpoint": "http://localhost:8080/v1",
            "model": "phi3-mini-4k-instruct",
            "temperature": 0.7,
        },
    )

    # Example 3: Ollama (Free!)
    print("=== Example 3: Ollama (Free) ===\n")
    framework_ollama = get_framework(
        FrameworkType.DIRECT_LLM,
        config={
            "llm_provider": "ollama",
            "endpoint": "http://localhost:11434",
            "model": "llama3.2:3b",
            "temperature": 0.7,
        },
    )

    # For this example, we'll use OpenAI
    framework = framework_openai

    # Create simple SEO agents
    analyzer_config = AgentConfig(
        name="SEO Analyzer",
        role="SEO analyst",
        goal="Analyze website SEO",
        tools=[],  # No tools needed for simple analysis
    )

    reporter_config = AgentConfig(
        name="SEO Reporter",
        role="report generator",
        goal="Generate SEO reports",
        tools=[],
    )

    # Create simple sequential workflow
    workflow_config = WorkflowConfig(
        name="Simple SEO Analysis",
        description="Basic SEO analysis with direct LLM calls",
        agents=[analyzer_config, reporter_config],
        tasks=[
            {
                "description": "Analyze SEO for the given URL and list top 5 issues",
                "agent": "SEO Analyzer",
            },
            {
                "description": "Create a summary report of the SEO analysis",
                "agent": "SEO Reporter",
            },
        ],
    )

    workflow = framework.create_workflow(workflow_config)

    # Execute workflow
    result = framework.execute_workflow(
        workflow,
        inputs={
            "url": "https://example.com",
        },
    )

    # Print results
    if result.success:
        print("✓ Direct LLM workflow completed!")

        print(f"\nTask Results:")
        for task_result in result.output["task_results"]:
            print(f"\n- {task_result['task']}")
            print(f"  Agent: {task_result['agent']}")
            print(f"  Status: {'✓' if task_result['success'] else '✗'}")
    else:
        print(f"✗ Workflow failed: {result.error}")

    # Get metrics
    metrics = framework.get_metrics()
    print(f"\nPerformance:")
    print(f"- Executions: {metrics['total_executions']}")
    print(f"- Success rate: {metrics['successful_executions']}/{metrics['total_executions']}")
    print(f"- Avg duration: {metrics['average_duration_ms']:.2f}ms")


def simple_agent_example():
    """Example: Single agent execution without workflow."""

    print("\n\n=== Simple Agent Example (No Workflow) ===\n")

    # Initialize with Docker Model Runner (free!)
    framework = get_framework(
        FrameworkType.DIRECT_LLM,
        config={
            "llm_provider": "docker_model_runner",
            "endpoint": "http://localhost:8080/v1",
            "model": "phi3-mini-4k-instruct",
        },
    )

    # Create single agent
    agent_config = AgentConfig(
        name="Quick SEO Check",
        role="SEO checker",
        goal="Quick SEO analysis",
    )

    agent = framework.create_agent(agent_config)

    # Execute single task
    result = framework.execute_agent(
        agent,
        task={
            "description": "List 3 most important SEO factors for e-commerce sites",
            "context": {},
        },
    )

    if result.success:
        print("✓ Agent completed task!")
        print(f"\nResult: {result.output['result']}")
    else:
        print(f"✗ Task failed: {result.error}")


def cost_comparison():
    """Show cost comparison of different LLM providers."""

    print("\n\n=== Cost Comparison ===\n")

    configs = {
        "Docker Model Runner": {
            "provider": "docker_model_runner",
            "model": "phi3-mini-4k-instruct",
            "cost_per_1k": "$0.00",
        },
        "Ollama": {
            "provider": "ollama",
            "model": "llama3.2:3b",
            "cost_per_1k": "$0.00",
        },
        "OpenAI GPT-4": {
            "provider": "openai",
            "model": "gpt-4o",
            "cost_per_1k": "$0.015 (input) + $0.060 (output)",
        },
        "Anthropic Claude": {
            "provider": "anthropic",
            "model": "claude-3-5-sonnet-20241022",
            "cost_per_1k": "$0.003 (input) + $0.015 (output)",
        },
    }

    print("LLM Provider Cost Comparison (per 1K tokens):\n")
    for name, config in configs.items():
        print(f"- {name}: {config['cost_per_1k']}")

    print("\nFor 1M tokens per month:")
    print("- Docker Model Runner: $0/month (FREE!)")
    print("- Ollama: $0/month (FREE!)")
    print("- OpenAI GPT-4: ~$75/month")
    print("- Anthropic Claude: ~$18/month")


if __name__ == "__main__":
    main()
    simple_agent_example()
    cost_comparison()
