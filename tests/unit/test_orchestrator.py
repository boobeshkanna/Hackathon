"""
Unit tests for Lambda Workflow Orchestrator

Tests the main orchestrator handler and its components.
"""
import json
import pytest
import sys
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Mock aws_lambda_powertools before importing modules that use it
sys.modules['aws_lambda_powertools'] = MagicMock()

# Import orchestrator components
from backend.lambda_functions.orchestrator.batch_processor import BatchProcessor
from backend.lambda_functions.orchestrator.error_handler import (
    ErrorHandler,
    ErrorCategory,
    ProcessingStage
)
from backend.models.catalog import ProcessingStatus

# Mock the handler module functions
with patch.dict('sys.modules', {
    'backend.services.media_processing.image_enhancement': MagicMock(),
    'backend.services.sagemaker_client.client': MagicMock(),
    'backend.services.bedrock_client.client': MagicMock(),
    'backend.services.bedrock_client.attribute_extractor': MagicMock(),
    'backend.services.bedrock_client.transcreation_service': MagicMock(),
    'backend.services.ondc_gateway.gateway': MagicMock(),
    'backend.services.ondc_gateway.api_client': MagicMock(),
}):
    from backend.lambda_functions.orchestrator.handler import (
        is_recoverable_error,
        localize_notification_message
    )


class TestErrorRecovery:
    """Test error recovery and categorization"""
    
    def test_is_recoverable_error_timeout(self):
        """Test timeout errors are recoverable"""
        error = Exception("Request timeout after 30 seconds")
        assert is_recoverable_error(error) is True
    
    def test_is_recoverable_error_throttling(self):
        """Test throttling errors are recoverable"""
        error = Exception("Rate limit exceeded, status code 429")
        assert is_recoverable_error(error) is True
    
    def test_is_recoverable_error_server_error(self):
        """Test 5xx errors are recoverable"""
        error = Exception("Service unavailable, status code 503")
        assert is_recoverable_error(error) is True
    
    def test_is_recoverable_error_permanent(self):
        """Test permanent errors are not recoverable"""
        error = Exception("Invalid request, status code 400")
        assert is_recoverable_error(error) is False


class TestNotificationLocalization:
    """Test notification message localization"""
    
    def test_localize_hindi_completed(self):
        """Test Hindi localization for completed stage"""
        message = localize_notification_message(
            stage='completed',
            language='hi',
            catalog_id='cat-123'
        )
        
        assert 'सफलतापूर्वक' in message
        assert 'cat-123' in message
    
    def test_localize_english_completed(self):
        """Test English localization for completed stage"""
        message = localize_notification_message(
            stage='completed',
            language='en',
            catalog_id='cat-123'
        )
        
        assert 'successfully' in message.lower()
        assert 'cat-123' in message
    
    def test_localize_failed(self):
        """Test localization for failed stage"""
        message = localize_notification_message(
            stage='failed',
            language='en',
            error_message='Test error'
        )
        
        assert 'error' in message.lower()
        assert 'Test error' in message


class TestBatchProcessor:
    """Test batch processing optimizer"""
    
    def test_should_enable_batch_processing_threshold(self):
        """Test batch processing enabled when threshold met"""
        processor = BatchProcessor(queue_url='https://sqs.test.com/queue')
        
        # Mock queue depth check
        with patch.object(processor, 'check_queue_depth', return_value=10):
            assert processor.should_enable_batch_processing(3) is True
    
    def test_should_enable_batch_processing_current_batch(self):
        """Test batch processing enabled for large current batch"""
        processor = BatchProcessor(queue_url='https://sqs.test.com/queue')
        
        with patch.object(processor, 'check_queue_depth', return_value=2):
            assert processor.should_enable_batch_processing(5) is True
    
    def test_should_not_enable_batch_processing(self):
        """Test batch processing not enabled for small batches"""
        processor = BatchProcessor(queue_url='https://sqs.test.com/queue')
        
        with patch.object(processor, 'check_queue_depth', return_value=2):
            assert processor.should_enable_batch_processing(2) is False
    
    def test_optimize_batch_size(self):
        """Test batch size optimization"""
        processor = BatchProcessor(queue_url='https://sqs.test.com/queue')
        
        assert processor.optimize_batch_size(3) == 3
        assert processor.optimize_batch_size(7) == 5
        assert processor.optimize_batch_size(15) == 10
        assert processor.optimize_batch_size(100) == 20
    
    def test_estimate_cost_savings(self):
        """Test cost savings estimation"""
        processor = BatchProcessor(queue_url='https://sqs.test.com/queue')
        
        savings = processor.estimate_cost_savings(10)
        
        assert 'individual_cost' in savings
        assert 'batch_cost' in savings
        assert 'savings' in savings
        assert 'savings_percent' in savings
        assert savings['savings'] > 0
        assert savings['savings_percent'] > 0


class TestErrorHandler:
    """Test error handler with graceful degradation"""
    
    def test_categorize_transient_error(self):
        """Test transient error categorization"""
        handler = ErrorHandler()
        
        error = Exception("Connection timeout")
        category = handler.categorize_error(error, ProcessingStage.ASR)
        
        assert category == ErrorCategory.TRANSIENT
    
    def test_categorize_permanent_error(self):
        """Test permanent error categorization"""
        handler = ErrorHandler()
        
        error = Exception("Invalid request, 400 Bad Request")
        category = handler.categorize_error(error, ProcessingStage.SUBMISSION)
        
        assert category == ErrorCategory.PERMANENT
    
    def test_categorize_degradable_error(self):
        """Test degradable error categorization"""
        handler = ErrorHandler()
        
        error = Exception("Model inference failed")
        category = handler.categorize_error(error, ProcessingStage.ASR)
        
        # ASR errors should be degradable
        assert category in [ErrorCategory.DEGRADABLE, ErrorCategory.TRANSIENT]
    
    def test_handle_asr_error_graceful_degradation(self):
        """Test ASR error handling with graceful degradation"""
        handler = ErrorHandler()
        
        error = Exception("ASR model unavailable")
        result = handler.handle_asr_error(error, 'trk-123')
        
        assert 'transcription' in result
        assert result['transcription']['text'] == ''
        assert result['transcription']['requires_manual_review'] is True
    
    def test_handle_enhancement_error_fallback(self):
        """Test image enhancement error with fallback to original"""
        handler = ErrorHandler()
        
        error = Exception("Enhancement failed")
        result = handler.handle_enhancement_error(error, 'trk-123')
        
        assert result['enhanced'] is False
        assert result['use_original'] is True
        assert result['fallback'] == 'original_image'
    
    def test_should_route_to_dlq_permanent(self):
        """Test DLQ routing for permanent errors"""
        handler = ErrorHandler()
        
        error = Exception("Invalid schema, 400 Bad Request")
        should_route = handler.should_route_to_dlq(
            error, ProcessingStage.SUBMISSION, retry_count=1
        )
        
        assert should_route is True
    
    def test_should_route_to_dlq_max_retries(self):
        """Test DLQ routing after max retries"""
        handler = ErrorHandler()
        
        error = Exception("Timeout")
        should_route = handler.should_route_to_dlq(
            error, ProcessingStage.SUBMISSION, retry_count=5
        )
        
        assert should_route is True
    
    def test_get_fallback_strategy(self):
        """Test fallback strategy retrieval"""
        handler = ErrorHandler()
        
        strategy = handler.get_fallback_strategy(ProcessingStage.ASR)
        assert 'manual' in strategy.lower()
        
        strategy = handler.get_fallback_strategy(ProcessingStage.ENHANCEMENT)
        assert 'original' in strategy.lower()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
