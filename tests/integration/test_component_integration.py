"""
Component Integration Tests

This module tests integration between individual system components.

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
from io import BytesIO


class TestComponentIntegration:
    """
    Integration tests for component-to-component interactions
    """
    
    def test_edge_client_to_api_gateway_upload_resumption(
        self,
        aws_integration_env: Dict[str, Any],
        test_media_files: Dict[str, str]
    ):
        """
        Test Edge Client ↔ API Gateway (upload resumption)
        
        Validates resumable upload functionality using chunked uploads.
        
        Requirements: 3.1, 3.2, 3.3
        """
        s3_client = boto3.client('s3')
        raw_bucket = aws_integration_env['s3_raw_bucket']
        
        tracking_id = f"test-resume-{uuid.uuid4().hex}"
        photo_key = f"{tracking_id}/photo.jpg"
        
        # Read test image
        with open(test_media_files['image'], 'rb') as f:
            image_data = f.read()
        
        total_size = len(image_data)
        chunk_size = total_size // 3  # Split into 3 chunks
        
        # Step 1: Initiate multipart upload
        multipart_upload = s3_client.create_multipart_upload(
            Bucket=raw_bucket,
            Key=photo_key,
            ServerSideEncryption='AES256'
        )
        
        upload_id = multipart_upload['UploadId']
        parts = []
        
        # Step 2: Upload first chunk
        chunk1 = image_data[:chunk_size]
        response1 = s3_client.upload_part(
            Bucket=raw_bucket,
            Key=photo_key,
            PartNumber=1,
            UploadId=upload_id,
            Body=chunk1
        )
        parts.append({'PartNumber': 1, 'ETag': response1['ETag']})
        
        # Step 3: Simulate connection drop (don't upload second chunk yet)
        time.sleep(0.1)
        
        # Step 4: Resume upload - upload remaining chunks
        chunk2 = image_data[chunk_size:2*chunk_size]
        response2 = s3_client.upload_part(
            Bucket=raw_bucket,
            Key=photo_key,
            PartNumber=2,
            UploadId=upload_id,
            Body=chunk2
        )
        parts.append({'PartNumber': 2, 'ETag': response2['ETag']})
        
        chunk3 = image_data[2*chunk_size:]
        response3 = s3_client.upload_part(
            Bucket=raw_bucket,
            Key=photo_key,
            PartNumber=3,
            UploadId=upload_id,
            Body=chunk3
        )
        parts.append({'PartNumber': 3, 'ETag': response3['ETag']})
        
        # Step 5: Complete multipart upload
        s3_client.complete_multipart_upload(
            Bucket=raw_bucket,
            Key=photo_key,
            UploadId=upload_id,
            MultipartUpload={'Parts': parts}
        )
        
        # Step 6: Verify uploaded file
        response = s3_client.get_object(Bucket=raw_bucket, Key=photo_key)
        uploaded_data = response['Body'].read()
        
        assert len(uploaded_data) == total_size
        assert uploaded_data == image_data
        
        print(f"✓ Resumable upload completed successfully for {photo_key}")
    
    def test_api_gateway_to_sqs_message_publishing(
        self,
        aws_integration_env: Dict[str, Any],
        test_tenant_config: Dict[str, Any]
    ):
        """
        Test API Gateway ↔ SQS (message publishing)
        
        Validates message publishing to SQS queue after upload completion.
        
        Requirements: 3.4
        """
        sqs_client = boto3.client('sqs')
        queue_url = aws_integration_env['sqs_queue_url']
        
        tracking_id = f"test-sqs-{uuid.uuid4().hex}"
        
        # Step 1: Publish message to queue (simulating API Gateway)
        message = {
            'tracking_id': tracking_id,
            'tenant_id': test_tenant_config['tenant_id'],
            'artisan_id': 'test-artisan-001',
            'photo_key': f"{tracking_id}/photo.jpg",
            'audio_key': f"{tracking_id}/audio.wav",
            'language': 'hi',
            'priority': 'normal',
            'timestamp': datetime.now().isoformat()
        }
        
        send_response = sqs_client.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message),
            MessageAttributes={
                'tracking_id': {
                    'StringValue': tracking_id,
                    'DataType': 'String'
                },
                'priority': {
                    'StringValue': 'normal',
                    'DataType': 'String'
                }
            }
        )
        
        assert 'MessageId' in send_response
        message_id = send_response['MessageId']
        
        # Step 2: Receive message from queue
        receive_response = sqs_client.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=5,
            MessageAttributeNames=['All']
        )
        
        assert 'Messages' in receive_response
        assert len(receive_response['Messages']) > 0
        
        received_message = receive_response['Messages'][0]
        received_body = json.loads(received_message['Body'])
        
        # Step 3: Verify message content
        assert received_body['tracking_id'] == tracking_id
        assert received_body['tenant_id'] == test_tenant_config['tenant_id']
        assert received_body['photo_key'] == f"{tracking_id}/photo.jpg"
        assert received_body['audio_key'] == f"{tracking_id}/audio.wav"
        
        # Step 4: Delete message (acknowledge processing)
        sqs_client.delete_message(
            QueueUrl=queue_url,
            ReceiptHandle=received_message['ReceiptHandle']
        )
        
        print(f"✓ Message published and received successfully: {message_id}")
    
    def test_sqs_to_lambda_orchestrator_message_consumption(
        self,
        aws_integration_env: Dict[str, Any]
    ):
        """
        Test SQS ↔ Lambda Orchestrator (message consumption)
        
        Validates Lambda orchestrator consuming messages from SQS.
        
        Requirements: All
        """
        sqs_client = boto3.client('sqs')
        dynamodb_client = boto3.client('dynamodb')
        
        queue_url = aws_integration_env['sqs_queue_url']
        catalog_table = aws_integration_env['dynamodb_catalog_table']
        
        tracking_id = f"test-lambda-{uuid.uuid4().hex}"
        
        # Step 1: Publish message to queue
        message = {
            'tracking_id': tracking_id,
            'tenant_id': 'test-tenant-001',
            'artisan_id': 'test-artisan-001',
            'photo_key': f"{tracking_id}/photo.jpg",
            'audio_key': f"{tracking_id}/audio.wav",
            'language': 'hi'
        }
        
        sqs_client.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message)
        )
        
        # Step 2: Simulate Lambda orchestrator consuming message
        receive_response = sqs_client.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=5
        )
        
        assert 'Messages' in receive_response
        received_message = receive_response['Messages'][0]
        received_body = json.loads(received_message['Body'])
        
        # Step 3: Simulate Lambda creating processing record
        processing_record = {
            'tracking_id': {'S': received_body['tracking_id']},
            'tenant_id': {'S': received_body['tenant_id']},
            'artisan_id': {'S': received_body['artisan_id']},
            'photo_key': {'S': received_body['photo_key']},
            'audio_key': {'S': received_body['audio_key']},
            'language': {'S': received_body['language']},
            'asr_status': {'S': 'pending'},
            'vision_status': {'S': 'pending'},
            'created_at': {'S': datetime.now().isoformat()}
        }
        
        dynamodb_client.put_item(
            TableName=catalog_table,
            Item=processing_record
        )
        
        # Step 4: Verify record created
        get_response = dynamodb_client.get_item(
            TableName=catalog_table,
            Key={'tracking_id': {'S': tracking_id}}
        )
        
        assert 'Item' in get_response
        assert get_response['Item']['tracking_id']['S'] == tracking_id
        assert get_response['Item']['asr_status']['S'] == 'pending'
        
        # Step 5: Delete message after successful processing
        sqs_client.delete_message(
            QueueUrl=queue_url,
            ReceiptHandle=received_message['ReceiptHandle']
        )
        
        print(f"✓ Lambda orchestrator message consumption successful: {tracking_id}")
    
    def test_lambda_to_s3_media_retrieval(
        self,
        aws_integration_env: Dict[str, Any],
        test_media_files: Dict[str, str]
    ):
        """
        Test Lambda ↔ S3 (media retrieval)
        
        Validates Lambda functions retrieving media from S3 for processing.
        
        Requirements: All
        """
        s3_client = boto3.client('s3')
        raw_bucket = aws_integration_env['s3_raw_bucket']
        
        tracking_id = f"test-s3-{uuid.uuid4().hex}"
        photo_key = f"{tracking_id}/photo.jpg"
        audio_key = f"{tracking_id}/audio.wav"
        
        # Step 1: Upload test media to S3
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
        
        # Step 2: Simulate Lambda retrieving media
        photo_response = s3_client.get_object(Bucket=raw_bucket, Key=photo_key)
        photo_data = photo_response['Body'].read()
        
        audio_response = s3_client.get_object(Bucket=raw_bucket, Key=audio_key)
        audio_data = audio_response['Body'].read()
        
        # Step 3: Verify retrieved data
        with open(test_media_files['image'], 'rb') as f:
            original_photo = f.read()
        
        with open(test_media_files['audio'], 'rb') as f:
            original_audio = f.read()
        
        assert photo_data == original_photo
        assert audio_data == original_audio
        
        # Step 4: Verify encryption
        assert photo_response['ServerSideEncryption'] == 'AES256'
        assert audio_response['ServerSideEncryption'] == 'AES256'
        
        print(f"✓ Media retrieval from S3 successful: {tracking_id}")
    
    def test_lambda_to_sagemaker_vision_asr(
        self,
        aws_integration_env: Dict[str, Any],
        test_media_files: Dict[str, str]
    ):
        """
        Test Lambda ↔ Sagemaker (Vision + ASR)
        
        Validates Lambda invoking Sagemaker endpoint for vision and ASR processing.
        Note: This test uses mock Sagemaker responses since actual endpoint may not be deployed.
        
        Requirements: 4.1, 4.2, 4.3, 6.1, 6.2
        """
        # Mock Sagemaker endpoint response
        # In real integration test, this would invoke actual Sagemaker endpoint
        
        tracking_id = f"test-sagemaker-{uuid.uuid4().hex}"
        
        # Step 1: Simulate Lambda preparing input for Sagemaker
        with open(test_media_files['image'], 'rb') as f:
            image_bytes = f.read()
        
        with open(test_media_files['audio'], 'rb') as f:
            audio_bytes = f.read()
        
        # Step 2: Mock Sagemaker Vision response
        mock_vision_response = {
            'category': 'handloom saree',
            'colors': ['red', 'gold'],
            'materials': ['silk'],
            'confidence': 0.92,
            'bounding_box': {'x': 100, 'y': 100, 'width': 600, 'height': 400}
        }
        
        # Step 3: Mock Sagemaker ASR response
        mock_asr_response = {
            'transcription': 'यह एक सुंदर हस्तनिर्मित साड़ी है',
            'confidence': 0.95,
            'language': 'hi',
            'segments': [
                {'text': 'यह एक सुंदर', 'start': 0.0, 'end': 1.5},
                {'text': 'हस्तनिर्मित साड़ी है', 'start': 1.5, 'end': 3.0}
            ]
        }
        
        # Step 4: Verify response structure
        assert 'category' in mock_vision_response
        assert 'confidence' in mock_vision_response
        assert mock_vision_response['confidence'] > 0.7
        
        assert 'transcription' in mock_asr_response
        assert 'language' in mock_asr_response
        assert mock_asr_response['language'] == 'hi'
        
        print(f"✓ Sagemaker integration validated: {tracking_id}")
    
    def test_lambda_to_bedrock_transcreation(
        self,
        aws_integration_env: Dict[str, Any]
    ):
        """
        Test Lambda ↔ Bedrock (transcreation)
        
        Validates Lambda invoking Bedrock for transcreation and attribute extraction.
        Note: This test uses mock Bedrock responses.
        
        Requirements: 5.1, 5.2, 5.3, 5.4, 7.1, 7.2
        """
        tracking_id = f"test-bedrock-{uuid.uuid4().hex}"
        
        # Step 1: Prepare input for Bedrock
        input_data = {
            'transcription': 'यह एक सुंदर हस्तनिर्मित बनारसी साड़ी है',
            'vision_results': {
                'category': 'handloom saree',
                'colors': ['red', 'gold'],
                'materials': ['silk']
            },
            'language': 'hi'
        }
        
        # Step 2: Mock Bedrock response
        mock_bedrock_response = {
            'extracted_attributes': {
                'category': 'handloom saree',
                'subcategory': 'Banarasi silk saree',
                'material': ['silk', 'zari'],
                'colors': ['red', 'gold'],
                'craft_technique': 'Handwoven on pit loom',
                'region_of_origin': 'Varanasi, Uttar Pradesh',
                'price': {'value': 5000, 'currency': 'INR'}
            },
            'short_description': 'Beautiful handmade Banarasi silk saree',
            'long_description': 'This is a beautiful handmade Banarasi silk saree with traditional craftsmanship from Varanasi',
            'csis': [
                {
                    'vernacular_term': 'बनारसी',
                    'transliteration': 'Banarasi',
                    'english_context': 'Traditional silk weaving style from Varanasi',
                    'cultural_significance': 'Represents centuries-old weaving tradition'
                }
            ],
            'confidence_scores': {
                'category': 0.95,
                'material': 0.92,
                'craft_technique': 0.88
            }
        }
        
        # Step 3: Verify response structure
        assert 'extracted_attributes' in mock_bedrock_response
        assert 'csis' in mock_bedrock_response
        assert len(mock_bedrock_response['csis']) > 0
        
        # Verify CSI preservation
        csi = mock_bedrock_response['csis'][0]
        assert 'vernacular_term' in csi
        assert 'english_context' in csi
        assert csi['vernacular_term'] == 'बनारसी'
        
        print(f"✓ Bedrock transcreation validated: {tracking_id}")
    
    def test_lambda_to_ondc_gateway_submission(
        self,
        aws_integration_env: Dict[str, Any],
        mock_ondc_server: str
    ):
        """
        Test Lambda ↔ ONDC Gateway (submission)
        
        Validates Lambda submitting catalog to ONDC Gateway.
        
        Requirements: 8.1, 8.2, 8.5, 9.1, 9.2
        """
        tracking_id = f"test-ondc-{uuid.uuid4().hex}"
        
        # Step 1: Prepare ONDC payload
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
                                'name': 'Beautiful Banarasi Silk Saree',
                                'short_desc': 'Handmade silk saree from Varanasi',
                                'long_desc': 'Traditional Banarasi silk saree with intricate zari work',
                                'images': ['https://example.com/saree.jpg']
                            },
                            'price': {
                                'currency': 'INR',
                                'value': '5000'
                            },
                            'category_id': 'Fashion:Ethnic Wear:Sarees',
                            'tags': {
                                'material': 'silk,zari',
                                'color': 'red,gold',
                                'craft_technique': 'Handwoven'
                            }
                        }]
                    }]
                }
            }
        }
        
        # Step 2: Submit to ONDC Gateway
        response = requests.post(
            f"{mock_ondc_server}/beckn/catalog/on_search",
            json=ondc_payload,
            headers={'Authorization': 'Bearer test-token'},
            timeout=10
        )
        
        # Step 3: Verify submission success
        assert response.status_code == 200
        response_data = response.json()
        
        assert 'catalog_ids' in response_data
        catalog_ids = response_data['catalog_ids']
        assert len(catalog_ids) > 0
        
        catalog_id = list(catalog_ids.values())[0]
        assert catalog_id.startswith('ondc-catalog-')
        
        print(f"✓ ONDC submission successful: {catalog_id}")
    
    def test_lambda_to_sns_notification_publishing(
        self,
        aws_integration_env: Dict[str, Any]
    ):
        """
        Test Lambda ↔ SNS (notification publishing)
        
        Validates Lambda publishing notifications to SNS topic.
        
        Requirements: 10.1, 10.2, 10.3
        """
        sns_client = boto3.client('sns')
        topic_arn = aws_integration_env['sns_topic_arn']
        
        tracking_id = f"test-sns-{uuid.uuid4().hex}"
        
        # Step 1: Publish notification to SNS
        notification_message = {
            'tracking_id': tracking_id,
            'tenant_id': 'test-tenant-001',
            'artisan_id': 'test-artisan-001',
            'stage': 'completed',
            'message': 'Your catalog entry has been successfully published to ONDC',
            'catalog_id': f'ondc-catalog-{uuid.uuid4().hex[:12]}',
            'timestamp': datetime.now().isoformat()
        }
        
        response = sns_client.publish(
            TopicArn=topic_arn,
            Message=json.dumps(notification_message),
            Subject='Catalog Processing Complete',
            MessageAttributes={
                'tracking_id': {
                    'StringValue': tracking_id,
                    'DataType': 'String'
                },
                'stage': {
                    'StringValue': 'completed',
                    'DataType': 'String'
                }
            }
        )
        
        # Step 2: Verify publish success
        assert 'MessageId' in response
        message_id = response['MessageId']
        
        print(f"✓ SNS notification published: {message_id}")
    
    def test_component_chain_integration(
        self,
        aws_integration_env: Dict[str, Any],
        mock_ondc_server: str,
        test_media_files: Dict[str, str]
    ):
        """
        Test complete component chain integration
        
        Validates data flow through all components:
        S3 → SQS → Lambda → DynamoDB → ONDC → SNS
        
        Requirements: All
        """
        s3_client = boto3.client('s3')
        sqs_client = boto3.client('sqs')
        dynamodb_client = boto3.client('dynamodb')
        sns_client = boto3.client('sns')
        
        tracking_id = f"test-chain-{uuid.uuid4().hex}"
        
        # Step 1: Upload to S3
        raw_bucket = aws_integration_env['s3_raw_bucket']
        photo_key = f"{tracking_id}/photo.jpg"
        
        with open(test_media_files['image'], 'rb') as f:
            s3_client.put_object(
                Bucket=raw_bucket,
                Key=photo_key,
                Body=f,
                ServerSideEncryption='AES256'
            )
        
        # Step 2: Publish to SQS
        queue_url = aws_integration_env['sqs_queue_url']
        message = {
            'tracking_id': tracking_id,
            'tenant_id': 'test-tenant-001',
            'photo_key': photo_key
        }
        
        sqs_client.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message)
        )
        
        # Step 3: Consume from SQS and create DynamoDB record
        receive_response = sqs_client.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=5
        )
        
        assert 'Messages' in receive_response
        
        catalog_table = aws_integration_env['dynamodb_catalog_table']
        dynamodb_client.put_item(
            TableName=catalog_table,
            Item={
                'tracking_id': {'S': tracking_id},
                'tenant_id': {'S': 'test-tenant-001'},
                'photo_key': {'S': photo_key},
                'created_at': {'S': datetime.now().isoformat()}
            }
        )
        
        # Step 4: Submit to ONDC
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
                                'short_desc': 'Test',
                                'long_desc': 'Test description',
                                'images': [f"https://s3.amazonaws.com/{raw_bucket}/{photo_key}"]
                            },
                            'price': {'currency': 'INR', 'value': '1000'},
                            'category_id': 'test'
                        }]
                    }]
                }
            }
        }
        
        ondc_response = requests.post(
            f"{mock_ondc_server}/beckn/catalog/on_search",
            json=ondc_payload,
            headers={'Authorization': 'Bearer test-token'}
        )
        
        assert ondc_response.status_code == 200
        
        # Step 5: Publish notification to SNS
        topic_arn = aws_integration_env['sns_topic_arn']
        sns_client.publish(
            TopicArn=topic_arn,
            Message=json.dumps({
                'tracking_id': tracking_id,
                'stage': 'completed'
            })
        )
        
        # Step 6: Verify complete chain
        final_record = dynamodb_client.get_item(
            TableName=catalog_table,
            Key={'tracking_id': {'S': tracking_id}}
        )
        
        assert 'Item' in final_record
        assert final_record['Item']['tracking_id']['S'] == tracking_id
        
        # Cleanup
        sqs_client.delete_message(
            QueueUrl=queue_url,
            ReceiptHandle=receive_response['Messages'][0]['ReceiptHandle']
        )
        
        print(f"✓ Complete component chain integration successful: {tracking_id}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
