"""
ONDC API Client - Handles catalog submission to ONDC network using Beckn protocol

This module implements the API client for submitting catalog entries to ONDC,
including authentication, request signing, and response parsing.

Requirements: 9.1, 9.3
"""
import hashlib
import hmac
import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from backend.models.catalog import ONDCCatalogItem


logger = logging.getLogger(__name__)


class ONDCAPIError(Exception):
    """Base exception for ONDC API errors"""
    pass


class ONDCAuthenticationError(ONDCAPIError):
    """Authentication/authorization errors"""
    pass


class ONDCValidationError(ONDCAPIError):
    """Validation errors from ONDC"""
    pass


class ONDCNetworkError(ONDCAPIError):
    """Network/connectivity errors"""
    pass


class ONDCResponse:
    """Represents an ONDC API response"""
    
    def __init__(
        self,
        status_code: int,
        body: Dict[str, Any],
        headers: Dict[str, str],
        request_id: Optional[str] = None
    ):
        self.status_code = status_code
        self.body = body
        self.headers = headers
        self.request_id = request_id
        self.catalog_id = self._extract_catalog_id()
    
    def _extract_catalog_id(self) -> Optional[str]:
        """Extract catalog ID from response body"""
        try:
            # ONDC returns catalog ID in message.catalog.bpp/providers[0].items[0].id
            if 'message' in self.body:
                catalog = self.body['message'].get('catalog', {})
                providers = catalog.get('bpp/providers', [])
                if providers and 'items' in providers[0]:
                    items = providers[0]['items']
                    if items:
                        return items[0].get('id')
            return None
        except (KeyError, IndexError, TypeError):
            return None
    
    def is_success(self) -> bool:
        """Check if response indicates success"""
        return 200 <= self.status_code < 300
    
    def is_retryable(self) -> bool:
        """Check if error is retryable"""
        # 5xx errors are retryable
        if self.status_code >= 500:
            return True
        
        # 429 rate limiting is retryable
        if self.status_code == 429:
            return True
        
        # Network timeouts are retryable
        if self.status_code == 408:
            return True
        
        return False
    
    def get_error_message(self) -> str:
        """Extract error message from response"""
        if 'error' in self.body:
            error = self.body['error']
            if isinstance(error, dict):
                return error.get('message', str(error))
            return str(error)
        
        if 'message' in self.body:
            return str(self.body['message'])
        
        return f"HTTP {self.status_code}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary for logging"""
        return {
            'status_code': self.status_code,
            'body': self.body,
            'request_id': self.request_id,
            'catalog_id': self.catalog_id,
            'is_success': self.is_success(),
            'is_retryable': self.is_retryable()
        }


