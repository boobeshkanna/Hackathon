#!/bin/bash

set -e

echo "=========================================="
echo "Cleaning up failed CDK deployment"
echo "=========================================="

STACK_NAME="VernacularArtisanCatalogStack"

# Check if stack exists
if aws cloudformation describe-stacks --stack-name $STACK_NAME &> /dev/null; then
    echo "Found stack $STACK_NAME, deleting..."
    aws cloudformation delete-stack --stack-name $STACK_NAME
    
    echo "Waiting for stack deletion to complete..."
    aws cloudformation wait stack-delete-complete --stack-name $STACK_NAME
    
    echo "✅ Stack deleted successfully"
else
    echo "Stack $STACK_NAME not found, nothing to delete"
fi

echo ""
echo "=========================================="
echo "Cleanup complete! You can now redeploy."
echo "Run: ./scripts/deploy_infrastructure.sh"
echo "=========================================="
