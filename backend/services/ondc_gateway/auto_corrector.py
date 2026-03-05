"""
ONDC Auto-Corrector - Automatically corrects common validation errors

This module implements automatic correction for common validation errors
and flags uncorrectable errors for manual review.

Requirements: 8.3, 8.4
"""
import logging
from typing import List, Optional, Tuple
from backend.models.catalog import ONDCCatalogItem, ItemDescriptor
from backend.services.ondc_gateway.validator import ValidationError, ValidationResult


logger = logging.getLogger(__name__)


class CorrectionResult:
    """Result of auto-correction operation"""
    
    def __init__(
        self,
        corrected_item: Optional[ONDCCatalogItem],
        corrections_applied: List[str],
        manual_review_required: bool,
        uncorrectable_errors: List[ValidationError]
    ):
        self.corrected_item = corrected_item
        self.corrections_applied = corrections_applied
        self.manual_review_required = manual_review_required
        self.uncorrectable_errors = uncorrectable_errors
    
    def __repr__(self):
        return (
            f"CorrectionResult("
            f"corrections={len(self.corrections_applied)}, "
            f"manual_review={self.manual_review_required})"
        )
    
    def to_dict(self):
        return {
            'corrected': self.corrected_item is not None,
            'corrections_applied': self.corrections_applied,
            'manual_review_required': self.manual_review_required,
            'uncorrectable_errors': [e.to_dict() for e in self.uncorrectable_errors]
        }


