"""
API Gateway Lambda handler
"""
import json
import uuid
from datetime import datetime
from typing import Dict, Any
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.utilities.typing import LambdaContext

# Import models
import sys
sys.path.append('/opt/python')  # Lambda layer path

from backend.models.request import CatalogSubmissionRequest, CatalogQueryRequest
from backend.models.response import (
    CatalogSubmissionResponse,
    CatalogListResponse,
    ErrorResponse,
    HealthCheckResponse,
    UploadResponse,
    UploadCompleteResponse,
    StatusUpdate
)
from backend.models.catalog import ProcessingStatus
from backend.lambda_functions.api_handlers.upload_handlers import upload_handler

# Initialize
logger = Logger()
tracer = Tracer()
app = APIGatewayRestResolver()


@app.get("/health")
@tracer.capture_method
def health_check() -> Dict[str, Any]:
    """Health check endpoint"""
    logger.info("Health check requested")
    
    response = HealthCheckResponse(
        status="healthy",
        services={
            "api": "operational",
            "database": "operational",
            "queue": "operational"
        }
    )
    
    return response.dict()


# ============================================================================
# Resumable Upload Endpoints
# ============================================================================

@app.post("/v1/catalog/upload/initiate")
@tracer.capture_method
def initiate_upload() -> Dict[str, Any]:
    """
    Initiate resumable upload by generating presigned S3 URLs
    
    Request body:
    - tenantId: Tenant organization identifier
    - artisanId: Artisan identifier
    - contentType: MIME type (image/jpeg, audio/opus, etc.)
    
    Returns:
    - trackingId: Unique tracking identifier
    - uploadUrl: Presigned URL for S3 upload
    - expiresAt: URL expiration timestamp
    """
    try:
        request_data = app.current_event.json_body
        logger.info("Upload initiation requested", extra={"request": request_data})
        
        # Validate required fields
        tenant_id = request_data.get('tenantId')
        artisan_id = request_data.get('artisanId')
        content_type = request_data.get('contentType')
        
        if not tenant_id or not artisan_id or not content_type:
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "error": "ValidationError",
                    "message": "tenantId, artisanId, and contentType are required"
                })
            }
        
        # Validate content type
        allowed_types = [
            'image/jpeg', 'image/png', 
            'audio/opus', 'audio/mpeg', 'audio/wav'
        ]
        if content_type not in allowed_types:
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "error": "ValidationError",
                    "message": f"contentType must be one of: {', '.join(allowed_types)}"
                })
            }
        
        # Initiate upload
        result = upload_handler.initiate_upload(tenant_id, artisan_id, content_type)
        
        response = UploadResponse(
            tracking_id=result['tracking_id'],
            upload_url=result['upload_url'],
            expires_at=result['expires_at']
        )
        
        return {
            "statusCode": 200,
            "body": response.json()
        }
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        return {
            "statusCode": 400,
            "body": json.dumps({
                "error": "ValidationError",
                "message": str(e)
            })
        }
    except Exception as e:
        logger.error(f"Error initiating upload: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": "InternalServerError",
                "message": "Failed to initiate upload"
            })
        }


@app.post("/v1/catalog/upload/complete")
@tracer.capture_method
def complete_upload() -> Dict[str, Any]:
    """
    Complete upload and publish to SQS for processing
    
    Request body:
    - trackingId: Tracking identifier from initiate
    - photoKey: S3 key for photo (optional)
    - audioKey: S3 key for audio (optional)
    - language: Language code (default: 'hi')
    
    Returns:
    - status: 'accepted'
    - trackingId: Tracking identifier
    - message: Confirmation message
    """
    try:
        request_data = app.current_event.json_body
        logger.info("Upload completion requested", extra={"request": request_data})
        
        # Validate required fields
        tracking_id = request_data.get('trackingId')
        if not tracking_id:
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "error": "ValidationError",
                    "message": "trackingId is required"
                })
            }
        
        photo_key = request_data.get('photoKey')
        audio_key = request_data.get('audioKey')
        language = request_data.get('language', 'hi')
        
        # Complete upload
        result = upload_handler.complete_upload(
            tracking_id=tracking_id,
            photo_key=photo_key,
            audio_key=audio_key,
            language=language
        )
        
        response = UploadCompleteResponse(
            status=result['status'],
            tracking_id=result['tracking_id'],
            message=result['message']
        )
        
        return {
            "statusCode": 200,
            "body": response.json()
        }
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        return {
            "statusCode": 400,
            "body": json.dumps({
                "error": "ValidationError",
                "message": str(e)
            })
        }
    except Exception as e:
        logger.error(f"Error completing upload: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": "InternalServerError",
                "message": "Failed to complete upload"
            })
        }


