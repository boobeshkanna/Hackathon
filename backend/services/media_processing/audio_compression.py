"""
Audio compression module for Vernacular Artisan Catalog.

Implements Opus codec compression, audio quality metrics calculation (SNR),
and audio duration validation.

Requirements: 1.4, 4.5
"""

from typing import Dict, Optional
from io import BytesIO
import numpy as np
from pydub import AudioSegment
from pydub.exceptions import CouldntDecodeError
import shutil


class AudioCompressionError(Exception):
    """Raised when audio compression fails."""
    pass


class AudioDurationError(Exception):
    """Raised when audio duration exceeds maximum allowed."""
    pass


class FFmpegNotFoundError(AudioCompressionError):
    """Raised when ffmpeg is not installed on the system."""
    pass


MAX_AUDIO_DURATION_SECONDS = 120  # 2 minutes


def _check_ffmpeg_installed() -> None:
    """
    Check if ffmpeg and ffprobe are installed on the system.
    
    Raises:
        FFmpegNotFoundError: If ffmpeg or ffprobe is not found
    """
    ffmpeg_path = shutil.which("ffmpeg")
    ffprobe_path = shutil.which("ffprobe")
    
    if not ffmpeg_path or not ffprobe_path:
        missing = []
        if not ffmpeg_path:
            missing.append("ffmpeg")
        if not ffprobe_path:
            missing.append("ffprobe")
        
        raise FFmpegNotFoundError(
            f"Required system dependencies not found: {', '.join(missing)}. "
            f"Please install ffmpeg on your system:\n"
            f"  - Ubuntu/Debian: sudo apt install -y ffmpeg\n"
            f"  - Fedora/RHEL: sudo dnf install -y ffmpeg\n"
            f"  - macOS: brew install ffmpeg\n"
            f"  - Windows: Download from https://ffmpeg.org/download.html\n"
            f"See docs/QUICKSTART.md for detailed installation instructions."
        )


def compress_audio(
    audio_data: bytes,
    bitrate: str = "32k",
    codec: str = "libopus",
    validate_duration: bool = True
) -> bytes:
    """
    Compress audio to Opus codec format with specified bitrate.
    
    Args:
        audio_data: Raw audio bytes (any format supported by pydub)
        bitrate: Target bitrate (default "32k" = 32kbps)
        codec: Audio codec (default "libopus" for Opus)
        validate_duration: Whether to validate max duration (default True)
    
    Returns:
        Compressed audio bytes in Opus format
    
    Raises:
        AudioCompressionError: If compression fails
        AudioDurationError: If audio exceeds max duration (2 minutes)
        FFmpegNotFoundError: If ffmpeg is not installed
    
    Requirements: 1.4, 4.5
    """
    # Check ffmpeg installation first
    _check_ffmpeg_installed()
    
    try:
        # Load audio from bytes
        audio = AudioSegment.from_file(BytesIO(audio_data))
        
        # Validate duration
        duration_seconds = len(audio) / 1000.0  # pydub uses milliseconds
        
        if validate_duration and duration_seconds > MAX_AUDIO_DURATION_SECONDS:
            raise AudioDurationError(
                f"Audio duration ({duration_seconds:.1f}s) exceeds maximum "
                f"allowed duration ({MAX_AUDIO_DURATION_SECONDS}s)"
            )
        
        # Export to Opus format with specified bitrate
        output = BytesIO()
        audio.export(
            output,
            format="opus",
            codec=codec,
            bitrate=bitrate,
            parameters=["-vbr", "on"]  # Enable variable bitrate for better quality
        )
        
        compressed_data = output.getvalue()
        
        return compressed_data
        
    except AudioDurationError:
        raise
    except FFmpegNotFoundError:
        raise
    except CouldntDecodeError as e:
        raise AudioCompressionError(f"Failed to decode audio: {str(e)}")
    except FileNotFoundError as e:
        # Catch FileNotFoundError for ffmpeg/ffprobe
        if 'ffmpeg' in str(e) or 'ffprobe' in str(e):
            raise FFmpegNotFoundError(
                f"ffmpeg or ffprobe not found. Please install ffmpeg on your system. "
                f"See docs/QUICKSTART.md for installation instructions."
            )
        raise AudioCompressionError(f"Failed to compress audio: {str(e)}")
    except Exception as e:
        raise AudioCompressionError(f"Failed to compress audio: {str(e)}")


