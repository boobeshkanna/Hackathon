"""
Tenant management API handlers
Implements tenant configuration CRUD operations
"""
import json
from typing import Dict, Any
from aws_lambda_powertools import Logger, Tracer

from backend.models.tenant import TenantConfiguration
from backend.services.tenant_service import tenant_service

logger = Logger()
tracer = Tracer()


class TenantHandler:
    """Handler for tenant management operations"""
    
    @tracer.capture_method
    def get_tenant_configuration(self, tenant_id: str) -> Dict[str, Any]:
        """
        Get tenant configuration
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Dict with tenant configuration
        """
        try:
            tenant_config = tenant_service.get_tenant_configuration(tenant_id)
            
            if not tenant_config:
                return {
                    'statusCode': 404,
                    'body': json.dumps({
                        'error': 'NotFound',
                        'message': f'Tenant {tenant_id} not found'
                    })
                }
            
            # Remove sensitive fields
            config_dict = json.loads(tenant_config.json())
            config_dict.pop('ondc_api_key', None)
            
            return {
                'statusCode': 200,
                'body': json.dumps(config_dict)
            }
            
        except Exception as e:
            logger.error(f"Error fetching tenant configuration: {str(e)}", exc_info=True)
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'InternalServerError',
                    'message': 'Failed to fetch tenant configuration'
                })
            }
    
    @tracer.capture_method
    def create_tenant_configuration(self, tenant_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create new tenant configuration
        
        Args:
            tenant_data: Tenant configuration data
            
        Returns:
            Dict with creation status
        """
        try:
            # Validate and create tenant configuration
            tenant_config = TenantConfiguration(**tenant_data)
            result = tenant_service.create_tenant_configuration(tenant_config)
            
            return {
                'statusCode': 201,
                'body': json.dumps(result)
            }
            
        except ValueError as e:
            logger.error(f"Validation error: {str(e)}")
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'ValidationError',
                    'message': str(e)
                })
            }
        except Exception as e:
            logger.error(f"Error creating tenant configuration: {str(e)}", exc_info=True)
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'InternalServerError',
                    'message': 'Failed to create tenant configuration'
                })
            }
    
    @tracer.capture_method
    def update_tenant_configuration(
        self, 
        tenant_id: str, 
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update tenant configuration
        
        Args:
            tenant_id: Tenant identifier
            updates: Fields to update
            
        Returns:
            Dict with update status
        """
        try:
            result = tenant_service.update_tenant_configuration(tenant_id, updates)
            
            return {
                'statusCode': 200,
                'body': json.dumps(result)
            }
            
        except ValueError as e:
            logger.error(f"Validation error: {str(e)}")
            return {
                'statusCode': 404,
                'body': json.dumps({
                    'error': 'NotFound',
                    'message': str(e)
                })
            }
        except Exception as e:
            logger.error(f"Error updating tenant configuration: {str(e)}", exc_info=True)
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'InternalServerError',
                    'message': 'Failed to update tenant configuration'
                })
            }
    
    @tracer.capture_method
    def get_tenant_quota_status(self, tenant_id: str) -> Dict[str, Any]:
        """
        Get tenant quota status
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Dict with quota status for all quota types
        """
        try:
            catalog_quota = tenant_service.check_tenant_quota(tenant_id, 'catalog')
            storage_quota = tenant_service.check_tenant_quota(tenant_id, 'storage')
            api_quota = tenant_service.check_tenant_quota(tenant_id, 'api')
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'tenant_id': tenant_id,
                    'quotas': {
                        'catalog': catalog_quota,
                        'storage': storage_quota,
                        'api': api_quota
                    }
                })
            }
            
        except ValueError as e:
            logger.error(f"Validation error: {str(e)}")
            return {
                'statusCode': 404,
                'body': json.dumps({
                    'error': 'NotFound',
                    'message': str(e)
                })
            }
        except Exception as e:
            logger.error(f"Error fetching quota status: {str(e)}", exc_info=True)
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'InternalServerError',
                    'message': 'Failed to fetch quota status'
                })
            }
    
    @tracer.capture_method
    def get_tenant_catalogs(
        self, 
        tenant_id: str, 
        limit: int = 100,
        last_key: str = None
    ) -> Dict[str, Any]:
        """
        Get catalog entries for a tenant
        
        Args:
            tenant_id: Tenant identifier
            limit: Maximum number of items
            last_key: Pagination token
            
        Returns:
            Dict with catalog entries
        """
        try:
            last_evaluated_key = json.loads(last_key) if last_key else None
            
            result = tenant_service.get_tenant_catalogs(
                tenant_id=tenant_id,
                limit=limit,
                last_evaluated_key=last_evaluated_key
            )
            
            response_body = {
                'tenant_id': tenant_id,
                'items': result['items'],
                'count': result['count']
            }
            
            if result.get('last_evaluated_key'):
                response_body['next_token'] = json.dumps(result['last_evaluated_key'])
            
            return {
                'statusCode': 200,
                'body': json.dumps(response_body)
            }
            
        except Exception as e:
            logger.error(f"Error fetching tenant catalogs: {str(e)}", exc_info=True)
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'InternalServerError',
                    'message': 'Failed to fetch tenant catalogs'
                })
            }


# Singleton instance
tenant_handler = TenantHandler()
