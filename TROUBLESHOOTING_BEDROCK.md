# Bedrock Model Access Troubleshooting

## Current Error
```
ValidationException: Invocation of model ID anthropic.claude-3-5-sonnet-20241022-v2:0 with on-demand throughput isn't supported.
```

## ✅ Fix Applied
Changed model ID from `anthropic.claude-3-5-sonnet-20241022-v2:0` to `anthropic.claude-3-5-sonnet-20240620-v1:0`

The v1 model doesn't require inference profiles and is more widely available.

## Next Steps

### 1. Enable Bedrock Model Access (REQUIRED)

You need to enable model access in AWS Console:

```bash
# Open AWS Console
1. Go to: https://ap-south-1.console.aws.amazon.com/bedrock/home?region=ap-south-1#/modelaccess
2. Click "Manage model access" (or "Edit" if already on the page)
3. Enable these models:
   ✓ Claude 3.5 Sonnet
   ✓ Claude 3 Haiku
   ✓ Claude 3 Sonnet (fallback)
4. Click "Save changes"
5. Wait 2-3 minutes for access to be granted
```

### 2. Verify Model Availability

Run this command to check which models are available:

```bash
aws bedrock list-foundation-models \
  --region ap-south-1 \
  --by-provider anthropic \
  --query 'modelSummaries[*].[modelId,modelName]' \
  --output table
```

Expected output should include:
- `anthropic.claude-3-5-sonnet-20240620-v1:0`
- `anthropic.claude-3-haiku-20240307-v1:0`
- `anthropic.claude-3-sonnet-20240229-v1:0`

### 3. Test the AI Stack

After enabling model access, test locally:

```bash
cd backend
python test_ai_stack.py
```

This will:
- Test Bedrock vision analysis
- Test Bedrock catalog generation
- Test Rekognition (standard, since no Custom Labels model configured)
- Show you the complete flow

### 4. Common Issues & Solutions

#### Issue: "Access denied" or "Model not found"
**Solution**: Enable model access in Bedrock console (step 1 above)

#### Issue: "Throttling" errors
**Solution**: 
- Claude 3.5 Sonnet has lower rate limits initially
- Use Claude 3 Haiku for high-volume operations
- Request quota increase in Service Quotas console

#### Issue: "Region not supported"
**Solution**: 
- Claude 3.5 Sonnet is available in: us-east-1, us-west-2, ap-south-1, eu-central-1
- If ap-south-1 doesn't work, try us-east-1:
  ```bash
  # Update .env
  AWS_REGION=us-east-1
  ```

#### Issue: Custom Labels model not configured
**Solution**: This is expected! The code falls back to standard Rekognition.
- To use Custom Labels, follow: `docs/REKOGNITION_CUSTOM_LABELS_SETUP.md`
- Standard Rekognition works fine for basic product detection

### 5. Cost Monitoring

Monitor your Bedrock usage:

```bash
# Check Bedrock costs (last 7 days)
aws ce get-cost-and-usage \
  --time-period Start=2026-02-20,End=2026-02-27 \
  --granularity DAILY \
  --metrics BlendedCost \
  --filter file://<(echo '{
    "Dimensions": {
      "Key": "SERVICE",
      "Values": ["Amazon Bedrock"]
    }
  }')
```

Expected costs:
- Claude 3.5 Sonnet: $3 per 1M input tokens, $15 per 1M output tokens
- Claude 3 Haiku: $0.25 per 1M input tokens, $1.25 per 1M output tokens
- Transcribe: $0.024 per minute
- Rekognition: $0.001 per image

### 6. Deploy to Lambda

Once local testing works:

```bash
cd backend/infrastructure/cdk
npm run deploy
```

The Lambda functions will automatically use the AI stack.

## Architecture Overview

```
User Upload
    ↓
API Gateway → API Handler Lambda
    ↓
S3 (raw media) + SQS Message
    ↓
Orchestrator Lambda
    ↓
AI Orchestrator Service
    ├── Rekognition Custom Labels (or standard)
    ├── Bedrock Claude 3.5 Sonnet (vision)
    ├── AWS Transcribe (audio)
    └── Bedrock Claude 3 Haiku (catalog)
    ↓
DynamoDB (catalog entry)
```

## Quick Reference

### Environment Variables
```bash
AWS_REGION=ap-south-1
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20240620-v1:0
TRANSCRIBE_S3_BUCKET=transcribe-temp-ap-south-1-728768429855
```

### Test Commands
```bash
# Test AI stack locally
python backend/test_ai_stack.py

# Test with your own image
python backend/test_ai_stack.py --image path/to/product.jpg

# Test with audio
python backend/test_ai_stack.py --image product.jpg --audio description.mp3
```

### Useful AWS CLI Commands
```bash
# List Bedrock models
aws bedrock list-foundation-models --region ap-south-1

# Test Bedrock access
aws bedrock-runtime invoke-model \
  --model-id anthropic.claude-3-haiku-20240307-v1:0 \
  --body '{"anthropic_version":"bedrock-2023-05-31","max_tokens":100,"messages":[{"role":"user","content":"Hello"}]}' \
  --region ap-south-1 \
  output.json

# Check Transcribe jobs
aws transcribe list-transcription-jobs --region ap-south-1

# List Rekognition Custom Labels projects
aws rekognition describe-projects --region ap-south-1
```

## Support

If you continue to have issues:

1. Check CloudWatch Logs for detailed error messages
2. Verify IAM permissions include:
   - `bedrock:InvokeModel`
   - `transcribe:StartTranscriptionJob`
   - `rekognition:DetectCustomLabels`
3. Ensure you're using the latest boto3: `pip install --upgrade boto3`

## What Changed

Files modified to fix the Bedrock error:
- `backend/services/bedrock_client/vision_analyzer.py` - Changed model ID to v1, added fallback logic
- `.env` - Updated BEDROCK_MODEL_ID to v1 model

The code now:
- Uses Claude 3.5 Sonnet v1 (no inference profile needed)
- Automatically falls back to Claude 3 Sonnet if 3.5 unavailable
- Checks model availability at initialization
- Uses instance variable `self.model_id` instead of hardcoded constant
