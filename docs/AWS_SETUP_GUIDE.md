# AWS Console Setup Guide - Step by Step

This guide will walk you through setting up your AWS account and obtaining all the credentials needed for the Vernacular Artisan Catalog project.

---

## Table of Contents

1. [Create AWS Account](#1-create-aws-account)
2. [Set Up IAM User](#2-set-up-iam-user)
3. [Get AWS Credentials](#3-get-aws-credentials)
4. [Configure AWS CLI](#4-configure-aws-cli)
5. [Get AWS Account ID](#5-get-aws-account-id)
6. [Enable Required AWS Services](#6-enable-required-aws-services)
7. [Fill Your .env File](#7-fill-your-env-file)
8. [Verify Setup](#8-verify-setup)

---

## 1. Create AWS Account

### Step 1.1: Sign Up for AWS

1. Go to [https://aws.amazon.com](https://aws.amazon.com)
2. Click **"Create an AWS Account"** (top right)
3. Enter your email address and choose an AWS account name
4. Click **"Verify email address"**
5. Check your email and enter the verification code
6. Create a strong password for your root account

### Step 1.2: Provide Contact Information

1. Select account type: **"Personal"** or **"Business"**
2. Fill in your contact information:
   - Full name
   - Phone number
   - Address
3. Read and accept the AWS Customer Agreement
4. Click **"Continue"**

### Step 1.3: Add Payment Information

1. Enter your credit/debit card details
2. Enter billing address
3. Click **"Verify and Continue"**
4. AWS will charge $1 for verification (refunded immediately)

### Step 1.4: Verify Your Identity

1. Choose verification method: **SMS** or **Voice call**
2. Enter your phone number
3. Enter the verification code you receive
4. Click **"Continue"**

### Step 1.5: Choose Support Plan

1. Select **"Basic Support - Free"** (sufficient for development)
2. Click **"Complete sign up"**

🎉 Your AWS account is now created!

---

## 2. Set Up IAM User

**IMPORTANT:** Never use your root account for daily operations. Create an IAM user instead.

### Step 2.1: Sign in to AWS Console

1. Go to [https://console.aws.amazon.com](https://console.aws.amazon.com)
2. Click **"Root user"**
3. Enter your root account email
4. Enter your password
5. Click **"Sign in"**

### Step 2.2: Navigate to IAM

1. In the AWS Console search bar (top), type **"IAM"**
2. Click on **"IAM"** (Identity and Access Management)
3. You'll see the IAM Dashboard

### Step 2.3: Create IAM User

1. In the left sidebar, click **"Users"**
2. Click **"Create user"** (orange button, top right)
3. Enter username: `artisan-catalog-admin` (or your preferred name)
4. Check ✅ **"Provide user access to the AWS Management Console"**
5. Select **"I want to create an IAM user"**
6. Choose **"Custom password"** and enter a strong password
7. Uncheck **"Users must create a new password at next sign-in"** (optional)
8. Click **"Next"**

### Step 2.4: Set Permissions

1. Select **"Attach policies directly"**
2. Search and check these policies:
   - ✅ `AdministratorAccess` (for full deployment access)
   
   **OR** for more restricted access, select these instead:
   - ✅ `AWSLambda_FullAccess`
   - ✅ `AmazonS3FullAccess`
   - ✅ `AmazonDynamoDBFullAccess`
   - ✅ `AmazonSQSFullAccess`
   - ✅ `AmazonAPIGatewayAdministrator`
   - ✅ `CloudWatchFullAccess`
   - ✅ `IAMFullAccess`
   - ✅ `AWSCloudFormationFullAccess`
   - ✅ `AmazonSageMakerFullAccess`

3. Click **"Next"**
4. Review and click **"Create user"**

### Step 2.5: Save Console Sign-in URL

1. After user creation, you'll see a success message
2. **IMPORTANT:** Copy and save the **Console sign-in URL**
   - Example: `https://123456789012.signin.aws.amazon.com/console`
3. Click **"Return to users list"**

---

## 3. Get AWS Credentials

### Step 3.1: Create Access Keys

1. In IAM Users list, click on your username (`artisan-catalog-admin`)
2. Click the **"Security credentials"** tab
3. Scroll down to **"Access keys"** section
4. Click **"Create access key"**

### Step 3.2: Choose Use Case

1. Select **"Command Line Interface (CLI)"**
2. Check ✅ **"I understand the above recommendation..."**
3. Click **"Next"**

### Step 3.3: Add Description (Optional)

1. Add description tag: `Artisan Catalog Development`
2. Click **"Create access key"**

### Step 3.4: Download Credentials

🚨 **CRITICAL:** This is your ONLY chance to see the Secret Access Key!

1. You'll see:
   - **Access key ID**: `AKIAIOSFODNN7EXAMPLE`
   - **Secret access key**: `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY`

2. **Option 1:** Click **"Download .csv file"** (RECOMMENDED)
   - Save this file securely
   - Never commit it to Git!

3. **Option 2:** Copy both values to a secure location

4. Click **"Done"**

### Step 3.5: Store Credentials Securely

```bash
# Create a secure credentials file (Linux/Mac)
mkdir -p ~/.aws
chmod 700 ~/.aws
touch ~/.aws/credentials
chmod 600 ~/.aws/credentials
```

---

## 4. Configure AWS CLI

### Step 4.1: Install AWS CLI

**Linux:**
```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
```

**macOS:**
```bash
curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"
sudo installer -pkg AWSCLIV2.pkg -target /
```

**Windows:**
Download and run: [AWS CLI MSI Installer](https://awscli.amazonaws.com/AWSCLIV2.msi)

### Step 4.2: Verify Installation

```bash
aws --version
# Expected output: aws-cli/2.x.x Python/3.x.x ...
```

### Step 4.3: Configure AWS CLI

```bash
aws configure
```

You'll be prompted for:

```
AWS Access Key ID [None]: AKIAIOSFODNN7EXAMPLE
AWS Secret Access Key [None]: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
Default region name [None]: ap-south-1
Default output format [None]: json
```

**Region Options:**
- `ap-south-1` - Asia Pacific (Mumbai) - RECOMMENDED for India
- `us-east-1` - US East (N. Virginia)
- `us-west-2` - US West (Oregon)
- `eu-west-1` - Europe (Ireland)

### Step 4.4: Test Configuration

```bash
aws sts get-caller-identity
```

Expected output:
```json
{
    "UserId": "AIDAI23HXS2RV2EXAMPLE",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/artisan-catalog-admin"
}
```

✅ If you see this, your AWS CLI is configured correctly!

---

## 5. Get AWS Account ID

### Method 1: From CLI (Easiest)

```bash
aws sts get-caller-identity --query Account --output text
```

Output: `123456789012`

### Method 2: From AWS Console

1. Click your username in the top-right corner
2. Your Account ID is displayed in the dropdown
3. Click to copy it

### Method 3: From IAM Dashboard

1. Go to IAM Dashboard
2. Look for **"AWS Account"** section on the right
3. Your Account ID is displayed there

---

## 6. Enable Required AWS Services

### Step 6.1: Enable Amazon Bedrock

1. In AWS Console search bar, type **"Bedrock"**
2. Click **"Amazon Bedrock"**
3. In the left sidebar, click **"Model access"**
4. Click **"Manage model access"** (orange button)
5. Check these models:
   - ✅ **Claude 3 Sonnet** (by Anthropic)
   - ✅ **Claude 3.5 Sonnet** (by Anthropic)
   - ✅ **Titan Text G1 - Express** (by Amazon)
6. Click **"Request model access"**
7. Wait for approval (usually instant, sometimes takes a few minutes)

**Note:** Bedrock is available in these regions:
- `us-east-1` (N. Virginia)
- `us-west-2` (Oregon)
- `ap-southeast-1` (Singapore)
- `eu-west-1` (Ireland)

If you're using `ap-south-1`, you'll need to make cross-region calls to Bedrock.

### Step 6.2: Verify Bedrock Access

```bash
aws bedrock list-foundation-models --region us-east-1 --query 'modelSummaries[?modelId==`anthropic.claude-3-sonnet-20240229-v1:0`]'
```

### Step 6.3: Enable AWS X-Ray (Optional but Recommended)

X-Ray is automatically available, no setup needed. It will be enabled when you deploy.

### Step 6.4: Check Service Quotas

```bash
# Check Lambda concurrent executions limit
aws service-quotas get-service-quota \
  --service-code lambda \
  --quota-code L-B99A9384 \
  --region ap-south-1

# Check SageMaker endpoint instances
aws service-quotas get-service-quota \
  --service-code sagemaker \
  --quota-code L-93D7C6F0 \
  --region ap-south-1
```

If limits are too low, request increases via AWS Console > Service Quotas.

---

## 7. Fill Your .env File

Now you have all the information needed! Let's fill your `.env` file.

### Step 7.1: Open Your .env File

```bash
cd /path/to/vernacular-artisan-catalog
nano .env  # or use your preferred editor
```

### Step 7.2: Fill in AWS Configuration

```bash
# AWS Configuration
AWS_REGION=ap-south-1                    # ← Your chosen region
AWS_ACCOUNT_ID=123456789012              # ← From step 5

# S3 Buckets (will be created during deployment)
S3_RAW_MEDIA_BUCKET=artisan-catalog-raw-media-123456789012
S3_ENHANCED_BUCKET=artisan-catalog-enhanced-123456789012

# DynamoDB Tables (will be created during deployment)
DYNAMODB_CATALOG_TABLE=CatalogProcessingRecords
DYNAMODB_TENANT_TABLE=TenantConfigurations

# SQS Queue (will be created during deployment)
SQS_QUEUE_URL=https://sqs.ap-south-1.amazonaws.com/123456789012/catalog-processing-queue

# Sagemaker (will be configured after deployment)
SAGEMAKER_ENDPOINT_NAME=vision-asr-endpoint

# Bedrock
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
BEDROCK_REGION=us-east-1                 # ← Bedrock region (if different from AWS_REGION)

# ONDC Configuration (get from ONDC portal)
ONDC_API_URL=https://staging.ondc.org/api
ONDC_SELLER_ID=your-seller-id-here       # ← Get from ONDC
ONDC_API_KEY=your-ondc-api-key-here      # ← Get from ONDC

# Application Settings
LOG_LEVEL=INFO
MAX_UPLOAD_SIZE_MB=10
SUPPORTED_LANGUAGES=hi,te,ta,bn,mr,gu,kn,ml,pa,or
```

### Step 7.3: Update Bucket Names with Your Account ID

Replace `123456789012` with your actual AWS Account ID:

```bash
# Use this command to auto-update (Linux/Mac)
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
sed -i "s/123456789012/$ACCOUNT_ID/g" .env
```

### Step 7.4: Get ONDC Credentials (If Applicable)

1. Go to [ONDC Network Portal](https://ondc.org)
2. Register as a seller/network participant
3. Complete onboarding process
4. Get your:
   - **Seller ID** (also called Subscriber ID)
   - **API Key** (also called Signing Key)
5. Update `.env` file with these values

---

## 8. Verify Setup

### Step 8.1: Verify AWS Access

```bash
# Test AWS CLI access
aws sts get-caller-identity

# Test S3 access
aws s3 ls

# Test DynamoDB access
aws dynamodb list-tables --region ap-south-1

# Test Lambda access
aws lambda list-functions --region ap-south-1
```

### Step 8.2: Verify Bedrock Access

```bash
# List available models
aws bedrock list-foundation-models --region us-east-1

# Test model invocation (optional)
aws bedrock invoke-model \
  --model-id anthropic.claude-3-sonnet-20240229-v1:0 \
  --body '{"prompt":"Hello","max_tokens":100}' \
  --region us-east-1 \
  output.txt
```

### Step 8.3: Check Your .env File

```bash
# Display your .env (without sensitive values)
cat .env | grep -v "API_KEY\|SECRET"
```

### Step 8.4: Verify Prerequisites for Deployment

```bash
# Check all required tools
echo "Checking prerequisites..."

# AWS CLI
aws --version && echo "✅ AWS CLI installed" || echo "❌ AWS CLI missing"

# Node.js
node --version && echo "✅ Node.js installed" || echo "❌ Node.js missing"

# Python
python3 --version && echo "✅ Python installed" || echo "❌ Python missing"

# AWS CDK
cdk --version && echo "✅ AWS CDK installed" || echo "❌ AWS CDK missing"

# AWS Credentials
aws sts get-caller-identity > /dev/null 2>&1 && echo "✅ AWS credentials configured" || echo "❌ AWS credentials not configured"
```

---

## Next Steps

Now that your AWS setup is complete, you can:

1. **Deploy Infrastructure:**
   ```bash
   cd backend/infrastructure/cdk
   npm install
   cdk bootstrap  # First time only
   cdk deploy
   ```

2. **Deploy SageMaker Endpoint:**
   ```bash
   # Follow the SageMaker deployment guide
   # See: docs/SAGEMAKER_ENDPOINT_DEPLOYMENT.md
   ```

3. **Test Your API:**
   ```bash
   # After deployment, test the API endpoint
   # See: docs/API_DOCUMENTATION.md
   ```

---

## Troubleshooting

### Issue: "Unable to locate credentials"

**Solution:**
```bash
# Re-run AWS configure
aws configure

# Or manually edit credentials file
nano ~/.aws/credentials
```

### Issue: "Access Denied" errors

**Solution:**
1. Verify IAM user has correct permissions
2. Check if you're using the right AWS profile:
   ```bash
   export AWS_PROFILE=default
   aws sts get-caller-identity
   ```

### Issue: "Region not supported"

**Solution:**
- Some services (like Bedrock) are only available in specific regions
- Use `us-east-1` or `us-west-2` for Bedrock
- Keep your main infrastructure in `ap-south-1` (Mumbai)

### Issue: "Service quota exceeded"

**Solution:**
1. Go to AWS Console > Service Quotas
2. Search for the service (Lambda, SageMaker, etc.)
3. Request quota increase
4. Wait for approval (usually 24-48 hours)

### Issue: "Bedrock model access denied"

**Solution:**
1. Go to Bedrock console
2. Click "Model access" in left sidebar
3. Ensure models show "Access granted" status
4. If pending, wait a few minutes and refresh

---

## Security Best Practices

1. ✅ **Never commit credentials to Git**
   ```bash
   # Verify .env is in .gitignore
   cat .gitignore | grep .env
   ```

2. ✅ **Rotate access keys regularly**
   - Every 90 days minimum
   - Immediately if compromised

3. ✅ **Enable MFA on root account**
   - Go to IAM > Dashboard
   - Click "Add MFA" for root account

4. ✅ **Use IAM roles for EC2/Lambda**
   - Don't hardcode credentials in code
   - Let AWS handle credential management

5. ✅ **Monitor AWS CloudTrail**
   - Enable CloudTrail for audit logging
   - Review logs regularly

6. ✅ **Set up billing alerts**
   - Go to Billing > Billing preferences
   - Enable "Receive Billing Alerts"
   - Create CloudWatch alarm for costs

---

## Cost Estimation

Expected monthly costs for development:

| Service | Usage | Estimated Cost |
|---------|-------|----------------|
| Lambda | 1M requests, 512MB | $0.20 |
| API Gateway | 1M requests | $3.50 |
| S3 | 10GB storage, 1GB transfer | $0.50 |
| DynamoDB | On-demand, 1M reads/writes | $1.25 |
| SQS | 1M requests | $0.40 |
| CloudWatch | Logs, metrics | $2.00 |
| SageMaker | ml.g4dn.xlarge, 100 hours | $75.00 |
| Bedrock | 1M tokens | $3.00 |
| **Total** | | **~$85-90/month** |

**Free Tier Benefits** (first 12 months):
- Lambda: 1M free requests/month
- API Gateway: 1M free requests/month
- S3: 5GB free storage
- DynamoDB: 25GB free storage

---

## Support Resources

- **AWS Documentation:** [https://docs.aws.amazon.com](https://docs.aws.amazon.com)
- **AWS Support:** [https://console.aws.amazon.com/support](https://console.aws.amazon.com/support)
- **AWS Forums:** [https://forums.aws.amazon.com](https://forums.aws.amazon.com)
- **Project Documentation:** See `docs/` folder

---

## Summary Checklist

Before proceeding with deployment, ensure:

- ✅ AWS account created
- ✅ IAM user created with appropriate permissions
- ✅ AWS CLI installed and configured
- ✅ Access keys generated and stored securely
- ✅ AWS Account ID obtained
- ✅ Bedrock model access enabled
- ✅ `.env` file filled with correct values
- ✅ All prerequisite tools installed (Node.js, Python, CDK)
- ✅ AWS credentials verified with `aws sts get-caller-identity`

**You're now ready to deploy! 🚀**

Proceed to: `docs/AWS_DEPLOYMENT.md` for deployment instructions.
