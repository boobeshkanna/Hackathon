"""
Unit tests for Bedrock LLM integration
"""
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from backend.services.bedrock_client import BedrockClient, AttributeExtractor, TranscreationService
from backend.models import ExtractedAttributes, CSI


class TestBedrockClient:
    """Test BedrockClient functionality"""
    
    @patch('backend.services.bedrock_client.client.boto3.client')
    def test_initialization(self, mock_boto_client):
        """Test Bedrock client initialization"""
        client = BedrockClient()
        assert client.model_id == 'anthropic.claude-3-sonnet-20240229-v1:0'
        mock_boto_client.assert_called_once_with('bedrock-runtime', region_name='ap-south-1')
    
    @patch('backend.services.bedrock_client.client.boto3.client')
    def test_extract_attributes(self, mock_boto_client):
        """Test attribute extraction from multimodal input"""
        # Mock Bedrock response
        mock_response = {
            'body': MagicMock()
        }
        response_json = {
            "content": [{
                "text": '{"category": "Handloom Saree", "material": ["silk"], "colors": ["red"], "short_description": "Beautiful silk saree", "long_description": "A beautiful handwoven silk saree", "confidence_scores": {"category": 0.9}}'
            }]
        }
        mock_response['body'].read.return_value = json.dumps(response_json).encode('utf-8')
        
        mock_boto_client.return_value.invoke_model.return_value = mock_response
        
        client = BedrockClient()
        result = client.extract_attributes(
            transcription="यह एक सुंदर रेशमी साड़ी है",
            vision_data={'colors': ['red'], 'materials': ['silk']},
            language='hi'
        )
        
        assert isinstance(result, ExtractedAttributes)
        assert result.category == 'Handloom Saree'
        assert 'silk' in result.material
        assert 'red' in result.colors
    
    @patch('backend.services.bedrock_client.client.boto3.client')
    def test_identify_csi_terms(self, mock_boto_client):
        """Test CSI term identification"""
        mock_response = {
            'body': MagicMock()
        }
        response_json = {
            "content": [{
                "text": '[{"vernacular_term": "बनारसी", "transliteration": "Banarasi", "english_context": "Traditional weaving style from Varanasi", "cultural_significance": "Represents centuries-old craft tradition"}]'
            }]
        }
        mock_response['body'].read.return_value = json.dumps(response_json).encode('utf-8')
        
        mock_boto_client.return_value.invoke_model.return_value = mock_response
        
        client = BedrockClient()
        result = client.identify_csi_terms(
            transcription="यह बनारसी साड़ी है",
            language='hi'
        )
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], CSI)
        assert result[0].vernacular_term == 'बनारसी'
        assert result[0].transliteration == 'Banarasi'


class TestAttributeExtractor:
    """Test AttributeExtractor functionality"""
    
    @patch('backend.services.bedrock_client.attribute_extractor.BedrockClient')
    def test_extract_attributes_with_priority(self, mock_bedrock_class):
        """Test attribute extraction with voice priority resolution"""
        # Mock BedrockClient
        mock_client = Mock()
        mock_bedrock_class.return_value = mock_client
        
        # Mock extracted attributes
        mock_attrs = ExtractedAttributes(
            category='Handloom Saree',
            material=['silk'],
            colors=['red'],
            short_description='Beautiful silk saree',
            long_description='A beautiful handwoven silk saree',
            confidence_scores={'category': 0.9}
        )
        mock_client.extract_attributes.return_value = mock_attrs
        mock_client.identify_csi_terms.return_value = []
        
        extractor = AttributeExtractor(bedrock_client=mock_client)
        
        asr_result = {
            'transcription': 'यह एक सुंदर रेशमी साड़ी है',
            'confidence': 0.85
        }
        vision_result = {
            'colors': ['blue'],  # Conflict with voice
            'materials': ['cotton'],  # Conflict with voice
            'confidence': 0.75
        }
        
        result = extractor.extract_attributes_with_priority(
            asr_result=asr_result,
            vision_result=vision_result,
            language='hi'
        )
        
        assert isinstance(result, ExtractedAttributes)
        assert result.category == 'Handloom Saree'
        # Voice priority: should use voice-derived attributes
        assert 'silk' in result.material
        assert 'red' in result.colors
    
    def test_normalize_price(self):
        """Test price normalization"""
        extractor = AttributeExtractor()
        
        # Test various price formats
        price1 = {'value': '500', 'currency': 'rs'}
        normalized1 = extractor._normalize_price(price1)
        assert normalized1['value'] == 500.0
        assert normalized1['currency'] == 'INR'
        
        price2 = {'value': 1000, 'currency': 'RUPEES'}
        normalized2 = extractor._normalize_price(price2)
        assert normalized2['value'] == 1000.0
        assert normalized2['currency'] == 'INR'
    
    def test_extract_price_from_text(self):
        """Test price extraction from text"""
        extractor = AttributeExtractor()
        
        # Hindi text with price
        text1 = "यह साड़ी 500 रुपये की है"
        price1 = extractor.extract_price_from_text(text1, 'hi')
        assert price1 is not None
        assert price1['value'] == 500.0
        assert price1['currency'] == 'INR'
        
        # English text with price
        text2 = "This saree costs Rs. 1000"
        price2 = extractor.extract_price_from_text(text2, 'en')
        assert price2 is not None
        assert price2['value'] == 1000.0


