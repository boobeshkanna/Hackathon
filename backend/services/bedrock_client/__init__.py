"""
Amazon Bedrock Client Services

Uses Claude models via Bedrock for AI tasks:
- Claude 3.5 Sonnet: Complex vision analysis and reasoning
- Claude 3 Haiku: Cost-effective catalog generation
"""
from .vision_analyzer import BedrockVisionAnalyzer
from .catalog_generator import BedrockCatalogGenerator

__all__ = ['BedrockVisionAnalyzer', 'BedrockCatalogGenerator']
