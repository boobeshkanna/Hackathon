"""
AWS Sagemaker Client for Vision and ASR inference

This client provides a unified interface to invoke a combined Sagemaker endpoint
that handles both image analysis (Vision) and audio transcription (ASR).

Features:
- Retry logic with exponential backoff
- Timeout handling
- Error categorization (transient vs permanent)
- Low-confidence flagging
- Support for multimodal (image + audio) processing
"""
import json
import logging
import time
import base64
from typing import Dict, Any, Optional, Tuple
from enum import Enum
import boto3
from botocore.exceptions import ClientError, ReadTimeoutError, ConnectTimeoutError
from botocore.config import Config

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """Error categories for retry logic"""
    TRANSIENT = "transient"  # Retryable errors
    PERMANENT = "permanent"  # Non-retryable errors


class ConfidenceLevel(Enum):
    """Confidence level categories"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SagemakerClient:
    """Client for AWS Sagemaker inference endpoints with retry logic and error handling"""
    
    # Confidence thresholds
    ASR_CONFIDENCE_THRESHOLD = 0.7
    VISION_CONFIDENCE_THRESHOLD = 0.6
    
    # Retry configuration
    MAX_RETRIES = 3
    INITIAL_RETRY_DELAY = 1  # seconds
    MAX_RETRY_DELAY = 10  # seconds
    
    def __init__(
        self,
        endpoint_name: Optional[str] = None,
        region: str = 'ap-south-1',
        timeout_seconds: int = 30,
        max_retries: int = 3,
        asr_confidence_threshold: float = 0.7,
        vision_confidence_threshold: float = 0.6
    ):
        """
        Initialize Sagemaker client with retry and timeout configuration
        
        Args:
            endpoint_name: Sagemaker endpoint name
            region: AWS region
            timeout_seconds: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            asr_confidence_threshold: Minimum confidence for ASR results
            vision_confidence_threshold: Minimum confidence for vision results
        """
        self.endpoint_name = endpoint_name
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.asr_confidence_threshold = asr_confidence_threshold
        self.vision_confidence_threshold = vision_confidence_threshold
        
        # Configure boto3 client with timeout
        config = Config(
            read_timeout=timeout_seconds,
            connect_timeout=10,
            retries={'max_attempts': 0}  # We handle retries manually
        )
        
        self.client = boto3.client(
            'sagemaker-runtime',
            region_name=region,
            config=config
        )
        
        logger.info(
            f"Initialized Sagemaker client for endpoint: {endpoint_name}, "
            f"timeout: {timeout_seconds}s, max_retries: {max_retries}"
        )
    
    def invoke_combined_endpoint(
        self,
        image_bytes: Optional[bytes] = None,
        audio_bytes: Optional[bytes] = None,
        language_hint: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Invoke combined Vision + ASR endpoint with retry logic
        
        Args:
            image_bytes: Image data as bytes (optional)
            audio_bytes: Audio data as bytes (optional)
            language_hint: Language code hint for ASR (hi, te, ta, etc.)
            
        Returns:
            Dict containing combined analysis results with confidence flags
            
        Raises:
            ValueError: If both image_bytes and audio_bytes are None
            Exception: If all retry attempts fail
        """
        if image_bytes is None and audio_bytes is None:
            raise ValueError("At least one of image_bytes or audio_bytes must be provided")
        
        # Prepare payload
        payload = {
            'task': 'multimodal_analysis'
        }
        
        if image_bytes:
            payload['image'] = base64.b64encode(image_bytes).decode('utf-8')
        
        if audio_bytes:
            payload['audio'] = base64.b64encode(audio_bytes).decode('utf-8')
        
        if language_hint:
            payload['language_hint'] = language_hint
        
        # Invoke with retry logic
        result = self._invoke_with_retry(payload)
        
        # Flag low confidence results
        result = self._flag_low_confidence(result)
        
        return result
    
    def _invoke_with_retry(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Invoke endpoint with exponential backoff retry logic
        
        Args:
            payload: Request payload
            
        Returns:
            Response from endpoint
            
        Raises:
            Exception: If all retry attempts fail
        """
        last_exception = None
        retry_delay = self.INITIAL_RETRY_DELAY
        
        for attempt in range(self.max_retries + 1):
            try:
                logger.info(f"Invoking Sagemaker endpoint (attempt {attempt + 1}/{self.max_retries + 1})")
                
                response = self.client.invoke_endpoint(
                    EndpointName=self.endpoint_name,
                    ContentType='application/json',
                    Body=json.dumps(payload)
                )
                
                result = json.loads(response['Body'].read().decode())
                logger.info("Sagemaker endpoint invoked successfully")
                return result
                
            except (ReadTimeoutError, ConnectTimeoutError) as e:
                last_exception = e
                error_category = self._categorize_error(e)
                logger.warning(
                    f"Timeout error on attempt {attempt + 1}: {e}, "
                    f"category: {error_category.value}"
                )
                
                if error_category == ErrorCategory.PERMANENT or attempt >= self.max_retries:
                    break
                
                # Exponential backoff
                time.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, self.MAX_RETRY_DELAY)
                
            except ClientError as e:
                last_exception = e
                error_category = self._categorize_error(e)
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                
                logger.warning(
                    f"Client error on attempt {attempt + 1}: {error_code}, "
                    f"category: {error_category.value}"
                )
                
                # Don't retry permanent errors
                if error_category == ErrorCategory.PERMANENT:
                    logger.error(f"Permanent error, not retrying: {e}")
                    raise
                
                if attempt >= self.max_retries:
                    break
                
                # Exponential backoff for transient errors
                time.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, self.MAX_RETRY_DELAY)
                
            except Exception as e:
                last_exception = e
                logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
                
                if attempt >= self.max_retries:
                    break
                
                time.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, self.MAX_RETRY_DELAY)
        
        # All retries exhausted
        logger.error(f"All {self.max_retries + 1} attempts failed")
        raise Exception(f"Sagemaker invocation failed after {self.max_retries + 1} attempts") from last_exception
    
    def _categorize_error(self, error: Exception) -> ErrorCategory:
        """
        Categorize error as transient (retryable) or permanent
        
        Args:
            error: Exception to categorize
            
        Returns:
            ErrorCategory enum value
        """
        # Timeout errors are transient
        if isinstance(error, (ReadTimeoutError, ConnectTimeoutError)):
            return ErrorCategory.TRANSIENT
        
        # ClientError categorization
        if isinstance(error, ClientError):
            error_code = error.response.get('Error', {}).get('Code', '')
            status_code = error.response.get('ResponseMetadata', {}).get('HTTPStatusCode', 0)
            
            # 5xx errors are transient (server errors)
            if 500 <= status_code < 600:
                return ErrorCategory.TRANSIENT
            
            # Throttling is transient
            if error_code in ['ThrottlingException', 'TooManyRequestsException', 'ServiceUnavailable']:
                return ErrorCategory.TRANSIENT
            
            # 4xx errors are generally permanent (client errors)
            if 400 <= status_code < 500:
                # Except for rate limiting
                if status_code == 429:
                    return ErrorCategory.TRANSIENT
                return ErrorCategory.PERMANENT
        
        # Unknown errors are treated as transient (retry once)
        return ErrorCategory.TRANSIENT
    
    def _flag_low_confidence(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Flag low confidence results for manual review
        
        Args:
            result: Endpoint response
            
        Returns:
            Result with confidence flags added
        """
        # Flag ASR low confidence
        if 'transcription' in result:
            transcription = result['transcription']
            confidence = transcription.get('confidence', 0.0)
            
            if confidence < self.asr_confidence_threshold:
                transcription['low_confidence'] = True
                transcription['requires_manual_review'] = True
                logger.warning(
                    f"ASR confidence {confidence:.2f} below threshold "
                    f"{self.asr_confidence_threshold}, flagged for review"
                )
            else:
                transcription['low_confidence'] = False
                transcription['requires_manual_review'] = False
            
            # Flag low confidence segments
            if 'segments' in transcription:
                for segment in transcription['segments']:
                    seg_confidence = segment.get('confidence', 0.0)
                    if seg_confidence < self.asr_confidence_threshold:
                        segment['low_confidence'] = True
                        logger.warning(
                            f"ASR segment '{segment.get('text', '')}' has low confidence: "
                            f"{seg_confidence:.2f}"
                        )
        
        # Flag Vision low confidence
        if 'vision' in result:
            vision = result['vision']
            confidence = vision.get('confidence', 0.0)
            
            if confidence < self.vision_confidence_threshold:
                vision['low_confidence'] = True
                vision['requires_manual_review'] = True
                logger.warning(
                    f"Vision confidence {confidence:.2f} below threshold "
                    f"{self.vision_confidence_threshold}, flagged for review"
                )
            else:
                vision['low_confidence'] = False
                vision['requires_manual_review'] = False
        
        return result
    
    def health_check(self) -> bool:
        """
        Check if Sagemaker endpoint is healthy
        
        Returns:
            True if endpoint is healthy, False otherwise
        """
        try:
            sagemaker_client = boto3.client('sagemaker')
            response = sagemaker_client.describe_endpoint(
                EndpointName=self.endpoint_name
            )
            status = response['EndpointStatus']
            logger.info(f"Endpoint status: {status}")
            return status == 'InService'
            
        except ClientError as e:
            logger.error(f"Error checking endpoint health: {e}")
            return False

    
    def invoke_vision_model(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Invoke vision model for image analysis (backward compatibility wrapper)
        
        Args:
            image_bytes: Image data as bytes
            
        Returns:
            Dict containing vision analysis results
        """
        logger.info("Using backward compatibility wrapper for vision-only invocation")
        result = self.invoke_combined_endpoint(image_bytes=image_bytes)
        return result.get('vision', {})
    
    def invoke_asr_model(self, audio_bytes: bytes, language_code: str = 'hi') -> Dict[str, Any]:
        """
        Invoke ASR model (backward compatibility wrapper)
        
        Args:
            audio_bytes: Audio data as bytes
            language_code: Language code (hi, te, ta, etc.)
            
        Returns:
            Dict containing transcription results
        """
        logger.info(f"Using backward compatibility wrapper for ASR-only invocation (language: {language_code})")
        result = self.invoke_combined_endpoint(
            audio_bytes=audio_bytes,
            language_hint=language_code
        )
        return result.get('transcription', {})
    
    def get_confidence_level(self, confidence: float, is_vision: bool = False) -> ConfidenceLevel:
        """
        Categorize confidence score into levels
        
        Args:
            confidence: Confidence score (0.0 to 1.0)
            is_vision: Whether this is a vision confidence score
            
        Returns:
            ConfidenceLevel enum value
        """
        threshold = self.vision_confidence_threshold if is_vision else self.asr_confidence_threshold
        
        if confidence >= 0.85:
            return ConfidenceLevel.HIGH
        elif confidence >= threshold:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW
