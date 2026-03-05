"""
Image enhancement module for Lambda processing.

Implements brightness/contrast adjustment, sharpening filters, quality assessment,
multi-resolution image generation, and S3 upload integration.

Requirements: 6.1, 6.2, 6.3, 6.4, 6.5
"""

from typing import Dict, List, Tuple, Union, Optional
from io import BytesIO
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import cv2
import boto3
from botocore.exceptions import ClientError
from aws_lambda_powertools import Logger

from backend.lambda_functions.shared.config import config

logger = Logger()


class ImageEnhancementError(Exception):
    """Raised when image enhancement fails."""
    pass


class ImageQualityError(Exception):
    """Raised when image quality is too poor for enhancement."""
    pass


def adjust_brightness_contrast(
    image: Image.Image,
    brightness_factor: float = 1.2,
    contrast_factor: float = 1.1
) -> Image.Image:
    """
    Adjust brightness and contrast of an image.
    
    Args:
        image: PIL Image object
        brightness_factor: Brightness multiplier (1.0 = no change, >1.0 = brighter)
        contrast_factor: Contrast multiplier (1.0 = no change, >1.0 = more contrast)
    
    Returns:
        Enhanced PIL Image object
    
    Requirements: 6.2
    """
    try:
        # Adjust brightness
        enhancer = ImageEnhance.Brightness(image)
        image = enhancer.enhance(brightness_factor)
        
        # Adjust contrast
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(contrast_factor)
        
        return image
    except Exception as e:
        raise ImageEnhancementError(f"Failed to adjust brightness/contrast: {str(e)}")


def sharpen_image(image: Image.Image, strength: float = 1.5) -> Image.Image:
    """
    Apply sharpening filter to improve blurry images.
    
    Args:
        image: PIL Image object
        strength: Sharpening strength (1.0 = no change, >1.0 = sharper)
    
    Returns:
        Sharpened PIL Image object
    
    Requirements: 6.3
    """
    try:
        # Apply unsharp mask for sharpening
        enhancer = ImageEnhance.Sharpness(image)
        sharpened = enhancer.enhance(strength)
        
        return sharpened
    except Exception as e:
        raise ImageEnhancementError(f"Failed to sharpen image: {str(e)}")


def detect_blur(image_data: Union[bytes, Image.Image]) -> float:
    """
    Detect blur in image using Laplacian variance method.
    
    Lower values indicate more blur. Typical thresholds:
    - > 100: Sharp image
    - 50-100: Acceptable sharpness
    - < 50: Blurry image
    
    Args:
        image_data: Image bytes or PIL Image object
    
    Returns:
        Laplacian variance (higher = sharper)
    
    Requirements: 6.3, 6.5
    """
    try:
        # Load image if bytes
        if isinstance(image_data, bytes):
            image = Image.open(BytesIO(image_data))
        else:
            image = image_data
        
        # Convert to grayscale numpy array
        gray = np.array(image.convert('L'))
        
        # Calculate Laplacian variance
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        variance = laplacian.var()
        
        return float(variance)
    except Exception as e:
        raise ImageEnhancementError(f"Failed to detect blur: {str(e)}")


def check_brightness(image_data: Union[bytes, Image.Image]) -> float:
    """
    Check average brightness of image.
    
    Returns mean brightness value (0-255):
    - > 150: Bright image
    - 100-150: Normal brightness
    - 50-100: Low brightness
    - < 50: Very dark image
    
    Args:
        image_data: Image bytes or PIL Image object
    
    Returns:
        Mean brightness value (0-255)
    
    Requirements: 6.2, 6.5
    """
    try:
        # Load image if bytes
        if isinstance(image_data, bytes):
            image = Image.open(BytesIO(image_data))
        else:
            image = image_data
        
        # Convert to grayscale and calculate mean
        gray = np.array(image.convert('L'))
        mean_brightness = float(np.mean(gray))
        
        return mean_brightness
    except Exception as e:
        raise ImageEnhancementError(f"Failed to check brightness: {str(e)}")


