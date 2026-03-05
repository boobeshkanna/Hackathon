# Sagemaker Client Service

⚠️ **RECOMMENDATION: Don't use this unless you have a trained model!**

**Instead, use AWS Managed AI Services** (no training required):
- See: `backend/services/aws_ai_services/` 
- Read: `docs/RECOMMENDED_AI_APPROACH.md`
- Saves 90% cost and weeks of setup time

---

A robust Python client for AWS Sagemaker endpoints that handles both Vision and ASR (Automatic Speech Recognition) inference for the Vernacular Artisan Catalog system.

## Features

- **Combined Multimodal Endpoint**: Single endpoint for both image analysis and audio transcription
- **Retry Logic**: Exponential backoff retry with configurable attempts
- **Timeout Handling**: Configurable timeouts with proper error handling
- **Error Categorization**: Automatic classification of errors as transient or permanent
- **Low-Confidence Flagging**: Automatic flagging of results below confidence thresholds
- **Language Support**: 10 Indian vernacular languages (Hindi, Tamil, Telugu, Bengali, etc.)
- **Backward Compatibility**: Separate methods for vision-only and ASR-only inference

## Installation

The client is part of the backend services and requires:

```bash
pip install boto3 botocore
```

## Configuration

Set the following environment variables:

```bash
# Required
SAGEMAKER_ENDPOINT_NAME=vernacular-vision-asr-endpoint
SAGEMAKER_REGION=ap-south-1

# Optional (with defaults)
SAGEMAKER_TIMEOUT_SECONDS=30
SAGEMAKER_MAX_RETRIES=3
ASR_CONFIDENCE_THRESHOLD=0.7
VISION_CONFIDENCE_THRESHOLD=0.6
```

## Usage

### Basic Combined Inference

```python
from backend.services.sagemaker_client import SagemakerClient

# Initialize client
client = SagemakerClient(
    endpoint_name='vernacular-vision-asr-endpoint',
    region='ap-south-1'
)

# Load media files
with open('product_image.jpg', 'rb') as f:
    image_bytes = f.read()

with open('product_audio.opus', 'rb') as f:
    audio_bytes = f.read()

# Invoke combined endpoint
result = client.invoke_combined_endpoint(
    image_bytes=image_bytes,
    audio_bytes=audio_bytes,
    language_hint='hi'  # Hindi
)

# Access results
transcription = result['transcription']
vision = result['vision']

print(f"Text: {transcription['text']}")
print(f"Language: {transcription['language']}")
print(f"Category: {vision['category']}")
print(f"Colors: {vision['colors']}")
```

### Vision-Only Inference

```python
# Backward compatibility method
result = client.invoke_vision_model(image_bytes)

print(f"Category: {result['category']}")
print(f"Confidence: {result['confidence']}")
```

### ASR-Only Inference

```python
# Backward compatibility method
result = client.invoke_asr_model(audio_bytes, language_code='hi')

print(f"Transcription: {result['text']}")
print(f"Language: {result['language']}")
```

### Custom Configuration

```python
client = SagemakerClient(
    endpoint_name='my-endpoint',
    region='ap-south-1',
    timeout_seconds=45,
    max_retries=5,
    asr_confidence_threshold=0.8,
    vision_confidence_threshold=0.7
)
```

### Health Check

```python
if client.health_check():
    print("Endpoint is healthy")
else:
    print("Endpoint is not available")
```

### Confidence Level Checking

```python
from backend.services.sagemaker_client import ConfidenceLevel

confidence = 0.75
level = client.get_confidence_level(confidence, is_vision=True)

if level == ConfidenceLevel.HIGH:
    print("High confidence result")
elif level == ConfidenceLevel.MEDIUM:
    print("Medium confidence result")
else:
    print("Low confidence - requires review")
```

## Response Format

### Combined Endpoint Response

```json
{
  "transcription": {
    "text": "यह एक हाथ से बुनी हुई रेशमी साड़ी है",
    "language": "hi",
    "confidence": 0.92,
    "low_confidence": false,
    "requires_manual_review": false,
    "segments": [
      {
        "text": "यह एक हाथ से बुनी हुई",
        "start": 0.0,
        "end": 2.5,
        "confidence": 0.95,
        "low_confidence": false
      }
    ]
  },
  "vision": {
    "category": "Handloom Saree",
    "subcategory": "Silk Saree",
    "colors": ["red", "gold", "maroon"],
    "materials": ["silk", "zari"],
    "confidence": 0.87,
    "low_confidence": false,
    "requires_manual_review": false,
    "bounding_box": {
      "x": 120,
      "y": 80,
      "width": 800,
      "height": 1200
    }
  },
  "processing_time_ms": 1250
}
```

