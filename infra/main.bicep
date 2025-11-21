// Main Azure infrastructure deployment for AI SEO Agent
// Usage: az deployment sub create --location swedencentral --template-file main.bicep

targetScope = 'subscription'

@description('Environment name')
@allowed(['dev', 'staging', 'prod'])
param environment string = 'dev'

@description('Azure region for resources')
param location string = 'swedencentral'

@description('Base name for resources')
param baseName string = 'ai-seo-agent'

// Resource group
resource rg 'Microsoft.Resources/resourceGroups@2023-07-01' = {
  name: 'rg-${baseName}-${environment}'
  location: location
  tags: {
    environment: environment
    project: baseName
  }
}

// Deploy core infrastructure
module core 'modules/core.bicep' = {
  scope: rg
  name: 'core-deployment'
  params: {
    baseName: baseName
    environment: environment
    location: location
  }
}

// Deploy Container Apps
module containerApps 'modules/container-apps.bicep' = {
  scope: rg
  name: 'container-apps-deployment'
  params: {
    baseName: baseName
    environment: environment
    location: location
    logAnalyticsWorkspaceId: core.outputs.logAnalyticsWorkspaceId
    containerRegistryName: core.outputs.containerRegistryName
  }
}

// Deploy Azure OpenAI
module openai 'modules/openai.bicep' = {
  scope: rg
  name: 'openai-deployment'
  params: {
    baseName: baseName
    environment: environment
    location: location
  }
}

// Outputs
output resourceGroupName string = rg.name
output containerAppUrl string = containerApps.outputs.containerAppUrl
output openaiEndpoint string = openai.outputs.openaiEndpoint
output keyVaultName string = core.outputs.keyVaultName
