"""
SQS Message Publisher with idempotency and error handling
Implements Requirements 3.4, 9.1
"""
import json
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError
from aws_lambda_powertools import Logger

from backend.lambda_functions.shared.config import config

logger = Logger()


class SQSPublisher:
    """
    Publishes messages to SQS queue with idempotency and error handling
    
    Features:
    - Idempotency key generation for deduplication
    - Message serialization with validation
    - Error handling and retry logic
    - Message grouping for FIFO queues
    """
    
    def __init__(self):
        self.sqs_client = boto3.client('sqs', region_name=config.AWS_REGION)
        self.queue_url = config.SQS_QUEUE_URL
    
    def publish_catalog_processing_message(
        self,
        tracking_id: str,
        tenant_id: str,
        artisan_id: str,
        photo_key: str,
        audio_key: str,
        language: str,
        priority: str = 'normal',
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Publish catalog processing message to SQS queue
        
        Args:
            tracking_id: Unique tracking identifier
            tenant_id: Tenant organization identifier
            artisan_id: Artisan identifier
            photo_key: S3 key for photo
            audio_key: S3 key for audio
            language: Language code (hi, te, ta, etc.)
            priority: Message priority (normal, high)
            metadata: Additional metadata
            
        Returns:
            Dict with message_id and status
        """
        try:
            # Generate idempotency key for deduplication
            idempotency_key = self._generate_idempotency_key(
                tracking_id, tenant_id, artisan_id
            )
            
            # Build message body
            message_body = {
                "trackingId": tracking_id,
                "tenantId": tenant_id,
                "artisanId": artisan_id,
                "photoKey": photo_key,
                "audioKey": audio_key,
                "language": language,
                "priority": priority,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": metadata or {}
            }
            
            # Validate message
            self._validate_message(message_body)
            
            # Serialize message
            message_json = json.dumps(message_body)
            
            # Determine if queue is FIFO
            is_fifo = self.queue_url.endswith('.fifo')
            
            # Prepare send message parameters
            send_params = {
                'QueueUrl': self.queue_url,
                'MessageBody': message_json,
                'MessageAttributes': {
                    'TrackingId': {
                        'StringValue': tracking_id,
                        'DataType': 'String'
                    },
                    'TenantId': {
                        'StringValue': tenant_id,
                        'DataType': 'String'
                    },
                    'Priority': {
                        'StringValue': priority,
                        'DataType': 'String'
                    },
                    'Language': {
                        'StringValue': language,
                        'DataType': 'String'
                    }
                }
            }
            
            # Add FIFO-specific parameters
            if is_fifo:
                send_params['MessageDeduplicationId'] = idempotency_key
                send_params['MessageGroupId'] = tenant_id  # Group by tenant for ordering
            
            # Send message to SQS
            response = self.sqs_client.send_message(**send_params)
            
            logger.info(
                "Message published to SQS",
                extra={
                    "tracking_id": tracking_id,
                    "message_id": response.get('MessageId'),
                    "idempotency_key": idempotency_key,
                    "queue_url": self.queue_url
                }
            )
            
            return {
                'message_id': response.get('MessageId'),
                'idempotency_key': idempotency_key,
                'status': 'published',
                'tracking_id': tracking_id
            }
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            logger.error(
                f"AWS error publishing message: {error_code}",
                extra={
                    "tracking_id": tracking_id,
                    "error": str(e)
                },
                exc_info=True
            )
            raise
        except Exception as e:
            logger.error(
                f"Error publishing message: {str(e)}",
                extra={"tracking_id": tracking_id},
                exc_info=True
            )
            raise
    
    def publish_status_update(
        self,
        tracking_id: str,
        stage: str,
        status: str,
        message: str,
        catalog_id: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Publish status update message for notifications
        
        Args:
            tracking_id: Tracking identifier
            stage: Processing stage (uploaded, processing, completed, failed)
            status: Status (success, error)
            message: Status message
            catalog_id: ONDC catalog ID (if completed)
            error_details: Error information (if failed)
            
        Returns:
            Dict with message_id and status
        """
        try:
            # Build message body
            message_body = {
                "trackingId": tracking_id,
                "stage": stage,
                "status": status,
                "message": message,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            if catalog_id:
                message_body['catalogId'] = catalog_id
            
            if error_details:
                message_body['errorDetails'] = error_details
            
            # Serialize message
            message_json = json.dumps(message_body)
            
            # Send to status update queue (or SNS topic)
            # For now, using the same queue with different message attributes
            response = self.sqs_client.send_message(
                QueueUrl=self.queue_url,
                MessageBody=message_json,
                MessageAttributes={
                    'MessageType': {
                        'StringValue': 'StatusUpdate',
                        'DataType': 'String'
                    },
                    'TrackingId': {
                        'StringValue': tracking_id,
                        'DataType': 'String'
                    },
                    'Stage': {
                        'StringValue': stage,
                        'DataType': 'String'
                    }
                }
            )
            
            logger.info(
                "Status update published",
                extra={
                    "tracking_id": tracking_id,
                    "stage": stage,
                    "message_id": response.get('MessageId')
                }
            )
            
            return {
                'message_id': response.get('MessageId'),
                'status': 'published'
            }
            
        except Exception as e:
            logger.error(
                f"Error publishing status update: {str(e)}",
                extra={"tracking_id": tracking_id},
                exc_info=True
            )
            raise
    
    def _generate_idempotency_key(
        self, 
        tracking_id: str, 
        tenant_id: str, 
        artisan_id: str
    ) -> str:
        """
        Generate deterministic idempotency key for message deduplication
        
        Args:
            tracking_id: Tracking identifier
            tenant_id: Tenant identifier
            artisan_id: Artisan identifier
            
        Returns:
            SHA-256 hash as idempotency key
        """
        key_input = f"{tracking_id}|{tenant_id}|{artisan_id}"
        return hashlib.sha256(key_input.encode()).hexdigest()[:32]
    
    def _validate_message(self, message: Dict[str, Any]) -> None:
        """
        Validate message structure and required fields
        
        Args:
            message: Message body to validate
            
        Raises:
            ValueError: If message is invalid
        """
        required_fields = ['trackingId', 'tenantId', 'artisanId', 'language']
        
        for field in required_fields:
            if field not in message or not message[field]:
                raise ValueError(f"Required field '{field}' is missing or empty")
        
        # Validate at least one media key is present
        if not message.get('photoKey') and not message.get('audioKey'):
            raise ValueError("At least one of 'photoKey' or 'audioKey' must be provided")
        
        # Validate language code
        supported_languages = config.get_supported_languages()
        if message['language'] not in supported_languages:
            raise ValueError(
                f"Unsupported language '{message['language']}'. "
                f"Supported: {', '.join(supported_languages)}"
            )
        
        # Validate priority
        valid_priorities = ['normal', 'high', 'low']
        if message.get('priority') and message['priority'] not in valid_priorities:
            raise ValueError(
                f"Invalid priority '{message['priority']}'. "
                f"Valid values: {', '.join(valid_priorities)}"
            )


# Singleton instance
sqs_publisher = SQSPublisher()