## Error Handling

The client automatically categorizes and handles errors:

### Transient Errors (Retryable)
- Network timeouts
- Server errors (5xx)
- Throttling exceptions
- Rate limiting (429)

### Permanent Errors (Not Retryable)
- Invalid requests (400)
- Authentication failures (401)
- Authorization failures (403)
- Resource not found (404)

### Example Error Handling

```python
try:
    result = client.invoke_combined_endpoint(
        image_bytes=image_bytes,
        audio_bytes=audio_bytes
    )
except ValueError as e:
    print(f"Invalid input: {e}")
except Exception as e:
    print(f"Inference failed after retries: {e}")
```

## Low-Confidence Flagging

Results below confidence thresholds are automatically flagged:

```python
result = client.invoke_combined_endpoint(...)

if result['transcription']['requires_manual_review']:
    print("⚠️  ASR result needs manual review")
    # Route to manual review queue

if result['vision']['requires_manual_review']:
    print("⚠️  Vision result needs manual review")
    # Route to manual review queue
```

## Supported Languages

The ASR component supports the following Indian languages:

| Code | Language   |
|------|------------|
| hi   | Hindi      |
| ta   | Tamil      |
| te   | Telugu     |
| bn   | Bengali    |
| mr   | Marathi    |
| gu   | Gujarati   |
| kn   | Kannada    |
| ml   | Malayalam  |
| pa   | Punjabi    |
| or   | Odia       |

## Retry Logic

The client implements exponential backoff:

1. **Initial attempt**: Immediate
2. **Retry 1**: Wait 1 second
3. **Retry 2**: Wait 2 seconds
4. **Retry 3**: Wait 4 seconds
5. **Max delay**: 10 seconds

Permanent errors are not retried.

## Performance Considerations

- **Timeout**: Default 30 seconds (configurable)
- **Max Retries**: Default 3 attempts (configurable)
- **Payload Size**: Images and audio are base64 encoded (increases size by ~33%)
- **Concurrent Requests**: Client is thread-safe for concurrent invocations

## Monitoring

The client logs all operations:

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('backend.services.sagemaker_client')
```

Log levels:
- **INFO**: Successful operations, retry attempts
- **WARNING**: Low confidence results, transient errors
- **ERROR**: Permanent errors, exhausted retries

## Testing

Run the example script:

```bash
python -m backend.services.sagemaker_client.example_usage
```

## IAM Permissions

The Lambda execution role needs:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sagemaker:InvokeEndpoint",
        "sagemaker:DescribeEndpoint"
      ],
      "Resource": "arn:aws:sagemaker:REGION:ACCOUNT:endpoint/ENDPOINT_NAME"
    }
  ]
}
```

## Deployment

See [SAGEMAKER_ENDPOINT_DEPLOYMENT.md](../../../docs/SAGEMAKER_ENDPOINT_DEPLOYMENT.md) for endpoint deployment instructions.

## Architecture

```
┌─────────────────┐
│  Lambda/Client  │
└────────┬────────┘
         │
         │ invoke_combined_endpoint()
         │
         ▼
┌─────────────────────────┐
│  SagemakerClient        │
│  - Retry Logic          │
│  - Error Categorization │
│  - Confidence Flagging  │
└────────┬────────────────┘
         │
         │ boto3 invoke_endpoint()
         │
         ▼
┌─────────────────────────┐
│  Sagemaker Endpoint     │
│  - Vision Model         │
│  - ASR Model            │
│  - Preprocessing        │
└─────────────────────────┘
```

## Requirements Validation

This implementation satisfies the following requirements:

- **Requirement 4.1**: ASR transcribes vernacular audio (10 languages)
- **Requirement 4.2**: Support for all listed languages
- **Requirement 4.3**: Preserves original vernacular text
- **Requirement 4.4**: Flags low-confidence segments for manual review
- **Requirement 6.1**: Detects and extracts primary product from images
- **Requirement 6.5**: Notifies if image quality is too poor (via confidence flags)
- **Requirement 7.1**: Extracts product category from image and text
- **Requirement 14.1**: Implements fault tolerance and graceful degradation

## License

Part of the Vernacular Artisan Catalog system.
