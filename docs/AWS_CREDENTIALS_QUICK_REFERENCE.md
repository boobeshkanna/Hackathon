# AWS Credentials Quick Reference

## Quick Commands

### Get Your AWS Account ID
```bash
aws sts get-caller-identity --query Account --output text
```

### Get Your Current Region
```bash
aws configure get region
```

### Test Your AWS Access
```bash
aws sts get-caller-identity
```

### List Your Access Keys
```bash
aws iam list-access-keys --user-name YOUR_USERNAME
```

---

## .env File Template

Copy this and fill in your values:

```bash
# ============================================
# AWS CONFIGURATION
# ============================================
# Get Account ID: aws sts get-caller-identity --query Account --output text
AWS_REGION=ap-south-1
AWS_ACCOUNT_ID=YOUR_ACCOUNT_ID_HERE

# ============================================
# S3 BUCKETS (Auto-created by CDK)
# ============================================
S3_RAW_MEDIA_BUCKET=artisan-catalog-raw-media-YOUR_ACCOUNT_ID
S3_ENHANCED_BUCKET=artisan-catalog-enhanced-YOUR_ACCOUNT_ID

# ============================================
# DYNAMODB TABLES (Auto-created by CDK)
# ============================================
DYNAMODB_CATALOG_TABLE=CatalogProcessingRecords
DYNAMODB_TENANT_TABLE=TenantConfigurations

# ============================================
# SQS QUEUE (Auto-created by CDK)
# ============================================
SQS_QUEUE_URL=https://sqs.ap-south-1.amazonaws.com/YOUR_ACCOUNT_ID/catalog-processing-queue

# ============================================
# SAGEMAKER (Configure after deployment)
# ============================================
SAGEMAKER_ENDPOINT_NAME=vision-asr-endpoint

# ============================================
# BEDROCK (Enable in AWS Console first)
# ============================================
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
BEDROCK_REGION=us-east-1

# ============================================
# ONDC (Get from ONDC portal)
# ============================================
ONDC_API_URL=https://staging.ondc.org/api
ONDC_SELLER_ID=your-seller-id
ONDC_API_KEY=your-api-key

# ============================================
# APPLICATION SETTINGS
# ============================================
LOG_LEVEL=INFO
MAX_UPLOAD_SIZE_MB=10
SUPPORTED_LANGUAGES=hi,te,ta,bn,mr,gu,kn,ml,pa,or
```

---

## Where to Find Each Credential

