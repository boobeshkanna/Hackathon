"""
AI Provider implementations for OpenAI, Anthropic, Groq, and Bedrock
"""
import os
import json
import base64
import logging
from typing import Dict, Any, Optional, List
from enum import Enum

logger = logging.getLogger(__name__)


class AIProvider(str, Enum):
    """Supported AI providers"""
    BEDROCK = "bedrock"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GROQ = "groq"


class BaseAIProvider:
    """Base class for AI providers"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
    
    def generate_text(self, prompt: str, max_tokens: int = 2000, temperature: float = 0.7) -> str:
        raise NotImplementedError
    
    def analyze_image(self, image_bytes: bytes, prompt: str, max_tokens: int = 2000) -> str:
        raise NotImplementedError


class OpenAIProvider(BaseAIProvider):
    """OpenAI API provider"""
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key or os.getenv('OPENAI_API_KEY'))
        if not self.api_key:
            raise ValueError("OpenAI API key not provided")
        
        try:
            import openai
            self.client = openai.OpenAI(api_key=self.api_key)
            logger.info("Initialized OpenAI provider")
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")
    
    def generate_text(self, prompt: str, max_tokens: int = 2000, temperature: float = 0.7) -> str:
        """Generate text using OpenAI"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",  # or gpt-4-turbo, gpt-3.5-turbo
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI generation error: {e}")
            raise
    
    def analyze_image(self, image_bytes: bytes, prompt: str, max_tokens: int = 2000) -> str:
        """Analyze image using OpenAI Vision"""
        try:
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            response = self.client.chat.completions.create(
                model="gpt-4o",  # Vision-capable model
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI vision error: {e}")
            raise


class AnthropicProvider(BaseAIProvider):
    """Anthropic Claude API provider"""
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key or os.getenv('ANTHROPIC_API_KEY'))
        if not self.api_key:
            raise ValueError("Anthropic API key not provided")
        
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=self.api_key)
            logger.info("Initialized Anthropic provider")
        except ImportError:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")
    
    def generate_text(self, prompt: str, max_tokens: int = 2000, temperature: float = 0.7) -> str:
        """Generate text using Claude"""
        try:
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",  # or claude-3-opus, claude-3-haiku
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Anthropic generation error: {e}")
            raise
    
    def analyze_image(self, image_bytes: bytes, prompt: str, max_tokens: int = 2000) -> str:
        """Analyze image using Claude Vision"""
        try:
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=max_tokens,
                messages=[
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
                            {"type": "text", "text": prompt}
                        ]
                    }
                ]
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Anthropic vision error: {e}")
            raise


class GroqProvider(BaseAIProvider):
    """Groq API provider (fast inference)"""
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key or os.getenv('GROQ_API_KEY'))
        if not self.api_key:
            raise ValueError("Groq API key not provided")
        
        try:
            from groq import Groq
            self.client = Groq(api_key=self.api_key)
            logger.info("Initialized Groq provider")
        except ImportError:
            raise ImportError("groq package not installed. Run: pip install groq")
    
    def generate_text(self, prompt: str, max_tokens: int = 2000, temperature: float = 0.7) -> str:
        """Generate text using Groq"""
        try:
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",  # or mixtral-8x7b-32768
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Groq generation error: {e}")
            raise
    
    def analyze_image(self, image_bytes: bytes, prompt: str, max_tokens: int = 2000) -> str:
        """Groq vision support using Llama 4 Scout"""
        try:
            # Use Llama 4 Scout vision model
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            response = self.client.chat.completions.create(
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.warning(f"Groq vision not available: {e}")
            raise NotImplementedError("Groq vision support limited - use OpenAI or Anthropic for vision tasks")


class BedrockProvider(BaseAIProvider):
    """AWS Bedrock provider"""
    
    def __init__(self, region: str = 'ap-south-1', model_id: str = 'anthropic.claude-3-haiku-20240307-v1:0'):
        super().__init__()
        self.region = region
        self.model_id = model_id
        
        try:
            import boto3
            self.client = boto3.client('bedrock-runtime', region_name=region)
            logger.info(f"Initialized Bedrock provider with model: {model_id}")
        except Exception as e:
            logger.error(f"Failed to initialize Bedrock: {e}")
            raise
    
    def generate_text(self, prompt: str, max_tokens: int = 2000, temperature: float = 0.7) -> str:
        """Generate text using Bedrock"""
        try:
            body = json.dumps({
                'anthropic_version': 'bedrock-2023-05-31',
                'max_tokens': max_tokens,
                'temperature': temperature,
                'messages': [{'role': 'user', 'content': prompt}]
            })
            
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=body
            )
            
            response_body = json.loads(response['body'].read())
            return response_body['content'][0]['text']
        except Exception as e:
            logger.error(f"Bedrock generation error: {e}")
            raise
    
    def analyze_image(self, image_bytes: bytes, prompt: str, max_tokens: int = 2000) -> str:
        """Analyze image using Bedrock Claude"""
        try:
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            body = json.dumps({
                'anthropic_version': 'bedrock-2023-05-31',
                'max_tokens': max_tokens,
                'messages': [
                    {
                        'role': 'user',
                        'content': [
                            {
                                'type': 'image',
                                'source': {
                                    'type': 'base64',
                                    'media_type': 'image/jpeg',
                                    'data': image_base64
                                }
                            },
                            {'type': 'text', 'text': prompt}
                        ]
                    }
                ]
            })
            
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=body
            )
            
            response_body = json.loads(response['body'].read())
            return response_body['content'][0]['text']
        except Exception as e:
            logger.error(f"Bedrock vision error: {e}")
            raise
