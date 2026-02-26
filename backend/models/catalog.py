"""
Data models for catalog processing
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field, validator


class ProcessingStatus(str, Enum):
    """Processing status for each stage"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class QueueStatus(str, Enum):
    """Local queue entry status"""
    QUEUED = "queued"
    SYNCING = "syncing"
    SYNCED = "synced"
    FAILED = "failed"


class MediaType(str, Enum):
    """Media file types"""
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"


class LanguageCode(str, Enum):
    """Supported Indian languages"""
    HINDI = "hi"
    TELUGU = "te"
    TAMIL = "ta"
    BENGALI = "bn"
    MARATHI = "mr"
    GUJARATI = "gu"
    KANNADA = "kn"
    MALAYALAM = "ml"
    PUNJABI = "pa"
    ODIA = "or"


# ============================================================================
# Local Queue Entry (Edge Client)
# ============================================================================

class LocalQueueEntry(BaseModel):
    """Local queue entry for edge client offline-first operation"""
    local_id: str = Field(..., description="UUID generated on device")
    photo_path: str = Field(..., description="Local file path to photo")
    audio_path: str = Field(..., description="Local file path to audio")
    photo_size: int = Field(..., description="Photo file size in bytes")
    audio_size: int = Field(..., description="Audio file size in bytes")
    captured_at: datetime = Field(default_factory=datetime.utcnow, description="Capture timestamp")
    sync_status: QueueStatus = Field(default=QueueStatus.QUEUED, description="Sync status")
    retry_count: int = Field(default=0, description="Number of retry attempts")
    last_retry_at: Optional[datetime] = Field(None, description="Last retry timestamp")
    tracking_id: Optional[str] = Field(None, description="Assigned after upload initiation")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ============================================================================
# Catalog Processing Record (Backend)
# ============================================================================

class CatalogProcessingRecord(BaseModel):
    """Complete catalog processing record stored in DynamoDB"""
    tracking_id: str = Field(..., description="Primary key - unique tracking identifier")
    tenant_id: str = Field(..., description="Tenant organization identifier")
    artisan_id: str = Field(..., description="Artisan identifier")
    photo_key: str = Field(..., description="S3 object key for photo")
    audio_key: str = Field(..., description="S3 object key for audio")
    language: LanguageCode = Field(..., description="Input language ISO 639-1 code")
    
    # ASR Processing Stage
    asr_status: ProcessingStatus = Field(default=ProcessingStatus.PENDING)
    asr_result: Optional[Dict[str, Any]] = Field(None, description="ASR transcription result")
    
    # Vision Processing Stage
    vision_status: ProcessingStatus = Field(default=ProcessingStatus.PENDING)
    vision_result: Optional[Dict[str, Any]] = Field(None, description="Vision analysis result")
    
    # Extraction Stage
    extraction_status: ProcessingStatus = Field(default=ProcessingStatus.PENDING)
    extraction_result: Optional[Dict[str, Any]] = Field(None, description="Extracted attributes")
    
    # Mapping Stage
    mapping_status: ProcessingStatus = Field(default=ProcessingStatus.PENDING)
    ondc_payload: Optional[Dict[str, Any]] = Field(None, description="Beckn-compliant payload")
    
    # Submission Stage
    submission_status: ProcessingStatus = Field(default=ProcessingStatus.PENDING)
    ondc_catalog_id: Optional[str] = Field(None, description="ONDC-assigned catalog ID")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(None)
    error_details: Optional[Dict[str, Any]] = Field(None, description="Error details if failed")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ============================================================================
# Extracted Attributes (Intermediate Format)
# ============================================================================

class CSI(BaseModel):
    """Cultural Specific Item - preserves cultural context"""
    vernacular_term: str = Field(..., description="Original term in artisan's language")
    transliteration: str = Field(..., description="Roman script representation")
    english_context: str = Field(..., description="Contextual explanation in English")
    cultural_significance: str = Field(..., description="Why this term matters culturally")


class ExtractedAttributes(BaseModel):
    """Extracted product attributes from multimodal input"""
    # Core attributes
    category: str = Field(..., description="Product category (e.g., 'Handloom Saree')")
    subcategory: Optional[str] = Field(None, description="Product subcategory (e.g., 'Banarasi Silk')")
    
    # Physical attributes
    material: List[str] = Field(default_factory=list, description="Materials (e.g., ['silk', 'zari'])")
    colors: List[str] = Field(default_factory=list, description="Colors (e.g., ['red', 'gold'])")
    dimensions: Optional[Dict[str, Any]] = Field(None, description="Dimensions with unit")
    weight: Optional[Dict[str, Any]] = Field(None, description="Weight with unit")
    
    # Pricing
    price: Optional[Dict[str, Any]] = Field(None, description="Price with currency")
    
    # Description
    short_description: str = Field(..., description="1-2 sentence description")
    long_description: str = Field(..., description="Detailed transcreated description")
    
    # Cultural preservation
    csis: List[CSI] = Field(default_factory=list, description="Cultural Specific Items")
    craft_technique: Optional[str] = Field(None, description="Craft technique (e.g., 'Handwoven on pit loom')")
    region_of_origin: Optional[str] = Field(None, description="Region (e.g., 'Varanasi, Uttar Pradesh')")
    
    # Confidence scores
    confidence_scores: Dict[str, float] = Field(default_factory=dict, description="Per-attribute confidence")


