# Sagemaker Vision & ASR Endpoint Deployment Guide

## Overview

This guide describes how to deploy a combined multimodal Sagemaker endpoint that handles both image analysis (Vision) and audio transcription (ASR) for the Vernacular Artisan Catalog system.

## Architecture

The endpoint uses a single multimodal model that can process:
- **Image inputs**: Product images for category detection, color extraction, material identification
- **Audio inputs**: Vernacular audio recordings for transcription with language detection

### Supported Languages

The ASR component must support the following vernacular languages:
- Hindi (hi)
- Tamil (ta)
- Telugu (te)
- Bengali (bn)
- Marathi (mr)
- Gujarati (gu)
- Kannada (kn)
- Malayalam (ml)
- Punjabi (pa)
- Odia (or)

## Model Requirements

### Vision Model Capabilities
- Object detection and extraction
- Product category classification
- Color detection (primary and secondary colors)
- Material identification (fabric, metal, wood, clay, etc.)
- Confidence scoring (minimum threshold: 0.6)

### ASR Model Capabilities
- Multilingual speech recognition for Indian languages
- Automatic language detection
- Confidence scoring per segment (minimum threshold: 0.7)
- Support for audio formats: Opus, MP3, WAV
- Maximum audio duration: 2 minutes

## Deployment Steps

### 1. Model Selection

**Option A: Use Pre-trained Models**
- Vision: Use AWS Rekognition Custom Labels or fine-tuned CLIP model
- ASR: Use IndicWav2Vec or Whisper with Indic language support

**Option B: Custom Multimodal Model**
- Train a unified model that accepts both image and audio inputs
- Use a shared embedding space for cross-modal understanding

### 2. Model Packaging

Create a model package with the following structure:

```
model/
├── code/
│   ├── inference.py          # Inference handler
│   ├── requirements.txt      # Python dependencies
│   └── preprocessing.py      # Input preprocessing
├── model_artifacts/
│   ├── vision_model.pth      # Vision model weights
│   └── asr_model.pth         # ASR model weights
└── config.json               # Model configuration
```

### 3. Inference Handler Implementation

The `inference.py` must implement the following interface:

```python
def model_fn(model_dir):
    """Load the model from the model directory"""
    # Load vision and ASR models
    pass

def input_fn(request_body, content_type):
    """Preprocess input data"""
    # Parse JSON payload with image and/or audio
    pass

def predict_fn(input_data, model):
    """Run inference"""
    # Process image and audio through respective models
    pass

def output_fn(prediction, accept):
    """Format output"""
    # Return structured JSON response
    pass
```

### 4. Input/Output Schema

**Input Format:**

```json
{
  "image": "base64_encoded_image_data",
  "audio": "base64_encoded_audio_data",
  "language_hint": "hi",
  "task": "multimodal_analysis"
}
```

**Output Format:**

```json
{
  "transcription": {
    "text": "यह एक हाथ से बुनी हुई रेशमी साड़ी है",
    "language": "hi",
    "confidence": 0.92,
    "segments": [
      {
        "text": "यह एक हाथ से बुनी हुई",
        "start": 0.0,
        "end": 2.5,
        "confidence": 0.95
      },
      {
        "text": "रेशमी साड़ी है",
        "start": 2.5,
        "end": 4.0,
        "confidence": 0.89
      }
    ]
  },
  "vision": {
    "category": "Handloom Saree",
    "subcategory": "Silk Saree",
    "colors": ["red", "gold", "maroon"],
    "materials": ["silk", "zari"],
    "confidence": 0.87,
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

### 5. Preprocessing Requirements

**Image Preprocessing:**
- Resize to model input dimensions (e.g., 224x224 or 512x512)
- Normalize pixel values (mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
- Convert to RGB if grayscale
- Handle EXIF orientation

**Audio Preprocessing:**
- Convert to WAV format if needed
- Resample to model's expected sample rate (typically 16kHz)
- Normalize audio levels
- Trim silence from beginning and end

### 6. Create Sagemaker Endpoint

```bash
# 1. Upload model artifacts to S3
aws s3 cp model.tar.gz s3://your-bucket/models/vernacular-vision-asr/

# 2. Create model
aws sagemaker create-model \
    --model-name vernacular-vision-asr-model \
    --primary-container Image=<ecr-image-uri>,ModelDataUrl=s3://your-bucket/models/vernacular-vision-asr/model.tar.gz \
    --execution-role-arn arn:aws:iam::ACCOUNT:role/SagemakerExecutionRole

# 3. Create endpoint configuration
aws sagemaker create-endpoint-config \
    --endpoint-config-name vernacular-vision-asr-config \
    --production-variants VariantName=AllTraffic,ModelName=vernacular-vision-asr-model,InstanceType=ml.g4dn.xlarge,InitialInstanceCount=1

# 4. Create endpoint
aws sagemaker create-endpoint \
    --endpoint-name vernacular-vision-asr-endpoint \
    --endpoint-config-name vernacular-vision-asr-config