class ONDCAutoCorrector:
    """
    Automatically corrects common validation errors in ONDC catalog items.
    
    Requirements: 8.3, 8.4
    """
    
    def __init__(self):
        self.corrections_applied = []
    
    def auto_correct(
        self,
        item: ONDCCatalogItem,
        validation_result: ValidationResult
    ) -> CorrectionResult:
        """
        Attempt to automatically correct validation errors.
        
        Args:
            item: Original ONDC catalog item
            validation_result: Validation result with errors
        
        Returns:
            CorrectionResult: Result of correction attempt
        
        Requirements: 8.3, 8.4
        """
        if validation_result.is_valid:
            return CorrectionResult(
                corrected_item=item,
                corrections_applied=[],
                manual_review_required=False,
                uncorrectable_errors=[]
            )
        
        self.corrections_applied = []
        corrected_item = item.model_copy(deep=True)
        uncorrectable_errors = []
        
        for error in validation_result.errors:
            corrected = self._correct_error(corrected_item, error)
            if not corrected:
                uncorrectable_errors.append(error)
        
        # Log corrections to CloudWatch
        if self.corrections_applied:
            logger.info(
                f"Auto-corrections applied to item {item.id}: "
                f"{', '.join(self.corrections_applied)}"
            )
        
        # Log uncorrectable errors to CloudWatch
        if uncorrectable_errors:
            logger.warning(
                f"Uncorrectable validation errors for item {item.id}: "
                f"{[e.to_dict() for e in uncorrectable_errors]}"
            )
        
        return CorrectionResult(
            corrected_item=corrected_item if not uncorrectable_errors else None,
            corrections_applied=self.corrections_applied,
            manual_review_required=len(uncorrectable_errors) > 0,
            uncorrectable_errors=uncorrectable_errors
        )
    
    def _correct_error(self, item: ONDCCatalogItem, error: ValidationError) -> bool:
        """
        Attempt to correct a single validation error.
        
        Returns:
            bool: True if error was corrected, False if manual review needed
        """
        field = error.field
        error_type = error.error_type
        
        # Handle length errors
        if error_type == 'length':
            return self._correct_length_error(item, field)
        
        # Handle format errors
        if error_type == 'format':
            return self._correct_format_error(item, field)
        
        # Handle required field errors
        if error_type == 'required':
            return self._correct_required_error(item, field)
        
        # Handle range errors
        if error_type == 'range':
            return self._correct_range_error(item, field)
        
        return False
    
    def _correct_length_error(self, item: ONDCCatalogItem, field: str) -> bool:
        """Correct field length violations by truncating."""
        if field == 'descriptor.name':
            if item.descriptor and item.descriptor.name:
                original_length = len(item.descriptor.name)
                item.descriptor.name = self._truncate_at_word_boundary(
                    item.descriptor.name, 100
                )
                self.corrections_applied.append(
                    f"Truncated name from {original_length} to {len(item.descriptor.name)} chars"
                )
                return True
        
        elif field == 'descriptor.short_desc':
            if item.descriptor and item.descriptor.short_desc:
                original_length = len(item.descriptor.short_desc)
                item.descriptor.short_desc = self._truncate_at_word_boundary(
                    item.descriptor.short_desc, 500
                )
                self.corrections_applied.append(
                    f"Truncated short_desc from {original_length} to {len(item.descriptor.short_desc)} chars"
                )
                return True
        
        elif field == 'descriptor.long_desc':
            if item.descriptor and item.descriptor.long_desc:
                original_length = len(item.descriptor.long_desc)
                item.descriptor.long_desc = self._truncate_at_word_boundary(
                    item.descriptor.long_desc, 5000
                )
                self.corrections_applied.append(
                    f"Truncated long_desc from {original_length} to {len(item.descriptor.long_desc)} chars"
                )
                return True
        
        elif field == 'category_id':
            if item.category_id:
                original_length = len(item.category_id)
                item.category_id = item.category_id[:200]
                self.corrections_applied.append(
                    f"Truncated category_id from {original_length} to {len(item.category_id)} chars"
                )
                return True
        
        return False
    
    def _correct_format_error(self, item: ONDCCatalogItem, field: str) -> bool:
        """Correct format violations."""
        if field == 'price.value':
            if item.price and item.price.value:
                # Try to extract numeric value from string
                cleaned = self._extract_numeric_value(item.price.value)
                if cleaned:
                    item.price.value = cleaned
                    self.corrections_applied.append(
                        f"Cleaned price value to numeric format: {cleaned}"
                    )
                    return True
        
        elif field == 'price.currency':
            if item.price and item.price.currency:
                # Normalize currency to uppercase 3-letter code
                normalized = item.price.currency.upper().strip()
                if len(normalized) == 3 and normalized.isalpha():
                    item.price.currency = normalized
                    self.corrections_applied.append(
                        f"Normalized currency to: {normalized}"
                    )
                    return True
                # Default to INR if invalid
                item.price.currency = 'INR'
                self.corrections_applied.append("Set default currency to INR")
                return True
        
        elif field == 'id':
            if item.id:
                # Remove invalid characters from ID
                cleaned = ''.join(c for c in item.id if c.isalnum() or c in '_-')
                if cleaned:
                    item.id = cleaned
                    self.corrections_applied.append(
                        f"Cleaned item ID to valid format: {cleaned}"
                    )
                    return True
        
        elif field.startswith('descriptor.images['):
            # Cannot auto-correct invalid image URLs
            return False
        
        return False
    
    def _correct_required_error(self, item: ONDCCatalogItem, field: str) -> bool:
        """Correct missing required fields with defaults."""
        if field == 'descriptor.name':
            if item.descriptor:
                item.descriptor.name = "Handcrafted Product"
                self.corrections_applied.append("Set default product name")
                return True
        
        elif field == 'descriptor.short_desc':
            if item.descriptor:
                item.descriptor.short_desc = "Handcrafted artisan product"
                self.corrections_applied.append("Set default short description")
                return True
        
        elif field == 'descriptor.long_desc':
            if item.descriptor:
                item.descriptor.long_desc = "This is a handcrafted artisan product made with traditional techniques."
                self.corrections_applied.append("Set default long description")
                return True
        
        elif field == 'price.value':
            if item.price:
                item.price.value = "0"
                self.corrections_applied.append("Set default price value to 0")
                return True
        
        elif field == 'category_id':
            item.category_id = "General:Handicrafts"
            self.corrections_applied.append("Set default category")
            return True
        
        # Cannot auto-correct missing ID or images - require manual review
        elif field in ['id', 'descriptor.images']:
            return False
        
        return False
    
    def _correct_range_error(self, item: ONDCCatalogItem, field: str) -> bool:
        """Correct value range violations."""
        if field == 'price.value':
            if item.price and item.price.value:
                try:
                    price_value = float(item.price.value)
                    if price_value < 0:
                        item.price.value = "0"
                        self.corrections_applied.append("Corrected negative price to 0")
                        return True
                    elif price_value > 10000000:
                        item.price.value = "10000000"
                        self.corrections_applied.append("Capped price at maximum value")
                        return True
                except ValueError:
                    pass
        
        return False
    
    @staticmethod
    def _truncate_at_word_boundary(text: str, max_length: int) -> str:
        """Truncate text at word boundary to avoid cutting words."""
        if len(text) <= max_length:
            return text
        
        # Find last space before max_length, accounting for '...' suffix
        truncated = text[:max_length-3].rsplit(' ', 1)[0]
        return truncated + '...'
    
    @staticmethod
    def _extract_numeric_value(value: str) -> Optional[str]:
        """Extract numeric value from string (e.g., '₹500' -> '500')."""
        import re
        # Remove currency symbols and non-numeric characters except decimal point
        cleaned = re.sub(r'[^\d.]', '', value)
        
        # Validate it's a valid number
        try:
            float(cleaned)
            return cleaned
        except ValueError:
            return None


def auto_correct_validation_errors(
    item: ONDCCatalogItem,
    validation_result: ValidationResult
) -> CorrectionResult:
    """
    Convenience function to auto-correct validation errors.
    
    Args:
        item: Original ONDC catalog item
        validation_result: Validation result with errors
    
    Returns:
        CorrectionResult: Result of correction attempt
    
    Requirements: 8.3, 8.4
    """
    corrector = ONDCAutoCorrector()
    return corrector.auto_correct(item, validation_result)
