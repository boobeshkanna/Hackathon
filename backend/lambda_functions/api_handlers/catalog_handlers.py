"""
Catalog API Handlers
Handles catalog review and publish operations for the mobile app

Requirements: 8.1, 9.1
"""
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import boto3
from botocore.exceptions import ClientError

from backend.models.catalog import (
    CatalogProcessingRecord,
    ONDCCatalogItem,
    ProcessingStatus
)
from backend.services.ondc_gateway.gateway import ONDCGateway
from backend.services.ondc_gateway.schema_mapper import map_to_beckn_item
from backend.models.catalog import ExtractedAttributes

logger = logging.getLogger(__name__)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
catalog_table = dynamodb.Table('CatalogProcessingRecords')

# Initialize ONDC Gateway
ondc_gateway = ONDCGateway()


def get_catalog_by_tracking_id(tracking_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch catalog data by tracking ID from DynamoDB
    
    Args:
        tracking_id: Unique tracking identifier
        
    Returns:
        Dict containing catalog item data or None if not found
        
    Requirements: 8.1
    """
    try:
        response = catalog_table.get_item(Key={'tracking_id': tracking_id})
        
        if 'Item' not in response:
            logger.warning(f"Catalog not found for tracking_id: {tracking_id}")
            return None
        
        record = response['Item']
        
        # Check if extraction is completed
        if record.get('extraction_status') != ProcessingStatus.COMPLETED.value:
            logger.warning(f"Catalog extraction not completed for tracking_id: {tracking_id}")
            return None
        
        # Build catalog item from extracted attributes
        extracted_data = record.get('extraction_result', {})
        image_urls = []
        
        # Get image URLs from vision result
        if 'vision_result' in record:
            vision_result = record['vision_result']
            if 'processed_images' in vision_result:
                image_urls = vision_result['processed_images']
        
        # Convert extracted attributes to ExtractedAttributes model
        extracted = ExtractedAttributes(**extracted_data)
        
        # Map to ONDC catalog item
        ondc_item = map_to_beckn_item(extracted, image_urls)
        
        # Build response with additional metadata
        catalog_item = {
            'itemId': ondc_item.id,
            'descriptor': {
                'name': ondc_item.descriptor.name,
                'shortDesc': ondc_item.descriptor.short_desc,
                'longDesc': ondc_item.descriptor.long_desc,
                'images': ondc_item.descriptor.images,
            },
            'price': {
                'currency': ondc_item.price.currency,
                'value': ondc_item.price.value,
            },
            'categoryId': ondc_item.category_id,
            'tags': ondc_item.tags,
            'trackingId': tracking_id,
            'tenantId': record.get('tenant_id'),
            'artisanId': record.get('artisan_id'),
            'createdAt': int(datetime.fromisoformat(record['created_at']).timestamp() * 1000),
            'updatedAt': int(datetime.fromisoformat(record['updated_at']).timestamp() * 1000),
        }
        
        # Add CSIs if available
        if extracted.csis:
            catalog_item['csis'] = [
                {
                    'vernacularTerm': csi.vernacular_term,
                    'transliteration': csi.transliteration,
                    'englishContext': csi.english_context,
                    'culturalSignificance': csi.cultural_significance,
                }
                for csi in extracted.csis
            ]
        
        return catalog_item
        
    except ClientError as e:
        logger.error(f"DynamoDB error fetching catalog: {e}")
        return None
    except Exception as e:
        logger.error(f"Error fetching catalog: {e}")
        return None


def publish_catalog_to_ondc(tracking_id: str, catalog_item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Publish catalog item to ONDC network
    
    Args:
        tracking_id: Unique tracking identifier
        catalog_item: Catalog item data to publish
        
    Returns:
        Dict with success status and ONDC catalog ID
        
    Requirements: 9.1
    """
    try:
        # Reconstruct ONDCCatalogItem from dict
        ondc_item = ONDCCatalogItem(
            id=catalog_item['itemId'],
            descriptor=catalog_item['descriptor'],
            price=catalog_item['price'],
            category_id=catalog_item['categoryId'],
            tags=catalog_item.get('tags', {}),
        )
        
        # Submit to ONDC Gateway
        result = ondc_gateway.submit_catalog_item(ondc_item)
        
        if result.get('success'):
            # Update DynamoDB record
            catalog_table.update_item(
                Key={'tracking_id': tracking_id},
                UpdateExpression='SET submission_status = :status, ondc_catalog_id = :catalog_id, completed_at = :completed_at',
                ExpressionAttributeValues={
                    ':status': ProcessingStatus.COMPLETED.value,
                    ':catalog_id': result['catalog_id'],
                    ':completed_at': datetime.utcnow().isoformat(),
                }
            )
            
            return {
                'success': True,
                'ondcCatalogId': result['catalog_id'],
                'message': 'Successfully published to ONDC network',
            }
        else:
            # Update with failure status
            catalog_table.update_item(
                Key={'tracking_id': tracking_id},
                UpdateExpression='SET submission_status = :status, error_details = :error',
                ExpressionAttributeValues={
                    ':status': ProcessingStatus.FAILED.value,
                    ':error': {'message': result.get('message', 'Unknown error')},
                }
            )
            
            return {
                'success': False,
                'message': result.get('message', 'Failed to publish to ONDC'),
                'errors': result.get('errors', []),
            }
            
    except Exception as e:
        logger.error(f"Error publishing catalog: {e}")
        return {
            'success': False,
            'message': f'Internal error: {str(e)}',
        }


def handle_get_catalog(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for GET /catalog/{trackingId}
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response
    """
    try:
        # Extract tracking ID from path parameters
        tracking_id = event['pathParameters']['trackingId']
        
        # Fetch catalog data
        catalog_item = get_catalog_by_tracking_id(tracking_id)
        
        if not catalog_item:
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                },
                'body': json.dumps({
                    'error': 'Catalog not found',
                    'message': f'No catalog found for tracking ID: {tracking_id}',
                })
            }
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
            },
            'body': json.dumps({
                'catalogItem': catalog_item,
            })
        }
        
    except Exception as e:
        logger.error(f"Error in handle_get_catalog: {e}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
            },
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e),
            })
        }


def handle_publish_catalog(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for POST /catalog/publish
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response
    """
    try:
        # Parse request body
        body = json.loads(event['body'])
        tracking_id = body['trackingId']
        catalog_item = body['catalogItem']
        
        # Publish to ONDC
        result = publish_catalog_to_ondc(tracking_id, catalog_item)
        
        status_code = 200 if result['success'] else 400
        
        return {
            'statusCode': status_code,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
            },
            'body': json.dumps(result)
        }
        
    except KeyError as e:
        logger.error(f"Missing required field: {e}")
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
            },
            'body': json.dumps({
                'error': 'Bad request',
                'message': f'Missing required field: {str(e)}',
            })
        }
    except Exception as e:
        logger.error(f"Error in handle_publish_catalog: {e}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
            },
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e),
            })
        }
