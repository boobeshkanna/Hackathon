"""
Unit tests for new data models (Task 2.2)
"""
import pytest
from datetime import datetime
from backend.models import (
    # Core models
    LocalQueueEntry,
    CatalogProcessingRecord,
    CSI,
    ExtractedAttributes,
    Price,
    ItemDescriptor,
    ONDCCatalogItem,
    # Tenant models
    TenantConfiguration,
    ArtisanProfile,
    TenantQuotaUsage,
    # Response models
    UploadResponse,
    UploadCompleteResponse,
    StatusUpdate,
    ErrorDetail,
    # Enums
    ProcessingStatus,
    QueueStatus,
    LanguageCode,
)


class TestLocalQueueEntry:
    """Test LocalQueueEntry model for edge client"""
    
    def test_local_queue_entry_creation(self):
        """Test creating a local queue entry"""
        entry = LocalQueueEntry(
            local_id="local_123",
            photo_path="/storage/photo.jpg",
            audio_path="/storage/audio.opus",
            photo_size=1024000,
            audio_size=512000
        )
        
        assert entry.local_id == "local_123"
        assert entry.sync_status == QueueStatus.QUEUED
        assert entry.retry_count == 0
        assert entry.tracking_id is None
        assert isinstance(entry.captured_at, datetime)
    
    def test_local_queue_entry_with_tracking_id(self):
        """Test queue entry after upload initiation"""
        entry = LocalQueueEntry(
            local_id="local_123",
            photo_path="/storage/photo.jpg",
            audio_path="/storage/audio.opus",
            photo_size=1024000,
            audio_size=512000,
            tracking_id="trk_abc123",
            sync_status=QueueStatus.SYNCING
        )
        
        assert entry.tracking_id == "trk_abc123"
        assert entry.sync_status == QueueStatus.SYNCING


class TestCatalogProcessingRecord:
    """Test CatalogProcessingRecord model"""
    
    def test_catalog_processing_record_creation(self):
        """Test creating a catalog processing record"""
        record = CatalogProcessingRecord(
            tracking_id="trk_abc123",
            tenant_id="tenant_001",
            artisan_id="artisan_001",
            photo_key="photos/abc123.jpg",
            audio_key="audio/abc123.opus",
            language=LanguageCode.HINDI
        )
        
        assert record.tracking_id == "trk_abc123"
        assert record.asr_status == ProcessingStatus.PENDING
        assert record.vision_status == ProcessingStatus.PENDING
        assert record.extraction_status == ProcessingStatus.PENDING
        assert record.mapping_status == ProcessingStatus.PENDING
        assert record.submission_status == ProcessingStatus.PENDING
        assert isinstance(record.created_at, datetime)
    
    def test_catalog_processing_record_with_results(self):
        """Test record with processing results"""
        record = CatalogProcessingRecord(
            tracking_id="trk_abc123",
            tenant_id="tenant_001",
            artisan_id="artisan_001",
            photo_key="photos/abc123.jpg",
            audio_key="audio/abc123.opus",
            language=LanguageCode.HINDI,
            asr_status=ProcessingStatus.COMPLETED,
            asr_result={"transcription": "यह एक साड़ी है", "confidence": 0.95},
            vision_status=ProcessingStatus.COMPLETED,
            vision_result={"category": "saree", "colors": ["red", "gold"]}
        )
        
        assert record.asr_status == ProcessingStatus.COMPLETED
        assert record.asr_result["confidence"] == 0.95
        assert "red" in record.vision_result["colors"]


class TestExtractedAttributes:
    """Test ExtractedAttributes model"""
    
    def test_extracted_attributes_creation(self):
        """Test creating extracted attributes"""
        attrs = ExtractedAttributes(
            category="Handloom Saree",
            subcategory="Banarasi Silk",
            material=["silk", "zari"],
            colors=["red", "gold"],
            short_description="Beautiful Banarasi silk saree",
            long_description="Traditional handwoven Banarasi silk saree with intricate zari work",
            price={"value": 5000, "currency": "INR"}
        )
        
        assert attrs.category == "Handloom Saree"
        assert "silk" in attrs.material
        assert attrs.price["value"] == 5000
    
    def test_extracted_attributes_with_csi(self):
        """Test attributes with cultural specific items"""
        csi = CSI(
            vernacular_term="बनारसी",
            transliteration="Banarasi",
            english_context="Traditional silk weaving from Varanasi",
            cultural_significance="UNESCO recognized craft heritage"
        )
        
        attrs = ExtractedAttributes(
            category="Handloom Saree",
            material=["silk"],
            colors=["red"],
            short_description="Banarasi saree",
            long_description="Traditional Banarasi silk saree",
            csis=[csi],
            craft_technique="Handwoven on pit loom",
            region_of_origin="Varanasi, Uttar Pradesh"
        )
        
        assert len(attrs.csis) == 1
        assert attrs.csis[0].vernacular_term == "बनारसी"
        assert attrs.craft_technique == "Handwoven on pit loom"


