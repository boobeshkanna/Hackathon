"""
Example usage of the Sagemaker Client

This script demonstrates how to use the SagemakerClient for Vision and ASR inference.
"""
import logging
from pathlib import Path
from backend.services.sagemaker_client import SagemakerClient, ErrorCategory, ConfidenceLevel
from backend.services.sagemaker_client.config import SagemakerConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def example_combined_inference():
    """Example: Combined Vision + ASR inference"""
    logger.info("=== Example: Combined Vision + ASR Inference ===")
    
    # Initialize client
    client = SagemakerClient(
        endpoint_name=SagemakerConfig.ENDPOINT_NAME,
        region=SagemakerConfig.REGION,
        timeout_seconds=SagemakerConfig.TIMEOUT_SECONDS,
        max_retries=SagemakerConfig.MAX_RETRIES,
        asr_confidence_threshold=SagemakerConfig.ASR_CONFIDENCE_THRESHOLD,
        vision_confidence_threshold=SagemakerConfig.VISION_CONFIDENCE_THRESHOLD
    )
    
    # Load sample media files
    image_path = Path("samples/product_image.jpg")
    audio_path = Path("samples/product_description.opus")
    
    if not image_path.exists() or not audio_path.exists():
        logger.warning("Sample files not found, skipping example")
        return
    
    with open(image_path, 'rb') as f:
        image_bytes = f.read()
    
    with open(audio_path, 'rb') as f:
        audio_bytes = f.read()
    
    try:
        # Invoke combined endpoint
        result = client.invoke_combined_endpoint(
            image_bytes=image_bytes,
            audio_bytes=audio_bytes,
            language_hint='hi'  # Hindi
        )
        
        # Process transcription results
        if 'transcription' in result:
            transcription = result['transcription']
            logger.info(f"Transcription: {transcription.get('text', '')}")
            logger.info(f"Language: {transcription.get('language', 'unknown')}")
            logger.info(f"Confidence: {transcription.get('confidence', 0.0):.2f}")
            
            if transcription.get('requires_manual_review'):
                logger.warning("⚠️  ASR result requires manual review (low confidence)")
        
        # Process vision results
        if 'vision' in result:
            vision = result['vision']
            logger.info(f"Category: {vision.get('category', 'unknown')}")
            logger.info(f"Colors: {', '.join(vision.get('colors', []))}")
            logger.info(f"Materials: {', '.join(vision.get('materials', []))}")
            logger.info(f"Confidence: {vision.get('confidence', 0.0):.2f}")
            
            if vision.get('requires_manual_review'):
                logger.warning("⚠️  Vision result requires manual review (low confidence)")
        
        logger.info("✓ Combined inference completed successfully")
        
    except Exception as e:
        logger.error(f"✗ Combined inference failed: {e}")


def example_vision_only():
    """Example: Vision-only inference"""
    logger.info("\n=== Example: Vision-Only Inference ===")
    
    client = SagemakerClient(
        endpoint_name=SagemakerConfig.ENDPOINT_NAME,
        region=SagemakerConfig.REGION
    )
    
    image_path = Path("samples/product_image.jpg")
    
    if not image_path.exists():
        logger.warning("Sample image not found, skipping example")
        return
    
    with open(image_path, 'rb') as f:
        image_bytes = f.read()
    
    try:
        # Invoke vision model (backward compatibility)
        result = client.invoke_vision_model(image_bytes)
        
        logger.info(f"Category: {result.get('category', 'unknown')}")
        logger.info(f"Confidence: {result.get('confidence', 0.0):.2f}")
        
        # Check confidence level
        confidence = result.get('confidence', 0.0)
        level = client.get_confidence_level(confidence, is_vision=True)
        logger.info(f"Confidence Level: {level.value}")
        
        logger.info("✓ Vision inference completed successfully")
        
    except Exception as e:
        logger.error(f"✗ Vision inference failed: {e}")


