"""
ONDC Audit Logger - Logs all submission attempts to DynamoDB

This module implements comprehensive audit logging for ONDC catalog submissions,
including timestamps, response codes, error messages, and catalog IDs.

Requirements: 9.4, 9.5
"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from enum import Enum

from backend.services.ondc_gateway.api_client import ONDCResponse


logger = logging.getLogger(__name__)


class SubmissionStatus(str, Enum):
    """Status of submission attempt"""
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"
    EXHAUSTED = "exhausted"


@dataclass
class AuditLogEntry:
    """Represents a single audit log entry for ONDC submission"""
    tracking_id: str
    tenant_id: str
    artisan_id: str
    idempotency_key: str
    attempt_number: int
    
    # Submission details
    submission_type: str  # "create" or "update"
    item_id: str
    original_catalog_id: Optional[str] = None
    
    # Response details
    status: SubmissionStatus = SubmissionStatus.FAILED
    http_status_code: Optional[int] = None
    ondc_catalog_id: Optional[str] = None
    ondc_request_id: Optional[str] = None
    
    # Error details
    error_message: Optional[str] = None
    error_category: Optional[str] = None
    is_retryable: bool = False
    
    # Timing
    timestamp: datetime = None
    response_time_ms: Optional[int] = None
    
    # Metadata
    api_endpoint: Optional[str] = None
    request_payload_size: Optional[int] = None
    response_payload_size: Optional[int] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for DynamoDB storage"""
        data = asdict(self)
        # Convert datetime to ISO string
        if self.timestamp:
            data['timestamp'] = self.timestamp.isoformat()
        # Convert enums to strings
        data['status'] = self.status.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AuditLogEntry':
        """Create from dictionary (from DynamoDB)"""
        # Convert ISO string back to datetime
        if 'timestamp' in data and data['timestamp']:
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        # Convert status string to enum
        if 'status' in data:
            data['status'] = SubmissionStatus(data['status'])
        return cls(**data)


