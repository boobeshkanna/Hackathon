"""
Integration Test Environment Setup

This module provides utilities for setting up and tearing down AWS integration test environment.
It creates test versions of all AWS resources needed for end-to-end testing.

Requirements: All
"""

import os
import json
import boto3
import pytest
from typing import Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class AWSIntegrationTestEnvironment:
    """Manages AWS resources for integration testing"""
    
    def __init__(self, test_suffix: Optional[str] = None):
        """
        Initialize test environment
        
        Args:
            test_suffix: Optional suffix for test resource names (defaults to timestamp)
        """
        self.test_suffix = test_suffix or datetime.now().strftime("%Y%m%d%H%M%S")
        self.region = os.getenv("AWS_REGION", "ap-south-1")
        
        # Initialize AWS clients
        self.s3_client = boto3.client('s3', region_name=self.region)
        self.dynamodb_client = boto3.client('dynamodb', region_name=self.region)
        self.sqs_client = boto3.client('sqs', region_name=self.region)
        self.lambda_client = boto3.client('lambda', region_name=self.region)
        self.apigateway_client = boto3.client('apigateway', region_name=self.region)
        self.sns_client = boto3.client('sns', region_name=self.region)
        
        # Resource names
        self.resources = {
            's3_raw_bucket': f"test-artisan-raw-{self.test_suffix}",
            's3_enhanced_bucket': f"test-artisan-enhanced-{self.test_suffix}",
            'dynamodb_catalog_table': f"TestCatalogRecords-{self.test_suffix}",
            'dynamodb_tenant_table': f"TestTenantConfig-{self.test_suffix}",
            'sqs_queue_name': f"test-catalog-queue-{self.test_suffix}",
            'sqs_dlq_name': f"test-catalog-dlq-{self.test_suffix}",
            'sns_topic_name': f"test-catalog-notifications-{self.test_suffix}",
            'mock_ondc_endpoint': None,  # Will be set up separately
        }
        
        self.created_resources = []
    
    def setup_all(self) -> Dict[str, Any]:
        """
        Set up all AWS resources for integration testing
        
        Returns:
            Dictionary containing all resource identifiers
        """
        print(f"Setting up integration test environment with suffix: {self.test_suffix}")
        
        # Create S3 buckets
        self._setup_s3_buckets()
        
        # Create DynamoDB tables
        self._setup_dynamodb_tables()
        
        # Create SQS queues
        self._setup_sqs_queues()
        
        # Create SNS topic
        self._setup_sns_topic()
        
        # Set up mock ONDC endpoint (using API Gateway mock)
        self._setup_mock_ondc_endpoint()
        
        print("Integration test environment setup complete")
        return self.resources
    
    def _setup_s3_buckets(self):
        """Create S3 buckets for raw and enhanced media"""
        print("Creating S3 buckets...")
        
        for bucket_key in ['s3_raw_bucket', 's3_enhanced_bucket']:
            bucket_name = self.resources[bucket_key]
            try:
                if self.region == 'us-east-1':
                    self.s3_client.create_bucket(Bucket=bucket_name)
                else:
                    self.s3_client.create_bucket(
                        Bucket=bucket_name,
                        CreateBucketConfiguration={'LocationConstraint': self.region}
                    )
                
                # Enable versioning
                self.s3_client.put_bucket_versioning(
                    Bucket=bucket_name,
                    VersioningConfiguration={'Status': 'Enabled'}
                )
                
                # Enable encryption
                self.s3_client.put_bucket_encryption(
                    Bucket=bucket_name,
                    ServerSideEncryptionConfiguration={
                        'Rules': [{
                            'ApplyServerSideEncryptionByDefault': {
                                'SSEAlgorithm': 'AES256'
                            }
                        }]
                    }
                )
                
                self.created_resources.append(('s3', bucket_name))
                print(f"  Created S3 bucket: {bucket_name}")
            except Exception as e:
                print(f"  Error creating S3 bucket {bucket_name}: {e}")
                raise
    
    def _setup_dynamodb_tables(self):
        """Create DynamoDB tables for catalog and tenant data"""
        print("Creating DynamoDB tables...")
        
        # Catalog processing records table
        catalog_table = self.resources['dynamodb_catalog_table']
        try:
            self.dynamodb_client.create_table(
                TableName=catalog_table,
                KeySchema=[
                    {'AttributeName': 'tracking_id', 'KeyType': 'HASH'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'tracking_id', 'AttributeType': 'S'},
                    {'AttributeName': 'tenant_id', 'AttributeType': 'S'},
                    {'AttributeName': 'created_at', 'AttributeType': 'S'}
                ],
                GlobalSecondaryIndexes=[
                    {
                        'IndexName': 'TenantIndex',
                        'KeySchema': [
                            {'AttributeName': 'tenant_id', 'KeyType': 'HASH'},
                            {'AttributeName': 'created_at', 'KeyType': 'RANGE'}
                        ],
                        'Projection': {'ProjectionType': 'ALL'},
                        'ProvisionedThroughput': {
                            'ReadCapacityUnits': 5,
                            'WriteCapacityUnits': 5
                        }
                    }
                ],
                ProvisionedThroughput={
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5
                },
                SSESpecification={
                    'Enabled': True,
                    'SSEType': 'AES256'
                }
            )
            
            # Wait for table to be active
            waiter = self.dynamodb_client.get_waiter('table_exists')
            waiter.wait(TableName=catalog_table)
            
            self.created_resources.append(('dynamodb', catalog_table))
            print(f"  Created DynamoDB table: {catalog_table}")
        except Exception as e:
            print(f"  Error creating DynamoDB table {catalog_table}: {e}")
            raise
        
        # Tenant configuration table
        tenant_table = self.resources['dynamodb_tenant_table']
        try:
            self.dynamodb_client.create_table(
                TableName=tenant_table,
                KeySchema=[
                    {'AttributeName': 'tenant_id', 'KeyType': 'HASH'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'tenant_id', 'AttributeType': 'S'}
                ],
                ProvisionedThroughput={
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5
                },
                SSESpecification={
                    'Enabled': True,
                    'SSEType': 'AES256'
                }
            )
            
            # Wait for table to be active
            waiter = self.dynamodb_client.get_waiter('table_exists')
            waiter.wait(TableName=tenant_table)
            
            self.created_resources.append(('dynamodb', tenant_table))
            print(f"  Created DynamoDB table: {tenant_table}")
        except Exception as e:
            print(f"  Error creating DynamoDB table {tenant_table}: {e}")
            raise
    
    def _setup_sqs_queues(self):
        """Create SQS queues for async processing"""
        print("Creating SQS queues...")
        
        # Create DLQ first
        dlq_name = self.resources['sqs_dlq_name']
        try:
            dlq_response = self.sqs_client.create_queue(
                QueueName=dlq_name,
                Attributes={
                    'MessageRetentionPeriod': '1209600',  # 14 days
                    'VisibilityTimeout': '300'
                }
            )
            dlq_url = dlq_response['QueueUrl']
            
            # Get DLQ ARN
            dlq_attrs = self.sqs_client.get_queue_attributes(
                QueueUrl=dlq_url,
                AttributeNames=['QueueArn']
            )
            dlq_arn = dlq_attrs['Attributes']['QueueArn']
            
            self.created_resources.append(('sqs', dlq_name))
            print(f"  Created SQS DLQ: {dlq_name}")
        except Exception as e:
            print(f"  Error creating SQS DLQ {dlq_name}: {e}")
            raise
        
        # Create main queue with DLQ
        queue_name = self.resources['sqs_queue_name']
        try:
            queue_response = self.sqs_client.create_queue(
                QueueName=queue_name,
                Attributes={
                    'MessageRetentionPeriod': '345600',  # 4 days
                    'VisibilityTimeout': '300',
                    'RedrivePolicy': json.dumps({
                        'deadLetterTargetArn': dlq_arn,
                        'maxReceiveCount': '3'
                    })
                }
            )
            queue_url = queue_response['QueueUrl']
            self.resources['sqs_queue_url'] = queue_url
            
            self.created_resources.append(('sqs', queue_name))
            print(f"  Created SQS queue: {queue_name}")
        except Exception as e:
            print(f"  Error creating SQS queue {queue_name}: {e}")
            raise
    
    def _setup_sns_topic(self):
        """Create SNS topic for notifications"""
        print("Creating SNS topic...")
        
        topic_name = self.resources['sns_topic_name']
        try:
            response = self.sns_client.create_topic(Name=topic_name)
            topic_arn = response['TopicArn']
            self.resources['sns_topic_arn'] = topic_arn
            
            self.created_resources.append(('sns', topic_name))
            print(f"  Created SNS topic: {topic_name}")
        except Exception as e:
            print(f"  Error creating SNS topic {topic_name}: {e}")
            raise
    
    def _setup_mock_ondc_endpoint(self):
        """Set up mock ONDC API endpoint using API Gateway"""
        print("Setting up mock ONDC endpoint...")
        
        # For integration tests, we'll use a simple mock server
        # In a real scenario, this would be an API Gateway with mock integrations
        # For now, we'll just set a placeholder URL
        self.resources['mock_ondc_endpoint'] = f"http://localhost:8080/mock-ondc"
        print(f"  Mock ONDC endpoint: {self.resources['mock_ondc_endpoint']}")
        print("  Note: Start mock ONDC server separately for full integration tests")
    
    def seed_test_data(self):
        """Seed test data into DynamoDB tables"""
        print("Seeding test data...")
        
        # Seed tenant configuration
        tenant_table = self.resources['dynamodb_tenant_table']
        test_tenant = {
            'tenant_id': {'S': 'test-tenant-001'},
            'name': {'S': 'Test Artisan Cooperative'},
            'language_preferences': {'SS': ['hi', 'te', 'ta']},
            'ondc_seller_id': {'S': 'test-seller-001'},
            'ondc_api_key': {'S': 'test-api-key'},
            'quota_daily_uploads': {'N': '1000'},
            'created_at': {'S': datetime.now().isoformat()}
        }
        
        self.dynamodb_client.put_item(
            TableName=tenant_table,
            Item=test_tenant
        )
        print("  Seeded test tenant data")
    
    def teardown_all(self):
        """Clean up all created AWS resources"""
        print(f"Tearing down integration test environment...")
        
        # Delete in reverse order
        for resource_type, resource_name in reversed(self.created_resources):
            try:
                if resource_type == 's3':
                    # Empty bucket first
                    self._empty_s3_bucket(resource_name)
                    self.s3_client.delete_bucket(Bucket=resource_name)
                    print(f"  Deleted S3 bucket: {resource_name}")
                
                elif resource_type == 'dynamodb':
                    self.dynamodb_client.delete_table(TableName=resource_name)
                    print(f"  Deleted DynamoDB table: {resource_name}")
                
                elif resource_type == 'sqs':
                    queue_url = self.sqs_client.get_queue_url(QueueName=resource_name)['QueueUrl']
                    self.sqs_client.delete_queue(QueueUrl=queue_url)
                    print(f"  Deleted SQS queue: {resource_name}")
                
                elif resource_type == 'sns':
                    topic_arn = self.resources.get('sns_topic_arn')
                    if topic_arn:
                        self.sns_client.delete_topic(TopicArn=topic_arn)
                    print(f"  Deleted SNS topic: {resource_name}")
            
            except Exception as e:
                print(f"  Error deleting {resource_type} {resource_name}: {e}")
        
        print("Integration test environment teardown complete")
    
    def _empty_s3_bucket(self, bucket_name: str):
        """Empty all objects from S3 bucket"""
        try:
            # List and delete all objects
            paginator = self.s3_client.get_paginator('list_objects_v2')
            for page in paginator.paginate(Bucket=bucket_name):
                if 'Contents' in page:
                    objects = [{'Key': obj['Key']} for obj in page['Contents']]
                    self.s3_client.delete_objects(
                        Bucket=bucket_name,
                        Delete={'Objects': objects}
                    )
            
            # List and delete all versions
            paginator = self.s3_client.get_paginator('list_object_versions')
            for page in paginator.paginate(Bucket=bucket_name):
                if 'Versions' in page:
                    versions = [{'Key': v['Key'], 'VersionId': v['VersionId']} 
                               for v in page['Versions']]
                    self.s3_client.delete_objects(
                        Bucket=bucket_name,
                        Delete={'Objects': versions}
                    )
        except Exception as e:
            print(f"  Error emptying S3 bucket {bucket_name}: {e}")