@app.get("/v1/catalog/status/<tracking_id>")
@tracer.capture_method
def get_catalog_status_v1(tracking_id: str) -> Dict[str, Any]:
    """
    Get processing status for a tracking ID
    
    Path parameter:
    - tracking_id: Tracking identifier
    
    Returns:
    - trackingId: Tracking identifier
    - stage: Current processing stage
    - message: Status message
    - catalogId: ONDC catalog ID (if completed)
    - errorDetails: Error information (if failed)
    """
    try:
        logger.info("Status requested", extra={"tracking_id": tracking_id})
        
        # Get status
        result = upload_handler.get_status(tracking_id)
        
        response = StatusUpdate(
            tracking_id=result['tracking_id'],
            stage=result['stage'],
            message=result['message'],
            catalog_id=result.get('catalog_id'),
            timestamp=result['timestamp']
        )
        
        return {
            "statusCode": 200,
            "body": response.json()
        }
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        return {
            "statusCode": 404,
            "body": json.dumps({
                "error": "NotFound",
                "message": str(e)
            })
        }
    except Exception as e:
        logger.error(f"Error fetching status: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": "InternalServerError",
                "message": "Failed to fetch status"
            })
        }


# ============================================================================
# Legacy Catalog Endpoints (for backward compatibility)
# ============================================================================

@app.post("/catalog")
@tracer.capture_method
def submit_catalog() -> Dict[str, Any]:
    """
    Submit a new catalog entry for processing
    
    Request body should contain:
    - tenant_id: Artisan identifier
    - language: Language code (hi, te, ta, etc.)
    - image_data: Base64 encoded image (optional)
    - audio_data: Base64 encoded audio (optional)
    - metadata: Additional metadata (optional)
    """
    try:
        # Parse request
        request_data = app.current_event.json_body
        logger.info("Catalog submission received", extra={"tenant_id": request_data.get("tenant_id")})
        
        # Validate request
        submission = CatalogSubmissionRequest(**request_data)

        
        # Validate at least one media type is provided
        if not submission.image_data and not submission.audio_data:
            return {
                "statusCode": 400,
                "body": ErrorResponse(
                    error="ValidationError",
                    message="At least one of image_data or audio_data must be provided"
                ).json()
            }
        
        # Generate catalog ID
        catalog_id = f"cat_{uuid.uuid4().hex[:12]}"
        
        # TODO: Store in DynamoDB
        # TODO: Upload media to S3
        # TODO: Send message to SQS queue
        
        # For now, return mock response
        response = CatalogSubmissionResponse(
            catalog_id=catalog_id,
            status=ProcessingStatus.PENDING,
            message="Catalog submission received and queued for processing",
            estimated_processing_time_seconds=30
        )
        
        logger.info("Catalog submitted successfully", extra={"catalog_id": catalog_id})
        
        return {
            "statusCode": 202,
            "body": response.json()
        }
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        return {
            "statusCode": 400,
            "body": ErrorResponse(
                error="ValidationError",
                message=str(e)
            ).json()
        }
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "body": ErrorResponse(
                error="InternalServerError",
                message="An unexpected error occurred"
            ).json()
        }


@app.get("/catalog/<catalog_id>")
@tracer.capture_method
def get_catalog_status(catalog_id: str) -> Dict[str, Any]:
    """
    Get status of a specific catalog entry
    
    Path parameter:
    - catalog_id: Catalog identifier
    """
    try:
        logger.info("Catalog status requested", extra={"catalog_id": catalog_id})
        
        # TODO: Fetch from DynamoDB
        
        # Mock response
        return {
            "statusCode": 200,
            "body": json.dumps({
                "catalog_id": catalog_id,
                "status": "processing",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            })
        }
        
    except Exception as e:
        logger.error(f"Error fetching catalog: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "body": ErrorResponse(
                error="InternalServerError",
                message="Failed to fetch catalog status"
            ).json()
        }



@app.get("/catalog")
@tracer.capture_method
def list_catalogs() -> Dict[str, Any]:
    """
    List catalog entries with optional filters
    
    Query parameters:
    - tenant_id: Filter by tenant (optional)
    - status: Filter by status (optional)
    - limit: Number of results (default: 10, max: 100)
    """
    try:
        # Parse query parameters
        query_params = app.current_event.query_string_parameters or {}
        logger.info("Catalog list requested", extra={"params": query_params})
        
        query = CatalogQueryRequest(**query_params)
        
        # TODO: Query DynamoDB
        
        # Mock response
        response = CatalogListResponse(
            catalogs=[],
            total=0,
            limit=query.limit
        )
        
        return {
            "statusCode": 200,
            "body": response.json()
        }
        
    except Exception as e:
        logger.error(f"Error listing catalogs: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "body": ErrorResponse(
                error="InternalServerError",
                message="Failed to list catalogs"
            ).json()
        }


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Lambda handler for API Gateway events
    
    This handler uses AWS Lambda Powertools for:
    - Structured logging
    - Distributed tracing with X-Ray
    - API Gateway event parsing
    """
    return app.resolve(event, context)
