"""
Vision Analyzer using Unified AI Client with fallback support
"""
import json
import logging
from typing import Dict, Any, Optional, List
from services.ai_client import UnifiedAIClient, AIProvider

logger = logging.getLogger(__name__)


class UnifiedVisionAnalyzer:
    """Vision analysis using any available AI provider"""
    
    def __init__(self, preferred_provider: Optional[AIProvider] = None):
        """
        Initialize vision analyzer with unified client
        
        Args:
            preferred_provider: Preferred AI provider (auto-detect if None)
        """
        self.client = UnifiedAIClient(
            preferred_provider=preferred_provider,
            fallback_enabled=True
        )
        logger.info(f"Initialized UnifiedVisionAnalyzer with providers: {self.client.get_available_providers()}")
    
    def analyze_product_image(
        self,
        image_bytes: bytes,
        rekognition_labels: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Analyze product image using available AI provider
        
        Args:
            image_bytes: Image data as bytes
            rekognition_labels: Optional labels from Rekognition Custom Labels
            
        Returns:
            Dict containing detailed product analysis
        """
        prompt = self._build_vision_prompt(rekognition_labels)
        
        try:
            logger.info("Starting vision analysis")
            
            response_text = self.client.analyze_image(
                image_bytes=image_bytes,
                prompt=prompt,
                max_tokens=2000
            )
            
            # Parse structured response
            result = self._parse_vision_response(response_text)
            
            # Add metadata
            result['rekognition_labels'] = rekognition_labels or []
            result['providers_available'] = [p.value for p in self.client.get_available_providers()]
            
            logger.info(f"Vision analysis complete: category={result.get('category')}")
            return result
            
        except Exception as e:
            logger.error(f"Vision analysis error: {e}")
            raise
    
    def _build_vision_prompt(self, rekognition_labels: Optional[List[str]] = None) -> str:
        """Build prompt for vision analysis"""
        base_prompt = """Analyze this artisan product image and provide detailed information in JSON format.

Focus on:
1. Product category (be specific: e.g., "Banarasi Silk Saree", not just "Saree")
2. Subcategory (e.g., "Wedding Saree", "Casual Wear")
3. Materials used (be specific: silk, cotton, zari, ikat, etc.)
4. Colors (primary and secondary colors)
5. Craftsmanship details (handloom, hand-embroidered, etc.)
6. Patterns and designs (geometric, floral, traditional motifs)
7. Estimated quality level (premium, standard, basic)
8. Confidence score (0.0 to 1.0)

"""
        
        if rekognition_labels:
            base_prompt += f"\nRekognition detected these labels: {', '.join(rekognition_labels)}\n"
            base_prompt += "Use these as hints but provide more specific artisan product details.\n"
        
        base_prompt += """
Return ONLY a JSON object with this structure:
{
  "category": "specific product category",
  "subcategory": "product subcategory",
  "materials": ["material1", "material2"],
  "colors": {
    "primary": ["color1", "color2"],
    "secondary": ["color3"]
  },
  "craftsmanship": {
    "technique": "handloom/hand-embroidered/etc",
    "details": "specific craftsmanship details"
  },
  "patterns": ["pattern1", "pattern2"],
  "quality_level": "premium/standard/basic",
  "confidence": 0.85,
  "description": "brief product description"
}

Be specific about Indian artisan products. Use proper terminology for traditional crafts.
"""
        
        return base_prompt
    
    def _parse_vision_response(self, response_text: str) -> Dict[str, Any]:
        """Parse AI response"""
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
            
            # Add flags for low confidence
            confidence = result.get('confidence', 0.0)
            result['low_confidence'] = confidence < 0.7
            result['requires_manual_review'] = confidence < 0.7
            
            return result
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse vision response: {e}")
            logger.debug(f"Response text: {response_text}")
            
            return {
                'category': 'Unknown',
                'subcategory': None,
                'materials': [],
                'colors': {'primary': [], 'secondary': []},
                'craftsmanship': {'technique': 'unknown', 'details': ''},
                'patterns': [],
                'quality_level': 'unknown',
                'confidence': 0.0,
                'description': 'Failed to analyze image',
                'low_confidence': True,
                'requires_manual_review': True,
                'error': str(e)
            }
    
    def extract_text_from_image(self, image_bytes: bytes) -> List[str]:
        """Extract text from image"""
        prompt = """Extract all visible text from this image.
Return only the text you see, one item per line.
If there's no text, return an empty list."""
        
        try:
            response_text = self.client.analyze_image(
                image_bytes=image_bytes,
                prompt=prompt,
                max_tokens=500
            )
            
            # Split by newlines and filter empty lines
            lines = [line.strip() for line in response_text.split('\n') if line.strip()]
            return lines
            
        except Exception as e:
            logger.error(f"Text extraction error: {e}")
            return []
