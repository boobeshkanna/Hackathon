"""
Amazon Rekognition Custom Labels Product Detector

Uses Rekognition Custom Labels for trained product detection.
"""
import logging
from typing import Dict, Any, List, Optional
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class RekognitionProductDetector:
    """Product detection using Rekognition Custom Labels"""
    
    def __init__(
        self,
        project_arn: Optional[str] = None,
        model_version: str = 'latest',
        region: str = 'ap-south-1',
        min_confidence: float = 70.0
    ):
        """
        Initialize Rekognition Custom Labels client
        
        Args:
            project_arn: ARN of the Custom Labels project
            model_version: Model version to use
            region: AWS region
            min_confidence: Minimum confidence threshold (0-100)
        """
        self.client = boto3.client('rekognition', region_name=region)
        self.project_arn = project_arn
        self.model_version = model_version
        self.min_confidence = min_confidence
        self.region = region
        
        # Model ARN will be constructed when needed
        self.model_arn = None
        if project_arn:
            self.model_arn = self._construct_model_arn(project_arn, model_version)
    
    def _construct_model_arn(self, project_arn: str, version: str) -> str:
        """
        Construct model ARN from project ARN
        
        Args:
            project_arn: Project ARN
            version: Model version
            
        Returns:
            Model ARN
        """
        # Format: arn:aws:rekognition:region:account:project/project-name/version/version-name/timestamp
        if version == 'latest':
            # Get latest version
            try:
                response = self.client.describe_project_versions(
                    ProjectArn=project_arn,
                    MaxResults=1
                )
                versions = response.get('ProjectVersionDescriptions', [])
                if versions:
                    return versions[0]['ProjectVersionArn']
            except ClientError as e:
                logger.warning(f"Failed to get latest version: {e}")
        
        return f"{project_arn}/version/{version}"
    
    def detect_products(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Detect products in image using Custom Labels
        
        Args:
            image_bytes: Image data as bytes
            
        Returns:
            Dict containing detection results
        """
        if not self.model_arn:
            logger.warning("No Custom Labels model configured, using standard Rekognition")
            return self._detect_with_standard_rekognition(image_bytes)
        
        try:
            logger.info(f"Detecting products with Custom Labels model: {self.model_arn}")
            
            response = self.client.detect_custom_labels(
                ProjectVersionArn=self.model_arn,
                Image={'Bytes': image_bytes},
                MinConfidence=self.min_confidence
            )
            
            custom_labels = response.get('CustomLabels', [])
            
            # Parse results
            result = self._parse_custom_labels(custom_labels)
            
            logger.info(f"Detected {len(custom_labels)} products with confidence >= {self.min_confidence}%")
            return result
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            
            if error_code == 'ResourceNotFoundException':
                logger.error(f"Custom Labels model not found: {self.model_arn}")
                logger.info("Falling back to standard Rekognition")
                return self._detect_with_standard_rekognition(image_bytes)
            
            elif error_code == 'InvalidParameterException':
                logger.error(f"Model not running or invalid: {self.model_arn}")
                logger.info("Falling back to standard Rekognition")
                return self._detect_with_standard_rekognition(image_bytes)
            
            else:
                logger.error(f"Rekognition Custom Labels error: {e}")
                raise
    
    def _parse_custom_labels(self, custom_labels: List[Dict]) -> Dict[str, Any]:
        """
        Parse Custom Labels detection results
        
        Args:
            custom_labels: Custom labels from Rekognition
            
        Returns:
            Parsed detection results
        """
        detections = []
        categories = []
        max_confidence = 0.0
        
        for label in custom_labels:
            name = label.get('Name', '')
            confidence = label.get('Confidence', 0.0)
            geometry = label.get('Geometry', {})
            
            detection = {
                'label': name,
                'confidence': confidence / 100.0,  # Convert to 0-1 scale
                'bounding_box': self._parse_bounding_box(geometry)
            }
            
            detections.append(detection)
            
            if name not in categories:
                categories.append(name)
            
            if confidence > max_confidence:
                max_confidence = confidence
        
        # Get primary detection (highest confidence)
        primary_detection = max(detections, key=lambda x: x['confidence']) if detections else None
        
        result = {
            'detections': detections,
            'categories': categories,
            'primary_category': primary_detection['label'] if primary_detection else 'Unknown',
            'primary_confidence': max_confidence / 100.0,
            'detection_count': len(detections),
            'low_confidence': max_confidence < 70.0,
            'requires_manual_review': max_confidence < 70.0,
            'model_type': 'custom_labels'
        }
        
        return result
    
    def _parse_bounding_box(self, geometry: Dict) -> Optional[Dict[str, float]]:
        """
        Parse bounding box from geometry
        
        Args:
            geometry: Geometry dict from Rekognition
            
        Returns:
            Bounding box dict or None
        """
        if not geometry:
            return None
        
        bbox = geometry.get('BoundingBox', {})
        if not bbox:
            return None
        
        return {
            'left': bbox.get('Left', 0.0),
            'top': bbox.get('Top', 0.0),
            'width': bbox.get('Width', 0.0),
            'height': bbox.get('Height', 0.0)
        }
    
    def _detect_with_standard_rekognition(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Fallback to standard Rekognition if Custom Labels unavailable
        
        Args:
            image_bytes: Image data as bytes
            
        Returns:
            Detection results using standard Rekognition
        """
        try:
            response = self.client.detect_labels(
                Image={'Bytes': image_bytes},
                MaxLabels=10,
                MinConfidence=self.min_confidence
            )
            
            labels = response.get('Labels', [])
            
            # Convert to similar format as Custom Labels
            detections = []
            categories = []
            
            for label in labels:
                name = label.get('Name', '')
                confidence = label.get('Confidence', 0.0)
                
                detections.append({
                    'label': name,
                    'confidence': confidence / 100.0,
                    'bounding_box': None
                })
                
                categories.append(name)
            
            max_confidence = max([d['confidence'] for d in detections]) * 100 if detections else 0.0
            
            result = {
                'detections': detections,
                'categories': categories,
                'primary_category': detections[0]['label'] if detections else 'Unknown',
                'primary_confidence': max_confidence / 100.0,
                'detection_count': len(detections),
                'low_confidence': max_confidence < 70.0,
                'requires_manual_review': max_confidence < 70.0,
                'model_type': 'standard_rekognition'
            }
            
            return result
            
        except ClientError as e:
            logger.error(f"Standard Rekognition error: {e}")
            raise
    
    def start_model(self) -> bool:
        """
        Start the Custom Labels model
        
        Returns:
            True if started successfully
        """
        if not self.model_arn:
            logger.error("No model ARN configured")
            return False
        
        try:
            logger.info(f"Starting Custom Labels model: {self.model_arn}")
            
            self.client.start_project_version(
                ProjectVersionArn=self.model_arn,
                MinInferenceUnits=1
            )
            
            logger.info("Model start initiated (may take 10-30 minutes)")
            return True
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            
            if error_code == 'ResourceInUseException':
                logger.info("Model is already running")
                return True
            
            logger.error(f"Failed to start model: {e}")
            return False
    
    def stop_model(self) -> bool:
        """
        Stop the Custom Labels model
        
        Returns:
            True if stopped successfully
        """
        if not self.model_arn:
            logger.error("No model ARN configured")
            return False
        
        try:
            logger.info(f"Stopping Custom Labels model: {self.model_arn}")
            
            self.client.stop_project_version(
                ProjectVersionArn=self.model_arn
            )
            
            logger.info("Model stop initiated")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to stop model: {e}")
            return False
    
    def get_model_status(self) -> str:
        """
        Get the status of the Custom Labels model
        
        Returns:
            Model status string
        """
        if not self.model_arn:
            return 'NOT_CONFIGURED'
        
        try:
            response = self.client.describe_project_versions(
                ProjectArn=self.project_arn,
                VersionNames=[self.model_version] if self.model_version != 'latest' else None,
                MaxResults=1
            )
            
            versions = response.get('ProjectVersionDescriptions', [])
            if versions:
                return versions[0].get('Status', 'UNKNOWN')
            
            return 'NOT_FOUND'
            
        except ClientError as e:
            logger.error(f"Failed to get model status: {e}")
            return 'ERROR'
