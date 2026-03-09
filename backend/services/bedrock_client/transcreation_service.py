"""
Transcreation service for cultural preservation and SEO-friendly descriptions
"""
import logging
from typing import Dict, Any, Optional
from models import ExtractedAttributes, ONDCCatalogItem, ItemDescriptor, Price
from services.bedrock_client.client import BedrockClient

logger = logging.getLogger(__name__)


class TranscreationService:
    """Service for transcreating vernacular descriptions with cultural preservation"""
    
    def __init__(self, bedrock_client: Optional[BedrockClient] = None):
        """
        Initialize transcreation service
        
        Args:
            bedrock_client: Optional BedrockClient instance
        """
        self.bedrock_client = bedrock_client or BedrockClient()
    
    def transcreate_with_cultural_preservation(
        self,
        vernacular_text: str,
        extracted_attrs: ExtractedAttributes,
        language: str = 'hi'
    ) -> ExtractedAttributes:
        """
        Transcreate vernacular description to SEO-friendly English while preserving culture
        
        Args:
            vernacular_text: Original vernacular description
            extracted_attrs: Extracted attributes with CSI terms
            language: Source language code
            
        Returns:
            ExtractedAttributes with transcreated descriptions
        """
        logger.info("Starting transcreation with cultural preservation")
        
        # Generate transcreated descriptions
        descriptions = self.bedrock_client.transcreate_description(
            vernacular_text=vernacular_text,
            extracted_attrs=extracted_attrs,
            language=language
        )
        
        # Update attributes with transcreated descriptions
        extracted_attrs.short_description = descriptions['short_description']
        extracted_attrs.long_description = self._enhance_long_description(
            base_description=descriptions['long_description'],
            extracted_attrs=extracted_attrs
        )
        
        logger.info("Transcreation completed successfully")
        return extracted_attrs
    
    def _enhance_long_description(
        self,
        base_description: str,
        extracted_attrs: ExtractedAttributes
    ) -> str:
        """
        Enhance long description with CSI context, craft technique, and region
        
        Args:
            base_description: Base transcreated description
            extracted_attrs: Extracted attributes
            
        Returns:
            Enhanced long description
        """
        parts = [base_description]
        
        # Add CSI section if present
        if extracted_attrs.csis:
            csi_section = "\n\nCultural Significance:"
            for csi in extracted_attrs.csis:
                csi_section += f"\n• {csi.vernacular_term} ({csi.transliteration}): {csi.english_context}"
            parts.append(csi_section)
        
        # Add craft technique if present
        if extracted_attrs.craft_technique:
            parts.append(f"\n\nCraft Technique: {extracted_attrs.craft_technique}")
        
        # Add region of origin if present
        if extracted_attrs.region_of_origin:
            parts.append(f"\nRegion of Origin: {extracted_attrs.region_of_origin}")
        
        return "".join(parts)
    
    def format_as_beckn_item(
        self,
        extracted_attrs: ExtractedAttributes,
        image_urls: list[str],
        item_id: Optional[str] = None
    ) -> ONDCCatalogItem:
        """
        Format extracted attributes as Beckn-compatible ONDC catalog item
        
        Args:
            extracted_attrs: Extracted and transcreated attributes
            image_urls: List of product image URLs
            item_id: Optional item ID (generated if not provided)
            
        Returns:
            ONDCCatalogItem in Beckn protocol format
        """
        logger.info("Formatting as Beckn-compatible catalog item")
        
        # Generate item ID if not provided
        if not item_id:
            item_id = self._generate_item_id(extracted_attrs)
        
        # Create item descriptor
        descriptor = ItemDescriptor(
            name=self._truncate_text(extracted_attrs.short_description, 100),
            short_desc=self._truncate_text(extracted_attrs.short_description, 500),
            long_desc=extracted_attrs.long_description,
            images=image_urls
        )
        
        # Create price
        price = None
        if extracted_attrs.price:
            price = Price(
                currency=extracted_attrs.price.get('currency', 'INR'),
                value=str(extracted_attrs.price.get('value', 0))
            )
        else:
            # Default price if not extracted
            price = Price(currency='INR', value='0')
        
        # Map category to ONDC taxonomy
        category_id = self._map_category_to_ondc(extracted_attrs.category)
        
        # Build tags with all attributes
        tags = self._build_tags(extracted_attrs)
        
        # Create ONDC catalog item
        catalog_item = ONDCCatalogItem(
            id=item_id,
            descriptor=descriptor,
            price=price,
            category_id=category_id,
            tags=tags
        )
        
        logger.info(f"Beckn item created with ID: {item_id}")
        return catalog_item
    
    def _generate_item_id(self, extracted_attrs: ExtractedAttributes) -> str:
        """
        Generate deterministic item ID from attributes
        
        Args:
            extracted_attrs: Extracted attributes
            
        Returns:
            Unique item ID
        """
        import hashlib
        
        # Use hash of core attributes for deterministic ID
        id_components = [
            extracted_attrs.category or 'unknown',
            extracted_attrs.subcategory or '',
            ','.join(sorted(extracted_attrs.material)),
            ','.join(sorted(extracted_attrs.colors)),
        ]
        
        if extracted_attrs.price:
            id_components.append(str(extracted_attrs.price.get('value', 0)))
        
        hash_input = '|'.join(id_components)
        item_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:16]
        
        return f"item_{item_hash}"
    
    def _map_category_to_ondc(self, category: str) -> str:
        """
        Map extracted category to ONDC standard category taxonomy
        
        Args:
            category: Extracted category
            
        Returns:
            ONDC category ID
        """
        # Comprehensive category mapping
        category_mapping = {
            # Textiles & Apparel
            'handloom saree': 'Fashion:Ethnic Wear:Sarees',
            'saree': 'Fashion:Ethnic Wear:Sarees',
            'silk saree': 'Fashion:Ethnic Wear:Sarees',
            'cotton saree': 'Fashion:Ethnic Wear:Sarees',
            'dupatta': 'Fashion:Ethnic Wear:Dupattas',
            'stole': 'Fashion:Accessories:Stoles',
            'shawl': 'Fashion:Accessories:Shawls',
            
            # Jewelry
            'jewelry': 'Fashion:Jewelry:Handcrafted',
            'necklace': 'Fashion:Jewelry:Necklaces',
            'earrings': 'Fashion:Jewelry:Earrings',
            'bracelet': 'Fashion:Jewelry:Bracelets',
            'bangle': 'Fashion:Jewelry:Bangles',
            
            # Home & Decor
            'pottery': 'Home & Decor:Handicrafts:Pottery',
            'ceramic': 'Home & Decor:Handicrafts:Ceramics',
            'wall hanging': 'Home & Decor:Wall Art:Hangings',
            'painting': 'Home & Decor:Wall Art:Paintings',
            'sculpture': 'Home & Decor:Handicrafts:Sculptures',
            
            # Bags & Accessories
            'bag': 'Fashion:Bags:Handcrafted',
            'purse': 'Fashion:Bags:Purses',
            'clutch': 'Fashion:Bags:Clutches',
            
            # Default
            'unknown': 'General:Handicrafts',
        }
        
        category_lower = category.lower() if category else 'unknown'
        return category_mapping.get(category_lower, 'General:Handicrafts')
    
    def _build_tags(self, extracted_attrs: ExtractedAttributes) -> Dict[str, Any]:
        """
        Build tags dict from extracted attributes
        
        Args:
            extracted_attrs: Extracted attributes
            
        Returns:
            Tags dict for ONDC item
        """
        tags = {}
        
        # Add material tags
        if extracted_attrs.material:
            tags['material'] = ','.join(extracted_attrs.material)
        
        # Add color tags
        if extracted_attrs.colors:
            tags['color'] = ','.join(extracted_attrs.colors)
        
        # Add craft technique
        if extracted_attrs.craft_technique:
            tags['craft_technique'] = extracted_attrs.craft_technique
        
        # Add region
        if extracted_attrs.region_of_origin:
            tags['region'] = extracted_attrs.region_of_origin
        
        # Add CSI terms as tags
        if extracted_attrs.csis:
            csi_terms = [csi.transliteration for csi in extracted_attrs.csis]
            tags['cultural_terms'] = ','.join(csi_terms)
        
        # Add dimensions if present
        if extracted_attrs.dimensions:
            dims = extracted_attrs.dimensions
            if 'length' in dims and 'width' in dims:
                tags['dimensions'] = f"{dims['length']}x{dims['width']}{dims.get('unit', 'cm')}"
        
        # Add weight if present
        if extracted_attrs.weight:
            weight = extracted_attrs.weight
            tags['weight'] = f"{weight['value']}{weight.get('unit', 'g')}"
        
        return tags
    
    def _truncate_text(self, text: str, max_length: int) -> str:
        """
        Truncate text to max length, preserving word boundaries
        
        Args:
            text: Text to truncate
            max_length: Maximum length
            
        Returns:
            Truncated text
        """
        if len(text) <= max_length:
            return text
        
        # Truncate at word boundary
        truncated = text[:max_length].rsplit(' ', 1)[0]
        return truncated + '...'
