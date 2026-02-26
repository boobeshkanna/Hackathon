"""
Upload handlers for resumable multipart uploads
Implements POST /v1/catalog/upload/initiate, POST /v1/catalog/upload/complete, GET /v1/catalog/status/{trackingId}
"""
import json
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError
from aws_lambda_powertools import Logger, Tracer

# Import models
import sys
sys.path.append('/opt/python')  # Lambda layer path

from backend.models.response import UploadResponse, UploadCompleteResponse, StatusUpdate, ErrorResponse
from backend.models.catalog import CatalogProcessingRecord, ProcessingStatus
from backend.lambda_functions.shared.config import config
from backend.services.s3_upload import multipart_upload_manager
from backend.services.queue import sqs_publisher

# Initialize AWS clients
logger = Logger()
tracer = Tracer()
s3_client = boto3.client('s3', region_name=config.AWS_REGION)
dynamodb = boto3.resource('dynamodb', region_name=config.AWS_REGION)
sqs_client = boto3.client('sqs', region_name=config.AWS_REGION)

# DynamoDB tables
catalog_table = dynamodb.Table(config.DYNAMODB_CATALOG_TABLE)


class UploadHandler:
    """Handler for resumable upload operations"""
    
    def __init__(self):
        self.s3_client = s3_client
        self.dynamodb = dynamodb
        self.sqs_client = sqs_client
        self.raw_bucket = config.S3_RAW_MEDIA_BUCKET
        self.queue_url = config.SQS_QUEUE_URL
    
    @tracer.capture_method
    def initiate_upload(self, tenant_id: str, artisan_id: str, content_type: str) -> Dict[str, Any]:
        """
        Initiate resumable upload by generating presigned URLs for S3 multipart upload
        
        Args:
            tenant_id: Tenant organization identifier
            artisan_id: Artisan identifier
            content_type: MIME type of the content (image/jpeg, audio/opus, etc.)
            
        Returns:
            Dict with tracking_id, upload_url, and expires_at
        """
        try:
            # Generate tracking ID
            tracking_id = f"trk_{uuid.uuid4().hex[:16]}"
            
            # Determine file extension from content type
            extension_map = {
                'image/jpeg': 'jpg',
                'image/png': 'png',
                'audio/opus': 'opus',
                'audio/mpeg': 'mp3',
                'audio/wav': 'wav'
            }
            extension = extension_map.get(content_type, 'bin')
            
            # Generate S3 key with tenant isolation
            s3_key = f"{tenant_id}/{artisan_id}/{tracking_id}.{extension}"
            
            # Generate presigned URL for multipart upload (valid for 1 hour)
            expires_in = 3600  # 1 hour
            presigned_url = self.s3_client.generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': self.raw_bucket,
                    'Key': s3_key,
                    'ContentType': content_type
                },
                ExpiresIn=expires_in
            )
            
            # Create initial processing record in DynamoDB
            now = datetime.utcnow()
            expires_at = now + timedelta(seconds=expires_in)
            
            record = CatalogProcessingRecord(
                tracking_id=tracking_id,
                tenant_id=tenant_id,
                artisan_id=artisan_id,
                photo_key=s3_key if 'image' in content_type else '',
                audio_key=s3_key if 'audio' in content_type else '',
                language='hi',  # Default, will be updated on completion
                created_at=now,
                updated_at=now
            )
            
            # Store in DynamoDB
            catalog_table.put_item(Item=json.loads(record.json()))
            
            logger.info(
                "Upload initiated",
                extra={
                    "tracking_id": tracking_id,
                    "tenant_id": tenant_id,
                    "artisan_id": artisan_id,
                    "s3_key": s3_key
                }
            )
            
            return {
                "tracking_id": tracking_id,
                "upload_url": presigned_url,
                "expires_at": expires_at.isoformat(),
                "s3_key": s3_key  # Internal use
            }
            
        except ClientError as e:
            logger.error(f"AWS error initiating upload: {str(e)}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Error initiating upload: {str(e)}", exc_info=True)
            raise
    
    @tracer.capture_method
    def initiate_multipart_upload(
        self, 
        tenant_id: str, 
        artisan_id: str, 
        content_type: str,
        file_size: int
    ) -> Dict[str, Any]:
        """
        Initiate multipart upload for large files with resume capability
        
        Args:
            tenant_id: Tenant organization identifier
            artisan_id: Artisan identifier
            content_type: MIME type of the content
            file_size: Total file size in bytes
            
        Returns:
            Dict with tracking_id, part_urls, and upload metadata
        """
        try:
            # Generate tracking ID
            tracking_id = f"trk_{uuid.uuid4().hex[:16]}"
            
            # Initiate multipart upload using the manager
            result = multipart_upload_manager.initiate_multipart_upload(
                tracking_id=tracking_id,
                tenant_id=tenant_id,
                artisan_id=artisan_id,
                content_type=content_type,
                file_size=file_size
            )
            
            # Create initial processing record in DynamoDB
            now = datetime.utcnow()
            
            record = CatalogProcessingRecord(
                tracking_id=tracking_id,
                tenant_id=tenant_id,
                artisan_id=artisan_id,
                photo_key=result['s3_key'] if 'image' in content_type else '',
                audio_key=result['s3_key'] if 'audio' in content_type else '',
                language='hi',  # Default, will be updated on completion
                created_at=now,
                updated_at=now
            )
            
            # Store in DynamoDB
            catalog_table.put_item(Item=json.loads(record.json()))
            
            logger.info(
                "Multipart upload initiated",
                extra={
                    "tracking_id": tracking_id,
                    "tenant_id": tenant_id,
                    "artisan_id": artisan_id,
                    "num_parts": result['num_parts']
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error initiating multipart upload: {str(e)}", exc_info=True)
            raise
    
    @tracer.capture_method
    def get_upload_resume_info(self, tracking_id: str) -> Dict[str, Any]:
        """
        Get upload state for resuming interrupted uploads
        
        Args:
            tracking_id: Tracking identifier
            
        Returns:
            Dict with upload state including completed and pending parts
        """
        try:
            return multipart_upload_manager.get_upload_state(tracking_id)
        except Exception as e:
            logger.error(f"Error getting upload resume info: {str(e)}", exc_info=True)
            raise
    
    @tracer.capture_method
    def complete_upload(self, tracking_id: str, photo_key: Optional[str] = None, 
                       audio_key: Optional[str] = None, language: str = 'hi') -> Dict[str, Any]:
        """
        Complete upload and publish message to SQS for processing
        
        Args:
            tracking_id: Tracking identifier
            photo_key: S3 key for photo (optional)
            audio_key: S3 key for audio (optional)
            language: Language code for processing
            
        Returns:
            Dict with status and tracking_id
        """
        try:
            # Validate at least one media key is provided
            if not photo_key and not audio_key:
                raise ValueError("At least one of photo_key or audio_key must be provided")
            
            # Fetch record from DynamoDB
            response = catalog_table.get_item(Key={'tracking_id': tracking_id})
            
            if 'Item' not in response:
                raise ValueError(f"Tracking ID {tracking_id} not found")
            
            record_data = response['Item']
            
            # Update record with media keys and language
            update_expression = "SET updated_at = :updated_at, #lang = :language"
            expression_values = {
                ':updated_at': datetime.utcnow().isoformat(),
                ':language': language
            }
            expression_names = {'#lang': 'language'}
            
            if photo_key:
                update_expression += ", photo_key = :photo_key"
                expression_values[':photo_key'] = photo_key
            
            if audio_key:
                update_expression += ", audio_key = :audio_key"
                expression_values[':audio_key'] = audio_key
            
            catalog_table.update_item(
                Key={'tracking_id': tracking_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values,
                ExpressionAttributeNames=expression_names
            )
            
            # Publish message to SQS queue using the publisher
            publish_result = sqs_publisher.publish_catalog_processing_message(
                tracking_id=tracking_id,
                tenant_id=record_data.get('tenant_id', ''),
                artisan_id=record_data.get('artisan_id', ''),
                photo_key=photo_key or record_data.get('photo_key', ''),
                audio_key=audio_key or record_data.get('audio_key', ''),
                language=language,
                priority='normal'
            )
            
            logger.info(
                "Upload completed and queued",
                extra={
                    "tracking_id": tracking_id,
                    "message_id": publish_result.get('message_id'),
                    "idempotency_key": publish_result.get('idempotency_key')
                }
            )
            
            return {
                "status": "accepted",
                "tracking_id": tracking_id,
                "message": "Upload accepted and queued for processing"
            }
            
        except ValueError as e:
            logger.error(f"Validation error: {str(e)}")
            raise
        except ClientError as e:
            logger.error(f"AWS error completing upload: {str(e)}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Error completing upload: {str(e)}", exc_info=True)
            raise
    
    @tracer.capture_method
    def get_status(self, tracking_id: str) -> Dict[str, Any]:
        """
        Get processing status for a tracking ID
        
        Args:
            tracking_id: Tracking identifier
            
        Returns:
            Dict with stage, message, catalog_id (if completed), and error_details (if failed)
        """
        try:
            # Fetch record from DynamoDB
            response = catalog_table.get_item(Key={'tracking_id': tracking_id})
            
            if 'Item' not in response:
                raise ValueError(f"Tracking ID {tracking_id} not found")
            
            record = response['Item']
            
            # Determine current stage based on processing status
            stage = self._determine_stage(record)
            message = self._generate_status_message(stage, record)
            
            result = {
                "tracking_id": tracking_id,
                "stage": stage,
                "message": message,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Add catalog ID if completed
            if record.get('ondc_catalog_id'):
                result['catalog_id'] = record['ondc_catalog_id']
            
            # Add error details if failed
            if record.get('error_details'):
                result['error_details'] = record['error_details']
            
            logger.info(
                "Status retrieved",
                extra={
                    "tracking_id": tracking_id,
                    "stage": stage
                }
            )
            
            return result
            
        except ValueError as e:
            logger.error(f"Validation error: {str(e)}")
            raise
        except ClientError as e:
            logger.error(f"AWS error fetching status: {str(e)}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Error fetching status: {str(e)}", exc_info=True)
            raise
    
    def _determine_stage(self, record: Dict[str, Any]) -> str:
        """Determine current processing stage from record"""
        # Check submission status first (final stage)
        submission_status = record.get('submission_status', 'pending')
        if submission_status == 'completed':
            return 'completed'
        elif submission_status == 'failed':
            return 'failed'
        
        # Check other stages
        mapping_status = record.get('mapping_status', 'pending')
        extraction_status = record.get('extraction_status', 'pending')
        vision_status = record.get('vision_status', 'pending')
        asr_status = record.get('asr_status', 'pending')
        
        if mapping_status in ['in_progress', 'completed']:
            return 'mapping'
        elif extraction_status in ['in_progress', 'completed']:
            return 'extraction'
        elif vision_status in ['in_progress', 'completed'] or asr_status in ['in_progress', 'completed']:
            return 'processing'
        else:
            return 'uploaded'
    
    def _generate_status_message(self, stage: str, record: Dict[str, Any]) -> str:
        """Generate human-readable status message"""
        messages = {
            'uploaded': 'Media uploaded successfully, queued for processing',
            'processing': 'Processing media with AI models',
            'extraction': 'Extracting product attributes',
            'mapping': 'Mapping to ONDC catalog format',
            'completed': 'Catalog entry successfully published to ONDC',
            'failed': 'Processing failed'
        }
        
        message = messages.get(stage, 'Processing in progress')
        
        # Add error details if failed
        if stage == 'failed' and record.get('error_details'):
            error_msg = record['error_details'].get('message', 'Unknown error')
            message = f"{message}: {error_msg}"
        
        return message


# Singleton instance
upload_handler = UploadHandler()
