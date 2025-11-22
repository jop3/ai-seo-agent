#!/bin/bash
#
# Azure Deployment Script for AI SEO Agent
# Automates the deployment to Azure using Azure CLI
#

set -e

echo "🚀 Azure Deployment for AI SEO Agent"
echo "===================================="
echo ""

# Check Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo "❌ Azure CLI is not installed."
    echo "Install it with: curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash"
    exit 1
fi

echo "✅ Azure CLI detected"

# Check if logged in
if ! az account show &> /dev/null; then
    echo "❌ Not logged in to Azure."
    echo "Run: az login"
    exit 1
fi

SUBSCRIPTION_ID=$(az account show --query id -o tsv)
echo "✅ Logged in to Azure (Subscription: $SUBSCRIPTION_ID)"
echo ""

# Configuration
read -p "Enter resource group name [ai-seo-agent-rg]: " RESOURCE_GROUP
RESOURCE_GROUP=${RESOURCE_GROUP:-ai-seo-agent-rg}

read -p "Enter location [eastus]: " LOCATION
LOCATION=${LOCATION:-eastus}

read -p "Enter app name [seo-agent]: " APP_NAME
APP_NAME=${APP_NAME:-seo-agent}

echo ""
echo "Configuration:"
echo "  Resource Group: $RESOURCE_GROUP"
echo "  Location: $LOCATION"
echo "  App Name: $APP_NAME"
echo ""

read -p "Continue with deployment? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled."
    exit 0
fi

# Step 1: Create Resource Group
echo ""
echo "📦 Step 1/9: Creating resource group..."
az group create \
  --name "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --output table

# Step 2: Create Azure OpenAI
echo ""
echo "🤖 Step 2/9: Creating Azure OpenAI service..."
OPENAI_NAME="${APP_NAME}-openai"
az cognitiveservices account create \
  --name "$OPENAI_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --kind OpenAI \
  --sku S0 \
  --location "$LOCATION" \
  --yes \
  --output table

echo "   Waiting for OpenAI service to be ready..."
sleep 10

# Deploy GPT-4o model
echo "   Deploying GPT-4o model..."
az cognitiveservices account deployment create \
  --name "$OPENAI_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --deployment-name gpt-4o \
  --model-name gpt-4 \
  --model-version "0125" \
  --model-format OpenAI \
  --sku-capacity 10 \
  --sku-name "Standard" \
  --output table || echo "   Note: GPT-4o deployment may require manual setup in Azure Portal"

# Step 3: Create Cosmos DB (Optional - can use PostgreSQL instead)
echo ""
read -p "Create Cosmos DB for database? (y for Cosmos DB, n for Azure PostgreSQL) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🗄️  Step 3/9: Creating Cosmos DB..."
    COSMOS_NAME="${APP_NAME}-cosmos"
    az cosmosdb create \
      --name "$COSMOS_NAME" \
      --resource-group "$RESOURCE_GROUP" \
      --locations regionName="$LOCATION" \
      --enable-automatic-failover true \
      --output table
else
    echo "🐘 Step 3/9: Creating Azure PostgreSQL..."
    DB_NAME="${APP_NAME}-db"
    DB_ADMIN_USER="seoagent"
    DB_ADMIN_PASSWORD=$(openssl rand -base64 32)

    az postgres flexible-server create \
      --name "$DB_NAME" \
      --resource-group "$RESOURCE_GROUP" \
      --location "$LOCATION" \
      --admin-user "$DB_ADMIN_USER" \
      --admin-password "$DB_ADMIN_PASSWORD" \
      --sku-name Standard_B1ms \
      --tier Burstable \
      --storage-size 32 \
      --version 15 \
      --public-access 0.0.0.0 \
      --output table

    echo "   Database credentials saved (keep these secure!):"
    echo "   Username: $DB_ADMIN_USER"
    echo "   Password: $DB_ADMIN_PASSWORD"
    echo "   Connection: postgresql://$DB_ADMIN_USER:$DB_ADMIN_PASSWORD@$DB_NAME.postgres.database.azure.com/postgres"
fi

# Step 4: Create Azure Redis Cache
echo ""
echo "⚡ Step 4/9: Creating Redis Cache..."
REDIS_NAME="${APP_NAME}-redis"
az redis create \
  --name "$REDIS_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --sku Basic \
  --vm-size c0 \
  --output table

