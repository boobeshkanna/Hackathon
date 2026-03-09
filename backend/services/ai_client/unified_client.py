"""
Unified AI Client with automatic fallback support
"""
import os
import logging
from typing import Dict, Any, Optional, List
from .providers import (
    AIProvider, BaseAIProvider, OpenAIProvider, 
    AnthropicProvider, GroqProvider, BedrockProvider
)

logger = logging.getLogger(__name__)


class UnifiedAIClient:
    """
    Unified AI client with automatic provider fallback
    
    Priority order (configurable):
    1. Bedrock (if AWS credentials available)
    2. Anthropic (if API key available)
    3. OpenAI (if API key available)
    4. Groq (if API key available)
    """
    
    def __init__(
        self,
        preferred_provider: Optional[AIProvider] = None,
        fallback_enabled: bool = True
    ):
        """
        Initialize unified AI client
        
        Args:
            preferred_provider: Preferred AI provider (auto-detect if None)
            fallback_enabled: Enable automatic fallback to other providers
        """
        self.fallback_enabled = fallback_enabled
        self.providers: Dict[AIProvider, BaseAIProvider] = {}
        self.preferred_provider = preferred_provider
        
        # Initialize available providers
        self._initialize_providers()
        
        if not self.providers:
            raise RuntimeError(
                "No AI providers available. Set at least one of: "
                "OPENAI_API_KEY, ANTHROPIC_API_KEY, GROQ_API_KEY, or AWS credentials"
            )
        
        logger.info(f"Initialized UnifiedAIClient with providers: {list(self.providers.keys())}")
    
    def _initialize_providers(self):
        """Initialize all available AI providers"""
        
        # Try Bedrock first (if preferred or AWS creds available)
        if self.preferred_provider == AIProvider.BEDROCK or os.getenv('AWS_REGION'):
            try:
                bedrock = BedrockProvider(
                    region=os.getenv('AWS_REGION', 'ap-south-1'),
                    model_id=os.getenv('BEDROCK_MODEL_ID', 'anthropic.claude-3-haiku-20240307-v1:0')
                )
                self.providers[AIProvider.BEDROCK] = bedrock
                logger.info("✓ Bedrock provider available")
            except Exception as e:
                logger.warning(f"✗ Bedrock provider unavailable: {e}")
        
        # Try Anthropic
        if os.getenv('ANTHROPIC_API_KEY'):
            try:
                anthropic = AnthropicProvider()
                self.providers[AIProvider.ANTHROPIC] = anthropic
                logger.info("✓ Anthropic provider available")
            except Exception as e:
                logger.warning(f"✗ Anthropic provider unavailable: {e}")
        
        # Try OpenAI
        if os.getenv('OPENAI_API_KEY'):
            try:
                openai = OpenAIProvider()
                self.providers[AIProvider.OPENAI] = openai
                logger.info("✓ OpenAI provider available")
            except Exception as e:
                logger.warning(f"✗ OpenAI provider unavailable: {e}")
        
        # Try Groq
        if os.getenv('GROQ_API_KEY'):
            try:
                groq = GroqProvider()
                self.providers[AIProvider.GROQ] = groq
                logger.info("✓ Groq provider available")
            except Exception as e:
                logger.warning(f"✗ Groq provider unavailable: {e}")
    
    def _get_provider_priority(self) -> List[AIProvider]:
        """Get provider priority order"""
        if self.preferred_provider and self.preferred_provider in self.providers:
            # Preferred provider first, then others
            priority = [self.preferred_provider]
            priority.extend([p for p in self.providers.keys() if p != self.preferred_provider])
            return priority
        
        # Default priority order
        default_order = [
            AIProvider.BEDROCK,
            AIProvider.ANTHROPIC,
            AIProvider.OPENAI,
            AIProvider.GROQ
        ]
        return [p for p in default_order if p in self.providers]
    
    def generate_text(
        self,
        prompt: str,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        provider: Optional[AIProvider] = None
    ) -> str:
        """
        Generate text using available AI provider
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            provider: Specific provider to use (None for auto)
            
        Returns:
            Generated text
        """
        providers_to_try = [provider] if provider else self._get_provider_priority()
        
        last_error = None
        for provider_name in providers_to_try:
            if provider_name not in self.providers:
                continue
            
            try:
                logger.info(f"Attempting text generation with {provider_name}")
                result = self.providers[provider_name].generate_text(
                    prompt=prompt,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                logger.info(f"✓ Text generation successful with {provider_name}")
                return result
            except Exception as e:
                last_error = e
                logger.warning(f"✗ {provider_name} failed: {e}")
                
                if not self.fallback_enabled or provider:
                    raise
                
                logger.info("Trying next provider...")
                continue
        
        raise RuntimeError(f"All AI providers failed. Last error: {last_error}")
    
    def analyze_image(
        self,
        image_bytes: bytes,
        prompt: str,
        max_tokens: int = 2000,
        provider: Optional[AIProvider] = None
    ) -> str:
        """
        Analyze image using available AI provider with vision capabilities
        
        Args:
            image_bytes: Image data as bytes
            prompt: Analysis prompt
            max_tokens: Maximum tokens to generate
            provider: Specific provider to use (None for auto)
            
        Returns:
            Analysis result
        """
        # Vision-capable providers in priority order
        vision_providers = [
            AIProvider.BEDROCK,
            AIProvider.ANTHROPIC,
            AIProvider.OPENAI,
            AIProvider.GROQ  # Limited vision support
        ]
        
        providers_to_try = [provider] if provider else [
            p for p in vision_providers if p in self.providers
        ]
        
        last_error = None
        for provider_name in providers_to_try:
            if provider_name not in self.providers:
                continue
            
            try:
                logger.info(f"Attempting image analysis with {provider_name}")
                result = self.providers[provider_name].analyze_image(
                    image_bytes=image_bytes,
                    prompt=prompt,
                    max_tokens=max_tokens
                )
                logger.info(f"✓ Image analysis successful with {provider_name}")
                return result
            except NotImplementedError:
                logger.warning(f"✗ {provider_name} doesn't support vision")
                continue
            except Exception as e:
                last_error = e
                logger.warning(f"✗ {provider_name} vision failed: {e}")
                
                if not self.fallback_enabled or provider:
                    raise
                
                logger.info("Trying next provider...")
                continue
        
        raise RuntimeError(f"All vision-capable providers failed. Last error: {last_error}")
    
    def get_available_providers(self) -> List[AIProvider]:
        """Get list of available providers"""
        return list(self.providers.keys())
    
    def is_provider_available(self, provider: AIProvider) -> bool:
        """Check if specific provider is available"""
        return provider in self.providers
