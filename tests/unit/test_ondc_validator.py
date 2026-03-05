"""
Unit tests for ONDC Validator

Tests validation of ONDC catalog items against Beckn protocol requirements.
"""
import pytest
from backend.models.catalog import ONDCCatalogItem, ItemDescriptor, Price
from backend.services.ondc_gateway.validator import (
    ONDCValidator,
    ValidationError,
    ValidationResult,
    validate_ondc_payload
)


class TestONDCValidator:
    """Test ONDCValidator class"""
    
    def test_valid_item(self):
        """Test validation passes for valid item"""
        item = ONDCCatalogItem(
            id="item_abc123",
            descriptor=ItemDescriptor(
                name="Handwoven Silk Saree",
                short_desc="Beautiful handwoven silk saree with traditional motifs",
                long_desc="This exquisite handwoven silk saree features intricate traditional motifs and vibrant colors.",
                images=["https://example.com/image1.jpg"]
            ),
            price=Price(currency="INR", value="5000"),
            category_id="Fashion:Ethnic Wear:Sarees"
        )
        
        validator = ONDCValidator()
        result = validator.validate(item)
        
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_missing_required_fields(self):
        """Test validation fails for missing required fields"""
        item = ONDCCatalogItem(
            id="",  # Missing ID
            descriptor=ItemDescriptor(
                name="",  # Missing name
                short_desc="Description",
                long_desc="Long description",
                images=[]  # Missing images
            ),
            price=Price(currency="INR", value=""),  # Missing price value
            category_id=""  # Missing category
        )
        
        validator = ONDCValidator()
        result = validator.validate(item)
        
        assert not result.is_valid
        assert len(result.errors) > 0
        
        error_fields = [e.field for e in result.errors]
        assert "id" in error_fields
        assert "descriptor.name" in error_fields
        assert "price.value" in error_fields
        assert "category_id" in error_fields
        assert "descriptor.images" in error_fields
    
    def test_name_length_validation(self):
        """Test name length constraint"""
        long_name = "A" * 150
        # Use model_construct to bypass Pydantic validation
        descriptor = ItemDescriptor.model_construct(
            name=long_name,
            short_desc="Description",
            long_desc="Long description",
            images=["https://example.com/image.jpg"]
        )
        item = ONDCCatalogItem.model_construct(
            id="item_123",
            descriptor=descriptor,
            price=Price(currency="INR", value="1000"),
            category_id="General:Handicrafts"
        )
        
        validator = ONDCValidator()
        result = validator.validate(item)
        
        assert not result.is_valid
        name_errors = [e for e in result.errors if e.field == "descriptor.name"]
        assert len(name_errors) > 0
        assert "100 characters" in name_errors[0].message
    
    def test_short_desc_length_validation(self):
        """Test short description length constraint"""
        long_desc = "A" * 600
        # Use model_construct to bypass Pydantic validation
        descriptor = ItemDescriptor.model_construct(
            name="Product",
            short_desc=long_desc,
            long_desc="Long description",
            images=["https://example.com/image.jpg"]
        )
        item = ONDCCatalogItem.model_construct(
            id="item_123",
            descriptor=descriptor,
            price=Price(currency="INR", value="1000"),
            category_id="General:Handicrafts"
        )
        
        validator = ONDCValidator()
        result = validator.validate(item)
        
        assert not result.is_valid
        desc_errors = [e for e in result.errors if e.field == "descriptor.short_desc"]
        assert len(desc_errors) > 0
        assert "500 characters" in desc_errors[0].message
    
    def test_invalid_price_format(self):
        """Test price format validation"""
        item = ONDCCatalogItem(
            id="item_123",
            descriptor=ItemDescriptor(
                name="Product",
                short_desc="Description",
                long_desc="Long description",
                images=["https://example.com/image.jpg"]
            ),
            price=Price(currency="INR", value="not_a_number"),
            category_id="General:Handicrafts"
        )
        
        validator = ONDCValidator()
        result = validator.validate(item)
        
        assert not result.is_valid
        price_errors = [e for e in result.errors if e.field == "price.value"]
        assert len(price_errors) > 0
        assert "numeric" in price_errors[0].message.lower()
    
    def test_invalid_currency_format(self):
        """Test currency format validation"""
        item = ONDCCatalogItem(
            id="item_123",
            descriptor=ItemDescriptor(
                name="Product",
                short_desc="Description",
                long_desc="Long description",
                images=["https://example.com/image.jpg"]
            ),
            price=Price(currency="INVALID", value="1000"),
            category_id="General:Handicrafts"
        )
        
        validator = ONDCValidator()
        result = validator.validate(item)
        
        assert not result.is_valid
        currency_errors = [e for e in result.errors if e.field == "price.currency"]
        assert len(currency_errors) > 0
    
    def test_price_range_validation(self):
        """Test price range constraints"""
        # Test negative price
        item_negative = ONDCCatalogItem(
            id="item_123",
            descriptor=ItemDescriptor(
                name="Product",
                short_desc="Description",
                long_desc="Long description",
                images=["https://example.com/image.jpg"]
            ),
            price=Price(currency="INR", value="-100"),
            category_id="General:Handicrafts"
        )
        
        validator = ONDCValidator()
        result = validator.validate(item_negative)
        
        assert not result.is_valid
        price_errors = [e for e in result.errors if e.field == "price.value" and e.error_type == "range"]
        assert len(price_errors) > 0
    
    def test_invalid_image_url(self):
        """Test image URL validation"""
        item = ONDCCatalogItem(
            id="item_123",
            descriptor=ItemDescriptor(
                name="Product",
                short_desc="Description",
                long_desc="Long description",
                images=["not_a_valid_url", "https://example.com/valid.jpg"]
            ),
            price=Price(currency="INR", value="1000"),
            category_id="General:Handicrafts"
        )
        
        validator = ONDCValidator()
        result = validator.validate(item)
        
        assert not result.is_valid
        image_errors = [e for e in result.errors if "images" in e.field]
        assert len(image_errors) > 0
    
    def test_invalid_item_id_format(self):
        """Test item ID format validation"""
        item = ONDCCatalogItem(
            id="item with spaces!@#",
            descriptor=ItemDescriptor(
                name="Product",
                short_desc="Description",
                long_desc="Long description",
                images=["https://example.com/image.jpg"]
            ),
            price=Price(currency="INR", value="1000"),
            category_id="General:Handicrafts"
        )
        
        validator = ONDCValidator()
        result = validator.validate(item)
        
        assert not result.is_valid
        id_errors = [e for e in result.errors if e.field == "id"]
        assert len(id_errors) > 0