class TestONDCCatalogItem:
    """Test ONDC catalog item model"""
    
    def test_ondc_catalog_item_creation(self):
        """Test creating ONDC catalog item"""
        descriptor = ItemDescriptor(
            name="Banarasi Silk Saree",
            short_desc="Traditional handwoven silk saree",
            long_desc="Beautiful Banarasi silk saree with intricate zari work from Varanasi",
            images=["https://example.com/image1.jpg"]
        )
        
        price = Price(currency="INR", value="5000")
        
        item = ONDCCatalogItem(
            id="item_abc123",
            descriptor=descriptor,
            price=price,
            category_id="Fashion:Ethnic Wear:Sarees",
            tags={"material": "silk", "color": "red"}
        )
        
        assert item.id == "item_abc123"
        assert item.price.value == "5000"
        assert item.category_id == "Fashion:Ethnic Wear:Sarees"
        assert item.tags["material"] == "silk"
    
    def test_item_descriptor_validation(self):
        """Test descriptor field validation"""
        # Test name length validation
        with pytest.raises(ValueError):
            ItemDescriptor(
                name="A" * 101,  # Exceeds 100 chars
                short_desc="Short description",
                long_desc="Long description",
                images=[]
            )
        
        # Test short_desc length validation
        with pytest.raises(ValueError):
            ItemDescriptor(
                name="Valid name",
                short_desc="A" * 501,  # Exceeds 500 chars
                long_desc="Long description",
                images=[]
            )


class TestTenantConfiguration:
    """Test TenantConfiguration model"""
    
    def test_tenant_configuration_creation(self):
        """Test creating tenant configuration"""
        config = TenantConfiguration(
            tenant_id="tenant_001",
            tenant_name="Artisan Cooperative",
            default_language=LanguageCode.HINDI,
            supported_languages=[LanguageCode.HINDI, LanguageCode.TAMIL],
            ondc_seller_id="seller_001",
            ondc_api_key="api_key_123",
            ondc_bpp_id="bpp_001",
            contact_email="contact@example.com"
        )
        
        assert config.tenant_id == "tenant_001"
        assert config.default_language == LanguageCode.HINDI
        assert len(config.supported_languages) == 2
        assert config.monthly_catalog_quota == 1000  # Default value
        assert config.is_active is True


class TestArtisanProfile:
    """Test ArtisanProfile model"""
    
    def test_artisan_profile_creation(self):
        """Test creating artisan profile"""
        profile = ArtisanProfile(
            artisan_id="artisan_001",
            tenant_id="tenant_001",
            name="Ramesh Kumar",
            phone_number="+919876543210",
            preferred_language=LanguageCode.HINDI,
            region="Uttar Pradesh",
            district="Varanasi",
            craft_type="Handloom",
            specialization="Banarasi Silk Weaving"
        )
        
        assert profile.artisan_id == "artisan_001"
        assert profile.preferred_language == LanguageCode.HINDI
        assert profile.craft_type == "Handloom"
        assert profile.total_catalogs_created == 0  # Default value
        assert profile.is_active is True
    
    def test_artisan_profile_with_statistics(self):
        """Test profile with statistics"""
        profile = ArtisanProfile(
            artisan_id="artisan_001",
            tenant_id="tenant_001",
            name="Ramesh Kumar",
            phone_number="+919876543210",
            preferred_language=LanguageCode.HINDI,
            total_catalogs_created=50,
            total_catalogs_published=45
        )
        
        assert profile.total_catalogs_created == 50
        assert profile.total_catalogs_published == 45


class TestTenantQuotaUsage:
    """Test TenantQuotaUsage model"""
    
    def test_tenant_quota_usage_creation(self):
        """Test creating tenant quota usage"""
        usage = TenantQuotaUsage(
            tenant_id="tenant_001",
            month="2024-02",
            catalogs_created=150,
            catalogs_published=140,
            storage_used_gb=25.5,
            api_requests=5000,
            processing_cost_usd=75.50,
            storage_cost_usd=10.25
        )
        
        assert usage.tenant_id == "tenant_001"
        assert usage.month == "2024-02"
        assert usage.catalogs_created == 150
        assert usage.processing_cost_usd == 75.50


class TestResponseModels:
    """Test new response models"""
    
    def test_upload_response(self):
        """Test UploadResponse model"""
        response = UploadResponse(
            tracking_id="trk_abc123",
            upload_url="https://s3.amazonaws.com/bucket/path",
            expires_at=datetime.utcnow()
        )
        
        assert response.tracking_id == "trk_abc123"
        assert "s3.amazonaws.com" in response.upload_url
    
    def test_upload_complete_response(self):
        """Test UploadCompleteResponse model"""
        response = UploadCompleteResponse(
            tracking_id="trk_abc123"
        )
        
        assert response.status == "accepted"
        assert response.tracking_id == "trk_abc123"
    
    def test_status_update(self):
        """Test StatusUpdate model"""
        update = StatusUpdate(
            tracking_id="trk_abc123",
            stage="completed",
            message="Processing completed successfully",
            catalog_id="ondc_cat_789"
        )
        
        assert update.tracking_id == "trk_abc123"
        assert update.stage == "completed"
        assert update.catalog_id == "ondc_cat_789"
    
    def test_error_detail(self):
        """Test ErrorDetail model"""
        detail = ErrorDetail(
            field="language",
            issue="Unsupported language code",
            code="INVALID_LANGUAGE"
        )
        
        assert detail.field == "language"
        assert detail.code == "INVALID_LANGUAGE"
