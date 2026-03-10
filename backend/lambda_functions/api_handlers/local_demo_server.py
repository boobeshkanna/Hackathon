"""
Local Demo Server - Run without AWS infrastructure
Uses third-party AI providers (OpenAI, Anthropic, Groq)
"""
import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
from dotenv import load_dotenv

# Add backend to path
backend_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_path))

from services.ai_client import UnifiedAIClient, AIProvider
from services.bedrock_client.unified_vision_analyzer import UnifiedVisionAnalyzer
from services.bedrock_client.unified_client import UnifiedBedrockClient

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Vernacular Artisan Catalog - Demo API",
    description="Demo API using third-party AI providers (no AWS required)",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup templates
templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

# Initialize AI clients
try:
    vision_analyzer = UnifiedVisionAnalyzer()
    bedrock_client = UnifiedBedrockClient()
    logger.info("✓ AI clients initialized successfully")
    logger.info(f"Available providers: {vision_analyzer.client.get_available_providers()}")
except Exception as e:
    logger.error(f"✗ Failed to initialize AI clients: {e}")
    logger.error("Please set at least one API key: OPENAI_API_KEY, ANTHROPIC_API_KEY, or GROQ_API_KEY")
    sys.exit(1)


@app.get("/", response_class=HTMLResponse)
async def demo_ui(request: Request):
    """Demo web interface for uploading images and voice"""
    return templates.TemplateResponse("demo.html", {"request": request})


@app.get("/health")
async def health_check():
    """Detailed health check"""
    providers = vision_analyzer.client.get_available_providers()
    
    return {
        "status": "healthy",
        "ai_providers": {
            "available": [p.value for p in providers],
            "count": len(providers),
            "bedrock": AIProvider.BEDROCK in providers,
            "openai": AIProvider.OPENAI in providers,
            "anthropic": AIProvider.ANTHROPIC in providers,
            "groq": AIProvider.GROQ in providers
        }
    }


@app.get("/api/status")
async def api_status():
    """API status endpoint for JSON response"""
    return {
        "status": "running",
        "service": "Vernacular Artisan Catalog Demo API",
        "providers_available": [p.value for p in vision_analyzer.client.get_available_providers()],
        "message": "Upload product images and audio to generate catalog entries"
    }

# Initialize AI clients
try:
    vision_analyzer = UnifiedVisionAnalyzer()
    bedrock_client = UnifiedBedrockClient()
    logger.info("✓ AI clients initialized successfully")
    logger.info(f"Available providers: {vision_analyzer.client.get_available_providers()}")
except Exception as e:
    logger.error(f"✗ Failed to initialize AI clients: {e}")
    logger.error("Please set at least one API key: OPENAI_API_KEY, ANTHROPIC_API_KEY, or GROQ_API_KEY")
    sys.exit(1)


@app.get("/", response_class=HTMLResponse)
async def demo_ui(request: Request):
    """Demo web interface for uploading images and voice"""
    return templates.TemplateResponse("demo.html", {"request": request})


@app.get("/health")
async def health_check():
    """Detailed health check"""
    providers = vision_analyzer.client.get_available_providers()
    
    return {
        "status": "healthy",
        "ai_providers": {
            "available": [p.value for p in providers],
            "count": len(providers),
            "bedrock": AIProvider.BEDROCK in providers,
            "openai": AIProvider.OPENAI in providers,
            "anthropic": AIProvider.ANTHROPIC in providers,
            "groq": AIProvider.GROQ in providers
        }
    }


@app.get("/api/status")
async def api_status():
    """API status endpoint for JSON response"""
    return {
        "status": "running",
        "service": "Vernacular Artisan Catalog Demo API",
        "providers_available": [p.value for p in vision_analyzer.client.get_available_providers()],
        "message": "Upload product images and audio to generate catalog entries"
    }


