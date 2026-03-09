"""
Lambda Workflow Orchestrator - Main SQS Event Handler

This Lambda function orchestrates the entire AI processing pipeline:
1. Consumes SQS messages with catalog processing requests
2. Fetches raw media from S3
3. Calls AWS Rekognition for Vision + AWS Transcribe for ASR
4. Calls Groq (replacing Bedrock) for transcreation and attribute extraction
5. Enhances images and saves to S3
6. Maps to ONDC schema and validates
7. Submits to ONDC Gateway
8. Publishes status notifications to SNS
9. Handles errors with graceful degradation

Requirements: 4.1, 6.1, 7.1, 7.2, 8.1, 9.1, 9.5, 10.1, 10.2, 10.3, 10.4, 
              13.3, 14.1, 14.2, 14.3, 14.4, 14.5, 19.3
"""
import json
import logging
import os
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
import boto3
from botocore.exceptions import ClientError

# Import models
from backend.models.catalog import (
    CatalogProcessingRecord,
    ProcessingStatus,
    ExtractedAttributes
)

# Import services
from backend.services.ai_orchestrator import AIOrchestrator
# COMMENTED: Bedrock-specific services (replaced by Groq)
# from backend.services.bedrock_client.client import BedrockClient
# from backend.services.bedrock_client.attribute_extractor import AttributeExtractor
# from backend.services.bedrock_client.transcreation_service import TranscreationService
from backend.services.bedrock_client.unified_client import UnifiedBedrockClient  # Using Groq
from backend.services.media_processing import image_enhancement
from backend.services.ondc_gateway.gateway import ONDCGateway
from backend.services.ondc_gateway.api_client import ONDCAPIClient

# Import shared utilities
from backend.lambda_functions.shared.config import config
from backend.lambda_functions.shared.logger import setup_logger
from backend.lambda_functions.api_handlers.data_minimization import (
    filter_pii_from_text,
    create_bedrock_pii_filtering_prompt,  # Still useful for prompt structure
    validate_no_pii_in_output
)

# Import observability services
from backend.services.observability.metrics import get_metrics_service
from backend.services.observability.tracing import (
    get_tracing_service,
    trace_lambda_handler,
    trace_operation
)

# Setup logger
logger = setup_logger(__name__)

# Initialize AWS clients
s3_client = boto3.client('s3', region_name=config.AWS_REGION)
dynamodb = boto3.resource('dynamodb', region_name=config.AWS_REGION)
sns_client = boto3.client('sns', region_name=config.AWS_REGION)
sqs_client = boto3.client('sqs', region_name=config.AWS_REGION)

# Initialize service clients (reused across invocations)
ai_orchestrator = None
# COMMENTED: Bedrock-specific clients
# bedrock_client = None
# attribute_extractor = None
# transcreation_service = None
unified_client = None  # Using Groq-based unified client
ondc_gateway = None
metrics_service = None
tracing_service = None


def get_metrics_service_instance():
    """Get or create metrics service singleton"""
    global metrics_service
    if metrics_service is None:
        metrics_service = get_metrics_service(
            namespace='VernacularArtisanCatalog',
            region=config.AWS_REGION
        )
    return metrics_service


def get_tracing_service_instance():
    """Get or create tracing service singleton"""
    global tracing_service
    if tracing_service is None:
        tracing_service = get_tracing_service(
            service_name='VernacularArtisanCatalog'
        )
    return tracing_service


def get_ai_orchestrator() -> AIOrchestrator:
    """Get or create AI Orchestrator (singleton)"""
    global ai_orchestrator
    if ai_orchestrator is None:
        ai_orchestrator = AIOrchestrator(
            region=config.AWS_REGION,
            rekognition_project_arn=os.getenv('REKOGNITION_PROJECT_ARN'),
            transcribe_s3_bucket=os.getenv('TRANSCRIBE_S3_BUCKET')
        )
    return ai_orchestrator


# COMMENTED: Bedrock-specific client getters (replaced by unified client)
# def get_bedrock_client() -> BedrockClient:
#     """Get or create Bedrock client (singleton)"""
#     global bedrock_client
#     if bedrock_client is None:
#         bedrock_client = BedrockClient(
#             model_id=config.BEDROCK_MODEL_ID,
#             region=config.AWS_REGION
#         )
#     return bedrock_client


