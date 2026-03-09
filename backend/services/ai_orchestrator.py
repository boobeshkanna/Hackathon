"""
AI Services Orchestrator

Coordinates all AI services for complete product processing:
- Rekognition Custom Labels: Product detection (AWS)
- Groq: Vision analysis (replacing Bedrock)
- AWS Transcribe: Audio transcription (AWS)
- Groq: Catalog generation (replacing Bedrock)
"""
import logging
from typing import Dict, Any, Optional
from .rekognition_custom import RekognitionProductDetector
# from .bedrock_client import BedrockVisionAnalyzer, BedrockCatalogGenerator  # COMMENTED: Using Groq instead
from .bedrock_client import UnifiedVisionAnalyzer, UnifiedCatalogGenerator  # Using unified client with Groq
from .aws_ai_services import TranscriptionService
from services.ai_client import AIProvider

logger = logging.getLogger(__name__)


class AIOrchestrator:
    """Orchestrates all AI services for product processing"""
    
    def __init__(
            self,
            region: str = 'ap-south-1',
            rekognition_project_arn: Optional[str] = None,
            transcribe_s3_bucket: Optional[str] = None,
            bedrock_model_id: Optional[str] = None  # DEPRECATED: Using Groq instead
        ):
            """
            Initialize AI orchestrator

            Args:
                region: AWS region
                rekognition_project_arn: Custom Labels project ARN
                transcribe_s3_bucket: S3 bucket for Transcribe temp storage
                bedrock_model_id: DEPRECATED - Using Groq instead of Bedrock
            """
            self.region = region

            # Initialize AWS services (Rekognition)
            self.product_detector = RekognitionProductDetector(
                project_arn=rekognition_project_arn,
                region=region
            )

            # COMMENTED: Bedrock-based vision analyzer
            # self.vision_analyzer = BedrockVisionAnalyzer(region=region, model_id=bedrock_model_id)
            # Using Groq-based unified vision analyzer
            self.vision_analyzer = UnifiedVisionAnalyzer(preferred_provider=AIProvider.GROQ)

            # COMMENTED: Bedrock-based catalog generator
            # self.catalog_generator = BedrockCatalogGenerator(region=region, model_id=bedrock_model_id)
            # Using Groq-based unified catalog generator
            self.catalog_generator = UnifiedCatalogGenerator(preferred_provider=AIProvider.GROQ)

            # Initialize AWS Transcribe service
            self.transcription_service = TranscriptionService(
                region=region,
                s3_bucket=transcribe_s3_bucket
            )

            logger.info("AI Orchestrator initialized")
    
    def process_product(
        self,
        image_bytes: bytes,
        audio_bytes: Optional[bytes] = None,
        language_code: str = 'hi',
        audio_format: str = 'opus',
        artisan_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Complete product processing pipeline
        
        Args:
            image_bytes: Product image data
            audio_bytes: Optional audio description
            language_code: Language code for audio
            audio_format: Audio format
            artisan_info: Optional artisan information
            
        Returns:
            Complete processing results
        """
        logger.info("Starting complete product processing")
        
        result = {
            'detection': None,
            'vision_analysis': None,
            'transcription': None,
            'catalog_entry': None,
            'processing_stages': []
        }
        
        try:
            # Stage 1: Product Detection with Rekognition Custom Labels
            logger.info("Stage 1: Product detection")
            detection_result = self.product_detector.detect_products(image_bytes)
            result['detection'] = detection_result
            result['processing_stages'].append({
                'stage': 'detection',
                'status': 'success',
                'model': detection_result.get('model_type')
            })
            
            # Stage 2: Vision Analysis with Claude 3.5 Sonnet
            logger.info("Stage 2: Vision analysis")
            rekognition_labels = detection_result.get('categories', [])
            vision_result = self.vision_analyzer.analyze_product_image(
                image_bytes,
                rekognition_labels=rekognition_labels
            )
            result['vision_analysis'] = vision_result
            result['processing_stages'].append({
                'stage': 'vision_analysis',
                'status': 'success',
                'model': 'claude-3.5-sonnet'
            })
            
            # Stage 3: Audio Transcription (if provided)
            if audio_bytes:
                logger.info("Stage 3: Audio transcription")
                transcription_result = self.transcription_service.transcribe_audio(
                    audio_bytes,
                    language_code=language_code,
                    audio_format=audio_format
                )
                result['transcription'] = transcription_result
                result['processing_stages'].append({
                    'stage': 'transcription',
                    'status': 'success',
                    'service': 'aws-transcribe'
                })
            else:
                logger.info("Stage 3: Skipped (no audio provided)")
                result['transcription'] = {
                    'text': '',
                    'language': language_code,
                    'confidence': 0.0
                }
                result['processing_stages'].append({
                    'stage': 'transcription',
                    'status': 'skipped'
                })
            
            # Stage 4: Catalog Generation with Claude 3 Haiku
            logger.info("Stage 4: Catalog generation")
            catalog_result = self.catalog_generator.generate_catalog_entry(
                vision_analysis=vision_result,
                transcription=result['transcription'],
                artisan_info=artisan_info
            )
            result['catalog_entry'] = catalog_result
            result['processing_stages'].append({
                'stage': 'catalog_generation',
                'status': 'success',
                'model': 'claude-3-haiku'
            })
            
            # Calculate overall confidence
            confidences = []
            if detection_result.get('primary_confidence'):
                confidences.append(detection_result['primary_confidence'])
            if vision_result.get('confidence'):
                confidences.append(vision_result['confidence'])
            if result['transcription'].get('confidence'):
                confidences.append(result['transcription']['confidence'])
            if catalog_result.get('confidence'):
                confidences.append(catalog_result['confidence'])
            
            overall_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            result['overall_confidence'] = overall_confidence
            result['low_confidence'] = overall_confidence < 0.7
            result['requires_manual_review'] = overall_confidence < 0.7
            result['status'] = 'success'
            
            logger.info(f"Processing complete. Overall confidence: {overall_confidence:.2%}")
            
        except Exception as e:
            logger.error(f"Processing failed: {e}")
            result['status'] = 'failed'
            result['error'] = str(e)
            result['requires_manual_review'] = True
        
        return result
    
    def process_image_only(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Process image without audio
        
        Args:
            image_bytes: Product image data
            
        Returns:
            Vision processing results
        """
        logger.info("Processing image only")
        
        # Detect products
        detection_result = self.product_detector.detect_products(image_bytes)
        
        # Analyze with Claude
        rekognition_labels = detection_result.get('categories', [])
        vision_result = self.vision_analyzer.analyze_product_image(
            image_bytes,
            rekognition_labels=rekognition_labels
        )
        
        return {
            'detection': detection_result,
            'vision_analysis': vision_result,
            'confidence': vision_result.get('confidence', 0.0)
        }
    
    def process_audio_only(
        self,
        audio_bytes: bytes,
        language_code: str = 'hi',
        audio_format: str = 'opus'
    ) -> Dict[str, Any]:
        """
        Process audio without image
        
        Args:
            audio_bytes: Audio data
            language_code: Language code
            audio_format: Audio format
            
        Returns:
            Transcription results
        """
        logger.info("Processing audio only")
        
        transcription_result = self.transcription_service.transcribe_audio(
            audio_bytes,
            language_code=language_code,
            audio_format=audio_format
        )
        
        return transcription_result
    
    def generate_catalog_from_data(
        self,
        vision_data: Dict[str, Any],
        transcription_data: Dict[str, Any],
        artisan_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate catalog entry from pre-processed data
        
        Args:
            vision_data: Vision analysis results
            transcription_data: Transcription results
            artisan_info: Artisan information
            
        Returns:
            Catalog entry
        """
        logger.info("Generating catalog from existing data")
        
        return self.catalog_generator.generate_catalog_entry(
            vision_analysis=vision_data,
            transcription=transcription_data,
            artisan_info=artisan_info
        )
    
    def translate_description(self, text: str, source_language: str) -> str:
        """
        Translate vernacular description to English
        
        Args:
            text: Vernacular text
            source_language: Source language code
            
        Returns:
            English translation
        """
        return self.catalog_generator.translate_to_english(text, source_language)
    
    def enhance_catalog_description(
        self,
        description: str,
        context: Dict[str, Any]
    ) -> str:
        """
        Enhance catalog description with additional context
        
        Args:
            description: Basic description
            context: Additional context
            
        Returns:
            Enhanced description
        """
        return self.catalog_generator.enhance_description(description, context)
    
    def get_service_status(self) -> Dict[str, str]:
        """
        Get status of all AI services
        
        Returns:
            Dict with service statuses
        """
        return {
            'rekognition_custom_labels': self.product_detector.get_model_status(),
            'bedrock_vision': 'available',  # Bedrock is always available
            'bedrock_catalog': 'available',
            'transcribe': 'available'
        }
