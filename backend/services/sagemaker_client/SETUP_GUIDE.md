# SageMaker Endpoint Setup Guide

Complete guide to set up the SageMaker endpoint for Vision + ASR inference.

## Prerequisites

- AWS CLI configured with appropriate credentials
- AWS account with SageMaker access
- Python 3.8+ with boto3 installed
- Sufficient AWS service limits for SageMaker endpoints

## Quick Start

### Option 1: Deploy with Placeholder Model (for testing)

This deploys a placeholder model that returns mock responses. Useful for testing the infrastructure.

```bash
# 1. Package the placeholder model
./backend/services/sagemaker_client/package_model.sh

# 2. Upload to S3
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="ap-south-1"
aws s3 mb s3://sagemaker-${REGION}-${ACCOUNT_ID} 2>/dev/null || true
aws s3 cp model.tar.gz s3://sagemaker-${REGION}-${ACCOUNT_ID}/models/vernacular-vision-asr/

# 3. Deploy endpoint
./backend/services/sagemaker_client/deploy_endpoint.sh

# 4. Test endpoint
export SAGEMAKER_ENDPOINT_NAME=vernacular-vision-asr-endpoint
python backend/services/sagemaker_client/test_endpoint.py
```

### Option 2: Deploy with Your Own Model

If you have trained your own Vision + ASR model:

```bash
# 1. Prepare your model directory structure
mkdir -p my_model/code
mkdir -p my_model/model_artifacts

# 2. Add your inference code
cp your_inference.py my_model/code/inference.py
cp your_requirements.txt my_model/code/requirements.txt

# 3. Add your model weights
cp your_vision_model.pth my_model/model_artifacts/
cp your_asr_model.pth my_model/model_artifacts/

# 4. Package the model
cd my_model
tar -czf model.tar.gz *
cd ..

# 5. Upload to S3
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="ap-south-1"
aws s3 cp my_model/model.tar.gz s3://sagemaker-${REGION}-${ACCOUNT_ID}/models/vernacular-vision-asr/

# 6. Deploy endpoint
./backend/services/sagemaker_client/deploy_endpoint.sh
```

## Detailed Steps

### Step 1: Prepare Model Artifacts

Your model directory should follow this structure:

```
model/
├── code/
│   ├── inference.py          # Inference handler (required)
│   └── requirements.txt      # Python dependencies (required)
└── model_artifacts/          # Optional: model weights
    ├── vision_model.pth
    └── asr_model.pth
```

#### inference.py Requirements

Your `inference.py` must implement these functions:

```python
def model_fn(model_dir: str):
    """Load model from directory"""
    pass

def input_fn(request_body: bytes, content_type: str):
    """Preprocess input"""
    pass

def predict_fn(input_data, model):
    """Run inference"""
    pass

def output_fn(prediction, accept: str):
    """Format output"""
    pass
```

See `backend/services/sagemaker_client/model/inference.py` for a complete example.

### Step 2: Package Model

```bash
./backend/services/sagemaker_client/package_model.sh
```

This creates `model.tar.gz` with the correct structure for SageMaker.

### Step 3: Upload to S3

```bash
# Get your AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="ap-south-1"

# Create S3 bucket if it doesn't exist
aws s3 mb s3://sagemaker-${REGION}-${ACCOUNT_ID} 2>/dev/null || true

# Upload model
aws s3 cp model.tar.gz s3://sagemaker-${REGION}-${ACCOUNT_ID}/models/vernacular-vision-asr/
```

### Step 4: Deploy Endpoint

```bash
./backend/services/sagemaker_client/deploy_endpoint.sh
```

This script will:
1. Create SageMaker execution role (if needed)
2. Create SageMaker model
3. Create endpoint configuration
4. Deploy endpoint
5. Wait for endpoint to be in service

**Note:** Endpoint deployment takes 5-10 minutes.

### Step 5: Configure Lambda Environment

Add the endpoint name to your Lambda environment variables:

