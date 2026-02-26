"""
AWS Bedrock Client for LLM inference
"""
import json
import logging
from typing import Dict, Any, Optional, List
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class BedrockClient:
    """Client for AWS Bedrock LLM services"""
    
    def __init__(self, model_id: str = 'anthropic.claude-v2', region: str = 'ap-south-1'):
        """
        Initialize Bedrock client
        
        Args:
            model_id: Bedrock model ID
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

    
    def _invoke_model(self, prompt: str, max_tokens: int = 2000) -> str:
        """
        Invoke Bedrock model with prompt
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            
        Returns:
            Model response text
        """
        if 'claude' in self.model_id:
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
        
        if 'claude' in self.model_id:
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
