# Azure Deployment Guide - AI SEO Agent

Complete guide for deploying the AI SEO Agent on Microsoft Azure with Azure OpenAI, Cosmos DB, and all Azure-native services.

## Azure Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Azure AI SEO Agent - Full Stack Architecture                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ Azure App Service / Container Apps                             │   │
│  │  ├─ FastAPI Application                                        │   │
│  │  ├─ Auto-scaling (0-10 instances)                              │   │
│  │  └─ Managed SSL certificates                                   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                            │                                            │
│                            ▼                                            │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ Azure OpenAI / AI Foundry                                      │   │
│  │  ├─ GPT-4o, GPT-4, GPT-3.5-turbo                              │   │
│  │  ├─ Managed API with SLA                                       │   │
│  │  └─ Content filtering & monitoring                             │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                            │                                            │
│                            ▼                                            │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ Data Layer                                                      │   │
│  │  ├─ Cosmos DB (NoSQL, globally distributed)                    │   │
│  │  ├─ Blob Storage (file storage, backups)                       │   │
│  │  └─ Azure Cache for Redis (caching, sessions)                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                            │                                            │
│                            ▼                                            │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ Security & Monitoring                                           │   │
│  │  ├─ Key Vault (secrets management)                             │   │
│  │  ├─ Application Insights (monitoring, logging)                 │   │
│  │  ├─ Managed Identity (passwordless auth)                       │   │
│  │  └─ Azure Monitor (alerts, dashboards)                         │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Why Azure?

✅ **Native Azure OpenAI Integration** - Pre-configured for Azure OpenAI
✅ **Enterprise-Grade Security** - Key Vault, Managed Identity, Private Endpoints
✅ **Global Scale** - Cosmos DB global distribution, CDN
✅ **Comprehensive Monitoring** - Application Insights, Azure Monitor
✅ **Cost Effective** - Reserved instances, auto-scaling
✅ **Compliance** - SOC, ISO, HIPAA, FedRAMP certified

---

## Quick Start (Azure Portal)

### 1. Deploy with One Click

