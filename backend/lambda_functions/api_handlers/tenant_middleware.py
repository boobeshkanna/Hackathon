"""
Tenant middleware for API Gateway request validation and tenant identification
Implements tenant-level rate limiting and quota enforcement
"""
import json
from typing import Dict, Any, Optional, Callable
from functools import wraps
from aws_lambda_powertools import Logger

from backend.services.tenant_service import tenant_service

logger = Logger()


class TenantMiddleware:
    """Middleware for tenant identification and validation"""
    
    @staticmethod
    def extract_tenant_id(event: Dict[str, Any]) -> Optional[str]:
        """
        Extract tenant_id from API Gateway event
        
        Checks in order:
        1. Request headers (X-Tenant-ID)
        2. Query parameters (tenant_id)
        3. Request body (tenant_id)
        
        Args:
            event: API Gateway event
            
        Returns:
            Tenant ID or None if not found
        """
        # Check headers
        headers = event.get('headers', {})
        tenant_id = headers.get('X-Tenant-ID') or headers.get('x-tenant-id')
        
        if tenant_id:
            return tenant_id
        
        # Check query parameters
        query_params = event.get('queryStringParameters', {})
        if query_params:
            tenant_id = query_params.get('tenant_id')
            if tenant_id:
                return tenant_id
        
        # Check request body
        body = event.get('body')
        if body:
            try:
                body_data = json.loads(body) if isinstance(body, str) else body
                tenant_id = body_data.get('tenant_id')
                if tenant_id:
                    return tenant_id
            except json.JSONDecodeError:
                pass
        
        return None
    
    @staticmethod
    def extract_artisan_id(event: Dict[str, Any]) -> Optional[str]:
        """
        Extract artisan_id from API Gateway event
        
        Args:
            event: API Gateway event
            
        Returns:
            Artisan ID or None if not found
        """
        # Check headers
        headers = event.get('headers', {})
        artisan_id = headers.get('X-Artisan-ID') or headers.get('x-artisan-id')
        
        if artisan_id:
            return artisan_id
        
        # Check query parameters
        query_params = event.get('queryStringParameters', {})
        if query_params:
            artisan_id = query_params.get('artisan_id')
            if artisan_id:
                return artisan_id
        
        # Check request body
        body = event.get('body')
        if body:
            try:
                body_data = json.loads(body) if isinstance(body, str) else body
                artisan_id = body_data.get('artisan_id')
                if artisan_id:
                    return artisan_id
            except json.JSONDecodeError:
                pass
        
        return None
    
    @staticmethod
    def validate_tenant_request(event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate tenant request and extract tenant context
        
        Args:
            event: API Gateway event
            
        Returns:
            Dict with tenant_id, artisan_id, and tenant_config
            
        Raises:
            ValueError: If validation fails
        """
        # Extract tenant_id
        tenant_id = TenantMiddleware.extract_tenant_id(event)
        if not tenant_id:
            raise ValueError("Missing tenant_id in request")
        
        # Extract artisan_id
        artisan_id = TenantMiddleware.extract_artisan_id(event)
        if not artisan_id:
            raise ValueError("Missing artisan_id in request")
        
        # Get tenant configuration
        tenant_config = tenant_service.get_tenant_configuration(tenant_id)
        if not tenant_config:
            raise ValueError(f"Tenant {tenant_id} not found")
        
        # Check if tenant is active
        if not tenant_config.is_active:
            raise ValueError(f"Tenant {tenant_id} is not active")
        
        # Validate artisan belongs to tenant
        if not tenant_service.validate_tenant_access(tenant_id, artisan_id):
            raise ValueError(f"Artisan {artisan_id} does not belong to tenant {tenant_id}")
        
        return {
            'tenant_id': tenant_id,
            'artisan_id': artisan_id,
            'tenant_config': tenant_config
        }
    
    @staticmethod
    def check_quota(tenant_id: str, quota_type: str) -> Dict[str, Any]:
        """
        Check tenant quota availability
        
        Args:
            tenant_id: Tenant identifier
            quota_type: Type of quota to check
            
        Returns:
            Dict with quota status
            
        Raises:
            ValueError: If quota exceeded
        """
        quota_status = tenant_service.check_tenant_quota(tenant_id, quota_type)
        
        if not quota_status.get('has_quota', False):
            raise ValueError(
                f"Quota exceeded for {quota_type}. "
                f"Used: {quota_status.get('used')}/{quota_status.get('limit')}"
            )
        
        return quota_status


def require_tenant(handler: Callable) -> Callable:
    """
    Decorator to require tenant validation for API handlers
    
    Usage:
        @require_tenant
        def my_handler(event, context):
            tenant_context = event['tenant_context']
            tenant_id = tenant_context['tenant_id']
            ...
    """
    @wraps(handler)
    def wrapper(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
        try:
            # Validate tenant request
            tenant_context = TenantMiddleware.validate_tenant_request(event)
            
            # Add tenant context to event
            event['tenant_context'] = tenant_context
            
            # Call the handler
            return handler(event, context)
            
        except ValueError as e:
            logger.error(f"Tenant validation error: {str(e)}")
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'ValidationError',
                    'message': str(e)
                })
            }
        except Exception as e:
            logger.error(f"Unexpected error in tenant middleware: {str(e)}", exc_info=True)
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'InternalServerError',
                    'message': 'An unexpected error occurred'
                })
            }
    
    return wrapper


def require_quota(quota_type: str) -> Callable:
    """
    Decorator to check tenant quota before executing handler
    
    Usage:
        @require_tenant
        @require_quota('catalog')
        def my_handler(event, context):
            ...
    """
    def decorator(handler: Callable) -> Callable:
        @wraps(handler)
        def wrapper(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
            try:
                # Get tenant context (should be set by require_tenant decorator)
                tenant_context = event.get('tenant_context')
                if not tenant_context:
                    raise ValueError("Tenant context not found. Use @require_tenant decorator first.")
                
                tenant_id = tenant_context['tenant_id']
                
                # Check quota
                TenantMiddleware.check_quota(tenant_id, quota_type)
                
                # Call the handler
                result = handler(event, context)
                
                # Increment quota usage on success
                if result.get('statusCode') == 200:
                    tenant_service.increment_quota_usage(tenant_id, quota_type)
                
                return result
                
            except ValueError as e:
                logger.error(f"Quota check error: {str(e)}")
                return {
                    'statusCode': 429,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'error': 'QuotaExceeded',
                        'message': str(e)
                    })
                }
            except Exception as e:
                logger.error(f"Unexpected error in quota middleware: {str(e)}", exc_info=True)
                return {
                    'statusCode': 500,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'error': 'InternalServerError',
                        'message': 'An unexpected error occurred'
                    })
                }
        
        return wrapper
    
    return decorator
