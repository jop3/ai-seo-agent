"""
Example: Using AWS Bedrock AgentCore for SEO Analysis

This example shows how to use AWS Bedrock AgentCore with Memory, Gateway,
and Observability for production SEO workflows.
"""

from src.frameworks import (
    AgentConfig,
    DeploymentConfig,
    FrameworkType,
    WorkflowConfig,
    get_framework,
)


def main():
    """Run AWS Bedrock AgentCore SEO analysis example."""

    # Initialize AWS Bedrock AgentCore
    framework = get_framework(
        FrameworkType.AWS_BEDROCK,
        config={
            "region": "us-east-1",
            "memory_backend": "dynamodb",  # or "opensearch", "s3"
            "gateway_enabled": True,
        },
    )

    # Create Bedrock agents with action groups
    seo_auditor_config = AgentConfig(
        name="SEO Auditor",
        role="Comprehensive SEO Auditor",
        goal="Perform complete SEO audits",
        backstory="Expert auditor with knowledge of all SEO aspects",
        tools=["bedrock-kb", "lambda-crawler", "s3-reports"],
        llm_config={
            "model_id": "anthropic.claude-3-5-sonnet-20241022-v2:0",
            "temperature": 0.7,
        },
        memory=True,
        verbose=True,
    )

    competitor_analyst_config = AgentConfig(
        name="Competitor Analyst",
        role="Competitive Intelligence Analyst",
        goal="Analyze competitor SEO strategies",
        backstory="Specialist in competitive analysis and market intelligence",
        tools=["bedrock-kb", "lambda-scraper"],
        llm_config={
            "model_id": "anthropic.claude-3-5-sonnet-20241022-v2:0",
            "temperature": 0.6,
        },
        memory=True,
        verbose=True,
    )

    # Create Bedrock workflow with Step Functions
    workflow_config = WorkflowConfig(
        name="Production SEO Analysis",
        description="Scalable SEO analysis with AWS Bedrock",
        agents=[seo_auditor_config, competitor_analyst_config],
        tasks=[
            {
                "description": "Audit website SEO and generate report",
                "agent": "SEO Auditor",
            },
            {
                "description": "Analyze top 10 competitors",
                "agent": "Competitor Analyst",
            },
        ],
        max_iterations=10,
        cache_results=True,
    )

    workflow = framework.create_workflow(workflow_config)

    # Execute workflow with session management
    result = framework.execute_workflow(
        workflow,
        inputs={
            "url": "https://example.com",
            "session_id": "audit-2024-01-15",
            "competitors": [
                "competitor1.com",
                "competitor2.com",
                "competitor3.com",
            ],
        },
    )

    # Print results
    if result.success:
        print("✓ AWS Bedrock workflow completed!")
        print(f"\nSession ID: {result.metadata['workflow_name']}")
        print(f"Region: {result.metadata['region']}")

        print(f"\nTask Results:")
        for task_result in result.output["task_results"]:
            print(f"\n- {task_result['task']}")
            print(f"  Agent: {task_result['agent']}")
            print(f"  Status: {'✓' if task_result['success'] else '✗'}")
    else:
        print(f"✗ Workflow failed: {result.error}")

    # Deploy to AWS (optional)
    print("\n--- Deployment ---")
    deployment_url = framework.deploy(
        DeploymentConfig(
            target="aws",
            region="us-east-1",
            credentials={"account_id": "123456789012"},
        )
    )
    print(f"Deployment URL: {deployment_url}")


if __name__ == "__main__":
    main()