```bash
# In your CDK stack or Lambda configuration
SAGEMAKER_ENDPOINT_NAME=vernacular-vision-asr-endpoint
SAGEMAKER_REGION=ap-south-1
SAGEMAKER_TIMEOUT_SECONDS=30
SAGEMAKER_MAX_RETRIES=3
ASR_CONFIDENCE_THRESHOLD=0.7
VISION_CONFIDENCE_THRESHOLD=0.6
```

### Step 6: Test Endpoint

```bash
# Set endpoint name
export SAGEMAKER_ENDPOINT_NAME=vernacular-vision-asr-endpoint

# Run all tests
python backend/services/sagemaker_client/test_endpoint.py

# Run specific test
python backend/services/sagemaker_client/test_endpoint.py --test health
python backend/services/sagemaker_client/test_endpoint.py --test vision
python backend/services/sagemaker_client/test_endpoint.py --test asr --language hi
python backend/services/sagemaker_client/test_endpoint.py --test combined

# Test with your own files
python backend/services/sagemaker_client/test_endpoint.py \
    --image path/to/image.jpg \
    --audio path/to/audio.opus \
    --language hi
```

## Instance Types

Choose an instance type based on your needs:

| Instance Type | vCPUs | GPU Memory | Use Case | Cost/Hour* |
|--------------|-------|------------|----------|-----------|
| ml.g4dn.xlarge | 4 | 16 GB | Development/Testing | ~$0.70 |
| ml.g4dn.2xlarge | 8 | 16 GB | Production (low traffic) | ~$1.00 |
| ml.g4dn.4xlarge | 16 | 16 GB | Production (high traffic) | ~$1.60 |
| ml.inf1.xlarge | 4 | - | Cost-optimized (Inferentia) | ~$0.40 |

*Approximate costs in ap-south-1 region

To change instance type, edit `deploy_endpoint.sh`:

```bash
INSTANCE_TYPE="ml.g4dn.2xlarge"  # Change this line
```

## Auto-Scaling Setup

Enable auto-scaling to handle traffic spikes:

```bash
# Register scalable target
aws application-autoscaling register-scalable-target \
    --service-namespace sagemaker \
    --resource-id endpoint/vernacular-vision-asr-endpoint/variant/AllTraffic \
    --scalable-dimension sagemaker:variant:DesiredInstanceCount \
    --min-capacity 1 \
    --max-capacity 5

# Create scaling policy
cat > scaling-policy.json <<EOF
{
  "TargetValue": 70.0,
  "PredefinedMetricSpecification": {
    "PredefinedMetricType": "SageMakerVariantInvocationsPerInstance"
  },
  "ScaleInCooldown": 300,
  "ScaleOutCooldown": 60
}
EOF

aws application-autoscaling put-scaling-policy \
    --service-namespace sagemaker \
    --resource-id endpoint/vernacular-vision-asr-endpoint/variant/AllTraffic \
    --scalable-dimension sagemaker:variant:DesiredInstanceCount \
    --policy-name vernacular-scaling-policy \
    --policy-type TargetTrackingScaling \
    --target-tracking-scaling-policy-configuration file://scaling-policy.json
```

## Monitoring

### CloudWatch Metrics

Monitor these key metrics:

- `ModelLatency`: Inference time
- `Invocations`: Request count
- `InvocationErrors`: Error count
- `CPUUtilization`: CPU usage
- `GPUUtilization`: GPU usage
- `MemoryUtilization`: Memory usage

### Create Alarms

