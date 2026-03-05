# AWS Deployment Guide - Vernacular Artisan Catalog

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [AWS Infrastructure Components](#aws-infrastructure-components)
5. [IAM Roles and Permissions](#iam-roles-and-permissions)
6. [Environment Variables and Secrets](#environment-variables-and-secrets)
7. [Deployment Methods](#deployment-methods)
8. [CI/CD Pipeline Configuration](#cicd-pipeline-configuration)
9. [Post-Deployment Configuration](#post-deployment-configuration)
10. [Monitoring and Observability](#monitoring-and-observability)
11. [Security Configuration](#security-configuration)
12. [Cost Optimization](#cost-optimization)
13. [Troubleshooting](#troubleshooting)

---

## Overview

The Vernacular Artisan Catalog is deployed on AWS using a serverless architecture. This guide provides comprehensive instructions for deploying and managing the infrastructure using AWS CDK (Cloud Development Kit).

### Architecture Principles

- **Serverless-first**: Lambda, API Gateway, SQS, S3, DynamoDB
- **Event-driven**: Asynchronous processing with SQS queues
- **Multi-tenant**: Tenant isolation at data and configuration levels
- **Secure by default**: Encryption at rest and in transit, least privilege IAM
- **Observable**: CloudWatch metrics, logs, traces, and alarms
- **Cost-optimized**: Auto-scaling, intelligent tiering, on-demand pricing

---

## Architecture

### High-Level Architecture

```
┌─────────────────┐
│  Mobile Client  │
│  (React Native) │
└────────┬────────┘
         │ HTTPS (TLS 1.2+)
         ▼
┌─────────────────────────────────────────┐
│         API Gateway (REST API)          │
│  - Rate limiting (100 req/s)            │
│  - Request validation                   │
│  - API key authentication               │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│    Lambda: API Handler (Python 3.11)    │
│  - Upload initiation                    │
│  - Upload completion                    │
│  - Status queries                       │
└────┬────────────────────────────────────┘
     │
     ├──────────────┬──────────────┬───────────────┐
     ▼              ▼              ▼               ▼
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│ S3 Raw   │  │ S3 Enh.  │  │   SQS    │  │ DynamoDB │
│  Media   │  │  Media   │  │  Queue   │  │  Tables  │
└──────────┘  └──────────┘  └────┬─────┘  └──────────┘
                                  │
                                  ▼
                    ┌──────────────────────────┐
                    │ Lambda: Orchestrator     │
                    │ - ASR processing         │
                    │ - Vision processing      │
                    │ - Attribute extraction   │
                    │ - ONDC submission        │
                    └──────┬───────────────────┘
                           │
                ┌──────────┼──────────┐
                ▼          ▼          ▼
         ┌──────────┐ ┌────────┐ ┌──────┐
         │ Sagemaker│ │ Bedrock│ │ SNS  │
         │ Endpoint │ │  LLM   │ │Topic │
         └──────────┘ └────────┘ └──────┘
```

### AWS Services Used

| Service | Purpose | Configuration |
|---------|---------|---------------|
| **Lambda** | Serverless compute for API and processing | Python 3.11, 512MB-1024MB RAM |
| **API Gateway** | REST API endpoint | Regional, TLS 1.2+, rate limiting |
| **S3** | Media storage (raw + enhanced) | AES-256 encryption, lifecycle policies |
| **DynamoDB** | Metadata and state storage | On-demand billing, encryption |
| **SQS** | Asynchronous message queue | Standard queue, DLQ, encryption |
| **Sagemaker** | Vision + ASR model endpoint | Real-time inference |
| **Bedrock** | LLM for transcreation | Claude/Titan models |
| **SNS** | Notifications and alarms | Email/SMS subscriptions |
| **CloudWatch** | Logs, metrics, alarms, dashboard | 7-day log retention |
| **X-Ray** | Distributed tracing | Active tracing enabled |
| **IAM** | Access control | Least privilege roles |

---

## Prerequisites

### Required Tools


1. **AWS CLI** (v2.x or later)
   ```bash
   # Install AWS CLI
   curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
   unzip awscliv2.zip
   sudo ./aws/install
   
   # Verify installation
   aws --version
   ```

2. **Node.js** (v18.x or later)
   ```bash
   # Install Node.js
   curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
   sudo apt-get install -y nodejs
   
   # Verify installation
   node --version
   npm --version
   ```

3. **Python** (v3.11 or later)
   ```bash
   # Install Python 3.11
   sudo apt-get update
   sudo apt-get install python3.11 python3.11-venv python3-pip
   
   # Verify installation
   python3.11 --version
   ```

4. **AWS CDK** (v2.115.0 or later)
   ```bash
   # Install AWS CDK globally
   npm install -g aws-cdk
   
   # Verify installation
   cdk --version
   ```

### AWS Account Requirements

- **AWS Account** with administrative access
- **IAM User** with permissions to create:
  - Lambda functions
  - API Gateway APIs
  - S3 buckets
  - DynamoDB tables
  - SQS queues
  - IAM roles and policies
  - CloudWatch resources
  - Sagemaker endpoints
  - Bedrock model access


### AWS CLI Configuration

```bash
# Configure AWS credentials
aws configure

# Enter your credentials:
# AWS Access Key ID: YOUR_ACCESS_KEY
# AWS Secret Access Key: YOUR_SECRET_KEY
# Default region name: ap-south-1  # or your preferred region
# Default output format: json

# Verify configuration
aws sts get-caller-identity
```

---

## AWS Infrastructure Components

### 1. S3 Buckets

#### Raw Media Bucket
- **Purpose**: Store original photos and audio files from artisans
- **Naming**: `artisan-catalog-raw-media-{account-id}`
- **Encryption**: AES-256 (S3-managed)
- **Lifecycle**: 30-day expiration (privacy requirement)
- **Access**: Private, HTTPS-only

#### Enhanced Media Bucket
- **Purpose**: Store processed/enhanced images
- **Naming**: `artisan-catalog-enhanced-{account-id}`
- **Encryption**: AES-256 (S3-managed)
- **Lifecycle**: 30-day expiration
- **Access**: Private, HTTPS-only

**CDK Configuration:**
```typescript
const rawMediaBucket = new s3.Bucket(this, 'RawMediaBucket', {
  encryption: s3.BucketEncryption.S3_MANAGED,
  blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
  enforceSSL: true,
  lifecycleRules: [{
    expiration: cdk.Duration.days(30),
    transitions: [{
      storageClass: s3.StorageClass.INTELLIGENT_TIERING,
      transitionAfter: cdk.Duration.days(7)
    }]
  }]
});
```

### 2. DynamoDB Tables

#### CatalogProcessingRecords Table
- **Purpose**: Track catalog entry processing state
- **Partition Key**: `tracking_id` (String)
- **Billing**: On-demand (pay-per-request)
- **Encryption**: AWS-managed
- **Point-in-time recovery**: Enabled
- **Global Secondary Indexes**:
  - `TenantIndex`: Query by tenant_id + created_at
  - `StatusIndex`: Query by submission_status + updated_at
  - `ArtisanIndex`: Query by artisan_id + created_at


#### LocalQueueEntries Table
- **Purpose**: Track edge client sync status
- **Partition Key**: `local_id` (String)
- **GSI**: `TrackingIdIndex` for lookup by tracking_id

#### TenantConfigurations Table
- **Purpose**: Store tenant-specific settings
- **Partition Key**: `tenant_id` (String)
- **Attributes**: language preferences, ONDC credentials, quotas

#### ArtisanProfiles Table
- **Purpose**: Store artisan information
- **Partition Key**: `artisan_id` (String)
- **GSI**: `TenantIndex` for tenant-based queries

### 3. SQS Queue

#### Processing Queue
- **Name**: `catalog-processing-queue`
- **Type**: Standard (high throughput)
- **Visibility Timeout**: 300 seconds (matches Lambda timeout)
- **Retention**: 14 days
- **Encryption**: SQS-managed
- **Dead Letter Queue**: `catalog-processing-dlq` (3 max receives)

**Purpose**: Decouple API Gateway from processing Lambda, enable async processing

### 4. Lambda Functions

#### API Handler Lambda
- **Name**: `artisan-catalog-api-handler`
- **Runtime**: Python 3.11
- **Memory**: 512 MB
- **Timeout**: 30 seconds
- **Handler**: `main.handler`
- **Tracing**: X-Ray active
- **Endpoints**:
  - `POST /v1/catalog/upload/initiate` - Start upload
  - `POST /v1/catalog/upload/complete` - Finish upload
  - `GET /v1/catalog/status/{trackingId}` - Query status

#### Orchestrator Lambda
- **Name**: `artisan-catalog-orchestrator`
- **Runtime**: Python 3.11
- **Memory**: 1024 MB
- **Timeout**: 300 seconds (5 minutes)
- **Handler**: `main.handler`
- **Tracing**: X-Ray active
- **Trigger**: SQS queue (batch size: 10)
- **Reserved Concurrency**: 50 (for auto-scaling)

**Processing Stages**:
1. ASR transcription (Sagemaker)
2. Image enhancement
3. Vision analysis (Sagemaker)
4. Attribute extraction (Bedrock)
5. ONDC schema mapping
6. ONDC submission


### 5. API Gateway

#### Configuration
- **Type**: REST API (Regional)
- **Stage**: prod
- **Security**: TLS 1.2+ (enforced)
- **Authentication**: API Key required
- **Rate Limiting**: 100 requests/second
- **Burst Limit**: 200 requests
- **Daily Quota**: 100,000 requests per API key
- **Logging**: INFO level
- **Tracing**: X-Ray enabled

#### Usage Plan
- Throttling prevents overload
- API keys for client authentication
- Per-method request validation

### 6. Sagemaker Endpoint

#### Vision + ASR Combined Endpoint
- **Purpose**: Run vision model (CLIP/custom) and ASR model (Whisper/IndicWav2Vec)
- **Instance Type**: ml.g4dn.xlarge (GPU instance)
- **Auto-scaling**: Based on invocation count
- **Endpoint Name**: Set in `SAGEMAKER_ENDPOINT_NAME` environment variable

**Deployment**: See [SAGEMAKER_ENDPOINT_DEPLOYMENT.md](./SAGEMAKER_ENDPOINT_DEPLOYMENT.md)

### 7. Bedrock

#### LLM for Transcreation
- **Models**: Claude 3 Sonnet or Titan Text
- **Purpose**: Attribute extraction, cultural transcreation
- **Region**: Must be Bedrock-enabled region (us-east-1, us-west-2, etc.)

**Enable Bedrock Access**:
1. Go to AWS Bedrock console
2. Request model access for Claude/Titan
3. Wait for approval (usually instant)

### 8. SNS Topic

#### Alarm Topic
- **Name**: `artisan-catalog-alarms`
- **Purpose**: Receive CloudWatch alarm notifications
- **Subscriptions**: Email (configurable)

### 9. CloudWatch

#### Log Groups
- `/aws/lambda/artisan-catalog-api-handler` (7-day retention)
- `/aws/lambda/artisan-catalog-orchestrator` (7-day retention)
- API Gateway execution logs

#### Metrics (Custom Namespace: `VernacularArtisanCatalog`)
- `QueueDepth` - Number of messages in queue
- `ProcessingLatency` - End-to-end processing time
- `ErrorCount` / `SuccessCount` - Processing outcomes
- `ONDCSubmissionStatus` - ONDC API success/failure
- `ProcessingCost` - Per-entry cost tracking


#### Alarms
- **OrchestratorDurationAlarm**: Alert if processing > 60s
- **ApiHandlerDurationAlarm**: Alert if API response > 30s
- **ErrorRateAlarm**: Alert if error rate > 5% over 10 minutes
- **CostThresholdAlarm**: Alert if processing cost > $0.50 per entry
- **QueueDepthAlarm**: Alert if queue depth > 100
- **DLQMessagesAlarm**: Alert if messages in dead letter queue

#### Dashboard
- **Name**: `ArtisanCatalogSystemHealth`
- **Widgets**: Queue depth, latency, errors, Lambda duration, ONDC status, costs

---

## IAM Roles and Permissions

### Lambda Execution Role

**Role Name**: `VernacularArtisanCatalogStack-LambdaExecutionRole`

**Managed Policies**:
- `AWSLambdaBasicExecutionRole` - CloudWatch Logs access
- `AWSXRayDaemonWriteAccess` - X-Ray tracing

**Inline Policies**:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      "Resource": [
        "arn:aws:s3:::artisan-catalog-raw-media-*/*",
        "arn:aws:s3:::artisan-catalog-enhanced-*/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:Query",
        "dynamodb:Scan"
      ],
      "Resource": [
        "arn:aws:dynamodb:*:*:table/CatalogProcessingRecords",
        "arn:aws:dynamodb:*:*:table/CatalogProcessingRecords/index/*",
        "arn:aws:dynamodb:*:*:table/LocalQueueEntries",
        "arn:aws:dynamodb:*:*:table/LocalQueueEntries/index/*",
        "arn:aws:dynamodb:*:*:table/TenantConfigurations",
        "arn:aws:dynamodb:*:*:table/ArtisanProfiles",
        "arn:aws:dynamodb:*:*:table/ArtisanProfiles/index/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "sqs:SendMessage",
        "sqs:ReceiveMessage",
        "sqs:DeleteMessage",
        "sqs:GetQueueAttributes"
      ],
      "Resource": "arn:aws:sqs:*:*:catalog-processing-queue"
    },
    {
      "Effect": "Allow",
      "Action": [
        "sagemaker:InvokeEndpoint"
      ],
      "Resource": "arn:aws:sagemaker:*:*:endpoint/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "sns:Publish"
      ],
      "Resource": "arn:aws:sns:*:*:artisan-catalog-alarms"
    }
  ]
}
```


### Sagemaker Execution Role

**Role Name**: `SagemakerExecutionRole`

**Managed Policies**:
- `AmazonSageMakerFullAccess`

**Inline Policies**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject"
      ],
      "Resource": [
        "arn:aws:s3:::artisan-catalog-raw-media-*/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage"
      ],
      "Resource": "*"
    }
  ]
}
```

### Deployment User/Role

For CI/CD pipelines, create a deployment role with:
- `AWSCloudFormationFullAccess`
- `IAMFullAccess`
- `AmazonS3FullAccess`
- `AWSLambda_FullAccess`
- `AmazonDynamoDBFullAccess`
- `AmazonSQSFullAccess`
- `AmazonAPIGatewayAdministrator`
- `CloudWatchFullAccess`

---

## Environment Variables and Secrets

### Lambda Environment Variables

Both Lambda functions receive these environment variables:

```bash
# AWS Configuration
AWS_REGION=ap-south-1

# S3 Buckets
S3_RAW_MEDIA_BUCKET=artisan-catalog-raw-media-123456789
S3_ENHANCED_BUCKET=artisan-catalog-enhanced-123456789

# DynamoDB Tables
DYNAMODB_CATALOG_TABLE=CatalogProcessingRecords
DYNAMODB_LOCAL_QUEUE_TABLE=LocalQueueEntries
DYNAMODB_TENANT_TABLE=TenantConfigurations
DYNAMODB_ARTISAN_TABLE=ArtisanProfiles

# SQS Queue
SQS_QUEUE_URL=https://sqs.ap-south-1.amazonaws.com/123456789/catalog-processing-queue

# SNS Topic
SNS_NOTIFICATION_TOPIC_ARN=arn:aws:sns:ap-south-1:123456789:artisan-catalog-alarms

# Logging
LOG_LEVEL=INFO
```


### AWS Secrets Manager (for sensitive data)

Store sensitive configuration in AWS Secrets Manager:

```bash
# Create secret for ONDC credentials
aws secretsmanager create-secret \
  --name artisan-catalog/ondc-credentials \
  --description "ONDC API credentials" \
  --secret-string '{
    "api_key": "YOUR_ONDC_API_KEY",
    "seller_id": "YOUR_SELLER_ID",
    "api_endpoint": "https://api.ondc.org"
  }'

# Create secret for Sagemaker endpoint
aws secretsmanager create-secret \
  --name artisan-catalog/sagemaker-config \
  --description "Sagemaker endpoint configuration" \
  --secret-string '{
    "endpoint_name": "artisan-vision-asr-endpoint",
    "region": "ap-south-1"
  }'

# Grant Lambda permission to read secrets
aws iam attach-role-policy \
  --role-name VernacularArtisanCatalogStack-LambdaExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/SecretsManagerReadWrite
```

### Accessing Secrets in Lambda

```python
import boto3
import json

def get_secret(secret_name):
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])

# Usage
ondc_creds = get_secret('artisan-catalog/ondc-credentials')
api_key = ondc_creds['api_key']
```

### Local Development (.env file)

For local testing, create a `.env` file:

```bash
# Copy template
cp .env.example .env

# Edit with your values
AWS_REGION=ap-south-1
AWS_PROFILE=default
S3_RAW_MEDIA_BUCKET=artisan-catalog-raw-media-local
S3_ENHANCED_BUCKET=artisan-catalog-enhanced-local
DYNAMODB_CATALOG_TABLE=CatalogProcessingRecords
SQS_QUEUE_URL=http://localhost:9324/queue/catalog-processing-queue
SAGEMAKER_ENDPOINT_NAME=artisan-vision-asr-endpoint
LOG_LEVEL=DEBUG
```

---

## Deployment Methods

### Method 1: Automated Deployment Script (Recommended)

```bash
# Run the deployment script
./scripts/deploy_infrastructure.sh
```

This script:
1. Checks prerequisites (AWS CLI, Node.js, CDK)
2. Verifies AWS credentials
3. Installs CDK dependencies
4. Bootstraps CDK (first time only)
5. Synthesizes CloudFormation template
6. Deploys the stack


### Method 2: Manual CDK Deployment

```bash
# Navigate to CDK directory
cd backend/infrastructure/cdk

# Install dependencies
npm install

# Bootstrap CDK (first time only, per account/region)
cdk bootstrap aws://ACCOUNT-ID/REGION

# Synthesize CloudFormation template (optional, for review)
cdk synth

# Deploy stack
cdk deploy

# Deploy with context parameters
cdk deploy \
  -c domainName=api.artisan-catalog.com \
  -c alarmEmail=alerts@example.com \
  -c provisionedConcurrency=10
```

### Method 3: CloudFormation Template Deployment

```bash
# Generate CloudFormation template
cd backend/infrastructure/cdk
cdk synth > template.yaml

# Deploy via AWS CLI
aws cloudformation create-stack \
  --stack-name VernacularArtisanCatalogStack \
  --template-body file://template.yaml \
  --capabilities CAPABILITY_IAM

# Monitor deployment
aws cloudformation describe-stacks \
  --stack-name VernacularArtisanCatalogStack \
  --query 'Stacks[0].StackStatus'
```

### CDK Context Parameters

Optional parameters for customization:

| Parameter | Description | Example |
|-----------|-------------|---------|
| `domainName` | Custom domain for API Gateway | `api.artisan-catalog.com` |
| `alarmEmail` | Email for CloudWatch alarms | `alerts@example.com` |
| `provisionedConcurrency` | Warm Lambda instances | `10` |

**Usage:**
```bash
cdk deploy \
  -c domainName=api.artisan-catalog.com \
  -c alarmEmail=alerts@example.com
```

---

## CI/CD Pipeline Configuration

### GitHub Actions Workflow

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to AWS

on:
  push:
    branches:
      - main
  workflow_dispatch:

env:
  AWS_REGION: ap-south-1
  NODE_VERSION: '18'
  PYTHON_VERSION: '3.11'

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: ${{ env.NODE_VERSION }}
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION }}
      
      - name: Install CDK
        run: npm install -g aws-cdk
      
      - name: Install dependencies
        run: |
          cd backend/infrastructure/cdk
          npm install
      
      - name: CDK Synth
        run: |
          cd backend/infrastructure/cdk
          cdk synth
      
      - name: CDK Deploy
        run: |
          cd backend/infrastructure/cdk
          cdk deploy --require-approval never
      
      - name: Package Lambda functions
        run: |
          cd backend/lambda_functions
          ./package_lambdas.sh
      
      - name: Run integration tests
        run: |
          pytest tests/integration/ -v
```


### AWS CodePipeline Configuration

For AWS-native CI/CD:

```yaml
# buildspec.yml
version: 0.2

phases:
  install:
    runtime-versions:
      nodejs: 18
      python: 3.11
    commands:
      - npm install -g aws-cdk
      - pip install -r requirements.txt
  
  pre_build:
    commands:
      - echo "Running tests..."
      - pytest tests/unit/ -v
  
  build:
    commands:
      - echo "Deploying infrastructure..."
      - cd backend/infrastructure/cdk
      - npm install
      - cdk deploy --require-approval never
  
  post_build:
    commands:
      - echo "Running integration tests..."
      - pytest tests/integration/ -v

artifacts:
  files:
    - '**/*'
```

**Create CodePipeline:**
```bash
# Create CodeCommit repository
aws codecommit create-repository \
  --repository-name vernacular-artisan-catalog

# Create CodeBuild project
aws codebuild create-project \
  --name artisan-catalog-build \
  --source type=CODECOMMIT,location=https://git-codecommit.ap-south-1.amazonaws.com/v1/repos/vernacular-artisan-catalog \
  --artifacts type=NO_ARTIFACTS \
  --environment type=LINUX_CONTAINER,image=aws/codebuild/standard:7.0,computeType=BUILD_GENERAL1_SMALL \
  --service-role arn:aws:iam::ACCOUNT-ID:role/CodeBuildServiceRole

# Create CodePipeline
aws codepipeline create-pipeline \
  --cli-input-json file://pipeline-config.json
```

---

## Post-Deployment Configuration

### 1. Retrieve CDK Outputs

After deployment, CDK outputs important values:

```bash
# Get stack outputs
aws cloudformation describe-stacks \
  --stack-name VernacularArtisanCatalogStack \
  --query 'Stacks[0].Outputs'
```

**Expected Outputs:**
- `ApiUrl` - API Gateway endpoint URL
- `RawBucketName` - S3 raw media bucket name
- `EnhancedBucketName` - S3 enhanced media bucket name
- `ApiKeyId` - API Gateway API key ID
- `AlarmTopicArn` - SNS topic ARN for alarms
- `DashboardUrl` - CloudWatch dashboard URL

### 2. Retrieve API Key Value

```bash
# Get API key value (needed for client authentication)
aws apigateway get-api-key \
  --api-key API_KEY_ID \
  --include-value \
  --query 'value' \
  --output text
```

Save this value securely and provide it to mobile clients.


### 3. Deploy Sagemaker Endpoint

Follow the [Sagemaker Endpoint Deployment Guide](./SAGEMAKER_ENDPOINT_DEPLOYMENT.md):

```bash
# Deploy Sagemaker endpoint
cd backend/sagemaker
python deploy_endpoint.py

# Update Lambda environment with endpoint name
aws lambda update-function-configuration \
  --function-name artisan-catalog-orchestrator \
  --environment Variables={SAGEMAKER_ENDPOINT_NAME=artisan-vision-asr-endpoint}
```

### 4. Enable Bedrock Model Access

```bash
# Request Bedrock model access (via console or CLI)
# Go to: AWS Console > Bedrock > Model access
# Enable: Claude 3 Sonnet, Titan Text

# Verify access
aws bedrock list-foundation-models --region us-east-1
```

### 5. Configure SNS Email Subscription

```bash
# Subscribe email to alarm topic
aws sns subscribe \
  --topic-arn arn:aws:sns:ap-south-1:ACCOUNT-ID:artisan-catalog-alarms \
  --protocol email \
  --notification-endpoint alerts@example.com

# Confirm subscription via email
```

### 6. Create Initial Tenant Configuration

```bash
# Insert tenant configuration into DynamoDB
aws dynamodb put-item \
  --table-name TenantConfigurations \
  --item '{
    "tenant_id": {"S": "tenant-001"},
    "tenant_name": {"S": "Artisan Cooperative 1"},
    "language_preferences": {"L": [{"S": "hi"}, {"S": "ta"}]},
    "ondc_seller_id": {"S": "SELLER123"},
    "quota_daily_uploads": {"N": "1000"},
    "created_at": {"S": "2024-01-01T00:00:00Z"}
  }'
```

### 7. Test Deployment

```bash
# Test API endpoint
curl -X POST https://API_URL/v1/catalog/upload/initiate \
  -H "x-api-key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "tenantId": "tenant-001",
    "artisanId": "artisan-001",
    "contentType": "multipart/form-data"
  }'

# Expected response:
# {
#   "trackingId": "uuid-here",
#   "uploadUrl": "https://...",
#   "expiresAt": "2024-01-01T01:00:00Z"
# }
```

### 8. Update Mobile Client Configuration

Update mobile app with deployed values:

```typescript
// mobile/src/config/aws.ts
export const AWS_CONFIG = {
  apiUrl: 'https://YOUR_API_URL/v1',
  apiKey: 'YOUR_API_KEY',
  region: 'ap-south-1'
};
```

---

## Monitoring and Observability

### CloudWatch Dashboard

Access the dashboard:
```
https://console.aws.amazon.com/cloudwatch/home?region=ap-south-1#dashboards:name=ArtisanCatalogSystemHealth
```

**Key Metrics to Monitor:**
- Queue depth (should be < 100)
- Processing latency (p95 < 120s)
- Error rate (should be < 5%)
- Lambda duration (API < 30s, Orchestrator < 60s)
- ONDC submission success rate
- Processing cost per entry


### CloudWatch Logs Insights Queries

**Query 1: Error Analysis**
```sql
fields @timestamp, @message
| filter @message like /ERROR/
| sort @timestamp desc
| limit 100
```

**Query 2: Processing Latency**
```sql
fields @timestamp, tracking_id, processing_latency
| filter @message like /Processing completed/
| stats avg(processing_latency), max(processing_latency), min(processing_latency) by bin(5m)
```

**Query 3: ONDC Submission Failures**
```sql
fields @timestamp, tracking_id, error_message
| filter stage = "ondc_submission" and status = "failed"
| sort @timestamp desc
```

### X-Ray Tracing

View distributed traces:
```
https://console.aws.amazon.com/xray/home?region=ap-south-1#/traces
```

**Trace Analysis:**
- Identify slow components (ASR, Vision, Bedrock)
- Detect bottlenecks in processing pipeline
- Analyze error patterns across services

### Custom Metrics

Emit custom metrics from Lambda:

```python
import boto3

cloudwatch = boto3.client('cloudwatch')

def emit_metric(metric_name, value, unit='Count', dimensions=None):
    cloudwatch.put_metric_data(
        Namespace='VernacularArtisanCatalog',
        MetricData=[{
            'MetricName': metric_name,
            'Value': value,
            'Unit': unit,
            'Dimensions': dimensions or []
        }]
    )

# Usage
emit_metric('ProcessingLatency', 45.2, 'Seconds')
emit_metric('ProcessingCost', 0.35, 'None', [
    {'Name': 'Operation', 'Value': 'sagemaker'}
])
```

### Alarm Actions

Configure alarm actions:

```bash
# Add SNS action to alarm
aws cloudwatch put-metric-alarm \
  --alarm-name high-error-rate \
  --alarm-description "Alert when error rate exceeds 5%" \
  --metric-name ErrorCount \
  --namespace VernacularArtisanCatalog \
  --statistic Sum \
  --period 600 \
  --threshold 50 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --alarm-actions arn:aws:sns:ap-south-1:ACCOUNT-ID:artisan-catalog-alarms
```

---

## Security Configuration

### 1. Encryption

**At Rest:**
- S3: AES-256 (S3-managed keys)
- DynamoDB: AWS-managed encryption
- SQS: SQS-managed encryption

**In Transit:**
- API Gateway: TLS 1.2+ enforced
- S3: HTTPS-only (enforceSSL: true)
- All AWS service communication: TLS 1.2+


### 2. Network Security

**VPC Configuration (Optional):**

For enhanced security, deploy Lambda in VPC:

```typescript
// Add to CDK stack
const vpc = new ec2.Vpc(this, 'VPC', {
  maxAzs: 2,
  natGateways: 1
});

const lambdaSecurityGroup = new ec2.SecurityGroup(this, 'LambdaSG', {
  vpc,
  description: 'Security group for Lambda functions',
  allowAllOutbound: true
});

// Update Lambda configuration
const orchestratorLambda = new lambda.Function(this, 'Orchestrator', {
  // ... existing config
  vpc: vpc,
  securityGroups: [lambdaSecurityGroup],
  vpcSubnets: {
    subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS
  }
});
```

**Note:** VPC deployment increases cold start time and requires NAT Gateway (additional cost).

### 3. API Security

**API Key Rotation:**
```bash
# Create new API key
aws apigateway create-api-key \
  --name artisan-catalog-api-key-v2 \
  --enabled

# Associate with usage plan
aws apigateway create-usage-plan-key \
  --usage-plan-id USAGE_PLAN_ID \
  --key-id NEW_API_KEY_ID \
  --key-type API_KEY

# Revoke old key after migration
aws apigateway update-api-key \
  --api-key OLD_API_KEY_ID \
  --patch-operations op=replace,path=/enabled,value=false
```

**WAF Integration (Optional):**
```bash
# Create WAF Web ACL
aws wafv2 create-web-acl \
  --name artisan-catalog-waf \
  --scope REGIONAL \
  --default-action Allow={} \
  --rules file://waf-rules.json

# Associate with API Gateway
aws wafv2 associate-web-acl \
  --web-acl-arn WAF_ACL_ARN \
  --resource-arn API_GATEWAY_ARN
```

### 4. IAM Best Practices

**Least Privilege:**
- Lambda roles have minimal required permissions
- No wildcard (*) resources where possible
- Separate roles for different functions

**Audit:**
```bash
# Review IAM policies
aws iam get-role-policy \
  --role-name VernacularArtisanCatalogStack-LambdaExecutionRole \
  --policy-name inline-policy

# Check for overly permissive policies
aws iam simulate-principal-policy \
  --policy-source-arn ROLE_ARN \
  --action-names s3:DeleteBucket \
  --resource-arns arn:aws:s3:::*
```

### 5. Secrets Management

**Rotate Secrets:**
```bash
# Enable automatic rotation for secrets
aws secretsmanager rotate-secret \
  --secret-id artisan-catalog/ondc-credentials \
  --rotation-lambda-arn ROTATION_LAMBDA_ARN \
  --rotation-rules AutomaticallyAfterDays=30
```

### 6. Compliance

**Enable AWS Config:**
```bash
# Enable Config to track resource compliance
aws configservice put-configuration-recorder \
  --configuration-recorder name=default,roleARN=CONFIG_ROLE_ARN

aws configservice put-delivery-channel \
  --delivery-channel name=default,s3BucketName=config-bucket
```

**Enable CloudTrail:**
```bash
# Enable CloudTrail for audit logging
aws cloudtrail create-trail \
  --name artisan-catalog-trail \
  --s3-bucket-name cloudtrail-bucket

aws cloudtrail start-logging \
  --name artisan-catalog-trail
```

---

## Cost Optimization

### 1. S3 Cost Optimization

**Intelligent Tiering:**
- Automatically moves objects to cheaper storage classes
- Configured in CDK stack (7-day transition)

**Lifecycle Policies:**
- 30-day expiration (privacy requirement)
- Reduces storage costs for old media

### 2. Lambda Cost Optimization

**Right-sizing:**
```bash
# Analyze Lambda memory usage
aws lambda get-function \
  --function-name artisan-catalog-orchestrator \
  --query 'Configuration.MemorySize'

# Adjust if needed
aws lambda update-function-configuration \
  --function-name artisan-catalog-orchestrator \
  --memory-size 768  # Reduce from 1024 if underutilized
```

**Provisioned Concurrency:**
- Only enable for API handler if cold starts are an issue
- Cost: ~$0.015/hour per provisioned instance
- Trade-off: Consistent latency vs. cost


### 3. DynamoDB Cost Optimization

**On-Demand vs. Provisioned:**
- Current: On-demand (pay-per-request)
- Switch to provisioned if traffic is predictable

```bash
# Switch to provisioned capacity
aws dynamodb update-table \
  --table-name CatalogProcessingRecords \
  --billing-mode PROVISIONED \
  --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5

# Enable auto-scaling
aws application-autoscaling register-scalable-target \
  --service-namespace dynamodb \
  --resource-id table/CatalogProcessingRecords \
  --scalable-dimension dynamodb:table:WriteCapacityUnits \
  --min-capacity 5 \
  --max-capacity 100
```

### 4. Sagemaker Cost Optimization

**Auto-scaling:**
```python
# Configure endpoint auto-scaling
import boto3

client = boto3.client('application-autoscaling')

# Register scalable target
client.register_scalable_target(
    ServiceNamespace='sagemaker',
    ResourceId='endpoint/artisan-vision-asr-endpoint/variant/AllTraffic',
    ScalableDimension='sagemaker:variant:DesiredInstanceCount',
    MinCapacity=1,
    MaxCapacity=5
)

# Create scaling policy
client.put_scaling_policy(
    PolicyName='sagemaker-scaling-policy',
    ServiceNamespace='sagemaker',
    ResourceId='endpoint/artisan-vision-asr-endpoint/variant/AllTraffic',
    ScalableDimension='sagemaker:variant:DesiredInstanceCount',
    PolicyType='TargetTrackingScaling',
    TargetTrackingScalingPolicyConfiguration={
        'TargetValue': 70.0,
        'PredefinedMetricSpecification': {
            'PredefinedMetricType': 'SageMakerVariantInvocationsPerInstance'
        }
    }
)
```

**Serverless Inference (Alternative):**
- For low/variable traffic, use Sagemaker Serverless
- Pay only for inference time
- No idle instance costs

### 5. Cost Monitoring

**Set up Budget Alerts:**
```bash
# Create budget
aws budgets create-budget \
  --account-id ACCOUNT_ID \
  --budget file://budget.json \
  --notifications-with-subscribers file://notifications.json
```

**budget.json:**
```json
{
  "BudgetName": "ArtisanCatalogMonthlyBudget",
  "BudgetLimit": {
    "Amount": "500",
    "Unit": "USD"
  },
  "TimeUnit": "MONTHLY",
  "BudgetType": "COST",
  "CostFilters": {
    "TagKeyValue": ["user:Project$VernacularArtisanCatalog"]
  }
}
```

**Cost Allocation Tags:**
```bash
# Tag resources for cost tracking
aws resourcegroupstaggingapi tag-resources \
  --resource-arn-list \
    arn:aws:lambda:ap-south-1:ACCOUNT-ID:function:artisan-catalog-* \
  --tags Project=VernacularArtisanCatalog,Environment=Production
```

### 6. Estimated Monthly Costs

**Assumptions:**
- 10,000 catalog entries/month
- Average processing time: 60s
- Sagemaker: 1 instance running 24/7

| Service | Usage | Cost |
|---------|-------|------|
| Lambda (API Handler) | 10,000 invocations × 30s × 512MB | $0.50 |
| Lambda (Orchestrator) | 10,000 invocations × 60s × 1024MB | $2.00 |
| API Gateway | 10,000 requests | $0.04 |
| S3 Storage | 50GB × 2 buckets | $2.30 |
| S3 Requests | 20,000 PUT/GET | $0.10 |
| DynamoDB | 10,000 writes, 50,000 reads | $1.50 |
| SQS | 10,000 messages | $0.00 (free tier) |
| Sagemaker | ml.g4dn.xlarge × 730 hours | $530.00 |
| Bedrock | 10,000 invocations × 1000 tokens | $30.00 |
| CloudWatch | Logs + metrics | $5.00 |
| **Total** | | **~$571/month** |

**Cost Reduction Strategies:**
- Use Sagemaker Serverless: Save ~$500/month for low traffic
- Batch processing: Reduce Lambda invocations
- Optimize Bedrock prompts: Reduce token usage

---

## Troubleshooting

### Common Issues

#### 1. CDK Bootstrap Failure

**Error:** `CDK bootstrap failed: Access Denied`

**Solution:**
```bash
# Ensure IAM user has required permissions
aws iam attach-user-policy \
  --user-name YOUR_USER \
  --policy-arn arn:aws:iam::aws:policy/AdministratorAccess

# Retry bootstrap
cdk bootstrap
```


#### 2. Lambda Timeout

**Error:** `Task timed out after 300.00 seconds`

**Solution:**
```bash
# Increase Lambda timeout
aws lambda update-function-configuration \
  --function-name artisan-catalog-orchestrator \
  --timeout 600

# Or optimize processing:
# - Reduce image size before Sagemaker inference
# - Use smaller Bedrock models
# - Implement parallel processing
```

#### 3. Sagemaker Endpoint Not Found

**Error:** `Could not find endpoint: artisan-vision-asr-endpoint`

**Solution:**
```bash
# Check if endpoint exists
aws sagemaker describe-endpoint \
  --endpoint-name artisan-vision-asr-endpoint

# If not found, deploy endpoint
cd backend/sagemaker
python deploy_endpoint.py

# Update Lambda environment variable
aws lambda update-function-configuration \
  --function-name artisan-catalog-orchestrator \
  --environment Variables={SAGEMAKER_ENDPOINT_NAME=artisan-vision-asr-endpoint}
```

#### 4. API Gateway 403 Forbidden

**Error:** `{"message":"Forbidden"}`

**Solution:**
```bash
# Check if API key is provided
curl -H "x-api-key: YOUR_API_KEY" https://API_URL/v1/catalog/status/test

# Verify API key is associated with usage plan
aws apigateway get-usage-plan-keys \
  --usage-plan-id USAGE_PLAN_ID

# If not associated, add it
aws apigateway create-usage-plan-key \
  --usage-plan-id USAGE_PLAN_ID \
  --key-id API_KEY_ID \
  --key-type API_KEY
```

#### 5. DynamoDB Throttling

**Error:** `ProvisionedThroughputExceededException`

**Solution:**
```bash
# Switch to on-demand billing (if using provisioned)
aws dynamodb update-table \
  --table-name CatalogProcessingRecords \
  --billing-mode PAY_PER_REQUEST

# Or increase provisioned capacity
aws dynamodb update-table \
  --table-name CatalogProcessingRecords \
  --provisioned-throughput ReadCapacityUnits=10,WriteCapacityUnits=10
```

#### 6. S3 Access Denied

**Error:** `An error occurred (AccessDenied) when calling the PutObject operation`

**Solution:**
```bash
# Check Lambda role has S3 permissions
aws iam get-role-policy \
  --role-name VernacularArtisanCatalogStack-LambdaExecutionRole \
  --policy-name S3Access

# Add S3 permissions if missing
aws iam put-role-policy \
  --role-name VernacularArtisanCatalogStack-LambdaExecutionRole \
  --policy-name S3Access \
  --policy-document file://s3-policy.json
```

#### 7. Bedrock Access Denied

**Error:** `AccessDeniedException: You don't have access to the model`

**Solution:**
```bash
# Request model access in Bedrock console
# Go to: AWS Console > Bedrock > Model access
# Enable: Claude 3 Sonnet, Titan Text

# Verify access
aws bedrock list-foundation-models --region us-east-1

# Ensure Lambda role has Bedrock permissions
aws iam put-role-policy \
  --role-name VernacularArtisanCatalogStack-LambdaExecutionRole \
  --policy-name BedrockAccess \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": ["bedrock:InvokeModel"],
      "Resource": "*"
    }]
  }'
```

### Debugging Tips

**1. Enable Debug Logging:**
```bash
aws lambda update-function-configuration \
  --function-name artisan-catalog-orchestrator \
  --environment Variables={LOG_LEVEL=DEBUG}
```

**2. View Lambda Logs:**
```bash
# Stream logs in real-time
aws logs tail /aws/lambda/artisan-catalog-orchestrator --follow

# Query specific errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/artisan-catalog-orchestrator \
  --filter-pattern "ERROR"
```

**3. Test Lambda Locally:**
```bash
# Use SAM CLI for local testing
sam local invoke artisan-catalog-orchestrator \
  --event test-event.json
```

**4. Check X-Ray Traces:**
```bash
# Get trace summaries
aws xray get-trace-summaries \
  --start-time $(date -u -d '1 hour ago' +%s) \
  --end-time $(date -u +%s)

# Get specific trace
aws xray batch-get-traces \
  --trace-ids TRACE_ID
```

### Support Resources

- **AWS Documentation**: https://docs.aws.amazon.com/
- **CDK Documentation**: https://docs.aws.amazon.com/cdk/
- **Sagemaker Documentation**: https://docs.aws.amazon.com/sagemaker/
- **Bedrock Documentation**: https://docs.aws.amazon.com/bedrock/
- **Project Repository**: [GitHub Link]
- **Issue Tracker**: [GitHub Issues]

---

## Appendix

### A. Resource Naming Conventions

| Resource Type | Naming Pattern | Example |
|---------------|----------------|---------|
| S3 Bucket | `artisan-catalog-{purpose}-{account-id}` | `artisan-catalog-raw-media-123456789` |
| Lambda Function | `artisan-catalog-{purpose}` | `artisan-catalog-api-handler` |
| DynamoDB Table | `{PascalCase}` | `CatalogProcessingRecords` |
| SQS Queue | `{kebab-case}` | `catalog-processing-queue` |
| IAM Role | `{StackName}-{Purpose}Role` | `VernacularArtisanCatalogStack-LambdaExecutionRole` |
| CloudWatch Alarm | `artisan-catalog-{metric}` | `artisan-catalog-error-rate` |

### B. Region Selection

**Recommended Regions:**
- **Primary**: `ap-south-1` (Mumbai) - Closest to target users in India
- **Bedrock**: `us-east-1` or `us-west-2` - Bedrock availability
- **Sagemaker**: Same as primary region

**Multi-Region Considerations:**
- Use CloudFront for global API distribution
- Replicate S3 buckets for disaster recovery
- DynamoDB Global Tables for multi-region writes

### C. Disaster Recovery

**Backup Strategy:**
- DynamoDB: Point-in-time recovery enabled
- S3: Versioning + cross-region replication (optional)
- Lambda: Code stored in version control

**Recovery Procedures:**
```bash
# Restore DynamoDB table
aws dynamodb restore-table-to-point-in-time \
  --source-table-name CatalogProcessingRecords \
  --target-table-name CatalogProcessingRecords-Restored \
  --restore-date-time 2024-01-01T00:00:00Z

# Redeploy infrastructure
cdk deploy --force
```

### D. Compliance Checklist

- [ ] Encryption at rest enabled (S3, DynamoDB, SQS)
- [ ] Encryption in transit enforced (TLS 1.2+)
- [ ] IAM roles follow least privilege
- [ ] CloudTrail logging enabled
- [ ] CloudWatch alarms configured
- [ ] API rate limiting enabled
- [ ] Data retention policies configured (30 days)
- [ ] Backup and recovery tested
- [ ] Security group rules reviewed
- [ ] API keys rotated regularly

---

## Conclusion

This guide provides comprehensive instructions for deploying the Vernacular Artisan Catalog on AWS. For additional support, refer to the project documentation or contact the development team.

**Next Steps:**
1. Complete prerequisites
2. Run deployment script
3. Configure post-deployment settings
4. Test the deployment
5. Monitor system health
6. Optimize costs

**Deployment Checklist:**
- [ ] AWS CLI configured
- [ ] CDK installed
- [ ] Infrastructure deployed
- [ ] Sagemaker endpoint deployed
- [ ] Bedrock access enabled
- [ ] API key retrieved
- [ ] SNS email subscribed
- [ ] Tenant configuration created
- [ ] Mobile client updated
- [ ] Integration tests passed
- [ ] Monitoring dashboard reviewed
- [ ] Cost alerts configured

For questions or issues, please refer to the troubleshooting section or open an issue in the project repository.
