// Azure OpenAI / AI Foundry resources

@description('Base name for resources')
param baseName string

@description('Environment')
param environment string

@description('Location - Azure OpenAI has limited region availability')
param location string

// Azure OpenAI Account
resource openaiAccount 'Microsoft.CognitiveServices/accounts@2023-10-01-preview' = {
  name: 'oai-${baseName}-${environment}'
  location: location
  kind: 'OpenAI'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: 'oai-${baseName}-${environment}'
    publicNetworkAccess: 'Enabled'
  }
}

// GPT-4o deployment for main agent work
resource gpt4oDeployment 'Microsoft.CognitiveServices/accounts/deployments@2023-10-01-preview' = {
  parent: openaiAccount
  name: 'gpt-4o'
  sku: {
    name: 'Standard'
    capacity: 30 // Tokens per minute (in thousands)
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4o'
      version: '2024-08-06'
    }
    raiPolicyName: 'Microsoft.Default'
  }
}

// GPT-4o-mini for lighter tasks (cost optimization)
resource gpt4oMiniDeployment 'Microsoft.CognitiveServices/accounts/deployments@2023-10-01-preview' = {
  parent: openaiAccount
  name: 'gpt-4o-mini'
  sku: {
    name: 'Standard'
    capacity: 60
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4o-mini'
      version: '2024-07-18'
    }
    raiPolicyName: 'Microsoft.Default'
  }
  dependsOn: [gpt4oDeployment]
}

// Text embedding model for semantic search
resource embeddingDeployment 'Microsoft.CognitiveServices/accounts/deployments@2023-10-01-preview' = {
  parent: openaiAccount
  name: 'text-embedding-3-small'
  sku: {
    name: 'Standard'
    capacity: 120
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'text-embedding-3-small'
      version: '1'
    }
    raiPolicyName: 'Microsoft.Default'
  }
  dependsOn: [gpt4oMiniDeployment]
}

// Outputs
output openaiAccountName string = openaiAccount.name
output openaiEndpoint string = openaiAccount.properties.endpoint
output gpt4oDeploymentName string = gpt4oDeployment.name
output gpt4oMiniDeploymentName string = gpt4oMiniDeployment.name
output embeddingDeploymentName string = embeddingDeployment.name