# def get_attribute_extractor() -> AttributeExtractor:
#     """Get or create Attribute Extractor (singleton)"""
#     global attribute_extractor
#     if attribute_extractor is None:
#         attribute_extractor = AttributeExtractor(
#             bedrock_client=get_bedrock_client()
#         )
#     return attribute_extractor


# def get_transcreation_service() -> TranscreationService:
#     """Get or create Transcreation Service (singleton)"""
#     global transcreation_service
#     if transcreation_service is None:
#         transcreation_service = TranscreationService(
#             bedrock_client=get_bedrock_client()
#         )
#     return transcreation_service


def get_unified_client() -> UnifiedBedrockClient:
    """Get or create Unified AI client (singleton) - Using Groq"""
    global unified_client
    if unified_client is None:
        from services.ai_client import AIProvider
        unified_client = UnifiedBedrockClient(
            preferred_provider=AIProvider.GROQ
        )
    return unified_client


def get_ondc_gateway() -> ONDCGateway:
    """Get or create ONDC Gateway (singleton)"""
    global ondc_gateway
    if ondc_gateway is None:
        api_client = ONDCAPIClient(
            base_url=config.ONDC_API_URL,
            seller_id=config.ONDC_SELLER_ID,
            api_key=config.ONDC_API_KEY
        )
        ondc_gateway = ONDCGateway(api_client=api_client)
    return ondc_gateway