class TestTranscreationService:
    """Test TranscreationService functionality"""
    
    @patch('backend.services.bedrock_client.transcreation_service.BedrockClient')
    def test_transcreate_with_cultural_preservation(self, mock_bedrock_class):
        """Test transcreation with cultural preservation"""
        mock_client = Mock()
        mock_bedrock_class.return_value = mock_client
        
        # Mock transcreation response
        mock_client.transcreate_description.return_value = {
            'short_description': 'Handwoven Banarasi Silk Saree',
            'long_description': 'A beautiful handwoven silk saree from Varanasi'
        }
        
        service = TranscreationService(bedrock_client=mock_client)
        
        attrs = ExtractedAttributes(
            category='Handloom Saree',
            material=['silk'],
            colors=['red'],
            short_description='',
            long_description='',
            craft_technique='Handwoven on pit loom',
            region_of_origin='Varanasi, Uttar Pradesh',
            csis=[
                CSI(
                    vernacular_term='बनारसी',
                    transliteration='Banarasi',
                    english_context='Traditional weaving style from Varanasi',
                    cultural_significance='Represents centuries-old craft tradition'
                )
            ]
        )
        
        result = service.transcreate_with_cultural_preservation(
            vernacular_text='यह एक सुंदर बनारसी साड़ी है',
            extracted_attrs=attrs,
            language='hi'
        )
        
        assert result.short_description == 'Handwoven Banarasi Silk Saree'
        assert 'Varanasi' in result.long_description
        assert 'Cultural Significance' in result.long_description
        assert 'Banarasi' in result.long_description
    
    def test_map_category_to_ondc(self):
        """Test category mapping to ONDC taxonomy"""
        service = TranscreationService()
        
        assert service._map_category_to_ondc('Handloom Saree') == 'Fashion:Ethnic Wear:Sarees'
        assert service._map_category_to_ondc('Pottery') == 'Home & Decor:Handicrafts:Pottery'
        assert service._map_category_to_ondc('Jewelry') == 'Fashion:Jewelry:Handcrafted'
        assert service._map_category_to_ondc('Unknown') == 'General:Handicrafts'
    
    def test_generate_item_id(self):
        """Test deterministic item ID generation"""
        service = TranscreationService()
        
        attrs1 = ExtractedAttributes(
            category='Handloom Saree',
            material=['silk'],
            colors=['red'],
            short_description='Test',
            long_description='Test',
            price={'value': 500, 'currency': 'INR'}
        )
        
        attrs2 = ExtractedAttributes(
            category='Handloom Saree',
            material=['silk'],
            colors=['red'],
            short_description='Different description',
            long_description='Different description',
            price={'value': 500, 'currency': 'INR'}
        )
        
        # Same attributes should generate same ID
        id1 = service._generate_item_id(attrs1)
        id2 = service._generate_item_id(attrs2)
        assert id1 == id2
        assert id1.startswith('item_')
    
    def test_format_as_beckn_item(self):
        """Test formatting as Beckn-compatible item"""
        service = TranscreationService()
        
        attrs = ExtractedAttributes(
            category='Handloom Saree',
            material=['silk'],
            colors=['red', 'gold'],
            short_description='Beautiful Banarasi Silk Saree',
            long_description='A beautiful handwoven silk saree from Varanasi',
            price={'value': 5000, 'currency': 'INR'},
            craft_technique='Handwoven on pit loom',
            region_of_origin='Varanasi, Uttar Pradesh'
        )
        
        image_urls = ['https://example.com/image1.jpg']
        
        result = service.format_as_beckn_item(
            extracted_attrs=attrs,
            image_urls=image_urls
        )
        
        assert result.descriptor.name == 'Beautiful Banarasi Silk Saree'
        assert result.price.value == '5000'
        assert result.price.currency == 'INR'
        assert result.category_id == 'Fashion:Ethnic Wear:Sarees'
        assert 'material' in result.tags
        assert result.tags['material'] == 'silk'
        assert result.tags['color'] == 'red,gold'
