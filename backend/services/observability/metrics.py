"""
CloudWatch Metrics Service

Emits custom metrics for queue depth, latency, error rates, and success rates.
Provides per-operation metrics for upload, Sagemaker, Bedrock, and ONDC submission.

Requirements: 15.1, 15.5
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class MetricsService:
    """Service for emitting CloudWatch metrics"""
    
    def __init__(self, namespace: str = 'VernacularArtisanCatalog', region: str = 'us-east-1'):
        """
        Initialize metrics service
        
        Args:
            namespace: CloudWatch namespace for metrics
            region: AWS region
        """
        self.namespace = namespace
        self.cloudwatch = boto3.client('cloudwatch', region_name=region)
        
    def emit_queue_depth(self, queue_name: str, depth: int, tenant_id: Optional[str] = None):
        """
        Emit queue depth metric
        
        Args:
            queue_name: Name of the queue
            depth: Current queue depth
            tenant_id: Optional tenant ID for tenant-specific metrics
            
        Requirements: 15.1
        """
        dimensions = [{'Name': 'QueueName', 'Value': queue_name}]
        if tenant_id:
            dimensions.append({'Name': 'TenantId', 'Value': tenant_id})
        
        self._put_metric(
            metric_name='QueueDepth',
            value=depth,
            unit='Count',
            dimensions=dimensions
        )
    
    def emit_processing_latency(
        self,
        operation: str,
        latency_ms: float,
        tenant_id: Optional[str] = None,
        tracking_id: Optional[str] = None
    ):
        """
        Emit processing latency metric
        
        Args:
            operation: Operation name (upload, sagemaker, bedrock, ondc_submission)
            latency_ms: Latency in milliseconds
            tenant_id: Optional tenant ID
            tracking_id: Optional tracking ID for tracing
            
        Requirements: 15.1
        """
        dimensions = [{'Name': 'Operation', 'Value': operation}]
        if tenant_id:
            dimensions.append({'Name': 'TenantId', 'Value': tenant_id})
        
        self._put_metric(
            metric_name='ProcessingLatency',
            value=latency_ms,
            unit='Milliseconds',
            dimensions=dimensions
        )
        
        logger.info(
            f"Latency metric: operation={operation}, latency={latency_ms}ms, "
            f"tenant_id={tenant_id}, tracking_id={tracking_id}"
        )
    
    def emit_error_rate(
        self,
        operation: str,
        error_count: int = 1,
        tenant_id: Optional[str] = None,
        error_type: Optional[str] = None
    ):
        """
        Emit error rate metric
        
        Args:
            operation: Operation name
            error_count: Number of errors (default 1)
            tenant_id: Optional tenant ID
            error_type: Optional error type for categorization
            
        Requirements: 15.1
        """
        dimensions = [{'Name': 'Operation', 'Value': operation}]
        if tenant_id:
            dimensions.append({'Name': 'TenantId', 'Value': tenant_id})
        if error_type:
            dimensions.append({'Name': 'ErrorType', 'Value': error_type})
        
        self._put_metric(
            metric_name='ErrorCount',
            value=error_count,
            unit='Count',
            dimensions=dimensions
        )
        
        logger.warning(
            f"Error metric: operation={operation}, error_count={error_count}, "
            f"tenant_id={tenant_id}, error_type={error_type}"
        )
    
    def emit_success_rate(
        self,
        operation: str,
        success_count: int = 1,
        tenant_id: Optional[str] = None
    ):
        """
        Emit success rate metric
        
        Args:
            operation: Operation name
            success_count: Number of successes (default 1)
            tenant_id: Optional tenant ID
            
        Requirements: 15.1
        """
        dimensions = [{'Name': 'Operation', 'Value': operation}]
        if tenant_id:
            dimensions.append({'Name': 'TenantId', 'Value': tenant_id})
        
        self._put_metric(
            metric_name='SuccessCount',
            value=success_count,
            unit='Count',
            dimensions=dimensions
        )
        
        logger.info(
            f"Success metric: operation={operation}, success_count={success_count}, "
            f"tenant_id={tenant_id}"
        )
    
    def emit_ondc_submission_status(
        self,
        status: str,
        tenant_id: Optional[str] = None,
        tracking_id: Optional[str] = None
    ):
        """
        Emit ONDC submission status metric
        
        Args:
            status: Submission status (success, failed, retrying)
            tenant_id: Optional tenant ID
            tracking_id: Optional tracking ID
            
        Requirements: 15.1
        """
        dimensions = [
            {'Name': 'Operation', 'Value': 'ondc_submission'},
            {'Name': 'Status', 'Value': status}
        ]
        if tenant_id:
            dimensions.append({'Name': 'TenantId', 'Value': tenant_id})
        
        self._put_metric(
            metric_name='ONDCSubmissionStatus',
            value=1,
            unit='Count',
            dimensions=dimensions
        )
        
        logger.info(
            f"ONDC submission metric: status={status}, tenant_id={tenant_id}, "
            f"tracking_id={tracking_id}"
        )
    
    def emit_cost_metric(
        self,
        operation: str,
        cost_usd: float,
        tenant_id: Optional[str] = None,
        tracking_id: Optional[str] = None
    ):
        """
        Emit cost metric for monitoring per-entry processing costs
        
        Args:
            operation: Operation name (sagemaker, bedrock, total)
            cost_usd: Cost in USD
            tenant_id: Optional tenant ID
            tracking_id: Optional tracking ID
            
        Requirements: 13.5
        """
        dimensions = [{'Name': 'Operation', 'Value': operation}]
        if tenant_id:
            dimensions.append({'Name': 'TenantId', 'Value': tenant_id})
        
        self._put_metric(
            metric_name='ProcessingCost',
            value=cost_usd,
            unit='None',  # USD
            dimensions=dimensions
        )
        
        logger.info(
            f"Cost metric: operation={operation}, cost=${cost_usd:.4f}, "
            f"tenant_id={tenant_id}, tracking_id={tracking_id}"
        )
    
    def _put_metric(
        self,
        metric_name: str,
        value: float,
        unit: str,
        dimensions: list
    ):
        """
        Put metric data to CloudWatch
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            unit: Metric unit
            dimensions: List of dimensions
        """
        try:
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=[
                    {
                        'MetricName': metric_name,
                        'Value': value,
                        'Unit': unit,
                        'Timestamp': datetime.utcnow(),
                        'Dimensions': dimensions
                    }
                ]
            )
        except ClientError as e:
            logger.error(f"Failed to emit metric {metric_name}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error emitting metric {metric_name}: {e}")


# Singleton instance
_metrics_service: Optional[MetricsService] = None


def get_metrics_service(namespace: str = 'VernacularArtisanCatalog', region: str = 'us-east-1') -> MetricsService:
    """Get or create metrics service singleton"""
    global _metrics_service
    if _metrics_service is None:
        _metrics_service = MetricsService(namespace=namespace, region=region)
    return _metrics_service
