#!/bin/bash
# Quick test to verify Bedrock model access

echo "=========================================="
echo "Testing Bedrock Model Access"
echo "=========================================="
echo ""

# Load environment
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

REGION=${AWS_REGION:-ap-south-1}

echo "Region: $REGION"
echo ""

echo "1. Checking available Anthropic models..."
echo ""

aws bedrock list-foundation-models \
  --region $REGION \
  --by-provider anthropic \
  --query 'modelSummaries[*].[modelId,modelName]' \
  --output table

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Error: Could not list models"
    echo "   Make sure AWS credentials are configured"
    exit 1
fi

echo ""
echo "2. Testing Claude 3 Haiku (fast test)..."
echo ""

# Create test request (properly formatted)
REQUEST_BODY='{"anthropic_version":"bedrock-2023-05-31","max_tokens":50,"messages":[{"role":"user","content":"Say Hello from Bedrock in one sentence."}]}'

aws bedrock-runtime invoke-model \
  --model-id anthropic.claude-3-haiku-20240307-v1:0 \
  --body "$REQUEST_BODY" \
  --region $REGION \
  /tmp/bedrock_output.json

if [ $? -eq 0 ] && [ -f /tmp/bedrock_output.json ]; then
    echo "✅ Success! Bedrock is working."
    echo ""
    echo "Response:"
    RESPONSE=$(python3 -c "import sys, json; data=json.load(open('/tmp/bedrock_output.json')); print(data['content'][0]['text'])" 2>/dev/null)
    if [ -n "$RESPONSE" ]; then
        echo "  $RESPONSE"
    else
        echo "  (Response received but couldn't parse)"
        cat /tmp/bedrock_output.json
    fi
    echo ""
    echo "=========================================="
    echo "✅ Bedrock Access Confirmed"
    echo "=========================================="
    echo ""
    echo "You can now run: python backend/test_ai_stack.py"
    echo ""
else
    echo ""
    echo "❌ Error: Could not invoke model"
    echo ""
    echo "Possible reasons:"
    echo "  1. Model access not enabled in Bedrock console"
    echo "  2. IAM permissions missing (bedrock:InvokeModel)"
    echo "  3. Model not available in region: $REGION"
    echo ""
    echo "To enable model access:"
    echo "  1. Go to: https://$REGION.console.aws.amazon.com/bedrock/home?region=$REGION#/modelaccess"
    echo "  2. Click 'Manage model access'"
    echo "  3. Enable Claude 3 Haiku, Claude 3.5 Sonnet, Claude 3 Sonnet"
    echo "  4. Wait 2-3 minutes"
    echo "  5. Run this script again"
    echo ""
    exit 1
fi

# Cleanup
rm -f /tmp/bedrock_output.json