@app.post("/api/analyze-image")
async def analyze_image(
    image: UploadFile = File(...),
    language: str = Form("hi")
):
    """
    Analyze product image using AI vision
    
    Args:
        image: Product image file
        language: Language code (default: hi for Hindi)
    
    Returns:
        Product analysis with category, materials, colors, etc.
    """
    try:
        # Read image bytes
        image_bytes = await image.read()
        
        logger.info(f"Analyzing image: {image.filename} ({len(image_bytes)} bytes)")
        
        # Analyze image
        result = vision_analyzer.analyze_product_image(
            image_bytes=image_bytes,
            rekognition_labels=None
        )
        
        return JSONResponse(content={
            "success": True,
            "analysis": result,
            "providers_used": result.get('providers_available', [])
        })
        
    except Exception as e:
        logger.error(f"Image analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/extract-attributes")
async def extract_attributes(
    transcription: str = Form(...),
    vision_data: str = Form("{}"),
    language: str = Form("hi")
):
    """
    Extract structured attributes from transcription and vision data
    
    Args:
        transcription: Voice transcription text
        vision_data: JSON string of vision analysis
        language: Language code
    
    Returns:
        Extracted product attributes
    """
    try:
        import json
        vision_dict = json.loads(vision_data) if vision_data != "{}" else {}
        
        logger.info(f"Extracting attributes from transcription (lang: {language})")
        
        # Extract attributes
        attributes = bedrock_client.extract_attributes(
            transcription=transcription,
            vision_data=vision_dict,
            language=language
        )
        
        # Identify CSI terms
        csi_terms = bedrock_client.identify_csi_terms(
            transcription=transcription,
            language=language
        )
        attributes.csis = csi_terms
        
        # Transcreate description
        descriptions = bedrock_client.transcreate_description(
            vernacular_text=transcription,
            extracted_attrs=attributes,
            language=language
        )
        
        return JSONResponse(content={
            "success": True,
            "attributes": attributes.dict(),
            "descriptions": descriptions,
            "csi_terms": [csi.dict() for csi in csi_terms]
        })
        
    except Exception as e:
        logger.error(f"Attribute extraction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/process-product")
async def process_product(
    image: UploadFile = File(...),
    transcription: str = Form(""),
    language: str = Form("hi")
):
    """
    Complete product processing pipeline
    
    Args:
        image: Product image file
        transcription: Voice transcription (optional)
        language: Language code
    
    Returns:
        Complete catalog entry with all extracted information
    """
    try:
        # Read image
        image_bytes = await image.read()
        
        logger.info(f"Processing product: {image.filename}")
        
        # Step 1: Analyze image
        vision_result = vision_analyzer.analyze_product_image(
            image_bytes=image_bytes
        )
        
        # Step 2: Extract attributes (if transcription provided)
        if transcription:
            attributes = bedrock_client.extract_attributes(
                transcription=transcription,
                vision_data=vision_result,
                language=language
            )
            
            # Identify CSI terms
            csi_terms = bedrock_client.identify_csi_terms(
                transcription=transcription,
                language=language
            )
            attributes.csis = csi_terms
            
            # Transcreate description
            descriptions = bedrock_client.transcreate_description(
                vernacular_text=transcription,
                extracted_attrs=attributes,
                language=language
            )
        else:
            # Use vision-only data
            attributes = None
            csi_terms = []
            descriptions = {
                'short_description': vision_result.get('description', ''),
                'long_description': vision_result.get('description', '')
            }
        
        return JSONResponse(content={
            "success": True,
            "vision_analysis": vision_result,
            "attributes": attributes.dict() if attributes else None,
            "descriptions": descriptions,
            "csi_terms": [csi.dict() for csi in csi_terms],
            "providers_available": [p.value for p in vision_analyzer.client.get_available_providers()]
        })
        
    except Exception as e:
        logger.error(f"Product processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def main():
    """Run the demo server"""
    port = int(os.getenv('PORT', 8000))
    host = os.getenv('HOST', '0.0.0.0')
    
    logger.info("=" * 60)
    logger.info("Vernacular Artisan Catalog - Demo Server")
    logger.info("=" * 60)
    logger.info(f"Server starting on http://{host}:{port}")
    logger.info(f"API docs available at http://{host}:{port}/docs")
    logger.info("=" * 60)
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )


if __name__ == "__main__":
    main()
