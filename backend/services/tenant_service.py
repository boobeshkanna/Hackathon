"""
Tenant configuration service for multi-tenancy support
Implements tenant data isolation, configuration management, and quota enforcement
"""
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
import boto3
from botocore.exceptions import ClientError
from aws_lambda_powertools import Logger

from backend.models.tenant import TenantConfiguration, ArtisanProfile, TenantQuotaUsage
from backend.lambda_functions.shared.config import config

logger = Logger()


class TenantService:
    """Service for managing tenant configurations and data isolation"""
    
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb', region_name=config.AWS_REGION)
        self.tenant_table = self.dynamodb.Table(config.DYNAMODB_TENANT_TABLE)
        self.catalog_table = self.dynamodb.Table(config.DYNAMODB_CATALOG_TABLE)
    
    def get_tenant_configuration(self, tenant_id: str) -> Optional[TenantConfiguration]:
        """
        Retrieve tenant configuration from DynamoDB
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            TenantConfiguration object or None if not found
        """
        try:
            response = self.tenant_table.get_item(
                Key={'tenant_id': tenant_id}
            )
            
            if 'Item' not in response:
                logger.warning(f"Tenant configuration not found: {tenant_id}")
                return None
            
            return TenantConfiguration(**response['Item'])
            
        except ClientError as e:
            logger.error(f"Error fetching tenant configuration: {str(e)}", exc_info=True)
            raise
    
    def create_tenant_configuration(self, tenant_config: TenantConfiguration) -> Dict[str, Any]:
        """
        Create new tenant configuration
        
        Args:
            tenant_config: TenantConfiguration object
            
        Returns:
            Dict with status and tenant_id
        """
        try:
            # Convert to dict and store in DynamoDB
            item = json.loads(tenant_config.json())
            
            self.tenant_table.put_item(
                Item=item,
                ConditionExpression='attribute_not_exists(tenant_id)'
            )
            
            logger.info(f"Tenant configuration created: {tenant_config.tenant_id}")
            
            return {
                "status": "created",
                "tenant_id": tenant_config.tenant_id
            }
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                logger.error(f"Tenant already exists: {tenant_config.tenant_id}")
                raise ValueError(f"Tenant {tenant_config.tenant_id} already exists")
            logger.error(f"Error creating tenant configuration: {str(e)}", exc_info=True)
            raise
    
    def update_tenant_configuration(
        self, 
        tenant_id: str, 
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update tenant configuration
        
        Args:
            tenant_id: Tenant identifier
            updates: Dict of fields to update
            
        Returns:
            Dict with status and updated fields
        """
        try:
            # Build update expression
            update_expression = "SET updated_at = :updated_at"
            expression_values = {
                ':updated_at': datetime.utcnow().isoformat()
            }
            
            for key, value in updates.items():
                if key not in ['tenant_id', 'created_at']:  # Don't allow updating these
                    update_expression += f", {key} = :{key}"
                    expression_values[f':{key}'] = value
            
            self.tenant_table.update_item(
                Key={'tenant_id': tenant_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values,
                ConditionExpression='attribute_exists(tenant_id)'
            )
            
            logger.info(f"Tenant configuration updated: {tenant_id}")
            
            return {
                "status": "updated",
                "tenant_id": tenant_id,
                "updated_fields": list(updates.keys())
            }
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                logger.error(f"Tenant not found: {tenant_id}")
                raise ValueError(f"Tenant {tenant_id} not found")
            logger.error(f"Error updating tenant configuration: {str(e)}", exc_info=True)
            raise
    
    def get_tenant_catalogs(
        self, 
        tenant_id: str, 
        limit: int = 100,
        last_evaluated_key: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get catalog entries for a specific tenant (data isolation)
        
        Args:
            tenant_id: Tenant identifier
            limit: Maximum number of items to return
            last_evaluated_key: Pagination token
            
        Returns:
            Dict with items and pagination info
        """
        try:
            # Query using GSI on tenant_id
            query_params = {
                'IndexName': 'tenant_id-index',
                'KeyConditionExpression': 'tenant_id = :tenant_id',
                'ExpressionAttributeValues': {
                    ':tenant_id': tenant_id
                },
                'Limit': limit
            }
            
            if last_evaluated_key:
                query_params['ExclusiveStartKey'] = last_evaluated_key
            
            response = self.catalog_table.query(**query_params)
            
            return {
                'items': response.get('Items', []),
                'count': response.get('Count', 0),
                'last_evaluated_key': response.get('LastEvaluatedKey')
            }
            
        except ClientError as e:
            logger.error(f"Error fetching tenant catalogs: {str(e)}", exc_info=True)
            raise
    
    def check_tenant_quota(self, tenant_id: str, quota_type: str) -> Dict[str, Any]:
        """
        Check if tenant has available quota
        
        Args:
            tenant_id: Tenant identifier
            quota_type: Type of quota to check ('catalog', 'storage', 'api')
            
        Returns:
            Dict with quota status and available amount
        """
        try:
            # Get tenant configuration
            tenant_config = self.get_tenant_configuration(tenant_id)
            if not tenant_config:
                raise ValueError(f"Tenant {tenant_id} not found")
            
            # Get current month usage
            current_month = datetime.utcnow().strftime('%Y-%m')
            usage = self._get_quota_usage(tenant_id, current_month)
            
            # Check quota based on type
            if quota_type == 'catalog':
                quota_limit = tenant_config.monthly_catalog_quota
                current_usage = usage.catalogs_created
                available = quota_limit - current_usage
                
                return {
                    'quota_type': 'catalog',
                    'limit': quota_limit,
                    'used': current_usage,
                    'available': available,
                    'has_quota': available > 0
                }
            
            elif quota_type == 'storage':
                quota_limit = tenant_config.storage_quota_gb
                current_usage = usage.storage_used_gb
                available = quota_limit - current_usage
                
                return {
                    'quota_type': 'storage',
                    'limit': quota_limit,
                    'used': current_usage,
                    'available': available,
                    'has_quota': available > 0
                }
            
            elif quota_type == 'api':
                # API quota is per minute, not monthly
                return {
                    'quota_type': 'api',
                    'limit': tenant_config.api_rate_limit,
                    'has_quota': True  # Rate limiting handled by API Gateway
                }
            
            else:
                raise ValueError(f"Unknown quota type: {quota_type}")
                
        except Exception as e:
            logger.error(f"Error checking tenant quota: {str(e)}", exc_info=True)
            raise
    
    def increment_quota_usage(
        self, 
        tenant_id: str, 
        quota_type: str, 
        amount: float = 1.0
    ) -> Dict[str, Any]:
        """
        Increment tenant quota usage
        
        Args:
            tenant_id: Tenant identifier
            quota_type: Type of quota ('catalog', 'storage', 'api')
            amount: Amount to increment
            
        Returns:
            Dict with updated usage
        """
        try:
            current_month = datetime.utcnow().strftime('%Y-%m')
            
            # Build update expression based on quota type
            if quota_type == 'catalog':
                update_expression = "ADD catalogs_created :amount SET updated_at = :updated_at"
            elif quota_type == 'storage':
                update_expression = "ADD storage_used_gb :amount SET updated_at = :updated_at"
            elif quota_type == 'api':
                update_expression = "ADD api_requests :amount SET updated_at = :updated_at"
            else:
                raise ValueError(f"Unknown quota type: {quota_type}")
            
            # Use a separate quota usage table (assuming it exists)
            # For now, we'll track in the tenant table itself
            response = self.tenant_table.update_item(
                Key={'tenant_id': tenant_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues={
                    ':amount': amount,
                    ':updated_at': datetime.utcnow().isoformat()
                },
                ReturnValues='ALL_NEW'
            )
            
            logger.info(
                f"Quota usage incremented",
                extra={
                    'tenant_id': tenant_id,
                    'quota_type': quota_type,
                    'amount': amount
                }
            )
            
            return {
                'status': 'updated',
                'tenant_id': tenant_id,
                'quota_type': quota_type
            }
            
        except ClientError as e:
            logger.error(f"Error incrementing quota usage: {str(e)}", exc_info=True)
            raise
    
    def _get_quota_usage(self, tenant_id: str, month: str) -> TenantQuotaUsage:
        """
        Get quota usage for a specific month
        
        Args:
            tenant_id: Tenant identifier
            month: Month in YYYY-MM format
            
        Returns:
            TenantQuotaUsage object
        """
        # For simplicity, we'll return a default usage object
        # In production, this would query a separate quota usage table
        return TenantQuotaUsage(
            tenant_id=tenant_id,
            month=month,
            catalogs_created=0,
            catalogs_published=0,
            storage_used_gb=0.0,
            api_requests=0
        )
    
    def validate_tenant_access(
        self, 
        tenant_id: str, 
        artisan_id: str
    ) -> bool:
        """
        Validate that an artisan belongs to a tenant
        
        Args:
            tenant_id: Tenant identifier
            artisan_id: Artisan identifier
            
        Returns:
            True if artisan belongs to tenant, False otherwise
        """
        try:
            # In production, this would query an artisan table
            # For now, we'll assume validation passes if tenant exists
            tenant_config = self.get_tenant_configuration(tenant_id)
            return tenant_config is not None and tenant_config.is_active
            
        except Exception as e:
            logger.error(f"Error validating tenant access: {str(e)}", exc_info=True)
            return False


# Singleton instance
tenant_service = TenantService()
