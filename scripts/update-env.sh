#!/bin/bash

# Script to automatically update .env file with AWS credentials
# Usage: ./scripts/update-env.sh

set -e

echo "================================================"
echo "AWS Environment Configuration Script"
echo "================================================"
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI is not installed"
    echo "   Install it from: https://aws.amazon.com/cli/"
    exit 1
fi

echo "✅ AWS CLI found"

# Check if AWS credentials are configured
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS credentials not configured"
    echo "   Run: aws configure"
    exit 1
fi

echo "✅ AWS credentials configured"
echo ""

# Get AWS Account ID
echo "Fetching AWS Account ID..."
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "   Account ID: $ACCOUNT_ID"

# Get AWS Region
echo "Fetching AWS Region..."
REGION=$(aws configure get region)
if [ -z "$REGION" ]; then
    REGION="ap-south-1"
    echo "   No region configured, using default: $REGION"
else
    echo "   Region: $REGION"
fi

# Get AWS User ARN
USER_ARN=$(aws sts get-caller-identity --query Arn --output text)
echo "   User: $USER_ARN"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found, creating from .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "✅ Created .env from .env.example"
    else
        echo "❌ .env.example not found"
        exit 1
    fi
fi

# Backup existing .env
echo "Creating backup of .env..."
cp .env .env.backup
echo "✅ Backup created: .env.backup"
echo ""

# Update .env file
echo "Updating .env file..."

# Update AWS_ACCOUNT_ID
if grep -q "AWS_ACCOUNT_ID=" .env; then
    sed -i "s/AWS_ACCOUNT_ID=.*/AWS_ACCOUNT_ID=$ACCOUNT_ID/" .env
    echo "✅ Updated AWS_ACCOUNT_ID"
else
    echo "AWS_ACCOUNT_ID=$ACCOUNT_ID" >> .env
    echo "✅ Added AWS_ACCOUNT_ID"
fi

# Update AWS_REGION
if grep -q "AWS_REGION=" .env; then
    sed -i "s/AWS_REGION=.*/AWS_REGION=$REGION/" .env
    echo "✅ Updated AWS_REGION"
else
    echo "AWS_REGION=$REGION" >> .env
    echo "✅ Added AWS_REGION"
fi

# Update S3 bucket names with account ID
sed -i "s/artisan-catalog-raw-media-[0-9]*/artisan-catalog-raw-media-$ACCOUNT_ID/" .env
sed -i "s/S3_RAW_MEDIA_BUCKET=artisan-catalog-raw-media$/S3_RAW_MEDIA_BUCKET=artisan-catalog-raw-media-$ACCOUNT_ID/" .env
echo "✅ Updated S3_RAW_MEDIA_BUCKET"

sed -i "s/artisan-catalog-enhanced-[0-9]*/artisan-catalog-enhanced-$ACCOUNT_ID/" .env
sed -i "s/S3_ENHANCED_BUCKET=artisan-catalog-enhanced$/S3_ENHANCED_BUCKET=artisan-catalog-enhanced-$ACCOUNT_ID/" .env
echo "✅ Updated S3_ENHANCED_BUCKET"

# Update SQS queue URL
sed -i "s|sqs\.$REGION\.amazonaws\.com/[0-9]*/|sqs.$REGION.amazonaws.com/$ACCOUNT_ID/|" .env
sed -i "s|SQS_QUEUE_URL=https://sqs\.[a-z0-9-]*\.amazonaws\.com/your-account/|SQS_QUEUE_URL=https://sqs.$REGION.amazonaws.com/$ACCOUNT_ID/|" .env
echo "✅ Updated SQS_QUEUE_URL"

echo ""
echo "================================================"
echo "Configuration Summary"
echo "================================================"
echo ""
echo "AWS Account ID:  $ACCOUNT_ID"
echo "AWS Region:      $REGION"
echo "AWS User:        $USER_ARN"
echo ""
echo "Updated values in .env:"
echo "  - AWS_ACCOUNT_ID"
echo "  - AWS_REGION"
echo "  - S3_RAW_MEDIA_BUCKET"
echo "  - S3_ENHANCED_BUCKET"
echo "  - SQS_QUEUE_URL"
echo ""
echo "================================================"
echo "⚠️  Manual Configuration Still Required"
echo "================================================"
echo ""
echo "You still need to manually configure:"
echo ""
echo "1. ONDC Credentials (get from ONDC portal):"
echo "   - ONDC_SELLER_ID"
echo "   - ONDC_API_KEY"
echo ""
echo "2. SageMaker Endpoint (after deployment):"
echo "   - SAGEMAKER_ENDPOINT_NAME"
echo ""
echo "3. Bedrock Configuration (optional):"
echo "   - BEDROCK_MODEL_ID"
echo "   - BEDROCK_REGION"
echo ""
echo "================================================"
echo "Next Steps"
echo "================================================"
echo ""
echo "1. Edit .env and add missing credentials:"
echo "   nano .env"
echo ""
echo "2. Verify your configuration:"
echo "   cat .env"
echo ""
echo "3. Deploy infrastructure:"
echo "   cd backend/infrastructure/cdk"
echo "   npm install"
echo "   cdk bootstrap"
echo "   cdk deploy"
echo ""
echo "✅ Configuration complete!"
echo ""
