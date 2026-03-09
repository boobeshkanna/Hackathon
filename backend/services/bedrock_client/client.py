"""
AWS Bedrock Client for LLM inference
"""
import json
import logging
from typing import Dict, Any, Optional, List
import boto3
from botocore.exceptions import ClientError
from models import ExtractedAttributes, CSI

logger = logging.getLogger(__name__)


class BedrockClient:
    """Client for AWS Bedrock LLM services"""
    
    def __init__(self, model_id: str = 'anthropic.claude-3-sonnet-20240229-v1:0', region: str = 'ap-south-1'):
        """
        Initialize Bedrock client
        
        Args:
            model_id: Bedrock model ID (default: Claude 3 Sonnet for multimodal)
            region: AWS region
        """
        self.model_id = model_id
        self.client = boto3.client('bedrock-runtime', region_name=region)
        logger.info(f"Initialized Bedrock client with model: {model_id}")
    
    def generate_catalog_entry(
        self,
        transcription: str,
        vision_data: Dict[str, Any],
        language: str = 'hi'
    ) -> Dict[str, Any]:
        """
        Generate ONDC catalog entry from transcription and vision data
        
        Args:
            transcription: Vernacular transcription
            vision_data: Vision model output
            language: Source language code
            
        Returns:
            Dict containing structured catalog entry
        """
        prompt = self._build_catalog_prompt(transcription, vision_data, language)
        
        try:
            response = self._invoke_model(prompt)
            catalog_entry = self._parse_catalog_response(response)
            logger.info("Catalog entry generated successfully")
            return catalog_entry
            
        except ClientError as e:
            logger.error(f"Error generating catalog entry: {e}")
            raise
    
    def extract_attributes(
        self,
        transcription: str,
        vision_data: Dict[str, Any],
        language: str = 'hi'
    ) -> ExtractedAttributes:
        """
        Extract structured attributes from multimodal input using Bedrock LLM
        
        Args:
            transcription: Vernacular transcription from ASR
            vision_data: Vision model analysis results
            language: Source language code
            
        Returns:
            ExtractedAttributes with comprehensive product information
        """
        prompt = self._build_attribute_extraction_prompt(transcription, vision_data, language)
        
        try:
            response = self._invoke_model(prompt, max_tokens=3000)
            attributes = self._parse_attributes_response(response)
            logger.info(f"Extracted attributes for category: {attributes.category}")
            return attributes
            
        except ClientError as e:
            logger.error(f"Error extracting attributes: {e}")
            raise
        except Exception as e:
            logger.error(f"Error parsing attributes: {e}")
            raise
    
    def identify_csi_terms(
        self,
        transcription: str,
        language: str = 'hi'
    ) -> List[CSI]:
        """
        Identify Cultural Specific Items (CSI) from vernacular transcription
        
        Args:
            transcription: Vernacular transcription
            language: Source language code
            
        Returns:
            List of CSI objects with cultural context
        """
        prompt = self._build_csi_identification_prompt(transcription, language)
        
        try:
            response = self._invoke_model(prompt, max_tokens=2000)
            csi_list = self._parse_csi_response(response)
            logger.info(f"Identified {len(csi_list)} CSI terms")
            return csi_list
            
        except ClientError as e:
            logger.error(f"Error identifying CSI terms: {e}")
            raise
    
    def transcreate_description(
        self,
        vernacular_text: str,
        extracted_attrs: ExtractedAttributes,
        language: str = 'hi'
    ) -> Dict[str, str]:
        """
        Transcreate vernacular description to SEO-friendly English while preserving cultural context
        
        Args:
            vernacular_text: Original vernacular description
            extracted_attrs: Extracted attributes with CSI terms
            language: Source language code
            
        Returns:
            Dict with 'short_description' and 'long_description'
        """
        prompt = self._build_transcreation_prompt(vernacular_text, extracted_attrs, language)
        
        try:
            response = self._invoke_model(prompt, max_tokens=2000)
            descriptions = self._parse_transcreation_response(response)
            logger.info("Transcreation completed successfully")
            return descriptions
            
        except ClientError as e:
            logger.error(f"Error transcreating description: {e}")
            raise

    
    def _invoke_model(self, prompt: str, max_tokens: int = 2000) -> str:
        """
        Invoke Bedrock model with prompt
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            
        Returns:
            Model response text
        """
        if 'claude-3' in self.model_id:
            # Claude 3 uses Messages API
            body = json.dumps({
                'anthropic_version': 'bedrock-2023-05-31',
                'max_tokens': max_tokens,
                'messages': [
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                'temperature': 0.7,
                'top_p': 0.9,
            })
        elif 'claude' in self.model_id:
            # Claude 2 uses legacy format
            body = json.dumps({
                'prompt': f'\n\nHuman: {prompt}\n\nAssistant:',
                'max_tokens_to_sample': max_tokens,
                'temperature': 0.7,
                'top_p': 0.9,
            })
        else:  # Titan or other models
            body = json.dumps({
                'inputText': prompt,
                'textGenerationConfig': {
                    'maxTokenCount': max_tokens,
                    'temperature': 0.7,
                    'topP': 0.9,
                }
            })
        
        response = self.client.invoke_model(
            modelId=self.model_id,
            body=body,
            contentType='application/json',
            accept='application/json'
        )
        
        response_body = json.loads(response['body'].read())
        
        if 'claude-3' in self.model_id:
            return response_body['content'][0]['text']
        elif 'claude' in self.model_id:
            return response_body['completion']
        else:
            return response_body['results'][0]['outputText']
    
    def _build_catalog_prompt(
        self,
        transcription: str,
        vision_data: Dict[str, Any],
        language: str
    ) -> str:
        """Build prompt for catalog generation"""
        return f"""You are an expert at converting vernacular product descriptions into structured ONDC catalog entries.

Language: {language}
Transcription: {transcription}
Vision Analysis: {json.dumps(vision_data, indent=2)}

Generate a structured catalog entry with:
1. Product name (preserve vernacular terms)
2. Category (ONDC taxonomy)
3. Description (bilingual: vernacular + English)
4. Attributes (color, material, size, etc.)
5. Price estimation (if mentioned)
6. Cultural context preservation

Output as JSON."""
    
    def _build_attribute_extraction_prompt(
        self,
        transcription: str,
        vision_data: Dict[str, Any],
        language: str
    ) -> str:
        """Build prompt for comprehensive attribute extraction"""
        return f"""You are an expert at extracting structured product attributes from multimodal artisan product descriptions.

LANGUAGE: {language}

VOICE TRANSCRIPTION (AUTHORITATIVE):
{transcription}

VISION ANALYSIS:
{json.dumps(vision_data, indent=2)}

TASK: Extract comprehensive product attributes following these rules:

1. CONFLICT RESOLUTION: If voice and vision disagree, ALWAYS prioritize voice transcription
2. CULTURAL PRESERVATION: Identify and preserve culturally significant terms (craft techniques, regional names, traditional materials)
3. PRICE EXTRACTION: Extract price with currency normalization (e.g., "पांच सौ रुपये" → {{"value": 500, "currency": "INR"}})
4. CONFIDENCE SCORING: Provide confidence (0.0-1.0) for each extracted attribute

OUTPUT FORMAT (JSON):
{{
  "category": "string (e.g., 'Handloom Saree', 'Pottery', 'Jewelry')",
  "subcategory": "string or null",
  "material": ["list of materials"],
  "colors": ["list of colors"],
  "dimensions": {{"length": number, "width": number, "height": number, "unit": "string"}} or null,
  "weight": {{"value": number, "unit": "string"}} or null,
  "price": {{"value": number, "currency": "string"}} or null,
  "short_description": "1-2 sentence description",
  "long_description": "Detailed description preserving cultural context",
  "craft_technique": "string or null (e.g., 'Handwoven on pit loom')",
  "region_of_origin": "string or null (e.g., 'Varanasi, Uttar Pradesh')",
  "confidence_scores": {{
    "category": 0.0-1.0,
    "material": 0.0-1.0,
    "colors": 0.0-1.0,
    "price": 0.0-1.0
  }}
}}

Extract attributes now:"""
    
    def _build_csi_identification_prompt(
        self,
        transcription: str,
        language: str
    ) -> str:
        """Build prompt for CSI (Cultural Specific Item) identification"""
        return f"""You are an expert in Indian traditional crafts and cultural heritage.

LANGUAGE: {language}
TRANSCRIPTION: {transcription}

TASK: Identify Cultural Specific Items (CSI) - terms that carry cultural significance and should be preserved in their original form.

CSI CATEGORIES:
1. Traditional craft techniques (e.g., "बनारसी बुनाई", "कांथा स्टिच")
2. Regional product names (e.g., "पोचमपल्ली", "चंदेरी")
3. Cultural materials (e.g., "ज़री", "खादी")
4. Traditional patterns/designs (e.g., "पैस्ले", "बूटी")
5. Cultural significance markers (e.g., "मंगल सूत्र", "पूजा थाली")

OUTPUT FORMAT (JSON array):
[
  {{
    "vernacular_term": "original term in source language",
    "transliteration": "roman script representation",
    "english_context": "brief explanation in English",
    "cultural_significance": "why this term matters culturally"
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
        
        return f"""You are an expert at transcreation - culturally adapting content while preserving meaning and context.

LANGUAGE: {language}
VERNACULAR TEXT: {vernacular_text}

EXTRACTED ATTRIBUTES:
- Category: {extracted_attrs.category}
- Materials: {', '.join(extracted_attrs.material)}
- Colors: {', '.join(extracted_attrs.colors)}
- Craft Technique: {extracted_attrs.craft_technique or 'Not specified'}
- Region: {extracted_attrs.region_of_origin or 'Not specified'}
{csi_context}

TASK: Create SEO-friendly English descriptions that:
1. PRESERVE cultural terms (use transliteration + context)
2. Make content discoverable for English-speaking buyers
3. Maintain authenticity and cultural significance
4. Include craft technique and region of origin
5. Are Beckn protocol compatible

OUTPUT FORMAT (JSON):
{{
  "short_description": "1-2 sentences, max 100 chars, SEO-optimized",
  "long_description": "Detailed description with cultural context, craft technique, and region. Preserve CSI terms with explanations."
}}

Generate transcreated descriptions now:"""

    
    def _parse_catalog_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response into structured catalog entry"""
        try:
            # Extract JSON from response
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            json_str = response[start_idx:end_idx]
            return json.loads(json_str)
        except (ValueError, json.JSONDecodeError) as e:
            logger.error(f"Error parsing catalog response: {e}")
            return {
                'raw_response': response,
                'parse_error': str(e)
            }
    
    def _parse_attributes_response(self, response: str) -> ExtractedAttributes:
        """Parse LLM response into ExtractedAttributes model"""
        try:
            # Extract JSON from response
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            json_str = response[start_idx:end_idx]
            data = json.loads(json_str)
            
            # Create ExtractedAttributes from parsed data
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
                csis=[],  # Will be populated separately
                craft_technique=data.get('craft_technique'),
                region_of_origin=data.get('region_of_origin'),
                confidence_scores=data.get('confidence_scores', {})
            )
        except (ValueError, json.JSONDecodeError) as e:
            logger.error(f"Error parsing attributes response: {e}")
            # Return minimal valid ExtractedAttributes
            return ExtractedAttributes(
                category='Unknown',
                short_description='Product description unavailable',
                long_description='Product description unavailable',
                confidence_scores={'category': 0.0}
            )
    
    def _parse_csi_response(self, response: str) -> List[CSI]:
        """Parse LLM response into list of CSI objects"""
        try:
            # Extract JSON array from response
            start_idx = response.find('[')
            end_idx = response.rfind(']') + 1
            json_str = response[start_idx:end_idx]
            data = json.loads(json_str)
            
            # Create CSI objects
            csi_list = []
            for item in data:
                csi = CSI(
                    vernacular_term=item.get('vernacular_term', ''),
                    transliteration=item.get('transliteration', ''),
                    english_context=item.get('english_context', ''),
                    cultural_significance=item.get('cultural_significance', '')
                )
                csi_list.append(csi)
            
            return csi_list
        except (ValueError, json.JSONDecodeError) as e:
            logger.error(f"Error parsing CSI response: {e}")
            return []
    
    def _parse_transcreation_response(self, response: str) -> Dict[str, str]:
        """Parse LLM response into transcreated descriptions"""
        try:
            # Extract JSON from response
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            json_str = response[start_idx:end_idx]
            data = json.loads(json_str)
            
            return {
                'short_description': data.get('short_description', ''),
                'long_description': data.get('long_description', '')
            }
        except (ValueError, json.JSONDecodeError) as e:
            logger.error(f"Error parsing transcreation response: {e}")
            return {
                'short_description': 'Product description unavailable',
                'long_description': 'Product description unavailable'
            }
    
    def translate_text(self, text: str, source_lang: str, target_lang: str = 'en') -> str:
        """
        Translate text between languages
        
        Args:
            text: Text to translate
            source_lang: Source language code
            target_lang: Target language code
            
        Returns:
            Translated text
        """
        prompt = f"Translate the following {source_lang} text to {target_lang}:\n\n{text}"
        
        try:
            return self._invoke_model(prompt, max_tokens=500)
        except ClientError as e:
            logger.error(f"Error translating text: {e}")
            raise
