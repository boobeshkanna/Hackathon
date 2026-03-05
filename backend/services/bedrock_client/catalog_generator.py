"""
Amazon Bedrock Catalog Generator using Claude

Uses Claude models for cost-effective catalog generation.
"""
import json
import logging
import os
from typing import Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class BedrockCatalogGenerator:
    """Catalog generation using Claude via Bedrock"""
    
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
        
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1500,
            "temperature": 0.5,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        try:
            logger.info(f"Invoking {self.model_id} for catalog generation")
            
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body)
            )
            
            response_body = json.loads(response['body'].read())
            
            # Extract text from response
            content = response_body.get('content', [])
            catalog_text = content[0].get('text', '') if content else ''
            
            # Parse structured response
            result = self._parse_catalog_response(catalog_text)
            
            # Add metadata
            result['model'] = 'claude-3-haiku'
            result['source_language'] = transcription.get('language', 'unknown')
            
            logger.info(f"Catalog entry generated: {result.get('product_name')}")
            return result
            
        except ClientError as e:
            logger.error(f"Bedrock catalog generation error: {e}")
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
        prompt = """Generate an ONDC-compliant product catalog entry based on the following information:

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

Generate a complete ONDC catalog entry in JSON format with:

1. Product name (in English, descriptive)
2. Product description (detailed, in English)
3. Category and subcategory (ONDC standard categories)
4. Attributes (materials, colors, dimensions, etc.)
5. Price estimation (if mentioned in audio, otherwise null)
6. Tags for searchability
7. Vernacular description (preserve original language)

Return ONLY a JSON object with this structure:
{
  "product_name": "descriptive product name",
  "short_description": "brief description (50 words)",
  "long_description": "detailed description (200 words)",
  "category": "ONDC category",
  "subcategory": "ONDC subcategory",
  "attributes": {
    "materials": ["material1", "material2"],
    "colors": ["color1", "color2"],
    "dimensions": "if mentioned",
    "weight": "if mentioned",
    "craftsmanship": "technique details"
  },
  "price": {
    "value": null or number,
    "currency": "INR"
  },
  "tags": ["tag1", "tag2", "tag3"],
  "vernacular": {
    "language": "language code",
    "description": "original vernacular description"
  },
  "seo_keywords": ["keyword1", "keyword2"],
  "confidence": 0.85
}

Guidelines:
- Use proper English grammar and spelling
- Preserve vernacular text exactly as transcribed
- Be specific about materials and craftsmanship
- Use ONDC standard categories where possible
- Include relevant search keywords
- Estimate confidence based on data quality
"""
        
        return prompt
    
    def _parse_catalog_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse Claude's catalog response
        
        Args:
            response_text: Response text from Claude
            
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
        
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 500,
            "temperature": 0.3,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
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
            translation = content[0].get('text', '') if content else ''
            
            return translation.strip()
            
        except ClientError as e:
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
        
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 800,
            "temperature": 0.6,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
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
            enhanced = content[0].get('text', '') if content else ''
            
            return enhanced.strip()
            
        except ClientError as e:
            logger.error(f"Description enhancement error: {e}")
            return basic_description  # Return original if enhancement fails
