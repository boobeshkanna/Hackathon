"""
Media processing services for Vernacular Artisan Catalog.

Provides image and audio compression utilities with quality metrics.
"""

from .image_compression import (
    compress_image,
    resize_image,
    calculate_psnr,
    calculate_ssim,
    calculate_quality_metrics,
    ImageCompressionError
)

from .image_enhancement import (
    enhance_and_upload,
    adjust_brightness_contrast,
    sharpen_image,
    detect_blur,
    check_brightness,
    assess_quality,
    generate_multi_resolution,
    upload_to_s3,
    ImageEnhancementError,
    ImageQualityError
)

from .audio_compression import (
    compress_audio,
    get_audio_duration,
    validate_audio_duration,
    calculate_snr,
    calculate_audio_quality_metrics,
    AudioCompressionError,
    AudioDurationError,
    FFmpegNotFoundError,
    MAX_AUDIO_DURATION_SECONDS
)

__all__ = [
    # Image compression
    'compress_image',
    'resize_image',
    'calculate_psnr',
    'calculate_ssim',
    'calculate_quality_metrics',
    'ImageCompressionError',
    # Image enhancement
    'enhance_and_upload',
    'adjust_brightness_contrast',
    'sharpen_image',
    'detect_blur',
    'check_brightness',
    'assess_quality',
    'generate_multi_resolution',
    'upload_to_s3',
    'ImageEnhancementError',
    'ImageQualityError',
    # Audio compression
    'compress_audio',
    'get_audio_duration',
    'validate_audio_duration',
    'calculate_snr',
    'calculate_audio_quality_metrics',
    'AudioCompressionError',
    'AudioDurationError',
    'FFmpegNotFoundError',
    'MAX_AUDIO_DURATION_SECONDS'
]
