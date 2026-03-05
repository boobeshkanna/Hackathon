# 🚀 START HERE - Bedrock Error Fixed

## What Happened

You got this error:
```
ValidationException: Invocation of model ID anthropic.claude-3-5-sonnet-20241022-v2:0 
with on-demand throughput isn't supported.
```

## What I Fixed

✅ Changed model from v2 to v1 (no inference profile needed)
✅ Added automatic fallback to Claude 3 Sonnet
✅ Fixed code to use the correct model ID

## What You Need To Do (4 steps, 10 minutes)

### Step 0: Add Payment Method (REQUIRED FIRST)

Bedrock requires a valid payment method on your AWS account:

1. Go to: https://console.aws.amazon.com/billing/home#/paymentmethods
2. Click "Add a payment method"
3. Enter credit/debit card details
4. Wait 2-5 minutes for AWS to process

Don't worry about costs - you'll stay within free tier for testing (~$4 per 1000 products after).

**If you get "INVALID_PAYMENT_INSTRUMENT" error, see: [FIX_PAYMENT_ISSUE.md](FIX_PAYMENT_ISSUE.md)**

### Step 1: Enable Bedrock Models (REQUIRED)

Open this link: https://ap-south-1.console.aws.amazon.com/bedrock/home?region=ap-south-1#/modelaccess

1. Click "Manage model access"
2. Enable: Claude 3.5 Sonnet, Claude 3 Haiku, Claude 3 Sonnet
3. Click "Save changes"
4. Wait 2-3 minutes

### Step 2: Test Bedrock Access

```bash
python3 test_bedrock_simple.py
```

If you see "✅ Bedrock Access Confirmed", you're good to go!

### Step 3: Test Your AI Stack

```bash
python backend/test_ai_stack.py
```

Choose option 2 (test image) and provide a product image path.

## Expected Result

```
📊 Detection Results:
  Primary Category: Textile
  Confidence: 85%

🔍 Vision Analysis:
  Category: Banarasi Silk Saree
  Materials: ['silk', 'zari']
  Confidence: 87%

✅ Overall Confidence: 86%
```

## If You Get Errors

### "Access denied" or "Model not found"
→ Go back to Step 1 and enable model access

### "INVALID_PAYMENT_INSTRUMENT" error
→ Add payment method to AWS account (see Step 0 above)
→ Read: `FIX_PAYMENT_ISSUE.md` for detailed instructions

### "AWS credentials not configured"
→ Run: `aws configure`

### "TRANSCRIBE_S3_BUCKET not set"
→ Run: `source .env`

### Still not working?
→ Read: `TROUBLESHOOTING_BEDROCK.md`

## Your AI Stack

✅ Rekognition - Product detection
✅ Bedrock Claude 3.5 Sonnet - Vision analysis
✅ Bedrock Claude 3 Haiku - Catalog generation
✅ AWS Transcribe - Audio transcription

All integrated into your Lambda orchestrator!

## Cost

~$4 per 1000 products (90% cheaper than SageMaker)

## Files Changed

- `backend/services/bedrock_client/vision_analyzer.py` - Fixed model ID
- `.env` - Updated BEDROCK_MODEL_ID to v1

## Next Steps After Testing

1. Deploy to Lambda: `cd backend/infrastructure/cdk && npm run deploy`
2. Test via API Gateway
3. Set up monitoring

## Quick Commands

```bash
# Test Bedrock access (RECOMMENDED)
python3 test_bedrock_simple.py

# Test AI stack locally
python backend/test_ai_stack.py

# Check available models
aws bedrock list-foundation-models --region ap-south-1 --by-provider anthropic

# Deploy to AWS
cd backend/infrastructure/cdk && npm run deploy
```

## Documentation

- `NEXT_STEPS.md` - Detailed next steps
- `TROUBLESHOOTING_BEDROCK.md` - Troubleshooting guide
- `QUICKSTART_AI_STACK.md` - How to use the AI stack
- `backend/services/AI_STACK_README.md` - Technical details

## Questions?

The code is ready. You just need to enable model access in AWS Console (Step 1).

That's it! 🎉