# Step 5: Create Storage Account
echo ""
echo "📁 Step 5/9: Creating Storage Account..."
STORAGE_NAME="${APP_NAME}storage$(date +%s | tail -c 5)"
az storage account create \
  --name "$STORAGE_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --sku Standard_LRS \
  --output table

# Step 6: Create Key Vault
echo ""
echo "🔐 Step 6/9: Creating Key Vault..."
KEYVAULT_NAME="${APP_NAME}-kv-$(date +%s | tail -c 5)"
az keyvault create \
  --name "$KEYVAULT_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --output table

# Step 7: Store secrets in Key Vault
echo ""
echo "🔑 Step 7/9: Storing secrets in Key Vault..."

# Get Azure OpenAI key
OPENAI_KEY=$(az cognitiveservices account keys list \
  --name "$OPENAI_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query key1 -o tsv)

OPENAI_ENDPOINT=$(az cognitiveservices account show \
  --name "$OPENAI_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query properties.endpoint -o tsv)

az keyvault secret set \
  --vault-name "$KEYVAULT_NAME" \
  --name "azure-openai-key" \
  --value "$OPENAI_KEY" \
  --output none

az keyvault secret set \
  --vault-name "$KEYVAULT_NAME" \
  --name "azure-openai-endpoint" \
  --value "$OPENAI_ENDPOINT" \
  --output none

echo "   ✅ Secrets stored in Key Vault"

# Step 8: Create Container Apps Environment
echo ""
read -p "Deploy to Azure Container Apps? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🐳 Step 8/9: Creating Container Apps environment..."

    # Check if containerapp extension is installed
    if ! az extension show --name containerapp &> /dev/null; then
        echo "   Installing Container Apps extension..."
        az extension add --name containerapp --upgrade
    fi

    ENV_NAME="${APP_NAME}-env"
    az containerapp env create \
      --name "$ENV_NAME" \
      --resource-group "$RESOURCE_GROUP" \
      --location "$LOCATION" \
      --output table

    # Step 9: Deploy Container App
    echo ""
    echo "🚀 Step 9/9: Deploying Container App..."

    # Note: This requires a container image to be built and pushed to ACR first
    echo "   ⚠️  Container App requires Docker image."
    echo "   Build and push your image, then run:"
    echo ""
    echo "   az containerapp create \\"
    echo "     --name ${APP_NAME}-api \\"
    echo "     --resource-group $RESOURCE_GROUP \\"
    echo "     --environment $ENV_NAME \\"
    echo "     --image <your-acr>.azurecr.io/seo-agent:latest \\"
    echo "     --target-port 8000 \\"
    echo "     --ingress external \\"
    echo "     --min-replicas 0 \\"
    echo "     --max-replicas 10"
else
    echo "ℹ️  Step 8-9: Skipped Container Apps deployment"
    echo "   You can deploy to App Service instead - see AZURE_DEPLOYMENT.md"
fi

# Display summary
echo ""
echo "=================================="
echo "✅ Azure Deployment Complete!"
echo "=================================="
echo ""
echo "📋 Resources Created:"
echo "   Resource Group: $RESOURCE_GROUP"
echo "   Azure OpenAI: $OPENAI_NAME"
echo "   Key Vault: $KEYVAULT_NAME"
echo "   Storage: $STORAGE_NAME"
echo "   Redis: $REDIS_NAME"
if [[ -n "$COSMOS_NAME" ]]; then
    echo "   Cosmos DB: $COSMOS_NAME"
elif [[ -n "$DB_NAME" ]]; then
    echo "   PostgreSQL: $DB_NAME"
fi
echo ""
echo "🔗 Next Steps:"
echo "   1. Review AZURE_DEPLOYMENT.md for complete configuration"
echo "   2. Configure environment variables in Key Vault or App Settings"
echo "   3. Build and deploy your application"
echo "   4. Set up monitoring with Application Insights"
echo "   5. Configure CI/CD pipeline"
echo ""
echo "📖 Useful commands:"
echo "   View resources: az resource list -g $RESOURCE_GROUP -o table"
echo "   View Key Vault secrets: az keyvault secret list --vault-name $KEYVAULT_NAME -o table"
echo "   Delete all resources: az group delete -n $RESOURCE_GROUP --yes"
echo ""
