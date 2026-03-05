#!/bin/bash

set -e

echo "=========================================="
echo "Packaging SageMaker Model"
echo "=========================================="

MODEL_DIR="backend/services/sagemaker_client/model"
OUTPUT_FILE="model.tar.gz"

# Check if model directory exists
if [ ! -d "$MODEL_DIR" ]; then
    echo "❌ Model directory not found: $MODEL_DIR"
    exit 1
fi

echo "Packaging model from: $MODEL_DIR"

# Create temporary directory for packaging
TMP_DIR=$(mktemp -d)
echo "Using temporary directory: $TMP_DIR"

# Copy model files
echo "Copying model files..."
cp -r "$MODEL_DIR"/* "$TMP_DIR/"

# Create code directory if it doesn't exist
mkdir -p "$TMP_DIR/code"

# Move inference.py and requirements.txt to code directory
if [ -f "$TMP_DIR/inference.py" ]; then
    mv "$TMP_DIR/inference.py" "$TMP_DIR/code/"
fi

if [ -f "$TMP_DIR/requirements.txt" ]; then
    mv "$TMP_DIR/requirements.txt" "$TMP_DIR/code/"
fi

# Create tar.gz archive
echo "Creating archive..."
cd "$TMP_DIR"
tar -czf "$OUTPUT_FILE" *
cd - > /dev/null

# Move archive to current directory
mv "$TMP_DIR/$OUTPUT_FILE" .

# Cleanup
rm -rf "$TMP_DIR"

echo ""
echo "=========================================="
echo "✅ Model packaged successfully!"
echo "=========================================="
echo ""
echo "Output file: $OUTPUT_FILE"
echo "Size: $(du -h $OUTPUT_FILE | cut -f1)"
echo ""
echo "Next steps:"
echo "  1. Upload to S3:"
echo "     aws s3 cp $OUTPUT_FILE s3://sagemaker-REGION-ACCOUNT/models/vernacular-vision-asr/"
echo ""
echo "  2. Deploy endpoint:"
echo "     ./backend/services/sagemaker_client/deploy_endpoint.sh"
echo ""
