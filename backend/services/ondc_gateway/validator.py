"""
ONDC Schema Validator - Validates catalog items against Beckn protocol

This module implements JSON Schema validation for ONDC/Beckn protocol compliance.

Requirements: 8.2, 8.5
"""
import re
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
from backend.models.catalog import ONDCCatalogItem


class ValidationError:
    """Represents a single validation error"""
    
    def __init__(self, field: str, message: str, error_type: str = 'validation'):
        self.field = field
        self.message = message
        self.error_type = error_type
    
    def __repr__(self):
        return f"ValidationError(field='{self.field}', message='{self.message}')"
    
    def to_dict(self) -> Dict[str, str]:
        return {
            'field': self.field,
            'message': self.message,
            'error_type': self.error_type
        }


class ValidationResult:
    """Result of validation operation"""
    
    def __init__(self, is_valid: bool, errors: Optional[List[ValidationError]] = None):
        self.is_valid = is_valid
        self.errors = errors or []
    
    def __bool__(self):
        return self.is_valid
    
    def __repr__(self):
        if self.is_valid:
            return "ValidationResult(is_valid=True)"
        return f"ValidationResult(is_valid=False, errors={len(self.errors)})"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'is_valid': self.is_valid,
            'errors': [e.to_dict() for e in self.errors]
        }


