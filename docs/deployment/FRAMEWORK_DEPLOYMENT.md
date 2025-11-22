# Multi-Framework Deployment Guide

Complete deployment guide for all supported agent frameworks.

## Table of Contents

1. [Google ADK → Vertex AI](#google-adk--vertex-ai)
2. [LangGraph → LangGraph Cloud](#langgraph--langgraph-cloud)
3. [Microsoft Agent Framework → Azure](#microsoft-agent-framework--azure)
4. [AWS Bedrock AgentCore → AWS](#aws-bedrock-agentcore--aws)
5. [CrewAI → Docker/Kubernetes](#crewai--dockerkubernetes)
6. [Direct LLM → Any Platform](#direct-llm--any-platform)

---

## Google ADK → Vertex AI

Deploy your agents to Google Cloud's Vertex AI Agent Engine.

### Prerequisites

```bash
# Install Google Cloud SDK
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Install Google ADK
pip install google-cloud-aiplatform

# Authenticate
gcloud auth login
gcloud auth application-default login
```

### Configuration

```python
# config/google_adk.yaml
framework: google_adk
google_cloud:
  project_id: "my-gcp-project"
  location: "us-central1"
  service_account: "seo-agent@my-project.iam.gserviceaccount.com"

deployment:
  target: "vertex-ai"
  agent_runtime: "agent-engine"
  scaling:
    min_instances: 1
    max_instances: 10
    target_cpu: 70
```

### Deployment Steps

#### 1. Enable Required APIs

```bash
gcloud services enable \
  aiplatform.googleapis.com \
  cloudresourcemanager.googleapis.com \
  iam.googleapis.com
```

#### 2. Create Service Account

```bash
# Create service account
gcloud iam service-accounts create seo-agent \
  --display-name="SEO Agent Service Account"

# Grant permissions
gcloud projects add-iam-policy-binding my-gcp-project \
  --member="serviceAccount:seo-agent@my-project.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"
```

#### 3. Deploy Agent

```python
from src.frameworks import get_framework, FrameworkType, DeploymentConfig

framework = get_framework(FrameworkType.GOOGLE_ADK, config={
    "project_id": "my-gcp-project",
    "location": "us-central1"
})

# Deploy
deployment_url = framework.deploy(DeploymentConfig(
    target="vertex-ai",
    region="us-central1",
    credentials={
        "service_account": "seo-agent@my-project.iam.gserviceaccount.com"
    }
))

print(f"Deployed to: {deployment_url}")
```

#### 4. Test Deployment

```bash
# Test via gcloud
gcloud ai agents predict \
  --agent-id=your-agent-id \
  --location=us-central1 \
  --prompt="Analyze SEO for example.com"
```

### Cost Estimation

- **Vertex AI Agent Engine**: $0.50 per 1K requests
- **Gemini 2.0 Flash**: $0.075 per 1M input tokens, $0.30 per 1M output tokens
- **Monthly estimate (100K requests)**: ~$150-250/month

### Monitoring

```bash
# View logs
gcloud logging read "resource.type=aiplatform.googleapis.com/Agent" --limit=50

# Metrics
gcloud monitoring time-series list \
  --filter='metric.type="aiplatform.googleapis.com/agent/request_count"'
```

---

## LangGraph → LangGraph Cloud

Deploy LangGraph workflows to LangGraph Cloud with LangSmith observability.

### Prerequisites

```bash
# Install LangGraph
pip install langgraph langsmith langchain-openai

# Set API keys
export LANGCHAIN_API_KEY="lsv2_..."
export LANGCHAIN_TRACING_V2=true
export LANGCHAIN_PROJECT="seo-agent"
```

### Configuration

```python
# config/langgraph.yaml
framework: langgraph
langgraph:
  api_key: "${LANGCHAIN_API_KEY}"
  project: "seo-agent"
  checkpointer: "redis"
  redis_url: "redis://localhost:6379"

deployment:
  target: "langgraph-cloud"
  environment: "production"
  scaling:
    memory: "2Gi"
    cpu: "1000m"
```

### Deployment Steps

#### 1. Package Graph

```python
# Create langgraph.json
{
  "dependencies": ["langgraph", "langchain-openai"],
  "graphs": {
    "seo_agent": "./src/workflows/seo_graph.py:graph"
  },
  "env": ".env"
}
```

#### 2. Deploy to LangGraph Cloud

```bash
# Login to LangSmith
langsmith login

# Deploy graph
langsmith deployment create \
  --name seo-agent \
  --graph-id seo_agent \
  --environment production
```

#### 3. Programmatic Deployment

```python
from src.frameworks import get_framework, FrameworkType, DeploymentConfig

framework = get_framework(FrameworkType.LANGGRAPH, config={
    "llm_provider": "openai",
    "api_key": "sk-...",
    "checkpointer": {"type": "redis"}
})

deployment_url = framework.deploy(DeploymentConfig(
    target="langgraph-cloud",
    credentials={"api_key": "lsv2_..."}
))
```

#### 4. Invoke Deployed Graph

```python
from langgraph_sdk import get_client

client = get_client()
thread = await client.threads.create()

result = await client.runs.create(
    thread_id=thread["thread_id"],
    assistant_id="seo_agent",
    input={"url": "https://example.com"}
)
```

### Cost Estimation

- **LangGraph Cloud**: $0.10 per compute minute
- **LangSmith**: $39/month (includes 10K traces)
- **OpenAI GPT-4**: $15 per 1M input tokens
- **Monthly estimate (100K analyses)**: ~$900/month

### Monitoring

LangSmith provides automatic observability:

```python
# View traces in LangSmith dashboard
https://smith.langchain.com/o/{org}/projects/p/{project}
```

---

## Microsoft Agent Framework → Azure

Deploy Semantic Kernel + AutoGen agents to Azure.

### Prerequisites

```bash
# Install Azure CLI
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Install Semantic Kernel
pip install semantic-kernel pyautogen

# Login
az login
```

### Configuration

```yaml
# config/microsoft_agent.yaml
framework: microsoft_agent
azure:
  subscription_id: "xxx"
  resource_group: "seo-agent-rg"
  location: "eastus"
  openai:
    endpoint: "https://myorg.openai.azure.com"
    deployment: "gpt-4o"
    api_version: "2024-02-01"

deployment:
  target: "azure"
  app_service_plan: "P1v2"
  container_registry: "myregistry.azurecr.io"
```

### Deployment Steps

#### 1. Create Azure Resources

```bash
# Create resource group
az group create --name seo-agent-rg --location eastus

# Create Container Registry
az acr create \
  --resource-group seo-agent-rg \
  --name seoagentregistry \
  --sku Standard

# Create Azure OpenAI resource
az cognitiveservices account create \
  --name seo-agent-openai \
  --resource-group seo-agent-rg \
  --kind OpenAI \
  --sku S0 \
  --location eastus
```

#### 2. Deploy Model

```bash
# Deploy GPT-4
az cognitiveservices account deployment create \
  --name seo-agent-openai \
  --resource-group seo-agent-rg \
  --deployment-name gpt-4o \
  --model-name gpt-4o \
  --model-version "2024-05-13" \
  --model-format OpenAI \
  --sku-capacity 10 \
  --sku-name Standard
```

#### 3. Build and Push Container

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ ./src/
COPY config/ ./config/

CMD ["python", "-m", "src.api.main"]
```

```bash
# Build
docker build -t seoagentregistry.azurecr.io/seo-agent:latest .

# Push
az acr login --name seoagentregistry
docker push seoagentregistry.azurecr.io/seo-agent:latest
```

#### 4. Deploy to Container Apps

```bash
# Create Container App environment
az containerapp env create \
  --name seo-agent-env \
  --resource-group seo-agent-rg \
  --location eastus

# Deploy app
az containerapp create \
  --name seo-agent \
  --resource-group seo-agent-rg \
  --environment seo-agent-env \
  --image seoagentregistry.azurecr.io/seo-agent:latest \
  --target-port 8000 \
  --ingress external \
  --env-vars \
    AZURE_OPENAI_ENDPOINT=secretref:openai-endpoint \
    AZURE_OPENAI_API_KEY=secretref:openai-key
```

#### 5. Programmatic Deployment

```python
from src.frameworks import get_framework, FrameworkType, DeploymentConfig

framework = get_framework(FrameworkType.MICROSOFT_AGENT, config={
    "azure_endpoint": "https://myorg.openai.azure.com",
    "api_key": "...",
    "deployment": "gpt-4o"
})

deployment_url = framework.deploy(DeploymentConfig(
    target="azure",
    region="eastus",
    credentials={"subscription_id": "..."}
))
```

### Cost Estimation

- **Azure Container Apps**: ~$50/month (1 vCPU, 2GB RAM)
- **Azure OpenAI GPT-4**: $30 per 1M input tokens
- **Azure Storage**: ~$5/month
- **Monthly estimate (100K analyses)**: ~$900/month

### Monitoring

```bash
# View logs
az containerapp logs show \
  --name seo-agent \
  --resource-group seo-agent-rg \
  --follow

# Metrics
az monitor metrics list \
  --resource seo-agent \
  --metric-names "Requests,RequestDuration"
```

---

## AWS Bedrock AgentCore → AWS

Deploy to AWS with Bedrock AgentCore Runtime.

### Prerequisites

```bash
# Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Install boto3
pip install boto3

# Configure
aws configure
```

### Configuration

```yaml
# config/aws_bedrock.yaml
framework: aws_bedrock
aws:
  region: "us-east-1"
  account_id: "123456789012"
  bedrock:
    model_id: "anthropic.claude-3-5-sonnet-20241022-v2:0"
    knowledge_base: "seo-kb"
  memory:
    backend: "dynamodb"
    table_name: "seo-agent-memory"
  gateway:
    enabled: true
    stage: "prod"
    throttle:
      rate_limit: 1000
      burst_limit: 2000
```

### Deployment Steps

#### 1. Create DynamoDB Table

```bash
# Create memory table
aws dynamodb create-table \
  --table-name seo-agent-memory \
  --attribute-definitions \
    AttributeName=session_id,AttributeType=S \
    AttributeName=timestamp,AttributeType=N \
  --key-schema \
    AttributeName=session_id,KeyType=HASH \
    AttributeName=timestamp,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST
```

#### 2. Create Bedrock Agent

```bash
# Create IAM role for agent
aws iam create-role \
  --role-name seo-agent-role \
  --assume-role-policy-document file://trust-policy.json

# Create Bedrock agent
aws bedrock-agent create-agent \
  --agent-name seo-agent \
  --foundation-model anthropic.claude-3-5-sonnet-20241022-v2:0 \
  --instruction "You are an SEO analysis agent" \
  --agent-resource-role-arn arn:aws:iam::123456789012:role/seo-agent-role
```

#### 3. Create Action Groups

```bash
# Create Lambda function for actions
aws lambda create-function \
  --function-name seo-agent-actions \
  --runtime python3.11 \
  --handler index.handler \
  --zip-file fileb://function.zip \
  --role arn:aws:iam::123456789012:role/lambda-role

# Add action group to agent
aws bedrock-agent create-agent-action-group \
  --agent-id AGENT_ID \
  --agent-version DRAFT \
  --action-group-name seo-actions \
  --action-group-executor lambda=arn:aws:lambda:us-east-1:123456789012:function:seo-agent-actions
```

#### 4. Create Step Functions Workflow

```json
{
  "Comment": "SEO Analysis Workflow",
  "StartAt": "InvokeAnalyzer",
  "States": {
    "InvokeAnalyzer": {
      "Type": "Task",
      "Resource": "arn:aws:states:::bedrock:invokeAgent",
      "Parameters": {
        "agentId": "${AgentId}",
        "agentAliasId": "${AliasId}",
        "sessionId.$": "$.session_id",
        "inputText.$": "$.prompt"
      },
      "End": true
    }
  }
}
```

```bash
# Create state machine
aws stepfunctions create-state-machine \
  --name seo-agent-workflow \
  --definition file://workflow.json \
  --role-arn arn:aws:iam::123456789012:role/stepfunctions-role
```

#### 5. Create API Gateway

```bash
# Create REST API
aws apigateway create-rest-api \
  --name seo-agent-api \
  --endpoint-configuration types=REGIONAL

# Create resource and method
aws apigateway put-method \
  --rest-api-id API_ID \
  --resource-id RESOURCE_ID \
  --http-method POST \
  --authorization-type NONE

# Deploy API
aws apigateway create-deployment \
  --rest-api-id API_ID \
  --stage-name prod
```

#### 6. Programmatic Deployment

```python
from src.frameworks import get_framework, FrameworkType, DeploymentConfig

framework = get_framework(FrameworkType.AWS_BEDROCK, config={
    "region": "us-east-1",
    "memory_backend": "dynamodb",
    "gateway_enabled": True
})

deployment_url = framework.deploy(DeploymentConfig(
    target="aws",
    region="us-east-1",
    credentials={"account_id": "123456789012"}
))
```

### Cost Estimation

- **Bedrock Agents**: $0.002 per request
- **Claude 3.5 Sonnet**: $3 per 1M input tokens, $15 per 1M output tokens
- **DynamoDB**: ~$5/month (pay-per-request)
- **API Gateway**: $3.50 per million requests
- **Step Functions**: $25 per million state transitions
- **Monthly estimate (100K analyses)**: ~$600/month

### Monitoring

```bash
# CloudWatch Logs
aws logs tail /aws/bedrock/agents/AGENT_ID --follow

# CloudWatch Metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Bedrock \
  --metric-name Invocations \
  --dimensions Name=AgentId,Value=AGENT_ID \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-02T00:00:00Z \
  --period 3600 \
  --statistics Sum
```

---

## CrewAI → Docker/Kubernetes

Deploy CrewAI workflows to Docker or Kubernetes.

### Prerequisites

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install kubectl (for K8s)
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# Install Helm (for K8s)
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```

### Configuration

```yaml
# config/crewai.yaml
framework: crewai
crewai:
  llm_provider: "openai"  # or "docker_model_runner" for free!
  model: "gpt-4o"
  process: "sequential"  # or "hierarchical"

deployment:
  target: "docker"  # or "kubernetes"
  registry: "ghcr.io/myorg"
  image: "seo-agent-crew"
  tag: "latest"
```

### Deployment Steps (Docker)

#### 1. Create Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY src/ ./src/
COPY config/ ./config/

# Expose port
EXPOSE 8000

# Run
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### 2. Build and Run

```bash
# Build image
docker build -t seo-agent-crew:latest .

# Run container
docker run -d \
  --name seo-agent \
  -p 8000:8000 \
  -e OPENAI_API_KEY=sk-... \
  seo-agent-crew:latest

# Test
curl http://localhost:8000/health
```

#### 3. Docker Compose (with Docker Model Runner)

```yaml
# docker-compose.yml
version: '3.8'

services:
  llm:
    image: ai/phi3-mini-4k-instruct
    ports:
      - "8080:8080"
    environment:
      - MODEL_ID=ai/phi3-mini-4k-instruct

  seo-agent:
    image: seo-agent-crew:latest
    ports:
      - "8000:8000"
    depends_on:
      - llm
    environment:
      - OPENAI_API_BASE=http://llm:8080/v1
      - OPENAI_API_KEY=not-needed
```

```bash
# Run with Docker Compose
docker-compose up -d
```

### Deployment Steps (Kubernetes)

#### 1. Create Deployment

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: seo-agent
spec:
  replicas: 3
  selector:
    matchLabels:
      app: seo-agent
  template:
    metadata:
      labels:
        app: seo-agent
    spec:
      containers:
      - name: seo-agent
        image: ghcr.io/myorg/seo-agent-crew:latest
        ports:
        - containerPort: 8000
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: openai-secret
              key: api-key
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
---
apiVersion: v1
kind: Service
metadata:
  name: seo-agent-service
spec:
  selector:
    app: seo-agent
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8000
  type: LoadBalancer
```

#### 2. Deploy to Kubernetes

```bash
# Create secret
kubectl create secret generic openai-secret \
  --from-literal=api-key=sk-...

# Apply deployment
kubectl apply -f k8s/deployment.yaml

# Check status
kubectl get pods
kubectl get services
```

#### 3. Create Helm Chart

```yaml
# helm/seo-agent/values.yaml
replicaCount: 3

image:
  repository: ghcr.io/myorg/seo-agent-crew
  tag: latest
  pullPolicy: IfNotPresent

service:
  type: LoadBalancer
  port: 80
  targetPort: 8000

resources:
  requests:
    memory: "512Mi"
    cpu: "500m"
  limits:
    memory: "2Gi"
    cpu: "2000m"

env:
  OPENAI_API_KEY: ""  # Set via --set
```

```bash
# Install with Helm
helm install seo-agent ./helm/seo-agent \
  --set env.OPENAI_API_KEY=sk-...
```

### Cost Estimation

**Docker (single instance):**
- VPS: ~$20/month (2 vCPU, 4GB RAM)
- LLM costs: $0 (Docker Model Runner) or $750/month (OpenAI)
- **Total: $20-770/month**

**Kubernetes (3 replicas):**
- K8s cluster: ~$100/month (managed service)
- LLM costs: $0 (Docker Model Runner) or $750/month (OpenAI)
- **Total: $100-850/month**

### Monitoring

```bash
# Docker logs
docker logs -f seo-agent

# Kubernetes logs
kubectl logs -f deployment/seo-agent

# Metrics
kubectl top pods
kubectl top nodes
```

---

## Direct LLM → Any Platform

Direct LLM can deploy to any platform since it has no framework dependencies.

### Deployment Options

1. **Docker** (see CrewAI Docker guide above)
2. **Vercel** (serverless functions)
3. **AWS Lambda** (serverless)
4. **Google Cloud Run** (containers)
5. **Azure Container Apps** (containers)
6. **Railway** (PaaS)
7. **Fly.io** (edge)

### Example: Deploy to Vercel

```bash
# Install Vercel CLI
npm install -g vercel

# Deploy
vercel --prod
```

```json
// vercel.json
{
  "version": 2,
  "builds": [
    {
      "src": "src/api/main.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "src/api/main.py"
    }
  ],
  "env": {
    "OPENAI_API_KEY": "@openai-api-key"
  }
}
```

### Cost Estimation

Platform-dependent:
- **Vercel**: $20/month (Pro plan)
- **AWS Lambda**: ~$5/month (free tier + usage)
- **Google Cloud Run**: ~$10/month
- **Railway**: $5-20/month
- **Fly.io**: $5-15/month

Plus LLM costs: $0 (Docker Model Runner) to $750/month (OpenAI GPT-4)

---

## Deployment Comparison

| Framework | Best Platform | Setup Time | Monthly Cost | Scaling | Complexity |
|-----------|--------------|------------|--------------|---------|------------|
| Google ADK | Vertex AI | 2 hours | $150-250 | Excellent | Medium |
| LangGraph | LangGraph Cloud | 1 hour | $850 | Good | Medium |
| Microsoft | Azure | 3 hours | $900 | Excellent | High |
| AWS Bedrock | AWS | 4 hours | $600 | Excellent | High |
| CrewAI | Docker/K8s | 1 hour | $20-850 | Good | Low |
| Direct LLM | Any | 30 mins | $5-750 | Varies | Very Low |

## Next Steps

1. Choose your framework based on requirements
2. Follow the deployment guide for your chosen platform
3. Monitor and optimize costs
4. Scale as needed

For questions or issues, see the [Troubleshooting Guide](../troubleshooting.md).