def assess_quality(image_data: Union[bytes, Image.Image]) -> Dict[str, float]:
    """
    Assess overall image quality.
    
    Args:
        image_data: Image bytes or PIL Image object
    
    Returns:
        Dictionary with quality metrics:
        - blur_score: Laplacian variance (higher = sharper)
        - brightness: Mean brightness (0-255)
        - is_acceptable: Boolean indicating if quality is acceptable
    
    Requirements: 6.3, 6.5
    """
    blur_score = detect_blur(image_data)
    brightness = check_brightness(image_data)
    
    # Quality thresholds
    MIN_BLUR_SCORE = 50.0
    MIN_BRIGHTNESS = 20.0
    MAX_BRIGHTNESS = 240.0
    
    is_acceptable = (
        blur_score >= MIN_BLUR_SCORE and
        MIN_BRIGHTNESS <= brightness <= MAX_BRIGHTNESS
    )
    
    return {
        'blur_score': blur_score,
        'brightness': brightness,
        'is_acceptable': is_acceptable,
        'needs_sharpening': blur_score < 100.0,
        'needs_brightness_adjustment': brightness < 100.0 or brightness > 200.0
    }


def generate_multi_resolution(
    image: Image.Image,
    sizes: Optional[Dict[str, int]] = None
) -> Dict[str, bytes]:
    """
    Generate multiple image sizes for different display contexts.
    
    Default sizes:
    - thumbnail: ≤200px
    - medium: ≤800px
    - full: ≤1920px
    
    Args:
        image: PIL Image object
        sizes: Optional dict of size names to max dimensions
    
    Returns:
        Dictionary mapping size names to image bytes
    
    Requirements: 6.4
    """
    if sizes is None:
        sizes = {
            'thumbnail': 200,
            'medium': 800,
            'full': 1920
        }
    
    try:
        result = {}
        
        for size_name, max_dimension in sizes.items():
            # Resize image
            resized = resize_to_max_dimension(image, max_dimension)
            
            # Convert to bytes
            output = BytesIO()
            resized.save(output, format='JPEG', quality=85, optimize=True)
            result[size_name] = output.getvalue()
        
        return result
    except Exception as e:
        raise ImageEnhancementError(f"Failed to generate multi-resolution images: {str(e)}")


def resize_to_max_dimension(image: Image.Image, max_dimension: int) -> Image.Image:
    """
    Resize image maintaining aspect ratio to fit within max_dimension.
    
    Args:
        image: PIL Image object
        max_dimension: Maximum width or height in pixels
    
    Returns:
        Resized PIL Image object
    
    Requirements: 6.4
    """
    width, height = image.size
    
    # Skip if already smaller
    if max(width, height) <= max_dimension:
        return image.copy()
    
    if width > height:
        new_width = max_dimension
        new_height = int(height * (max_dimension / width))
    else:
        new_height = max_dimension
        new_width = int(width * (max_dimension / height))
    
    return image.resize((new_width, new_height), Image.Resampling.LANCZOS)


def upload_to_s3(
    image_bytes: bytes,
    s3_key: str,
    content_type: str = 'image/jpeg',
    metadata: Optional[Dict[str, str]] = None
) -> str:
    """
    Upload image to S3 enhanced bucket.
    
    Args:
        image_bytes: Image data as bytes
        s3_key: S3 object key
        content_type: MIME type
        metadata: Optional metadata dict
    
    Returns:
        S3 key of uploaded image
    
    Raises:
        ImageEnhancementError: If upload fails
    
    Requirements: 6.4
    """
    try:
        s3_client = boto3.client('s3', region_name=config.AWS_REGION)
        
        upload_args = {
            'Bucket': config.S3_ENHANCED_BUCKET,
            'Key': s3_key,
            'Body': image_bytes,
            'ContentType': content_type
        }
        
        if metadata:
            upload_args['Metadata'] = metadata
        
        s3_client.put_object(**upload_args)
        
        logger.info(
            "Image uploaded to S3",
            extra={
                "s3_key": s3_key,
                "bucket": config.S3_ENHANCED_BUCKET,
                "size": len(image_bytes)
            }
        )
        
        return s3_key
    except ClientError as e:
        logger.error(f"AWS error uploading to S3: {str(e)}", exc_info=True)
        raise ImageEnhancementError(f"Failed to upload to S3: {str(e)}")
    except Exception as e:
        logger.error(f"Error uploading to S3: {str(e)}", exc_info=True)
        raise ImageEnhancementError(f"Failed to upload to S3: {str(e)}")