def get_audio_duration(audio_data: bytes) -> float:
    """
    Get audio duration in seconds.
    
    Args:
        audio_data: Audio bytes
    
    Returns:
        Duration in seconds
    
    Raises:
        AudioCompressionError: If duration calculation fails
        FFmpegNotFoundError: If ffmpeg is not installed
    
    Requirements: 4.5
    """
    # Check ffmpeg installation first
    _check_ffmpeg_installed()
    
    try:
        audio = AudioSegment.from_file(BytesIO(audio_data))
        return len(audio) / 1000.0  # Convert milliseconds to seconds
    except FFmpegNotFoundError:
        raise
    except FileNotFoundError as e:
        if 'ffmpeg' in str(e) or 'ffprobe' in str(e):
            raise FFmpegNotFoundError(
                f"ffmpeg or ffprobe not found. Please install ffmpeg on your system. "
                f"See docs/QUICKSTART.md for installation instructions."
            )
        raise AudioCompressionError(f"Failed to get audio duration: {str(e)}")
    except Exception as e:
        raise AudioCompressionError(f"Failed to get audio duration: {str(e)}")


def validate_audio_duration(audio_data: bytes, max_duration: int = MAX_AUDIO_DURATION_SECONDS) -> bool:
    """
    Validate that audio duration does not exceed maximum allowed.
    
    Args:
        audio_data: Audio bytes
        max_duration: Maximum duration in seconds (default 120)
    
    Returns:
        True if duration is valid, False otherwise
    
    Requirements: 4.5
    """
    try:
        duration = get_audio_duration(audio_data)
        return duration <= max_duration
    except AudioCompressionError:
        return False


def calculate_snr(original: bytes, compressed: bytes) -> float:
    """
    Calculate Signal-to-Noise Ratio (SNR) between original and compressed audio.
    
    Higher SNR indicates better quality. Typical values:
    - > 40 dB: Excellent quality
    - 20-40 dB: Good quality
    - 10-20 dB: Acceptable quality
    - < 10 dB: Poor quality
    
    Args:
        original: Original audio bytes
        compressed: Compressed audio bytes
    
    Returns:
        SNR value in decibels (dB)
    
    Raises:
        AudioCompressionError: If SNR calculation fails
        FFmpegNotFoundError: If ffmpeg is not installed
    
    Requirements: 1.4
    """
    # Check ffmpeg installation first
    _check_ffmpeg_installed()
    
    try:
        # Load audio files
        audio1 = AudioSegment.from_file(BytesIO(original))
        audio2 = AudioSegment.from_file(BytesIO(compressed))
        
        # Ensure same duration and sample rate
        if len(audio1) != len(audio2):
            # Trim to shorter duration
            min_len = min(len(audio1), len(audio2))
            audio1 = audio1[:min_len]
            audio2 = audio2[:min_len]
        
        # Ensure same sample rate
        if audio1.frame_rate != audio2.frame_rate:
            audio2 = audio2.set_frame_rate(audio1.frame_rate)
        
        # Convert to mono for comparison
        audio1 = audio1.set_channels(1)
        audio2 = audio2.set_channels(1)
        
        # Convert to numpy arrays
        samples1 = np.array(audio1.get_array_of_samples(), dtype=np.float64)
        samples2 = np.array(audio2.get_array_of_samples(), dtype=np.float64)
        
        # Calculate signal power
        signal_power = np.mean(samples1 ** 2)
        
        # Calculate noise (difference between original and compressed)
        noise = samples1 - samples2
        noise_power = np.mean(noise ** 2)
        
        # Avoid division by zero
        if noise_power == 0:
            return float('inf')  # Perfect reconstruction
        
        if signal_power == 0:
            return 0.0  # Silent audio
        
        # Calculate SNR in dB
        snr = 10 * np.log10(signal_power / noise_power)
        
        return float(snr)
        
    except FFmpegNotFoundError:
        raise
    except FileNotFoundError as e:
        if 'ffmpeg' in str(e) or 'ffprobe' in str(e):
            raise FFmpegNotFoundError(
                f"ffmpeg or ffprobe not found. Please install ffmpeg on your system. "
                f"See docs/QUICKSTART.md for installation instructions."
            )
        raise AudioCompressionError(f"Failed to calculate SNR: {str(e)}")
    except Exception as e:
        raise AudioCompressionError(f"Failed to calculate SNR: {str(e)}")


def calculate_audio_quality_metrics(original: bytes, compressed: bytes) -> Dict[str, float]:
    """
    Calculate comprehensive quality metrics for compressed audio.
    
    Args:
        original: Original audio bytes
        compressed: Compressed audio bytes
    
    Returns:
        Dictionary with quality metrics:
        - snr: Signal-to-Noise Ratio (dB)
        - compression_ratio: Original size / Compressed size
        - duration: Audio duration in seconds
    
    Requirements: 1.4
    """
    snr = calculate_snr(original, compressed)
    compression_ratio = len(original) / len(compressed) if len(compressed) > 0 else 0
    duration = get_audio_duration(original)
    
    return {
        'snr': snr,
        'compression_ratio': compression_ratio,
        'duration': duration,
        'original_size': len(original),
        'compressed_size': len(compressed)
    }
