"""
Tenant and Artisan configuration models
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from .catalog import LanguageCode


class TenantConfiguration(BaseModel):
    """Tenant organization configuration"""
    tenant_id: str = Field(..., description="Unique tenant identifier")
    tenant_name: str = Field(..., description="Organization name")
    
    # Language and cultural settings
    default_language: LanguageCode = Field(..., description="Default language for this tenant")
    supported_languages: List[LanguageCode] = Field(default_factory=list, description="Supported languages")
    cultural_kb_id: Optional[str] = Field(None, description="Cultural knowledge base identifier")
    
    # ONDC credentials
    ondc_seller_id: str = Field(..., description="ONDC seller/provider ID")
    ondc_api_key: str = Field(..., description="ONDC API key")
    ondc_bpp_id: str = Field(..., description="ONDC BPP (Buyer Platform Provider) ID")
    
    # Quotas and limits
    monthly_catalog_quota: int = Field(default=1000, description="Monthly catalog entry quota")
    storage_quota_gb: int = Field(default=100, description="Storage quota in GB")
    api_rate_limit: int = Field(default=100, description="API requests per minute")
    
    # Contact information
    contact_email: str = Field(..., description="Primary contact email")
    contact_phone: Optional[str] = Field(None, description="Contact phone number")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True, description="Whether tenant is active")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ArtisanProfile(BaseModel):
    """Artisan user profile"""
    artisan_id: str = Field(..., description="Unique artisan identifier")
    tenant_id: str = Field(..., description="Associated tenant ID")
    
    # Personal information
    name: str = Field(..., description="Artisan name")
    phone_number: str = Field(..., description="Phone number for notifications")
    preferred_language: LanguageCode = Field(..., description="Preferred language")
    
    # Location
    region: Optional[str] = Field(None, description="Region/state")
    district: Optional[str] = Field(None, description="District")
    village: Optional[str] = Field(None, description="Village/town")
    
    # Craft information
    craft_type: Optional[str] = Field(None, description="Type of craft (e.g., 'Handloom', 'Pottery')")
    specialization: Optional[str] = Field(None, description="Craft specialization")
    years_of_experience: Optional[int] = Field(None, description="Years of experience")
    
    # Device information
    device_id: Optional[str] = Field(None, description="Mobile device identifier")
    fcm_token: Optional[str] = Field(None, description="Firebase Cloud Messaging token for notifications")
    
    # Statistics
    total_catalogs_created: int = Field(default=0, description="Total catalog entries created")
    total_catalogs_published: int = Field(default=0, description="Total entries published to ONDC")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_active_at: Optional[datetime] = Field(None, description="Last activity timestamp")
    is_active: bool = Field(default=True, description="Whether artisan profile is active")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TenantQuotaUsage(BaseModel):
    """Tenant quota usage tracking"""
    tenant_id: str = Field(..., description="Tenant identifier")
    month: str = Field(..., description="Month in YYYY-MM format")
    
    # Usage metrics
    catalogs_created: int = Field(default=0, description="Catalogs created this month")
    catalogs_published: int = Field(default=0, description="Catalogs published this month")
    storage_used_gb: float = Field(default=0.0, description="Storage used in GB")
    api_requests: int = Field(default=0, description="API requests this month")
    
    # Cost tracking
    processing_cost_usd: float = Field(default=0.0, description="AI processing cost in USD")
    storage_cost_usd: float = Field(default=0.0, description="Storage cost in USD")
    
    # Metadata
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