@trace_lambda_handler
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for SQS events
    
    Args:
        event: SQS event with catalog processing messages
        context: Lambda context
        
    Returns:
        Response with batch item failures for retry
        
    Requirements: 10.1, 10.2
    """
    logger.info(f"Received SQS event with {len(event.get('Records', []))} messages")
    
    # Get metrics service
    metrics = get_metrics_service_instance()
    
    # Emit queue depth metric
    try:
        # Get approximate queue depth from SQS
        queue_attrs = sqs_client.get_queue_attributes(
            QueueUrl=config.SQS_QUEUE_URL,
            AttributeNames=['ApproximateNumberOfMessages']
        )
        queue_depth = int(queue_attrs.get('Attributes', {}).get('ApproximateNumberOfMessages', 0))
        metrics.emit_queue_depth('catalog-processing-queue', queue_depth)
    except Exception as e:
        logger.warning(f"Failed to emit queue depth metric: {e}")
    
    # Check if batch processing is enabled
    batch_size = len(event.get('Records', []))
    enable_batch = batch_size >= 5  # Requirement 13.3
    
    if enable_batch:
        logger.info(f"Batch processing enabled for {batch_size} entries")
    
    # Track failed messages for retry
    batch_item_failures = []
    
    # Process each SQS message
    for record in event.get('Records', []):
        message_id = record.get('messageId')
        receipt_handle = record.get('receiptHandle')
        
        try:
            # Parse message body
            body = json.loads(record.get('body', '{}'))
            logger.info(f"Processing message: {message_id}, tracking_id: {body.get('tracking_id')}")
            
            # Process catalog entry
            result = process_catalog_entry(body)
            
            if not result['success']:
                # Add to batch failures for retry
                batch_item_failures.append({'itemIdentifier': message_id})
                logger.error(f"Processing failed for message {message_id}: {result.get('error')}")
            else:
                logger.info(f"Successfully processed message {message_id}")
                
        except Exception as e:
            logger.error(f"Error processing message {message_id}: {str(e)}", exc_info=True)
            batch_item_failures.append({'itemIdentifier': message_id})
    
    # Return batch item failures for SQS retry
    return {
        'batchItemFailures': batch_item_failures
    }


def process_catalog_entry(message: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a single catalog entry through the entire pipeline
    
    Args:
        message: SQS message with catalog processing request
        
    Returns:
        Dict with success status and result details
        
    Requirements: 4.1, 6.1, 7.1, 7.2, 8.1, 9.1, 9.5, 14.1, 14.2, 14.3, 14.4, 14.5
    """
    tracking_id = message.get('tracking_id')
    tenant_id = message.get('tenant_id')
    artisan_id = message.get('artisan_id')
    photo_key = message.get('photo_key')
    audio_key = message.get('audio_key')
    language = message.get('language', 'hi')
    
    logger.info(
        f"Starting pipeline: tracking_id={tracking_id}, "
        f"tenant_id={tenant_id}, language={language}"
    )
    
    # Get metrics service
    metrics = get_metrics_service_instance()
    
    # Track overall processing time
    pipeline_start_time = time.time()
    
    try:
        # Initialize processing record
        record = get_or_create_processing_record(
            tracking_id, tenant_id, artisan_id, photo_key, audio_key, language
        )
        
        # Stage 1: Fetch raw media from S3
        logger.info(f"[{tracking_id}] Stage 1: Fetching raw media from S3")
        image_bytes, audio_bytes = fetch_raw_media(photo_key, audio_key)
        
        # Stage 2: Call Sagemaker for Vision + ASR
        logger.info(f"[{tracking_id}] Stage 2: Calling Sagemaker for Vision + ASR")
        sagemaker_start = time.time()
        sagemaker_result = call_sagemaker_endpoint(
            tracking_id, record, image_bytes, audio_bytes, language
        )
        sagemaker_latency = (time.time() - sagemaker_start) * 1000
        metrics.emit_processing_latency('sagemaker', sagemaker_latency, tenant_id, tracking_id)
        
        # Stage 3: Call Bedrock for attribute extraction and transcreation
        logger.info(f"[{tracking_id}] Stage 3: Calling Bedrock for transcreation")
        bedrock_start = time.time()
        extracted_attrs = call_bedrock_for_extraction(
            tracking_id, record, sagemaker_result, language
        )
        bedrock_latency = (time.time() - bedrock_start) * 1000
        metrics.emit_processing_latency('bedrock', bedrock_latency, tenant_id, tracking_id)
        
        # Stage 4: Enhance images and save to S3
        logger.info(f"[{tracking_id}] Stage 4: Enhancing images")
        enhanced_image_urls = enhance_and_save_images(
            tracking_id, record, image_bytes, photo_key
        )
        
        # Stage 5: Map to ONDC schema, validate, and submit
        logger.info(f"[{tracking_id}] Stage 5: Submitting to ONDC")
        ondc_start = time.time()
        ondc_result = submit_to_ondc(
            tracking_id, record, extracted_attrs, enhanced_image_urls,
            tenant_id, artisan_id
        )
        ondc_latency = (time.time() - ondc_start) * 1000
        metrics.emit_processing_latency('ondc_submission', ondc_latency, tenant_id, tracking_id)
        
        # Stage 6: Publish success notification
        logger.info(f"[{tracking_id}] Stage 6: Publishing notification")
        publish_notification(
            tracking_id, tenant_id, artisan_id, language,
            stage='completed',
            catalog_id=ondc_result.ondc_catalog_id
        )
        
        # Mark as completed
        record.completed_at = datetime.utcnow()
        save_processing_record(record)
        
        # Emit success metrics
        pipeline_latency = (time.time() - pipeline_start_time) * 1000
        metrics.emit_processing_latency('total_pipeline', pipeline_latency, tenant_id, tracking_id)
        metrics.emit_success_rate('catalog_processing', 1, tenant_id)
        metrics.emit_ondc_submission_status('success', tenant_id, tracking_id)
        
        logger.info(f"[{tracking_id}] Pipeline completed successfully in {pipeline_latency:.2f}ms")
        
        return {
            'success': True,
            'tracking_id': tracking_id,
            'catalog_id': ondc_result.ondc_catalog_id
        }
        
    except Exception as e:
        logger.error(f"[{tracking_id}] Pipeline failed: {str(e)}", exc_info=True)
        
        # Emit error metrics
        pipeline_latency = (time.time() - pipeline_start_time) * 1000
        metrics.emit_processing_latency('total_pipeline', pipeline_latency, tenant_id, tracking_id)
        metrics.emit_error_rate('catalog_processing', 1, tenant_id, type(e).__name__)
        metrics.emit_ondc_submission_status('failed', tenant_id, tracking_id)
        
        # Update record with error
        try:
            record = get_processing_record(tracking_id)
            if record:
                record.error_details = {
                    'error': str(e),
                    'timestamp': datetime.utcnow().isoformat()
                }
                save_processing_record(record)
        except Exception as save_error:
            logger.error(f"Failed to save error details: {str(save_error)}")
        
        # Publish failure notification
        try:
            publish_notification(
                tracking_id, tenant_id, artisan_id, language,
                stage='failed',
                error_message=str(e)
            )
        except Exception as notif_error:
            logger.error(f"Failed to publish notification: {str(notif_error)}")
        
        # Check if error is recoverable
        if is_recoverable_error(e):
            # Return failure to trigger SQS retry
            return {
                'success': False,
                'error': str(e),
                'recoverable': True
            }
        else:
            # Send to DLQ (SQS will handle this automatically after max retries)
            logger.error(f"[{tracking_id}] Unrecoverable error, will route to DLQ")
            return {
                'success': False,
                'error': str(e),
                'recoverable': False
            }


