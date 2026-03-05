"""
ONDC Schema Mapper - Transforms ExtractedAttributes to Beckn protocol format

This module implements deterministic transformation rules to convert
ExtractedAttributes to ONDCCatalogItem (Beckn protocol).

Requirements: 8.1, 9.1
"""
import hashlib
from typing import Dict, List, Optional
from backend.models.catalog import (
    ExtractedAttributes,
    ONDCCatalogItem,
    ItemDescriptor,
    Price,
    CSI
)


# ONDC Category Taxonomy Mapping
CATEGORY_MAPPING = {
    # Textiles & Apparel
    'handloom saree': 'Fashion:Ethnic Wear:Sarees',
    'saree': 'Fashion:Ethnic Wear:Sarees',
    'silk saree': 'Fashion:Ethnic Wear:Sarees',
    'cotton saree': 'Fashion:Ethnic Wear:Sarees',
    'dupatta': 'Fashion:Ethnic Wear:Dupattas',
    'shawl': 'Fashion:Accessories:Shawls',
    'stole': 'Fashion:Accessories:Stoles',
    'kurta': 'Fashion:Ethnic Wear:Kurtas',
    'dhoti': 'Fashion:Ethnic Wear:Dhotis',
    
    # Handicrafts
    'pottery': 'Home & Decor:Handicrafts:Pottery',
    'ceramic': 'Home & Decor:Handicrafts:Pottery',
    'terracotta': 'Home & Decor:Handicrafts:Pottery',
    'clay pot': 'Home & Decor:Handicrafts:Pottery',
    'vase': 'Home & Decor:Handicrafts:Pottery',
    
    # Jewelry
    'jewelry': 'Fashion:Jewelry:Handcrafted',
    'jewellery': 'Fashion:Jewelry:Handcrafted',
    'necklace': 'Fashion:Jewelry:Necklaces',
    'earrings': 'Fashion:Jewelry:Earrings',
    'bracelet': 'Fashion:Jewelry:Bracelets',
    'bangle': 'Fashion:Jewelry:Bangles',
    'ring': 'Fashion:Jewelry:Rings',
    
    # Home Decor
    'wall hanging': 'Home & Decor:Wall Art:Hangings',
    'painting': 'Home & Decor:Wall Art:Paintings',
    'sculpture': 'Home & Decor:Handicrafts:Sculptures',
    'lamp': 'Home & Decor:Lighting:Lamps',
    'candle holder': 'Home & Decor:Lighting:Candle Holders',
    
    # Woodwork
    'wooden toy': 'Toys & Games:Traditional Toys:Wooden',
    'wooden box': 'Home & Decor:Storage:Wooden Boxes',
    'wooden furniture': 'Furniture:Handcrafted:Wooden',
    'carving': 'Home & Decor:Handicrafts:Wood Carvings',
    
    # Metalwork
    'brass': 'Home & Decor:Handicrafts:Brass',
    'copper': 'Home & Decor:Handicrafts:Copper',
    'bronze': 'Home & Decor:Handicrafts:Bronze',
    'metal craft': 'Home & Decor:Handicrafts:Metal',
    
    # Basketry & Weaving
    'basket': 'Home & Decor:Storage:Baskets',
    'mat': 'Home & Decor:Floor Coverings:Mats',
    'rug': 'Home & Decor:Floor Coverings:Rugs',
    'carpet': 'Home & Decor:Floor Coverings:Carpets',
    
    # Default fallback
    'handicraft': 'General:Handicrafts',
    'handmade': 'General:Handicrafts',
}


def map_to_beckn_item(
    extracted: ExtractedAttributes,
    image_urls: Optional[List[str]] = None
) -> ONDCCatalogItem:
    """
    Main transformation function to convert ExtractedAttributes to ONDCCatalogItem.
    
    Args:
        extracted: Extracted product attributes
        image_urls: List of processed image URLs (optional)
    
    Returns:
        ONDCCatalogItem: Beckn protocol compliant catalog item
    
    Requirements: 8.1, 9.1
    """
    # Generate deterministic item ID
    item_id = generate_item_id(extracted)
    
    # Build descriptor
    descriptor = ItemDescriptor(
        name=_truncate_name(extracted.short_description),
        short_desc=_truncate_short_desc(extracted.short_description),
        long_desc=build_long_description(extracted),
        images=image_urls or []
    )
    
    # Build price
    price = Price(
        currency=extracted.price.get('currency', 'INR') if extracted.price else 'INR',
        value=str(extracted.price.get('value', '0')) if extracted.price else '0'
    )
    
    # Map category
    category_id = map_category_to_ondc(extracted.category)
    
    # Build tags from attributes and CSIs
    tags = _build_tags(extracted)
    
    return ONDCCatalogItem(
        id=item_id,
        descriptor=descriptor,
        price=price,
        category_id=category_id,
        tags=tags
    )