class TestValidationResult:
    """Test ValidationResult class"""
    
    def test_valid_result(self):
        """Test valid result representation"""
        result = ValidationResult(is_valid=True, errors=[])
        
        assert result.is_valid
        assert bool(result) is True
        assert len(result.errors) == 0
    
    def test_invalid_result(self):
        """Test invalid result representation"""
        errors = [
            ValidationError("field1", "Error 1"),
            ValidationError("field2", "Error 2")
        ]
        result = ValidationResult(is_valid=False, errors=errors)
        
        assert not result.is_valid
        assert bool(result) is False
        assert len(result.errors) == 2
    
    def test_to_dict(self):
        """Test conversion to dictionary"""
        errors = [ValidationError("field1", "Error 1")]
        result = ValidationResult(is_valid=False, errors=errors)
        
        result_dict = result.to_dict()
        
        assert result_dict["is_valid"] is False
        assert len(result_dict["errors"]) == 1
        assert result_dict["errors"][0]["field"] == "field1"


class TestValidationError:
    """Test ValidationError class"""
    
    def test_error_creation(self):
        """Test error creation"""
        error = ValidationError("field_name", "Error message", "validation")
        
        assert error.field == "field_name"
        assert error.message == "Error message"
        assert error.error_type == "validation"
    
    def test_to_dict(self):
        """Test conversion to dictionary"""
        error = ValidationError("field_name", "Error message", "format")
        
        error_dict = error.to_dict()
        
        assert error_dict["field"] == "field_name"
        assert error_dict["message"] == "Error message"
        assert error_dict["error_type"] == "format"


class TestValidateOndcPayload:
    """Test validate_ondc_payload convenience function"""
    
    def test_convenience_function(self):
        """Test convenience function works correctly"""
        item = ONDCCatalogItem(
            id="item_123",
            descriptor=ItemDescriptor(
                name="Product",
                short_desc="Description",
                long_desc="Long description",
                images=["https://example.com/image.jpg"]
            ),
            price=Price(currency="INR", value="1000"),
            category_id="General:Handicrafts"
        )
        
        result = validate_ondc_payload(item)
        
        assert isinstance(result, ValidationResult)
        assert result.is_valid
