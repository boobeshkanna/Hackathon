"""
Tenant analytics API handlers
Implements dashboard data endpoints and reporting queries
"""
import json
from datetime import datetime, timedelta
from typing import Dict, Any
from aws_lambda_powertools import Logger, Tracer

from backend.services.tenant_analytics import tenant_analytics_service

logger = Logger()
tracer = Tracer()


class AnalyticsHandler:
    """Handler for tenant analytics operations"""
    
    @tracer.capture_method
    def get_tenant_dashboard(self, tenant_id: str) -> Dict[str, Any]:
        """
        Get comprehensive dashboard data for a tenant
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Dict with dashboard data
        """
        try:
            dashboard_data = tenant_analytics_service.get_tenant_dashboard_data(tenant_id)
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps(dashboard_data)
            }
            
        except Exception as e:
            logger.error(f"Error fetching dashboard data: {str(e)}", exc_info=True)
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'InternalServerError',
                    'message': 'Failed to fetch dashboard data'
                })
            }
    
    @tracer.capture_method
    def get_tenant_metrics(
        self, 
        tenant_id: str,
        start_date: str = None,
        end_date: str = None
    ) -> Dict[str, Any]:
        """
        Get aggregated metrics for a tenant
        
        Args:
            tenant_id: Tenant identifier
            start_date: Start date (ISO format)
            end_date: End date (ISO format)
            
        Returns:
            Dict with metrics
        """
        try:
            # Parse dates or use defaults
            if start_date:
                start_time = datetime.fromisoformat(start_date)
            else:
                start_time = datetime.utcnow() - timedelta(days=30)
            
            if end_date:
                end_time = datetime.fromisoformat(end_date)
            else:
                end_time = datetime.utcnow()
            
            metrics = tenant_analytics_service.get_tenant_metrics(
                tenant_id=tenant_id,
                start_time=start_time,
                end_time=end_time
            )
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps(metrics)
            }
            
        except ValueError as e:
            logger.error(f"Invalid date format: {str(e)}")
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'ValidationError',
                    'message': 'Invalid date format. Use ISO format (YYYY-MM-DD)'
                })
            }
        except Exception as e:
            logger.error(f"Error fetching metrics: {str(e)}", exc_info=True)
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'InternalServerError',
                    'message': 'Failed to fetch metrics'
                })
            }
    
    @tracer.capture_method
    def get_daily_metrics(self, tenant_id: str, days: int = 30) -> Dict[str, Any]:
        """
        Get daily metrics for a tenant
        
        Args:
            tenant_id: Tenant identifier
            days: Number of days to look back
            
        Returns:
            Dict with daily metrics
        """
        try:
            daily_metrics = tenant_analytics_service.get_tenant_daily_metrics(
                tenant_id=tenant_id,
                days=days
            )
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps(daily_metrics)
            }
            
        except Exception as e:
            logger.error(f"Error fetching daily metrics: {str(e)}", exc_info=True)
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'InternalServerError',
                    'message': 'Failed to fetch daily metrics'
                })
            }
    
    @tracer.capture_method
    def get_language_distribution(self, tenant_id: str) -> Dict[str, Any]:
        """
        Get language distribution for a tenant
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Dict with language distribution
        """
        try:
            distribution = tenant_analytics_service.get_tenant_language_distribution(tenant_id)
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps(distribution)
            }
            
        except Exception as e:
            logger.error(f"Error fetching language distribution: {str(e)}", exc_info=True)
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'InternalServerError',
                    'message': 'Failed to fetch language distribution'
                })
            }
    
    @tracer.capture_method
    def get_category_distribution(self, tenant_id: str) -> Dict[str, Any]:
        """
        Get category distribution for a tenant
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Dict with category distribution
        """
        try:
            distribution = tenant_analytics_service.get_tenant_category_distribution(tenant_id)
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps(distribution)
            }
            
        except Exception as e:
            logger.error(f"Error fetching category distribution: {str(e)}", exc_info=True)
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'InternalServerError',
                    'message': 'Failed to fetch category distribution'
                })
            }
    
    @tracer.capture_method
    def get_error_analysis(self, tenant_id: str, days: int = 7) -> Dict[str, Any]:
        """
        Get error analysis for a tenant
        
        Args:
            tenant_id: Tenant identifier
            days: Number of days to look back
            
        Returns:
            Dict with error analysis
        """
        try:
            error_analysis = tenant_analytics_service.get_tenant_error_analysis(
                tenant_id=tenant_id,
                days=days
            )
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps(error_analysis)
            }
            
        except Exception as e:
            logger.error(f"Error fetching error analysis: {str(e)}", exc_info=True)
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'InternalServerError',
                    'message': 'Failed to fetch error analysis'
                })
            }


# Singleton instance
analytics_handler = AnalyticsHandler()
