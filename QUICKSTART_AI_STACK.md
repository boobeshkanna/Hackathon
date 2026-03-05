# Quick Start: AI Stack Integration

## Where the Code Goes

The AI orchestrator code is **already integrated** into your Lambda function!

### Integration Points

1. **Lambda Orchestrator** (`backend/lambda_functions/orchestrator/handler.py`)
   - ✅ Already updated to use `AIOrchestrator`
   - ✅ Replaces old SageMaker client
   - ✅ Processes images and audio automatically

2. **AI Services** (`backend/services/`)
   - `ai_orchestrator.py` - Main coordinator
   - `bedrock_client/` - Claude 3.5 Sonnet & Haiku
   - `rekognition_custom/` - Product detection
   - `aws_ai_services/transcription_service.py` - AWS Transcribe

## How It Works

When a product is uploaded:

```
1. User uploads image + audio → API Gateway
2. API stores in S3 → Sends message to SQS
3. Lambda Orchestrator picks up message
4. Calls AIOrchestrator.process_product()
   ├─► Rekognition detects products
   ├─► Claude 3.5 Sonnet analyzes image
   ├─► AWS Transcribe transcribes audio
   └─► Claude 3 Haiku generates catalog
5. Saves catalog to DynamoDB
6. Submits to ONDC
```

## Testing Locally (Before Deploying)

### 1. Set Environment Variables

```bash
export AWS_REGION=ap-south-1
export TRANSCRIBE_S3_BUCKET=transcribe-temp-ap-south-1-YOUR_ACCOUNT_ID
export REKOGNITION_PROJECT_ARN=arn:aws:rekognition:...  # Optional
```

### 2. Run Test Script

```bash
cd backend
python test_ai_stack.py
```

This interactive script lets you test:
- Image-only processing
- Audio-only processing
- Complete pipeline
- Configuration check

### 3. Example Test Session

```bash
$ python test_ai_stack.py

============================================================
AI Stack Test Script
============================================================

Select a test:
  1. Check configuration
  2. Test image-only processing
  3. Test audio-only processing
  4. Test complete pipeline (image + audio)
  5. Exit

Enter choice (1-5): 4

============================================================
Testing Complete Pipeline (Image + Audio)
============================================================

Enter path to test image: /path/to/product.jpg
Enter path to test audio: /path/to/audio.opus
Enter language code (hi/ta/te/mr) [default: hi]: hi
Enter audio format (opus/mp3/wav) [default: opus]: opus

Processing:
  Image: /path/to/product.jpg (245678 bytes)
  Audio: /path/to/audio.opus (89234 bytes)
  Language: hi

⏳ Processing... (this may take 10-15 seconds)

============================================================
RESULTS
============================================================

📊 Detection:
  Category: Handloom Saree
  Confidence: 92.5%

🔍 Vision Analysis:
  Category: Banarasi Silk Saree
  Materials: ['silk', 'zari']
  Colors: {'primary': ['red', 'gold'], 'secondary': ['maroon']}

🎤 Transcription:
  Text: यह एक हाथ से बुनी हुई बनारसी रेशमी साड़ी है
  Confidence: 91.2%

📝 Catalog Entry:
  Product Name: Handwoven Banarasi Silk Wedding Saree
  Category: Apparel
  Short Description: Exquisite handloom Banarasi silk saree...

✅ Overall Status: success
✅ Overall Confidence: 89.5%
```

## Deploying to AWS

### 1. Enable Bedrock Models

Go to AWS Console > Bedrock > Model access:
- Request access to **Claude 3.5 Sonnet**
- Request access to **Claude 3 Haiku**
- Wait for approval (usually instant)

### 2. Create S3 Bucket

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
aws s3 mb s3://transcribe-temp-ap-south-1-${ACCOUNT_ID}
```

### 3. Update CDK Stack

Add environment variables to your Lambda in `backend/infrastructure/cdk/lib/stack.ts`:

```typescript
// Add to lambdaEnvironment
const lambdaEnvironment = {
  // ... existing vars ...
  TRANSCRIBE_S3_BUCKET: `transcribe-temp-${this.region}-${this.account}`,
  REKOGNITION_PROJECT_ARN: '', // Optional, leave empty if not using Custom Labels
};
```

Add IAM permissions:

```typescript
// Add to lambdaRole
lambdaRole.addToPolicy(new iam.PolicyStatement({
  actions: [
    // Rekognition
    'rekognition:DetectCustomLabels',
    'rekognition:DetectLabels',
    
    // Bedrock
    'bedrock:InvokeModel',
    
    // Transcribe
    'transcribe:StartTranscriptionJob',
    'transcribe:GetTranscriptionJob',
    'transcribe:DeleteTranscriptionJob',
  ],
  resources: ['*'],
}));

// S3 permissions for Transcribe
lambdaRole.addToPolicy(new iam.PolicyStatement({
  actions: [
    's3:PutObject',
    's3:GetObject',
    's3:DeleteObject',
  ],
  resources: [`arn:aws:s3:::transcribe-temp-${this.region}-${this.account}/*`],
}));
```

### 4. Deploy

```bash
./scripts/deploy_infrastructure.sh
```

### 5. Test End-to-End

Upload a product through your API:

```bash
curl -X POST https://your-api-gateway-url/v1/catalog/upload/initiate \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "test-tenant",
    "artisan_id": "test-artisan",
    "language": "hi"
  }'
```

Then upload the files and check the processing status.

## Cost Monitoring

### Per Product Cost

```
Rekognition (standard):  $0.001
Claude 3.5 Sonnet:       $0.003
Claude 3 Haiku:          $0.00025
AWS Transcribe:          $0.024 (1 min)
-------------------------------------------
Total:                   ~$0.028 per product
```

### Monthly Cost (10,000 products)

```
10,000 × $0.028 = $280/month
```

Much cheaper than SageMaker ($500+/month)!

## Troubleshooting

### "Bedrock Access Denied"

```bash
# Check model access
aws bedrock list-foundation-models --region ap-south-1

# Request access in console
# AWS Console > Bedrock > Model access > Request access
```

### "S3 Bucket Not Found"

```bash
# Create bucket
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
aws s3 mb s3://transcribe-temp-ap-south-1-${ACCOUNT_ID}
```

### "Transcribe Failed"

Check:
1. S3 bucket exists
2. Lambda has S3 permissions
3. Audio format is supported (opus, mp3, wav)
4. Audio file is not corrupted

### "Low Confidence Results"

This is normal! The system flags low confidence results for manual review.
Check `result['requires_manual_review']` in your code.

## Next Steps

1. ✅ Test locally with `python backend/test_ai_stack.py`
2. ✅ Enable Bedrock models
3. ✅ Create S3 bucket
4. ✅ Update CDK stack with permissions
5. ✅ Deploy to AWS
6. ✅ Test end-to-end
7. ✅ Monitor costs in AWS Cost Explorer

## Documentation

- **Complete Guide**: `backend/services/AI_STACK_README.md`
- **Setup Instructions**: `docs/AI_STACK_IMPLEMENTATION_COMPLETE.md`
- **Custom Labels**: `docs/REKOGNITION_CUSTOM_LABELS_SETUP.md`

## Support

The AI stack is fully integrated and ready to use. Just:
1. Enable Bedrock models
2. Create S3 bucket
3. Deploy

That's it! 🎉