def fetch_raw_media(
    photo_key: str,
    audio_key: str
) -> tuple[Optional[bytes], Optional[bytes]]:
    """
    Fetch raw media files from S3
    
    Args:
        photo_key: S3 key for photo
        audio_key: S3 key for audio
        
    Returns:
        Tuple of (image_bytes, audio_bytes)
    """
    image_bytes = None
    audio_bytes = None
    
    try:
        if photo_key:
            response = s3_client.get_object(
                Bucket=config.S3_RAW_MEDIA_BUCKET,
                Key=photo_key
            )
            image_bytes = response['Body'].read()
            logger.info(f"Fetched image: {len(image_bytes)} bytes")
    except ClientError as e:
        logger.error(f"Error fetching image from S3: {e}")
        raise
    
    try:
        if audio_key:
            response = s3_client.get_object(
                Bucket=config.S3_RAW_MEDIA_BUCKET,
                Key=audio_key
            )
            audio_bytes = response['Body'].read()
            logger.info(f"Fetched audio: {len(audio_bytes)} bytes")
    except ClientError as e:
        logger.error(f"Error fetching audio from S3: {e}")
        raise
    
    return image_bytes, audio_bytes


def call_sagemaker_endpoint(
    tracking_id: str,
    record: CatalogProcessingRecord,
    image_bytes: Optional[bytes],
    audio_bytes: Optional[bytes],
    language: str
) -> Dict[str, Any]:
    """
    Call AI services for Vision + ASR processing using new AI stack
    
    Requirements: 4.1, 6.1, 14.1
    """
    tracing = get_tracing_service_instance()
    
    try:
        # Update status
        record.asr_status = ProcessingStatus.IN_PROGRESS
        record.vision_status = ProcessingStatus.IN_PROGRESS
        save_processing_record(record)
        
        # Create X-Ray subsegment for AI processing
        subsegment = tracing.trace_sagemaker_call(
            endpoint_name='ai-orchestrator',
            tracking_id=tracking_id,
            tenant_id=record.tenant_id
        )
        
        try:
            # Call AI Orchestrator with new stack
            orchestrator = get_ai_orchestrator()
            result = orchestrator.process_product(
                image_bytes=image_bytes,
                audio_bytes=audio_bytes,
                language_code=language,
                audio_format='opus'
            )
            
            # Extract results from new format
            transcription_result = result.get('transcription', {})
            vision_result = result.get('vision_analysis', {})
            detection_result = result.get('detection', {})
            
            # Update record with results
            record.asr_result = transcription_result
            record.vision_result = {
                **vision_result,
                'detection': detection_result  # Include detection info
            }
            
            # Check for low confidence and handle gracefully
            if transcription_result.get('requires_manual_review'):
                logger.warning(f"[{tracking_id}] ASR requires manual review")
                record.asr_status = ProcessingStatus.COMPLETED  # Continue with low confidence
            else:
                record.asr_status = ProcessingStatus.COMPLETED
            
            if vision_result.get('requires_manual_review'):
                logger.warning(f"[{tracking_id}] Vision requires manual review")
                record.vision_status = ProcessingStatus.COMPLETED  # Continue with low confidence
            else:
                record.vision_status = ProcessingStatus.COMPLETED
            
            save_processing_record(record)
            
            # Return in expected format for downstream processing
            return {
                'transcription': transcription_result,
                'vision': vision_result,
                'detection': detection_result,
                'overall_confidence': result.get('overall_confidence', 0.0)
            }
            
        finally:
            tracing.end_subsegment(subsegment)
        
    except Exception as e:
        logger.error(f"[{tracking_id}] AI processing failed: {str(e)}")
        
        # Graceful degradation: Skip ASR/Vision if fails (Requirement 14.1, 14.2)
        record.asr_status = ProcessingStatus.SKIPPED
        record.vision_status = ProcessingStatus.SKIPPED
        record.asr_result = {'error': str(e), 'text': '', 'confidence': 0.0}
        record.vision_result = {'error': str(e)}
        save_processing_record(record)
        
        # Return empty results to continue pipeline
        return {
            'transcription': {'text': '', 'confidence': 0.0},
            'vision': {},
            'detection': {},
            'overall_confidence': 0.0
        }


