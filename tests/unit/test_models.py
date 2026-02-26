"""
Unit tests for data models
"""
import pytest
from datetime import datetime
from backend.models.catalog import (
    ProcessingStatus,
    MediaType,
    LanguageCode,
    MediaFile,
    VisionAnalysis,
    ASRTranscription,
    ONDCCatalogEntry,
    CatalogRecord
)
from backend.models.request import CatalogSubmissionRequest, CatalogQueryRequest
from backend.models.response import (
    CatalogSubmissionResponse,
    ErrorResponse,
    HealthCheckResponse
)


class TestCatalogModels:
    """Test catalog data models"""
    
    def test_media_file_creation(self):
        """Test MediaFile model creation"""
        media = MediaFile(
            file_id="test123",
            file_type=MediaType.IMAGE,
            s3_key="images/test.jpg",
            s3_bucket="test-bucket",
            file_size=1024,
            mime_type="image/jpeg"
        )
        
        assert media.file_id == "test123"
        assert media.file_type == MediaType.IMAGE
        assert media.file_size == 1024
        assert isinstance(media.uploaded_at, datetime)
    
    def test_vision_analysis(self):
        """Test VisionAnalysis model"""
        analysis = VisionAnalysis(
            objects_detected=["pottery", "clay"],
            colors=["brown", "red"],
            materials=["clay", "ceramic"],
            patterns=["geometric"],
            confidence_scores={"pottery": 0.95}
        )
        
        assert "pottery" in analysis.objects_detected
        assert analysis.confidence_scores["pottery"] == 0.95
    
    def test_asr_transcription(self):
        """Test ASRTranscription model"""
        transcription = ASRTranscription(
            text="यह एक मिट्टी का बर्तन है",
            language=LanguageCode.HINDI,
            confidence=0.92
        )
        
        assert transcription.language == LanguageCode.HINDI
        assert transcription.confidence == 0.92
        assert len(transcription.text) > 0

    
    def test_ondc_catalog_entry(self):
        """Test ONDCCatalogEntry model"""
        entry = ONDCCatalogEntry(
            product_name="Handcrafted Clay Pot",
            product_name_vernacular="मिट्टी का बर्तन",
            category="Home & Kitchen",
            description="Traditional handcrafted clay pot",
            description_vernacular="पारंपरिक हस्तनिर्मित मिट्टी का बर्तन",
            attributes={
                "material": "clay",
                "color": "brown",
                "size": "medium"
            },
            price=250.0,
            cultural_context="Traditional pottery from Rajasthan"
        )
        
        assert entry.product_name == "Handcrafted Clay Pot"
        assert entry.currency == "INR"
        assert entry.price == 250.0
        assert "material" in entry.attributes
    
    def test_catalog_record(self):
        """Test CatalogRecord model"""
        record = CatalogRecord(
            catalog_id="cat_test123",
            tenant_id="artisan_001",
            language=LanguageCode.HINDI,
            status=ProcessingStatus.PENDING
        )
        
        assert record.catalog_id == "cat_test123"
        assert record.status == ProcessingStatus.PENDING
        assert record.retry_count == 0
        assert isinstance(record.created_at, datetime)


class TestRequestModels:
    """Test API request models"""
    
    def test_catalog_submission_request(self):
        """Test CatalogSubmissionRequest validation"""
        request = CatalogSubmissionRequest(
            tenant_id="artisan_001",
            language=LanguageCode.HINDI,
            image_data="base64_image_data",
            audio_data="base64_audio_data",
            metadata={"location": "Jaipur"}
        )
        
        assert request.tenant_id == "artisan_001"
        assert request.language == LanguageCode.HINDI
        assert request.metadata["location"] == "Jaipur"
    
    def test_catalog_query_request(self):
        """Test CatalogQueryRequest with defaults"""
        request = CatalogQueryRequest()
        
        assert request.limit == 10
        assert request.catalog_id is None
    
    def test_catalog_query_request_with_filters(self):
        """Test CatalogQueryRequest with filters"""
        request = CatalogQueryRequest(
            tenant_id="artisan_001",
            status="completed",
            limit=20
        )
        
        assert request.tenant_id == "artisan_001"
        assert request.status == "completed"
        assert request.limit == 20


class TestResponseModels:
    """Test API response models"""
    
    def test_catalog_submission_response(self):
        """Test CatalogSubmissionResponse"""
        response = CatalogSubmissionResponse(
            catalog_id="cat_abc123",
            status=ProcessingStatus.PENDING,
            message="Submission received"
        )
        
        assert response.catalog_id == "cat_abc123"
        assert response.status == ProcessingStatus.PENDING
        assert response.estimated_processing_time_seconds == 30
    
    def test_error_response(self):
        """Test ErrorResponse"""
        from backend.models.response import ErrorDetail
        
        error = ErrorResponse(
            error="ValidationError",
            message="Invalid input",
            details=[
                ErrorDetail(field="language", issue="Unsupported language code")
            ]
        )
        
        assert error.error == "ValidationError"
        assert error.details[0].field == "language"
    
    def test_health_check_response(self):
        """Test HealthCheckResponse"""
        health = HealthCheckResponse(
            status="healthy",
            services={"api": "operational"}
        )
        
        assert health.status == "healthy"
        assert health.version == "1.0.0"
        assert isinstance(health.timestamp, datetime)
