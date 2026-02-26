#!/bin/bash
# Deploy AWS infrastructure using CDK

set -e

echo "=========================================="
echo "Deploying Vernacular Artisan Catalog Infrastructure"
echo "=========================================="

# Check prerequisites
echo "Checking prerequisites..."

if ! command -v aws &> /dev/null; then
    echo "Error: AWS CLI not found. Please install it first."
    exit 1
fi

if ! command -v node &> /dev/null; then
    echo "Error: Node.js not found. Please install it first."
    exit 1
fi

if ! command -v cdk &> /dev/null; then
    echo "Error: AWS CDK not found. Installing..."
    npm install -g aws-cdk
fi

# Check AWS credentials
echo "Checking AWS credentials..."
aws sts get-caller-identity > /dev/null 2>&1 || {
    echo "Error: AWS credentials not configured. Run 'aws configure' first."
    exit 1
}

# Navigate to CDK directory
cd backend/infrastructure/cdk

# Install dependencies
echo "Installing CDK dependencies..."
npm install

# Bootstrap CDK (first time only)
echo "Bootstrapping CDK..."
cdk bootstrap || echo "CDK already bootstrapped"

# Synthesize CloudFormation template
echo "Synthesizing CloudFormation template..."
cdk synth

# Deploy stack
echo "Deploying stack..."
cdk deploy --require-approval never

echo "=========================================="
echo "Deployment complete!"
echo "=========================================="
echo "Check AWS Console for deployed resources"
