"""
Data Minimization and Privacy Module

Implements data minimization and privacy requirements:
- Removes location data and device identifiers from requests (Requirement 12.1)
- Filters PII from voice transcriptions (Requirement 12.2)
"""
import re
from typing import Dict, Any, List
from aws_lambda_powertools import Logger

logger = Logger()

# PII patterns to filter from transcriptions
PII_PATTERNS = [
    # Phone numbers (Indian format)
    (r'\b\d{10}\b', '[PHONE_NUMBER]'),
    (r'\b\+91[\s-]?\d{10}\b', '[PHONE_NUMBER]'),
    (r'\b\d{5}[\s-]?\d{5}\b', '[PHONE_NUMBER]'),
    
    # Email addresses
    (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]'),
    
    # Aadhaar numbers (12 digits)
    (r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', '[ID_NUMBER]'),
    
    # PAN card (ABCDE1234F format)
    (r'\b[A-Z]{5}\d{4}[A-Z]\b', '[ID_NUMBER]'),
    
    # Bank account numbers (9-18 digits)
    (r'\b\d{9,18}\b', '[ACCOUNT_NUMBER]'),
    
    # URLs
    (r'https?://[^\s]+', '[URL]'),
    
    # IP addresses
    (r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '[IP_ADDRESS]'),
]

# Request headers/fields to remove for data minimization
SENSITIVE_HEADERS = [
    'x-forwarded-for',
    'x-real-ip',
    'cf-connecting-ip',
    'true-client-ip',
    'x-client-ip',
    'x-cluster-client-ip',
    'forwarded',
    'via',
    'user-agent',
    'x-device-id',
    'x-device-fingerprint',
    'x-imei',
    'x-android-id',
    'x-advertising-id',
    'x-idfa',
]

SENSITIVE_FIELDS = [
    'location',
    'latitude',
    'longitude',
    'gps_coordinates',
    'device_id',
    'device_fingerprint',
    'imei',
    'android_id',
    'advertising_id',
    'idfa',
    'mac_address',
    'ip_address',
]


def sanitize_request_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """
    Remove sensitive headers from API Gateway request
    
    Args:
        headers: Request headers dictionary
        
    Returns:
        Sanitized headers dictionary
    """
    if not headers:
        return {}
    
    sanitized = {}
    removed_count = 0
    
    for key, value in headers.items():
        if key.lower() not in SENSITIVE_HEADERS:
            sanitized[key] = value
        else:
            removed_count += 1
            logger.debug(f"Removed sensitive header: {key}")
    
    if removed_count > 0:
        logger.info(f"Removed {removed_count} sensitive headers for data minimization")
    
    return sanitized


def sanitize_request_body(body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove sensitive fields from request body
    
    Args:
        body: Request body dictionary
        
    Returns:
        Sanitized body dictionary
    """
    if not body:
        return {}
    
    sanitized = body.copy()
    removed_fields = []
    
    for field in SENSITIVE_FIELDS:
        if field in sanitized:
            del sanitized[field]
            removed_fields.append(field)
    
    if removed_fields:
        logger.info(f"Removed sensitive fields: {', '.join(removed_fields)}")
    
    return sanitized


def filter_pii_from_text(text: str) -> str:
    """
    Filter PII from transcribed text using pattern matching
    
    Args:
        text: Original transcribed text
        
    Returns:
        Text with PII replaced by placeholders
    """
    if not text:
        return text
    
    filtered_text = text
    replacements_made = 0
    
    for pattern, replacement in PII_PATTERNS:
        matches = re.findall(pattern, filtered_text)
        if matches:
            filtered_text = re.sub(pattern, replacement, filtered_text)
            replacements_made += len(matches)
            logger.debug(f"Filtered {len(matches)} instances of pattern: {pattern}")
    
    if replacements_made > 0:
        logger.info(f"Filtered {replacements_made} PII instances from transcription")
    
    return filtered_text


def extract_product_info_only(transcription: str) -> str:
    """
    Extract only product-related information from transcription
    
    This function uses heuristics to identify and extract product-related
    content while discarding personal conversations.
    
    Args:
        transcription: Full transcription text
        
    Returns:
        Product-related content only
    """
    # First, filter PII
    filtered = filter_pii_from_text(transcription)
    
    # Product-related keywords (can be expanded)
    product_keywords = [
        # Hindi
        'साड़ी', 'कपड़ा', 'रंग', 'कीमत', 'बनाया', 'हाथ', 'बुना',
        # English
        'saree', 'fabric', 'color', 'price', 'made', 'hand', 'woven',
        'material', 'size', 'weight', 'craft', 'design', 'pattern',
        # Tamil
        'புடவை', 'துணி', 'நிறம்', 'விலை',
        # Telugu
        'చీర', 'వస్త్రం', 'రంగు', 'ధర',
    ]
    
    # For now, return filtered text
    # In production, this would use NLP to extract product-specific sentences
    # TODO: Implement ML-based product content extraction
    
    return filtered


def create_bedrock_pii_filtering_prompt(transcription: str) -> str:
    """
    Create a Bedrock prompt that instructs the model to filter PII
    and extract only product information
    
    Args:
        transcription: Original transcription
        
    Returns:
        Prompt for Bedrock model
    """
    prompt = f"""You are processing a voice description of a handcrafted product from a rural artisan in India.

Your task is to extract ONLY product-related information and remove any personal information.

DO NOT include:
- Phone numbers
- Email addresses
- Personal names (unless they are part of the product name or craft tradition)
- Addresses
- ID numbers
- Bank details
- Any personal conversations

DO include:
- Product name and type
- Materials used
- Colors and patterns
- Dimensions and weight
- Craftsmanship techniques
- Cultural significance
- Price
- Region of origin (general region only, not specific address)

Original transcription:
{transcription}

Extract only product information:"""
    
    return prompt


def validate_no_pii_in_output(text: str) -> bool:
    """
    Validate that output text does not contain obvious PII
    
    Args:
        text: Text to validate
        
    Returns:
        True if no PII detected, False otherwise
    """
    for pattern, _ in PII_PATTERNS:
        if re.search(pattern, text):
            logger.warning(f"PII pattern detected in output: {pattern}")
            return False
    
    return True


def log_data_minimization_metrics(
    headers_removed: int,
    fields_removed: int,
    pii_filtered: int
) -> None:
    """
    Log data minimization metrics for monitoring
    
    Args:
        headers_removed: Number of sensitive headers removed
        fields_removed: Number of sensitive fields removed
        pii_filtered: Number of PII instances filtered
    """
    logger.info(
        "Data minimization applied",
        extra={
            "headers_removed": headers_removed,
            "fields_removed": fields_removed,
            "pii_filtered": pii_filtered,
        }
    )