# Pytest fixtures for integration tests
@pytest.fixture(scope="session")
def aws_test_environment():
    """
    Session-scoped fixture that sets up AWS test environment once for all tests
    """
    env = AWSIntegrationTestEnvironment()
    resources = env.setup_all()
    env.seed_test_data()
    
    yield resources
    
    # Teardown after all tests
    env.teardown_all()


@pytest.fixture(scope="function")
def clean_test_environment(aws_test_environment):
    """
    Function-scoped fixture that provides clean environment for each test
    """
    # Setup: environment is already created by session fixture
    yield aws_test_environment
    
    # Teardown: clean up test data after each test
    # (but keep the infrastructure)
    # This would involve clearing DynamoDB tables, S3 buckets, etc.


if __name__ == "__main__":
    # Allow running this script directly for manual setup/teardown
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "setup":
        env = AWSIntegrationTestEnvironment()
        resources = env.setup_all()
        env.seed_test_data()
        print("\nTest environment resources:")
        for key, value in resources.items():
            print(f"  {key}: {value}")
        print("\nRun 'python test_environment_setup.py teardown' to clean up")
    
    elif len(sys.argv) > 1 and sys.argv[1] == "teardown":
        env = AWSIntegrationTestEnvironment()
        # Load existing resources (would need to be saved from setup)
        env.teardown_all()
    
    else:
        print("Usage: python test_environment_setup.py [setup|teardown]")