def example_asr_only():
    """Example: ASR-only inference"""
    logger.info("\n=== Example: ASR-Only Inference ===")
    
    client = SagemakerClient(
        endpoint_name=SagemakerConfig.ENDPOINT_NAME,
        region=SagemakerConfig.REGION
    )
    
    audio_path = Path("samples/product_description.opus")
    
    if not audio_path.exists():
        logger.warning("Sample audio not found, skipping example")
        return
    
    with open(audio_path, 'rb') as f:
        audio_bytes = f.read()
    
    try:
        # Invoke ASR model (backward compatibility)
        result = client.invoke_asr_model(audio_bytes, language_code='hi')
        
        logger.info(f"Transcription: {result.get('text', '')}")
        logger.info(f"Language: {result.get('language', 'unknown')}")
        logger.info(f"Confidence: {result.get('confidence', 0.0):.2f}")
        
        # Check confidence level
        confidence = result.get('confidence', 0.0)
        level = client.get_confidence_level(confidence, is_vision=False)
        logger.info(f"Confidence Level: {level.value}")
        
        logger.info("✓ ASR inference completed successfully")
        
    except Exception as e:
        logger.error(f"✗ ASR inference failed: {e}")


def example_error_handling():
    """Example: Error handling and retry logic"""
    logger.info("\n=== Example: Error Handling ===")
    
    # Initialize client with custom retry settings
    client = SagemakerClient(
        endpoint_name="non-existent-endpoint",  # This will fail
        region=SagemakerConfig.REGION,
        timeout_seconds=5,
        max_retries=2
    )
    
    try:
        # This will trigger retry logic
        result = client.invoke_combined_endpoint(
            image_bytes=b"fake_image_data"
        )
        logger.info("Unexpected success")
        
    except Exception as e:
        logger.info(f"Expected error caught: {type(e).__name__}")
        logger.info("✓ Error handling working as expected")


def example_health_check():
    """Example: Endpoint health check"""
    logger.info("\n=== Example: Health Check ===")
    
    client = SagemakerClient(
        endpoint_name=SagemakerConfig.ENDPOINT_NAME,
        region=SagemakerConfig.REGION
    )
    
    is_healthy = client.health_check()
    
    if is_healthy:
        logger.info("✓ Endpoint is healthy and ready")
    else:
        logger.warning("⚠️  Endpoint is not healthy")


def example_config_validation():
    """Example: Configuration validation"""
    logger.info("\n=== Example: Configuration Validation ===")
    
    is_valid = SagemakerConfig.validate_config()
    
    if is_valid:
        logger.info("✓ Configuration is valid")
        logger.info(f"  Endpoint: {SagemakerConfig.ENDPOINT_NAME}")
        logger.info(f"  Region: {SagemakerConfig.REGION}")
        logger.info(f"  Timeout: {SagemakerConfig.TIMEOUT_SECONDS}s")
        logger.info(f"  Max Retries: {SagemakerConfig.MAX_RETRIES}")
        logger.info(f"  ASR Threshold: {SagemakerConfig.ASR_CONFIDENCE_THRESHOLD}")
        logger.info(f"  Vision Threshold: {SagemakerConfig.VISION_CONFIDENCE_THRESHOLD}")
    else:
        logger.error("✗ Configuration is invalid")
    
    # Check supported languages
    logger.info(f"\nSupported Languages ({len(SagemakerConfig.SUPPORTED_LANGUAGES)}):")
    for lang_code in SagemakerConfig.SUPPORTED_LANGUAGES:
        lang_name = SagemakerConfig.get_language_name(lang_code)
        logger.info(f"  {lang_code}: {lang_name}")


if __name__ == "__main__":
    logger.info("Sagemaker Client Examples\n")
    
    # Run examples
    example_config_validation()
    example_health_check()
    
    # These require actual media files and a deployed endpoint
    # example_combined_inference()
    # example_vision_only()
    # example_asr_only()
    # example_error_handling()
    
    logger.info("\n✓ All examples completed")
