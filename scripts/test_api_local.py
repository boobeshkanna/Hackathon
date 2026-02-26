#!/usr/bin/env python3
"""
Test script for local API server
Run the local server first: uvicorn backend.lambda_functions.api_handlers.local_server:app --reload
"""
import requests
import json
import base64

BASE_URL = "http://localhost:8000"


def test_health_check():
    """Test health check endpoint"""
    print("\n=== Testing Health Check ===")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    assert response.status_code == 200


def test_submit_catalog():
    """Test catalog submission"""
    print("\n=== Testing Catalog Submission ===")
    
    # Create mock base64 data
    mock_image = base64.b64encode(b"fake_image_data").decode()
    mock_audio = base64.b64encode(b"fake_audio_data").decode()
    
    payload = {
        "tenant_id": "artisan_001",
        "language": "hi",
        "image_data": mock_image,
        "audio_data": mock_audio,
        "metadata": {
            "location": "Jaipur",
            "category_hint": "handicraft"
        }
    }
    
    response = requests.post(f"{BASE_URL}/catalog", json=payload)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    assert response.status_code == 202
    
    return response.json()["catalog_id"]


def test_get_catalog_status(catalog_id):
    """Test getting catalog status"""
    print(f"\n=== Testing Get Catalog Status ===")
    response = requests.get(f"{BASE_URL}/catalog/{catalog_id}")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    assert response.status_code == 200


def test_list_catalogs():
    """Test listing catalogs"""
    print("\n=== Testing List Catalogs ===")
    response = requests.get(f"{BASE_URL}/catalog?limit=10")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    assert response.status_code == 200


def test_validation_error():
    """Test validation error handling"""
    print("\n=== Testing Validation Error ===")
    
    # Missing required field
    payload = {
        "language": "hi"
    }
    
    response = requests.post(f"{BASE_URL}/catalog", json=payload)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    assert response.status_code == 422  # FastAPI validation error


if __name__ == "__main__":
    print("=" * 60)
    print("Testing Vernacular Artisan Catalog API")
    print("=" * 60)
    
    try:
        test_health_check()
        catalog_id = test_submit_catalog()
        test_get_catalog_status(catalog_id)
        test_list_catalogs()
        test_validation_error()
        
        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to server")
        print("Make sure the server is running:")
        print("uvicorn backend.lambda_functions.api_handlers.local_server:app --reload")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
