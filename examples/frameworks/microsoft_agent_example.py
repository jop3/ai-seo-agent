"""
Example: Using Microsoft Agent Framework for SEO Analysis

This example shows how to use Microsoft's Agent Framework (Semantic Kernel + AutoGen)
with Azure OpenAI for enterprise SEO workflows.
"""

from src.frameworks import (
    AgentConfig,
    FrameworkType,
    WorkflowConfig,
    get_framework,
)


def main():
    """Run Microsoft Agent Framework SEO analysis example."""

    # Initialize Microsoft Agent Framework
    framework = get_framework(
        FrameworkType.MICROSOFT_AGENT,
        config={
            "azure_endpoint": "https://myorg.openai.azure.com",
            "api_key": "your-azure-openai-key",
            "deployment": "gpt-4o",
            "api_version": "2024-02-01",
        },
    )

    # Create SEO agents with Semantic Kernel integration
    technical_seo_config = AgentConfig(
        name="Technical SEO Specialist",
        role="Technical SEO Expert",
        goal="Identify and fix technical SEO issues",
        backstory="Expert in website architecture, crawling, and indexing",
        tools=["site_crawler", "schema_validator", "core_web_vitals"],
        llm_config={
            "temperature": 0.6,
        },
        memory=True,
        verbose=True,
    )

    content_seo_config = AgentConfig(
        name="Content SEO Specialist",
        role="Content Optimization Expert",
        goal="Optimize content for search engines and users",
        backstory="Specialist in on-page SEO and content strategy",
        tools=["content_analyzer", "keyword_density", "readability"],
        llm_config={
            "temperature": 0.7,
        },
        memory=True,
        verbose=True,
    )

    link_building_config = AgentConfig(
        name="Link Building Specialist",
        role="Off-Page SEO Expert",
        goal="Develop link building strategies",
        backstory="Expert in backlink analysis and outreach",
        tools=["backlink_checker", "domain_authority", "competitor_analysis"],
        llm_config={
            "temperature": 0.8,
        },
        memory=True,
        verbose=True,
    )

    # Create AutoGen GroupChat workflow
    workflow_config = WorkflowConfig(
        name="Enterprise SEO Audit",
        description="Comprehensive SEO audit with multiple specialists",
        agents=[technical_seo_config, content_seo_config, link_building_config],
        tasks=[
            {
                "description": "Perform technical SEO audit and identify issues",
                "agent": "Technical SEO Specialist",
            },
            {
                "description": "Analyze content quality and optimization opportunities",
                "agent": "Content SEO Specialist",
            },
            {
                "description": "Evaluate backlink profile and suggest strategies",
                "agent": "Link Building Specialist",
            },
        ],
        max_iterations=12,
        cache_results=True,
    )

    workflow = framework.create_workflow(workflow_config)

    # Execute workflow
    result = framework.execute_workflow(
        workflow,
        inputs={
            "domain": "example.com",
            "competitors": ["competitor1.com", "competitor2.com"],
            "target_markets": ["North America", "Europe"],
        },
    )

    # Print results
    if result.success:
        print("✓ Microsoft Agent Framework workflow completed!")
        print(f"\nConversation History:")
        for msg in result.output.get("conversation_history", []):
            print(f"\n{msg['speaker']}:")
            print(f"  {msg['message']}")

        print(f"\nTask Results:")
        for task_result in result.output["task_results"]:
            print(f"\n- {task_result['task']}")
            print(f"  Agent: {task_result['agent']}")
            print(f"  Status: {'✓' if task_result['success'] else '✗'}")
    else:
        print(f"✗ Workflow failed: {result.error}")


if __name__ == "__main__":
    main()
