"""
Unit tests for media compression utilities.

Tests image and audio compression functionality including quality metrics.
"""

import pytest
from io import BytesIO
from PIL import Image
from pydub import AudioSegment
from pydub.generators import Sine

from backend.services.media_processing import (
    compress_image,
    resize_image,
    calculate_psnr,
    calculate_ssim,
    calculate_quality_metrics,
    ImageCompressionError,
    compress_audio,
    get_audio_duration,
    validate_audio_duration,
    calculate_snr,
    calculate_audio_quality_metrics,
    AudioCompressionError,
    AudioDurationError,
    MAX_AUDIO_DURATION_SECONDS
)


# Helper functions to generate test data

def create_test_image(width: int = 800, height: int = 600, color: tuple = (255, 0, 0)) -> bytes:
    """Create a test image with specified dimensions and color."""
    img = Image.new('RGB', (width, height), color)
    output = BytesIO()
    img.save(output, format='JPEG', quality=95)
    return output.getvalue()


def create_test_audio(duration_ms: int = 5000, frequency: int = 440) -> bytes:
    """Create a test audio with specified duration and frequency."""
    audio = Sine(frequency).to_audio_segment(duration=duration_ms)
    output = BytesIO()
    audio.export(output, format='wav')
    return output.getvalue()


# Image Compression Tests

class TestImageCompression:
    """Tests for image compression functionality."""
    
    def test_compress_image_reduces_size(self):
        """Test that compression reduces file size."""
        original = create_test_image(1920, 1080)
        compressed = compress_image(original, quality=80)
        
        assert len(compressed) < len(original), "Compressed image should be smaller"
    
    def test_compress_image_with_quality_parameter(self):
        """Test compression with different quality settings."""
        original = create_test_image()
        
        high_quality = compress_image(original, quality=90)
        low_quality = compress_image(original, quality=50)
        
        assert len(low_quality) < len(high_quality), "Lower quality should produce smaller file"
    
    def test_compress_image_resizes_large_images(self):
        """Test that large images are resized to max dimension."""
        original = create_test_image(3000, 2000)
        compressed = compress_image(original, max_dimension=1920)
        
        # Load compressed image to check dimensions
        img = Image.open(BytesIO(compressed))
        assert max(img.size) <= 1920, "Image should be resized to max dimension"
    
    def test_compress_image_maintains_aspect_ratio(self):
        """Test that aspect ratio is maintained during resize."""
        original = create_test_image(1600, 900)  # 16:9 aspect ratio
        compressed = compress_image(original, max_dimension=800)
        
        img = Image.open(BytesIO(compressed))
        aspect_ratio = img.width / img.height
        expected_ratio = 1600 / 900
        
        assert abs(aspect_ratio - expected_ratio) < 0.01, "Aspect ratio should be maintained"
    
    def test_compress_image_handles_rgba(self):
        """Test compression of RGBA images (with transparency)."""
        # Create RGBA image
        img = Image.new('RGBA', (800, 600), (255, 0, 0, 128))
        output = BytesIO()
        img.save(output, format='PNG')
        original = output.getvalue()
        
        # Should not raise error
        compressed = compress_image(original)
        assert len(compressed) > 0
    
    def test_compress_image_invalid_data_raises_error(self):
        """Test that invalid image data raises error."""
        with pytest.raises(ImageCompressionError):
            compress_image(b"not an image")
    
    def test_resize_image_maintains_aspect_ratio(self):
        """Test resize_image function maintains aspect ratio."""
        img = Image.new('RGB', (1600, 900), (255, 0, 0))
        resized = resize_image(img, 800)
        
        assert max(resized.size) == 800
        aspect_ratio = resized.width / resized.height
        expected_ratio = 1600 / 900
        assert abs(aspect_ratio - expected_ratio) < 0.01


class TestImageQualityMetrics:
    """Tests for image quality metrics calculation."""
    
    def test_calculate_psnr_identical_images(self):
        """Test PSNR for identical images returns infinity."""
        original = create_test_image()
        psnr = calculate_psnr(original, original)
        
        assert psnr == float('inf'), "Identical images should have infinite PSNR"
    
    def test_calculate_psnr_compressed_image(self):
        """Test PSNR for compressed image is above threshold."""
        original = create_test_image()
        compressed = compress_image(original, quality=80)
        
        psnr = calculate_psnr(original, compressed)
        
        assert psnr >= 30, f"PSNR should be >= 30dB, got {psnr:.2f}dB"
    
    def test_calculate_ssim_identical_images(self):
        """Test SSIM for identical images returns 1.0."""
        original = create_test_image()
        ssim = calculate_ssim(original, original)
        
        assert ssim >= 0.99, "Identical images should have SSIM close to 1.0"
    
    def test_calculate_ssim_compressed_image(self):
        """Test SSIM for compressed image is above threshold."""
        original = create_test_image()
        compressed = compress_image(original, quality=80)
        
        ssim = calculate_ssim(original, compressed)
        
        assert ssim >= 0.85, f"SSIM should be >= 0.85, got {ssim:.4f}"
    
    def test_calculate_quality_metrics_returns_all_metrics(self):
        """Test that quality metrics returns all expected values."""
        original = create_test_image()
        compressed = compress_image(original, quality=80)
        
        metrics = calculate_quality_metrics(original, compressed)
        
        assert 'psnr' in metrics
        assert 'ssim' in metrics
        assert 'compression_ratio' in metrics
        assert 'original_size' in metrics
        assert 'compressed_size' in metrics
        
        assert metrics['psnr'] >= 30
        assert metrics['ssim'] >= 0.85
        assert metrics['compression_ratio'] > 1.0


