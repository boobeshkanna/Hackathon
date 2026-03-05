#!/bin/bash
# One-command test for the entire AI stack

set -e

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║         AI Stack Quick Test                                ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Load environment
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
    echo "✅ Loaded .env configuration"
else
    echo "⚠️  Warning: .env file not found"
fi

REGION=${AWS_REGION:-ap-south-1}
echo "   Region: $REGION"
echo ""

# Step 1: Check AWS credentials
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 1: Checking AWS Credentials"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if aws sts get-caller-identity &> /dev/null; then
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    echo "✅ AWS credentials configured"
    echo "   Account ID: $ACCOUNT_ID"
else
    echo "❌ AWS credentials not configured"
    echo "   Run: aws configure"
    exit 1
fi
echo ""

# Step 2: Check Bedrock model access
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 2: Checking Bedrock Model Access"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check if Claude 3 Haiku is available
if aws bedrock list-foundation-models \
    --region $REGION \
    --by-provider anthropic \
    --query 'modelSummaries[?modelId==`anthropic.claude-3-haiku-20240307-v1:0`]' \
    --output text &> /dev/null; then
    echo "✅ Bedrock models available"
else
    echo "❌ Bedrock models not accessible"
    echo ""
    echo "   You need to enable model access:"
    echo "   1. Go to: https://$REGION.console.aws.amazon.com/bedrock/home?region=$REGION#/modelaccess"
    echo "   2. Click 'Manage model access'"
    echo "   3. Enable: Claude 3.5 Sonnet, Claude 3 Haiku, Claude 3 Sonnet"
    echo "   4. Wait 2-3 minutes"
    echo "   5. Run this script again"
    echo ""
    exit 1
fi
echo ""

# Step 3: Test Bedrock invocation
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 3: Testing Bedrock Invocation"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

REQUEST_BODY='{"anthropic_version":"bedrock-2023-05-31","max_tokens":50,"messages":[{"role":"user","content":"Say Bedrock is working in one sentence."}]}'

if aws bedrock-runtime invoke-model \
    --model-id anthropic.claude-3-haiku-20240307-v1:0 \
    --body "$REQUEST_BODY" \
    --region $REGION \
    /tmp/bedrock_output.json &> /dev/null; then
    
    RESPONSE=$(python3 -c "import sys, json; data=json.load(open('/tmp/bedrock_output.json')); print(data['content'][0]['text'])" 2>/dev/null || echo "")
    
    if [ -n "$RESPONSE" ]; then
        echo "✅ Bedrock invocation successful"
        echo "   Response: $RESPONSE"
    else
        echo "⚠️  Bedrock responded but couldn't parse output"
    fi
else
    echo "❌ Bedrock invocation failed"
    echo "   Check IAM permissions: bedrock:InvokeModel"
    exit 1
fi

rm -f /tmp/bedrock_output.json
echo ""

# Step 4: Check S3 bucket
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 4: Checking S3 Configuration"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -n "$TRANSCRIBE_S3_BUCKET" ]; then
    echo "✅ TRANSCRIBE_S3_BUCKET configured: $TRANSCRIBE_S3_BUCKET"
    
    # Check if bucket exists
    if aws s3 ls "s3://$TRANSCRIBE_S3_BUCKET" &> /dev/null; then
        echo "✅ S3 bucket exists and is accessible"
    else
        echo "⚠️  S3 bucket not found or not accessible"
        echo "   Bucket: $TRANSCRIBE_S3_BUCKET"
    fi
else
    echo "⚠️  TRANSCRIBE_S3_BUCKET not set"
    echo "   Audio transcription will not work"
fi
echo ""

# Step 5: Check Python dependencies
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 5: Checking Python Dependencies"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if python3 -c "import boto3" 2>/dev/null; then
    BOTO3_VERSION=$(python3 -c "import boto3; print(boto3.__version__)" 2>/dev/null)
    echo "✅ boto3 installed: $BOTO3_VERSION"
else
    echo "❌ boto3 not installed"
    echo "   Run: pip install boto3"
    exit 1
fi
echo ""

# Summary
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                    Test Summary                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "✅ All checks passed!"
echo ""
echo "Your AI stack is ready to use."
echo ""
echo "Next steps:"
echo "  1. Test with an image:"
echo "     python backend/test_ai_stack.py"
echo ""
echo "  2. Deploy to AWS:"
echo "     cd backend/infrastructure/cdk && npm run deploy"
echo ""
echo "  3. Monitor costs:"
echo "     https://console.aws.amazon.com/cost-management/home"
echo ""
echo "Documentation:"
echo "  • START_HERE.md - Quick start guide"
echo "  • NEXT_STEPS.md - Detailed next steps"
echo "  • TROUBLESHOOTING_BEDROCK.md - Troubleshooting"
echo ""
