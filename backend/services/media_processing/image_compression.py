"""
Image compression module for Vernacular Artisan Catalog.

Implements JPEG compression with quality parameter, image resizing,
and quality metrics calculation (PSNR, SSIM).

Requirements: 1.2, 6.4
"""

from typing import Tuple, Dict, Optional
from io import BytesIO
import numpy as np
from PIL import Image
import cv2


class ImageCompressionError(Exception):
    """Raised when image compression fails."""
    pass


def compress_image(
    image_data: bytes,
    quality: int = 80,
    max_dimension: int = 1920,
    output_format: str = "JPEG"
) -> bytes:
    """
    Compress image to JPEG format with specified quality and resize to max dimensions.
    
    Args:
        image_data: Raw image bytes
        quality: JPEG compression quality (1-100, default 80%)
        max_dimension: Maximum width or height in pixels (default 1920px)
        output_format: Output format (default "JPEG")
    
    Returns:
        Compressed image bytes
    
    Raises:
        ImageCompressionError: If compression fails
    
    Requirements: 1.2, 6.4
    """
    try:
        # Load image from bytes
        image = Image.open(BytesIO(image_data))
        
        # Convert to RGB if necessary (JPEG doesn't support transparency)
        if image.mode in ('RGBA', 'LA', 'P'):
            # Create white background
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode in ('RGBA', 'LA') else None)
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Resize if needed
        if max(image.size) > max_dimension:
            image = resize_image(image, max_dimension)
        
        # Compress to JPEG
        output = BytesIO()
        image.save(output, format=output_format, quality=quality, optimize=True)
        compressed_data = output.getvalue()
        
        return compressed_data
        
    except Exception as e:
        raise ImageCompressionError(f"Failed to compress image: {str(e)}")


def resize_image(image: Image.Image, max_dimension: int) -> Image.Image:
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
    
    if width > height:
        new_width = max_dimension
        new_height = int(height * (max_dimension / width))
    else:
        new_height = max_dimension
        new_width = int(width * (max_dimension / height))
    
    return image.resize((new_width, new_height), Image.Resampling.LANCZOS)


def calculate_psnr(original: bytes, compressed: bytes) -> float:
    """
    Calculate Peak Signal-to-Noise Ratio (PSNR) between original and compressed images.
    
    Higher PSNR indicates better quality. Typical values:
    - > 40 dB: Excellent quality
    - 30-40 dB: Good quality
    - 20-30 dB: Acceptable quality
    - < 20 dB: Poor quality
    
    Args:
        original: Original image bytes
        compressed: Compressed image bytes
    
    Returns:
        PSNR value in decibels (dB)
    
    Raises:
        ImageCompressionError: If PSNR calculation fails
    
    Requirements: 1.2
    """
    try:
        # Load images
        img1 = Image.open(BytesIO(original))
        img2 = Image.open(BytesIO(compressed))
        
        # Ensure same size
        if img1.size != img2.size:
            img2 = img2.resize(img1.size, Image.Resampling.LANCZOS)
        
        # Convert to numpy arrays
        arr1 = np.array(img1.convert('RGB'), dtype=np.float64)
        arr2 = np.array(img2.convert('RGB'), dtype=np.float64)
        
        # Calculate MSE (Mean Squared Error)
        mse = np.mean((arr1 - arr2) ** 2)
        
        if mse == 0:
            return float('inf')  # Images are identical
        
        # Calculate PSNR
        max_pixel = 255.0
        psnr = 20 * np.log10(max_pixel / np.sqrt(mse))
        
        return float(psnr)
        
    except Exception as e:
        raise ImageCompressionError(f"Failed to calculate PSNR: {str(e)}")


def calculate_ssim(original: bytes, compressed: bytes) -> float:
    """
    Calculate Structural Similarity Index (SSIM) between original and compressed images.
    
    SSIM ranges from -1 to 1, where 1 indicates perfect similarity.
    Typical values:
    - > 0.95: Excellent quality
    - 0.85-0.95: Good quality
    - 0.70-0.85: Acceptable quality
    - < 0.70: Poor quality
    
    Args:
        original: Original image bytes
        compressed: Compressed image bytes
    
    Returns:
        SSIM value (0-1, higher is better)
    
    Raises:
        ImageCompressionError: If SSIM calculation fails
    
    Requirements: 1.2
    """
    try:
        # Load images
        img1 = Image.open(BytesIO(original))
        img2 = Image.open(BytesIO(compressed))
        
        # Ensure same size
        if img1.size != img2.size:
            img2 = img2.resize(img1.size, Image.Resampling.LANCZOS)
        
        # Convert to grayscale numpy arrays
        arr1 = np.array(img1.convert('L'), dtype=np.float64)
        arr2 = np.array(img2.convert('L'), dtype=np.float64)
        
        # Calculate SSIM using OpenCV
        # Note: cv2.SSIM is not available in all versions, so we implement it manually
        C1 = (0.01 * 255) ** 2
        C2 = (0.03 * 255) ** 2
        
        mu1 = cv2.GaussianBlur(arr1, (11, 11), 1.5)
        mu2 = cv2.GaussianBlur(arr2, (11, 11), 1.5)
        
        mu1_sq = mu1 ** 2
        mu2_sq = mu2 ** 2
        mu1_mu2 = mu1 * mu2
        
        sigma1_sq = cv2.GaussianBlur(arr1 ** 2, (11, 11), 1.5) - mu1_sq
        sigma2_sq = cv2.GaussianBlur(arr2 ** 2, (11, 11), 1.5) - mu2_sq
        sigma12 = cv2.GaussianBlur(arr1 * arr2, (11, 11), 1.5) - mu1_mu2
        
        ssim_map = ((2 * mu1_mu2 + C1) * (2 * sigma12 + C2)) / \
                   ((mu1_sq + mu2_sq + C1) * (sigma1_sq + sigma2_sq + C2))
        
        ssim_value = float(np.mean(ssim_map))
        
        return ssim_value
        
    except Exception as e:
        raise ImageCompressionError(f"Failed to calculate SSIM: {str(e)}")


def calculate_quality_metrics(original: bytes, compressed: bytes) -> Dict[str, float]:
    """
    Calculate comprehensive quality metrics for compressed image.
    
    Args:
        original: Original image bytes
        compressed: Compressed image bytes
    
    Returns:
        Dictionary with quality metrics:
        - psnr: Peak Signal-to-Noise Ratio (dB)
        - ssim: Structural Similarity Index (0-1)
        - compression_ratio: Original size / Compressed size
    
    Requirements: 1.2
    """
    psnr = calculate_psnr(original, compressed)
    ssim = calculate_ssim(original, compressed)
    compression_ratio = len(original) / len(compressed) if len(compressed) > 0 else 0
    
    return {
        'psnr': psnr,
        'ssim': ssim,
        'compression_ratio': compression_ratio,
        'original_size': len(original),
        'compressed_size': len(compressed)
    }
