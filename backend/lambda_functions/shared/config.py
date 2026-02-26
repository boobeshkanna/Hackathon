"""
Configuration management for Lambda functions
"""
import os
from typing import Optional


class Config:
    """Application configuration from environment variables"""
    
    # AWS Configuration
    AWS_REGION: str = os.getenv('AWS_REGION', 'ap-south-1')
    AWS_ACCOUNT_ID: str = os.getenv('AWS_ACCOUNT_ID', '')
    
    # S3 Buckets
    S3_RAW_MEDIA_BUCKET: str = os.getenv('S3_RAW_MEDIA_BUCKET', '')
    S3_ENHANCED_BUCKET: str = os.getenv('S3_ENHANCED_BUCKET', '')
    
    # DynamoDB Tables
    DYNAMODB_CATALOG_TABLE: str = os.getenv('DYNAMODB_CATALOG_TABLE', 'CatalogProcessingRecords')
    DYNAMODB_TENANT_TABLE: str = os.getenv('DYNAMODB_TENANT_TABLE', 'TenantConfigurations')
    
    # SQS Queue
    SQS_QUEUE_URL: str = os.getenv('SQS_QUEUE_URL', '')
    
    # Sagemaker
    SAGEMAKER_ENDPOINT_NAME: str = os.getenv('SAGEMAKER_ENDPOINT_NAME', '')
    
    # Bedrock
    BEDROCK_MODEL_ID: str = os.getenv('BEDROCK_MODEL_ID', 'anthropic.claude-v2')
    
    # ONDC Configuration
    ONDC_API_URL: str = os.getenv('ONDC_API_URL', 'https://staging.ondc.org/api')
    ONDC_SELLER_ID: str = os.getenv('ONDC_SELLER_ID', '')
    ONDC_API_KEY: str = os.getenv('ONDC_API_KEY', '')
    
    # Application Settings
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv('MAX_UPLOAD_SIZE_MB', '10'))
    SUPPORTED_LANGUAGES: str = os.getenv('SUPPORTED_LANGUAGES', 'hi,te,ta,bn,mr,gu,kn,ml,pa,or')
    
    @classmethod
    def get_supported_languages(cls) -> list[str]:
        """Get list of supported languages"""
        return cls.SUPPORTED_LANGUAGES.split(',')
    
    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration"""
        required = [
            cls.S3_RAW_MEDIA_BUCKET,
            cls.S3_ENHANCED_BUCKET,
            cls.SQS_QUEUE_URL,
        ]
        return all(required)


config = Config()
