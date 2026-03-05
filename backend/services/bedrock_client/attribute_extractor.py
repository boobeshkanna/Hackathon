"""
Attribute extraction service with voice priority resolution
"""
import logging
from typing import Dict, Any, List, Optional
from backend.models import ExtractedAttributes, CSI
from backend.services.bedrock_client.client import BedrockClient

logger = logging.getLogger(__name__)


class AttributeExtractor:
    """Service for extracting and resolving product attributes from multimodal input"""
    
    def __init__(self, bedrock_client: Optional[BedrockClient] = None):
        """
        Initialize attribute extractor
        
        Args:
            bedrock_client: Optional BedrockClient instance (creates new if not provided)
        """
        self.bedrock_client = bedrock_client or BedrockClient()
    
    def extract_attributes_with_priority(
        self,
        asr_result: Dict[str, Any],
        vision_result: Dict[str, Any],
        language: str = 'hi'
    ) -> ExtractedAttributes:
        """
        Extract attributes from combined ASR and Vision results with voice priority
        
        Args:
            asr_result: ASR transcription result with confidence
            vision_result: Vision analysis result
            language: Source language code
            
        Returns:
            ExtractedAttributes with resolved conflicts (voice priority)
        """
        transcription = asr_result.get('transcription', '')
        
        # Step 1: Extract attributes using Bedrock LLM
        logger.info("Extracting attributes from multimodal input")
        attributes = self.bedrock_client.extract_attributes(
            transcription=transcription,
            vision_data=vision_result,
            language=language
        )
        
        # Step 2: Identify CSI terms from vernacular transcription
        logger.info("Identifying CSI terms")
        csi_terms = self.bedrock_client.identify_csi_terms(
            transcription=transcription,
            language=language
        )
        attributes.csis = csi_terms
        
        # Step 3: Apply voice priority resolution for conflicts
        logger.info("Applying voice priority resolution")
        attributes = self._resolve_conflicts_with_voice_priority(
            attributes=attributes,
            asr_result=asr_result,
            vision_result=vision_result
        )
        
        # Step 4: Normalize price if present
        if attributes.price:
            attributes.price = self._normalize_price(attributes.price)
        
        # Step 5: Generate confidence scores
        attributes.confidence_scores = self._generate_confidence_scores(
            attributes=attributes,
            asr_confidence=asr_result.get('confidence', 0.0),
            vision_confidence=vision_result.get('confidence', 0.0)
        )
        
        logger.info(f"Attribute extraction complete for category: {attributes.category}")
        return attributes
    
    def _resolve_conflicts_with_voice_priority(
        self,
        attributes: ExtractedAttributes,
        asr_result: Dict[str, Any],
        vision_result: Dict[str, Any]
    ) -> ExtractedAttributes:
        """
        Resolve conflicts between voice and vision data, prioritizing voice
        
        Voice transcription is authoritative - if voice mentions an attribute,
        it overrides vision analysis.
        
        Args:
            attributes: Extracted attributes from LLM
            asr_result: ASR result with transcription
            vision_result: Vision analysis result
            
        Returns:
            Attributes with conflicts resolved
        """
        transcription = asr_result.get('transcription', '').lower()
        
        # If voice mentions category explicitly, trust it over vision
        if attributes.category and attributes.category != 'Unknown':
            logger.debug(f"Voice category '{attributes.category}' takes priority")
        elif vision_result.get('category'):
            # Fallback to vision if voice didn't provide category
            attributes.category = vision_result['category']
            logger.debug(f"Using vision category '{attributes.category}' as fallback")
        
        # Voice colors override vision colors if mentioned
        if not attributes.colors and vision_result.get('colors'):
            attributes.colors = vision_result['colors']
            logger.debug(f"Using vision colors as fallback: {attributes.colors}")
        
        # Voice materials override vision materials if mentioned
        if not attributes.material and vision_result.get('materials'):
            attributes.material = vision_result['materials']
            logger.debug(f"Using vision materials as fallback: {attributes.material}")
        
        return attributes
    
    def _normalize_price(self, price: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize price to standard format
        
        Args:
            price: Price dict with value and currency
            
        Returns:
            Normalized price dict
        """
        try:
            # Ensure value is numeric
            value = float(price.get('value', 0))
            currency = price.get('currency', 'INR').upper()
            
            # Normalize common currency variations
            currency_map = {
                'RS': 'INR',
                'RUPEES': 'INR',
                'RUPEE': 'INR',
                '₹': 'INR',
                'INR': 'INR'
            }
            
            normalized_currency = currency_map.get(currency, currency)
            
            return {
                'value': value,
                'currency': normalized_currency
            }
        except (ValueError, TypeError) as e:
            logger.warning(f"Error normalizing price: {e}")
            return price
    
    def _generate_confidence_scores(
        self,
        attributes: ExtractedAttributes,
        asr_confidence: float,
        vision_confidence: float
    ) -> Dict[str, float]:
        """
        Generate confidence scores for each extracted attribute
        
        Args:
            attributes: Extracted attributes
            asr_confidence: ASR transcription confidence
            vision_confidence: Vision analysis confidence
            
        Returns:
            Dict mapping attribute names to confidence scores
        """
        scores = attributes.confidence_scores or {}
        
        # Category confidence (higher if from voice)
        if 'category' not in scores:
            scores['category'] = asr_confidence if attributes.category else vision_confidence
        
        # Material confidence (voice priority)
        if 'material' not in scores:
            scores['material'] = asr_confidence if attributes.material else vision_confidence
        
        # Color confidence (voice priority)
        if 'colors' not in scores:
            scores['colors'] = asr_confidence if attributes.colors else vision_confidence
        
        # Price confidence (only from voice)
        if 'price' not in scores and attributes.price:
            scores['price'] = asr_confidence
        
        # Dimensions confidence (only from voice typically)
        if 'dimensions' not in scores and attributes.dimensions:
            scores['dimensions'] = asr_confidence
        
        # Weight confidence (only from voice typically)
        if 'weight' not in scores and attributes.weight:
            scores['weight'] = asr_confidence
        
        # Craft technique confidence (only from voice)
        if 'craft_technique' not in scores and attributes.craft_technique:
            scores['craft_technique'] = asr_confidence
        
        # Region confidence (only from voice)
        if 'region_of_origin' not in scores and attributes.region_of_origin:
            scores['region_of_origin'] = asr_confidence
        
        return scores
    
    def extract_price_from_text(self, text: str, language: str = 'hi') -> Optional[Dict[str, Any]]:
        """
        Extract and normalize price from text
        
        Args:
            text: Text containing price information
            language: Language code
            
        Returns:
            Normalized price dict or None
        """
        import re
        
        # Common price patterns for Indian languages
        patterns = [
            r'(\d+)\s*(?:रुपये|रुपए|rupees?|rs\.?|₹)',  # Hindi/English
            r'(?:रुपये|रुपए|rupees?|rs\.?|₹)\s*(\d+)',
            r'(\d+)\s*(?:టక|రూపాయలు)',  # Telugu
            r'(\d+)\s*(?:ரூபாய்)',  # Tamil
        ]
        
        text_lower = text.lower()
        
        for pattern in patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                try:
                    value = float(match.group(1))
                    return self._normalize_price({'value': value, 'currency': 'INR'})
                except (ValueError, IndexError):
                    continue
        
        return None
