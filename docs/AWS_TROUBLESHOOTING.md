# AWS Setup Troubleshooting Guide

Common issues and solutions when setting up AWS for the Vernacular Artisan Catalog project.

---

## Table of Contents

1. [AWS CLI Issues](#aws-cli-issues)
2. [Credential Issues](#credential-issues)
3. [Permission Issues](#permission-issues)
4. [Region Issues](#region-issues)
5. [Bedrock Issues](#bedrock-issues)
6. [Deployment Issues](#deployment-issues)
7. [Cost & Billing Issues](#cost--billing-issues)

---

## AWS CLI Issues

### Issue: "aws: command not found"

**Cause:** AWS CLI is not installed or not in PATH

**Solution:**
```bash
# Linux
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Verify
aws --version
```

### Issue: "aws --version" shows old version (v1.x)

**Cause:** AWS CLI v1 is installed instead of v2

**Solution:**
```bash
# Remove old version
pip uninstall awscli

# Install v2
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install --update

# Verify
aws --version  # Should show aws-cli/2.x.x
```

---

## Credential Issues

### Issue: "Unable to locate credentials"

**Cause:** AWS credentials not configured

**Solution:**
```bash
# Configure credentials
aws configure

# Or manually create credentials file
mkdir -p ~/.aws
cat > ~/.aws/credentials << EOF
[default]
aws_access_key_id = YOUR_ACCESS_KEY_ID
aws_secret_access_key = YOUR_SECRET_ACCESS_KEY
EOF

chmod 600 ~/.aws/credentials
```

### Issue: "The security token included in the request is invalid"

**Cause:** Access keys are incorrect or expired

**Solution:**
```bash
# Generate new access keys in IAM Console
# Then update credentials
aws configure

# Or edit credentials file
nano ~/.aws/credentials
```

### Issue: "Credentials were refreshed, but the refreshed credentials are still expired"

**Cause:** System clock is out of sync

**Solution:**
```bash
# Linux
sudo ntpdate -s time.nist.gov

# Or
sudo timedatectl set-ntp true
```

### Issue: Multiple AWS profiles causing confusion

**Cause:** Multiple profiles in ~/.aws/credentials

**Solution:**
```bash
# List profiles
cat ~/.aws/credentials

# Use specific profile
export AWS_PROFILE=default
aws sts get-caller-identity

# Or set in .env
echo "AWS_PROFILE=default" >> .env
```

---

## Permission Issues

### Issue: "User is not authorized to perform: iam:CreateRole"

**Cause:** IAM user lacks necessary permissions

**Solution:**
1. Go to IAM Console
2. Click on your user
3. Click "Add permissions"
4. Attach policy: `AdministratorAccess` (or specific policies)
5. Wait 1-2 minutes for permissions to propagate

### Issue: "Access Denied" when accessing S3/DynamoDB/Lambda

**Cause:** Missing service-specific permissions

**Solution:**
```bash
# Check current permissions
aws iam list-attached-user-policies --user-name YOUR_USERNAME

# Attach required policies via console or CLI
aws iam attach-user-policy \
  --user-name YOUR_USERNAME \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
```

### Issue: "You are not authorized to perform this operation"

**Cause:** Using root account or wrong IAM user

**Solution:**
```bash
# Check who you are
aws sts get-caller-identity

# If using wrong profile, switch
export AWS_PROFILE=correct-profile
```

---

## Region Issues

### Issue: "Could not connect to the endpoint URL"

**Cause:** Wrong region configured or service not available in region

**Solution:**
```bash
# Check current region
aws configure get region

# Set correct region
aws configure set region ap-south-1

# Or use region flag
aws s3 ls --region ap-south-1
```

### Issue: "Service is not available in this region"

**Cause:** Some services (like Bedrock) are only in specific regions

**Solution:**
```bash
# For Bedrock, use supported regions
# us-east-1, us-west-2, ap-southeast-1, eu-west-1

# Update .env
BEDROCK_REGION=us-east-1

# Your main infrastructure can stay in ap-south-1
AWS_REGION=ap-south-1
```

### Issue: Resources created in wrong region

**Cause:** Region mismatch between CLI config and .env

**Solution:**
```bash
# Check all region settings
aws configure get region
grep AWS_REGION .env
grep region ~/.aws/config

# Ensure consistency
aws configure set region ap-south-1
```

---

## Bedrock Issues

### Issue: "Could not resolve the foundation model"

**Cause:** Bedrock model access not enabled

**Solution:**
1. Go to [Bedrock Console](https://console.aws.amazon.com/bedrock)
2. Click "Model access" in left sidebar
3. Click "Manage model access"
4. Enable: Claude 3 Sonnet, Claude 3.5 Sonnet
5. Click "Request model access"
6. Wait for approval (usually instant)

### Issue: "Bedrock is not available in your region"

**Cause:** Bedrock not available in ap-south-1

**Solution:**
```bash
# Use cross-region access
# Update .env
BEDROCK_REGION=us-east-1

# Your Lambda will make cross-region calls
# This is normal and supported
```

### Issue: "Access denied to invoke model"

**Cause:** IAM role lacks Bedrock permissions

**Solution:**
```bash
# Add Bedrock permissions to Lambda execution role
aws iam attach-role-policy \
  --role-name VernacularArtisanCatalogStack-LambdaExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess
```

### Issue: "Model ID not found"

**Cause:** Wrong model ID format

**Solution:**
```bash
# List available models
aws bedrock list-foundation-models --region us-east-1

# Use correct model ID format
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
```

---

## Deployment Issues

### Issue: "CDK bootstrap required"

**Cause:** CDK not bootstrapped in account/region

**Solution:**
```bash
cd backend/infrastructure/cdk
cdk bootstrap aws://ACCOUNT_ID/REGION

# Or let CDK auto-detect
cdk bootstrap
```

### Issue: "Stack already exists"

**Cause:** Previous deployment exists

**Solution:**
```bash
# Update existing stack
cdk deploy

# Or destroy and redeploy
cdk destroy
cdk deploy
```

### Issue: "Resource limit exceeded"

**Cause:** AWS service quotas reached

**Solution:**
1. Go to AWS Console > Service Quotas
2. Search for the service (Lambda, SageMaker, etc.)
3. Request quota increase
4. Wait for approval (24-48 hours)

### Issue: "npm install fails in CDK directory"

**Cause:** Node.js version incompatibility

**Solution:**
```bash
# Check Node version
node --version  # Should be 18.x or later

# Install correct version
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Retry
cd backend/infrastructure/cdk
rm -rf node_modules package-lock.json
npm install
```

### Issue: "Python dependencies not found"

**Cause:** Virtual environment not activated or dependencies not installed

**Solution:**
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Verify
python -c "import boto3; print(boto3.__version__)"
```

---

## Cost & Billing Issues

### Issue: Unexpected AWS charges

**Cause:** Resources left running (especially SageMaker endpoints)

**Solution:**
```bash
# Check running resources
aws sagemaker list-endpoints
aws lambda list-functions
aws s3 ls

# Delete expensive resources
aws sagemaker delete-endpoint --endpoint-name ENDPOINT_NAME

# Set up billing alerts
aws cloudwatch put-metric-alarm \
  --alarm-name billing-alert \
  --alarm-description "Alert when bill exceeds $100" \
  --metric-name EstimatedCharges \
  --namespace AWS/Billing \
  --statistic Maximum \
  --period 21600 \
  --threshold 100 \
  --comparison-operator GreaterThanThreshold
```

### Issue: "Payment method declined"

**Cause:** Credit card issue or insufficient funds

**Solution:**
1. Go to AWS Console > Billing
2. Click "Payment methods"
3. Update or add new payment method
4. Verify card is valid and has sufficient funds

### Issue: Free tier exceeded

**Cause:** Usage beyond free tier limits

**Solution:**
```bash
# Check free tier usage
# Go to: https://console.aws.amazon.com/billing/home#/freetier

# Optimize costs:
# 1. Delete unused resources
# 2. Use on-demand pricing for DynamoDB
# 3. Set S3 lifecycle policies
# 4. Stop SageMaker endpoints when not in use
```

---

## General Debugging Commands

### Check AWS Configuration
```bash
# Who am I?
aws sts get-caller-identity

# What region?
aws configure get region

# What profile?
echo $AWS_PROFILE

# List all config
aws configure list
```

### Check Resource Status
```bash
# Lambda functions
aws lambda list-functions --region ap-south-1

# S3 buckets
aws s3 ls

# DynamoDB tables
aws dynamodb list-tables --region ap-south-1

# SQS queues
aws sqs list-queues --region ap-south-1

# CloudFormation stacks
aws cloudformation list-stacks --region ap-south-1
```

### Check Logs
```bash
# Lambda logs
aws logs tail /aws/lambda/artisan-catalog-api-handler --follow

# CloudFormation events
aws cloudformation describe-stack-events \
  --stack-name VernacularArtisanCatalogStack \
  --max-items 10
```

### Test Connectivity
```bash
# Test AWS API
aws sts get-caller-identity

# Test S3
aws s3 ls

# Test DynamoDB
aws dynamodb list-tables

# Test Bedrock
aws bedrock list-foundation-models --region us-east-1
```

---

## Getting Help

### AWS Support Resources

- **AWS Documentation:** https://docs.aws.amazon.com
- **AWS Forums:** https://forums.aws.amazon.com
- **AWS Support:** https://console.aws.amazon.com/support
- **Stack Overflow:** https://stackoverflow.com/questions/tagged/amazon-web-services

### Project-Specific Help

- **Setup Guide:** `docs/AWS_SETUP_GUIDE.md`
- **Deployment Guide:** `docs/AWS_DEPLOYMENT.md`
- **API Documentation:** `docs/API_DOCUMENTATION.md`
- **Quick Reference:** `docs/AWS_CREDENTIALS_QUICK_REFERENCE.md`

### Useful AWS CLI Commands for Debugging

```bash
# Enable debug output
aws s3 ls --debug

# Use specific profile
aws s3 ls --profile my-profile

# Use specific region
aws s3 ls --region ap-south-1

# Get help for any command
aws s3 help
aws lambda help
```

---

## Prevention Tips

1. ✅ **Always use IAM users, never root account**
2. ✅ **Enable MFA on all accounts**
3. ✅ **Set up billing alerts**
4. ✅ **Use .gitignore for .env files**
5. ✅ **Rotate access keys every 90 days**
6. ✅ **Tag all resources for cost tracking**
7. ✅ **Use CloudFormation/CDK for infrastructure**
8. ✅ **Enable CloudTrail for audit logging**
9. ✅ **Review IAM permissions regularly**
10. ✅ **Delete unused resources promptly**

---

## Emergency Procedures

### If Access Keys Are Compromised

```bash
# 1. Immediately deactivate the key
aws iam update-access-key \
  --access-key-id COMPROMISED_KEY \
  --status Inactive \
  --user-name YOUR_USERNAME

# 2. Create new access key
aws iam create-access-key --user-name YOUR_USERNAME

# 3. Update local configuration
aws configure

# 4. Delete old key
aws iam delete-access-key \
  --access-key-id COMPROMISED_KEY \
  --user-name YOUR_USERNAME

# 5. Review CloudTrail logs for unauthorized access
```

### If Unexpected Charges Occur

```bash
# 1. Check what's running
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-01-31 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=SERVICE

# 2. Stop expensive resources
aws sagemaker list-endpoints
aws sagemaker delete-endpoint --endpoint-name ENDPOINT_NAME

# 3. Contact AWS Support
# Go to: https://console.aws.amazon.com/support
```

---

## Still Having Issues?

If you're still experiencing problems:

1. Check the error message carefully
2. Search AWS documentation
3. Check AWS Service Health Dashboard
4. Review CloudWatch logs
5. Contact AWS Support (if you have a support plan)
6. Ask on AWS forums or Stack Overflow

Remember: Most issues are related to:
- Incorrect credentials
- Wrong region
- Missing permissions
- Service quotas
- Network connectivity
