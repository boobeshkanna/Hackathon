"""
Amazon Bedrock Client Services (DEPRECATED - Using Groq instead)

COMMENTED OUT: Bedrock-based services
- BedrockVisionAnalyzer: Replaced by UnifiedVisionAnalyzer (Groq)
- BedrockCatalogGenerator: Replaced by UnifiedCatalogGenerator (Groq)

NEW: Unified AI services with Groq support
"""
# COMMENTED: Bedrock-specific implementations
# from .vision_analyzer import BedrockVisionAnalyzer
# from .catalog_generator import BedrockCatalogGenerator

# NEW: Unified implementations using Groq
from .unified_vision_analyzer import UnifiedVisionAnalyzer
from .unified_catalog_generator import UnifiedCatalogGenerator

# Keep old imports for backward compatibility (but they use Groq now)
# __all__ = ['BedrockVisionAnalyzer', 'BedrockCatalogGenerator']

# New exports
__all__ = ['UnifiedVisionAnalyzer', 'UnifiedCatalogGenerator']