[![Deploy to Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#create/Microsoft.Template/uri/...)

Or use Azure CLI:

```bash
# Clone repository
git clone https://github.com/yourusername/ai-seo-agent.git
cd ai-seo-agent

# Run Azure setup
./scripts/azure-deploy.sh
```

---

## Manual Setup (Step-by-Step)

### Prerequisites

1. **Azure Subscription** - [Get a free account](https://azure.microsoft.com/free/)
2. **Azure CLI** - [Install guide](https://docs.microsoft.com/cli/azure/install-azure-cli)
3. **Azure OpenAI Access** - [Request access](https://aka.ms/oai/access)

### Step 1: Login and Setup

```bash
# Login to Azure
az login

# Set subscription (if you have multiple)
az account set --subscription "Your Subscription Name"

# Create resource group
az group create \
  --name ai-seo-agent-rg \
  --location eastus

# Set default resource group
az configure --defaults group=ai-seo-agent-rg location=eastus
```

### Step 2: Create Azure OpenAI Service

```bash
# Create Azure OpenAI resource
az cognitiveservices account create \
  --name seo-agent-openai \
  --resource-group ai-seo-agent-rg \
  --kind OpenAI \
  --sku S0 \
  --location eastus

# Deploy GPT-4o model
az cognitiveservices account deployment create \
  --name seo-agent-openai \
  --resource-group ai-seo-agent-rg \
  --deployment-name gpt-4o \
  --model-name gpt-4o \
  --model-version "2024-05-13" \
  --model-format OpenAI \
  --sku-capacity 10 \
  --sku-name Standard

# Get endpoint and key
az cognitiveservices account show \
  --name seo-agent-openai \
  --query "properties.endpoint" -o tsv

az cognitiveservices account keys list \
  --name seo-agent-openai \
  --query "key1" -o tsv
```

### Step 3: Create Cosmos DB

```bash
# Create Cosmos DB account (NoSQL API)
az cosmosdb create \
  --name seo-agent-cosmos \
  --resource-group ai-seo-agent-rg \
  --default-consistency-level Session \
  --locations regionName=eastus failoverPriority=0 \
  --enable-automatic-failover true

# Create database
az cosmosdb sql database create \
  --account-name seo-agent-cosmos \
  --resource-group ai-seo-agent-rg \
  --name seo-agent

# Create containers
az cosmosdb sql container create \
  --account-name seo-agent-cosmos \
  --database-name seo-agent \
  --name analyses \
  --partition-key-path "/url" \
  --throughput 400

az cosmosdb sql container create \
  --account-name seo-agent-cosmos \
  --database-name seo-agent \
  --name agent_results \
  --partition-key-path "/agent_type" \
  --throughput 400

# Get connection string
az cosmosdb keys list \
  --name seo-agent-cosmos \
  --type connection-strings \
  --query "connectionStrings[0].connectionString" -o tsv
```

### Step 4: Create Blob Storage

```bash
# Create storage account
az storage account create \
  --name seoagentstorage \
  --resource-group ai-seo-agent-rg \
  --sku Standard_LRS \
  --kind StorageV2

# Create container
az storage container create \
  --name seo-data \
  --account-name seoagentstorage

# Get connection string
az storage account show-connection-string \
  --name seoagentstorage \
  --query "connectionString" -o tsv
```

### Step 5: Create Azure Cache for Redis

```bash
# Create Redis cache
az redis create \
  --name seo-agent-cache \
  --resource-group ai-seo-agent-rg \
  --sku Basic \
  --vm-size c0 \
  --location eastus

# Get connection string
az redis list-keys \
  --name seo-agent-cache \
  --query "primaryKey" -o tsv

# Redis URL format: redis://:{password}@{hostname}:6380?ssl=true
```

### Step 6: Create Key Vault (Secrets Management)

```bash
# Create Key Vault
az keyvault create \
  --name seo-agent-kv \
  --resource-group ai-seo-agent-rg \
  --location eastus

# Store secrets
OPENAI_KEY=$(az cognitiveservices account keys list --name seo-agent-openai --query "key1" -o tsv)
COSMOS_KEY=$(az cosmosdb keys list --name seo-agent-cosmos --type keys --query "primaryMasterKey" -o tsv)
STORAGE_CONN=$(az storage account show-connection-string --name seoagentstorage --query "connectionString" -o tsv)
REDIS_KEY=$(az redis list-keys --name seo-agent-cache --query "primaryKey" -o tsv)

az keyvault secret set --vault-name seo-agent-kv --name openai-api-key --value "$OPENAI_KEY"
az keyvault secret set --vault-name seo-agent-kv --name cosmos-key --value "$COSMOS_KEY"
az keyvault secret set --vault-name seo-agent-kv --name storage-connection-string --value "$STORAGE_CONN"
az keyvault secret set --vault-name seo-agent-kv --name redis-key --value "$REDIS_KEY"
```

### Step 7: Deploy Application

#### Option A: Azure Container Apps (Recommended)

```bash
# Create Container Apps environment
az containerapp env create \
  --name seo-agent-env \
  --resource-group ai-seo-agent-rg \
  --location eastus

# Build and push container
az acr create \
  --name seoagentacr \
  --resource-group ai-seo-agent-rg \
  --sku Basic

az acr login --name seoagentacr

docker build -t seoagentacr.azurecr.io/seo-agent:latest .
docker push seoagentacr.azurecr.io/seo-agent:latest

# Deploy container app
az containerapp create \
  --name seo-agent-api \
  --resource-group ai-seo-agent-rg \
  --environment seo-agent-env \
  --image seoagentacr.azurecr.io/seo-agent:latest \
  --target-port 8000 \
  --ingress external \
  --min-replicas 0 \
  --max-replicas 10 \
  --secrets \
    openai-key=keyvaultref:https://seo-agent-kv.vault.azure.net/secrets/openai-api-key,identityref:/subscriptions/{sub-id}/resourcegroups/ai-seo-agent-rg/providers/Microsoft.ManagedIdentity/userAssignedIdentities/seo-agent-identity \
  --env-vars \
    AZURE_OPENAI_API_KEY=secretref:openai-key \
    AZURE_OPENAI_ENDPOINT=https://seo-agent-openai.openai.azure.com/ \
    COSMOS_ENDPOINT=https://seo-agent-cosmos.documents.azure.com:443/
```

#### Option B: Azure App Service

```bash
# Create App Service plan
az appservice plan create \
  --name seo-agent-plan \
  --resource-group ai-seo-agent-rg \
  --is-linux \
  --sku B1

# Create web app
az webapp create \
  --name seo-agent-api \
  --plan seo-agent-plan \
  --runtime "PYTHON:3.11"

# Configure app settings
az webapp config appsettings set \
  --name seo-agent-api \
  --settings \
    AZURE_OPENAI_ENDPOINT=https://seo-agent-openai.openai.azure.com/ \
    AZURE_OPENAI_API_KEY=@Microsoft.KeyVault(SecretUri=https://seo-agent-kv.vault.azure.net/secrets/openai-api-key/) \
    COSMOS_ENDPOINT=https://seo-agent-cosmos.documents.azure.com:443/ \
    COSMOS_KEY=@Microsoft.KeyVault(SecretUri=https://seo-agent-kv.vault.azure.net/secrets/cosmos-key/)

# Deploy code
az webapp deployment source config-zip \
  --name seo-agent-api \
  --src deployment.zip
```

### Step 8: Enable Managed Identity & Key Vault Access

```bash
# Enable system-assigned managed identity
az webapp identity assign \
  --name seo-agent-api \
  --resource-group ai-seo-agent-rg

# Get the identity's principal ID
PRINCIPAL_ID=$(az webapp identity show --name seo-agent-api --query principalId -o tsv)

# Grant Key Vault access
az keyvault set-policy \
  --name seo-agent-kv \
  --object-id $PRINCIPAL_ID \
  --secret-permissions get list
```

### Step 9: Setup Application Insights (Monitoring)

```bash
# Create Application Insights
az monitor app-insights component create \
  --app seo-agent-insights \
  --location eastus \
  --resource-group ai-seo-agent-rg \
  --application-type web

# Get instrumentation key
APPINSIGHTS_KEY=$(az monitor app-insights component show \
  --app seo-agent-insights \
  --query instrumentationKey -o tsv)

# Add to app settings
az webapp config appsettings set \
  --name seo-agent-api \
  --settings APPLICATIONINSIGHTS_CONNECTION_STRING="InstrumentationKey=$APPINSIGHTS_KEY"
```

---

## Infrastructure as Code (Bicep)

The repository includes Azure Bicep templates for automated deployment:

```bash
# Deploy all resources with Bicep
az deployment group create \
  --resource-group ai-seo-agent-rg \
  --template-file infra/main.bicep \
  --parameters @infra/parameters.json
```

**`infra/main.bicep`** - Already included in the repository!

---

## Configuration

### Environment Variables (.env for local development)

```bash
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://seo-agent-openai.openai.azure.com/
AZURE_OPENAI_API_KEY=your-key-here
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# Cosmos DB
COSMOS_ENDPOINT=https://seo-agent-cosmos.documents.azure.com:443/
COSMOS_KEY=your-cosmos-key-here
COSMOS_DATABASE=seo-agent

# Blob Storage
STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=...
STORAGE_CONTAINER=seo-data

# Redis
REDIS_URL=rediss://:{password}@seo-agent-cache.redis.cache.windows.net:6380

# Application Insights
APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=...

# Optional: Google Search Console
GSC_CREDENTIALS_PATH=./credentials/gsc-service-account.json
GSC_PROPERTY_URL=https://example.com

# Optional: Ahrefs
AHREFS_API_KEY=your-ahrefs-key
```

---

## Cost Optimization

### Estimated Monthly Costs (East US)

| Service | Tier | Monthly Cost | Notes |
|---------|------|--------------|-------|
| **Azure OpenAI** | Standard (10K TPM) | $50-200 | Based on usage |
| **Cosmos DB** | 400 RU/s | $24 | Serverless option: $0-50 |
| **Blob Storage** | Standard LRS | $2-10 | Based on data |
| **Redis Cache** | Basic C0 (250MB) | $16 | |
| **Container Apps** | Consumption | $0-50 | Pay per use |
| **App Insights** | Basic | $0-10 | 5GB free/month |
| **Key Vault** | Standard | $0.03 | Per 10K operations |
| **Total** | | **$92-340/month** | |

### Cost Saving Tips

1. **Use Cosmos DB Serverless** for development:
   ```bash
   az cosmosdb create --capabilities EnableServerless
   ```

2. **Use Reserved Capacity** for production (40% savings):
   ```bash
   az reservations catalog show --subscription-id {id}
   ```

3. **Enable Auto-shutdown** for dev/test environments

4. **Use Azure Hybrid Benefit** if you have licenses

5. **Monitor with Azure Cost Management**:
   ```bash
   az consumption usage list --start-date 2024-01-01 --end-date 2024-01-31
   ```

---

## Security Best Practices

### 1. Use Managed Identity (No passwords!)

```python
# src/config/azure.py
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

credential = DefaultAzureCredential()
client = SecretClient(vault_url="https://seo-agent-kv.vault.azure.net/", credential=credential)

openai_key = client.get_secret("openai-api-key").value
```

### 2. Enable Private Endpoints

```bash
# Create private endpoint for Cosmos DB
az network private-endpoint create \
  --name cosmos-private-endpoint \
  --resource-group ai-seo-agent-rg \
  --vnet-name seo-agent-vnet \
  --subnet default \
  --private-connection-resource-id $(az cosmosdb show --name seo-agent-cosmos --query id -o tsv) \
  --group-id Sql \
  --connection-name cosmos-connection
```

### 3. Enable HTTPS Only

```bash
az webapp update --name seo-agent-api --https-only true
```

### 4. Configure CORS

```bash
az webapp cors add \
  --name seo-agent-api \
  --allowed-origins https://yourdomain.com
```

### 5. Enable Azure Defender

```bash
az security pricing create \
  --name AppServices \
  --tier Standard
```

---

## Monitoring & Alerts

### Application Insights Queries

**Request Performance:**
```kusto
requests
| where timestamp > ago(1h)
| summarize avg(duration), percentile(duration, 95) by name
| order by avg_duration desc
```

**Failed Requests:**
```kusto
requests
| where success == false
| summarize count() by resultCode, name
| order by count_ desc
```

**Cache Performance:**
```kusto
customMetrics
| where name == "cache_hit_rate"
| summarize avg(value) by bin(timestamp, 5m)
```

### Setup Alerts

```bash
# Alert on high error rate
az monitor metrics alert create \
  --name high-error-rate \
  --resource-group ai-seo-agent-rg \
  --scopes $(az webapp show --name seo-agent-api --query id -o tsv) \
  --condition "avg Http5xx > 10" \
  --window-size 5m \
  --evaluation-frequency 1m \
  --action email your@email.com
```

---

## Scaling

### Auto-scaling Rules

```bash
# Scale based on CPU
az monitor autoscale create \
  --resource-group ai-seo-agent-rg \
  --resource seo-agent-api \
  --resource-type Microsoft.Web/sites \
  --name autoscale-cpu \
  --min-count 1 \
  --max-count 10 \
  --count 2

az monitor autoscale rule create \
  --resource-group ai-seo-agent-rg \
  --autoscale-name autoscale-cpu \
  --condition "Percentage CPU > 70 avg 5m" \
  --scale out 1

az monitor autoscale rule create \
  --resource-group ai-seo-agent-rg \
  --autoscale-name autoscale-cpu \
  --condition "Percentage CPU < 30 avg 10m" \
  --scale in 1
```

---

## Backup & Disaster Recovery

### Cosmos DB Backup

```bash
# Enable continuous backup (Point-in-time restore)
az cosmosdb update \
  --name seo-agent-cosmos \
  --backup-policy-type Continuous
```

### Blob Storage Backup

```bash
# Enable soft delete
az storage blob service-properties delete-policy update \
  --days-retained 7 \
  --account-name seoagentstorage \
  --enable true

# Enable versioning
az storage account blob-service-properties update \
  --account-name seoagentstorage \
  --enable-versioning true
```

---

## CI/CD with Azure DevOps

**azure-pipelines.yml:**

```yaml
trigger:
  - main

pool:
  vmImage: 'ubuntu-latest'

steps:
- task: UsePythonVersion@0
  inputs:
    versionSpec: '3.11'

- script: |
    pip install -e .
    pytest tests/
  displayName: 'Test'

- task: Docker@2
  inputs:
    command: buildAndPush
    repository: seoagentacr.azurecr.io/seo-agent
    tags: |
      $(Build.BuildId)
      latest

- task: AzureWebAppContainer@1
  inputs:
    azureSubscription: 'Azure Subscription'
    appName: 'seo-agent-api'
    containers: seoagentacr.azurecr.io/seo-agent:$(Build.BuildId)
```

---

## Troubleshooting

### Check App Service Logs

```bash
# Enable logging
az webapp log config \
  --name seo-agent-api \
  --application-logging filesystem \
  --level information

# Stream logs
az webapp log tail --name seo-agent-api
```

### Test Connectivity

```bash
# Test OpenAI endpoint
curl https://seo-agent-openai.openai.azure.com/openai/deployments?api-version=2024-02-15-preview \
  -H "api-key: $AZURE_OPENAI_API_KEY"

# Test Cosmos DB
curl https://seo-agent-cosmos.documents.azure.com/_dbs \
  -H "Authorization: $COSMOS_KEY"
```

### Common Issues

**Issue: "Authentication failed"**
```bash
# Verify managed identity
az webapp identity show --name seo-agent-api

# Grant Key Vault access
az keyvault set-policy --name seo-agent-kv --object-id {identity-principal-id} --secret-permissions get list
```

**Issue: "Rate limit exceeded"**
```bash
# Increase OpenAI deployment capacity
az cognitiveservices account deployment update \
  --name seo-agent-openai \
  --deployment-name gpt-4o \
  --sku-capacity 20
```

---

## Next Steps

1. **Test Deployment:**
   ```bash
   curl https://seo-agent-api.azurewebsites.net/health
   ```

2. **View Performance Dashboard:**
   ```bash
   curl https://seo-agent-api.azurewebsites.net/api/v1/performance/stats
   ```

3. **Setup Custom Domain:**
   ```bash
   az webapp config hostname add \
     --webapp-name seo-agent-api \
     --hostname api.yourdomain.com
   ```

4. **Monitor in Azure Portal:**
   - Application Insights → Performance
   - Cost Management → Cost Analysis
   - Monitor → Alerts

---

## Resources

- [Azure OpenAI Documentation](https://learn.microsoft.com/azure/ai-services/openai/)
- [Cosmos DB Best Practices](https://learn.microsoft.com/azure/cosmos-db/best-practices)
- [Container Apps Documentation](https://learn.microsoft.com/azure/container-apps/)
- [Azure CLI Reference](https://learn.microsoft.com/cli/azure/)

---

**Deployment Time:** 30-45 minutes
**Monthly Cost:** $92-340 (can start with $92 dev tier)
**Scalability:** 0 to millions of requests
**Global:** Deploy to 60+ regions worldwide
