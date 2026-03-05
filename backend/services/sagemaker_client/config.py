"""
Sagemaker Client Configuration

Configuration settings for the Sagemaker Vision & ASR endpoint.
"""
import os
from typing import Dict, List


class SagemakerConfig:
    """Configuration for Sagemaker client"""
    
    # Endpoint configuration
    ENDPOINT_NAME = os.getenv('SAGEMAKER_ENDPOINT_NAME', 'vernacular-vision-asr-endpoint')
    REGION = os.getenv('SAGEMAKER_REGION', 'ap-south-1')
    
    # Timeout configuration
    TIMEOUT_SECONDS = int(os.getenv('SAGEMAKER_TIMEOUT_SECONDS', '30'))
    CONNECT_TIMEOUT_SECONDS = 10
    
    # Retry configuration
    MAX_RETRIES = int(os.getenv('SAGEMAKER_MAX_RETRIES', '3'))
    INITIAL_RETRY_DELAY = 1  # seconds
    MAX_RETRY_DELAY = 10  # seconds
    
    # Confidence thresholds
    ASR_CONFIDENCE_THRESHOLD = float(os.getenv('ASR_CONFIDENCE_THRESHOLD', '0.7'))
    VISION_CONFIDENCE_THRESHOLD = float(os.getenv('VISION_CONFIDENCE_THRESHOLD', '0.6'))
    
    # Supported languages for ASR
    SUPPORTED_LANGUAGES: List[str] = [
        'hi',  # Hindi
        'ta',  # Tamil
        'te',  # Telugu
        'bn',  # Bengali
        'mr',  # Marathi
        'gu',  # Gujarati
        'kn',  # Kannada
        'ml',  # Malayalam
        'pa',  # Punjabi
        'or',  # Odia
    ]
    
    # Language names mapping
    LANGUAGE_NAMES: Dict[str, str] = {
        'hi': 'Hindi',
        'ta': 'Tamil',
        'te': 'Telugu',
        'bn': 'Bengali',
        'mr': 'Marathi',
        'gu': 'Gujarati',
        'kn': 'Kannada',
        'ml': 'Malayalam',
        'pa': 'Punjabi',
        'or': 'Odia',
    }
    
    @classmethod
    def is_language_supported(cls, language_code: str) -> bool:
        """
        Check if a language is supported
        
        Args:
            language_code: ISO 639-1 language code
            
        Returns:
            True if language is supported, False otherwise
        """
        return language_code in cls.SUPPORTED_LANGUAGES
    
    @classmethod
    def get_language_name(cls, language_code: str) -> str:
        """
        Get the full name of a language from its code
        
        Args:
            language_code: ISO 639-1 language code
            
        Returns:
            Full language name or the code if not found
        """
        return cls.LANGUAGE_NAMES.get(language_code, language_code)
    
    @classmethod
    def validate_config(cls) -> bool:
        """
        Validate configuration settings
        
        Returns:
            True if configuration is valid, False otherwise
        """
        if not cls.ENDPOINT_NAME:
            return False
        
        if cls.TIMEOUT_SECONDS <= 0:
            return False
        
        if cls.MAX_RETRIES < 0:
            return False
        
        if not (0.0 <= cls.ASR_CONFIDENCE_THRESHOLD <= 1.0):
            return False
        
        if not (0.0 <= cls.VISION_CONFIDENCE_THRESHOLD <= 1.0):
            return False
        
        return True
