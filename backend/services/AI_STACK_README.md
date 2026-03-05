# AI Services Stack

Complete AI stack using AWS managed services - no training required!

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     AI Orchestrator                          │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ Rekognition  │   │   Bedrock    │   │   Bedrock    │
│    Custom    │   │  Claude 3.5  │   │  Claude 3    │
│   Labels     │   │   Sonnet     │   │    Haiku     │
│              │   │              │   │              │
│  Product     │   │   Vision     │   │   Catalog    │
│  Detection   │   │   Analysis   │   │  Generation  │
└──────────────┘   └──────────────┘   └──────────────┘
        │                   │                   │
        └───────────────────┴───────────────────┘
                            │
                            ▼
                   ┌──────────────┐
                   │     AWS      │
                   │  Transcribe  │
                   │              │
                   │     ASR      │
                   └──────────────┘
```

## Services

### 1. Rekognition Custom Labels
- **Purpose**: Trained product detection
- **Cost**: $4/hour when running + $0.001/image
- **Setup**: Requires training with labeled images
- **Fallback**: Standard Rekognition if not trained

### 2. Claude 3.5 Sonnet (Bedrock)
- **Purpose**: Complex vision analysis and reasoning
- **Cost**: $0.003/image (1000 tokens)
- **Features**: Multimodal, detailed analysis
- **No training required**

### 3. Claude 3 Haiku (Bedrock)
- **Purpose**: Fast, cheap catalog generation
- **Cost**: $0.00025/request (1000 tokens)
- **Features**: Text generation, translation
- **No training required**

### 4. AWS Transcribe
- **Purpose**: Audio transcription
- **Cost**: $0.024/minute
- **Languages**: Hindi, Tamil, Telugu, Marathi
- **No training required**

## Quick Start

### Basic Usage

```python
from backend.services.ai_orchestrator import AIOrchestrator

# Initialize orchestrator
orchestrator = AIOrchestrator(
    region='ap-south-1',
    rekognition_project_arn='arn:aws:rekognition:...',  # Optional
    transcribe_s3_bucket='my-transcribe-bucket'
)

# Process complete product (image + audio)
with open('product.jpg', 'rb') as img, open('audio.opus', 'rb') as aud:
    result = orchestrator.process_product(
        image_bytes=img.read(),
        audio_bytes=aud.read(),
        language_code='hi',
        audio_format='opus'
    )

# Access results
print(f"Category: {result['catalog_entry']['category']}")
print(f"Description: {result['catalog_entry']['long_description']}")
print(f"Confidence: {result['overall_confidence']:.2%}")
```

### Image Only

```python
# Process image without audio
with open('product.jpg', 'rb') as f:
    result = orchestrator.process_image_only(f.read())

print(f"Detected: {result['detection']['primary_category']}")
print(f"Materials: {result['vision_analysis']['materials']}")
print(f"Colors: {result['vision_analysis']['colors']}")
```

### Audio Only

```python
# Process audio without image
with open('audio.opus', 'rb') as f:
    result = orchestrator.process_audio_only(
        audio_bytes=f.read(),
        language_code='hi',
        audio_format='opus'
    )

print(f"Transcription: {result['text']}")
print(f"Language: {result['language']}")
```

## Setup

### 1. IAM Permissions

Add to your Lambda execution role:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "rekognition:DetectCustomLabels",
        "rekognition:DetectLabels",
        "rekognition:StartProjectVersion",
        "rekognition:StopProjectVersion",
        "rekognition:DescribeProjectVersions"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel"
      ],
      "Resource": [
        "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0",
        "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-haiku-20240307-v1:0"
      ]
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

### 2. Enable Bedrock Models

```bash
# Enable Claude models in Bedrock console
# Go to: AWS Console > Bedrock > Model access
# Request access to:
# - Claude 3.5 Sonnet
# - Claude 3 Haiku
```

### 3. Create S3 Bucket for Transcribe

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
aws s3 mb s3://transcribe-temp-ap-south-1-${ACCOUNT_ID}
```