class ONDCValidator:
    """
    Validates ONDC catalog items against Beckn protocol schema.
    
    Requirements: 8.2, 8.5
    """
    
    # Field length constraints
    MAX_NAME_LENGTH = 100
    MAX_SHORT_DESC_LENGTH = 500
    MAX_LONG_DESC_LENGTH = 5000
    MAX_CATEGORY_LENGTH = 200
    
    # Price constraints
    MIN_PRICE = 0.0
    MAX_PRICE = 10000000.0  # 1 crore INR
    
    def validate(self, item: ONDCCatalogItem) -> ValidationResult:
        """
        Validate ONDC catalog item against Beckn protocol requirements.
        
        Args:
            item: ONDCCatalogItem to validate
        
        Returns:
            ValidationResult: Validation result with errors if any
        
        Requirements: 8.2, 8.5
        """
        errors = []
        
        # Validate required fields
        errors.extend(self._validate_required_fields(item))
        
        # Validate field formats
        errors.extend(self._validate_formats(item))
        
        # Validate length constraints
        errors.extend(self._validate_lengths(item))
        
        # Validate price
        errors.extend(self._validate_price(item))
        
        # Validate images
        errors.extend(self._validate_images(item))
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors
        )
    
    def _validate_required_fields(self, item: ONDCCatalogItem) -> List[ValidationError]:
        """
        Validate that all required fields are present and non-empty.
        
        Requirements: 8.5
        """
        errors = []
        
        # Item ID is required
        if not item.id or not item.id.strip():
            errors.append(ValidationError(
                field='id',
                message='Item ID is required',
                error_type='required'
            ))
        
        # Descriptor is required
        if not item.descriptor:
            errors.append(ValidationError(
                field='descriptor',
                message='Item descriptor is required',
                error_type='required'
            ))
            return errors  # Can't validate descriptor fields if descriptor is missing
        
        # Descriptor.name is required
        if not item.descriptor.name or not item.descriptor.name.strip():
            errors.append(ValidationError(
                field='descriptor.name',
                message='Product name is required',
                error_type='required'
            ))
        
        # Descriptor.short_desc is required
        if not item.descriptor.short_desc or not item.descriptor.short_desc.strip():
            errors.append(ValidationError(
                field='descriptor.short_desc',
                message='Short description is required',
                error_type='required'
            ))
        
        # Descriptor.long_desc is required
        if not item.descriptor.long_desc or not item.descriptor.long_desc.strip():
            errors.append(ValidationError(
                field='descriptor.long_desc',
                message='Long description is required',
                error_type='required'
            ))
        
        # Price is required
        if not item.price:
            errors.append(ValidationError(
                field='price',
                message='Price is required',
                error_type='required'
            ))
        elif not item.price.value or not item.price.value.strip():
            errors.append(ValidationError(
                field='price.value',
                message='Price value is required',
                error_type='required'
            ))
        
        # Category ID is required
        if not item.category_id or not item.category_id.strip():
            errors.append(ValidationError(
                field='category_id',
                message='Category ID is required',
                error_type='required'
            ))
        
        # At least one image is required
        if not item.descriptor.images or len(item.descriptor.images) == 0:
            errors.append(ValidationError(
                field='descriptor.images',
                message='At least one product image is required',
                error_type='required'
            ))
        
        return errors
    
    def _validate_formats(self, item: ONDCCatalogItem) -> List[ValidationError]:
        """
        Validate field formats (price format, URL format, etc.).
        
        Requirements: 8.2
        """
        errors = []
        
        # Validate price format (must be numeric string)
        if item.price and item.price.value:
            if not self._is_valid_price_format(item.price.value):
                errors.append(ValidationError(
                    field='price.value',
                    message='Price value must be a valid numeric string',
                    error_type='format'
                ))
        
        # Validate currency format (must be 3-letter code)
        if item.price and item.price.currency:
            if not self._is_valid_currency_format(item.price.currency):
                errors.append(ValidationError(
                    field='price.currency',
                    message='Currency must be a valid 3-letter ISO code (e.g., INR)',
                    error_type='format'
                ))
        
        # Validate item ID format (alphanumeric with underscores/hyphens)
        if item.id and not self._is_valid_id_format(item.id):
            errors.append(ValidationError(
                field='id',
                message='Item ID must contain only alphanumeric characters, underscores, and hyphens',
                error_type='format'
            ))
        
        return errors
    
    def _validate_lengths(self, item: ONDCCatalogItem) -> List[ValidationError]:
        """
        Validate field length constraints.
        
        Requirements: 8.2
        """
        errors = []
        
        if not item.descriptor:
            return errors
        
        # Validate name length
        if item.descriptor.name and len(item.descriptor.name) > self.MAX_NAME_LENGTH:
            errors.append(ValidationError(
                field='descriptor.name',
                message=f'Product name must be <= {self.MAX_NAME_LENGTH} characters (current: {len(item.descriptor.name)})',
                error_type='length'
            ))
        
        # Validate short description length
        if item.descriptor.short_desc and len(item.descriptor.short_desc) > self.MAX_SHORT_DESC_LENGTH:
            errors.append(ValidationError(
                field='descriptor.short_desc',
                message=f'Short description must be <= {self.MAX_SHORT_DESC_LENGTH} characters (current: {len(item.descriptor.short_desc)})',
                error_type='length'
            ))
        
        # Validate long description length
        if item.descriptor.long_desc and len(item.descriptor.long_desc) > self.MAX_LONG_DESC_LENGTH:
            errors.append(ValidationError(
                field='descriptor.long_desc',
                message=f'Long description must be <= {self.MAX_LONG_DESC_LENGTH} characters (current: {len(item.descriptor.long_desc)})',
                error_type='length'
            ))
        
        # Validate category ID length
        if item.category_id and len(item.category_id) > self.MAX_CATEGORY_LENGTH:
            errors.append(ValidationError(
                field='category_id',
                message=f'Category ID must be <= {self.MAX_CATEGORY_LENGTH} characters (current: {len(item.category_id)})',
                error_type='length'
            ))
        
        return errors
    
    def _validate_price(self, item: ONDCCatalogItem) -> List[ValidationError]:
        """
        Validate price value is within acceptable range.
        
        Requirements: 8.2
        """
        errors = []
        
        if not item.price or not item.price.value:
            return errors
        
        try:
            price_value = float(item.price.value)
            
            if price_value < self.MIN_PRICE:
                errors.append(ValidationError(
                    field='price.value',
                    message=f'Price must be >= {self.MIN_PRICE}',
                    error_type='range'
                ))
            
            if price_value > self.MAX_PRICE:
                errors.append(ValidationError(
                    field='price.value',
                    message=f'Price must be <= {self.MAX_PRICE}',
                    error_type='range'
                ))
        except ValueError:
            # Format error already caught in _validate_formats
            pass
        
        return errors
    
    def _validate_images(self, item: ONDCCatalogItem) -> List[ValidationError]:
        """
        Validate image URLs are valid and accessible.
        
        Requirements: 8.2
        """
        errors = []
        
        if not item.descriptor or not item.descriptor.images:
            return errors
        
        for i, img_url in enumerate(item.descriptor.images):
            if not img_url or not img_url.strip():
                errors.append(ValidationError(
                    field=f'descriptor.images[{i}]',
                    message='Image URL cannot be empty',
                    error_type='format'
                ))
            elif not self._is_valid_url(img_url):
                errors.append(ValidationError(
                    field=f'descriptor.images[{i}]',
                    message=f'Invalid image URL: {img_url}',
                    error_type='format'
                ))
        
        return errors
    
    @staticmethod
    def _is_valid_price_format(value: str) -> bool:
        """Check if price value is a valid numeric string."""
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def _is_valid_currency_format(currency: str) -> bool:
        """Check if currency is a valid 3-letter ISO code."""
        return bool(re.match(r'^[A-Z]{3}$', currency))
    
    @staticmethod
    def _is_valid_id_format(item_id: str) -> bool:
        """Check if item ID contains only valid characters."""
        return bool(re.match(r'^[a-zA-Z0-9_-]+$', item_id))
    
    @staticmethod
    def _is_valid_url(url: str) -> bool:
        """Check if URL is valid."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False


def validate_ondc_payload(item: ONDCCatalogItem) -> ValidationResult:
    """
    Convenience function to validate ONDC catalog item.
    
    Args:
        item: ONDCCatalogItem to validate
    
    Returns:
        ValidationResult: Validation result with errors if any
    
    Requirements: 8.2, 8.5
    """
    validator = ONDCValidator()
    return validator.validate(item)
