"""
Amazon Rekognition Vision Service

Uses AWS Rekognition for image analysis without requiring a trained model.
"""
import logging
from typing import Dict, Any, List, Optional
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class VisionService:
    """Service for image analysis using Amazon Rekognition"""
    
    def __init__(self, region: str = 'ap-south-1'):
        """
        Initialize Rekognition client
        
        Args:
            region: AWS region
        """
        self.client = boto3.client('rekognition', region_name=region)
        self.confidence_threshold = 60.0  # Minimum confidence for labels
        
    def analyze_product_image(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Analyze product image using Rekognition
        
        Args:
            image_bytes: Image data as bytes
            
        Returns:
            Dict containing analysis results
        """
        try:
            # Detect labels (objects, scenes, concepts)
            labels_response = self.client.detect_labels(
                Image={'Bytes': image_bytes},
                MaxLabels=10,
                MinConfidence=self.confidence_threshold
            )
            
            # Detect dominant colors
            # Note: Rekognition doesn't have direct color detection
            # You can use detect_labels and look for color-related labels
            # Or use a simple color extraction algorithm
            
            # Extract product information
            labels = labels_response.get('Labels', [])
            
            # Categorize labels
            category = self._extract_category(labels)
            materials = self._extract_materials(labels)
            colors = self._extract_colors(labels)
            
            # Get highest confidence
            max_confidence = max([label['Confidence'] for label in labels]) if labels else 0.0
            
            result = {
                'category': category,
                'subcategory': None,  # Can be refined based on labels
                'labels': [label['Name'] for label in labels],
                'materials': materials,
                'colors': colors,
                'confidence': max_confidence / 100.0,  # Convert to 0-1 scale
                'low_confidence': max_confidence < 70.0,
                'requires_manual_review': max_confidence < 70.0,
                'raw_labels': labels
            }
            
            logger.info(f"Image analysis complete: category={category}, confidence={max_confidence:.1f}%")
            return result
            
        except ClientError as e:
            logger.error(f"Rekognition error: {e}")
            raise
    
    def _extract_category(self, labels: List[Dict]) -> str:
        """
        Extract product category from labels
        
        Args:
            labels: Rekognition labels
            
        Returns:
            Product category
        """
        # Map common labels to product categories
        category_mapping = {
            'Clothing': 'Apparel',
            'Dress': 'Apparel',
            'Sari': 'Handloom Saree',
            'Textile': 'Textile Product',
            'Jewelry': 'Jewelry',
            'Pottery': 'Pottery',
            'Handicraft': 'Handicraft',
            'Furniture': 'Furniture',
            'Art': 'Art & Craft',
            'Basket': 'Basketry',
            'Bag': 'Bags & Accessories',
        }
        
        for label in labels:
            label_name = label['Name']
            if label_name in category_mapping:
                return category_mapping[label_name]
        
        # Default to first label if no mapping found
        return labels[0]['Name'] if labels else 'Unknown'
    
    def _extract_materials(self, labels: List[Dict]) -> List[str]:
        """
        Extract materials from labels
        
        Args:
            labels: Rekognition labels
            
        Returns:
            List of materials
        """
        material_keywords = [
            'Silk', 'Cotton', 'Wool', 'Leather', 'Metal', 
            'Wood', 'Clay', 'Stone', 'Glass', 'Fabric',
            'Textile', 'Bamboo', 'Jute', 'Brass', 'Silver'
        ]
        
        materials = []
        for label in labels:
            label_name = label['Name']
            if label_name in material_keywords:
                materials.append(label_name.lower())
        
        return materials if materials else ['unknown']
    
    def _extract_colors(self, labels: List[Dict]) -> List[str]:
        """
        Extract colors from labels
        
        Args:
            labels: Rekognition labels
            
        Returns:
            List of colors
        """
        color_keywords = [
            'Red', 'Blue', 'Green', 'Yellow', 'Orange', 'Purple',
            'Pink', 'Brown', 'Black', 'White', 'Gray', 'Gold',
            'Silver', 'Maroon', 'Beige', 'Cream'
        ]
        
        colors = []
        for label in labels:
            label_name = label['Name']
            if label_name in color_keywords:
                colors.append(label_name.lower())
        
        return colors if colors else ['multicolor']
    
    def detect_text_in_image(self, image_bytes: bytes) -> List[str]:
        """
        Detect text in image (useful for product labels)
        
        Args:
            image_bytes: Image data as bytes
            
        Returns:
            List of detected text strings
        """
        try:
            response = self.client.detect_text(
                Image={'Bytes': image_bytes}
            )
            
            text_detections = response.get('TextDetections', [])
            
            # Extract only LINE type text (not individual words)
            lines = [
                detection['DetectedText']
                for detection in text_detections
                if detection['Type'] == 'LINE' and detection['Confidence'] > 80.0
            ]
            
            logger.info(f"Detected {len(lines)} text lines in image")
            return lines
            
        except ClientError as e:
            logger.error(f"Text detection error: {e}")
            return []
    
    def check_image_quality(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Check image quality using Rekognition
        
        Args:
            image_bytes: Image data as bytes
            
        Returns:
            Dict with quality metrics
        """
        try:
            response = self.client.detect_labels(
                Image={'Bytes': image_bytes},
                MaxLabels=1
            )
            
            # If Rekognition can detect labels, image quality is acceptable
            labels = response.get('Labels', [])
            
            quality = {
                'acceptable': len(labels) > 0,
                'confidence': labels[0]['Confidence'] if labels else 0.0,
                'message': 'Image quality is acceptable' if labels else 'Image quality is too low'
            }
            
            return quality
            
        except ClientError as e:
            logger.error(f"Quality check error: {e}")
            return {
                'acceptable': False,
                'confidence': 0.0,
                'message': f'Error checking quality: {str(e)}'
            }
