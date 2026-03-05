#!/bin/bash

set -e

echo "=========================================="
echo "Deploying SageMaker Endpoint"
echo "=========================================="

# Configuration
ENDPOINT_NAME="vernacular-vision-asr-endpoint"
MODEL_NAME="vernacular-vision-asr-model"
CONFIG_NAME="vernacular-vision-asr-config"
REGION="ap-south-1"
INSTANCE_TYPE="ml.g4dn.xlarge"
INITIAL_INSTANCE_COUNT=1

# Get AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "AWS Account ID: $ACCOUNT_ID"

# Check if model artifacts exist
MODEL_BUCKET="sagemaker-${REGION}-${ACCOUNT_ID}"
MODEL_S3_PATH="s3://${MODEL_BUCKET}/models/vernacular-vision-asr/model.tar.gz"

echo ""
echo "Checking for model artifacts at: $MODEL_S3_PATH"
if ! aws s3 ls "$MODEL_S3_PATH" &> /dev/null; then
    echo "❌ Model artifacts not found at $MODEL_S3_PATH"
    echo ""
    echo "Please upload your model artifacts first:"
    echo "  1. Package your model: tar -czf model.tar.gz model/"
    echo "  2. Upload to S3: aws s3 cp model.tar.gz $MODEL_S3_PATH"
    echo ""
    echo "For testing, you can use a placeholder model."
    exit 1
fi

echo "✅ Model artifacts found"

# Get SageMaker execution role
ROLE_NAME="SageMakerExecutionRole"
ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"

echo ""
echo "Checking for SageMaker execution role: $ROLE_NAME"
if ! aws iam get-role --role-name "$ROLE_NAME" &> /dev/null; then
    echo "Creating SageMaker execution role..."
    
    # Create trust policy
    cat > /tmp/trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "sagemaker.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
    
    aws iam create-role \
        --role-name "$ROLE_NAME" \
        --assume-role-policy-document file:///tmp/trust-policy.json
    
    # Attach managed policies
    aws iam attach-role-policy \
        --role-name "$ROLE_NAME" \
        --policy-arn "arn:aws:iam::aws:policy/AmazonSageMakerFullAccess"
    
    echo "✅ Role created"
    echo "Waiting 10 seconds for role to propagate..."
    sleep 10
else
    echo "✅ Role exists"
fi

# Get container image URI (using built-in PyTorch container)
echo ""
echo "Getting container image URI..."
IMAGE_URI="763104351884.dkr.ecr.${REGION}.amazonaws.com/pytorch-inference:2.0.0-gpu-py310"
echo "Using image: $IMAGE_URI"

# Create or update model
echo ""
echo "Creating SageMaker model..."
if aws sagemaker describe-model --model-name "$MODEL_NAME" &> /dev/null; then
    echo "Model $MODEL_NAME already exists, deleting..."
    aws sagemaker delete-model --model-name "$MODEL_NAME"
    sleep 5
fi

aws sagemaker create-model \
    --model-name "$MODEL_NAME" \
    --primary-container \
        Image="$IMAGE_URI",ModelDataUrl="$MODEL_S3_PATH" \
    --execution-role-arn "$ROLE_ARN" \
    --region "$REGION"

echo "✅ Model created: $MODEL_NAME"

# Create endpoint configuration
echo ""
echo "Creating endpoint configuration..."
if aws sagemaker describe-endpoint-config --endpoint-config-name "$CONFIG_NAME" &> /dev/null; then
    echo "Endpoint config $CONFIG_NAME already exists, deleting..."
    aws sagemaker delete-endpoint-config --endpoint-config-name "$CONFIG_NAME"
    sleep 5
fi

aws sagemaker create-endpoint-config \
    --endpoint-config-name "$CONFIG_NAME" \
    --production-variants \
        VariantName=AllTraffic,ModelName="$MODEL_NAME",InstanceType="$INSTANCE_TYPE",InitialInstanceCount=$INITIAL_INSTANCE_COUNT \
    --region "$REGION"

echo "✅ Endpoint configuration created: $CONFIG_NAME"

# Create or update endpoint
echo ""
echo "Creating SageMaker endpoint..."
if aws sagemaker describe-endpoint --endpoint-name "$ENDPOINT_NAME" &> /dev/null; then
    echo "Endpoint $ENDPOINT_NAME already exists, updating..."
    aws sagemaker update-endpoint \
        --endpoint-name "$ENDPOINT_NAME" \
        --endpoint-config-name "$CONFIG_NAME" \
        --region "$REGION"
else
    aws sagemaker create-endpoint \
        --endpoint-name "$ENDPOINT_NAME" \
        --endpoint-config-name "$CONFIG_NAME" \
        --region "$REGION"
fi

echo "✅ Endpoint creation initiated: $ENDPOINT_NAME"

# Wait for endpoint to be in service
echo ""
echo "Waiting for endpoint to be in service (this may take 5-10 minutes)..."
aws sagemaker wait endpoint-in-service \
    --endpoint-name "$ENDPOINT_NAME" \
    --region "$REGION"

echo ""
echo "=========================================="
echo "✅ SageMaker Endpoint Deployed Successfully!"
echo "=========================================="
echo ""
echo "Endpoint Name: $ENDPOINT_NAME"
echo "Region: $REGION"
echo "Instance Type: $INSTANCE_TYPE"
echo ""
echo "Set the following environment variable in your Lambda functions:"
echo "  SAGEMAKER_ENDPOINT_NAME=$ENDPOINT_NAME"
echo ""
echo "To test the endpoint, run:"
echo "  python backend/services/sagemaker_client/test_endpoint.py"
echo ""
