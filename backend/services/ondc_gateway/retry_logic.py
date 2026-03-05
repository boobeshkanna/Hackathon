"""
ONDC Submission Retry Logic - Handles retry with exponential backoff

This module implements retry logic for ONDC catalog submissions with
exponential backoff, error categorization, and state persistence.

Requirements: 9.2, 9.3
"""
import logging
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass, asdict

from backend.services.ondc_gateway.api_client import (
    ONDCAPIClient,
    ONDCResponse,
    ONDCAPIError,
    ONDCAuthenticationError,
    ONDCValidationError,
    ONDCNetworkError
)


logger = logging.getLogger(__name__)


class ErrorCategory(str, Enum):
    """Error categorization for retry logic"""
    RETRYABLE = "retryable"
    PERMANENT = "permanent"
    AUTHENTICATION = "authentication"
    VALIDATION = "validation"


@dataclass
class RetryState:
    """Represents the retry state for a submission"""
    tracking_id: str
    idempotency_key: str
    attempt_count: int = 0
    max_attempts: int = 5
    last_attempt_at: Optional[datetime] = None
    last_error: Optional[str] = None
    last_error_category: Optional[ErrorCategory] = None
    next_retry_at: Optional[datetime] = None
    is_exhausted: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for DynamoDB storage"""
        data = asdict(self)
        # Convert datetime objects to ISO strings
        if self.last_attempt_at:
            data['last_attempt_at'] = self.last_attempt_at.isoformat()
        if self.next_retry_at:
            data['next_retry_at'] = self.next_retry_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RetryState':
        """Create from dictionary (from DynamoDB)"""
        # Convert ISO strings back to datetime
        if 'last_attempt_at' in data and data['last_attempt_at']:
            data['last_attempt_at'] = datetime.fromisoformat(data['last_attempt_at'])
        if 'next_retry_at' in data and data['next_retry_at']:
            data['next_retry_at'] = datetime.fromisoformat(data['next_retry_at'])
        
        # Convert error category string to enum
        if 'last_error_category' in data and data['last_error_category']:
            data['last_error_category'] = ErrorCategory(data['last_error_category'])
        
        return cls(**data)


class RetryLogic:
    """
    Implements retry logic with exponential backoff for ONDC submissions.
    
    Requirements: 9.2, 9.3
    """
    
    # Exponential backoff configuration
    BASE_DELAY_SECONDS = 60  # 1 minute
    MAX_DELAY_SECONDS = 3600  # 1 hour
    BACKOFF_MULTIPLIER = 2
    
    def __init__(
        self,
        max_attempts: int = 5,
        base_delay_seconds: int = 60,
        state_store: Optional[Callable] = None,
        state_loader: Optional[Callable] = None
    ):
        """
        Initialize retry logic.
        
        Args:
            max_attempts: Maximum number of retry attempts
            base_delay_seconds: Base delay for exponential backoff
            state_store: Function to persist retry state (tracking_id, state_dict)
            state_loader: Function to load retry state (tracking_id) -> state_dict
        """
        self.max_attempts = max_attempts
        self.base_delay_seconds = base_delay_seconds
        self.state_store = state_store
        self.state_loader = state_loader
    
    def categorize_error(
        self,
        error: Exception,
        response: Optional[ONDCResponse] = None
    ) -> ErrorCategory:
        """
        Categorize error as retryable or permanent.
        
        Args:
            error: Exception that occurred
            response: ONDC response if available
        
        Returns:
            ErrorCategory: Error category
        
        Requirements: 9.3
        """
        # Authentication errors are permanent
        if isinstance(error, ONDCAuthenticationError):
            return ErrorCategory.AUTHENTICATION
        
        # Validation errors are permanent
        if isinstance(error, ONDCValidationError):
            return ErrorCategory.VALIDATION
        
        # Network errors are retryable
        if isinstance(error, ONDCNetworkError):
            return ErrorCategory.RETRYABLE
        
        # Check response status code if available
        if response:
            # 5xx errors are retryable
            if response.status_code >= 500:
                return ErrorCategory.RETRYABLE
            
            # 429 rate limiting is retryable
            if response.status_code == 429:
                return ErrorCategory.RETRYABLE
            
            # 408 timeout is retryable
            if response.status_code == 408:
                return ErrorCategory.RETRYABLE
            
            # 4xx errors (except 408, 429) are permanent
            if 400 <= response.status_code < 500:
                return ErrorCategory.PERMANENT
        
        # Default to retryable for unknown errors
        return ErrorCategory.RETRYABLE
    
    def calculate_backoff_delay(self, attempt_count: int) -> int:
        """
        Calculate exponential backoff delay in seconds.
        
        Args:
            attempt_count: Current attempt count (0-indexed)
        
        Returns:
            int: Delay in seconds
        
        Requirements: 9.2
        """
        # Exponential backoff: base_delay * (2 ^ attempt_count)
        delay = self.base_delay_seconds * (self.BACKOFF_MULTIPLIER ** attempt_count)
        
        # Cap at maximum delay
        delay = min(delay, self.MAX_DELAY_SECONDS)
        
        return int(delay)
    
    def should_retry(self, retry_state: RetryState, error_category: ErrorCategory) -> bool:
        """
        Determine if submission should be retried.
        
        Args:
            retry_state: Current retry state
            error_category: Category of the error
        
        Returns:
            bool: True if should retry, False otherwise
        
        Requirements: 9.2, 9.3
        """
        # Don't retry permanent errors
        if error_category in [ErrorCategory.PERMANENT, ErrorCategory.AUTHENTICATION, ErrorCategory.VALIDATION]:
            logger.info(
                f"Not retrying permanent error: tracking_id={retry_state.tracking_id}, "
                f"category={error_category}"
            )
            return False
        
        # Don't retry if max attempts reached
        if retry_state.attempt_count >= retry_state.max_attempts:
            logger.warning(
                f"Max retry attempts reached: tracking_id={retry_state.tracking_id}, "
                f"attempts={retry_state.attempt_count}"
            )
            return False
        
        # Retry for retryable errors
        return True
    
    def update_retry_state(
        self,
        retry_state: RetryState,
        error: Exception,
        error_category: ErrorCategory
    ) -> RetryState:
        """
        Update retry state after a failed attempt.
        
        Args:
            retry_state: Current retry state
            error: Exception that occurred
            error_category: Category of the error
        
        Returns:
            RetryState: Updated retry state
        
        Requirements: 9.2
        """
        # Increment attempt count
        retry_state.attempt_count += 1
        retry_state.last_attempt_at = datetime.utcnow()
        retry_state.last_error = str(error)
        retry_state.last_error_category = error_category
        
        # Calculate next retry time
        if self.should_retry(retry_state, error_category):
            delay_seconds = self.calculate_backoff_delay(retry_state.attempt_count)
            retry_state.next_retry_at = datetime.utcnow() + timedelta(seconds=delay_seconds)
            retry_state.is_exhausted = False
            
            logger.info(
                f"Scheduling retry: tracking_id={retry_state.tracking_id}, "
                f"attempt={retry_state.attempt_count}/{retry_state.max_attempts}, "
                f"next_retry_at={retry_state.next_retry_at.isoformat()}, "
                f"delay={delay_seconds}s"
            )
        else:
            retry_state.next_retry_at = None
            retry_state.is_exhausted = True
            
            logger.warning(
                f"Retry exhausted: tracking_id={retry_state.tracking_id}, "
                f"attempts={retry_state.attempt_count}, category={error_category}"
            )
        
        # Persist state if store function provided
        if self.state_store:
            try:
                self.state_store(retry_state.tracking_id, retry_state.to_dict())
            except Exception as e:
                logger.error(f"Failed to persist retry state: {str(e)}")
        
        return retry_state
    
    def load_retry_state(self, tracking_id: str, idempotency_key: str) -> RetryState:
        """
        Load retry state from storage or create new.
        
        Args:
            tracking_id: Tracking ID
            idempotency_key: Idempotency key
        
        Returns:
            RetryState: Loaded or new retry state
        """
        # Try to load existing state
        if self.state_loader:
            try:
                state_dict = self.state_loader(tracking_id)
                if state_dict:
                    return RetryState.from_dict(state_dict)
            except Exception as e:
                logger.warning(f"Failed to load retry state: {str(e)}")
        
        # Create new state
        return RetryState(
            tracking_id=tracking_id,
            idempotency_key=idempotency_key,
            max_attempts=self.max_attempts
        )
    
    def execute_with_retry(
        self,
        api_client: ONDCAPIClient,
        submission_func: Callable,
        tracking_id: str,
        idempotency_key: str,
        **kwargs
    ) -> tuple[ONDCResponse, RetryState]:
        """
        Execute submission with retry logic.
        
        Args:
            api_client: ONDC API client
            submission_func: Function to call for submission (submit_catalog or update_catalog)
            tracking_id: Tracking ID
            idempotency_key: Idempotency key (preserved across retries)
            **kwargs: Additional arguments for submission function
        
        Returns:
            tuple: (ONDCResponse, RetryState)
        
        Raises:
            ONDCAPIError: If submission fails after all retries
        
        Requirements: 9.2, 9.3
        """
        # Load or create retry state
        retry_state = self.load_retry_state(tracking_id, idempotency_key)
        
        # Check if already exhausted
        if retry_state.is_exhausted:
            raise ONDCAPIError(
                f"Retry exhausted for tracking_id={tracking_id}, "
                f"last_error={retry_state.last_error}"
            )
        
        # Check if it's time to retry
        if retry_state.next_retry_at and datetime.utcnow() < retry_state.next_retry_at:
            raise ONDCAPIError(
                f"Too early to retry: tracking_id={tracking_id}, "
                f"next_retry_at={retry_state.next_retry_at.isoformat()}"
            )
        
        # Attempt submission
        try:
            logger.info(
                f"Attempting ONDC submission: tracking_id={tracking_id}, "
                f"attempt={retry_state.attempt_count + 1}/{retry_state.max_attempts}, "
                f"idempotency_key={idempotency_key}"
            )
            
            response = submission_func(
                idempotency_key=idempotency_key,
                tracking_id=tracking_id,
                **kwargs
            )
            
            # Check if successful
            if response.is_success():
                logger.info(
                    f"ONDC submission successful: tracking_id={tracking_id}, "
                    f"catalog_id={response.catalog_id}"
                )
                return response, retry_state
            
            # Non-success response - categorize and update state
            error = ONDCAPIError(response.get_error_message())
            error_category = self.categorize_error(error, response)
            retry_state = self.update_retry_state(retry_state, error, error_category)
            
            # Raise error if not retryable
            if not self.should_retry(retry_state, error_category):
                raise error
            
            return response, retry_state
            
        except ONDCAPIError as e:
            # Categorize error
            response = None
            if hasattr(e, 'response'):
                response = e.response
            
            error_category = self.categorize_error(e, response)
            retry_state = self.update_retry_state(retry_state, e, error_category)
            
            # Re-raise if not retryable
            if not self.should_retry(retry_state, error_category):
                raise
            
            # Return error response with retry state
            if response:
                return response, retry_state
            
            raise