### 4. (Optional) Train Rekognition Custom Labels

See: `docs/REKOGNITION_CUSTOM_LABELS_SETUP.md`

## Response Format

### Complete Processing Result

```json
{
  "detection": {
    "detections": [
      {
        "label": "Handloom Saree",
        "confidence": 0.92,
        "bounding_box": {...}
      }
    ],
    "primary_category": "Handloom Saree",
    "primary_confidence": 0.92,
    "model_type": "custom_labels"
  },
  "vision_analysis": {
    "category": "Banarasi Silk Saree",
    "subcategory": "Wedding Saree",
    "materials": ["silk", "zari"],
    "colors": {
      "primary": ["red", "gold"],
      "secondary": ["maroon"]
    },
    "craftsmanship": {
      "technique": "handloom",
      "details": "Traditional Banarasi weaving with zari work"
    },
    "confidence": 0.88,
    "model": "claude-3.5-sonnet"
  },
  "transcription": {
    "text": "यह एक हाथ से बुनी हुई बनारसी रेशमी साड़ी है",
    "language": "hi",
    "confidence": 0.91,
    "segments": [...]
  },
  "catalog_entry": {
    "product_name": "Handwoven Banarasi Silk Wedding Saree",
    "short_description": "Exquisite handloom Banarasi silk saree...",
    "long_description": "This stunning Banarasi silk saree...",
    "category": "Apparel",
    "subcategory": "Sarees",
    "attributes": {
      "materials": ["silk", "zari"],
      "colors": ["red", "gold", "maroon"],
      "craftsmanship": "Traditional handloom weaving"
    },
    "price": {"value": null, "currency": "INR"},
    "tags": ["handloom", "banarasi", "silk", "wedding"],
    "vernacular": {
      "language": "hi",
      "description": "यह एक हाथ से बुनी हुई..."
    },
    "confidence": 0.87,
    "model": "claude-3-haiku"
  },
  "overall_confidence": 0.895,
  "low_confidence": false,
  "requires_manual_review": false,
  "status": "success",
  "processing_stages": [
    {"stage": "detection", "status": "success", "model": "custom_labels"},
    {"stage": "vision_analysis", "status": "success", "model": "claude-3.5-sonnet"},
    {"stage": "transcription", "status": "success", "service": "aws-transcribe"},
    {"stage": "catalog_generation", "status": "success", "model": "claude-3-haiku"}
  ]
}
```

## Cost Breakdown

### Per Product (with all services)

```
Rekognition Custom Labels:  $0.001/image
Claude 3.5 Sonnet:          $0.003/image
Claude 3 Haiku:             $0.00025/request
AWS Transcribe:             $0.024/minute (avg 1 min)
---------------------------------------------------
TOTAL:                      ~$0.028 per product
```

### Monthly Cost (10,000 products)

```
10,000 products × $0.028 = $280/month
Plus: Rekognition model running cost = $4/hour × 730 hours = $2,920/month
---------------------------------------------------
TOTAL:                      ~$3,200/month
```

**Cost Optimization:**
- Only run Rekognition Custom Labels when needed (start/stop)
- Use standard Rekognition as fallback ($0.001/image only)
- Batch process during specific hours

### Without Custom Labels (Standard Rekognition)

```
10,000 products × $0.028 = $280/month
No model running cost
---------------------------------------------------
TOTAL:                      ~$280/month
```

## Features

### ✅ No Training Required
- Bedrock models are pre-trained
- AWS Transcribe is pre-trained
- Only Rekognition Custom Labels needs training (optional)

### ✅ High Accuracy
- Claude 3.5 Sonnet: State-of-the-art vision understanding
- AWS Transcribe: 85-92% accuracy for Indian languages
- Custom Labels: 90%+ accuracy when trained

### ✅ Multimodal
- Processes both images and audio
- Combines insights from multiple sources
- Generates comprehensive catalog entries

### ✅ Scalable
- All services auto-scale
- No infrastructure management
- Pay only for what you use

