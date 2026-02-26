"""
API response models
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from .catalog import ProcessingStatus


# ============================================================================
# Upload Response Models
# ============================================================================

class UploadResponse(BaseModel):
    """Response for upload initiation"""
    tracking_id: str = Field(..., description="Unique tracking identifier")
    upload_url: str = Field(..., description="Presigned URL for upload")
    expires_at: datetime = Field(..., description="Upload URL expiration timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        json_schema_extra = {
            "example": {
                "tracking_id": "trk_abc123xyz",
                "upload_url": "https://s3.amazonaws.com/bucket/path?signature=...",
                "expires_at": "2024-02-26T11:00:00Z"
            }
        }


class UploadCompleteResponse(BaseModel):
    """Response for upload completion"""
    status: str = Field(default="accepted", description="Acceptance status")
    tracking_id: str = Field(..., description="Tracking identifier")
    message: str = Field(default="Upload accepted and queued for processing")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "accepted",
                "tracking_id": "trk_abc123xyz",
                "message": "Upload accepted and queued for processing"
            }
        }


# ============================================================================
# Status Update Models
# ============================================================================

class StatusUpdate(BaseModel):
    """Status update notification"""
    tracking_id: str = Field(..., description="Tracking identifier")
    stage: str = Field(..., description="Processing stage")
    message: str = Field(..., description="Status message")
    catalog_id: Optional[str] = Field(None, description="ONDC catalog ID if completed")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        json_schema_extra = {
            "example": {
                "tracking_id": "trk_abc123xyz",
                "stage": "completed",
                "message": "Catalog entry successfully published to ONDC",
                "catalog_id": "ondc_cat_789",
                "timestamp": "2024-02-26T10:05:00Z"
            }
        }


# ============================================================================
# Error Response Models
# ============================================================================

class ErrorDetail(BaseModel):
    """Detailed error information"""
    field: Optional[str] = Field(None, description="Field that caused the error")
    issue: str = Field(..., description="Description of the issue")
    code: Optional[str] = Field(None, description="Error code")


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[List[ErrorDetail]] = Field(None, description="Detailed error information")
    tracking_id: Optional[str] = Field(None, description="Tracking ID if available")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "ValidationError",
                "message": "Invalid request data",
                "details": [
                    {
                        "field": "language",
                        "issue": "Unsupported language code",
                        "code": "INVALID_LANGUAGE"
                    }
                ]
            }
        }


# ============================================================================
# Legacy Response Models (for backward compatibility)
# ============================================================================

class CatalogSubmissionResponse(BaseModel):
    """Response for catalog submission (legacy)"""
    catalog_id: str = Field(..., description="Unique catalog identifier")
    status: ProcessingStatus = Field(..., description="Processing status")
    message: str = Field(..., description="Response message")
    estimated_processing_time_seconds: int = Field(default=30)
    
    class Config:
        json_schema_extra = {
            "example": {
                "catalog_id": "cat_abc123xyz",
                "status": "pending",
                "message": "Catalog submission received and queued for processing",
                "estimated_processing_time_seconds": 30
            }
        }


class CatalogStatusResponse(BaseModel):
    """Response for catalog status query"""
    catalog_id: str
    status: ProcessingStatus
    created_at: datetime
    updated_at: datetime
    processing_time_ms: Optional[int] = None
    error_message: Optional[str] = None
    catalog_entry: Optional[Dict[str, Any]] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CatalogListResponse(BaseModel):
    """Response for listing catalogs"""
    catalogs: List[CatalogStatusResponse]
    total: int
    limit: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "catalogs": [
                    {
                        "catalog_id": "cat_abc123",
                        "status": "completed",
                        "created_at": "2024-02-26T10:00:00Z",
                        "updated_at": "2024-02-26T10:00:30Z",
                        "processing_time_ms": 28500
                    }
                ],
                "total": 1,
                "limit": 10
            }
        }


class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = Field(default="1.0.0")
    services: Dict[str, str] = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