def enhance_and_upload(
    image_data: bytes,
    tracking_id: str,
    tenant_id: str,
    artisan_id: str,
    auto_enhance: bool = True
) -> Dict[str, any]:
    """
    Main enhancement pipeline: assess quality, enhance, generate sizes, upload to S3.
    
    This is the primary function that orchestrates all enhancement operations:
    1. Load and assess image quality
    2. Apply enhancements if needed (brightness, contrast, sharpening)
    3. Generate multiple resolutions (thumbnail, medium, full)
    4. Upload all versions to S3 enhanced bucket
    5. Return quality metrics and S3 keys
    
    Args:
        image_data: Raw image bytes
        tracking_id: Unique tracking identifier
        tenant_id: Tenant organization identifier
        artisan_id: Artisan identifier
        auto_enhance: Whether to automatically apply enhancements
    
    Returns:
        Dictionary with:
        - quality_metrics: Quality assessment results
        - enhancements_applied: List of enhancement operations performed
        - s3_keys: Dict mapping size names to S3 keys
        - original_size: Original image dimensions
    
    Raises:
        ImageQualityError: If image quality is too poor
        ImageEnhancementError: If enhancement fails
    
    Requirements: 6.1, 6.2, 6.3, 6.4, 6.5
    """
    try:
        # Load image
        image = Image.open(BytesIO(image_data))
        
        # Convert to RGB if necessary
        if image.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            if image.mode in ('RGBA', 'LA'):
                background.paste(image, mask=image.split()[-1])
                image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')
        
        original_size = image.size
        
        # Assess quality
        quality_metrics = assess_quality(image)
        
        logger.info(
            "Image quality assessed",
            extra={
                "tracking_id": tracking_id,
                "quality_metrics": quality_metrics
            }
        )
        
        # Check if quality is too poor
        if not quality_metrics['is_acceptable']:
            raise ImageQualityError(
                f"Image quality too poor: blur_score={quality_metrics['blur_score']:.2f}, "
                f"brightness={quality_metrics['brightness']:.2f}"
            )
        
        # Apply enhancements if needed
        enhancements_applied = []
        
        if auto_enhance:
            # Adjust brightness/contrast if needed
            if quality_metrics['needs_brightness_adjustment']:
                brightness_factor = 1.0
                if quality_metrics['brightness'] < 100:
                    brightness_factor = 1.3
                elif quality_metrics['brightness'] > 200:
                    brightness_factor = 0.8
                
                image = adjust_brightness_contrast(
                    image,
                    brightness_factor=brightness_factor,
                    contrast_factor=1.1
                )
                enhancements_applied.append('brightness_contrast')
            
            # Sharpen if blurry
            if quality_metrics['needs_sharpening']:
                image = sharpen_image(image, strength=1.5)
                enhancements_applied.append('sharpening')
        
        # Generate multiple resolutions
        multi_res_images = generate_multi_resolution(image)
        
        # Upload to S3 with proper naming
        s3_keys = {}
        base_key = f"{tenant_id}/{artisan_id}/{tracking_id}"
        
        for size_name, image_bytes in multi_res_images.items():
            s3_key = f"{base_key}/{size_name}_{tracking_id}.jpg"
            
            metadata = {
                'tracking_id': tracking_id,
                'tenant_id': tenant_id,
                'artisan_id': artisan_id,
                'size_type': size_name,
                'enhancements': ','.join(enhancements_applied) if enhancements_applied else 'none'
            }
            
            upload_to_s3(image_bytes, s3_key, metadata=metadata)
            s3_keys[size_name] = s3_key
        
        logger.info(
            "Image enhancement completed",
            extra={
                "tracking_id": tracking_id,
                "enhancements_applied": enhancements_applied,
                "s3_keys": s3_keys
            }
        )
        
        return {
            'quality_metrics': quality_metrics,
            'enhancements_applied': enhancements_applied,
            's3_keys': s3_keys,
            'original_size': original_size,
            'enhanced_sizes': {
                name: len(img_bytes) for name, img_bytes in multi_res_images.items()
            }
        }
        
    except ImageQualityError:
        # Re-raise quality errors
        raise
    except Exception as e:
        logger.error(
            f"Error in enhancement pipeline: {str(e)}",
            exc_info=True,
            extra={"tracking_id": tracking_id}
        )
        raise ImageEnhancementError(f"Enhancement pipeline failed: {str(e)}")
