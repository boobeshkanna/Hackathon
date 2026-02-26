# AWS CDK Infrastructure

This directory contains the AWS CDK infrastructure code for the Vernacular Artisan Catalog.

## Architecture

The CDK stack deploys:

- **API Gateway**: REST API for mobile app
- **Lambda Functions**: 
  - API Handler (30s timeout, 512MB)
  - Orchestrator (300s timeout, 1024MB)
- **S3 Buckets**:
  - Raw media bucket (with lifecycle rules)
  - Enhanced media bucket
- **DynamoDB Tables**:
  - CatalogProcessingRecords (with GSI on status)
  - TenantConfigurations
- **SQS Queue**: Processing queue with DLQ
- **IAM Roles**: Lambda execution role with necessary permissions
- **CloudWatch**: Log groups with 7-day retention

## Prerequisites

```bash
npm install -g aws-cdk
aws configure
```

## Commands

```bash
# Install dependencies
npm install

# Synthesize CloudFormation template
cdk synth

# Deploy stack
cdk deploy

# Destroy stack
cdk destroy

# View differences
cdk diff
```

## Configuration

The stack uses environment variables:
- `CDK_DEFAULT_ACCOUNT`: AWS account ID
- `CDK_DEFAULT_REGION`: AWS region (default: ap-south-1)

## Outputs

After deployment, the stack outputs:
- API Gateway URL
- S3 bucket names
- Other resource identifiers

## Cost Estimate

For development/testing:
- Lambda: ~$0.50/month
- S3: ~$0.10/month
- DynamoDB: ~$0.05/month
- API Gateway: ~$0.10/month

Total: ~$1/month (excluding AI services)
