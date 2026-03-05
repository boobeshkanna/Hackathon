"""
AWS X-Ray Distributed Tracing Service

Provides utilities for instrumenting Lambda functions, API Gateway, SQS, 
Sagemaker, and Bedrock calls with X-Ray tracing.

Requirements: 15.4
"""
import logging
import os
from typing import Dict, Any, Optional, Callable
from functools import wraps
import boto3
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all

logger = logging.getLogger(__name__)

# Patch AWS SDK clients for automatic X-Ray tracing
# This instruments boto3 calls to S3, DynamoDB, SQS, etc.
try:
    patch_all()
    logger.info("X-Ray SDK patched AWS services successfully")
except Exception as e:
    logger.warning(f"Failed to patch AWS services with X-Ray: {e}")


class TracingService:
    """Service for managing X-Ray distributed tracing"""
    
    def __init__(self, service_name: str = 'VernacularArtisanCatalog'):
        """
        Initialize tracing service
        
        Args:
            service_name: Name of the service for X-Ray segments
        """
        self.service_name = service_name
        
        # Configure X-Ray recorder
        xray_recorder.configure(
            service=service_name,
            sampling=True,
            context_missing='LOG_ERROR'
        )
    
    def trace_subsegment(self, name: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Decorator to create X-Ray subsegment for a function
        
        Args:
            name: Name of the subsegment
            metadata: Optional metadata to attach to subsegment
            
        Usage:
            @trace_subsegment('sagemaker_call')
            def call_sagemaker():
                ...
                
        Requirements: 15.4
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    with xray_recorder.in_subsegment(name) as subsegment:
                        # Add metadata
                        if metadata:
                            for key, value in metadata.items():
                                subsegment.put_metadata(key, value)
                        
                        # Add annotations for filtering
                        if 'tracking_id' in kwargs:
                            subsegment.put_annotation('tracking_id', kwargs['tracking_id'])
                        if 'tenant_id' in kwargs:
                            subsegment.put_annotation('tenant_id', kwargs['tenant_id'])
                        
                        # Execute function
                        result = func(*args, **kwargs)
                        
                        # Mark as successful
                        subsegment.put_annotation('status', 'success')
                        
                        return result
                        
                except Exception as e:
                    # Mark as failed and add error details
                    try:
                        subsegment = xray_recorder.current_subsegment()
                        if subsegment:
                            subsegment.put_annotation('status', 'error')
                            subsegment.put_annotation('error_type', type(e).__name__)
                            subsegment.put_metadata('error_message', str(e))
                    except:
                        pass
                    raise
            
            return wrapper
        return decorator
    
    def add_trace_metadata(self, key: str, value: Any):
        """
        Add metadata to current X-Ray segment
        
        Args:
            key: Metadata key
            value: Metadata value
        """
        try:
            segment = xray_recorder.current_segment()
            if segment:
                segment.put_metadata(key, value)
        except Exception as e:
            logger.debug(f"Failed to add trace metadata: {e}")
    
    def add_trace_annotation(self, key: str, value: str):
        """
        Add annotation to current X-Ray segment (indexed for filtering)
        
        Args:
            key: Annotation key
            value: Annotation value (must be string, number, or boolean)
        """
        try:
            segment = xray_recorder.current_segment()
            if segment:
                segment.put_annotation(key, value)
        except Exception as e:
            logger.debug(f"Failed to add trace annotation: {e}")
    
    def trace_sagemaker_call(
        self,
        endpoint_name: str,
        tracking_id: Optional[str] = None,
        tenant_id: Optional[str] = None
    ):
        """
        Create subsegment for Sagemaker endpoint invocation
        
        Args:
            endpoint_name: Sagemaker endpoint name
            tracking_id: Optional tracking ID
            tenant_id: Optional tenant ID
            
        Requirements: 15.4
        """
        try:
            subsegment = xray_recorder.begin_subsegment('sagemaker_invoke')
            subsegment.put_annotation('endpoint_name', endpoint_name)
            if tracking_id:
                subsegment.put_annotation('tracking_id', tracking_id)
            if tenant_id:
                subsegment.put_annotation('tenant_id', tenant_id)
            return subsegment
        except Exception as e:
            logger.debug(f"Failed to create Sagemaker subsegment: {e}")
            return None
    
    def trace_bedrock_call(
        self,
        model_id: str,
        operation: str,
        tracking_id: Optional[str] = None,
        tenant_id: Optional[str] = None
    ):
        """
        Create subsegment for Bedrock model invocation
        
        Args:
            model_id: Bedrock model ID
            operation: Operation name (e.g., 'attribute_extraction', 'transcreation')
            tracking_id: Optional tracking ID
            tenant_id: Optional tenant ID
            
        Requirements: 15.4
        """
        try:
            subsegment = xray_recorder.begin_subsegment(f'bedrock_{operation}')
            subsegment.put_annotation('model_id', model_id)
            subsegment.put_annotation('operation', operation)
            if tracking_id:
                subsegment.put_annotation('tracking_id', tracking_id)
            if tenant_id:
                subsegment.put_annotation('tenant_id', tenant_id)
            return subsegment
        except Exception as e:
            logger.debug(f"Failed to create Bedrock subsegment: {e}")
            return None
    
    def trace_ondc_call(
        self,
        operation: str,
        tracking_id: Optional[str] = None,
        tenant_id: Optional[str] = None
    ):
        """
        Create subsegment for ONDC API call
        
        Args:
            operation: Operation name (e.g., 'submit_catalog', 'update_catalog')
            tracking_id: Optional tracking ID
            tenant_id: Optional tenant ID
            
        Requirements: 15.4
        """
        try:
            subsegment = xray_recorder.begin_subsegment(f'ondc_{operation}')
            subsegment.put_annotation('operation', operation)
            if tracking_id:
                subsegment.put_annotation('tracking_id', tracking_id)
            if tenant_id:
                subsegment.put_annotation('tenant_id', tenant_id)
            return subsegment
        except Exception as e:
            logger.debug(f"Failed to create ONDC subsegment: {e}")
            return None
    
    def end_subsegment(self, subsegment):
        """
        End a subsegment
        
        Args:
            subsegment: Subsegment to end
        """
        try:
            if subsegment:
                xray_recorder.end_subsegment()
        except Exception as e:
            logger.debug(f"Failed to end subsegment: {e}")
    
    def propagate_trace_context(self) -> Dict[str, str]:
        """
        Get trace context for propagation across service boundaries
        
        Returns:
            Dict with trace context headers
            
        Requirements: 15.4
        """
        try:
            segment = xray_recorder.current_segment()
            if segment:
                trace_header = segment.get_trace_header()
                return {
                    'X-Amzn-Trace-Id': trace_header
                }
        except Exception as e:
            logger.debug(f"Failed to get trace context: {e}")
        
        return {}
    
    def inject_trace_context(self, headers: Dict[str, str]):
        """
        Inject trace context from headers
        
        Args:
            headers: HTTP headers containing trace context
            
        Requirements: 15.4
        """
        try:
            trace_header = headers.get('X-Amzn-Trace-Id')
            if trace_header:
                xray_recorder.set_trace_entity(trace_header)
        except Exception as e:
            logger.debug(f"Failed to inject trace context: {e}")


# Singleton instance
_tracing_service: Optional[TracingService] = None


def get_tracing_service(service_name: str = 'VernacularArtisanCatalog') -> TracingService:
    """Get or create tracing service singleton"""
    global _tracing_service
    if _tracing_service is None:
        _tracing_service = TracingService(service_name=service_name)
    return _tracing_service


# Convenience decorators
def trace_lambda_handler(func: Callable) -> Callable:
    """
    Decorator for Lambda handler functions to enable X-Ray tracing
    
    Usage:
        @trace_lambda_handler
        def lambda_handler(event, context):
            ...
    """
    @wraps(func)
    def wrapper(event, context):
        tracing = get_tracing_service()
        
        # Add Lambda context to trace
        tracing.add_trace_annotation('function_name', context.function_name)
        tracing.add_trace_annotation('request_id', context.request_id)
        
        # Add event metadata
        if 'Records' in event:
            tracing.add_trace_metadata('record_count', len(event['Records']))
        
        return func(event, context)
    
    return wrapper


def trace_operation(operation_name: str):
    """
    Decorator to trace a specific operation
    
    Usage:
        @trace_operation('process_catalog_entry')
        def process_entry(tracking_id, ...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            tracing = get_tracing_service()
            
            try:
                with xray_recorder.in_subsegment(operation_name) as subsegment:
                    # Add tracking_id if present
                    if 'tracking_id' in kwargs:
                        subsegment.put_annotation('tracking_id', kwargs['tracking_id'])
                    if 'tenant_id' in kwargs:
                        subsegment.put_annotation('tenant_id', kwargs['tenant_id'])
                    
                    result = func(*args, **kwargs)
                    subsegment.put_annotation('status', 'success')
                    return result
                    
            except Exception as e:
                try:
                    subsegment = xray_recorder.current_subsegment()
                    if subsegment:
                        subsegment.put_annotation('status', 'error')
                        subsegment.put_annotation('error_type', type(e).__name__)
                except:
                    pass
                raise
        
        return wrapper
    return decorator
