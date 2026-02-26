"""
S3 Multipart Upload Manager with presigned URLs and resume capability
Implements Requirements 3.2, 3.3
"""
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import boto3
from botocore.exceptions import ClientError
from aws_lambda_powertools import Logger

from backend.lambda_functions.shared.config import config

logger = Logger()


class MultipartUploadManager:
    """
    Manages S3 multipart uploads with presigned URLs and resume capability
    
    Features:
    - Generate presigned URLs for multipart upload parts
    - Track upload state in DynamoDB
    - Support upload resume from last successful part
    - Handle upload completion and abort
    """
    
    def __init__(self):
        self.s3_client = boto3.client('s3', region_name=config.AWS_REGION)
        self.dynamodb = boto3.resource('dynamodb', region_name=config.AWS_REGION)
        self.raw_bucket = config.S3_RAW_MEDIA_BUCKET
        self.upload_state_table = self.dynamodb.Table(f"{config.DYNAMODB_CATALOG_TABLE}_UploadState")
    
    def initiate_multipart_upload(
        self, 
        tracking_id: str,
        tenant_id: str,
        artisan_id: str,
        content_type: str,
        file_size: int,
        part_size: int = 5 * 1024 * 1024  # 5MB default
    ) -> Dict[str, Any]:
        """
        Initiate S3 multipart upload and generate presigned URLs for parts
        
        Args:
            tracking_id: Unique tracking identifier
            tenant_id: Tenant organization identifier
            artisan_id: Artisan identifier
            content_type: MIME type
            file_size: Total file size in bytes
            part_size: Size of each part (default 5MB)
            
        Returns:
            Dict with upload_id, part_urls, and tracking info
        """
        try:
            # Determine file extension
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
            
            # Initiate multipart upload
            response = self.s3_client.create_multipart_upload(
                Bucket=self.raw_bucket,
                Key=s3_key,
                ContentType=content_type,
                Metadata={
                    'tracking_id': tracking_id,
                    'tenant_id': tenant_id,
                    'artisan_id': artisan_id
                }
            )
            
            upload_id = response['UploadId']
            
            # Calculate number of parts
            num_parts = (file_size + part_size - 1) // part_size
            
            # Generate presigned URLs for each part (valid for 1 hour)
            expires_in = 3600
            part_urls = []
            
            for part_number in range(1, num_parts + 1):
                presigned_url = self.s3_client.generate_presigned_url(
                    'upload_part',
                    Params={
                        'Bucket': self.raw_bucket,
                        'Key': s3_key,
                        'UploadId': upload_id,
                        'PartNumber': part_number
                    },
                    ExpiresIn=expires_in
                )
                
                part_urls.append({
                    'part_number': part_number,
                    'url': presigned_url
                })
            
            # Store upload state in DynamoDB
            now = datetime.utcnow()
            expires_at = now + timedelta(seconds=expires_in)
            
            upload_state = {
                'tracking_id': tracking_id,
                'upload_id': upload_id,
                's3_key': s3_key,
                's3_bucket': self.raw_bucket,
                'content_type': content_type,
                'file_size': file_size,
                'part_size': part_size,
                'num_parts': num_parts,
                'completed_parts': [],
                'status': 'initiated',
                'created_at': now.isoformat(),
                'expires_at': expires_at.isoformat()
            }
            
            self.upload_state_table.put_item(Item=upload_state)
            
            logger.info(
                "Multipart upload initiated",
                extra={
                    "tracking_id": tracking_id,
                    "upload_id": upload_id,
                    "num_parts": num_parts,
                    "s3_key": s3_key
                }
            )
            
            return {
                'tracking_id': tracking_id,
                'upload_id': upload_id,
                's3_key': s3_key,
                'part_urls': part_urls,
                'num_parts': num_parts,
                'expires_at': expires_at.isoformat()
            }
            
        except ClientError as e:
            logger.error(f"AWS error initiating multipart upload: {str(e)}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Error initiating multipart upload: {str(e)}", exc_info=True)
            raise
    
    def record_part_completion(
        self, 
        tracking_id: str, 
        part_number: int, 
        etag: str
    ) -> Dict[str, Any]:
        """
        Record completion of an upload part
        
        Args:
            tracking_id: Tracking identifier
            part_number: Part number that was uploaded
            etag: ETag returned by S3 for the part
            
        Returns:
            Dict with updated upload state
        """
        try:
            # Fetch upload state
            response = self.upload_state_table.get_item(Key={'tracking_id': tracking_id})
            
            if 'Item' not in response:
                raise ValueError(f"Upload state not found for tracking_id: {tracking_id}")
            
            upload_state = response['Item']
            
            # Add completed part
            completed_parts = upload_state.get('completed_parts', [])
            
            # Check if part already recorded
            if not any(p['part_number'] == part_number for p in completed_parts):
                completed_parts.append({
                    'part_number': part_number,
                    'etag': etag
                })
            
            # Update state
            self.upload_state_table.update_item(
                Key={'tracking_id': tracking_id},
                UpdateExpression="SET completed_parts = :parts, updated_at = :updated_at",
                ExpressionAttributeValues={
                    ':parts': completed_parts,
                    ':updated_at': datetime.utcnow().isoformat()
                }
            )
            
            logger.info(
                "Part completion recorded",
                extra={
                    "tracking_id": tracking_id,
                    "part_number": part_number,
                    "completed_parts": len(completed_parts),
                    "total_parts": upload_state['num_parts']
                }
            )
            
            return {
                'tracking_id': tracking_id,
                'completed_parts': len(completed_parts),
                'total_parts': upload_state['num_parts'],
                'is_complete': len(completed_parts) == upload_state['num_parts']
            }
            
        except ValueError as e:
            logger.error(f"Validation error: {str(e)}")
            raise
        except ClientError as e:
            logger.error(f"AWS error recording part: {str(e)}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Error recording part: {str(e)}", exc_info=True)
            raise
    
    def get_upload_state(self, tracking_id: str) -> Dict[str, Any]:
        """
        Get current upload state for resume capability
        
        Args:
            tracking_id: Tracking identifier
            
        Returns:
            Dict with upload state including completed parts
        """
        try:
            response = self.upload_state_table.get_item(Key={'tracking_id': tracking_id})
            
            if 'Item' not in response:
                raise ValueError(f"Upload state not found for tracking_id: {tracking_id}")
            
            upload_state = response['Item']
            
            # Determine which parts still need to be uploaded
            completed_part_numbers = [p['part_number'] for p in upload_state.get('completed_parts', [])]
            pending_parts = [
                i for i in range(1, upload_state['num_parts'] + 1) 
                if i not in completed_part_numbers
            ]
            
            return {
                'tracking_id': tracking_id,
                'upload_id': upload_state['upload_id'],
                's3_key': upload_state['s3_key'],
                'status': upload_state['status'],
                'completed_parts': completed_part_numbers,
                'pending_parts': pending_parts,
                'num_parts': upload_state['num_parts'],
                'file_size': upload_state['file_size'],
                'part_size': upload_state['part_size']
            }
            
        except ValueError as e:
            logger.error(f"Validation error: {str(e)}")
            raise
        except ClientError as e:
            logger.error(f"AWS error fetching upload state: {str(e)}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Error fetching upload state: {str(e)}", exc_info=True)
            raise
    
    def complete_multipart_upload(self, tracking_id: str) -> Dict[str, Any]:
        """
        Complete multipart upload after all parts are uploaded
        
        Args:
            tracking_id: Tracking identifier
            
        Returns:
            Dict with s3_key and completion status
        """
        try:
            # Fetch upload state
            response = self.upload_state_table.get_item(Key={'tracking_id': tracking_id})
            
            if 'Item' not in response:
                raise ValueError(f"Upload state not found for tracking_id: {tracking_id}")
            
            upload_state = response['Item']
            
            # Verify all parts are completed
            completed_parts = upload_state.get('completed_parts', [])
            if len(completed_parts) != upload_state['num_parts']:
                raise ValueError(
                    f"Not all parts uploaded: {len(completed_parts)}/{upload_state['num_parts']}"
                )
            
            # Sort parts by part number
            parts = sorted(completed_parts, key=lambda x: x['part_number'])
            
            # Complete multipart upload
            response = self.s3_client.complete_multipart_upload(
                Bucket=upload_state['s3_bucket'],
                Key=upload_state['s3_key'],
                UploadId=upload_state['upload_id'],
                MultipartUpload={
                    'Parts': [
                        {
                            'PartNumber': part['part_number'],
                            'ETag': part['etag']
                        }
                        for part in parts
                    ]
                }
            )
            
            # Update state to completed
            self.upload_state_table.update_item(
                Key={'tracking_id': tracking_id},
                UpdateExpression="SET #status = :status, completed_at = :completed_at",
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':status': 'completed',
                    ':completed_at': datetime.utcnow().isoformat()
                }
            )
            
            logger.info(
                "Multipart upload completed",
                extra={
                    "tracking_id": tracking_id,
                    "s3_key": upload_state['s3_key'],
                    "etag": response.get('ETag')
                }
            )
            
            return {
                'tracking_id': tracking_id,
                's3_key': upload_state['s3_key'],
                's3_bucket': upload_state['s3_bucket'],
                'status': 'completed',
                'etag': response.get('ETag')
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
    
    def abort_multipart_upload(self, tracking_id: str) -> Dict[str, Any]:
        """
        Abort multipart upload and clean up
        
        Args:
            tracking_id: Tracking identifier
            
        Returns:
            Dict with abort status
        """
        try:
            # Fetch upload state
            response = self.upload_state_table.get_item(Key={'tracking_id': tracking_id})
            
            if 'Item' not in response:
                raise ValueError(f"Upload state not found for tracking_id: {tracking_id}")
            
            upload_state = response['Item']
            
            # Abort multipart upload in S3
            self.s3_client.abort_multipart_upload(
                Bucket=upload_state['s3_bucket'],
                Key=upload_state['s3_key'],
                UploadId=upload_state['upload_id']
            )
            
            # Update state to aborted
            self.upload_state_table.update_item(
                Key={'tracking_id': tracking_id},
                UpdateExpression="SET #status = :status, aborted_at = :aborted_at",
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':status': 'aborted',
                    ':aborted_at': datetime.utcnow().isoformat()
                }
            )
            
            logger.info(
                "Multipart upload aborted",
                extra={
                    "tracking_id": tracking_id,
                    "upload_id": upload_state['upload_id']
                }
            )
            
            return {
                'tracking_id': tracking_id,
                'status': 'aborted'
            }
            
        except ValueError as e:
            logger.error(f"Validation error: {str(e)}")
            raise
        except ClientError as e:
            logger.error(f"AWS error aborting upload: {str(e)}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Error aborting upload: {str(e)}", exc_info=True)
            raise


# Singleton instance
multipart_upload_manager = MultipartUploadManager()
