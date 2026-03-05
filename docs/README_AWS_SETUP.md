# AWS Setup Documentation - Complete Guide

Welcome! This directory contains comprehensive guides for setting up AWS for the Vernacular Artisan Catalog project.

---

## 📚 Documentation Overview

### 🚀 Start Here

**[AWS_SETUP_GUIDE.md](./AWS_SETUP_GUIDE.md)** - Complete step-by-step setup guide
- Create AWS account
- Set up IAM user
- Get credentials
- Configure AWS CLI
- Enable services
- Fill .env file

**Estimated time:** 30-40 minutes

---

### 📋 Quick References

**[AWS_CREDENTIALS_QUICK_REFERENCE.md](./AWS_CREDENTIALS_QUICK_REFERENCE.md)** - Quick lookup
- Commands to get credentials
- .env file template
- Where to find each credential
- Auto-fill script
- Verification checklist

**[AWS_SETUP_FLOWCHART.md](./AWS_SETUP_FLOWCHART.md)** - Visual guide
- Setup flowchart
- Credential flow diagram
- Service dependencies
- Time estimates

---

### 🔧 Deployment & Operations

**[AWS_DEPLOYMENT.md](./AWS_DEPLOYMENT.md)** - Full deployment guide
- Infrastructure components
- IAM roles and permissions
- Deployment methods
- CI/CD configuration
- Monitoring and observability

**[AWS_TROUBLESHOOTING.md](./AWS_TROUBLESHOOTING.md)** - Problem solving
- Common issues and solutions
- Debugging commands
- Emergency procedures
- Getting help

---

## 🎯 Quick Start (5 Minutes)

If you already have AWS experience:

```bash
# 1. Configure AWS CLI
aws configure

# 2. Get your account ID
aws sts get-caller-identity --query Account --output text

# 3. Run auto-setup script
./scripts/update-env.sh

# 4. Manually add ONDC credentials to .env
nano .env

# 5. Deploy
cd backend/infrastructure/cdk
npm install
cdk bootstrap
cdk deploy
```

---

## 📖 Detailed Setup Path

### For First-Time AWS Users

Follow this order:

1. **[AWS_SETUP_GUIDE.md](./AWS_SETUP_GUIDE.md)** (30-40 min)
   - Complete account setup
   - Get all credentials
   - Configure everything

2. **[AWS_CREDENTIALS_QUICK_REFERENCE.md](./AWS_CREDENTIALS_QUICK_REFERENCE.md)** (5 min)
   - Verify your setup
   - Run verification checklist

3. **[AWS_DEPLOYMENT.md](./AWS_DEPLOYMENT.md)** (20-30 min)
   - Deploy infrastructure
   - Configure services

4. **[AWS_TROUBLESHOOTING.md](./AWS_TROUBLESHOOTING.md)** (as needed)
   - Solve any issues

---

## 🔑 What You'll Need

### AWS Credentials

- ✅ AWS Account ID (12 digits)
- ✅ AWS Access Key ID
- ✅ AWS Secret Access Key
- ✅ AWS Region (e.g., ap-south-1)

### ONDC Credentials (Optional)

- ⚠️ ONDC Seller ID
- ⚠️ ONDC API Key

### Tools

- ✅ AWS CLI v2
- ✅ Node.js v18+
- ✅ Python 3.11+
- ✅ AWS CDK v2

---

## 📝 .env File Template

After setup, your `.env` should look like:

```bash
# AWS Configuration
AWS_REGION=ap-south-1
AWS_ACCOUNT_ID=123456789012

# S3 Buckets
S3_RAW_MEDIA_BUCKET=artisan-catalog-raw-media-123456789012
S3_ENHANCED_BUCKET=artisan-catalog-enhanced-123456789012

# DynamoDB Tables
DYNAMODB_CATALOG_TABLE=CatalogProcessingRecords
DYNAMODB_TENANT_TABLE=TenantConfigurations

# SQS Queue
SQS_QUEUE_URL=https://sqs.ap-south-1.amazonaws.com/123456789012/catalog-processing-queue

# Sagemaker
SAGEMAKER_ENDPOINT_NAME=vision-asr-endpoint

# Bedrock
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
BEDROCK_REGION=us-east-1

# ONDC Configuration
ONDC_API_URL=https://staging.ondc.org/api
ONDC_SELLER_ID=your-seller-id
ONDC_API_KEY=your-api-key

# Application Settings
LOG_LEVEL=INFO
MAX_UPLOAD_SIZE_MB=10
SUPPORTED_LANGUAGES=hi,te,ta,bn,mr,gu,kn,ml,pa,or
```

---

## ✅ Verification Checklist

Before deploying, ensure:

- [ ] AWS account created
- [ ] IAM user created with admin permissions
- [ ] Access keys generated and downloaded
- [ ] AWS CLI installed and configured
- [ ] `aws sts get-caller-identity` works
- [ ] AWS Account ID obtained
- [ ] Bedrock model access enabled
- [ ] `.env` file created and filled
- [ ] Node.js, Python, and CDK installed
- [ ] ONDC credentials added (if applicable)