def build_long_description(extracted: ExtractedAttributes) -> str:
    """
    Builds ONDC long description preserving cultural context and CSI terms.
    
    Args:
        extracted: Extracted product attributes
    
    Returns:
        str: Comprehensive description with cultural context
    
    Requirements: 8.1
    """
    parts = [extracted.long_description]
    
    # Add cultural significance section if CSIs exist
    if extracted.csis:
        csi_section = "\n\nCultural Significance:"
        for csi in extracted.csis:
            csi_section += f"\n• {csi.vernacular_term} ({csi.transliteration}): {csi.english_context}"
        parts.append(csi_section)
    
    # Add craft technique if available
    if extracted.craft_technique:
        parts.append(f"\n\nCraft Technique: {extracted.craft_technique}")
    
    # Add region of origin if available
    if extracted.region_of_origin:
        parts.append(f"Region of Origin: {extracted.region_of_origin}")
    
    return "\n".join(parts)


def map_category_to_ondc(category: str) -> str:
    """
    Maps extracted category to ONDC standard category taxonomy.
    
    Args:
        category: Extracted product category
    
    Returns:
        str: ONDC taxonomy category ID
    
    Requirements: 8.1
    """
    if not category:
        return 'General:Handicrafts'
    
    # Normalize category for lookup
    normalized = category.lower().strip()
    
    # Direct lookup
    if normalized in CATEGORY_MAPPING:
        return CATEGORY_MAPPING[normalized]
    
    # Partial match - check if any key is contained in the category
    for key, value in CATEGORY_MAPPING.items():
        if key in normalized or normalized in key:
            return value
    
    # Default fallback
    return 'General:Handicrafts'


def generate_item_id(extracted: ExtractedAttributes) -> str:
    """
    Generates deterministic item ID using hash of core attributes.
    
    This ensures the same product gets the same ID for idempotency.
    
    Args:
        extracted: Extracted product attributes
    
    Returns:
        str: Deterministic item ID
    
    Requirements: 9.1
    """
    # Build ID components from core attributes
    id_components = [
        extracted.category or '',
        extracted.subcategory or '',
        ','.join(sorted(extracted.material)) if extracted.material else '',
        ','.join(sorted(extracted.colors)) if extracted.colors else '',
        str(extracted.price.get('value', '')) if extracted.price else ''
    ]
    
    # Create hash input
    hash_input = '|'.join(id_components)
    
    # Generate SHA-256 hash and take first 16 characters
    item_hash = hashlib.sha256(hash_input.encode('utf-8')).hexdigest()[:16]
    
    return f"item_{item_hash}"


def _truncate_name(text: str, max_length: int = 100) -> str:
    """Truncate name to max length for Beckn protocol compliance."""
    if not text:
        return "Handcrafted Product"
    
    if len(text) <= max_length:
        return text
    
    # Truncate at word boundary, accounting for the '...' suffix
    truncated = text[:max_length-3].rsplit(' ', 1)[0]
    return truncated + '...'


def _truncate_short_desc(text: str, max_length: int = 500) -> str:
    """Truncate short description to max length for Beckn protocol compliance."""
    if not text:
        return "Handcrafted artisan product"
    
    if len(text) <= max_length:
        return text
    
    # Truncate at word boundary, accounting for the '...' suffix
    truncated = text[:max_length-3].rsplit(' ', 1)[0]
    return truncated + '...'


def _build_tags(extracted: ExtractedAttributes) -> Dict[str, str]:
    """
    Build tags dictionary from extracted attributes and CSIs.
    
    Args:
        extracted: Extracted product attributes
    
    Returns:
        Dict[str, str]: Tags for ONDC catalog item
    """
    tags = {}
    
    # Add material tags
    if extracted.material:
        tags['material'] = ','.join(extracted.material)
    
    # Add color tags
    if extracted.colors:
        tags['color'] = ','.join(extracted.colors)
    
    # Add craft technique
    if extracted.craft_technique:
        tags['craft_technique'] = extracted.craft_technique
    
    # Add region
    if extracted.region_of_origin:
        tags['region'] = extracted.region_of_origin
    
    # Add dimensions if available
    if extracted.dimensions:
        if 'length' in extracted.dimensions:
            tags['length'] = f"{extracted.dimensions['length']} {extracted.dimensions.get('unit', 'cm')}"
        if 'width' in extracted.dimensions:
            tags['width'] = f"{extracted.dimensions['width']} {extracted.dimensions.get('unit', 'cm')}"
        if 'height' in extracted.dimensions:
            tags['height'] = f"{extracted.dimensions['height']} {extracted.dimensions.get('unit', 'cm')}"
    
    # Add weight if available
    if extracted.weight:
        tags['weight'] = f"{extracted.weight.get('value', '')} {extracted.weight.get('unit', 'g')}"
    
    # Add CSI terms as tags
    if extracted.csis:
        for i, csi in enumerate(extracted.csis):
            tags[f'csi_{i+1}_term'] = csi.vernacular_term
            tags[f'csi_{i+1}_transliteration'] = csi.transliteration
            tags[f'csi_{i+1}_context'] = csi.english_context
    
    return tags
