"""
Unit tests for ONDC Auto-Corrector

Tests automatic correction of validation errors.
"""
import pytest
from backend.models.catalog import ONDCCatalogItem, ItemDescriptor, Price
from backend.services.ondc_gateway.validator import (
    ONDCValidator,
    ValidationError,
    ValidationResult
)
from backend.services.ondc_gateway.auto_corrector import (
    ONDCAutoCorrector,
    CorrectionResult,
    auto_correct_validation_errors
)


class TestONDCAutoCorrector:
    """Test ONDCAutoCorrector class"""
    
    def test_no_corrections_needed(self):
        """Test that valid items don't get corrected"""
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
        
        validator = ONDCValidator()
        validation_result = validator.validate(item)
        
        corrector = ONDCAutoCorrector()
        result = corrector.auto_correct(item, validation_result)
        
        assert result.corrected_item is not None
        assert len(result.corrections_applied) == 0
        assert not result.manual_review_required
        assert len(result.uncorrectable_errors) == 0
    
    def test_truncate_long_name(self):
        """Test automatic truncation of long names"""
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
        validation_result = validator.validate(item)
        
        corrector = ONDCAutoCorrector()
        result = corrector.auto_correct(item, validation_result)
        
        assert result.corrected_item is not None
        assert len(result.corrected_item.descriptor.name) <= 100
        assert len(result.corrections_applied) > 0
        assert "Truncated name" in result.corrections_applied[0]
    
    def test_truncate_long_short_desc(self):
        """Test automatic truncation of long short descriptions"""
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
        validation_result = validator.validate(item)
        
        corrector = ONDCAutoCorrector()
        result = corrector.auto_correct(item, validation_result)
        
        assert result.corrected_item is not None
        assert len(result.corrected_item.descriptor.short_desc) <= 500
        assert any("short_desc" in c for c in result.corrections_applied)
    
    def test_clean_price_value(self):
        """Test automatic cleaning of price values"""
        item = ONDCCatalogItem(
            id="item_123",
            descriptor=ItemDescriptor(
                name="Product",
                short_desc="Description",
                long_desc="Long description",
                images=["https://example.com/image.jpg"]
            ),
            price=Price(currency="INR", value="₹1,000.50"),
            category_id="General:Handicrafts"
        )
        
        validator = ONDCValidator()
        validation_result = validator.validate(item)
        
        corrector = ONDCAutoCorrector()
        result = corrector.auto_correct(item, validation_result)
        
        assert result.corrected_item is not None
        assert result.corrected_item.price.value == "1000.50"
        assert any("price" in c.lower() for c in result.corrections_applied)
    
    def test_normalize_currency(self):
        """Test automatic normalization of currency codes"""
        item = ONDCCatalogItem(
            id="item_123",
            descriptor=ItemDescriptor(
                name="Product",
                short_desc="Description",
                long_desc="Long description",
                images=["https://example.com/image.jpg"]
            ),
            price=Price(currency="inr", value="1000"),  # lowercase
            category_id="General:Handicrafts"
        )
        
        validator = ONDCValidator()
        validation_result = validator.validate(item)
        
        corrector = ONDCAutoCorrector()
        result = corrector.auto_correct(item, validation_result)
        
        assert result.corrected_item is not None
        assert result.corrected_item.price.currency == "INR"
    
    def test_clean_item_id(self):
        """Test automatic cleaning of item IDs"""
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
        validation_result = validator.validate(item)
        
        corrector = ONDCAutoCorrector()
        result = corrector.auto_correct(item, validation_result)
        
        assert result.corrected_item is not None
        assert " " not in result.corrected_item.id
        assert "!" not in result.corrected_item.id
        assert any("ID" in c for c in result.corrections_applied)
    
    def test_set_default_name(self):
        """Test setting default name for missing names"""
        item = ONDCCatalogItem(
            id="item_123",
            descriptor=ItemDescriptor(
                name="",  # Empty name
                short_desc="Description",
                long_desc="Long description",
                images=["https://example.com/image.jpg"]
            ),
            price=Price(currency="INR", value="1000"),
            category_id="General:Handicrafts"
        )
        
        validator = ONDCValidator()
        validation_result = validator.validate(item)
        
        corrector = ONDCAutoCorrector()
        result = corrector.auto_correct(item, validation_result)
        
        assert result.corrected_item is not None
        assert result.corrected_item.descriptor.name == "Handcrafted Product"
        assert any("default product name" in c.lower() for c in result.corrections_applied)
    
    def test_set_default_category(self):
        """Test setting default category for missing categories"""
        item = ONDCCatalogItem(
            id="item_123",
            descriptor=ItemDescriptor(
                name="Product",
                short_desc="Description",
                long_desc="Long description",
                images=["https://example.com/image.jpg"]
            ),
            price=Price(currency="INR", value="1000"),
            category_id=""  # Empty category
        )
        
        validator = ONDCValidator()
        validation_result = validator.validate(item)
        
        corrector = ONDCAutoCorrector()
        result = corrector.auto_correct(item, validation_result)
        
        assert result.corrected_item is not None
        assert result.corrected_item.category_id == "General:Handicrafts"
        assert any("default category" in c.lower() for c in result.corrections_applied)
    
    def test_correct_negative_price(self):
        """Test correction of negative prices"""
        item = ONDCCatalogItem(
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
        validation_result = validator.validate(item)
        
        corrector = ONDCAutoCorrector()
        result = corrector.auto_correct(item, validation_result)
        
        assert result.corrected_item is not None
        assert result.corrected_item.price.value == "0"
        assert any("negative price" in c.lower() for c in result.corrections_applied)
    
    def test_uncorrectable_missing_images(self):
        """Test that missing images cannot be auto-corrected"""
        item = ONDCCatalogItem(
            id="item_123",
            descriptor=ItemDescriptor(
                name="Product",
                short_desc="Description",
                long_desc="Long description",
                images=[]  # No images
            ),
            price=Price(currency="INR", value="1000"),
            category_id="General:Handicrafts"
        )
        
        validator = ONDCValidator()
        validation_result = validator.validate(item)
        
        corrector = ONDCAutoCorrector()
        result = corrector.auto_correct(item, validation_result)
        
        assert result.corrected_item is None
        assert result.manual_review_required
        assert len(result.uncorrectable_errors) > 0
        assert any(e.field == "descriptor.images" for e in result.uncorrectable_errors)
    
    def test_uncorrectable_invalid_image_url(self):
        """Test that invalid image URLs cannot be auto-corrected"""
        item = ONDCCatalogItem(
            id="item_123",
            descriptor=ItemDescriptor(
                name="Product",
                short_desc="Description",
                long_desc="Long description",
                images=["not_a_valid_url"]
            ),
            price=Price(currency="INR", value="1000"),
            category_id="General:Handicrafts"
        )
        
        validator = ONDCValidator()
        validation_result = validator.validate(item)
        
        corrector = ONDCAutoCorrector()
        result = corrector.auto_correct(item, validation_result)
        
        assert result.corrected_item is None
        assert result.manual_review_required
        assert len(result.uncorrectable_errors) > 0
    
    def test_multiple_corrections(self):
        """Test multiple corrections applied together"""
        long_name = "A" * 150
        # Use model_construct to bypass Pydantic validation
        descriptor = ItemDescriptor.model_construct(
            name=long_name,
            short_desc="Description",
            long_desc="Long description",
            images=["https://example.com/image.jpg"]
        )
        item = ONDCCatalogItem.model_construct(
            id="item with spaces",
            descriptor=descriptor,
            price=Price(currency="inr", value="₹1,000"),
            category_id="General:Handicrafts"
        )
        
        validator = ONDCValidator()
        validation_result = validator.validate(item)
        
        corrector = ONDCAutoCorrector()
        result = corrector.auto_correct(item, validation_result)
        
        assert result.corrected_item is not None
        assert len(result.corrections_applied) >= 3  # Name, ID, currency, price
        assert not result.manual_review_required


class TestCorrectionResult:
    """Test CorrectionResult class"""
    
    def test_successful_correction(self):
        """Test successful correction result"""
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
        
        result = CorrectionResult(
            corrected_item=item,
            corrections_applied=["Correction 1", "Correction 2"],
            manual_review_required=False,
            uncorrectable_errors=[]
        )
        
        assert result.corrected_item is not None
        assert len(result.corrections_applied) == 2
        assert not result.manual_review_required
    
    def test_failed_correction(self):
        """Test failed correction result"""
        errors = [ValidationError("field1", "Error 1")]
        
        result = CorrectionResult(
            corrected_item=None,
            corrections_applied=[],
            manual_review_required=True,
            uncorrectable_errors=errors
        )
        
        assert result.corrected_item is None
        assert result.manual_review_required
        assert len(result.uncorrectable_errors) == 1
    
    def test_to_dict(self):
        """Test conversion to dictionary"""
        result = CorrectionResult(
            corrected_item=None,
            corrections_applied=["Correction 1"],
            manual_review_required=True,
            uncorrectable_errors=[ValidationError("field1", "Error 1")]
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["corrected"] is False
        assert len(result_dict["corrections_applied"]) == 1
        assert result_dict["manual_review_required"] is True
        assert len(result_dict["uncorrectable_errors"]) == 1


class TestAutoCorrectValidationErrors:
    """Test auto_correct_validation_errors convenience function"""
    
    def test_convenience_function(self):
        """Test convenience function works correctly"""
        # Use model_construct to bypass Pydantic validation
        descriptor = ItemDescriptor.model_construct(
            name="A" * 150,  # Too long
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
        validation_result = validator.validate(item)
        
        result = auto_correct_validation_errors(item, validation_result)
        
        assert isinstance(result, CorrectionResult)
        assert result.corrected_item is not None
        assert len(result.corrections_applied) > 0
