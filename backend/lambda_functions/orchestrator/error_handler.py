"""
Error Handler for Graceful Degradation

Implements error handling strategies for each processing stage with fallback logic.
Ensures single component failure doesn't fail entire entry.

Requirements: 14.1, 14.2, 14.3, 14.4, 14.5
"""
import logging
from typing import Dict, Any, Optional
from enum import Enum

from backend.lambda_functions.shared.logger import setup_logger
from backend.lambda_functions.shared.config import config

logger = setup_logger(__name__)


class ErrorCategory(str, Enum):
    """Error categories for handling strategy"""
    TRANSIENT = "transient"  # Retryable errors
    PERMANENT = "permanent"  # Non-retryable errors
    DEGRADABLE = "degradable"  # Can continue with degraded functionality


class ProcessingStage(str, Enum):
    """Processing stages"""
    MEDIA_FETCH = "media_fetch"
    ASR = "asr"
    VISION = "vision"
    EXTRACTION = "extraction"
    ENHANCEMENT = "enhancement"
    MAPPING = "mapping"
    SUBMISSION = "submission"
    NOTIFICATION = "notification"


class ErrorHandler:
    """
    Error handler with graceful degradation strategies
    
    Requirements: 14.1, 14.2, 14.3, 14.4, 14.5
    """
    
    def __init__(self):
        """Initialize error handler"""
        self.error_counts = {}
    
    def categorize_error(self, error: Exception, stage: ProcessingStage) -> ErrorCategory:
        """
        Categorize error for handling strategy
        
        Args:
            error: Exception that occurred
            stage: Processing stage where error occurred
            
        Returns:
            ErrorCategory enum value
            
        Requirements: 14.5
        """
        error_str = str(error).lower()
        error_type = type(error).__name__
        
        # Transient errors (should retry)
        transient_keywords = [
            'timeout', 'throttl', 'rate limit', 'service unavailable',
            'connection', 'network', '503', '429', '500', '502', '504',
            'too many requests', 'temporarily unavailable'
        ]
        
        if any(keyword in error_str for keyword in transient_keywords):
            return ErrorCategory.TRANSIENT
        
        # Permanent errors (should not retry)
        permanent_keywords = [
            'not found', '404', 'unauthorized', '401', '403',
            'invalid', 'malformed', 'bad request', '400',
            'authentication failed', 'permission denied'
        ]
        
        if any(keyword in error_str for keyword in permanent_keywords):
            return ErrorCategory.PERMANENT
        
        # Stage-specific categorization
        if stage in [ProcessingStage.ASR, ProcessingStage.VISION, 
                     ProcessingStage.ENHANCEMENT, ProcessingStage.EXTRACTION]:
            # These stages can be degraded
            return ErrorCategory.DEGRADABLE
        
        # Default to transient for unknown errors
        return ErrorCategory.TRANSIENT
    
    def handle_asr_error(
        self,
        error: Exception,
        tracking_id: str
    ) -> Dict[str, Any]:
        """
        Handle ASR service failure with fallback
        
        Requirements: 14.1
        """
        logger.warning(f"[{tracking_id}] ASR failed: {str(error)}")
        
        category = self.categorize_error(error, ProcessingStage.ASR)
        
        if category == ErrorCategory.TRANSIENT:
            # Retry will be handled by SQS
            logger.info(f"[{tracking_id}] ASR error is transient, will retry")
            raise error
        
        # Graceful degradation: Continue without transcription
        logger.info(f"[{tracking_id}] Continuing without ASR (fallback to manual transcription)")
        
        return {
            'transcription': {
                'text': '',
                'confidence': 0.0,
                'error': str(error),
                'fallback': 'manual_transcription_required',
                'requires_manual_review': True
            }
        }
    
    def handle_vision_error(
        self,
        error: Exception,
        tracking_id: str
    ) -> Dict[str, Any]:
        """
        Handle Vision service failure with fallback
        
        Requirements: 14.1
        """
        logger.warning(f"[{tracking_id}] Vision failed: {str(error)}")
        
        category = self.categorize_error(error, ProcessingStage.VISION)
        
        if category == ErrorCategory.TRANSIENT:
            # Retry will be handled by SQS
            logger.info(f"[{tracking_id}] Vision error is transient, will retry")
            raise error
        
        # Graceful degradation: Continue without vision analysis
        logger.info(f"[{tracking_id}] Continuing without Vision analysis")
        
        return {
            'vision': {
                'category': 'Unknown',
                'colors': [],
                'materials': [],
                'confidence': 0.0,
                'error': str(error),
                'fallback': 'manual_analysis_required',
                'requires_manual_review': True
            }
        }
    
    def handle_enhancement_error(
        self,
        error: Exception,
        tracking_id: str,
        original_image_bytes: Optional[bytes] = None
    ) -> Dict[str, Any]:
        """
        Handle image enhancement failure with fallback
        
        Requirements: 14.2
        """
        logger.warning(f"[{tracking_id}] Image enhancement failed: {str(error)}")
        
        # Graceful degradation: Use original image
        logger.info(f"[{tracking_id}] Using original image (enhancement skipped)")
        
        return {
            'enhanced': False,
            'use_original': True,
            'error': str(error),
            'fallback': 'original_image'
        }
    
    def handle_extraction_error(
        self,
        error: Exception,
        tracking_id: str
    ) -> Dict[str, Any]:
        """
        Handle attribute extraction failure with fallback
        
        Requirements: 14.3
        """
        logger.warning(f"[{tracking_id}] Attribute extraction failed: {str(error)}")
        
        category = self.categorize_error(error, ProcessingStage.EXTRACTION)
        
        if category == ErrorCategory.TRANSIENT:
            # Retry will be handled by SQS
            logger.info(f"[{tracking_id}] Extraction error is transient, will retry")
            raise error
        
        # Graceful degradation: Use basic extraction without RAG
        logger.info(f"[{tracking_id}] Using basic extraction (without cultural context)")
        
        return {
            'category': 'Unknown',
            'short_description': 'Product description unavailable',
            'long_description': 'Product description unavailable',
            'material': [],
            'colors': [],
            'confidence_scores': {'category': 0.0},
            'error': str(error),
            'fallback': 'basic_extraction',
            'requires_manual_review': True
        }
    
    def handle_mapping_error(
        self,
        error: Exception,
        tracking_id: str
    ) -> Dict[str, Any]:
        """
        Handle schema mapping failure
        
        Requirements: 14.4
        """
        logger.error(f"[{tracking_id}] Schema mapping failed: {str(error)}")
        
        category = self.categorize_error(error, ProcessingStage.MAPPING)
        
        # Mapping errors are critical - cannot proceed without valid schema
        if category == ErrorCategory.TRANSIENT:
            logger.info(f"[{tracking_id}] Mapping error is transient, will retry")
            raise error
        
        # Permanent mapping error - flag for manual review
        logger.error(f"[{tracking_id}] Permanent mapping error, flagging for manual review")
        
        return {
            'success': False,
            'error': str(error),
            'requires_manual_review': True,
            'stage': 'mapping'
        }
    
    def handle_submission_error(
        self,
        error: Exception,
        tracking_id: str
    ) -> Dict[str, Any]:
        """
        Handle ONDC submission failure
        
        Requirements: 14.5
        """
        logger.error(f"[{tracking_id}] ONDC submission failed: {str(error)}")
        
        category = self.categorize_error(error, ProcessingStage.SUBMISSION)
        
        if category == ErrorCategory.TRANSIENT:
            # Retry will be handled by SQS
            logger.info(f"[{tracking_id}] Submission error is transient, will retry")
            raise error
        
        # Permanent submission error
        logger.error(f"[{tracking_id}] Permanent submission error, routing to DLQ")
        
        return {
            'success': False,
            'error': str(error),
            'requires_manual_review': True,
            'stage': 'submission',
            'route_to_dlq': True
        }
    
    def handle_notification_error(
        self,
        error: Exception,
        tracking_id: str
    ) -> None:
        """
        Handle notification failure (non-critical)
        
        Requirements: 14.4
        """
        logger.warning(f"[{tracking_id}] Notification failed: {str(error)}")
        
        # Notification failures are non-critical - log and continue
        logger.info(f"[{tracking_id}] Continuing despite notification failure")
    
    def should_route_to_dlq(
        self,
        error: Exception,
        stage: ProcessingStage,
        retry_count: int
    ) -> bool:
        """
        Determine if message should be routed to DLQ
        
        Args:
            error: Exception that occurred
            stage: Processing stage
            retry_count: Number of retries attempted
            
        Returns:
            True if should route to DLQ
            
        Requirements: 14.5
        """
        category = self.categorize_error(error, stage)
        
        # Route to DLQ if:
        # 1. Permanent error
        # 2. Max retries exceeded (handled by SQS)
        # 3. Critical stage failure (mapping, submission)
        
        if category == ErrorCategory.PERMANENT:
            return True
        
        if stage in [ProcessingStage.MAPPING, ProcessingStage.SUBMISSION]:
            if retry_count >= 3:
                return True
        
        return False
    
    def get_fallback_strategy(self, stage: ProcessingStage) -> str:
        """
        Get fallback strategy for a processing stage
        
        Args:
            stage: Processing stage
            
        Returns:
            Fallback strategy description
        """
        strategies = {
            ProcessingStage.ASR: "Continue without transcription, flag for manual review",
            ProcessingStage.VISION: "Continue without vision analysis, use basic attributes",
            ProcessingStage.ENHANCEMENT: "Use original image without enhancement",
            ProcessingStage.EXTRACTION: "Use basic extraction without cultural context",
            ProcessingStage.MAPPING: "Flag for manual review, cannot proceed",
            ProcessingStage.SUBMISSION: "Retry with exponential backoff, then route to DLQ",
            ProcessingStage.NOTIFICATION: "Log error and continue (non-critical)"
        }
        
        return strategies.get(stage, "No fallback available")
    
    def log_error_metrics(
        self,
        stage: ProcessingStage,
        error: Exception,
        tracking_id: str
    ):
        """
        Log error metrics for monitoring
        
        Args:
            stage: Processing stage
            error: Exception that occurred
            tracking_id: Tracking ID
        """
        # Increment error count for this stage
        stage_key = stage.value
        if stage_key not in self.error_counts:
            self.error_counts[stage_key] = 0
        self.error_counts[stage_key] += 1
        
        # Log structured error for CloudWatch
        logger.error(
            f"Error in {stage.value}",
            extra={
                'tracking_id': tracking_id,
                'stage': stage.value,
                'error_type': type(error).__name__,
                'error_message': str(error),
                'error_count': self.error_counts[stage_key]
            }
        )


# Global error handler instance
error_handler = ErrorHandler()


def get_error_handler() -> ErrorHandler:
    """Get global error handler instance"""
    return error_handler