```

### 7. Instance Type Selection

**Recommended Instance Types:**
- **Development/Testing**: `ml.g4dn.xlarge` (1 GPU, 16GB GPU memory)
- **Production**: `ml.g4dn.2xlarge` or `ml.g4dn.4xlarge` (for higher throughput)
- **Cost-Optimized**: `ml.inf1.xlarge` (AWS Inferentia chip for inference)

### 8. Auto-Scaling Configuration

```bash
# Register scalable target
aws application-autoscaling register-scalable-target \
    --service-namespace sagemaker \
    --resource-id endpoint/vernacular-vision-asr-endpoint/variant/AllTraffic \
    --scalable-dimension sagemaker:variant:DesiredInstanceCount \
    --min-capacity 1 \
    --max-capacity 5

# Create scaling policy
aws application-autoscaling put-scaling-policy \
    --service-namespace sagemaker \
    --resource-id endpoint/vernacular-vision-asr-endpoint/variant/AllTraffic \
    --scalable-dimension sagemaker:variant:DesiredInstanceCount \
    --policy-name vernacular-scaling-policy \
    --policy-type TargetTrackingScaling \
    --target-tracking-scaling-policy-configuration file://scaling-policy.json
```

**scaling-policy.json:**
```json
{
  "TargetValue": 70.0,
  "PredefinedMetricSpecification": {
    "PredefinedMetricType": "SageMakerVariantInvocationsPerInstance"
  },
  "ScaleInCooldown": 300,
  "ScaleOutCooldown": 60
}
```

## Configuration

### Environment Variables

Set the following environment variables in Lambda functions:

```bash
SAGEMAKER_ENDPOINT_NAME=vernacular-vision-asr-endpoint
SAGEMAKER_REGION=ap-south-1
SAGEMAKER_TIMEOUT_SECONDS=30
SAGEMAKER_MAX_RETRIES=3
ASR_CONFIDENCE_THRESHOLD=0.7
VISION_CONFIDENCE_THRESHOLD=0.6
```

### IAM Permissions

The Lambda execution role needs the following permissions:

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
      "Resource": "arn:aws:sagemaker:ap-south-1:ACCOUNT:endpoint/vernacular-vision-asr-endpoint"
    }
  ]
}
```

## Testing

### Test the Endpoint

```python
import boto3
import json
import base64

client = boto3.client('sagemaker-runtime', region_name='ap-south-1')

# Load test data
with open('test_image.jpg', 'rb') as f:
    image_data = base64.b64encode(f.read()).decode('utf-8')

with open('test_audio.opus', 'rb') as f:
    audio_data = base64.b64encode(f.read()).decode('utf-8')

# Prepare payload
payload = {
    'image': image_data,
    'audio': audio_data,
    'language_hint': 'hi',
    'task': 'multimodal_analysis'
}

# Invoke endpoint
response = client.invoke_endpoint(
    EndpointName='vernacular-vision-asr-endpoint',
    ContentType='application/json',
    Body=json.dumps(payload)
)

# Parse response
result = json.loads(response['Body'].read().decode())
print(json.dumps(result, indent=2))
```

## Monitoring

### CloudWatch Metrics

Monitor the following metrics:
- `ModelLatency`: Time taken for inference
- `Invocations`: Number of endpoint invocations
- `InvocationErrors`: Number of failed invocations
- `CPUUtilization`: CPU usage
- `GPUUtilization`: GPU usage (if applicable)
- `MemoryUtilization`: Memory usage

### Alarms

Create CloudWatch alarms for:
- High latency (> 5 seconds)
- High error rate (> 5%)
- Low confidence scores (> 20% of requests)

## Cost Optimization

1. **Use Spot Instances**: For non-production environments
2. **Auto-Scaling**: Scale down during low-traffic periods
3. **Batch Processing**: Process multiple requests in a single invocation when possible
4. **Model Optimization**: Use model quantization and pruning to reduce inference time
5. **Async Inference**: Use Sagemaker Async Inference for non-real-time workloads

## Troubleshooting

### Common Issues

**Issue: Endpoint creation fails**
- Check IAM role permissions
- Verify model artifacts are accessible in S3
- Check CloudWatch logs for detailed error messages

**Issue: High latency**
- Consider using larger instance types
- Optimize model (quantization, pruning)
- Enable model compilation with SageMaker Neo

**Issue: Low confidence scores**
- Fine-tune model on domain-specific data
- Improve input data quality
- Adjust confidence thresholds

**Issue: Out of memory errors**
- Use larger instance types
- Reduce batch size
- Optimize model architecture

## References

- [AWS Sagemaker Documentation](https://docs.aws.amazon.com/sagemaker/)
- [Sagemaker Inference](https://docs.aws.amazon.com/sagemaker/latest/dg/deploy-model.html)
- [IndicWav2Vec Model](https://huggingface.co/ai4bharat/indicwav2vec)
- [CLIP Model](https://github.com/openai/CLIP)
