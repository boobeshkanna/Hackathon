# Next Steps - Quick Start Guide

## What Was Fixed

✅ Changed Bedrock model from v2 to v1 (no inference profile needed)
✅ Added automatic fallback to Claude 3 Sonnet
✅ Fixed model ID usage in both vision and text extraction methods

## What You Need To Do Now

### Step 1: Enable Bedrock Model Access (REQUIRED - 2 minutes)

Open this URL in your browser:
```
https://ap-south-1.console.aws.amazon.com/bedrock/home?region=ap-south-1#/modelaccess
```

1. Click "Manage model access" or "Edit"
2. Check these boxes:
   - ✓ Claude 3.5 Sonnet
   - ✓ Claude 3 Haiku  
   - ✓ Claude 3 Sonnet
3. Click "Save changes"
4. Wait 2-3 minutes

### Step 2: Test Locally (5 minutes)

```bash
# Make sure you're in the project root
cd ~/kact/Hackathon

# Load environment variables
source .env

# Run the test script
python backend/test_ai_stack.py
```

Choose option 1 first to check configuration, then option 2 to test with an image.

### Step 3: Deploy to AWS (if local test works)

```bash
cd backend/infrastructure/cdk
npm run deploy
```

## Test Commands

### Quick Test (Image Only)
```bash
cd backend
python test_ai_stack.py
# Choose option 2, then provide path to a product image
```

### Full Test (Image + Audio)
```bash
cd backend
python test_ai_stack.py
# Choose option 4, provide both image and audio paths
```

### Check AWS Model Access
```bash
aws bedrock list-foundation-models \
  --region ap-south-1 \
  --by-provider anthropic \
  --query 'modelSummaries[*].[modelId,modelName]' \
  --output table
```

## Expected Output

When testing with an image, you should see:

```
📊 Detection Results:
  Primary Category: Textile
  Confidence: 85%
  Model Type: standard_rekognition

🔍 Vision Analysis:
  Category: Banarasi Silk Saree
  Subcategory: Wedding Saree
  Materials: ['silk', 'zari']
  Colors: {'primary': ['red', 'gold'], 'secondary': ['green']}
  Confidence: 87%

🎨 Craftsmanship:
  Technique: handloom
  Details: Traditional Banarasi weaving with gold zari work

✅ Overall Confidence: 86%
```

## Common Issues

### "Access denied" or "Model not found"
→ You need to enable model access in Bedrock console (Step 1 above)

### "No Custom Labels model configured"
→ This is normal! The code falls back to standard Rekognition
→ To use Custom Labels, see: `docs/REKOGNITION_CUSTOM_LABELS_SETUP.md`

### "TRANSCRIBE_S3_BUCKET not set"
→ Already set in your .env file, just run: `source .env`

### "Throttling" errors
→ Normal for new accounts, wait a few seconds and retry
→ Or use Claude 3 Haiku instead (cheaper, faster, higher limits)

## Architecture

Your AI stack now uses:

1. **Rekognition** (standard) - Product detection
2. **Bedrock Claude 3.5 Sonnet** - Vision analysis  
3. **Bedrock Claude 3 Haiku** - Catalog generation
4. **AWS Transcribe** - Audio transcription

All integrated into your existing Lambda orchestrator.

## Files Modified

- `backend/services/bedrock_client/vision_analyzer.py` - Fixed model ID
- `.env` - Updated BEDROCK_MODEL_ID

## Documentation

- `TROUBLESHOOTING_BEDROCK.md` - Detailed troubleshooting guide
- `QUICKSTART_AI_STACK.md` - How to use the AI stack
- `backend/services/AI_STACK_README.md` - Technical details
- `docs/AI_STACK_IMPLEMENTATION_COMPLETE.md` - Complete implementation guide

## Cost Estimate

For 1000 products:
- Rekognition: $1 (1000 images × $0.001)
- Bedrock Sonnet: ~$0.50 (vision analysis)
- Bedrock Haiku: ~$0.10 (catalog generation)
- Transcribe: ~$2.40 (100 minutes × $0.024)

**Total: ~$4 per 1000 products**

Much cheaper than SageMaker endpoints!

## Support

If you still get errors after enabling model access:

1. Check CloudWatch Logs
2. Run: `aws bedrock list-foundation-models --region ap-south-1`
3. Try a different region: `AWS_REGION=us-east-1`
4. Check IAM permissions include `bedrock:InvokeModel`

## What's Next?

Once local testing works:

1. Deploy to Lambda: `cd backend/infrastructure/cdk && npm run deploy`
2. Test via API Gateway
3. Set up Rekognition Custom Labels (optional)
4. Configure ONDC integration
5. Add monitoring and alerts
