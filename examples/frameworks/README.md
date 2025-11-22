# Agent Framework Examples

This directory contains examples for each supported agent framework.

## 🚀 Quick Start

Each example is standalone and can be run independently:

```bash
# Install dependencies first
pip install -r requirements.txt

# Run any example
python examples/frameworks/google_adk_example.py
python examples/frameworks/langgraph_example.py
python examples/frameworks/microsoft_agent_example.py
python examples/frameworks/aws_bedrock_example.py
python examples/frameworks/crewai_example.py
python examples/frameworks/direct_llm_example.py
```

## 📋 Framework Comparison

| Framework | Best For | Deployment | Cost | Learning Curve |
|-----------|----------|------------|------|----------------|
| **Direct LLM** | Simple workflows, prototyping | Any platform | Provider-dependent | ⭐ Easy |
| **Google ADK** | Google Cloud users, Gemini models | Vertex AI | Pay-per-use | ⭐⭐ Medium |
| **LangGraph** | Complex state management, graphs | LangGraph Cloud | Pay-per-use | ⭐⭐⭐ Advanced |
| **Microsoft** | Enterprise, Azure users | Azure | Pay-per-use | ⭐⭐⭐ Advanced |
| **AWS Bedrock** | AWS users, production scale | AWS | Pay-per-use | ⭐⭐⭐ Advanced |
| **CrewAI** | Role-based collaboration | Docker, K8s | Provider-dependent | ⭐⭐ Medium |

## 🎯 When to Use Each Framework

### Direct LLM (`direct_llm_example.py`)
**Use when:**
- You need simple, sequential workflows
- You want rapid prototyping
- You want to minimize dependencies
- You need platform flexibility

**Features:**
- ✓ No framework overhead
- ✓ Works with any LLM provider
- ✓ Simplest to understand
- ✓ Easiest to debug

### Google ADK (`google_adk_example.py`)
**Use when:**
- You're using Google Cloud / Vertex AI
- You want to use Gemini models
- You need model-agnostic development
- You want enterprise Google integrations

**Features:**
- ✓ Vertex AI Agent Engine integration
- ✓ LiteLLM for multi-model support
- ✓ Google Cloud native deployment
- ✓ Built-in observability

### LangGraph (`langgraph_example.py`)
**Use when:**
- You need complex workflow graphs
- You want state persistence
- You need conditional branching
- You want LangSmith observability

**Features:**
- ✓ Graph-based workflow definition
- ✓ State checkpointing
- ✓ Conditional edges
- ✓ Human-in-the-loop support

### Microsoft Agent Framework (`microsoft_agent_example.py`)
**Use when:**
- You're using Azure / Microsoft 365
- You need Semantic Kernel plugins
- You want AutoGen multi-agent chat
- You're building enterprise applications

**Features:**
- ✓ Semantic Kernel integration
- ✓ AutoGen GroupChat
- ✓ Azure AI services integration
- ✓ Enterprise security & compliance

### AWS Bedrock AgentCore (`aws_bedrock_example.py`)
**Use when:**
- You're using AWS
- You need production-scale deployment
- You want built-in memory management
- You need API Gateway integration

**Features:**
- ✓ Bedrock Agent Runtime
- ✓ DynamoDB/OpenSearch memory
- ✓ Step Functions orchestration
- ✓ API Gateway + CloudWatch

### CrewAI (`crewai_example.py`)
**Use when:**
- You want role-based agents
- You need clear task delegation
- You want simple collaboration
- You prefer intuitive agent definitions

**Features:**
- ✓ Role-based agent system
- ✓ Sequential & hierarchical processes
- ✓ Simple task definition
- ✓ Natural collaboration patterns

## 💡 Example Breakdown

### 1. Google ADK Example

```python
from src.frameworks import get_framework, FrameworkType, AgentConfig

# Initialize
framework = get_framework(
    FrameworkType.GOOGLE_ADK,
    config={
        "project_id": "my-gcp-project",
        "location": "us-central1"
    }
)

# Create agent
agent = framework.create_agent(AgentConfig(
    name="SEO Analyzer",
    role="analyst",
    goal="Analyze SEO performance"
))

# Execute
result = framework.execute_agent(agent, {"description": "Analyze site"})
```

### 2. LangGraph Example

