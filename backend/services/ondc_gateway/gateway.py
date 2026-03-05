"""
ONDC Gateway - Main orchestrator for catalog submission

This module provides a high-level interface that orchestrates all ONDC Gateway
components: schema mapping, validation, API client, retry logic, audit logging,
and update detection.

Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 18.1, 18.2, 18.3, 18.4
"""
import logging
import time
from typing import Optional, Dict, Any, Tuple
from datetime import datetime

from backend.models.catalog import ExtractedAttributes, ONDCCatalogItem
from backend.services.ondc_gateway.schema_mapper import map_to_beckn_item, generate_item_id
from backend.services.ondc_gateway.validator import ONDCValidator
from backend.services.ondc_gateway.auto_corrector import ONDCAutoCorrector
from backend.services.ondc_gateway.api_client import ONDCAPIClient, ONDCResponse, ONDCAPIError
from backend.services.ondc_gateway.retry_logic import RetryLogic, RetryState
from backend.services.ondc_gateway.audit_logger import ONDCAuditLogger
from backend.services.ondc_gateway.update_detector import ONDCUpdateDetector, UpdateDetectionResult


logger = logging.getLogger(__name__)


class ONDCGatewayResult:
    """Result of ONDC Gateway submission"""
    
    def __init__(
        self,
        success: bool,
        ondc_catalog_id: Optional[str] = None,
        is_update: bool = False,
        version_number: int = 1,
        response: Optional[ONDCResponse] = None,
        retry_state: Optional[RetryState] = None,
        validation_errors: Optional[list] = None,
        error_message: Optional[str] = None
    ):
        self.success = success
        self.ondc_catalog_id = ondc_catalog_id
        self.is_update = is_update
        self.version_number = version_number
        self.response = response
        self.retry_state = retry_state
        self.validation_errors = validation_errors or []
        self.error_message = error_message
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'success': self.success,
            'ondc_catalog_id': self.ondc_catalog_id,
            'is_update': self.is_update,
            'version_number': self.version_number,
            'validation_errors': [e.to_dict() for e in self.validation_errors],
            'error_message': self.error_message,
            'retry_state': self.retry_state.to_dict() if self.retry_state else None
        }