def call_bedrock_for_extraction(
    tracking_id: str,
    record: CatalogProcessingRecord,
    sagemaker_result: Dict[str, Any],
    language: str
) -> ExtractedAttributes:
    """
    Call Bedrock for attribute extraction and transcreation
    
    Requirements: 7.1, 7.2, 12.2, 14.3
    """
    tracing = get_tracing_service_instance()
    
    try:
        # Update status
        record.extraction_status = ProcessingStatus.IN_PROGRESS
        save_processing_record(record)
        
        # Extract transcription and vision data
        transcription_text = sagemaker_result.get('transcription', {}).get('text', '')
        vision_data = sagemaker_result.get('vision', {})
        
        # Apply PII filtering to transcription (Requirement 12.2)
        if transcription_text:
            logger.info(f"[{tracking_id}] Applying PII filtering to transcription")
            filtered_transcription = filter_pii_from_text(transcription_text)
            
            # Update sagemaker result with filtered text
            sagemaker_result['transcription']['text'] = filtered_transcription
            
            # Log if PII was filtered
            if filtered_transcription != transcription_text:
                logger.info(f"[{tracking_id}] PII filtered from transcription")
        
        # Create X-Ray subsegment for Bedrock attribute extraction
        subsegment = tracing.trace_bedrock_call(
            model_id=config.BEDROCK_MODEL_ID,
            operation='attribute_extraction',
            tracking_id=tracking_id,
            tenant_id=record.tenant_id
        )
        
        try:
            # Call Bedrock for attribute extraction
            extractor = get_attribute_extractor()
            extracted = extractor.extract_attributes_with_priority(
                asr_result=sagemaker_result.get('transcription', {}),
                vision_result=vision_data,
                language=language
            )
        finally:
            tracing.end_subsegment(subsegment)
        
        # Create X-Ray subsegment for Bedrock transcreation
        subsegment = tracing.trace_bedrock_call(
            model_id=config.BEDROCK_MODEL_ID,
            operation='transcreation',
            tracking_id=tracking_id,
            tenant_id=record.tenant_id
        )
        
        try:
            # Call Bedrock for transcreation
            transcreation_svc = get_transcreation_service()
            extracted = transcreation_svc.transcreate_with_cultural_preservation(
                vernacular_text=filtered_transcription if transcription_text else '',
                extracted_attrs=extracted,
                language=language
            )
        finally:
            tracing.end_subsegment(subsegment)
        
        # Validate no PII in output
        if extracted.long_description:
            if not validate_no_pii_in_output(extracted.long_description):
                logger.warning(f"[{tracking_id}] PII detected in output, applying additional filtering")
                extracted.long_description = filter_pii_from_text(extracted.long_description)
        
        if extracted.short_description:
            if not validate_no_pii_in_output(extracted.short_description):
                logger.warning(f"[{tracking_id}] PII detected in short description, applying additional filtering")
                extracted.short_description = filter_pii_from_text(extracted.short_description)
        
        # Update record
        record.extraction_result = extracted.dict()
        record.extraction_status = ProcessingStatus.COMPLETED
        save_processing_record(record)
        
        return extracted
        
    except Exception as e:
        logger.error(f"[{tracking_id}] Bedrock extraction failed: {str(e)}")
        
        # Graceful degradation: Use basic extraction (Requirement 14.3)
        record.extraction_status = ProcessingStatus.SKIPPED
        record.extraction_result = {'error': str(e)}
        save_processing_record(record)
        
        # Return minimal attributes
        return ExtractedAttributes(
            category='Unknown',
            short_description='Product description unavailable',
            long_description='Product description unavailable',
            confidence_scores={'category': 0.0}
        )


