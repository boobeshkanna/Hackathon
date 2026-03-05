"""
Lambda Workflow Orchestrator

Main orchestrator for the AI processing pipeline that coordinates:
- SQS event handling
- Media fetching from S3
- Sagemaker Vision + ASR processing
- Bedrock transcreation and attribute extraction
- Image enhancement
- ONDC schema mapping and submission
- Status notifications
- Error handling with graceful degradation
- Batch processing optimization

Requirements: 4.1, 6.1, 7.1, 7.2, 8.1, 9.1, 9.5, 10.1, 10.2, 10.3, 10.4,
              13.3, 14.1, 14.2, 14.3, 14.4, 14.5, 19.3
"""
from backend.lambda_functions.orchestrator.handler import lambda_handler
from backend.lambda_functions.orchestrator.batch_processor import BatchProcessor, create_batch_processor
from backend.lambda_functions.orchestrator.error_handler import ErrorHandler, get_error_handler

__all__ = [
    'lambda_handler',
    'BatchProcessor',
    'create_batch_processor',
    'ErrorHandler',
    'get_error_handler'
]
