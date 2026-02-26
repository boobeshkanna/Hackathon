"""
API request models
"""
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from .catalog import LanguageCode


class CatalogSubmissionRequest(BaseModel):
    """Request model for catalog submission"""
    tenant_id: str = Field(..., description="Tenant/artisan identifier")
    language: LanguageCode = Field(..., description="Language of audio description")
    image_data: Optional[str] = Field(None, description="Base64 encoded image data")
    audio_data: Optional[str] = Field(None, description="Base64 encoded audio data")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    
    @validator('image_data', 'audio_data')
    def validate_media_data(cls, v):
        """Validate that at least one media type is provided"""
        if v and len(v) > 10 * 1024 * 1024:  # 10MB limit
            raise ValueError("Media data exceeds 10MB limit")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "tenant_id": "artisan_12345",
                "language": "hi",
                "image_data": "base64_encoded_image...",
                "audio_data": "base64_encoded_audio...",
                "metadata": {
                    "location": "Jaipur",
                    "category_hint": "handicraft"
                }
            }
        }


class CatalogQueryRequest(BaseModel):
    """Request model for querying catalog status"""
    catalog_id: Optional[str] = Field(None, description="Specific catalog ID")
    tenant_id: Optional[str] = Field(None, description="Filter by tenant")
    status: Optional[str] = Field(None, description="Filter by status")
    limit: int = Field(10, ge=1, le=100, description="Number of results")
    
    class Config:
        json_schema_extra = {
            "example": {
                "tenant_id": "artisan_12345",
                "status": "completed",
                "limit": 10
            }
        }
