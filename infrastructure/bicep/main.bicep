// Family Wealth Management - Main Infrastructure Template
// Deploys all Azure resources for the application

@description('Environment name (dev, prod)')
param environment string = 'dev'

@description('Azure region for resources')
param location string = resourceGroup().location

@description('Base name for all resources')
param baseName string = 'fwm'

@description('SQL Server admin username')
@secure()
param sqlAdminUsername string

@description('SQL Server admin password')
@secure()
param sqlAdminPassword string

@description('Azure Entra ID tenant ID')
param tenantId string

// Variables
var uniqueSuffix = uniqueString(resourceGroup().id)
var appName = '${baseName}-${environment}-${uniqueSuffix}'

// Key Vault
module keyVault 'keyvault.bicep' = {
  name: 'keyVaultDeployment'
  params: {
    keyVaultName: '${appName}-kv'
    location: location
    tenantId: tenantId
  }
}

// Storage Account
module storage 'storage.bicep' = {
  name: 'storageDeployment'
  params: {
    storageAccountName: '${replace(appName, '-', '')}st'
    location: location
  }
}

// SQL Database
module database 'database.bicep' = {
  name: 'databaseDeployment'
  params: {
    sqlServerName: '${appName}-sql'
    sqlDatabaseName: '${appName}-db'
    location: location
    administratorLogin: sqlAdminUsername
    administratorPassword: sqlAdminPassword
  }
}

// Function App
module functions 'functions.bicep' = {
  name: 'functionsDeployment'
  params: {
    functionAppName: '${appName}-func'
    location: location
    storageAccountName: storage.outputs.storageAccountName
    keyVaultName: keyVault.outputs.keyVaultName
    sqlServerName: database.outputs.sqlServerName
    sqlDatabaseName: database.outputs.sqlDatabaseName
  }
}

// Application Insights
module monitoring 'monitoring.bicep' = {
  name: 'monitoringDeployment'
  params: {
    appInsightsName: '${appName}-insights'
    location: location
  }
}

// Outputs
output functionAppUrl string = functions.outputs.functionAppUrl
output keyVaultName string = keyVault.outputs.keyVaultName
output sqlServerName string = database.outputs.sqlServerName
output storageAccountName string = storage.outputs.storageAccountName
output appInsightsName string = monitoring.outputs.appInsightsName
