"""
Amazon Bedrock Vision Analyzer using Claude

Uses Claude models for complex vision analysis with multimodal capabilities.
"""
import json
import logging
import base64
import os
from typing import Dict, Any, Optional, List
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class BedrockVisionAnalyzer:
    """Vision analysis using Claude via Bedrock"""
    
    def __init__(self, region: str = 'ap-south-1', model_id: Optional[str] = None):
        """
        Initialize Bedrock client
        
        Args:
            region: AWS region
            model_id: Optional model ID override (defaults to BEDROCK_MODEL_ID env var)
        """
        self.client = boto3.client('bedrock-runtime', region_name=region)
        self.region = region
        # Use provided model_id, or fall back to env var, or use default
        self.model_id = model_id or os.getenv('BEDROCK_MODEL_ID', 'anthropic.claude-3-haiku-20240307-v1:0')
        
        logger.info(f"Initialized Bedrock Vision Analyzer with model: {self.model_id}")
        
    def analyze_product_image(
        self,
        image_bytes: bytes,
        rekognition_labels: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Analyze product image using Claude 3.5 Sonnet
        
        Args:
            image_bytes: Image data as bytes
            rekognition_labels: Optional labels from Rekognition Custom Labels
            
        Returns:
            Dict containing detailed product analysis
        """
        # Encode image to base64
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # Build prompt
        prompt = self._build_vision_prompt(rekognition_labels)
        
        # Prepare request
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2000,
            "temperature": 0.3,  # Lower temperature for more consistent results
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
        }
        
        try:
            logger.info(f"Invoking {self.model_id} for vision analysis")
            
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body)
            )
            
            response_body = json.loads(response['body'].read())
            
            # Extract text from response
            content = response_body.get('content', [])
            analysis_text = content[0].get('text', '') if content else ''
            
            # Parse structured response
            result = self._parse_vision_response(analysis_text)
            
            # Add metadata
            result['model'] = self.model_id
            result['rekognition_labels'] = rekognition_labels or []
            
            logger.info(f"Vision analysis complete: category={result.get('category')}")
            return result
            
        except ClientError as e:
            logger.error(f"Bedrock vision analysis error: {e}")
            raise
    
    def _build_vision_prompt(self, rekognition_labels: Optional[List[str]] = None) -> str:
        """
        Build prompt for vision analysis
        
        Args:
            rekognition_labels: Optional labels from Rekognition
            
        Returns:
            Prompt string
        """
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
        """
        Parse Claude's vision response
        
        Args:
            response_text: Response text from Claude
            
        Returns:
            Parsed result dictionary
        """
        try:
            # Try to extract JSON from response
            # Claude sometimes wraps JSON in markdown code blocks
            if '```json' in response_text:
                json_start = response_text.find('```json') + 7
                json_end = response_text.find('```', json_start)
                json_text = response_text[json_start:json_end].strip()
            elif '```' in response_text:
                json_start = response_text.find('```') + 3
                json_end = response_text.find('```', json_start)
                json_text = response_text[json_start:json_end].strip()
            else:
                # Try to find JSON object
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
            
            # Return fallback result
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
        """
        Extract text from image using Claude's vision capabilities
        
        Args:
            image_bytes: Image data as bytes
            
        Returns:
            List of extracted text strings
        """
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        prompt = """Extract all visible text from this image.
Return only the text you see, one item per line.
If there's no text, return an empty list."""
        
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 500,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
        }
        
        try:
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body)
            )
            
            response_body = json.loads(response['body'].read())
            content = response_body.get('content', [])
            text = content[0].get('text', '') if content else ''
            
            # Split by newlines and filter empty lines
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            
            return lines
            
        except ClientError as e:
            logger.error(f"Text extraction error: {e}")
            return []