class ONDCAPIClient:
    """
    ONDC API client for catalog submission using Beckn protocol.
    
    Requirements: 9.1, 9.3
    """
    
    # ONDC API endpoints
    DEFAULT_BASE_URL = "https://api.ondc.org/v1"
    CATALOG_SUBMISSION_PATH = "/beckn/catalog/on_search"
    CATALOG_UPDATE_PATH = "/beckn/catalog/on_update"
    
    # Request timeouts
    CONNECT_TIMEOUT = 10  # seconds
    READ_TIMEOUT = 30  # seconds
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        seller_id: Optional[str] = None,
        bpp_id: Optional[str] = None,
        signing_key: Optional[str] = None,
        max_retries: int = 0  # Retries handled by retry logic module
    ):
        """
        Initialize ONDC API client.
        
        Args:
            base_url: ONDC API base URL (defaults to production)
            api_key: ONDC API key for authentication
            seller_id: ONDC seller/provider ID
            bpp_id: ONDC BPP (Buyer Platform Provider) ID
            signing_key: Secret key for request signing
            max_retries: Maximum number of automatic retries (default 0)
        """
        self.base_url = base_url or self.DEFAULT_BASE_URL
        self.api_key = api_key
        self.seller_id = seller_id
        self.bpp_id = bpp_id
        self.signing_key = signing_key
        
        # Create session with connection pooling
        self.session = requests.Session()
        
        # Configure retry strategy (only for connection errors, not HTTP errors)
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1,
            status_forcelist=[],  # Don't retry HTTP errors automatically
            allowed_methods=["POST", "PUT"],
            raise_on_status=False
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=20)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set default headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'VernacularArtisanCatalog/1.0'
        })
        
        if self.api_key:
            self.session.headers.update({
                'Authorization': f'Bearer {self.api_key}'
            })
    
    def submit_catalog(
        self,
        item: ONDCCatalogItem,
        idempotency_key: str,
        tenant_id: str,
        tracking_id: str
    ) -> ONDCResponse:
        """
        Submit a new catalog entry to ONDC.
        
        Args:
            item: ONDC catalog item to submit
            idempotency_key: Unique idempotency key for this submission
            tenant_id: Tenant identifier
            tracking_id: Tracking ID for logging
        
        Returns:
            ONDCResponse: Response from ONDC API
        
        Raises:
            ONDCAPIError: If submission fails
        
        Requirements: 9.1, 9.3
        """
        # Build Beckn protocol payload
        payload = self._build_beckn_payload(item, is_update=False)
        
        # Add idempotency key to headers
        headers = {
            'X-Idempotency-Key': idempotency_key,
            'X-Tenant-ID': tenant_id,
            'X-Tracking-ID': tracking_id
        }
        
        # Sign request
        if self.signing_key:
            signature = self._sign_request(payload, idempotency_key)
            headers['X-Request-Signature'] = signature
        
        # Submit to ONDC
        url = f"{self.base_url}{self.CATALOG_SUBMISSION_PATH}"
        
        logger.info(
            f"Submitting catalog to ONDC: tracking_id={tracking_id}, "
            f"item_id={item.id}, idempotency_key={idempotency_key}"
        )
        
        try:
            response = self.session.post(
                url,
                json=payload,
                headers=headers,
                timeout=(self.CONNECT_TIMEOUT, self.READ_TIMEOUT)
            )
            
            # Parse response
            ondc_response = self._parse_response(response, tracking_id)
            
            # Log response
            logger.info(
                f"ONDC submission response: tracking_id={tracking_id}, "
                f"status={ondc_response.status_code}, "
                f"catalog_id={ondc_response.catalog_id}, "
                f"retryable={ondc_response.is_retryable()}"
            )
            
            return ondc_response
            
        except requests.exceptions.Timeout as e:
            logger.error(f"ONDC API timeout: tracking_id={tracking_id}, error={str(e)}")
            raise ONDCNetworkError(f"Request timeout: {str(e)}")
        
        except requests.exceptions.ConnectionError as e:
            logger.error(f"ONDC API connection error: tracking_id={tracking_id}, error={str(e)}")
            raise ONDCNetworkError(f"Connection error: {str(e)}")
        
        except requests.exceptions.RequestException as e:
            logger.error(f"ONDC API request error: tracking_id={tracking_id}, error={str(e)}")
            raise ONDCAPIError(f"Request failed: {str(e)}")
    
    def update_catalog(
        self,
        item: ONDCCatalogItem,
        idempotency_key: str,
        tenant_id: str,
        tracking_id: str,
        original_catalog_id: str
    ) -> ONDCResponse:
        """
        Update an existing catalog entry in ONDC.
        
        Args:
            item: Updated ONDC catalog item
            idempotency_key: Unique idempotency key for this update
            tenant_id: Tenant identifier
            tracking_id: Tracking ID for logging
            original_catalog_id: Original ONDC catalog ID to update
        
        Returns:
            ONDCResponse: Response from ONDC API
        
        Raises:
            ONDCAPIError: If update fails
        
        Requirements: 18.2, 18.4
        """
        # Build Beckn protocol payload for update
        payload = self._build_beckn_payload(item, is_update=True)
        
        # Ensure item ID matches original catalog ID
        payload['message']['catalog']['bpp/providers'][0]['items'][0]['id'] = original_catalog_id
        
        # Add idempotency key to headers
        headers = {
            'X-Idempotency-Key': idempotency_key,
            'X-Tenant-ID': tenant_id,
            'X-Tracking-ID': tracking_id,
            'X-Original-Catalog-ID': original_catalog_id
        }
        
        # Sign request
        if self.signing_key:
            signature = self._sign_request(payload, idempotency_key)
            headers['X-Request-Signature'] = signature
        
        # Submit update to ONDC
        url = f"{self.base_url}{self.CATALOG_UPDATE_PATH}"
        
        logger.info(
            f"Updating catalog in ONDC: tracking_id={tracking_id}, "
            f"original_catalog_id={original_catalog_id}, idempotency_key={idempotency_key}"
        )
        
        try:
            response = self.session.post(
                url,
                json=payload,
                headers=headers,
                timeout=(self.CONNECT_TIMEOUT, self.READ_TIMEOUT)
            )
            
            # Parse response
            ondc_response = self._parse_response(response, tracking_id)
            
            # Log response
            logger.info(
                f"ONDC update response: tracking_id={tracking_id}, "
                f"status={ondc_response.status_code}, "
                f"catalog_id={ondc_response.catalog_id}"
            )
            
            return ondc_response
            
        except requests.exceptions.RequestException as e:
            logger.error(f"ONDC API update error: tracking_id={tracking_id}, error={str(e)}")
            raise ONDCAPIError(f"Update failed: {str(e)}")
    
    def _build_beckn_payload(self, item: ONDCCatalogItem, is_update: bool = False) -> Dict[str, Any]:
        """
        Build Beckn protocol payload for ONDC submission.
        
        Args:
            item: ONDC catalog item
            is_update: Whether this is an update operation
        
        Returns:
            Dict: Beckn protocol compliant payload
        """
        action = "on_update" if is_update else "on_search"
        
        payload = {
            "context": {
                "domain": "retail",
                "country": "IND",
                "action": action,
                "bap_id": "buyer-app-id",  # This would come from config
                "bpp_id": self.bpp_id or "seller-app-id",
                "transaction_id": f"txn_{int(time.time())}",
                "message_id": f"msg_{int(time.time())}",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            },
            "message": {
                "catalog": {
                    "bpp/providers": [{
                        "id": self.seller_id or "provider-id",
                        "items": [{
                            "id": item.id,
                            "descriptor": {
                                "name": item.descriptor.name,
                                "short_desc": item.descriptor.short_desc,
                                "long_desc": item.descriptor.long_desc,
                                "images": item.descriptor.images
                            },
                            "price": {
                                "currency": item.price.currency,
                                "value": item.price.value
                            },
                            "category_id": item.category_id,
                            "tags": item.tags
                        }]
                    }]
                }
            }
        }
        
        # Add optional fields if present
        if item.descriptor.audio:
            payload["message"]["catalog"]["bpp/providers"][0]["items"][0]["descriptor"]["audio"] = item.descriptor.audio
        
        if item.descriptor.video:
            payload["message"]["catalog"]["bpp/providers"][0]["items"][0]["descriptor"]["video"] = item.descriptor.video
        
        if item.fulfillment_id:
            payload["message"]["catalog"]["bpp/providers"][0]["items"][0]["fulfillment_id"] = item.fulfillment_id
        
        if item.location_id:
            payload["message"]["catalog"]["bpp/providers"][0]["items"][0]["location_id"] = item.location_id
        
        return payload
    
    def _sign_request(self, payload: Dict[str, Any], idempotency_key: str) -> str:
        """
        Sign request using HMAC-SHA256.
        
        Args:
            payload: Request payload
            idempotency_key: Idempotency key
        
        Returns:
            str: Request signature
        """
        # Create signing string: idempotency_key + payload
        payload_str = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        signing_string = f"{idempotency_key}:{payload_str}"
        
        # Generate HMAC-SHA256 signature
        signature = hmac.new(
            self.signing_key.encode('utf-8'),
            signing_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def _parse_response(self, response: requests.Response, tracking_id: str) -> ONDCResponse:
        """
        Parse HTTP response into ONDCResponse.
        
        Args:
            response: HTTP response
            tracking_id: Tracking ID for logging
        
        Returns:
            ONDCResponse: Parsed response
        
        Raises:
            ONDCAPIError: If response parsing fails
        """
        try:
            body = response.json()
        except ValueError:
            # Response is not JSON
            body = {
                'error': {
                    'message': f'Invalid JSON response: {response.text[:200]}'
                }
            }
        
        # Extract request ID from headers
        request_id = response.headers.get('X-Request-ID') or response.headers.get('X-Correlation-ID')
        
        ondc_response = ONDCResponse(
            status_code=response.status_code,
            body=body,
            headers=dict(response.headers),
            request_id=request_id
        )
        
        # Handle specific error cases
        if response.status_code == 401 or response.status_code == 403:
            error_msg = ondc_response.get_error_message()
            logger.error(f"ONDC authentication error: tracking_id={tracking_id}, error={error_msg}")
            raise ONDCAuthenticationError(error_msg)
        
        if response.status_code == 400 and 'validation' in str(body).lower():
            error_msg = ondc_response.get_error_message()
            logger.warning(f"ONDC validation error: tracking_id={tracking_id}, error={error_msg}")
            raise ONDCValidationError(error_msg)
        
        return ondc_response
    
    def close(self):
        """Close the HTTP session"""
        self.session.close()
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
