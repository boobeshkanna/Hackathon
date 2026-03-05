## Rekognition Custom Labels Setup (Optional)

Rekognition Custom Labels allows you to train a model to detect specific artisan product categories.

### When to Use

✅ Use Custom Labels if:
- You have 1000+ labeled product images
- You need specific product categories (e.g., "Banarasi Silk Saree" vs "Saree")
- You have budget for $4/hour model running cost
- You need 90%+ detection accuracy

❌ Skip Custom Labels if:
- You don't have labeled training data
- Generic categories are sufficient
- Budget is limited
- You're building an MVP

**Note:** The system works fine without Custom Labels using standard Rekognition as fallback.

### Training Data Requirements

- **Minimum**: 1000 labeled images per category
- **Recommended**: 2000+ images per category
- **Categories**: 10-50 product categories
- **Format**: JPEG or PNG
- **Size**: 15KB - 15MB per image

### Setup Steps

#### 1. Prepare Training Data

```bash
# Organize images by category
training_data/
├── banarasi_silk_saree/
│   ├── image001.jpg
│   ├── image002.jpg
│   └── ...
├── pottery/
│   ├── image001.jpg
│   └── ...
└── jewelry/
    └── ...
```

#### 2. Create S3 Bucket and Upload

```bash
# Create bucket
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
aws s3 mb s3://rekognition-training-${ACCOUNT_ID}

# Upload training data
aws s3 sync training_data/ s3://rekognition-training-${ACCOUNT_ID}/training/
```

#### 3. Create Manifest File

```json
{
  "source-ref": "s3://rekognition-training-ACCOUNT/training/banarasi_silk_saree/image001.jpg",
  "category": "Banarasi Silk Saree",
  "category-metadata": {
    "confidence": 1,
    "job-name": "labeling-job",
    "class-name": "Banarasi Silk Saree",
    "human-annotated": "yes",
    "creation-date": "2024-01-01T00:00:00",
    "type": "groundtruth/image-classification"
  }
}
```

#### 4. Create Project via Console

1. Go to AWS Console > Rekognition > Custom Labels
2. Click "Create project"
3. Name: "artisan-product-detection"
4. Click "Create project"

#### 5. Create Dataset

1. In project, click "Create dataset"
2. Choose "Import images from S3"
3. S3 URI: `s3://rekognition-training-ACCOUNT/training/`
4. Upload manifest file
5. Click "Create dataset"

#### 6. Train Model

1. Click "Train model"
2. Choose training dataset
3. Choose test dataset (20% split)
4. Click "Train"
5. Wait 1-2 hours for training

**Cost**: ~$1 per hour of training

#### 7. Evaluate Model

After training:
- Check F1 score (should be > 0.90)
- Review per-category metrics
- Test with sample images

#### 8. Deploy Model

```bash
# Get project ARN
PROJECT_ARN=$(aws rekognition describe-projects \
    --query 'ProjectDescriptions[?ProjectName==`artisan-product-detection`].ProjectArn' \
    --output text)

# Get latest model version ARN
MODEL_ARN=$(aws rekognition describe-project-versions \
    --project-arn $PROJECT_ARN \
    --query 'ProjectVersionDescriptions[0].ProjectVersionArn' \
    --output text)

# Start model
aws rekognition start-project-version \
    --project-version-arn $MODEL_ARN \
    --min-inference-units 1

# Wait 10-30 minutes for model to start
```

#### 9. Configure in Code

```python
from backend.services.ai_orchestrator import AIOrchestrator

orchestrator = AIOrchestrator(
    region='ap-south-1',
    rekognition_project_arn='arn:aws:rekognition:ap-south-1:ACCOUNT:project/artisan-product-detection/...',
    transcribe_s3_bucket='my-bucket'
)
```

### Cost Management

#### Running Costs

```
Model running: $4/hour × 730 hours/month = $2,920/month
Inference: $0.001 per image
```

#### Cost Optimization

**Option 1: On-Demand (Recommended for MVP)**
```bash
# Start model only when needed
aws rekognition start-project-version --project-version-arn $MODEL_ARN --min-inference-units 1

# Process images (takes 10-30 min to start)
# ...

# Stop model when done
aws rekognition stop-project-version --project-version-arn $MODEL_ARN
```

**Option 2: Scheduled**
```bash
# Use CloudWatch Events to start/stop on schedule
# Example: Run 9 AM - 6 PM weekdays only
# Cost: $4/hour × 9 hours × 5 days × 4 weeks = $720/month
```

**Option 3: Event-Driven**
```bash
# Start model when queue depth > threshold
# Stop model when idle for > 30 minutes
# Requires custom Lambda function
```

### Testing

```python
from backend.services.rekognition_custom import RekognitionProductDetector

detector = RekognitionProductDetector(
    project_arn='arn:aws:rekognition:...',
    region='ap-south-1'
)

# Check status
status = detector.get_model_status()
print(f"Model status: {status}")

# Start if needed
if status != 'RUNNING':
    detector.start_model()
    print("Starting model (wait 10-30 minutes)...")

# Test detection
with open('test_image.jpg', 'rb') as f:
    result = detector.detect_products(f.read())
    
print(f"Detected: {result['primary_category']}")
print(f"Confidence: {result['primary_confidence']:.2%}")
```

### Fallback Behavior

If Custom Labels model is not running or not configured:
- System automatically falls back to standard Rekognition
- Generic labels are used (e.g., "Clothing" instead of "Banarasi Silk Saree")
- No errors or failures
- Slightly lower accuracy but still functional

### Monitoring

```bash
# Check model status
aws rekognition describe-project-versions \
    --project-arn $PROJECT_ARN

# View CloudWatch metrics
aws cloudwatch get-metric-statistics \
    --namespace AWS/Rekognition \
    --metric-name UserErrorCount \
    --dimensions Name=ProjectVersionArn,Value=$MODEL_ARN \
    --start-time 2024-01-01T00:00:00Z \
    --end-time 2024-01-02T00:00:00Z \
    --period 3600 \
    --statistics Sum
```

### Troubleshooting

**Model won't start**
- Check IAM permissions
- Verify model is in TRAINING_COMPLETED status
- Check CloudWatch logs

**Low accuracy**
- Add more training images (2000+ per category)
- Balance dataset (equal images per category)
- Improve image quality
- Retrain model

**High costs**
- Stop model when not in use
- Use scheduled start/stop
- Consider standard Rekognition for MVP

### Recommendation

**For MVP: Skip Custom Labels**
- Use standard Rekognition (included in orchestrator)
- Save $2,920/month
- Still get good results with Claude 3.5 Sonnet
- Train Custom Labels later when you have data and budget

**For Production: Use Custom Labels**
- Train after collecting 1000+ labeled images
- Implement on-demand start/stop
- Monitor costs closely
- Provides best accuracy for specific products