def enhance_and_save_images(
    tracking_id: str,
    record: CatalogProcessingRecord,
    image_bytes: Optional[bytes],
    original_key: str
) -> List[str]:
    """
    Enhance images and save to S3 enhanced bucket
    
    Requirements: 6.1, 6.2, 6.3, 6.4, 14.2
    """
    if not image_bytes:
        logger.warning(f"[{tracking_id}] No image to enhance")
        return []
    
    try:
        # Use the enhance_and_upload function from image_enhancement module
        image_urls = image_enhancement.enhance_and_upload(
            image_data=image_bytes,
            tracking_id=tracking_id,
            bucket_name=config.S3_ENHANCED_BUCKET
        )
        
        logger.info(f"[{tracking_id}] Enhanced and uploaded {len(image_urls)} images")
        return image_urls
        
    except Exception as e:
        logger.error(f"[{tracking_id}] Image enhancement failed: {str(e)}")
        
        # Graceful degradation: Use original image (Requirement 14.2)
        try:
            # Upload original image
            key = f"enhanced/{tracking_id}/original.jpg"
            s3_client.put_object(
                Bucket=config.S3_ENHANCED_BUCKET,
                Key=key,
                Body=image_bytes,
                ContentType='image/jpeg'
            )
            
            url = f"https://{config.S3_ENHANCED_BUCKET}.s3.{config.AWS_REGION}.amazonaws.com/{key}"
            logger.info(f"[{tracking_id}] Using original image: {url}")
            return [url]
            
        except Exception as upload_error:
            logger.error(f"[{tracking_id}] Failed to upload original image: {str(upload_error)}")
            return []


def submit_to_ondc(
    tracking_id: str,
    record: CatalogProcessingRecord,
    extracted: ExtractedAttributes,
    image_urls: List[str],
    tenant_id: str,
    artisan_id: str
) -> Any:
    """
    Submit catalog entry to ONDC Gateway
    
    Requirements: 8.1, 9.1, 9.5
    """
    tracing = get_tracing_service_instance()
    
    try:
        # Update status
        record.mapping_status = ProcessingStatus.IN_PROGRESS
        record.submission_status = ProcessingStatus.IN_PROGRESS
        save_processing_record(record)
        
        # Create X-Ray subsegment for ONDC submission
        subsegment = tracing.trace_ondc_call(
            operation='submit_catalog',
            tracking_id=tracking_id,
            tenant_id=tenant_id
        )
        
        try:
            # Submit to ONDC Gateway
            gateway = get_ondc_gateway()
            result = gateway.submit_catalog(
                extracted=extracted,
                tracking_id=tracking_id,
                tenant_id=tenant_id,
                artisan_id=artisan_id,
                image_urls=image_urls
            )
            
            if result.success:
                # Update record
                record.mapping_status = ProcessingStatus.COMPLETED
                record.submission_status = ProcessingStatus.COMPLETED
                record.ondc_catalog_id = result.ondc_catalog_id
                save_processing_record(record)
                
                logger.info(f"[{tracking_id}] ONDC submission successful: {result.ondc_catalog_id}")
                return result
            else:
                # Submission failed
                record.mapping_status = ProcessingStatus.FAILED
                record.submission_status = ProcessingStatus.FAILED
                record.error_details = {
                    'ondc_error': result.error_message,
                    'validation_errors': [e.to_dict() for e in result.validation_errors]
                }
                save_processing_record(record)
                
                raise Exception(f"ONDC submission failed: {result.error_message}")
                
        finally:
            tracing.end_subsegment(subsegment)
            
    except Exception as e:
        logger.error(f"[{tracking_id}] ONDC submission failed: {str(e)}")
        
        record.mapping_status = ProcessingStatus.FAILED
        record.submission_status = ProcessingStatus.FAILED
        save_processing_record(record)
        
        raise


