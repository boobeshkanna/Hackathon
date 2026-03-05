"""
Unit tests for tenant service
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from backend.models.tenant import TenantConfiguration, LanguageCode
from backend.services.tenant_service import TenantService


@pytest.fixture
def mock_dynamodb():
    """Mock DynamoDB resource"""
    with patch('boto3.resource') as mock_resource:
        mock_table = MagicMock()
        mock_resource.return_value.Table.return_value = mock_table
        yield mock_table


@pytest.fixture
def tenant_service(mock_dynamodb):
    """Create tenant service with mocked DynamoDB"""
    service = TenantService()
    service.tenant_table = mock_dynamodb
    service.catalog_table = mock_dynamodb
    return service


@pytest.fixture
def sample_tenant_config():
    """Sample tenant configuration"""
    return TenantConfiguration(
        tenant_id="tenant-123",
        tenant_name="Test Artisan Cooperative",
        default_language=LanguageCode.HINDI,
        supported_languages=[LanguageCode.HINDI, LanguageCode.TAMIL],
        cultural_kb_id="kb-india-north",
        ondc_seller_id="seller-123",
        ondc_api_key="test-api-key",
        ondc_bpp_id="bpp-123",
        monthly_catalog_quota=1000,
        storage_quota_gb=100,
        api_rate_limit=100,
        contact_email="contact@test.com"
    )


def test_get_tenant_configuration_success(tenant_service, mock_dynamodb, sample_tenant_config):
    """Test successful tenant configuration retrieval"""
    # Arrange
    mock_dynamodb.get_item.return_value = {
        'Item': {
            'tenant_id': 'tenant-123',
            'tenant_name': 'Test Artisan Cooperative',
            'default_language': 'hi',
            'supported_languages': ['hi', 'ta'],
            'cultural_kb_id': 'kb-india-north',
            'ondc_seller_id': 'seller-123',
            'ondc_api_key': 'test-api-key',
            'ondc_bpp_id': 'bpp-123',
            'monthly_catalog_quota': 1000,
            'storage_quota_gb': 100,
            'api_rate_limit': 100,
            'contact_email': 'contact@test.com',
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
            'is_active': True
        }
    }
    
    # Act
    result = tenant_service.get_tenant_configuration('tenant-123')
    
    # Assert
    assert result is not None
    assert result.tenant_id == 'tenant-123'
    assert result.tenant_name == 'Test Artisan Cooperative'
    assert result.default_language == LanguageCode.HINDI
    mock_dynamodb.get_item.assert_called_once()


def test_get_tenant_configuration_not_found(tenant_service, mock_dynamodb):
    """Test tenant configuration not found"""
    # Arrange
    mock_dynamodb.get_item.return_value = {}
    
    # Act
    result = tenant_service.get_tenant_configuration('nonexistent')
    
    # Assert
    assert result is None
    mock_dynamodb.get_item.assert_called_once()


def test_create_tenant_configuration_success(tenant_service, mock_dynamodb, sample_tenant_config):
    """Test successful tenant configuration creation"""
    # Arrange
    mock_dynamodb.put_item.return_value = {}
    
    # Act
    result = tenant_service.create_tenant_configuration(sample_tenant_config)
    
    # Assert
    assert result['status'] == 'created'
    assert result['tenant_id'] == 'tenant-123'
    mock_dynamodb.put_item.assert_called_once()


def test_update_tenant_configuration_success(tenant_service, mock_dynamodb):
    """Test successful tenant configuration update"""
    # Arrange
    mock_dynamodb.update_item.return_value = {}
    updates = {
        'tenant_name': 'Updated Cooperative',
        'monthly_catalog_quota': 2000
    }
    
    # Act
    result = tenant_service.update_tenant_configuration('tenant-123', updates)
    
    # Assert
    assert result['status'] == 'updated'
    assert result['tenant_id'] == 'tenant-123'
    assert 'tenant_name' in result['updated_fields']
    mock_dynamodb.update_item.assert_called_once()


def test_check_tenant_quota_catalog(tenant_service, mock_dynamodb, sample_tenant_config):
    """Test checking catalog quota"""
    # Arrange
    mock_dynamodb.get_item.return_value = {
        'Item': {
            'tenant_id': 'tenant-123',
            'tenant_name': 'Test Artisan Cooperative',
            'default_language': 'hi',
            'supported_languages': ['hi', 'ta'],
            'cultural_kb_id': 'kb-india-north',
            'ondc_seller_id': 'seller-123',
            'ondc_api_key': 'test-api-key',
            'ondc_bpp_id': 'bpp-123',
            'monthly_catalog_quota': 1000,
            'storage_quota_gb': 100,
            'api_rate_limit': 100,
            'contact_email': 'contact@test.com',
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
            'is_active': True
        }
    }
    
    # Act
    result = tenant_service.check_tenant_quota('tenant-123', 'catalog')
    
    # Assert
    assert result['quota_type'] == 'catalog'
    assert result['limit'] == 1000
    assert result['has_quota'] is True


def test_validate_tenant_access_success(tenant_service, mock_dynamodb, sample_tenant_config):
    """Test successful tenant access validation"""
    # Arrange
    mock_dynamodb.get_item.return_value = {
        'Item': {
            'tenant_id': 'tenant-123',
            'tenant_name': 'Test Artisan Cooperative',
            'default_language': 'hi',
            'supported_languages': ['hi', 'ta'],
            'cultural_kb_id': 'kb-india-north',
            'ondc_seller_id': 'seller-123',
            'ondc_api_key': 'test-api-key',
            'ondc_bpp_id': 'bpp-123',
            'monthly_catalog_quota': 1000,
            'storage_quota_gb': 100,
            'api_rate_limit': 100,
            'contact_email': 'contact@test.com',
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
            'is_active': True
        }
    }
    
    # Act
    result = tenant_service.validate_tenant_access('tenant-123', 'artisan-456')
    
    # Assert
    assert result is True


def test_validate_tenant_access_inactive_tenant(tenant_service, mock_dynamodb):
    """Test tenant access validation with inactive tenant"""
    # Arrange
    mock_dynamodb.get_item.return_value = {
        'Item': {
            'tenant_id': 'tenant-123',
            'tenant_name': 'Test Artisan Cooperative',
            'default_language': 'hi',
            'supported_languages': ['hi', 'ta'],
            'cultural_kb_id': 'kb-india-north',
            'ondc_seller_id': 'seller-123',
            'ondc_api_key': 'test-api-key',
            'ondc_bpp_id': 'bpp-123',
            'monthly_catalog_quota': 1000,
            'storage_quota_gb': 100,
            'api_rate_limit': 100,
            'contact_email': 'contact@test.com',
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
            'is_active': False
        }
    }
    
    # Act
    result = tenant_service.validate_tenant_access('tenant-123', 'artisan-456')
    
    # Assert
    assert result is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
