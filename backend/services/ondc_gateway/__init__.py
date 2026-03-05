"""
ONDC Gateway Service - Schema mapping, validation, and submission to ONDC

This module provides functionality to transform extracted product attributes
to ONDC/Beckn protocol format, validate against schema requirements, and
auto-correct common validation errors.
"""
from backend.services.ondc_gateway.schema_mapper import (
    map_to_beckn_item,
    build_long_description,
    map_category_to_ondc,
    generate_item_id,
    CATEGORY_MAPPING
)
from backend.services.ondc_gateway.validator import (
    ONDCValidator,
    ValidationError,
    ValidationResult,
    validate_ondc_payload
)
from backend.services.ondc_gateway.auto_corrector import (
    ONDCAutoCorrector,
    CorrectionResult,
    auto_correct_validation_errors
)
from backend.services.ondc_gateway.api_client import (
    ONDCAPIClient,
    ONDCResponse,
    ONDCAPIError,
    ONDCAuthenticationError,
    ONDCValidationError,
    ONDCNetworkError
)
from backend.services.ondc_gateway.retry_logic import (
    RetryLogic,
    RetryState,
    ErrorCategory
)
from backend.services.ondc_gateway.audit_logger import (
    ONDCAuditLogger,
    AuditLogEntry,
    SubmissionStatus,
    create_audit_log_table
)
from backend.services.ondc_gateway.update_detector import (
    ONDCUpdateDetector,
    UpdateDetectionResult,
    CatalogVersion,
    create_catalog_tables
)
from backend.services.ondc_gateway.gateway import (
    ONDCGateway,
    ONDCGatewayResult
)


__all__ = [
    # Schema Mapper
    'map_to_beckn_item',
    'build_long_description',
    'map_category_to_ondc',
    'generate_item_id',
    'CATEGORY_MAPPING',
    
    # Validator
    'ONDCValidator',
    'ValidationError',
    'ValidationResult',
    'validate_ondc_payload',
    
    # Auto-Corrector
    'ONDCAutoCorrector',
    'CorrectionResult',
    'auto_correct_validation_errors',
    
    # API Client
    'ONDCAPIClient',
    'ONDCResponse',
    'ONDCAPIError',
    'ONDCAuthenticationError',
    'ONDCValidationError',
    'ONDCNetworkError',
    
    # Retry Logic
    'RetryLogic',
    'RetryState',
    'ErrorCategory',
    
    # Audit Logger
    'ONDCAuditLogger',
    'AuditLogEntry',
    'SubmissionStatus',
    'create_audit_log_table',
    
    # Update Detector
    'ONDCUpdateDetector',
    'UpdateDetectionResult',
    'CatalogVersion',
    'create_catalog_tables',
    
    # Gateway
    'ONDCGateway',
    'ONDCGatewayResult',
]