class ONDCAuditLogger:
    """
    Audit logger for ONDC catalog submissions.
    
    Logs all submission attempts with comprehensive details to DynamoDB.
    
    Requirements: 9.4, 9.5
    """
    
    def __init__(
        self,
        dynamodb_client=None,
        table_name: str = "ondc_submission_audit_log"
    ):
        """
        Initialize audit logger.
        
        Args:
            dynamodb_client: boto3 DynamoDB client (optional, for testing)
            table_name: DynamoDB table name for audit logs
        """
        self.dynamodb_client = dynamodb_client
        self.table_name = table_name
        
        # Initialize DynamoDB client if not provided
        if self.dynamodb_client is None:
            try:
                import boto3
                self.dynamodb_client = boto3.client('dynamodb')
            except Exception as e:
                logger.warning(f"Failed to initialize DynamoDB client: {str(e)}")
    
    def log_submission_attempt(
        self,
        tracking_id: str,
        tenant_id: str,
        artisan_id: str,
        idempotency_key: str,
        attempt_number: int,
        submission_type: str,
        item_id: str,
        response: Optional[ONDCResponse] = None,
        error: Optional[Exception] = None,
        error_category: Optional[str] = None,
        original_catalog_id: Optional[str] = None,
        response_time_ms: Optional[int] = None,
        api_endpoint: Optional[str] = None
    ) -> AuditLogEntry:
        """
        Log a submission attempt to DynamoDB.
        
        Args:
            tracking_id: Tracking ID
            tenant_id: Tenant ID
            artisan_id: Artisan ID
            idempotency_key: Idempotency key
            attempt_number: Attempt number (1-indexed)
            submission_type: "create" or "update"
            item_id: Item ID
            response: ONDC response (if available)
            error: Exception (if failed)
            error_category: Error category
            original_catalog_id: Original catalog ID (for updates)
            response_time_ms: Response time in milliseconds
            api_endpoint: API endpoint called
        
        Returns:
            AuditLogEntry: Created audit log entry
        
        Requirements: 9.4, 9.5
        """
        # Determine status
        if response and response.is_success():
            status = SubmissionStatus.SUCCESS
        elif error_category == "retryable":
            status = SubmissionStatus.RETRYING
        elif error_category in ["permanent", "authentication", "validation"]:
            status = SubmissionStatus.EXHAUSTED
        else:
            status = SubmissionStatus.FAILED
        
        # Create audit log entry
        entry = AuditLogEntry(
            tracking_id=tracking_id,
            tenant_id=tenant_id,
            artisan_id=artisan_id,
            idempotency_key=idempotency_key,
            attempt_number=attempt_number,
            submission_type=submission_type,
            item_id=item_id,
            original_catalog_id=original_catalog_id,
            status=status,
            http_status_code=response.status_code if response else None,
            ondc_catalog_id=response.catalog_id if response else None,
            ondc_request_id=response.request_id if response else None,
            error_message=str(error) if error else None,
            error_category=error_category,
            is_retryable=error_category == "retryable" if error_category else False,
            response_time_ms=response_time_ms,
            api_endpoint=api_endpoint
        )
        
        # Persist to DynamoDB
        try:
            self._persist_to_dynamodb(entry)
            logger.info(
                f"Audit log created: tracking_id={tracking_id}, "
                f"attempt={attempt_number}, status={status}, "
                f"catalog_id={entry.ondc_catalog_id}"
            )
        except Exception as e:
            logger.error(f"Failed to persist audit log: {str(e)}")
        
        return entry
    
    def log_success(
        self,
        tracking_id: str,
        tenant_id: str,
        artisan_id: str,
        idempotency_key: str,
        attempt_number: int,
        submission_type: str,
        item_id: str,
        response: ONDCResponse,
        response_time_ms: Optional[int] = None,
        api_endpoint: Optional[str] = None,
        original_catalog_id: Optional[str] = None
    ) -> AuditLogEntry:
        """
        Log a successful submission.
        
        Requirements: 9.4, 9.5
        """
        return self.log_submission_attempt(
            tracking_id=tracking_id,
            tenant_id=tenant_id,
            artisan_id=artisan_id,
            idempotency_key=idempotency_key,
            attempt_number=attempt_number,
            submission_type=submission_type,
            item_id=item_id,
            response=response,
            original_catalog_id=original_catalog_id,
            response_time_ms=response_time_ms,
            api_endpoint=api_endpoint
        )
    
    def log_failure(
        self,
        tracking_id: str,
        tenant_id: str,
        artisan_id: str,
        idempotency_key: str,
        attempt_number: int,
        submission_type: str,
        item_id: str,
        error: Exception,
        error_category: str,
        response: Optional[ONDCResponse] = None,
        response_time_ms: Optional[int] = None,
        api_endpoint: Optional[str] = None,
        original_catalog_id: Optional[str] = None
    ) -> AuditLogEntry:
        """
        Log a failed submission.
        
        Requirements: 9.4
        """
        return self.log_submission_attempt(
            tracking_id=tracking_id,
            tenant_id=tenant_id,
            artisan_id=artisan_id,
            idempotency_key=idempotency_key,
            attempt_number=attempt_number,
            submission_type=submission_type,
            item_id=item_id,
            response=response,
            error=error,
            error_category=error_category,
            original_catalog_id=original_catalog_id,
            response_time_ms=response_time_ms,
            api_endpoint=api_endpoint
        )
    
    def get_submission_history(
        self,
        tracking_id: str,
        limit: int = 10
    ) -> List[AuditLogEntry]:
        """
        Retrieve submission history for a tracking ID.
        
        Args:
            tracking_id: Tracking ID
            limit: Maximum number of entries to retrieve
        
        Returns:
            List[AuditLogEntry]: Audit log entries
        """
        if not self.dynamodb_client:
            logger.warning("DynamoDB client not available")
            return []
        
        try:
            response = self.dynamodb_client.query(
                TableName=self.table_name,
                KeyConditionExpression='tracking_id = :tid',
                ExpressionAttributeValues={
                    ':tid': {'S': tracking_id}
                },
                ScanIndexForward=False,  # Sort by timestamp descending
                Limit=limit
            )
            
            entries = []
            for item in response.get('Items', []):
                # Convert DynamoDB item to dict
                entry_dict = self._dynamodb_item_to_dict(item)
                entries.append(AuditLogEntry.from_dict(entry_dict))
            
            return entries
            
        except Exception as e:
            logger.error(f"Failed to retrieve submission history: {str(e)}")
            return []
    
    def get_catalog_id(self, tracking_id: str) -> Optional[str]:
        """
        Retrieve the ONDC catalog ID for a tracking ID.
        
        Args:
            tracking_id: Tracking ID
        
        Returns:
            Optional[str]: ONDC catalog ID if found
        
        Requirements: 9.5
        """
        history = self.get_submission_history(tracking_id, limit=1)
        
        for entry in history:
            if entry.status == SubmissionStatus.SUCCESS and entry.ondc_catalog_id:
                return entry.ondc_catalog_id
        
        return None
    
    def _persist_to_dynamodb(self, entry: AuditLogEntry):
        """
        Persist audit log entry to DynamoDB.
        
        Args:
            entry: Audit log entry to persist
        """
        if not self.dynamodb_client:
            logger.warning("DynamoDB client not available, skipping persistence")
            return
        
        # Convert entry to DynamoDB item
        item = self._dict_to_dynamodb_item(entry.to_dict())
        
        # Add composite sort key (timestamp + attempt_number)
        sort_key = f"{entry.timestamp.isoformat()}#{entry.attempt_number:03d}"
        item['sort_key'] = {'S': sort_key}
        
        # Put item to DynamoDB
        self.dynamodb_client.put_item(
            TableName=self.table_name,
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
                item[key] = {'M': ONDCAuditLogger._dict_to_dynamodb_item(value)}
            elif isinstance(value, list):
                item[key] = {'L': [ONDCAuditLogger._dict_to_dynamodb_item({'v': v})['v'] for v in value]}
        return item
    
    @staticmethod
    def _dynamodb_item_to_dict(item: Dict[str, Any]) -> Dict[str, Any]:
        """Convert DynamoDB item format to Python dict"""
        data = {}
        for key, value in item.items():
            if 'S' in value:
                data[key] = value['S']
            elif 'N' in value:
                # Try to convert to int, fallback to float
                try:
                    data[key] = int(value['N'])
                except ValueError:
                    data[key] = float(value['N'])
            elif 'BOOL' in value:
                data[key] = value['BOOL']
            elif 'M' in value:
                data[key] = ONDCAuditLogger._dynamodb_item_to_dict(value['M'])
            elif 'L' in value:
                data[key] = [ONDCAuditLogger._dynamodb_item_to_dict({'v': v})['v'] for v in value['L']]
            elif 'NULL' in value:
                data[key] = None
        return data


def create_audit_log_table(dynamodb_client, table_name: str = "ondc_submission_audit_log"):
    """
    Create DynamoDB table for audit logs.
    
    Args:
        dynamodb_client: boto3 DynamoDB client
        table_name: Table name
    """
    try:
        dynamodb_client.create_table(
            TableName=table_name,
            KeySchema=[
                {'AttributeName': 'tracking_id', 'KeyType': 'HASH'},  # Partition key
                {'AttributeName': 'sort_key', 'KeyType': 'RANGE'}  # Sort key (timestamp#attempt)
            ],
            AttributeDefinitions=[
                {'AttributeName': 'tracking_id', 'AttributeType': 'S'},
                {'AttributeName': 'sort_key', 'AttributeType': 'S'},
                {'AttributeName': 'tenant_id', 'AttributeType': 'S'},
                {'AttributeName': 'timestamp', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'tenant_id-timestamp-index',
                    'KeySchema': [
                        {'AttributeName': 'tenant_id', 'KeyType': 'HASH'},
                        {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
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
        logger.info(f"Created audit log table: {table_name}")
    except Exception as e:
        logger.error(f"Failed to create audit log table: {str(e)}")
        raise
