"""
Local development server for testing API handlers
Run with: uvicorn backend.lambda_functions.api_handlers.local_server:app --reload
"""
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
import uuid
from datetime import datetime

from backend.models.request import CatalogSubmissionRequest, CatalogQueryRequest
from backend.models.response import (
    CatalogSubmissionResponse,
    CatalogStatusResponse,
    CatalogListResponse,
    ErrorResponse,
    HealthCheckResponse
)
from backend.models.catalog import ProcessingStatus

app = FastAPI(
    title="Vernacular Artisan Catalog API",
    description="API for submitting and managing artisan product catalogs",
    version="1.0.0"
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for local testing
catalog_store = {}


@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Health check endpoint"""
    return HealthCheckResponse(
        status="healthy",
        services={
            "api": "operational",
            "database": "mock",
            "queue": "mock"
        }
    )


@app.post("/catalog", response_model=CatalogSubmissionResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_catalog(request: CatalogSubmissionRequest):
    """Submit a new catalog entry for processing"""
    
    # Validate at least one media type
    if not request.image_data and not request.audio_data:
        raise HTTPException(
            status_code=400,
            detail="At least one of image_data or audio_data must be provided"
        )
    
    # Generate catalog ID
    catalog_id = f"cat_{uuid.uuid4().hex[:12]}"
    
    # Store in memory (mock)
    catalog_store[catalog_id] = {
        "catalog_id": catalog_id,
        "tenant_id": request.tenant_id,
        "language": request.language,
        "status": ProcessingStatus.PENDING,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    return CatalogSubmissionResponse(
        catalog_id=catalog_id,
        status=ProcessingStatus.PENDING,
        message="Catalog submission received and queued for processing",
        estimated_processing_time_seconds=30
    )



@app.get("/catalog/{catalog_id}", response_model=CatalogStatusResponse)
async def get_catalog_status(catalog_id: str):
    """Get status of a specific catalog entry"""
    
    if catalog_id not in catalog_store:
        raise HTTPException(
            status_code=404,
            detail=f"Catalog {catalog_id} not found"
        )
    
    catalog = catalog_store[catalog_id]
    
    return CatalogStatusResponse(
        catalog_id=catalog["catalog_id"],
        status=catalog["status"],
        created_at=catalog["created_at"],
        updated_at=catalog["updated_at"]
    )


@app.get("/catalog", response_model=CatalogListResponse)
async def list_catalogs(
    tenant_id: str = None,
    status: str = None,
    limit: int = 10
):
    """List catalog entries with optional filters"""
    
    # Filter catalogs
    filtered = list(catalog_store.values())
    
    if tenant_id:
        filtered = [c for c in filtered if c.get("tenant_id") == tenant_id]
    
    if status:
        filtered = [c for c in filtered if c.get("status") == status]
    
    # Apply limit
    filtered = filtered[:limit]
    
    # Convert to response models
    catalog_responses = [
        CatalogStatusResponse(
            catalog_id=c["catalog_id"],
            status=c["status"],
            created_at=c["created_at"],
            updated_at=c["updated_at"]
        )
        for c in filtered
    ]
    
    return CatalogListResponse(
        catalogs=catalog_responses,
        total=len(catalog_responses),
        limit=limit
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
