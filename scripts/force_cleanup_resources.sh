#!/bin/bash

set -e

echo "=========================================="
echo "Force cleaning up AWS resources"
echo "=========================================="

# Delete DynamoDB tables
echo "Deleting DynamoDB tables..."
for table in "CatalogProcessingRecords" "LocalQueueEntries" "TenantConfigurations" "ArtisanProfiles"; do
    if aws dynamodb describe-table --table-name $table &> /dev/null; then
        echo "  Deleting table: $table"
        aws dynamodb delete-table --table-name $table
    else
        echo "  Table $table not found, skipping"
    fi
done

# Delete S3 buckets (need to empty them first)
echo ""
echo "Deleting S3 buckets..."
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

for bucket in "artisan-catalog-raw-media-${ACCOUNT_ID}" "artisan-catalog-enhanced-${ACCOUNT_ID}"; do
    if aws s3 ls s3://$bucket &> /dev/null; then
        echo "  Emptying bucket: $bucket"
        aws s3 rm s3://$bucket --recursive
        echo "  Deleting bucket: $bucket"
        aws s3 rb s3://$bucket
    else
        echo "  Bucket $bucket not found, skipping"
    fi
done

echo ""
echo "Waiting for DynamoDB tables to be deleted..."
sleep 10

echo ""
echo "=========================================="
echo "✅ All resources cleaned up!"
echo "You can now redeploy with:"
echo "  ./scripts/deploy_infrastructure.sh"
echo "=========================================="
