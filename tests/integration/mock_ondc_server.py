"""
Mock ONDC API Server for Integration Testing

This module provides a mock ONDC API server that simulates the ONDC Gateway
for integration testing purposes.

Requirements: All
"""

from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any
import uvicorn
import uuid
from datetime import datetime
import json

app = FastAPI(title="Mock ONDC API Server")

# In-memory storage for submitted catalogs
submitted_catalogs = {}
submission_history = []


@app.post("/beckn/catalog/on_search")
async def on_search_catalog(
    request: Request,
    authorization: Optional[str] = Header(None)
):
    """
    Mock ONDC catalog submission endpoint
    
    Simulates the ONDC Beckn protocol catalog submission API
    """
    try:
        payload = await request.json()
        
        # Validate authorization
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Unauthorized")
        
        # Validate basic Beckn structure
        if 'context' not in payload or 'message' not in payload:
            return JSONResponse(
                status_code=400,
                content={
                    "error": {
                        "code": "INVALID_REQUEST",
                        "message": "Missing required fields: context or message"
                    }
                }
            )
        
        context = payload.get('context', {})
        message = payload.get('message', {})
        
        # Validate context fields
        required_context_fields = ['domain', 'country', 'action', 'bap_id', 'bpp_id']
        missing_fields = [f for f in required_context_fields if f not in context]
        if missing_fields:
            return JSONResponse(
                status_code=400,
                content={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": f"Missing context fields: {', '.join(missing_fields)}"
                    }
                }
            )
        
        # Validate catalog structure
        catalog = message.get('catalog', {})
        providers = catalog.get('bpp/providers', [])
        
        if not providers:
            return JSONResponse(
                status_code=400,
                content={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "No providers found in catalog"
                    }
                }
            )
        
        # Validate items
        for provider in providers:
            items = provider.get('items', [])
            if not items:
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "message": f"No items found for provider {provider.get('id')}"
                        }
                    }
                )
            
            for item in items:
                # Validate required item fields
                if 'descriptor' not in item:
                    return JSONResponse(
                        status_code=400,
                        content={
                            "error": {
                                "code": "VALIDATION_ERROR",
                                "message": f"Item {item.get('id')} missing descriptor"
                            }
                        }
                    )
                
                descriptor = item['descriptor']
                if not descriptor.get('name'):
                    return JSONResponse(
                        status_code=400,
                        content={
                            "error": {
                                "code": "VALIDATION_ERROR",
                                "message": f"Item {item.get('id')} missing descriptor.name"
                            }
                        }
                    )
                
                if 'price' not in item or not item['price'].get('value'):
                    return JSONResponse(
                        status_code=400,
                        content={
                            "error": {
                                "code": "VALIDATION_ERROR",
                                "message": f"Item {item.get('id')} missing price.value"
                            }
                        }
                    )
                
                if not descriptor.get('images'):
                    return JSONResponse(
                        status_code=400,
                        content={
                            "error": {
                                "code": "VALIDATION_ERROR",
                                "message": f"Item {item.get('id')} missing images"
                            }
                        }
                    )
        
        # Generate catalog IDs for items
        catalog_ids = {}
        for provider in providers:
            for item in items:
                item_id = item.get('id')
                catalog_id = f"ondc-catalog-{uuid.uuid4().hex[:12]}"
                catalog_ids[item_id] = catalog_id
                
                # Store in mock database
                submitted_catalogs[catalog_id] = {
                    'item_id': item_id,
                    'payload': item,
                    'submitted_at': datetime.now().isoformat(),
                    'status': 'active'
                }
        
        # Record submission history
        submission_history.append({
            'timestamp': datetime.now().isoformat(),
            'payload': payload,
            'catalog_ids': catalog_ids
        })
        
        # Return success response
        return JSONResponse(
            status_code=200,
            content={
                "message": {
                    "ack": {
                        "status": "ACK"
                    }
                },
                "catalog_ids": catalog_ids
            }
        )
    
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "code": "INVALID_JSON",
                    "message": "Request body is not valid JSON"
                }
            }
        )
    
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
        )


@app.put("/beckn/catalog/update")
async def update_catalog(
    request: Request,
    authorization: Optional[str] = Header(None)
):
    """
    Mock ONDC catalog update endpoint
    """
    try:
        payload = await request.json()
        
        # Validate authorization
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Unauthorized")
        
        catalog_id = payload.get('catalog_id')
        if not catalog_id or catalog_id not in submitted_catalogs:
            return JSONResponse(
                status_code=404,
                content={
                    "error": {
                        "code": "NOT_FOUND",
                        "message": f"Catalog ID {catalog_id} not found"
                    }
                }
            )
        
        # Update catalog
        submitted_catalogs[catalog_id]['payload'] = payload.get('item', {})
        submitted_catalogs[catalog_id]['updated_at'] = datetime.now().isoformat()
        
        return JSONResponse(
            status_code=200,
            content={
                "message": {
                    "ack": {
                        "status": "ACK"
                    }
                },
                "catalog_id": catalog_id
            }
        )
    
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
        )


@app.get("/beckn/catalog/{catalog_id}")
async def get_catalog(
    catalog_id: str,
    authorization: Optional[str] = Header(None)
):
    """
    Mock endpoint to retrieve catalog by ID
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    if catalog_id not in submitted_catalogs:
        return JSONResponse(
            status_code=404,
            content={
                "error": {
                    "code": "NOT_FOUND",
                    "message": f"Catalog ID {catalog_id} not found"
                }
            }
        )
    
    return JSONResponse(
        status_code=200,
        content=submitted_catalogs[catalog_id]
    )


@app.get("/test/submissions")
async def get_submission_history():
    """
    Test endpoint to retrieve submission history
    """
    return JSONResponse(
        status_code=200,
        content={
            "total": len(submission_history),
            "submissions": submission_history
        }
    )


@app.post("/test/reset")
async def reset_mock_data():
    """
    Test endpoint to reset all mock data
    """
    global submitted_catalogs, submission_history
    submitted_catalogs = {}
    submission_history = []
    
    return JSONResponse(
        status_code=200,
        content={"message": "Mock data reset successfully"}
    )


@app.post("/test/simulate-error")
async def simulate_error(request: Request):
    """
    Test endpoint to simulate various error conditions
    """
    payload = await request.json()
    error_type = payload.get('error_type', 'server_error')
    
    if error_type == 'rate_limit':
        return JSONResponse(
            status_code=429,
            content={
                "error": {
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": "Too many requests"
                }
            }
        )
    elif error_type == 'timeout':
        import time
        time.sleep(10)  # Simulate timeout
        return JSONResponse(status_code=200, content={"message": "OK"})
    else:
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Simulated server error"
                }
            }
        )


@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "timestamp": datetime.now().isoformat()
        }
    )


if __name__ == "__main__":
    print("Starting Mock ONDC API Server on http://localhost:8080")
    print("Use /test/reset to clear mock data")
    print("Use /test/submissions to view submission history")
    uvicorn.run(app, host="0.0.0.0", port=8080)
