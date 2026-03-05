# AWS Managed AI Services

**No training required!** Use AWS managed AI services instead of SageMaker.

## Why Use This Instead of SageMaker?

✅ **No model training needed** - Pre-trained models ready to use  
✅ **No infrastructure management** - Fully managed services  
✅ **Pay per use** - Only pay for what you analyze  
✅ **Quick setup** - Start using in minutes  
✅ **Auto-scaling** - Handles any load automatically  

## Services Used

### 1. Amazon Rekognition (Vision)
- Detects objects, scenes, and concepts in images
- Extracts text from images
- No training required
- **Cost**: ~$0.001 per image

### 2. Amazon Transcribe (ASR)
- Transcribes audio to text
- Supports Hindi, Tamil, Telugu, Marathi
- Automatic language detection
- **Cost**: ~$0.0004 per second of audio

## Quick Start

### Vision Analysis

```python
from backend.services.aws_ai_services import VisionService

# Initialize
vision = VisionService(region='ap-south-1')

# Analyze product image
with open('product.jpg', 'rb') as f:
    image_bytes = f.read()

result = vision.analyze_product_image(image_bytes)

print(f"Category: {result['category']}")
print(f"Materials: {result['materials']}")
print(f"Colors: {result['colors']}")
print(f"Confidence: {result['confidence']:.2%}")
```

### Audio Transcription

```python
from backend.services.aws_ai_services import TranscriptionService

# Initialize (requires S3 bucket for temp storage)
transcribe = TranscriptionService(
    region='ap-south-1',
    s3_bucket='my-transcribe-bucket'
)

# Transcribe audio
with open('audio.opus', 'rb') as f:
    audio_bytes = f.read()

result = transcribe.transcribe_audio(
    audio_bytes,
    language_code='hi',  # Hindi
    audio_format='opus'
)

print(f"Text: {result['text']}")
print(f"Language: {result['language']}")
print(f"Confidence: {result['confidence']:.2%}")
```

## Setup

### 1. IAM Permissions

Add these permissions to your Lambda execution role:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "rekognition:DetectLabels",
        "rekognition:DetectText"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "transcribe:StartTranscriptionJob",
        "transcribe:GetTranscriptionJob",
        "transcribe:DeleteTranscriptionJob"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::your-transcribe-bucket/*"
    }
  ]
}
```

### 2. Create S3 Bucket for Transcribe

```bash
# Transcribe needs S3 for temporary audio storage
aws s3 mb s3://transcribe-temp-ap-south-1-YOUR_ACCOUNT_ID
```

### 3. Environment Variables

```bash
# Optional - services use defaults if not set
AWS_REGION=ap-south-1
TRANSCRIBE_S3_BUCKET=transcribe-temp-ap-south-1-YOUR_ACCOUNT_ID
```

## Supported Languages

### Amazon Transcribe
- ✅ Hindi (hi-IN)
- ✅ Tamil (ta-IN)
- ✅ Telugu (te-IN)
- ✅ Marathi (mr-IN)
- ❌ Bengali, Gujarati, Kannada, Malayalam, Punjabi, Odia (not yet supported)

For unsupported languages, consider:
- Amazon Bedrock with Claude (can transcribe via audio analysis)
- Third-party services like Google Cloud Speech-to-Text
- IndicWav2Vec model on SageMaker (requires training)

## Cost Comparison

### SageMaker (with custom model)
- Instance cost: $0.70/hour (ml.g4dn.xlarge) = $504/month
- Plus: Training costs, storage, data transfer
- **Total**: ~$500-1000/month minimum

### Managed AI Services
- Rekognition: $0.001/image × 10,000 images = $10
- Transcribe: $0.024/minute × 1,000 minutes = $24
- **Total**: ~$34/month for 10K images + 1K minutes

**Savings**: 90%+ for typical workloads!

## Response Format

### Vision Response

```json
{
  "category": "Handloom Saree",
  "subcategory": null,
  "labels": ["Clothing", "Sari", "Textile", "Silk"],
  "materials": ["silk", "fabric"],
  "colors": ["red", "gold"],
  "confidence": 0.92,
  "low_confidence": false,
  "requires_manual_review": false,
  "raw_labels": [...]
}
```

### Transcription Response

```json
{
  "text": "यह एक हाथ से बुनी हुई रेशमी साड़ी है",
  "language": "hi",
  "confidence": 0.89,
  "low_confidence": false,
  "requires_manual_review": false,
  "segments": [
    {
      "text": "यह एक हाथ से बुनी हुई",
      "start": 0.0,
      "end": 2.5,
      "confidence": 0.92,
      "low_confidence": false
    }
  ]
}
```

## Integration with Existing Code

The services are designed to be drop-in replacements for SageMaker:

```python
# OLD: SageMaker
from backend.services.sagemaker_client import SagemakerClient
client = SagemakerClient(endpoint_name='my-endpoint')
result = client.invoke_combined_endpoint(image_bytes, audio_bytes)

# NEW: Managed AI Services
from backend.services.aws_ai_services import VisionService, TranscriptionService

vision = VisionService()
transcribe = TranscriptionService(s3_bucket='my-bucket')

vision_result = vision.analyze_product_image(image_bytes)
transcription_result = transcribe.transcribe_audio(audio_bytes, language_code='hi')

# Combine results
result = {
    'vision': vision_result,
    'transcription': transcription_result
}
```

## Limitations

### Amazon Rekognition
- Generic labels (not product-specific)
- No custom categories without Custom Labels training
- Limited material/color detection

### Amazon Transcribe
- Only 4 Indian languages supported
- Requires S3 for audio storage
- Async processing (2-5 seconds latency)
- Not real-time

## When to Use SageMaker Instead

Use SageMaker if you need:
- Custom product categories specific to artisan crafts
- Real-time transcription (< 1 second latency)
- Support for all 10 Indian languages
- Custom material/color detection
- Very high accuracy requirements

## Testing

```bash
# Test vision service
python -c "
from backend.services.aws_ai_services import VisionService
vision = VisionService()
with open('test_image.jpg', 'rb') as f:
    result = vision.analyze_product_image(f.read())
print(result)
"

# Test transcription service
python -c "
from backend.services.aws_ai_services import TranscriptionService
transcribe = TranscriptionService(s3_bucket='my-bucket')
with open('test_audio.opus', 'rb') as f:
    result = transcribe.transcribe_audio(f.read(), 'hi', 'opus')
print(result)
"
```

## Recommendation

**Start with managed AI services** (Rekognition + Transcribe):
1. ✅ No training required
2. ✅ 90% cost savings
3. ✅ Quick to deploy
4. ✅ Good enough for MVP

**Upgrade to SageMaker later** if you need:
- Custom product categories
- All 10 Indian languages
- Higher accuracy
- Real-time processing

## Next Steps

1. Update Lambda functions to use these services
2. Add IAM permissions
3. Create S3 bucket for Transcribe
4. Test with sample data
5. Deploy and monitor costs

The managed services are production-ready and will save you significant time and money!
