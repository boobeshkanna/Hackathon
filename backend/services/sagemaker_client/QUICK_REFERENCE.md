# SageMaker Endpoint Quick Reference

## Quick Deploy (Placeholder Model)

```bash
# 1. Package model
./backend/services/sagemaker_client/package_model.sh

# 2. Upload to S3
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
aws s3 cp model.tar.gz s3://sagemaker-ap-south-1-${ACCOUNT_ID}/models/vernacular-vision-asr/

# 3. Deploy
./backend/services/sagemaker_client/deploy_endpoint.sh

# 4. Test
export SAGEMAKER_ENDPOINT_NAME=vernacular-vision-asr-endpoint
python backend/services/sagemaker_client/test_endpoint.py
```

## Common Commands

### Check Endpoint Status
```bash
aws sagemaker describe-endpoint --endpoint-name vernacular-vision-asr-endpoint
```

### View Logs
```bash
aws logs tail /aws/sagemaker/Endpoints/vernacular-vision-asr-endpoint --follow
```

### Update Endpoint
```bash
# After changing model or config
aws sagemaker update-endpoint \
    --endpoint-name vernacular-vision-asr-endpoint \
    --endpoint-config-name vernacular-vision-asr-config
```

### Delete Endpoint
```bash
aws sagemaker delete-endpoint --endpoint-name vernacular-vision-asr-endpoint
```

## Python Client Usage

### Initialize Client
```python
from backend.services.sagemaker_client import SagemakerClient

client = SagemakerClient(
    endpoint_name='vernacular-vision-asr-endpoint',
    region='ap-south-1'
)
```

### Combined Inference
```python
result = client.invoke_combined_endpoint(
    image_bytes=image_data,
    audio_bytes=audio_data,
    language_hint='hi'
)
```

### Vision Only
```python
result = client.invoke_vision_model(image_bytes)
```

### ASR Only
```python
result = client.invoke_asr_model(audio_bytes, language_code='hi')
```

## Environment Variables

```bash
SAGEMAKER_ENDPOINT_NAME=vernacular-vision-asr-endpoint
SAGEMAKER_REGION=ap-south-1
SAGEMAKER_TIMEOUT_SECONDS=30
SAGEMAKER_MAX_RETRIES=3
ASR_CONFIDENCE_THRESHOLD=0.7
VISION_CONFIDENCE_THRESHOLD=0.6
```

## Instance Types

| Type | vCPUs | GPU | Cost/hr* | Use Case |
|------|-------|-----|----------|----------|
| ml.g4dn.xlarge | 4 | 16GB | $0.70 | Dev/Test |
| ml.g4dn.2xlarge | 8 | 16GB | $1.00 | Production |
| ml.inf1.xlarge | 4 | - | $0.40 | Cost-optimized |

*Approximate in ap-south-1

## Supported Languages

hi, ta, te, bn, mr, gu, kn, ml, pa, or

## Troubleshooting

### Endpoint not responding
```bash
# Check status
aws sagemaker describe-endpoint --endpoint-name vernacular-vision-asr-endpoint

# Check logs
aws logs tail /aws/sagemaker/Endpoints/vernacular-vision-asr-endpoint --follow
```

### High latency
- Upgrade instance type
- Enable auto-scaling
- Optimize model

### Out of memory
- Use larger instance
- Reduce batch size
- Check inference code

## Cost Monitoring

```bash
# Get invocation count
aws cloudwatch get-metric-statistics \
    --namespace AWS/SageMaker \
    --metric-name Invocations \
    --dimensions Name=EndpointName,Value=vernacular-vision-asr-endpoint \
    --start-time 2024-01-01T00:00:00Z \
    --end-time 2024-01-02T00:00:00Z \
    --period 3600 \
    --statistics Sum
```

## Files

- `client.py` - Python client with retry logic
- `config.py` - Configuration settings
- `model/inference.py` - Inference handler
- `deploy_endpoint.sh` - Deployment script
- `test_endpoint.py` - Test script
- `SETUP_GUIDE.md` - Complete setup guide
