"""
Tenant analytics and reporting service
Implements tenant-level metrics aggregation and dashboard data endpoints
"""
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import boto3
from botocore.exceptions import ClientError
from aws_lambda_powertools import Logger

from backend.lambda_functions.shared.config import config

logger = Logger()


class TenantAnalyticsService:
    """Service for tenant-level analytics and reporting"""
    
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb', region_name=config.AWS_REGION)
        self.cloudwatch = boto3.client('logs', region_name=config.AWS_REGION)
        self.catalog_table = self.dynamodb.Table(config.DYNAMODB_CATALOG_TABLE)
    
    def get_tenant_metrics(
        self, 
        tenant_id: str, 
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """
        Get aggregated metrics for a tenant within a time range
        
        Args:
            tenant_id: Tenant identifier
            start_time: Start of time range
            end_time: End of time range
            
        Returns:
            Dict with aggregated metrics
        """
        try:
            # Query catalog entries for the tenant within time range
            response = self.catalog_table.query(
                IndexName='tenant_id-index',
                KeyConditionExpression='tenant_id = :tenant_id',
                FilterExpression='created_at BETWEEN :start_time AND :end_time',
                ExpressionAttributeValues={
                    ':tenant_id': tenant_id,
                    ':start_time': start_time.isoformat(),
                    ':end_time': end_time.isoformat()
                }
            )
            
            items = response.get('Items', [])
            
            # Calculate metrics
            total_entries = len(items)
            completed_entries = sum(
                1 for item in items 
                if item.get('submission_status') == 'completed'
            )
            failed_entries = sum(
                1 for item in items 
                if item.get('submission_status') == 'failed'
            )
            in_progress_entries = total_entries - completed_entries - failed_entries
            
            # Calculate average processing time for completed entries
            processing_times = []
            for item in items:
                if item.get('submission_status') == 'completed':
                    created_at = datetime.fromisoformat(item.get('created_at', ''))
                    completed_at = datetime.fromisoformat(item.get('completed_at', ''))
                    processing_time = (completed_at - created_at).total_seconds()
                    processing_times.append(processing_time)
            
            avg_processing_time = (
                sum(processing_times) / len(processing_times) 
                if processing_times else 0
            )
            
            # Calculate success rate
            success_rate = (
                (completed_entries / total_entries * 100) 
                if total_entries > 0 else 0
            )
            
            return {
                'tenant_id': tenant_id,
                'time_range': {
                    'start': start_time.isoformat(),
                    'end': end_time.isoformat()
                },
                'metrics': {
                    'total_entries': total_entries,
                    'completed_entries': completed_entries,
                    'failed_entries': failed_entries,
                    'in_progress_entries': in_progress_entries,
                    'success_rate': round(success_rate, 2),
                    'avg_processing_time_seconds': round(avg_processing_time, 2)
                }
            }
            
        except ClientError as e:
            logger.error(f"Error fetching tenant metrics: {str(e)}", exc_info=True)
            raise
    
    def get_tenant_daily_metrics(
        self, 
        tenant_id: str, 
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get daily metrics for a tenant over the last N days
        
        Args:
            tenant_id: Tenant identifier
            days: Number of days to look back
            
        Returns:
            Dict with daily metrics
        """
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=days)
            
            # Query catalog entries
            response = self.catalog_table.query(
                IndexName='tenant_id-index',
                KeyConditionExpression='tenant_id = :tenant_id',
                FilterExpression='created_at BETWEEN :start_time AND :end_time',
                ExpressionAttributeValues={
                    ':tenant_id': tenant_id,
                    ':start_time': start_time.isoformat(),
                    ':end_time': end_time.isoformat()
                }
            )
            
            items = response.get('Items', [])
            
            # Group by day
            daily_metrics = {}
            for item in items:
                created_at = datetime.fromisoformat(item.get('created_at', ''))
                day_key = created_at.strftime('%Y-%m-%d')
                
                if day_key not in daily_metrics:
                    daily_metrics[day_key] = {
                        'date': day_key,
                        'total': 0,
                        'completed': 0,
                        'failed': 0,
                        'in_progress': 0
                    }
                
                daily_metrics[day_key]['total'] += 1
                
                status = item.get('submission_status', 'pending')
                if status == 'completed':
                    daily_metrics[day_key]['completed'] += 1
                elif status == 'failed':
                    daily_metrics[day_key]['failed'] += 1
                else:
                    daily_metrics[day_key]['in_progress'] += 1
            
            # Convert to list and sort by date
            daily_list = sorted(daily_metrics.values(), key=lambda x: x['date'])
            
            return {
                'tenant_id': tenant_id,
                'days': days,
                'daily_metrics': daily_list
            }
            
        except ClientError as e:
            logger.error(f"Error fetching daily metrics: {str(e)}", exc_info=True)
            raise
    
    def get_tenant_language_distribution(self, tenant_id: str) -> Dict[str, Any]:
        """
        Get language distribution for a tenant's catalog entries
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Dict with language distribution
        """
        try:
            # Query all catalog entries for the tenant
            response = self.catalog_table.query(
                IndexName='tenant_id-index',
                KeyConditionExpression='tenant_id = :tenant_id',
                ExpressionAttributeValues={
                    ':tenant_id': tenant_id
                }
            )
            
            items = response.get('Items', [])
            
            # Count by language
            language_counts = {}
            for item in items:
                language = item.get('language', 'unknown')
                language_counts[language] = language_counts.get(language, 0) + 1
            
            # Convert to list format
            distribution = [
                {'language': lang, 'count': count}
                for lang, count in language_counts.items()
            ]
            
            # Sort by count descending
            distribution.sort(key=lambda x: x['count'], reverse=True)
            
            return {
                'tenant_id': tenant_id,
                'total_entries': len(items),
                'language_distribution': distribution
            }
            
        except ClientError as e:
            logger.error(f"Error fetching language distribution: {str(e)}", exc_info=True)
            raise
    
    def get_tenant_category_distribution(self, tenant_id: str) -> Dict[str, Any]:
        """
        Get product category distribution for a tenant
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Dict with category distribution
        """
        try:
            # Query all catalog entries for the tenant
            response = self.catalog_table.query(
                IndexName='tenant_id-index',
                KeyConditionExpression='tenant_id = :tenant_id',
                ExpressionAttributeValues={
                    ':tenant_id': tenant_id
                }
            )
            
            items = response.get('Items', [])
            
            # Count by category
            category_counts = {}
            for item in items:
                extraction_result = item.get('extraction_result', {})
                if isinstance(extraction_result, str):
                    try:
                        extraction_result = json.loads(extraction_result)
                    except json.JSONDecodeError:
                        extraction_result = {}
                
                category = extraction_result.get('category', 'unknown')
                category_counts[category] = category_counts.get(category, 0) + 1
            
            # Convert to list format
            distribution = [
                {'category': cat, 'count': count}
                for cat, count in category_counts.items()
            ]
            
            # Sort by count descending
            distribution.sort(key=lambda x: x['count'], reverse=True)
            
            return {
                'tenant_id': tenant_id,
                'total_entries': len(items),
                'category_distribution': distribution
            }
            
        except ClientError as e:
            logger.error(f"Error fetching category distribution: {str(e)}", exc_info=True)
            raise
    
    def get_tenant_error_analysis(
        self, 
        tenant_id: str,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Get error analysis for a tenant's failed entries
        
        Args:
            tenant_id: Tenant identifier
            days: Number of days to look back
            
        Returns:
            Dict with error analysis
        """
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=days)
            
            # Query failed entries
            response = self.catalog_table.query(
                IndexName='tenant_id-index',
                KeyConditionExpression='tenant_id = :tenant_id',
                FilterExpression='submission_status = :failed AND created_at BETWEEN :start_time AND :end_time',
                ExpressionAttributeValues={
                    ':tenant_id': tenant_id,
                    ':failed': 'failed',
                    ':start_time': start_time.isoformat(),
                    ':end_time': end_time.isoformat()
                }
            )
            
            items = response.get('Items', [])
            
            # Categorize errors
            error_categories = {}
            for item in items:
                error_details = item.get('error_details', {})
                if isinstance(error_details, str):
                    try:
                        error_details = json.loads(error_details)
                    except json.JSONDecodeError:
                        error_details = {}
                
                error_type = error_details.get('type', 'unknown')
                error_categories[error_type] = error_categories.get(error_type, 0) + 1
            
            # Convert to list format
            error_list = [
                {'error_type': error_type, 'count': count}
                for error_type, count in error_categories.items()
            ]
            
            # Sort by count descending
            error_list.sort(key=lambda x: x['count'], reverse=True)
            
            return {
                'tenant_id': tenant_id,
                'time_range': {
                    'start': start_time.isoformat(),
                    'end': end_time.isoformat()
                },
                'total_errors': len(items),
                'error_distribution': error_list
            }
            
        except ClientError as e:
            logger.error(f"Error fetching error analysis: {str(e)}", exc_info=True)
            raise
    
    def get_tenant_dashboard_data(self, tenant_id: str) -> Dict[str, Any]:
        """
        Get comprehensive dashboard data for a tenant
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Dict with all dashboard metrics
        """
        try:
            # Get metrics for last 30 days
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=30)
            
            overall_metrics = self.get_tenant_metrics(tenant_id, start_time, end_time)
            daily_metrics = self.get_tenant_daily_metrics(tenant_id, days=30)
            language_dist = self.get_tenant_language_distribution(tenant_id)
            category_dist = self.get_tenant_category_distribution(tenant_id)
            error_analysis = self.get_tenant_error_analysis(tenant_id, days=7)
            
            return {
                'tenant_id': tenant_id,
                'generated_at': datetime.utcnow().isoformat(),
                'overall_metrics': overall_metrics['metrics'],
                'daily_metrics': daily_metrics['daily_metrics'],
                'language_distribution': language_dist['language_distribution'],
                'category_distribution': category_dist['category_distribution'],
                'error_analysis': error_analysis
            }
            
        except Exception as e:
            logger.error(f"Error generating dashboard data: {str(e)}", exc_info=True)
            raise
    
    def query_cloudwatch_insights(
        self, 
        tenant_id: str,
        query: str,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """
        Execute CloudWatch Insights query for tenant-specific logs
        
        Args:
            tenant_id: Tenant identifier
            query: CloudWatch Insights query
            start_time: Start of time range
            end_time: End of time range
            
        Returns:
            Dict with query results
        """
        try:
            # Add tenant_id filter to query
            tenant_query = f"{query} | filter tenant_id = '{tenant_id}'"
            
            # Start query
            response = self.cloudwatch.start_query(
                logGroupName='/aws/lambda/catalog-processing',
                startTime=int(start_time.timestamp()),
                endTime=int(end_time.timestamp()),
                queryString=tenant_query
            )
            
            query_id = response['queryId']
            
            # Wait for query to complete (simplified - in production use polling)
            import time
            time.sleep(2)
            
            # Get results
            results = self.cloudwatch.get_query_results(queryId=query_id)
            
            return {
                'tenant_id': tenant_id,
                'query_id': query_id,
                'status': results['status'],
                'results': results.get('results', [])
            }
            
        except ClientError as e:
            logger.error(f"Error executing CloudWatch query: {str(e)}", exc_info=True)
            raise


# Singleton instance
tenant_analytics_service = TenantAnalyticsService()
