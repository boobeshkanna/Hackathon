"""
Unified Catalog Generator with third-party AI support (Groq)

Replaces Bedrock-based catalog generation with Groq or other AI providers.
"""
import json
import logging
from typing import Dict, Any, Optional
from services.ai_client import UnifiedAIClient, AIProvider

logger = logging.getLogger(__name__)


class UnifiedCatalogGenerator:
    """Catalog generation using Groq or other AI providers (replacing Bedrock)"""
    
    def __init__(self, preferred_provider: Optional[AIProvider] = None):
        """
        Initialize unified catalog generator
        
        Args:
            preferred_provider: Preferred AI provider (defaults to Groq)
        """
        self.client = UnifiedAIClient(
            preferred_provider=preferred_provider or AIProvider.GROQ,
            fallback_enabled=True
        )
        logger.info(f"Initialized UnifiedCatalogGenerator with providers: {self.client.get_available_providers()}")
        
    def generate_catalog_entry(
        self,
        vision_analysis: Dict[str, Any],
        transcription: Dict[str, Any],
        artisan_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate ONDC catalog entry from vision and transcription data
        
        Args:
            vision_analysis: Vision analysis results
            transcription: Audio transcription results
            artisan_info: Optional artisan information
            
        Returns:
            Dict containing ONDC-compliant catalog entry
        """
        # Build prompt with all available data
        prompt = self._build_catalog_prompt(vision_analysis, transcription, artisan_info)
        
        try:
            logger.info("Generating catalog entry using Groq")
            
            response_text = self.client.generate_text(
                prompt=prompt,
                max_tokens=1500,
                temperature=0.5
            )
            
            # Parse structured response
            result = self._parse_catalog_response(response_text)
            
            # Add metadata
            result['model'] = 'groq'
            result['source_language'] = transcription.get('language', 'unknown')
            result['providers_available'] = [p.value for p in self.client.get_available_providers()]
            
            logger.info(f"Catalog entry generated: {result.get('product_name')}")
            return result
            
        except Exception as e:
            logger.error(f"Catalog generation error: {e}")
            raise
    
    def _build_catalog_prompt(
        self,
        vision_analysis: Dict[str, Any],
        transcription: Dict[str, Any],
        artisan_info: Optional[Dict[str, Any]]
    ) -> str:
        """
        Build prompt for catalog generation
        
        Args:
            vision_analysis: Vision analysis results
            transcription: Transcription results
            artisan_info: Artisan information
            
        Returns:
            Prompt string
        """
        prompt = """Generate a comprehensive ONDC-compliant product catalog entry based on the following information:

VISION ANALYSIS:
"""
        prompt += json.dumps(vision_analysis, indent=2, ensure_ascii=False)
        
        prompt += "\n\nARTISAN DESCRIPTION (in vernacular):\n"
        prompt += f"Language: {transcription.get('language', 'unknown')}\n"
        prompt += f"Text: {transcription.get('text', '')}\n"
        
        if artisan_info:
            prompt += "\n\nARTISAN INFORMATION:\n"
            prompt += json.dumps(artisan_info, indent=2, ensure_ascii=False)
        
        prompt += """

IMPORTANT: Extract ALL information from the artisan's description, especially:
- PRICE (look for numbers with currency like rupees, ₹, INR)
- DIMENSIONS (length, width, height, size)
- WEIGHT (if mentioned)
- QUANTITY (pieces, sets)
- SPECIAL FEATURES (handmade, traditional, etc.)

Generate a complete ONDC catalog entry in JSON format:

Return ONLY a JSON object with this EXACT structure:
{
  "product_name": "Descriptive product name in English",
  "short_description": "Brief 1-2 sentence description highlighting key features",
  "long_description": "Detailed 3-4 paragraph description covering materials, craftsmanship, cultural significance, and usage",
  "category": "Main product category",
  "subcategory": "Specific subcategory",
  "attributes": {
    "materials": ["material1", "material2"],
    "colors": ["primary_color", "secondary_color"],
    "dimensions": {
      "length": "value with unit (e.g., 6 meters)",
      "width": "value with unit (e.g., 1.2 meters)",
      "height": "value with unit if applicable"
    },
    "weight": "value with unit (e.g., 500 grams)",
    "craftsmanship": "Detailed technique description",
    "origin": "Region or place of origin",
    "care_instructions": "How to maintain the product"
  },
  "price": {
    "value": EXTRACT_NUMBER_FROM_TRANSCRIPTION,
    "currency": "INR",
    "display": "₹5,000"
  },
  "specifications": {
    "handmade": true/false,
    "traditional": true/false,
    "customizable": true/false,
    "occasion": "wedding/daily/festival/etc"
  },
  "tags": ["searchable", "keywords", "for", "discovery"],
  "vernacular": {
    "language": "language code",
    "description": "EXACT original vernacular description from transcription"
  },
  "seo_keywords": ["keyword1", "keyword2", "keyword3"],
  "confidence": 0.85,
  "extracted_from_voice": {
    "price_mentioned": true/false,
    "dimensions_mentioned": true/false,
    "materials_mentioned": true/false
  }
}

CRITICAL RULES:
1. ALWAYS extract price if ANY number is mentioned (e.g., "पांच हजार" = 5000, "दो सौ" = 200)
2. Convert vernacular numbers to digits (e.g., "पांच हजार रुपये" → 5000)
3. Extract dimensions if mentioned (e.g., "छह मीटर" = 6 meters)
4. Preserve ALL vernacular text exactly as provided
5. Be specific about materials and craftsmanship
6. Include cultural context in long description
7. Add care instructions if product type is known
8. Set confidence based on information completeness

NUMBER CONVERSION GUIDE (Hindi):
- एक = 1, दो = 2, तीन = 3, चार = 4, पांच = 5
- दस = 10, बीस = 20, पचास = 50, सौ = 100
- हजार = 1000, लाख = 100000

Generate the catalog now:"""
        
        return prompt
    
    def _parse_catalog_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse AI response
        
        Args:
            response_text: Response text from AI
            
        Returns:
            Parsed catalog entry
        """
        try:
            # Extract JSON from response
            if '```json' in response_text:
                json_start = response_text.find('```json') + 7
                json_end = response_text.find('```', json_start)
                json_text = response_text[json_start:json_end].strip()
            elif '```' in response_text:
                json_start = response_text.find('```') + 3
                json_end = response_text.find('```', json_start)
                json_text = response_text[json_start:json_end].strip()
            else:
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                json_text = response_text[json_start:json_end]
            
            result = json.loads(json_text)
            
            # Add flags
            confidence = result.get('confidence', 0.0)
            result['low_confidence'] = confidence < 0.7
            result['requires_manual_review'] = confidence < 0.7
            
            return result
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse catalog response: {e}")
            logger.debug(f"Response text: {response_text}")
            
            # Return fallback
            return {
                'product_name': 'Unknown Product',
                'short_description': 'Failed to generate description',
                'long_description': '',
                'category': 'Unknown',
                'subcategory': None,
                'attributes': {},
                'price': {'value': None, 'currency': 'INR'},
                'tags': [],
                'vernacular': {'language': 'unknown', 'description': ''},
                'seo_keywords': [],
                'confidence': 0.0,
                'low_confidence': True,
                'requires_manual_review': True,
                'error': str(e)
            }
    
    def translate_to_english(self, vernacular_text: str, source_language: str) -> str:
        """
        Translate vernacular text to English
        
        Args:
            vernacular_text: Text in vernacular language
            source_language: Source language code
            
        Returns:
            Translated English text
        """
        prompt = f"""Translate the following {source_language} text to English.
Preserve the meaning and context. Be accurate.

Text: {vernacular_text}

Return only the English translation, nothing else."""
        
        try:
            translation = self.client.generate_text(
                prompt=prompt,
                max_tokens=500,
                temperature=0.3
            )
            
            return translation.strip()
            
        except Exception as e:
            logger.error(f"Translation error: {e}")
            return vernacular_text  # Return original if translation fails
    
    def enhance_description(self, basic_description: str, additional_context: Dict[str, Any]) -> str:
        """
        Enhance a basic product description with additional context
        
        Args:
            basic_description: Basic product description
            additional_context: Additional context (materials, colors, etc.)
            
        Returns:
            Enhanced description
        """
        prompt = f"""Enhance this product description with the additional context provided.
Make it more detailed, engaging, and SEO-friendly while maintaining accuracy.

Basic Description:
{basic_description}

Additional Context:
{json.dumps(additional_context, indent=2, ensure_ascii=False)}

Return an enhanced description (150-200 words) that:
- Highlights unique features
- Mentions materials and craftsmanship
- Appeals to buyers
- Includes relevant keywords
- Maintains professional tone
"""
        
        try:
            enhanced = self.client.generate_text(
                prompt=prompt,
                max_tokens=800,
                temperature=0.6
            )
            
            return enhanced.strip()
            
        except Exception as e:
            logger.error(f"Description enhancement error: {e}")
            return basic_description  # Return original if enhancement fails