### ✅ Multilingual
- Supports Hindi, Tamil, Telugu, Marathi
- Preserves vernacular text
- Translates to English

## Limitations

### Rekognition Custom Labels
- Requires 1000+ labeled images for training
- Costs $4/hour when running
- Takes 30 minutes to start/stop

### AWS Transcribe
- Only 4 Indian languages supported
- 2-5 second latency (async)
- Requires S3 for temp storage

### Bedrock
- Requires model access approval
- Rate limits apply
- Not available in all regions

## Advanced Usage

### Custom Catalog Generation

```python
# Generate catalog with custom context
catalog = orchestrator.generate_catalog_from_data(
    vision_data=vision_result,
    transcription_data=transcription_result,
    artisan_info={
        'name': 'Artisan Name',
        'location': 'Varanasi',
        'specialization': 'Banarasi Silk'
    }
)
```

### Translation

```python
# Translate vernacular to English
english_text = orchestrator.translate_description(
    text="यह एक हाथ से बुनी हुई साड़ी है",
    source_language="hi"
)
```

### Description Enhancement

```python
# Enhance basic description
enhanced = orchestrator.enhance_catalog_description(
    description="Red silk saree",
    context={
        'materials': ['silk', 'zari'],
        'craftsmanship': 'handloom',
        'origin': 'Varanasi'
    }
)
```

### Service Status

```python
# Check service availability
status = orchestrator.get_service_status()
print(status)
# {
#   'rekognition_custom_labels': 'RUNNING',
#   'bedrock_vision': 'available',
#   'bedrock_catalog': 'available',
#   'transcribe': 'available'
# }
```

## Integration with Lambda

```python
# In your Lambda handler
from backend.services.ai_orchestrator import AIOrchestrator
import os

# Initialize once (outside handler for reuse)
orchestrator = AIOrchestrator(
    region=os.environ['AWS_REGION'],
    rekognition_project_arn=os.environ.get('REKOGNITION_PROJECT_ARN'),
    transcribe_s3_bucket=os.environ['TRANSCRIBE_S3_BUCKET']
)

def lambda_handler(event, context):
    # Get image and audio from event
    image_bytes = get_image_from_s3(event['image_key'])
    audio_bytes = get_audio_from_s3(event['audio_key'])
    
    # Process
    result = orchestrator.process_product(
        image_bytes=image_bytes,
        audio_bytes=audio_bytes,
        language_code=event.get('language', 'hi')
    )
    
    # Store catalog entry
    store_catalog_entry(result['catalog_entry'])
    
    return {
        'statusCode': 200,
        'body': json.dumps(result)
    }
```

## Testing

```bash
# Test complete pipeline
python -c "
from backend.services.ai_orchestrator import AIOrchestrator

orchestrator = AIOrchestrator(
    region='ap-south-1',
    transcribe_s3_bucket='my-bucket'
)

with open('test_image.jpg', 'rb') as img:
    with open('test_audio.opus', 'rb') as aud:
        result = orchestrator.process_product(
            image_bytes=img.read(),
            audio_bytes=aud.read(),
            language_code='hi'
        )
        
print(result['catalog_entry']['product_name'])
"
```

## Troubleshooting

### Bedrock Access Denied
- Request model access in Bedrock console
- Wait for approval (usually instant)
- Check IAM permissions

### Rekognition Model Not Running
- Start model: `orchestrator.product_detector.start_model()`
- Wait 10-30 minutes for startup
- Check status: `orchestrator.get_service_status()`

### Transcribe Errors
- Verify S3 bucket exists
- Check IAM permissions for S3
- Ensure audio format is supported

## Next Steps

1. ✅ Add IAM permissions
2. ✅ Enable Bedrock models
3. ✅ Create S3 bucket for Transcribe
4. ⚠️ (Optional) Train Rekognition Custom Labels
5. ✅ Test with sample data
6. ✅ Integrate with Lambda functions
7. ✅ Deploy and monitor

The stack is production-ready and will provide high-quality results!
