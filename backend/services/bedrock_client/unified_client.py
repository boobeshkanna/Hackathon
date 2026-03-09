"""
Unified Bedrock Client with third-party AI fallback
"""
import json
import logging
from typing import Dict, Any, Optional, List
from models import ExtractedAttributes, CSI
from services.ai_client import UnifiedAIClient, AIProvider

logger = logging.getLogger(__name__)


class UnifiedBedrockClient:
    """
    Bedrock-compatible client with automatic fallback to third-party AI providers
    """
    
    def __init__(self, preferred_provider: Optional[AIProvider] = None):
        """
        Initialize unified client
        
        Args:
            preferred_provider: Preferred AI provider (auto-detect if None)
        """
        self.client = UnifiedAIClient(
            preferred_provider=preferred_provider,
            fallback_enabled=True
        )
        logger.info(f"Initialized UnifiedBedrockClient with providers: {self.client.get_available_providers()}")
    
    def extract_attributes(
        self,
        transcription: str,
        vision_data: Dict[str, Any],
        language: str = 'hi'
    ) -> ExtractedAttributes:
        """Extract structured attributes from multimodal input"""
        prompt = self._build_attribute_extraction_prompt(transcription, vision_data, language)
        
        try:
            response = self.client.generate_text(prompt, max_tokens=3000, temperature=0.3)
            attributes = self._parse_attributes_response(response)
            logger.info(f"Extracted attributes for category: {attributes.category}")
            return attributes
        except Exception as e:
            logger.error(f"Error extracting attributes: {e}")
            raise
    
    def identify_csi_terms(self, transcription: str, language: str = 'hi') -> List[CSI]:
        """Identify Cultural Specific Items (CSI) from vernacular transcription"""
        prompt = self._build_csi_identification_prompt(transcription, language)
        
        try:
            response = self.client.generate_text(prompt, max_tokens=2000, temperature=0.3)
            csi_list = self._parse_csi_response(response)
            logger.info(f"Identified {len(csi_list)} CSI terms")
            return csi_list
        except Exception as e:
            logger.error(f"Error identifying CSI terms: {e}")
            return []
    
    def transcreate_description(
        self,
        vernacular_text: str,
        extracted_attrs: ExtractedAttributes,
        language: str = 'hi'
    ) -> Dict[str, str]:
        """Transcreate vernacular description to SEO-friendly English"""
        prompt = self._build_transcreation_prompt(vernacular_text, extracted_attrs, language)
        
        try:
            response = self.client.generate_text(prompt, max_tokens=2000, temperature=0.5)
            descriptions = self._parse_transcreation_response(response)
            logger.info("Transcreation completed successfully")
            return descriptions
        except Exception as e:
            logger.error(f"Error transcreating description: {e}")
            raise
    
    def _build_attribute_extraction_prompt(
        self,
        transcription: str,
        vision_data: Dict[str, Any],
        language: str
    ) -> str:
        """Build prompt for comprehensive attribute extraction"""
        return f"""You are an expert at extracting structured product attributes from multimodal artisan product descriptions.

LANGUAGE: {language}

VOICE TRANSCRIPTION (AUTHORITATIVE - THIS IS THE PRIMARY SOURCE):
{transcription}

VISION ANALYSIS (SECONDARY - Use only if voice doesn't provide info):
{json.dumps(vision_data, indent=2)}

TASK: Extract comprehensive product attributes following these rules:

1. CONFLICT RESOLUTION: If voice and vision disagree, ALWAYS prioritize voice transcription
2. PRICE EXTRACTION: Look for ANY numbers in transcription - convert vernacular numbers to digits
   - Hindi: पांच हजार = 5000, दो सौ = 200, तीन हजार = 3000
   - Look for: रुपये, ₹, rupees, INR
3. DIMENSIONS: Extract length, width, height if mentioned
   - Look for: मीटर (meters), सेंटीमीटर (cm), इंच (inches)
4. WEIGHT: Extract if mentioned (किलो, ग्राम, kg, grams)
5. CULTURAL PRESERVATION: Identify and preserve culturally significant terms
6. CONFIDENCE SCORING: Provide confidence (0.0-1.0) for each extracted attribute

VERNACULAR NUMBER CONVERSION (Hindi):
- एक=1, दो=2, तीन=3, चार=4, पांच=5, छह=6, सात=7, आठ=8, नौ=9, दस=10
- बीस=20, तीस=30, चालीस=40, पचास=50, साठ=60, सत्तर=70, अस्सी=80, नब्बे=90
- सौ=100, हजार=1000, लाख=100000

OUTPUT FORMAT (JSON):
{{
  "category": "string",
  "subcategory": "string or null",
  "material": ["list of materials from voice or vision"],
  "colors": ["list of colors from voice or vision"],
  "dimensions": {{
    "length": {{"value": number, "unit": "meters/cm/inches"}},
    "width": {{"value": number, "unit": "meters/cm/inches"}},
    "height": {{"value": number, "unit": "meters/cm/inches"}}
  }} or null,
  "weight": {{"value": number, "unit": "kg/grams"}} or null,
  "price": {{
    "value": EXTRACT_NUMBER_FROM_VOICE,
    "currency": "INR",
    "display": "₹5,000"
  }} or null,
  "short_description": "1-2 sentence description",
  "long_description": "Detailed description with cultural context",
  "craft_technique": "string or null",
  "region_of_origin": "string or null",
  "special_features": ["handmade", "traditional", "custom"],
  "confidence_scores": {{
    "category": 0.0-1.0,
    "material": 0.0-1.0,
    "colors": 0.0-1.0,
    "price": 0.0-1.0,
    "dimensions": 0.0-1.0
  }}
}}

CRITICAL: If transcription mentions ANY number, extract it as price. Don't leave price null if numbers are present!

Extract attributes now:"""
    
    def _build_csi_identification_prompt(self, transcription: str, language: str) -> str:
        """Build prompt for CSI identification"""
        return f"""You are an expert in Indian traditional crafts and cultural heritage.

LANGUAGE: {language}
TRANSCRIPTION: {transcription}

TASK: Identify Cultural Specific Items (CSI) - terms that carry cultural significance.

CSI CATEGORIES:
1. Traditional craft techniques
2. Regional product names
3. Cultural materials
4. Traditional patterns/designs
5. Cultural significance markers

OUTPUT FORMAT (JSON array):
[
  {{
    "vernacular_term": "original term",
    "transliteration": "roman script",
    "english_context": "brief explanation",
    "cultural_significance": "why this matters"
  }}
]

If no CSI terms found, return empty array [].

Identify CSI terms now:"""
    
    def _build_transcreation_prompt(
        self,
        vernacular_text: str,
        extracted_attrs: ExtractedAttributes,
        language: str
    ) -> str:
        """Build prompt for cultural transcreation"""
        csi_context = ""
        if extracted_attrs.csis:
            csi_context = "\n\nCULTURAL TERMS TO PRESERVE:\n"
            for csi in extracted_attrs.csis:
                csi_context += f"- {csi.vernacular_term} ({csi.transliteration}): {csi.english_context}\n"
        
        return f"""You are an expert at transcreation - culturally adapting content while preserving meaning.

LANGUAGE: {language}
VERNACULAR TEXT: {vernacular_text}

EXTRACTED ATTRIBUTES:
- Category: {extracted_attrs.category}
- Materials: {', '.join(extracted_attrs.material)}
- Colors: {', '.join(extracted_attrs.colors)}
{csi_context}

TASK: Create SEO-friendly English descriptions that preserve cultural terms.

OUTPUT FORMAT (JSON):
{{
  "short_description": "1-2 sentences, max 100 chars, SEO-optimized",
  "long_description": "Detailed description with cultural context"
}}

Generate transcreated descriptions now:"""
    
    def _parse_attributes_response(self, response: str) -> ExtractedAttributes:
        """Parse AI response into ExtractedAttributes"""
        try:
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            json_str = response[start_idx:end_idx]
            data = json.loads(json_str)
            
            return ExtractedAttributes(
                category=data.get('category', 'Unknown'),
                subcategory=data.get('subcategory'),
                material=data.get('material', []),
                colors=data.get('colors', []),
                dimensions=data.get('dimensions'),
                weight=data.get('weight'),
                price=data.get('price'),
                short_description=data.get('short_description', ''),
                long_description=data.get('long_description', ''),
                csis=[],
                craft_technique=data.get('craft_technique'),
                region_of_origin=data.get('region_of_origin'),
                confidence_scores=data.get('confidence_scores', {})
            )
        except Exception as e:
            logger.error(f"Error parsing attributes: {e}")
            return ExtractedAttributes(
                category='Unknown',
                short_description='Product description unavailable',
                long_description='Product description unavailable',
                confidence_scores={'category': 0.0}
            )
    
    def _parse_csi_response(self, response: str) -> List[CSI]:
        """Parse AI response into list of CSI objects"""
        try:
            start_idx = response.find('[')
            end_idx = response.rfind(']') + 1
            json_str = response[start_idx:end_idx]
            data = json.loads(json_str)
            
            return [
                CSI(
                    vernacular_term=item.get('vernacular_term', ''),
                    transliteration=item.get('transliteration', ''),
                    english_context=item.get('english_context', ''),
                    cultural_significance=item.get('cultural_significance', '')
                )
                for item in data
            ]
        except Exception as e:
            logger.error(f"Error parsing CSI response: {e}")
            return []
    
    def _parse_transcreation_response(self, response: str) -> Dict[str, str]:
        """Parse AI response into transcreated descriptions"""
        try:
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            json_str = response[start_idx:end_idx]
            data = json.loads(json_str)
            
            return {
                'short_description': data.get('short_description', ''),
                'long_description': data.get('long_description', '')
            }
        except Exception as e:
            logger.error(f"Error parsing transcreation: {e}")
            return {
                'short_description': 'Product description unavailable',
                'long_description': 'Product description unavailable'
            }
