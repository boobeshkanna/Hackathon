#!/usr/bin/env python3
"""
Test script for demo API
Tests all endpoints with sample data
"""
import os
import sys
import json
import logging
from pathlib import Path
from dotenv import load_dotenv

# Add backend to path
backend_path = Path(__file__).parent / 'backend'
sys.path.insert(0, str(backend_path))

from services.ai_client import UnifiedAIClient, AIProvider
from services.bedrock_client.unified_vision_analyzer import UnifiedVisionAnalyzer
from services.bedrock_client.unified_client import UnifiedBedrockClient

# Load environment
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_provider_availability():
    """Test which AI providers are available"""
    logger.info("=" * 60)
    logger.info("Testing AI Provider Availability")
    logger.info("=" * 60)
    
    try:
        client = UnifiedAIClient()
        providers = client.get_available_providers()
        
        logger.info(f"✓ Found {len(providers)} available provider(s)")
        for provider in providers:
            logger.info(f"  - {provider.value}")
        
        return True
    except Exception as e:
        logger.error(f"✗ No providers available: {e}")
        logger.error("\nPlease set at least one API key in .env:")
        logger.error("  - OPENAI_API_KEY")
        logger.error("  - ANTHROPIC_API_KEY")
        logger.error("  - GROQ_API_KEY")
        return False


def test_text_generation():
    """Test text generation"""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Text Generation")
    logger.info("=" * 60)
    
    try:
        client = UnifiedAIClient()
        
        prompt = """Extract product attributes from this description:
"यह बनारसी रेशम की साड़ी है, लाल और सुनहरे रंग की, हाथ से बुनी हुई"

Return JSON with: category, materials, colors"""
        
        logger.info("Sending prompt to AI...")
        response = client.generate_text(prompt, max_tokens=500)
        
        logger.info("✓ Text generation successful")
        logger.info(f"Response preview: {response[:200]}...")
        
        return True
    except Exception as e:
        logger.error(f"✗ Text generation failed: {e}")
        return False


def test_vision_analyzer():
    """Test vision analysis with sample image"""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Vision Analysis")
    logger.info("=" * 60)
    
    try:
        # Create a simple test image (1x1 red pixel)
        from PIL import Image
        import io
        
        img = Image.new('RGB', (100, 100), color='red')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        image_bytes = img_bytes.getvalue()
        
        logger.info("Created test image (100x100 red square)")
        
        analyzer = UnifiedVisionAnalyzer()
        logger.info("Analyzing image...")
        
        result = analyzer.analyze_product_image(
            image_bytes=image_bytes,
            rekognition_labels=None
        )
        
        logger.info("✓ Vision analysis successful")
        logger.info(f"Category detected: {result.get('category', 'Unknown')}")
        logger.info(f"Confidence: {result.get('confidence', 0.0)}")
        
        return True
    except Exception as e:
        logger.error(f"✗ Vision analysis failed: {e}")
        return False


def test_attribute_extraction():
    """Test attribute extraction"""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Attribute Extraction")
    logger.info("=" * 60)
    
    try:
        client = UnifiedBedrockClient()
        
        transcription = "यह बनारसी रेशम की साड़ी है, लाल और सुनहरे रंग की, हाथ से बुनी हुई, कीमत पांच हजार रुपये"
        vision_data = {
            "category": "Saree",
            "colors": {"primary": ["red", "gold"]},
            "confidence": 0.85
        }
        
        logger.info("Extracting attributes...")
        attributes = client.extract_attributes(
            transcription=transcription,
            vision_data=vision_data,
            language='hi'
        )
        
        logger.info("✓ Attribute extraction successful")
        logger.info(f"Category: {attributes.category}")
        logger.info(f"Materials: {attributes.material}")
        logger.info(f"Colors: {attributes.colors}")
        logger.info(f"Price: {attributes.price}")
        
        return True
    except Exception as e:
        logger.error(f"✗ Attribute extraction failed: {e}")
        return False


def test_csi_identification():
    """Test CSI term identification"""
    logger.info("\n" + "=" * 60)
    logger.info("Testing CSI Term Identification")
    logger.info("=" * 60)
    
    try:
        client = UnifiedBedrockClient()
        
        transcription = "यह बनारसी साड़ी है, ज़री के काम के साथ, कांथा स्टिच से सजी हुई"
        
        logger.info("Identifying CSI terms...")
        csi_terms = client.identify_csi_terms(
            transcription=transcription,
            language='hi'
        )
        
        logger.info(f"✓ Found {len(csi_terms)} CSI term(s)")
        for csi in csi_terms:
            logger.info(f"  - {csi.vernacular_term} ({csi.transliteration})")
        
        return True
    except Exception as e:
        logger.error(f"✗ CSI identification failed: {e}")
        return False


def main():
    """Run all tests"""
    logger.info("\n" + "=" * 60)
    logger.info("Vernacular Artisan Catalog - Demo API Tests")
    logger.info("=" * 60)
    
    results = {
        "Provider Availability": test_provider_availability(),
        "Text Generation": False,
        "Vision Analysis": False,
        "Attribute Extraction": False,
        "CSI Identification": False
    }
    
    # Only run other tests if providers are available
    if results["Provider Availability"]:
        results["Text Generation"] = test_text_generation()
        results["Vision Analysis"] = test_vision_analyzer()
        results["Attribute Extraction"] = test_attribute_extraction()
        results["CSI Identification"] = test_csi_identification()
    
    # Print summary
    logger.info("\n" + "=" * 60)
    logger.info("Test Summary")
    logger.info("=" * 60)
    
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        logger.info(f"{status} - {test_name}")
    
    total_passed = sum(results.values())
    total_tests = len(results)
    
    logger.info("=" * 60)
    logger.info(f"Results: {total_passed}/{total_tests} tests passed")
    logger.info("=" * 60)
    
    if total_passed == total_tests:
        logger.info("\n🎉 All tests passed! Your demo API is ready to use.")
        logger.info("\nNext steps:")
        logger.info("1. Run: python backend/lambda_functions/api_handlers/local_demo_server.py")
        logger.info("2. Open: http://localhost:8000/docs")
        logger.info("3. Test the API endpoints")
        return 0
    else:
        logger.error("\n⚠️  Some tests failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
