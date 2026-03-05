"""
ONDC Update Detector - Detects catalog updates vs new entries

This module implements logic to detect whether a catalog submission is
an update to an existing entry or a new entry, and maintains version history.

Requirements: 18.1, 18.2, 18.3, 18.4
"""
import hashlib
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict

from backend.models.catalog import ExtractedAttributes, ONDCCatalogItem


logger = logging.getLogger(__name__)


@dataclass
class CatalogVersion:
    """Represents a version of a catalog entry"""
    version_number: int
    tracking_id: str
    ondc_catalog_id: str
    item_fingerprint: str
    attributes_snapshot: Dict[str, Any]
    created_at: datetime
    updated_by: str  # artisan_id
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for DynamoDB storage"""
        data = asdict(self)
        if self.created_at:
            data['created_at'] = self.created_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CatalogVersion':
        """Create from dictionary (from DynamoDB)"""
        if 'created_at' in data and data['created_at']:
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        return cls(**data)


@dataclass
class UpdateDetectionResult:
    """Result of update detection"""
    is_update: bool
    original_catalog_id: Optional[str] = None
    item_fingerprint: str = ""
    matching_attributes: List[str] = None
    version_number: int = 1
    previous_version: Optional[CatalogVersion] = None
    
    def __post_init__(self):
        if self.matching_attributes is None:
            self.matching_attributes = []


class ONDCUpdateDetector:
    """
    Detects whether a catalog submission is an update or new entry.
    
    Uses attribute fingerprinting to match existing entries and maintains
    version history in DynamoDB.
    
    Requirements: 18.1, 18.2, 18.3, 18.4
    """
    
    # Attributes used for fingerprinting (to detect duplicates/updates)
    FINGERPRINT_ATTRIBUTES = [
        'category',
        'subcategory',
        'material',
        'colors',
        'craft_technique',
        'region_of_origin'
    ]
    
    def __init__(
        self,
        dynamodb_client=None,
        catalog_table_name: str = "ondc_catalog_entries",
        version_table_name: str = "ondc_catalog_versions"
    ):
        """
        Initialize update detector.
        
        Args:
            dynamodb_client: boto3 DynamoDB client (optional, for testing)
            catalog_table_name: DynamoDB table for catalog entries
            version_table_name: DynamoDB table for version history
        """
        self.dynamodb_client = dynamodb_client
        self.catalog_table_name = catalog_table_name
        self.version_table_name = version_table_name
        
        # Initialize DynamoDB client if not provided
        if self.dynamodb_client is None:
            try:
                import boto3
                self.dynamodb_client = boto3.client('dynamodb')
            except Exception as e:
                logger.warning(f"Failed to initialize DynamoDB client: {str(e)}")
    
    def detect_update(
        self,
        extracted: ExtractedAttributes,
        tenant_id: str,
        artisan_id: str
    ) -> UpdateDetectionResult:
        """
        Detect if this is an update to an existing catalog entry.
        
        Args:
            extracted: Extracted product attributes
            tenant_id: Tenant ID
            artisan_id: Artisan ID
        
        Returns:
            UpdateDetectionResult: Detection result
        
        Requirements: 18.1
        """
        # Generate fingerprint for this item
        fingerprint = self.generate_fingerprint(extracted)
        
        logger.info(
            f"Detecting update: tenant_id={tenant_id}, artisan_id={artisan_id}, "
            f"fingerprint={fingerprint}"
        )
        
        # Search for existing entry with matching fingerprint
        existing_entry = self._find_existing_entry(fingerprint, tenant_id, artisan_id)
        
        if existing_entry:
            # This is an update
            logger.info(
                f"Update detected: fingerprint={fingerprint}, "
                f"original_catalog_id={existing_entry['ondc_catalog_id']}"
            )
            
            # Get version history
            versions = self._get_version_history(existing_entry['ondc_catalog_id'])
            latest_version = versions[0] if versions else None
            next_version = (latest_version.version_number + 1) if latest_version else 2
            
            return UpdateDetectionResult(
                is_update=True,
                original_catalog_id=existing_entry['ondc_catalog_id'],
                item_fingerprint=fingerprint,
                matching_attributes=self.FINGERPRINT_ATTRIBUTES,
                version_number=next_version,
                previous_version=latest_version
            )
        else:
            # This is a new entry
            logger.info(f"New entry detected: fingerprint={fingerprint}")
            
            return UpdateDetectionResult(
                is_update=False,
                item_fingerprint=fingerprint,
                version_number=1
            )
    
    def generate_fingerprint(self, extracted: ExtractedAttributes) -> str:
        """
        Generate a fingerprint hash from core attributes.
        
        This fingerprint is used to detect duplicate/updated entries.
        
        Args:
            extracted: Extracted product attributes
        
        Returns:
            str: Fingerprint hash
        
        Requirements: 18.1
        """
        # Build fingerprint components
        components = []
        
        for attr in self.FINGERPRINT_ATTRIBUTES:
            value = getattr(extracted, attr, None)
            
            if value is None:
                components.append('')
            elif isinstance(value, list):
                # Sort lists for consistent hashing
                components.append(','.join(sorted(str(v) for v in value)))
            else:
                components.append(str(value))
        
        # Create hash input
        hash_input = '|'.join(components)
        
        # Generate SHA-256 hash
        fingerprint = hashlib.sha256(hash_input.encode('utf-8')).hexdigest()[:16]
        
        return fingerprint
    
    def save_catalog_entry(
        self,
        tracking_id: str,
        tenant_id: str,
        artisan_id: str,
        item: ONDCCatalogItem,
        extracted: ExtractedAttributes,
        ondc_catalog_id: str,
        fingerprint: str,
        is_update: bool = False,
        original_catalog_id: Optional[str] = None
    ):
        """
        Save catalog entry to DynamoDB.
        
        Args:
            tracking_id: Tracking ID
            tenant_id: Tenant ID
            artisan_id: Artisan ID
            item: ONDC catalog item
            extracted: Extracted attributes
            ondc_catalog_id: ONDC-assigned catalog ID
            fingerprint: Item fingerprint
            is_update: Whether this is an update
            original_catalog_id: Original catalog ID (for updates)
        
        Requirements: 18.4
        """
        if not self.dynamodb_client:
            logger.warning("DynamoDB client not available, skipping save")
            return
        
        # Use original catalog ID if this is an update
        catalog_id = original_catalog_id if is_update else ondc_catalog_id
        
        entry = {
            'ondc_catalog_id': {'S': catalog_id},
            'tenant_id': {'S': tenant_id},
            'artisan_id': {'S': artisan_id},
            'tracking_id': {'S': tracking_id},
            'item_fingerprint': {'S': fingerprint},
            'item_id': {'S': item.id},
            'category': {'S': extracted.category or ''},
            'subcategory': {'S': extracted.subcategory or ''},
            'material': {'S': ','.join(extracted.material) if extracted.material else ''},
            'colors': {'S': ','.join(extracted.colors) if extracted.colors else ''},
            'craft_technique': {'S': extracted.craft_technique or ''},
            'region_of_origin': {'S': extracted.region_of_origin or ''},
            'created_at': {'S': datetime.utcnow().isoformat()},
            'updated_at': {'S': datetime.utcnow().isoformat()},
            'is_active': {'BOOL': True}
        }
        
        try:
            self.dynamodb_client.put_item(
                TableName=self.catalog_table_name,
                Item=entry
            )
            logger.info(f"Saved catalog entry: catalog_id={catalog_id}")
        except Exception as e:
            logger.error(f"Failed to save catalog entry: {str(e)}")
    
    def save_version(
        self,
        ondc_catalog_id: str,
        tracking_id: str,
        artisan_id: str,
        version_number: int,
        fingerprint: str,
        extracted: ExtractedAttributes
    ) -> CatalogVersion:
        """
        Save a version to version history.
        
        Args:
            ondc_catalog_id: ONDC catalog ID
            tracking_id: Tracking ID
            artisan_id: Artisan ID
            version_number: Version number
            fingerprint: Item fingerprint
            extracted: Extracted attributes
        
        Returns:
            CatalogVersion: Created version
        
        Requirements: 18.3
        """
        version = CatalogVersion(
            version_number=version_number,
            tracking_id=tracking_id,
            ondc_catalog_id=ondc_catalog_id,
            item_fingerprint=fingerprint,
            attributes_snapshot={
                'category': extracted.category,
                'subcategory': extracted.subcategory,
                'material': extracted.material,
                'colors': extracted.colors,
                'dimensions': extracted.dimensions,
                'weight': extracted.weight,
                'price': extracted.price,
                'short_description': extracted.short_description,
                'long_description': extracted.long_description,
                'craft_technique': extracted.craft_technique,
                'region_of_origin': extracted.region_of_origin,
                'csis': [
                    {
                        'vernacular_term': csi.vernacular_term,
                        'transliteration': csi.transliteration,
                        'english_context': csi.english_context,
                        'cultural_significance': csi.cultural_significance
                    }
                    for csi in extracted.csis
                ] if extracted.csis else []
            },
            created_at=datetime.utcnow(),
            updated_by=artisan_id
        )
        
        if self.dynamodb_client:
            try:
                self._persist_version(version)
                logger.info(
                    f"Saved version: catalog_id={ondc_catalog_id}, "
                    f"version={version_number}"
                )
            except Exception as e:
                logger.error(f"Failed to save version: {str(e)}")
        
        return version
    
    def get_version_history(
        self,
        ondc_catalog_id: str,
        limit: int = 10
    ) -> List[CatalogVersion]:
        """
        Retrieve version history for a catalog entry.
        
        Args:
            ondc_catalog_id: ONDC catalog ID
            limit: Maximum number of versions to retrieve
        
        Returns:
            List[CatalogVersion]: Version history (newest first)
        
        Requirements: 18.3
        """
        return self._get_version_history(ondc_catalog_id, limit)
    
    def _find_existing_entry(
        self,
        fingerprint: str,
        tenant_id: str,
        artisan_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Find existing catalog entry by fingerprint.
        
        Args:
            fingerprint: Item fingerprint
            tenant_id: Tenant ID
            artisan_id: Artisan ID
        
        Returns:
            Optional[Dict]: Existing entry if found
        """
        if not self.dynamodb_client:
            return None
        
        try:
            # Query by fingerprint and tenant_id
            response = self.dynamodb_client.query(
                TableName=self.catalog_table_name,
                IndexName='fingerprint-tenant-index',
                KeyConditionExpression='item_fingerprint = :fp AND tenant_id = :tid',
                FilterExpression='artisan_id = :aid AND is_active = :active',
                ExpressionAttributeValues={
                    ':fp': {'S': fingerprint},
                    ':tid': {'S': tenant_id},
                    ':aid': {'S': artisan_id},
                    ':active': {'BOOL': True}
                },
                Limit=1
            )
            
            items = response.get('Items', [])
            if items:
                return self._dynamodb_item_to_dict(items[0])
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to find existing entry: {str(e)}")
            return None
    
    def _get_version_history(
        self,
        ondc_catalog_id: str,
        limit: int = 10
    ) -> List[CatalogVersion]:
        """Retrieve version history from DynamoDB"""
        if not self.dynamodb_client:
            return []
        
        try:
            response = self.dynamodb_client.query(
                TableName=self.version_table_name,
                KeyConditionExpression='ondc_catalog_id = :cid',
                ExpressionAttributeValues={
                    ':cid': {'S': ondc_catalog_id}
                },
                ScanIndexForward=False,  # Sort by version descending
                Limit=limit
            )
            
            versions = []
            for item in response.get('Items', []):
                version_dict = self._dynamodb_item_to_dict(item)
                versions.append(CatalogVersion.from_dict(version_dict))
            
            return versions
            
        except Exception as e:
            logger.error(f"Failed to retrieve version history: {str(e)}")
            return []
    
    def _persist_version(self, version: CatalogVersion):
        """Persist version to DynamoDB"""
        if not self.dynamodb_client:
            return
        
        item = self._dict_to_dynamodb_item(version.to_dict())
        
        self.dynamodb_client.put_item(
            TableName=self.version_table_name,
            Item=item
        )
    
    @staticmethod
    def _dict_to_dynamodb_item(data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Python dict to DynamoDB item format"""
        item = {}
        for key, value in data.items():
            if value is None:
                continue
            elif isinstance(value, str):
                item[key] = {'S': value}
            elif isinstance(value, int):
                item[key] = {'N': str(value)}
            elif isinstance(value, float):
                item[key] = {'N': str(value)}
            elif isinstance(value, bool):
                item[key] = {'BOOL': value}
            elif isinstance(value, dict):
                item[key] = {'M': ONDCUpdateDetector._dict_to_dynamodb_item(value)}
            elif isinstance(value, list):
                item[key] = {'L': [ONDCUpdateDetector._dict_to_dynamodb_item({'v': v})['v'] for v in value]}
        return item
    
    @staticmethod
    def _dynamodb_item_to_dict(item: Dict[str, Any]) -> Dict[str, Any]:
        """Convert DynamoDB item format to Python dict"""
        data = {}
        for key, value in item.items():
            if 'S' in value:
                data[key] = value['S']
            elif 'N' in value:
                try:
                    data[key] = int(value['N'])
                except ValueError:
                    data[key] = float(value['N'])
            elif 'BOOL' in value:
                data[key] = value['BOOL']
            elif 'M' in value:
                data[key] = ONDCUpdateDetector._dynamodb_item_to_dict(value['M'])
            elif 'L' in value:
                data[key] = [ONDCUpdateDetector._dynamodb_item_to_dict({'v': v})['v'] for v in value['L']]
            elif 'NULL' in value:
                data[key] = None
        return data


def create_catalog_tables(
    dynamodb_client,
    catalog_table_name: str = "ondc_catalog_entries",
    version_table_name: str = "ondc_catalog_versions"
):
    """
    Create DynamoDB tables for catalog entries and version history.
    
    Args:
        dynamodb_client: boto3 DynamoDB client
        catalog_table_name: Catalog entries table name
        version_table_name: Version history table name
    """
    # Create catalog entries table
    try:
        dynamodb_client.create_table(
            TableName=catalog_table_name,
            KeySchema=[
                {'AttributeName': 'ondc_catalog_id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'ondc_catalog_id', 'AttributeType': 'S'},
                {'AttributeName': 'item_fingerprint', 'AttributeType': 'S'},
                {'AttributeName': 'tenant_id', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'fingerprint-tenant-index',
                    'KeySchema': [
                        {'AttributeName': 'item_fingerprint', 'KeyType': 'HASH'},
                        {'AttributeName': 'tenant_id', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 10,
                'WriteCapacityUnits': 10
            }
        )
        logger.info(f"Created catalog entries table: {catalog_table_name}")
    except Exception as e:
        logger.error(f"Failed to create catalog entries table: {str(e)}")
    
    # Create version history table
    try:
        dynamodb_client.create_table(
            TableName=version_table_name,
            KeySchema=[
                {'AttributeName': 'ondc_catalog_id', 'KeyType': 'HASH'},
                {'AttributeName': 'version_number', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'ondc_catalog_id', 'AttributeType': 'S'},
                {'AttributeName': 'version_number', 'AttributeType': 'N'}
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        logger.info(f"Created version history table: {version_table_name}")
    except Exception as e:
        logger.error(f"Failed to create version history table: {str(e)}")