def publish_notification(
    tracking_id: str,
    tenant_id: str,
    artisan_id: str,
    language: str,
    stage: str,
    catalog_id: Optional[str] = None,
    error_message: Optional[str] = None
):
    """
    Publish status notification to SNS
    
    Requirements: 10.1, 10.2, 10.3, 10.4
    """
    try:
        # Localize message based on language
        message = localize_notification_message(stage, language, catalog_id, error_message)
        
        # Publish to SNS
        sns_topic_arn = os.getenv('SNS_NOTIFICATION_TOPIC_ARN')
        if not sns_topic_arn:
            logger.warning("SNS_NOTIFICATION_TOPIC_ARN not configured, skipping notification")
            return
        
        sns_client.publish(
            TopicArn=sns_topic_arn,
            Message=json.dumps({
                'tracking_id': tracking_id,
                'tenant_id': tenant_id,
                'artisan_id': artisan_id,
                'stage': stage,
                'catalog_id': catalog_id,
                'message': message,
                'language': language,
                'timestamp': datetime.utcnow().isoformat()
            }),
            Subject=f"Catalog Processing: {stage}",
            MessageAttributes={
                'tracking_id': {'DataType': 'String', 'StringValue': tracking_id},
                'stage': {'DataType': 'String', 'StringValue': stage},
                'language': {'DataType': 'String', 'StringValue': language}
            }
        )
        
        logger.info(f"[{tracking_id}] Published notification: stage={stage}")
        
    except Exception as e:
        logger.error(f"[{tracking_id}] Failed to publish notification: {str(e)}")
        # Don't fail the pipeline if notification fails


def localize_notification_message(
    stage: str,
    language: str,
    catalog_id: Optional[str] = None,
    error_message: Optional[str] = None
) -> str:
    """
    Localize notification message to artisan's language
    
    Requirements: 10.4
    """
    # Simple localization (in production, use proper i18n library)
    messages = {
        'hi': {
            'uploaded': 'आपकी उत्पाद जानकारी प्राप्त हो गई है',
            'processing': 'आपके उत्पाद की जानकारी संसाधित की जा रही है',
            'completed': f'आपका उत्पाद सफलतापूर्वक सूचीबद्ध हो गया है। कैटलॉग ID: {catalog_id}',
            'failed': f'उत्पाद सूचीबद्ध करने में त्रुटि: {error_message}'
        },
        'en': {
            'uploaded': 'Your product information has been received',
            'processing': 'Your product is being processed',
            'completed': f'Your product has been successfully listed. Catalog ID: {catalog_id}',
            'failed': f'Error listing product: {error_message}'
        }
    }
    
    # Default to English if language not supported
    lang_messages = messages.get(language, messages['en'])
    return lang_messages.get(stage, f'Status: {stage}')


def is_recoverable_error(error: Exception) -> bool:
    """
    Determine if error is recoverable (should retry)
    
    Requirements: 14.5
    """
    # Network errors, timeouts, throttling are recoverable
    error_str = str(error).lower()
    recoverable_keywords = [
        'timeout', 'throttl', 'rate limit', 'service unavailable',
        'connection', 'network', '503', '429', '500', '502', '504'
    ]
    
    return any(keyword in error_str for keyword in recoverable_keywords)


# DynamoDB helper functions

def get_processing_record(tracking_id: str) -> Optional[CatalogProcessingRecord]:
    """Get processing record from DynamoDB"""
    try:
        table = dynamodb.Table(config.DYNAMODB_CATALOG_TABLE)
        response = table.get_item(Key={'tracking_id': tracking_id})
        
        if 'Item' in response:
            return CatalogProcessingRecord(**response['Item'])
        return None
        
    except Exception as e:
        logger.error(f"Error getting processing record: {e}")
        return None


def get_or_create_processing_record(
    tracking_id: str,
    tenant_id: str,
    artisan_id: str,
    photo_key: str,
    audio_key: str,
    language: str
) -> CatalogProcessingRecord:
    """Get or create processing record"""
    record = get_processing_record(tracking_id)
    
    if record is None:
        record = CatalogProcessingRecord(
            tracking_id=tracking_id,
            tenant_id=tenant_id,
            artisan_id=artisan_id,
            photo_key=photo_key,
            audio_key=audio_key,
            language=language
        )
        save_processing_record(record)
    
    return record


def save_processing_record(record: CatalogProcessingRecord):
    """Save processing record to DynamoDB"""
    try:
        table = dynamodb.Table(config.DYNAMODB_CATALOG_TABLE)
        record.updated_at = datetime.utcnow()
        
        table.put_item(Item=json.loads(record.json()))
        
    except Exception as e:
        logger.error(f"Error saving processing record: {e}")
        raise
