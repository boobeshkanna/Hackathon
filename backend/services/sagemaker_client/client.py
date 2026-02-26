"""
AWS Sagemaker Client for Vision and ASR inference
"""
import json
import logging
from typing import Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class SagemakerClient:
    """Client for AWS Sagemaker inference endpoints"""
    
    def __init__(self, endpoint_name: Optional[str] = None, region: str = 'ap-south-1'):
        """
        Initialize Sagemaker client
        
        Args:
            endpoint_name: Sagemaker endpoint name
            region: AWS region
        """
        self.endpoint_name = endpoint_name
        self.client = boto3.client('sagemaker-runtime', region_name=region)
        logger.info(f"Initialized Sagemaker client for endpoint: {endpoint_name}")
    
    def invoke_vision_model(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Invoke vision model for image analysis
        
        Args:
            image_bytes: Image data as bytes
            
        Returns:
            Dict containing vision analysis results
        """
        try:
            payload = {
                'image': image_bytes.hex(),
                'task': 'object_detection_and_classification'
            }
            
            response = self.client.invoke_endpoint(
                EndpointName=self.endpoint_name,
                ContentType='application/json',
                Body=json.dumps(payload)
            )
            
            result = json.loads(response['Body'].read().decode())
            logger.info("Vision model invoked successfully")
            return result
            
        except ClientError as e:
            logger.error(f"Error invoking vision model: {e}")
            raise

    
    def invoke_asr_model(self, audio_bytes: bytes, language_code: str = 'hi') -> Dict[str, Any]:
        """
        Invoke ASR (Automatic Speech Recognition) model
        
        Args:
            audio_bytes: Audio data as bytes
            language_code: Language code (hi, te, ta, etc.)
            
        Returns:
            Dict containing transcription results
        """
        try:
            payload = {
                'audio': audio_bytes.hex(),
                'language': language_code,
                'task': 'transcription'
            }
            
            response = self.client.invoke_endpoint(
                EndpointName=self.endpoint_name,
                ContentType='application/json',
                Body=json.dumps(payload)
            )
            
            result = json.loads(response['Body'].read().decode())
            logger.info(f"ASR model invoked successfully for language: {language_code}")
            return result
            
        except ClientError as e:
            logger.error(f"Error invoking ASR model: {e}")
            raise
    
    def health_check(self) -> bool:
        """
        Check if Sagemaker endpoint is healthy
        
        Returns:
            True if endpoint is healthy, False otherwise
        """
        try:
            sagemaker_client = boto3.client('sagemaker')
            response = sagemaker_client.describe_endpoint(
                EndpointName=self.endpoint_name
            )
            status = response['EndpointStatus']
            logger.info(f"Endpoint status: {status}")
            return status == 'InService'
            
        except ClientError as e:
            logger.error(f"Error checking endpoint health: {e}")
            return False