class ONDCGateway:
    """
    Main ONDC Gateway orchestrator.
    
    Coordinates schema mapping, validation, submission, retry logic,
    audit logging, and update detection.
    
    Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 18.1, 18.2, 18.3, 18.4
    """
    
    def __init__(
        self,
        api_client: ONDCAPIClient,
        validator: Optional[ONDCValidator] = None,
        auto_corrector: Optional[ONDCAutoCorrector] = None,
        retry_logic: Optional[RetryLogic] = None,
        audit_logger: Optional[ONDCAuditLogger] = None,
        update_detector: Optional[ONDCUpdateDetector] = None
    ):
        """
        Initialize ONDC Gateway.
        
        Args:
            api_client: ONDC API client
            validator: Schema validator (optional, creates default)
            auto_corrector: Auto-corrector (optional, creates default)
            retry_logic: Retry logic (optional, creates default)
            audit_logger: Audit logger (optional, creates default)
            update_detector: Update detector (optional, creates default)
        """
        self.api_client = api_client
        self.validator = validator or ONDCValidator()
        self.auto_corrector = auto_corrector or ONDCAutoCorrector()
        self.retry_logic = retry_logic or RetryLogic()
        self.audit_logger = audit_logger or ONDCAuditLogger()
        self.update_detector = update_detector or ONDCUpdateDetector()
    
    def submit_catalog(
        self,
        extracted: ExtractedAttributes,
        tracking_id: str,
        tenant_id: str,
        artisan_id: str,
        image_urls: Optional[list] = None
    ) -> ONDCGatewayResult:
        """
        Submit catalog entry to ONDC with full orchestration.
        
        This method:
        1. Detects if this is an update or new entry
        2. Maps attributes to Beckn schema
        3. Validates and auto-corrects payload
        4. Submits to ONDC with retry logic
        5. Logs audit trail
        6. Saves version history
        
        Args:
            extracted: Extracted product attributes
            tracking_id: Tracking ID
            tenant_id: Tenant ID
            artisan_id: Artisan ID
            image_urls: List of image URLs (optional)
        
        Returns:
            ONDCGatewayResult: Submission result
        
        Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 18.1, 18.2, 18.3, 18.4
        """
        start_time = time.time()
        
        logger.info(
            f"Starting ONDC submission: tracking_id={tracking_id}, "
            f"tenant_id={tenant_id}, artisan_id={artisan_id}"
        )
        
        try:
            # Step 1: Detect if this is an update
            update_result = self.update_detector.detect_update(
                extracted, tenant_id, artisan_id
            )
            
            # Step 2: Map to Beckn schema
            item = map_to_beckn_item(extracted, image_urls)
            
            # Step 3: Validate payload
            validation_result = self.validator.validate(item)
            
            # Step 4: Auto-correct if validation fails
            if not validation_result.is_valid:
                logger.warning(
                    f"Validation failed: tracking_id={tracking_id}, "
                    f"errors={len(validation_result.errors)}"
                )
                
                correction_result = self.auto_corrector.auto_correct(item, validation_result)
                
                if correction_result.manual_review_required:
                    # Cannot auto-correct - return error
                    logger.error(
                        f"Manual review required: tracking_id={tracking_id}, "
                        f"uncorrectable_errors={len(correction_result.uncorrectable_errors)}"
                    )
                    
                    return ONDCGatewayResult(
                        success=False,
                        validation_errors=correction_result.uncorrectable_errors,
                        error_message="Validation failed - manual review required"
                    )
                
                # Use corrected item
                item = correction_result.corrected_item
                logger.info(
                    f"Auto-corrections applied: tracking_id={tracking_id}, "
                    f"corrections={len(correction_result.corrections_applied)}"
                )
            
            # Step 5: Generate idempotency key
            idempotency_key = self._generate_idempotency_key(
                tracking_id, item.id, update_result.item_fingerprint
            )
            
            # Step 6: Submit to ONDC (with retry logic)
            if update_result.is_update:
                response, retry_state = self._submit_update(
                    item, tracking_id, tenant_id, artisan_id,
                    idempotency_key, update_result.original_catalog_id
                )
            else:
                response, retry_state = self._submit_new(
                    item, tracking_id, tenant_id, artisan_id, idempotency_key
                )
            
            # Calculate response time
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # Step 7: Log audit trail
            if response.is_success():
                self.audit_logger.log_success(
                    tracking_id=tracking_id,
                    tenant_id=tenant_id,
                    artisan_id=artisan_id,
                    idempotency_key=idempotency_key,
                    attempt_number=retry_state.attempt_count + 1,
                    submission_type="update" if update_result.is_update else "create",
                    item_id=item.id,
                    response=response,
                    response_time_ms=response_time_ms,
                    original_catalog_id=update_result.original_catalog_id
                )
            
            # Step 8: Save catalog entry and version
            if response.is_success():
                catalog_id = update_result.original_catalog_id if update_result.is_update else response.catalog_id
                
                self.update_detector.save_catalog_entry(
                    tracking_id=tracking_id,
                    tenant_id=tenant_id,
                    artisan_id=artisan_id,
                    item=item,
                    extracted=extracted,
                    ondc_catalog_id=catalog_id,
                    fingerprint=update_result.item_fingerprint,
                    is_update=update_result.is_update,
                    original_catalog_id=update_result.original_catalog_id
                )
                
                self.update_detector.save_version(
                    ondc_catalog_id=catalog_id,
                    tracking_id=tracking_id,
                    artisan_id=artisan_id,
                    version_number=update_result.version_number,
                    fingerprint=update_result.item_fingerprint,
                    extracted=extracted
                )
            
            # Return result
            return ONDCGatewayResult(
                success=response.is_success(),
                ondc_catalog_id=response.catalog_id,
                is_update=update_result.is_update,
                version_number=update_result.version_number,
                response=response,
                retry_state=retry_state,
                error_message=response.get_error_message() if not response.is_success() else None
            )
            
        except ONDCAPIError as e:
            logger.error(f"ONDC API error: tracking_id={tracking_id}, error={str(e)}")
            
            return ONDCGatewayResult(
                success=False,
                error_message=str(e)
            )
        
        except Exception as e:
            logger.error(f"Unexpected error: tracking_id={tracking_id}, error={str(e)}", exc_info=True)
            
            return ONDCGatewayResult(
                success=False,
                error_message=f"Unexpected error: {str(e)}"
            )
    
    def _submit_new(
        self,
        item: ONDCCatalogItem,
        tracking_id: str,
        tenant_id: str,
        artisan_id: str,
        idempotency_key: str
    ) -> Tuple[ONDCResponse, RetryState]:
        """Submit new catalog entry"""
        logger.info(f"Submitting new catalog entry: tracking_id={tracking_id}")
        
        # Use retry logic to handle submission
        response, retry_state = self.retry_logic.execute_with_retry(
            api_client=self.api_client,
            submission_func=self.api_client.submit_catalog,
            tracking_id=tracking_id,
            idempotency_key=idempotency_key,
            item=item,
            tenant_id=tenant_id
        )
        
        return response, retry_state
    
    def _submit_update(
        self,
        item: ONDCCatalogItem,
        tracking_id: str,
        tenant_id: str,
        artisan_id: str,
        idempotency_key: str,
        original_catalog_id: str
    ) -> Tuple[ONDCResponse, RetryState]:
        """Submit catalog update"""
        logger.info(
            f"Submitting catalog update: tracking_id={tracking_id}, "
            f"original_catalog_id={original_catalog_id}"
        )
        
        # Use retry logic to handle submission
        response, retry_state = self.retry_logic.execute_with_retry(
            api_client=self.api_client,
            submission_func=self.api_client.update_catalog,
            tracking_id=tracking_id,
            idempotency_key=idempotency_key,
            item=item,
            tenant_id=tenant_id,
            original_catalog_id=original_catalog_id
        )
        
        return response, retry_state
    
    def _generate_idempotency_key(
        self,
        tracking_id: str,
        item_id: str,
        fingerprint: str
    ) -> str:
        """
        Generate deterministic idempotency key.
        
        Requirements: 9.1
        """
        # Combine tracking_id, item_id, and fingerprint for uniqueness
        return f"{tracking_id}:{item_id}:{fingerprint}"
    
    def close(self):
        """Close resources"""
        if self.api_client:
            self.api_client.close()
