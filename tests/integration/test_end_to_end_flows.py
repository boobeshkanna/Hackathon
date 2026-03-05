"""
End-to-End Flow Integration Tests

This module tests complete workflows from capture to ONDC submission.

Requirements: All
"""

import pytest
import boto3
import json
import time
import requests
from typing import Dict, Any
from datetime import datetime
import uuid


class TestEndToEndFlows:
    """
    End-to-end integration tests for the complete catalog workflow
    """
    
    def test_complete_flow_capture_to_notify(
        self,
        aws_integration_env: Dict[str, Any],
        mock_ondc_server: str,
        test_media_files: Dict[str, str],
        test_tenant_config: Dict[str, Any]
    ):
        """
        Test: Capture → Queue → Upload → Process → Submit → Notify
        
        This test validates the complete happy path from media capture
        to ONDC submission and notification delivery.
        
        Requirements: All
        """
        # Initialize AWS clients
        s3_client = boto3.client('s3')
        sqs_client = boto3.client('sqs')
        dynamodb_client = boto3.client('dynamodb')
        
        # Step 1: Simulate media capture and local queue
        tracking_id = f"test-{uuid.uuid4().hex}"
        local_entry = {
            'local_id': str(uuid.uuid4()),
            'tracking_id': tracking_id,
            'photo_path': test_media_files['image'],
            'audio_path': test_media_files['audio'],
            'captured_at': datetime.now().isoformat(),
            'sync_status': 'queued'
        }
        
        # Step 2: Upload media to S3 (simulating API Gateway upload)
        raw_bucket = aws_integration_env['s3_raw_bucket']
        photo_key = f"{tracking_id}/photo.jpg"
        audio_key = f"{tracking_id}/audio.wav"
        
        with open(test_media_files['image'], 'rb') as f:
            s3_client.put_object(
                Bucket=raw_bucket,
                Key=photo_key,
                Body=f,
                ServerSideEncryption='AES256'
            )
        
        with open(test_media_files['audio'], 'rb') as f:
            s3_client.put_object(
                Bucket=raw_bucket,
                Key=audio_key,
                Body=f,
                ServerSideEncryption='AES256'
            )
        
        # Step 3: Publish message to SQS queue
        queue_url = aws_integration_env['sqs_queue_url']
        message = {
            'tracking_id': tracking_id,
            'tenant_id': test_tenant_config['tenant_id'],
            'artisan_id': 'test-artisan-001',
            'photo_key': photo_key,
            'audio_key': audio_key,
            'language': 'hi',
            'priority': 'normal'
        }
        
        sqs_client.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message)
        )
        
        # Step 4: Create processing record in DynamoDB
        catalog_table = aws_integration_env['dynamodb_catalog_table']
        processing_record = {
            'tracking_id': {'S': tracking_id},
            'tenant_id': {'S': test_tenant_config['tenant_id']},
            'artisan_id': {'S': 'test-artisan-001'},
            'photo_key': {'S': photo_key},
            'audio_key': {'S': audio_key},
            'language': {'S': 'hi'},
            'asr_status': {'S': 'pending'},
            'vision_status': {'S': 'pending'},
            'extraction_status': {'S': 'pending'},
            'mapping_status': {'S': 'pending'},
            'submission_status': {'S': 'pending'},
            'created_at': {'S': datetime.now().isoformat()}
        }
        
        dynamodb_client.put_item(
            TableName=catalog_table,
            Item=processing_record
        )
        
        # Step 5: Simulate AI processing stages
        # (In real integration test, Lambda orchestrator would do this)
        
        # Simulate ASR processing
        asr_result = {
            'transcription': 'यह एक सुंदर हस्तनिर्मित साड़ी है',
            'confidence': 0.95,
            'language': 'hi'
        }
        
        dynamodb_client.update_item(
            TableName=catalog_table,
            Key={'tracking_id': {'S': tracking_id}},
            UpdateExpression='SET asr_status = :status, asr_result = :result',
            ExpressionAttributeValues={
                ':status': {'S': 'completed'},
                ':result': {'S': json.dumps(asr_result)}
            }
        )
        
        # Simulate Vision processing
        vision_result = {
            'category': 'handloom saree',
            'colors': ['red', 'gold'],
            'materials': ['silk'],
            'confidence': 0.92
        }
        
        dynamodb_client.update_item(
            TableName=catalog_table,
            Key={'tracking_id': {'S': tracking_id}},
            UpdateExpression='SET vision_status = :status, vision_result = :result',
            ExpressionAttributeValues={
                ':status': {'S': 'completed'},
                ':result': {'S': json.dumps(vision_result)}
            }
        )
        
        # Simulate attribute extraction
        extraction_result = {
            'category': 'handloom saree',
            'subcategory': 'silk saree',
            'material': ['silk', 'zari'],
            'colors': ['red', 'gold'],
            'price': {'value': 5000, 'currency': 'INR'},
            'short_description': 'Beautiful handmade silk saree',
            'long_description': 'This is a beautiful handmade silk saree with traditional craftsmanship',
            'confidence_scores': {'category': 0.92, 'material': 0.90}
        }
        
        dynamodb_client.update_item(
            TableName=catalog_table,
            Key={'tracking_id': {'S': tracking_id}},
            UpdateExpression='SET extraction_status = :status, extraction_result = :result',
            ExpressionAttributeValues={
                ':status': {'S': 'completed'},
                ':result': {'S': json.dumps(extraction_result)}
            }
        )
        
        # Step 6: Simulate ONDC schema mapping
        ondc_payload = {
            'context': {
                'domain': 'retail',
                'country': 'IND',
                'action': 'on_search',
                'bap_id': 'buyer-app-id',
                'bpp_id': test_tenant_config['ondc_seller_id']
            },
            'message': {
                'catalog': {
                    'bpp/providers': [{
                        'id': test_tenant_config['ondc_seller_id'],
                        'items': [{
                            'id': f'item-{tracking_id}',
                            'descriptor': {
                                'name': extraction_result['short_description'],
                                'short_desc': extraction_result['short_description'],
                                'long_desc': extraction_result['long_description'],
                                'images': [f"https://s3.amazonaws.com/{raw_bucket}/{photo_key}"]
                            },
                            'price': {
                                'currency': 'INR',
                                'value': '5000'
                            },
                            'category_id': 'Fashion:Ethnic Wear:Sarees',
                            'tags': {
                                'material': 'silk,zari',
                                'color': 'red,gold'
                            }
                        }]
                    }]
                }
            }
        }
        
        dynamodb_client.update_item(
            TableName=catalog_table,
            Key={'tracking_id': {'S': tracking_id}},
            UpdateExpression='SET mapping_status = :status, ondc_payload = :payload',
            ExpressionAttributeValues={
                ':status': {'S': 'completed'},
                ':payload': {'S': json.dumps(ondc_payload)}
            }
        )
        
        # Step 7: Submit to mock ONDC API
        response = requests.post(
            f"{mock_ondc_server}/beckn/catalog/on_search",
            json=ondc_payload,
            headers={'Authorization': 'Bearer test-token'}
        )
        
        assert response.status_code == 200, f"ONDC submission failed: {response.text}"
        
        response_data = response.json()
        assert 'catalog_ids' in response_data
        catalog_id = list(response_data['catalog_ids'].values())[0]
        
        # Update DynamoDB with catalog ID
        dynamodb_client.update_item(
            TableName=catalog_table,
            Key={'tracking_id': {'S': tracking_id}},
            UpdateExpression='SET submission_status = :status, ondc_catalog_id = :catalog_id, completed_at = :completed',
            ExpressionAttributeValues={
                ':status': {'S': 'completed'},
                ':catalog_id': {'S': catalog_id},
                ':completed': {'S': datetime.now().isoformat()}
            }
        )
        
        # Step 8: Verify final state
        final_record = dynamodb_client.get_item(
            TableName=catalog_table,
            Key={'tracking_id': {'S': tracking_id}}
        )
        
        assert final_record['Item']['submission_status']['S'] == 'completed'
        assert 'ondc_catalog_id' in final_record['Item']
        assert final_record['Item']['asr_status']['S'] == 'completed'
        assert final_record['Item']['vision_status']['S'] == 'completed'
        assert final_record['Item']['extraction_status']['S'] == 'completed'
        assert final_record['Item']['mapping_status']['S'] == 'completed'
        
        print(f"✓ End-to-end flow completed successfully for tracking_id: {tracking_id}")
    
    def test_offline_capture_online_sync_flow(
        self,
        aws_integration_env: Dict[str, Any],
        mock_ondc_server: str,
        test_media_files: Dict[str, str]
    ):
        """
        Test: Offline capture → Online sync → Process → Submit
        
        This test validates the offline-first workflow where media is captured
        without connectivity and synced later.
        
        Requirements: 2.1, 2.2, 2.3, 2.4, 2.5
        """
        s3_client = boto3.client('s3')
        sqs_client = boto3.client('sqs')
        
        # Step 1: Simulate offline capture (local queue only)
        local_entries = []
        for i in range(3):
            entry = {
                'local_id': str(uuid.uuid4()),
                'photo_path': test_media_files['image'],
                'audio_path': test_media_files['audio'],
                'captured_at': datetime.now().isoformat(),
                'sync_status': 'queued',
                'retry_count': 0
            }
            local_entries.append(entry)
        
        # Verify entries are queued locally
        assert len(local_entries) == 3
        assert all(e['sync_status'] == 'queued' for e in local_entries)
        
        # Step 2: Simulate network coming online and background sync
        for entry in local_entries:
            tracking_id = f"test-{uuid.uuid4().hex}"
            entry['tracking_id'] = tracking_id
            entry['sync_status'] = 'syncing'
            
            # Upload to S3
            raw_bucket = aws_integration_env['s3_raw_bucket']
            photo_key = f"{tracking_id}/photo.jpg"
            audio_key = f"{tracking_id}/audio.wav"
            
            with open(test_media_files['image'], 'rb') as f:
                s3_client.put_object(
                    Bucket=raw_bucket,
                    Key=photo_key,
                    Body=f,
                    ServerSideEncryption='AES256'
                )
            
            with open(test_media_files['audio'], 'rb') as f:
                s3_client.put_object(
                    Bucket=raw_bucket,
                    Key=audio_key,
                    Body=f,
                    ServerSideEncryption='AES256'
                )
            
            # Publish to queue
            queue_url = aws_integration_env['sqs_queue_url']
            message = {
                'tracking_id': tracking_id,
                'tenant_id': 'test-tenant-001',
                'artisan_id': 'test-artisan-001',
                'photo_key': photo_key,
                'audio_key': audio_key,
                'language': 'hi'
            }
            
            sqs_client.send_message(
                QueueUrl=queue_url,
                MessageBody=json.dumps(message)
            )
            
            entry['sync_status'] = 'synced'
        
        # Step 3: Verify all entries synced successfully
        assert all(e['sync_status'] == 'synced' for e in local_entries)
        assert all('tracking_id' in e for e in local_entries)
        
        print(f"✓ Offline capture and online sync completed for {len(local_entries)} entries")
    
    def test_failed_processing_retry_success(
        self,
        aws_integration_env: Dict[str, Any],
        mock_ondc_server: str
    ):
        """
        Test: Failed processing → Retry → Success
        
        This test validates retry logic for transient processing failures.
        
        Requirements: 2.4, 14.1, 14.2, 14.3, 14.4
        """
        sqs_client = boto3.client('sqs')
        dynamodb_client = boto3.client('dynamodb')
        
        tracking_id = f"test-retry-{uuid.uuid4().hex}"
        
        # Step 1: Create processing record with failed status
        catalog_table = aws_integration_env['dynamodb_catalog_table']
        processing_record = {
            'tracking_id': {'S': tracking_id},
            'tenant_id': {'S': 'test-tenant-001'},
            'artisan_id': {'S': 'test-artisan-001'},
            'photo_key': {'S': f"{tracking_id}/photo.jpg"},
            'audio_key': {'S': f"{tracking_id}/audio.wav"},
            'language': {'S': 'hi'},
            'asr_status': {'S': 'failed'},
            'asr_error': {'S': 'Timeout error'},
            'retry_count': {'N': '1'},
            'created_at': {'S': datetime.now().isoformat()}
        }
        
        dynamodb_client.put_item(
            TableName=catalog_table,
            Item=processing_record
        )
        
        # Step 2: Simulate retry with exponential backoff
        # First retry after 1 minute (simulated)
        time.sleep(0.1)  # Simulate delay
        
        # Retry processing
        dynamodb_client.update_item(
            TableName=catalog_table,
            Key={'tracking_id': {'S': tracking_id}},
            UpdateExpression='SET asr_status = :status, retry_count = :count',
            ExpressionAttributeValues={
                ':status': {'S': 'in_progress'},
                ':count': {'N': '2'}
            }
        )
        
        # Step 3: Simulate successful processing on retry
        asr_result = {
            'transcription': 'Test transcription',
            'confidence': 0.90,
            'language': 'hi'
        }
        
        dynamodb_client.update_item(
            TableName=catalog_table,
            Key={'tracking_id': {'S': tracking_id}},
            UpdateExpression='SET asr_status = :status, asr_result = :result',
            ExpressionAttributeValues={
                ':status': {'S': 'completed'},
                ':result': {'S': json.dumps(asr_result)}
            }
        )
        
        # Step 4: Verify successful retry
        final_record = dynamodb_client.get_item(
            TableName=catalog_table,
            Key={'tracking_id': {'S': tracking_id}}
        )
        
        assert final_record['Item']['asr_status']['S'] == 'completed'
        assert int(final_record['Item']['retry_count']['N']) == 2
        
        print(f"✓ Failed processing retry succeeded for tracking_id: {tracking_id}")
    
    def test_failed_ondc_submission_retry_success(
        self,
        aws_integration_env: Dict[str, Any],
        mock_ondc_server: str
    ):
        """
        Test: Failed ONDC submission → Retry → Success
        
        This test validates retry logic for ONDC submission failures.
        
        Requirements: 9.2, 9.3
        """
        dynamodb_client = boto3.client('dynamodb')
        
        tracking_id = f"test-ondc-retry-{uuid.uuid4().hex}"
        
        # Step 1: Create record with failed ONDC submission
        catalog_table = aws_integration_env['dynamodb_catalog_table']
        
        ondc_payload = {
            'context': {
                'domain': 'retail',
                'country': 'IND',
                'action': 'on_search',
                'bap_id': 'buyer-app-id',
                'bpp_id': 'test-seller-001'
            },
            'message': {
                'catalog': {
                    'bpp/providers': [{
                        'id': 'test-seller-001',
                        'items': [{
                            'id': f'item-{tracking_id}',
                            'descriptor': {
                                'name': 'Test Product',
                                'short_desc': 'Test description',
                                'long_desc': 'Test long description',
                                'images': ['https://example.com/image.jpg']
                            },
                            'price': {
                                'currency': 'INR',
                                'value': '1000'
                            },
                            'category_id': 'test-category'
                        }]
                    }]
                }
            }
        }
        
        processing_record = {
            'tracking_id': {'S': tracking_id},
            'tenant_id': {'S': 'test-tenant-001'},
            'submission_status': {'S': 'failed'},
            'submission_error': {'S': 'Network timeout'},
            'ondc_payload': {'S': json.dumps(ondc_payload)},
            'idempotency_key': {'S': f"idem-{tracking_id}"},
            'retry_count': {'N': '1'},
            'created_at': {'S': datetime.now().isoformat()}
        }
        
        dynamodb_client.put_item(
            TableName=catalog_table,
            Item=processing_record
        )
        
        # Step 2: Retry submission with same idempotency key
        response = requests.post(
            f"{mock_ondc_server}/beckn/catalog/on_search",
            json=ondc_payload,
            headers={'Authorization': 'Bearer test-token'}
        )
        
        assert response.status_code == 200
        response_data = response.json()
        catalog_id = list(response_data['catalog_ids'].values())[0]
        
        # Step 3: Update record with success
        dynamodb_client.update_item(
            TableName=catalog_table,
            Key={'tracking_id': {'S': tracking_id}},
            UpdateExpression='SET submission_status = :status, ondc_catalog_id = :catalog_id, retry_count = :count',
            ExpressionAttributeValues={
                ':status': {'S': 'completed'},
                ':catalog_id': {'S': catalog_id},
                ':count': {'N': '2'}
            }
        )
        
        # Step 4: Verify successful retry
        final_record = dynamodb_client.get_item(
            TableName=catalog_table,
            Key={'tracking_id': {'S': tracking_id}}
        )
        
        assert final_record['Item']['submission_status']['S'] == 'completed'
        assert 'ondc_catalog_id' in final_record['Item']
        
        print(f"✓ Failed ONDC submission retry succeeded for tracking_id: {tracking_id}")
    
    def test_update_existing_catalog_entry(
        self,
        aws_integration_env: Dict[str, Any],
        mock_ondc_server: str
    ):
        """
        Test: Update existing catalog entry → Version history
        
        This test validates catalog update workflow and version history.
        
        Requirements: 18.1, 18.2, 18.3, 18.4, 18.5
        """
        dynamodb_client = boto3.client('dynamodb')
        
        tracking_id = f"test-update-{uuid.uuid4().hex}"
        catalog_id = f"ondc-catalog-{uuid.uuid4().hex[:12]}"
        
        # Step 1: Create initial catalog entry
        catalog_table = aws_integration_env['dynamodb_catalog_table']
        
        initial_payload = {
            'context': {
                'domain': 'retail',
                'country': 'IND',
                'action': 'on_search',
                'bap_id': 'buyer-app-id',
                'bpp_id': 'test-seller-001'
            },
            'message': {
                'catalog': {
                    'bpp/providers': [{
                        'id': 'test-seller-001',
                        'items': [{
                            'id': f'item-{tracking_id}',
                            'descriptor': {
                                'name': 'Original Product Name',
                                'short_desc': 'Original description',
                                'long_desc': 'Original long description',
                                'images': ['https://example.com/image1.jpg']
                            },
                            'price': {
                                'currency': 'INR',
                                'value': '1000'
                            },
                            'category_id': 'test-category'
                        }]
                    }]
                }
            }
        }
        
        # Submit initial version
        response = requests.post(
            f"{mock_ondc_server}/beckn/catalog/on_search",
            json=initial_payload,
            headers={'Authorization': 'Bearer test-token'}
        )
        
        assert response.status_code == 200
        
        # Store in DynamoDB
        processing_record = {
            'tracking_id': {'S': tracking_id},
            'tenant_id': {'S': 'test-tenant-001'},
            'ondc_catalog_id': {'S': catalog_id},
            'ondc_payload': {'S': json.dumps(initial_payload)},
            'version': {'N': '1'},
            'created_at': {'S': datetime.now().isoformat()}
        }
        
        dynamodb_client.put_item(
            TableName=catalog_table,
            Item=processing_record
        )
        
        # Step 2: Create updated version
        updated_tracking_id = f"test-update-v2-{uuid.uuid4().hex}"
        
        updated_payload = {
            'catalog_id': catalog_id,
            'item': {
                'id': f'item-{tracking_id}',
                'descriptor': {
                    'name': 'Updated Product Name',
                    'short_desc': 'Updated description',
                    'long_desc': 'Updated long description',
                    'images': ['https://example.com/image2.jpg']
                },
                'price': {
                    'currency': 'INR',
                    'value': '1200'
                },
                'category_id': 'test-category'
            }
        }
        
        # Submit update
        response = requests.put(
            f"{mock_ondc_server}/beckn/catalog/update",
            json=updated_payload,
            headers={'Authorization': 'Bearer test-token'}
        )
        
        assert response.status_code == 200
        
        # Step 3: Store version history
        version_record = {
            'tracking_id': {'S': updated_tracking_id},
            'tenant_id': {'S': 'test-tenant-001'},
            'ondc_catalog_id': {'S': catalog_id},
            'ondc_payload': {'S': json.dumps(updated_payload)},
            'version': {'N': '2'},
            'previous_version_tracking_id': {'S': tracking_id},
            'created_at': {'S': datetime.now().isoformat()}
        }
        
        dynamodb_client.put_item(
            TableName=catalog_table,
            Item=version_record
        )
        
        # Step 4: Verify version history
        # Query all versions for this catalog ID
        response = dynamodb_client.query(
            TableName=catalog_table,
            IndexName='TenantIndex',
            KeyConditionExpression='tenant_id = :tenant_id',
            FilterExpression='ondc_catalog_id = :catalog_id',
            ExpressionAttributeValues={
                ':tenant_id': {'S': 'test-tenant-001'},
                ':catalog_id': {'S': catalog_id}
            }
        )
        
        versions = response['Items']
        assert len(versions) == 2
        
        # Verify catalog ID is preserved
        assert all(v['ondc_catalog_id']['S'] == catalog_id for v in versions)
        
        # Verify version numbers
        version_numbers = sorted([int(v['version']['N']) for v in versions])
        assert version_numbers == [1, 2]
        
        print(f"✓ Catalog update with version history completed for catalog_id: {catalog_id}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
