# AWS Setup Flowchart

```
┌─────────────────────────────────────────────────────────────┐
│                    START: AWS Setup                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 1: Create AWS Account                                 │
│  ✓ Go to aws.amazon.com                                     │
│  ✓ Sign up with email                                       │
│  ✓ Add payment method                                       │
│  ✓ Verify identity                                          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 2: Create IAM User                                    │
│  ✓ Go to IAM Console                                        │
│  ✓ Create user: artisan-catalog-admin                       │
│  ✓ Attach policy: AdministratorAccess                       │
│  ✓ Save console sign-in URL                                 │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 3: Create Access Keys                                 │
│  ✓ Go to IAM > Users > Security credentials                 │
│  ✓ Create access key for CLI                                │
│  ✓ Download CSV file                                        │
│  ✓ Store securely (NEVER commit to Git!)                    │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 4: Install & Configure AWS CLI                        │
│  ✓ Install AWS CLI v2                                       │
│  ✓ Run: aws configure                                       │
│  ✓ Enter Access Key ID                                      │
│  ✓ Enter Secret Access Key                                  │
│  ✓ Set region: ap-south-1                                   │
│  ✓ Test: aws sts get-caller-identity                        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 5: Get AWS Account ID                                 │
│  ✓ Run: aws sts get-caller-identity --query Account         │
│  ✓ Copy the 12-digit number                                 │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 6: Enable Bedrock                                     │
│  ✓ Go to Bedrock Console                                    │
│  ✓ Click "Model access"                                     │
│  ✓ Enable Claude 3 Sonnet                                   │
│  ✓ Wait for approval (instant)                              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 7: Fill .env File                                     │
│  ✓ Copy .env.example to .env                                │
│  ✓ Add AWS_ACCOUNT_ID                                       │
│  ✓ Add AWS_REGION                                           │
│  ✓ Update bucket names with account ID                      │
│  ✓ Add ONDC credentials (if available)                      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 8: Verify Setup                                       │
│  ✓ Run: aws sts get-caller-identity                         │
│  ✓ Run: aws s3 ls                                           │
│  ✓ Run: aws bedrock list-foundation-models                  │
│  ✓ Check .env file is complete                              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                 ✅ SETUP COMPLETE!                          │
│                                                              │
│  Next: Deploy Infrastructure                                │
│  Run: cd backend/infrastructure/cdk && cdk deploy           │
└─────────────────────────────────────────────────────────────┘
```

## Quick Reference: What Goes Where

```
┌──────────────────────┐
│   AWS Console        │  → Create IAM User
│   (Web Browser)      │  → Get Access Keys
│                      │  → Enable Bedrock
└──────────────────────┘
           │
           ▼
┌──────────────────────┐
│   ~/.aws/            │  → Store credentials
│   credentials        │  → Access Key ID
│                      │  → Secret Access Key
└──────────────────────┘
           │
           ▼
┌──────────────────────┐
│   .env file          │  → AWS_ACCOUNT_ID
│   (Project root)     │  → AWS_REGION
│                      │  → Bucket names
│                      │  → ONDC credentials
└──────────────────────┘
```

## Credential Flow

```
AWS Console
    │
    ├─→ Create IAM User
    │       │
    │       └─→ Generate Access Keys
    │               │
    │               ├─→ Access Key ID: AKIAIOSFODNN7EXAMPLE
    │               └─→ Secret Key: wJalrXUtnFEMI/K7MDENG/...
    │
    └─→ Get Account ID: 123456789012

                ↓

AWS CLI Configuration
    │
    ├─→ aws configure
    │       ├─→ Enter Access Key ID
    │       ├─→ Enter Secret Access Key
    │       ├─→ Enter Region (ap-south-1)
    │       └─→ Enter Output format (json)
    │
    └─→ Stored in ~/.aws/credentials

                ↓

Project .env File
    │
    ├─→ AWS_ACCOUNT_ID=123456789012
    ├─→ AWS_REGION=ap-south-1
    ├─→ S3_RAW_MEDIA_BUCKET=artisan-catalog-raw-media-123456789012
    └─→ S3_ENHANCED_BUCKET=artisan-catalog-enhanced-123456789012

                ↓

CDK Deployment
    │
    └─→ Creates all AWS resources automatically
```

## Service Dependencies

```
┌─────────────────────────────────────────────────────────────┐
│                     AWS Services Used                        │
└─────────────────────────────────────────────────────────────┘

Required for Deployment:
    ├─→ IAM (Identity & Access Management)
    ├─→ CloudFormation (Infrastructure as Code)
    └─→ S3 (CDK Bootstrap bucket)

Created by CDK:
    ├─→ Lambda (API Handler + Orchestrator)
    ├─→ API Gateway (REST API)
    ├─→ S3 (Raw + Enhanced media buckets)
    ├─→ DynamoDB (Catalog + Tenant tables)
    ├─→ SQS (Processing queue)
    ├─→ CloudWatch (Logs + Metrics + Alarms)
    └─→ X-Ray (Distributed tracing)

Configured Separately:
    ├─→ SageMaker (Vision + ASR endpoint)
    └─→ Bedrock (LLM for transcreation)
```

## Time Estimates

```
Task                                    Time
─────────────────────────────────────────────
Create AWS Account                      10 min
Create IAM User                         5 min
Generate Access Keys                    2 min
Install AWS CLI                         5 min
Configure AWS CLI                       2 min
Enable Bedrock                          3 min
Fill .env file                          5 min
Verify setup                            3 min
─────────────────────────────────────────────
TOTAL                                   35 min
```

## Common Paths

```
AWS Console URLs:
├─→ IAM: https://console.aws.amazon.com/iam
├─→ Bedrock: https://console.aws.amazon.com/bedrock
├─→ Lambda: https://console.aws.amazon.com/lambda
├─→ S3: https://console.aws.amazon.com/s3
└─→ CloudWatch: https://console.aws.amazon.com/cloudwatch

Local Files:
├─→ Credentials: ~/.aws/credentials
├─→ Config: ~/.aws/config
├─→ Project env: .env
└─→ Backup: .env.backup
```