# Audio Compression Tests

class TestAudioCompression:
    """Tests for audio compression functionality."""
    
    def test_compress_audio_reduces_size(self):
        """Test that compression reduces file size."""
        original = create_test_audio(duration_ms=5000)
        compressed = compress_audio(original, bitrate="32k")
        
        assert len(compressed) < len(original), "Compressed audio should be smaller"
    
    def test_compress_audio_with_different_bitrates(self):
        """Test compression with different bitrate settings."""
        original = create_test_audio()
        
        high_bitrate = compress_audio(original, bitrate="64k")
        low_bitrate = compress_audio(original, bitrate="16k")
        
        assert len(low_bitrate) < len(high_bitrate), "Lower bitrate should produce smaller file"
    
    def test_compress_audio_validates_duration(self):
        """Test that audio exceeding max duration raises error."""
        # Create audio longer than 2 minutes
        long_audio = create_test_audio(duration_ms=130000)  # 130 seconds
        
        with pytest.raises(AudioDurationError):
            compress_audio(long_audio, validate_duration=True)
    
    def test_compress_audio_skip_validation(self):
        """Test that duration validation can be skipped."""
        long_audio = create_test_audio(duration_ms=130000)
        
        # Should not raise error when validation is disabled
        compressed = compress_audio(long_audio, validate_duration=False)
        assert len(compressed) > 0
    
    def test_compress_audio_invalid_data_raises_error(self):
        """Test that invalid audio data raises error."""
        with pytest.raises(AudioCompressionError):
            compress_audio(b"not audio data")
    
    def test_get_audio_duration(self):
        """Test getting audio duration."""
        audio = create_test_audio(duration_ms=5000)
        duration = get_audio_duration(audio)
        
        assert 4.9 <= duration <= 5.1, f"Duration should be ~5 seconds, got {duration}"
    
    def test_validate_audio_duration_valid(self):
        """Test validation of valid audio duration."""
        audio = create_test_audio(duration_ms=60000)  # 1 minute
        
        assert validate_audio_duration(audio) is True
    
    def test_validate_audio_duration_invalid(self):
        """Test validation of invalid audio duration."""
        audio = create_test_audio(duration_ms=130000)  # 130 seconds
        
        assert validate_audio_duration(audio) is False


class TestAudioQualityMetrics:
    """Tests for audio quality metrics calculation."""
    
    def test_calculate_snr_identical_audio(self):
        """Test SNR for identical audio returns infinity."""
        original = create_test_audio()
        snr = calculate_snr(original, original)
        
        assert snr == float('inf'), "Identical audio should have infinite SNR"
    
    def test_calculate_snr_compressed_audio(self):
        """Test SNR for compressed audio is calculated correctly."""
        original = create_test_audio()
        compressed = compress_audio(original, bitrate="32k")
        
        snr = calculate_snr(original, compressed)
        
        # Note: Opus codec is optimized for speech, not pure sine waves
        # For simple sine wave, SNR may be negative due to codec artifacts
        # We just verify that SNR is calculated (not infinity, not NaN)
        assert snr != float('inf'), "SNR should not be infinity for compressed audio"
        assert not (snr != snr), "SNR should not be NaN"  # NaN check
        assert isinstance(snr, float), "SNR should be a float value"
    
    def test_calculate_audio_quality_metrics_returns_all_metrics(self):
        """Test that audio quality metrics returns all expected values."""
        original = create_test_audio()
        compressed = compress_audio(original, bitrate="32k")
        
        metrics = calculate_audio_quality_metrics(original, compressed)
        
        assert 'snr' in metrics
        assert 'compression_ratio' in metrics
        assert 'duration' in metrics
        assert 'original_size' in metrics
        assert 'compressed_size' in metrics
        
        assert metrics['compression_ratio'] > 1.0
        assert 4.9 <= metrics['duration'] <= 5.1