# ============================================================================
# ONDC Catalog Models (Beckn Protocol)
# ============================================================================

class Price(BaseModel):
    """Price information"""
    currency: str = Field(default="INR", description="Currency code")
    value: str = Field(..., description="Price value as string")


class TimeRange(BaseModel):
    """Time range for availability"""
    start: Optional[str] = None
    end: Optional[str] = None


class ItemDescriptor(BaseModel):
    """Beckn protocol item descriptor"""
    name: str = Field(..., description="Product name (max 100 chars)")
    code: Optional[str] = Field(None, description="Product code")
    symbol: Optional[str] = Field(None, description="Product symbol")
    short_desc: str = Field(..., description="Short description (max 500 chars)")
    long_desc: str = Field(..., description="Detailed description")
    images: List[str] = Field(default_factory=list, description="Image URLs")
    audio: Optional[str] = Field(None, description="Audio URL")
    video: Optional[str] = Field(None, description="Video URL")
    
    @validator('name')
    def validate_name_length(cls, v):
        if len(v) > 100:
            raise ValueError("name must be <= 100 characters")
        return v
    
    @validator('short_desc')
    def validate_short_desc_length(cls, v):
        if len(v) > 500:
            raise ValueError("short_desc must be <= 500 characters")
        return v


class ONDCCatalogItem(BaseModel):
    """ONDC catalog item following Beckn protocol"""
    id: str = Field(..., description="Unique item ID")
    descriptor: ItemDescriptor = Field(..., description="Item descriptor")
    price: Price = Field(..., description="Price information")
    category_id: str = Field(..., description="ONDC category ID")
    fulfillment_id: Optional[str] = Field(None, description="Fulfillment ID")
    location_id: Optional[str] = Field(None, description="Location ID")
    
    # Optional fields
    tags: Dict[str, Any] = Field(default_factory=dict, description="Custom attributes")
    time: Optional[TimeRange] = Field(None, description="Availability time range")
    matched: Optional[bool] = Field(None, description="Matched flag")
    related: Optional[bool] = Field(None, description="Related flag")
    recommended: Optional[bool] = Field(None, description="Recommended flag")


# ============================================================================
# Legacy Models (for backward compatibility)
# ============================================================================

class MediaFile(BaseModel):
    """Media file metadata"""
    file_id: str = Field(..., description="Unique file identifier")
    file_type: MediaType = Field(..., description="Type of media file")
    s3_key: str = Field(..., description="S3 object key")
    s3_bucket: str = Field(..., description="S3 bucket name")
    file_size: int = Field(..., description="File size in bytes")
    mime_type: str = Field(..., description="MIME type")
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class VisionAnalysis(BaseModel):
    """Vision model analysis results"""
    objects_detected: List[str] = Field(default_factory=list)
    colors: List[str] = Field(default_factory=list)
    materials: List[str] = Field(default_factory=list)
    patterns: List[str] = Field(default_factory=list)
    confidence_scores: Dict[str, float] = Field(default_factory=dict)
    raw_output: Optional[Dict[str, Any]] = None


class ASRTranscription(BaseModel):
    """ASR transcription results"""
    text: str = Field(..., description="Transcribed text")
    language: LanguageCode = Field(..., description="Detected language")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    word_timestamps: Optional[List[Dict[str, Any]]] = None
    raw_output: Optional[Dict[str, Any]] = None


class ONDCCatalogEntry(BaseModel):
    """ONDC-compliant catalog entry (legacy)"""
    product_name: str = Field(..., description="Product name")
    product_name_vernacular: Optional[str] = Field(None, description="Vernacular product name")
    category: str = Field(..., description="ONDC category")
    description: str = Field(..., description="Product description")
    description_vernacular: Optional[str] = Field(None, description="Vernacular description")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Product attributes")
    price: Optional[float] = Field(None, description="Estimated price")
    currency: str = Field("INR", description="Currency code")
    images: List[str] = Field(default_factory=list, description="Image URLs")
    cultural_context: Optional[str] = Field(None, description="Cultural significance")


class CatalogRecord(BaseModel):
    """Complete catalog processing record (legacy)"""
    catalog_id: str = Field(..., description="Unique catalog identifier")
    tenant_id: str = Field(..., description="Tenant identifier")
    status: ProcessingStatus = Field(default=ProcessingStatus.PENDING)
    
    # Input data
    image_file: Optional[MediaFile] = None
    audio_file: Optional[MediaFile] = None
    language: LanguageCode = Field(..., description="Input language")
    
    # Processing results
    vision_analysis: Optional[VisionAnalysis] = None
    transcription: Optional[ASRTranscription] = None
    catalog_entry: Optional[ONDCCatalogEntry] = None
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    processing_time_ms: Optional[int] = None
    error_message: Optional[str] = None
    retry_count: int = Field(default=0)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