```bash
# High latency alarm
aws cloudwatch put-metric-alarm \
    --alarm-name sagemaker-high-latency \
    --alarm-description "Alert when latency exceeds 5 seconds" \
    --metric-name ModelLatency \
    --namespace AWS/SageMaker \
    --statistic Average \
    --period 300 \
    --evaluation-periods 2 \
    --threshold 5000 \
    --comparison-operator GreaterThanThreshold \
    --dimensions Name=EndpointName,Value=vernacular-vision-asr-endpoint Name=VariantName,Value=AllTraffic

# High error rate alarm
aws cloudwatch put-metric-alarm \
    --alarm-name sagemaker-high-errors \
    --alarm-description "Alert when error rate exceeds 5%" \
    --metric-name Invocation4XXErrors \
    --namespace AWS/SageMaker \
    --statistic Sum \
    --period 300 \
    --evaluation-periods 1 \
    --threshold 5 \
    --comparison-operator GreaterThanThreshold \
    --dimensions Name=EndpointName,Value=vernacular-vision-asr-endpoint Name=VariantName,Value=AllTraffic
```

## Cost Optimization

### 1. Use Spot Instances (Non-Production)

Not directly supported for SageMaker endpoints, but you can use Async Inference with spot instances.

### 2. Auto-Scaling

Configure auto-scaling to scale down during low-traffic periods.

### 3. Async Inference

For non-real-time workloads, use SageMaker Async Inference:

```bash
aws sagemaker create-endpoint-config \
    --endpoint-config-name vernacular-async-config \
    --async-inference-config '{
        "OutputConfig": {
            "S3OutputPath": "s3://your-bucket/async-output/"
        }
    }' \
    --production-variants VariantName=AllTraffic,ModelName=vernacular-vision-asr-model,InstanceType=ml.g4dn.xlarge,InitialInstanceCount=1
```

### 4. Model Optimization

- Use model quantization (INT8, FP16)
- Use SageMaker Neo for model compilation
- Batch multiple requests when possible

## Troubleshooting

### Endpoint Creation Fails

**Check IAM permissions:**
```bash
aws iam get-role --role-name SageMakerExecutionRole
```

**Check CloudWatch logs:**
```bash
aws logs tail /aws/sagemaker/Endpoints/vernacular-vision-asr-endpoint --follow
```

### High Latency

1. Check instance type (upgrade if needed)
2. Optimize model (quantization, pruning)
3. Enable model compilation with SageMaker Neo
4. Check network latency

### Out of Memory Errors

1. Use larger instance type
2. Reduce batch size
3. Optimize model architecture
4. Check for memory leaks in inference code

### Low Confidence Scores

1. Fine-tune model on domain-specific data
2. Improve input data quality
3. Adjust confidence thresholds
4. Add data augmentation during training

## Cleanup

To delete the endpoint and save costs:

```bash
# Delete endpoint
aws sagemaker delete-endpoint --endpoint-name vernacular-vision-asr-endpoint

# Delete endpoint configuration
aws sagemaker delete-endpoint-config --endpoint-config-name vernacular-vision-asr-config

# Delete model
aws sagemaker delete-model --model-name vernacular-vision-asr-model

# Optional: Delete S3 artifacts
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="ap-south-1"
aws s3 rm s3://sagemaker-${REGION}-${ACCOUNT_ID}/models/vernacular-vision-asr/ --recursive
```

## Next Steps

1. **Train Your Model**: Replace the placeholder with your actual Vision + ASR model
2. **Fine-tune**: Fine-tune on domain-specific artisan product data
3. **Optimize**: Use model quantization and SageMaker Neo
4. **Monitor**: Set up CloudWatch dashboards and alarms
5. **Scale**: Configure auto-scaling based on traffic patterns

## Support

For issues or questions:
- Check CloudWatch logs: `/aws/sagemaker/Endpoints/vernacular-vision-asr-endpoint`
- Review SageMaker documentation: https://docs.aws.amazon.com/sagemaker/
- Check model inference logs in the endpoint

## References

- [SageMaker Inference Documentation](https://docs.aws.amazon.com/sagemaker/latest/dg/deploy-model.html)
- [SageMaker Python SDK](https://sagemaker.readthedocs.io/)
- [IndicWav2Vec Model](https://huggingface.co/ai4bharat/indicwav2vec)
- [CLIP Model](https://github.com/openai/CLIP)