---

## 🚀 Deployment Steps

Once setup is complete:

```bash
# 1. Navigate to CDK directory
cd backend/infrastructure/cdk

# 2. Install dependencies
npm install

# 3. Bootstrap CDK (first time only)
cdk bootstrap

# 4. Review what will be created
cdk synth

# 5. Deploy infrastructure
cdk deploy

# 6. Note the outputs (API URL, bucket names, etc.)
```

---

## 💰 Cost Estimates

### Development Environment

| Service | Monthly Cost |
|---------|--------------|
| Lambda | $0-5 |
| API Gateway | $3-5 |
| S3 | $1-3 |
| DynamoDB | $1-5 |
| SQS | $0-1 |
| CloudWatch | $2-5 |
| SageMaker | $50-100 |
| Bedrock | $3-10 |
| **Total** | **$60-135** |

### Free Tier Benefits (First 12 Months)

- Lambda: 1M free requests/month
- API Gateway: 1M free requests/month
- S3: 5GB free storage
- DynamoDB: 25GB free storage
- CloudWatch: 10 custom metrics

---

## 🔒 Security Best Practices

1. ✅ Never commit `.env` to Git
2. ✅ Use IAM users, not root account
3. ✅ Enable MFA on all accounts
4. ✅ Rotate access keys every 90 days
5. ✅ Use least privilege IAM policies
6. ✅ Enable CloudTrail for audit logs
7. ✅ Set up billing alerts
8. ✅ Review security regularly

---

## 🆘 Getting Help

### If You're Stuck

1. Check **[AWS_TROUBLESHOOTING.md](./AWS_TROUBLESHOOTING.md)**
2. Review error messages carefully
3. Search AWS documentation
4. Check AWS Service Health Dashboard
5. Ask on AWS forums or Stack Overflow

### Support Resources

- **AWS Documentation:** https://docs.aws.amazon.com
- **AWS Forums:** https://forums.aws.amazon.com
- **AWS Support:** https://console.aws.amazon.com/support
- **Stack Overflow:** https://stackoverflow.com/questions/tagged/aws

### Project Documentation

- **API Docs:** [API_DOCUMENTATION.md](./API_DOCUMENTATION.md)
- **Deployment:** [AWS_DEPLOYMENT.md](./AWS_DEPLOYMENT.md)
- **Quick Start:** [QUICKSTART.md](./QUICKSTART.md)
- **Operations:** [OPERATIONAL_RUNBOOKS.md](./OPERATIONAL_RUNBOOKS.md)

---

## 📊 Architecture Overview

```
Mobile App (React Native)
        ↓
API Gateway (REST API)
        ↓
Lambda (API Handler)
        ↓
    ┌───┴───┬────────┬─────────┐
    ↓       ↓        ↓         ↓
   S3    DynamoDB   SQS    CloudWatch
                     ↓
            Lambda (Orchestrator)
                     ↓
            ┌────────┼────────┐
            ↓        ↓        ↓
        SageMaker  Bedrock  ONDC
```

---

## 🎓 Learning Resources

### AWS Basics

- [AWS Getting Started](https://aws.amazon.com/getting-started/)
- [AWS Free Tier](https://aws.amazon.com/free/)
- [AWS Training](https://aws.amazon.com/training/)

### Service-Specific

- [Lambda Documentation](https://docs.aws.amazon.com/lambda/)
- [API Gateway Documentation](https://docs.aws.amazon.com/apigateway/)
- [DynamoDB Documentation](https://docs.aws.amazon.com/dynamodb/)
- [Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [SageMaker Documentation](https://docs.aws.amazon.com/sagemaker/)

### CDK

- [AWS CDK Documentation](https://docs.aws.amazon.com/cdk/)
- [CDK Workshop](https://cdkworkshop.com/)
- [CDK Examples](https://github.com/aws-samples/aws-cdk-examples)

---

## 🔄 Next Steps After Setup

1. ✅ Complete AWS setup (this guide)
2. ⏭️ Deploy infrastructure (`cdk deploy`)
3. ⏭️ Deploy SageMaker endpoint
4. ⏭️ Test API endpoints
5. ⏭️ Configure mobile app
6. ⏭️ Run integration tests
7. ⏭️ Set up monitoring
8. ⏭️ Configure CI/CD

---

## 📞 Contact & Support

For project-specific questions:
- Check documentation in `docs/` folder
- Review code comments
- Check GitHub issues (if applicable)

For AWS-specific questions:
- AWS Support (if you have a support plan)
- AWS Forums
- Stack Overflow

---

## 🎉 You're Ready!

Once you've completed the setup:

1. Your AWS account is configured
2. Your credentials are in place
3. Your `.env` file is ready
4. You can deploy the infrastructure

**Next:** Run `cd backend/infrastructure/cdk && cdk deploy`

Good luck! 🚀