| Credential | Where to Get It | Command/Link |
|------------|-----------------|--------------|
| **AWS_ACCOUNT_ID** | AWS CLI | `aws sts get-caller-identity --query Account --output text` |
| **AWS_REGION** | Your choice | `ap-south-1` (Mumbai) recommended |
| **Access Key ID** | IAM Console | IAM > Users > Security credentials > Create access key |
| **Secret Access Key** | IAM Console | Shown only once when creating access key |
| **S3 Bucket Names** | Auto-generated | Created by CDK deployment |
| **DynamoDB Tables** | Auto-generated | Created by CDK deployment |
| **SQS Queue URL** | Auto-generated | Created by CDK deployment |
| **SAGEMAKER_ENDPOINT_NAME** | After deployment | Set after deploying SageMaker model |
| **BEDROCK_MODEL_ID** | Bedrock Console | [Bedrock Model Access](https://console.aws.amazon.com/bedrock) |
| **ONDC_SELLER_ID** | ONDC Portal | [ONDC Network](https://ondc.org) |
| **ONDC_API_KEY** | ONDC Portal | [ONDC Network](https://ondc.org) |

---

## AWS Console Links

### IAM (Create Users & Access Keys)
```
https://console.aws.amazon.com/iam
```

### Bedrock (Enable Model Access)
```
https://console.aws.amazon.com/bedrock
```

### CloudFormation (View Deployments)
```
https://console.aws.amazon.com/cloudformation
```

### Lambda (View Functions)
```
https://console.aws.amazon.com/lambda
```

### S3 (View Buckets)
```
https://console.aws.amazon.com/s3
```

### DynamoDB (View Tables)
```
https://console.aws.amazon.com/dynamodb
```

### SageMaker (View Endpoints)
```
https://console.aws.amazon.com/sagemaker
```

### CloudWatch (View Logs & Metrics)
```
https://console.aws.amazon.com/cloudwatch
```

---

## Auto-Fill Script

Run this to automatically fill some values in your .env:

```bash
#!/bin/bash

# Get AWS Account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Get AWS Region
REGION=$(aws configure get region)

# Update .env file
sed -i "s/YOUR_ACCOUNT_ID_HERE/$ACCOUNT_ID/g" .env
sed -i "s/YOUR_ACCOUNT_ID/$ACCOUNT_ID/g" .env
sed -i "s/ap-south-1/$REGION/g" .env

echo "✅ Updated .env with:"
echo "   AWS_ACCOUNT_ID: $ACCOUNT_ID"
echo "   AWS_REGION: $REGION"
echo ""
echo "⚠️  You still need to manually add:"
echo "   - ONDC_SELLER_ID"
echo "   - ONDC_API_KEY"
echo "   - SAGEMAKER_ENDPOINT_NAME (after deployment)"
```

Save as `scripts/update-env.sh` and run:
```bash
chmod +x scripts/update-env.sh
./scripts/update-env.sh
```

---

## Verification Checklist

Run these commands to verify your setup:

```bash
# 1. AWS CLI installed
aws --version

# 2. AWS credentials configured
aws sts get-caller-identity

# 3. Can access S3
aws s3 ls

# 4. Can access DynamoDB
aws dynamodb list-tables --region ap-south-1

# 5. Can access Lambda
aws lambda list-functions --region ap-south-1

# 6. Bedrock access (if enabled)
aws bedrock list-foundation-models --region us-east-1

# 7. Node.js installed
node --version

# 8. Python installed
python3 --version

# 9. AWS CDK installed
cdk --version

# 10. .env file exists
test -f .env && echo "✅ .env exists" || echo "❌ .env missing"
```

---

## Common Issues & Quick Fixes

### Issue: "Unable to locate credentials"
```bash
# Fix: Configure AWS CLI
aws configure
```

### Issue: "Access Denied"
```bash
# Fix: Check IAM permissions
aws iam get-user
aws iam list-attached-user-policies --user-name YOUR_USERNAME
```

### Issue: "Region not found"
```bash
# Fix: Set region explicitly
export AWS_REGION=ap-south-1
aws configure set region ap-south-1
```

### Issue: "Bedrock model not accessible"
```bash
# Fix: Enable model access in console
# Go to: https://console.aws.amazon.com/bedrock
# Click: Model access > Manage model access
# Enable: Claude 3 Sonnet
```

---

## Security Reminders

🔒 **NEVER commit these to Git:**
- `.env` file
- `~/.aws/credentials`
- Access keys in code
- API keys in code

🔒 **Always:**
- Use `.gitignore` to exclude `.env`
- Rotate access keys every 90 days
- Enable MFA on root account
- Use IAM roles instead of access keys when possible

---

## Next Steps After Setup

1. ✅ Verify all credentials are in `.env`
2. ✅ Run verification checklist above
3. ✅ Deploy infrastructure: `cd backend/infrastructure/cdk && cdk deploy`
4. ✅ Deploy SageMaker endpoint (see `docs/SAGEMAKER_ENDPOINT_DEPLOYMENT.md`)
5. ✅ Test API endpoints (see `docs/API_DOCUMENTATION.md`)

---

## Support

- Full setup guide: `docs/AWS_SETUP_GUIDE.md`
- Deployment guide: `docs/AWS_DEPLOYMENT.md`
- API documentation: `docs/API_DOCUMENTATION.md`
- AWS Documentation: https://docs.aws.amazon.com
