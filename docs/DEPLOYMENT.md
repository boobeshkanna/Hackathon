# Deployment Guide

This guide covers deploying the Vernacular Artisan Catalog infrastructure to AWS.

## Prerequisites

1. AWS Account with appropriate permissions
2. AWS CLI configured (`aws configure`)
3. Node.js 18+ installed
4. Python 3.11+ installed
5. AWS CDK installed (`npm install -g aws-cdk`)

## Infrastructure Components

The deployment creates:
- 2 S3 buckets (raw media + enhanced media)
- 2 DynamoDB tables (catalog records + tenant config)
- 1 SQS queue with DLQ
- 2 Lambda functions (API handler + orchestrator)
- 1 API Gateway REST API
- IAM roles and policies
- CloudWatch log groups

## Deployment Steps

### 1. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your values
nano .env
```

### 2. Deploy Infrastructure

```bash
# Run deployment script
./scripts/deploy_infrastructure.sh
```

Or manually:

```bash
cd backend/infrastructure/cdk

# Install dependencies
npm install

# Bootstrap CDK (first time only)
cdk bootstrap

# Deploy
cdk deploy
```

### 3. Note the Outputs

After deployment, CDK will output:
- API Gateway URL
- S3 bucket names
- Other resource identifiers

Save these for your `.env` file.

## Post-Deployment Configuration

### 1. Update .env with Deployed Resources

```bash
# Update these from CDK outputs
S3_RAW_MEDIA_BUCKET=artisan-catalog-raw-media-123456789
S3_ENHANCED_BUCKET=artisan-catalog-enhanced-123456789
SQS_QUEUE_URL=https://sqs.ap-south-1.amazonaws.com/123456789/catalog-processing-queue
```

### 2. Deploy Lambda Code

```bash
# Package and deploy Lambda functions
cd backend
./scripts/package_lambdas.sh
```

### 3. Configure Sagemaker Endpoint

```bash
# Deploy Sagemaker endpoint (if not already deployed)
# Update SAGEMAKER_ENDPOINT_NAME in .env
```

### 4. Test the Deployment

```bash
# Run integration tests
pytest tests/integration/
```

## Monitoring

### CloudWatch Logs

View logs in AWS Console:
- Lambda logs: `/aws/lambda/artisan-catalog-*`
- API Gateway logs: API Gateway → Stages → Logs

### CloudWatch Metrics

Monitor:
- Lambda invocations and errors
- API Gateway requests
- SQS queue depth
- DynamoDB read/write capacity

## Cost Optimization

- Use S3 Intelligent Tiering for media storage
- DynamoDB on-demand pricing for variable workloads
- Lambda reserved concurrency if needed
- Set up CloudWatch alarms for cost anomalies

## Teardown

To remove all resources:

```bash
cd backend/infrastructure/cdk
cdk destroy
```

Note: S3 buckets with RETAIN policy must be manually deleted.