```python
# LangGraph with state management
framework = get_framework(
    FrameworkType.LANGGRAPH,
    config={
        "llm_provider": "openai",
        "api_key": "sk-...",
        "checkpointer": {"type": "redis"}  # State persistence
    }
)
```

### 3. CrewAI Example

```python
# CrewAI with detailed agent roles
agent_config = AgentConfig(
    name="SEO Researcher",
    role="Senior SEO Research Specialist",
    goal="Research SEO trends and keywords",
    backstory="""You are a Senior SEO Research Specialist
    with 10+ years of experience...""",
    tools=["search", "google_trends"]
)
```

## 🔧 Configuration

Each framework requires different configuration:

### Environment Variables

```bash
# OpenAI
export OPENAI_API_KEY="sk-..."

# Google Cloud
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/credentials.json"
export GCP_PROJECT_ID="my-project"

# Azure
export AZURE_OPENAI_ENDPOINT="https://myorg.openai.azure.com"
export AZURE_OPENAI_API_KEY="..."

# AWS
export AWS_ACCESS_KEY_ID="..."
export AWS_SECRET_ACCESS_KEY="..."
export AWS_REGION="us-east-1"

# Docker Model Runner (Free!)
export DOCKER_MODEL_ENDPOINT="http://localhost:8080/v1"
```

### Framework-Specific Setup

**Google ADK:**
```bash
gcloud auth application-default login
gcloud config set project my-project-id
```

**LangGraph:**
```bash
pip install langgraph langsmith
export LANGCHAIN_API_KEY="lsv2_..."
```

**Microsoft Agent:**
```bash
pip install semantic-kernel pyautogen
```

**AWS Bedrock:**
```bash
aws configure
```

**CrewAI:**
```bash
pip install crewai crewai-tools
```

## 📊 Performance Comparison

Based on typical SEO workflow (3 agents, 5 tasks):

| Framework | Avg Duration | Memory Usage | Complexity |
|-----------|-------------|--------------|------------|
| Direct LLM | ~15s | Low | Low |
| CrewAI | ~18s | Medium | Medium |
| Google ADK | ~20s | Medium | Medium |
| LangGraph | ~22s | Medium-High | High |
| Microsoft | ~25s | High | High |
| AWS Bedrock | ~20s | Medium | High |

*Note: Performance depends on LLM provider, network latency, and task complexity.*

## 💰 Cost Comparison

For 100K SEO analyses per month (3 agents, ~5K tokens each):

| Framework | Infrastructure | LLM Cost | Total |
|-----------|---------------|----------|-------|
| Direct LLM + Docker Model Runner | $0 | $0 | **$0/month** |
| Direct LLM + OpenAI | $0 | ~$750 | $750/month |
| Google ADK (Gemini) | ~$50 | ~$200 | $250/month |
| LangGraph Cloud | ~$100 | ~$750 | $850/month |
| Microsoft Agent (Azure) | ~$150 | ~$750 | $900/month |
| AWS Bedrock | ~$100 | ~$500 | $600/month |
| CrewAI + Docker Model Runner | $20 | $0 | $20/month |

**💡 Cost Optimization Tips:**
- Use Docker Model Runner for development/testing ($0)
- Use Ollama for free local inference ($0)
- Cache results to reduce LLM calls (50-70% savings)
- Use smaller models when appropriate (80% cost reduction)

## 🚀 Next Steps

1. **Choose your framework** based on requirements above
2. **Run the example** for that framework
3. **Customize** for your specific use case
4. **Deploy** using the deployment guides in `/docs/deployment/`

## 📚 Additional Resources

- [Framework Architecture](/src/frameworks/README.md)
- [Deployment Guides](/docs/deployment/)
- [API Documentation](/docs/api/)
- [Performance Tuning](/docs/performance.md)

## 🆘 Troubleshooting

**"Framework not initialized" error:**
```python
# Make sure to initialize before creating agents
framework.initialize(config)
```

**"API key required" error:**
```python
# Set API keys in config or environment
config = {"api_key": "your-key-here"}
```

**"Agent not found" error:**
```python
# Ensure agent name in task matches agent config name
task = {"agent": "SEO Analyzer"}  # Must match agent_config.name
```

## 📝 License

MIT License - see LICENSE file for details
