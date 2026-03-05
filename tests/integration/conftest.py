"""
Pytest configuration for integration tests

This module provides shared fixtures and configuration for integration tests.
"""

import pytest
import os
import subprocess
import time
import requests
from typing import Generator
from tests.integration.test_environment_setup import AWSIntegrationTestEnvironment


@pytest.fixture(scope="session")
def mock_ondc_server() -> Generator[str, None, None]:
    """
    Start mock ONDC server for integration tests
    
    Yields:
        Base URL of the mock ONDC server
    """
    # Start mock server in background
    process = subprocess.Popen(
        ["python", "tests/integration/mock_ondc_server.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for server to start
    base_url = "http://localhost:8080"
    max_retries = 30
    for i in range(max_retries):
        try:
            response = requests.get(f"{base_url}/health", timeout=1)
            if response.status_code == 200:
                print(f"Mock ONDC server started at {base_url}")
                break
        except requests.exceptions.RequestException:
            if i == max_retries - 1:
                process.kill()
                raise RuntimeError("Failed to start mock ONDC server")
            time.sleep(1)
    
    yield base_url
    
    # Cleanup: stop server
    process.terminate()
    process.wait(timeout=5)


@pytest.fixture(scope="session")
def aws_integration_env() -> Generator[dict, None, None]:
    """
    Set up AWS integration test environment
    
    Yields:
        Dictionary of AWS resource identifiers
    """
    env = AWSIntegrationTestEnvironment()
    resources = env.setup_all()
    env.seed_test_data()
    
    yield resources
    
    # Cleanup
    env.teardown_all()


@pytest.fixture(scope="function")
def clean_aws_env(aws_integration_env):
    """
    Provide clean AWS environment for each test
    
    This fixture ensures each test starts with a clean state
    """
    yield aws_integration_env
    
    # Cleanup after each test
    # Clear DynamoDB tables, S3 buckets, SQS queues
    # (Implementation would go here)


@pytest.fixture(scope="function")
def test_media_files(tmp_path):
    """
    Create test media files for integration tests
    
    Returns:
        Dictionary with paths to test image and audio files
    """
    from PIL import Image
    import numpy as np
    
    # Create test image
    image_path = tmp_path / "test_image.jpg"
    img = Image.fromarray(np.random.randint(0, 255, (800, 600, 3), dtype=np.uint8))
    img.save(image_path, "JPEG", quality=80)
    
    # Create test audio (simple WAV file)
    audio_path = tmp_path / "test_audio.wav"
    # For simplicity, create a minimal WAV file
    # In real tests, use actual audio samples
    with open(audio_path, 'wb') as f:
        # Minimal WAV header + silence
        f.write(b'RIFF' + (36).to_bytes(4, 'little') + b'WAVE')
        f.write(b'fmt ' + (16).to_bytes(4, 'little'))
        f.write((1).to_bytes(2, 'little'))  # PCM
        f.write((1).to_bytes(2, 'little'))  # Mono
        f.write((16000).to_bytes(4, 'little'))  # Sample rate
        f.write((32000).to_bytes(4, 'little'))  # Byte rate
        f.write((2).to_bytes(2, 'little'))  # Block align
        f.write((16).to_bytes(2, 'little'))  # Bits per sample
        f.write(b'data' + (0).to_bytes(4, 'little'))
    
    return {
        'image': str(image_path),
        'audio': str(audio_path)
    }


@pytest.fixture(scope="function")
def test_tenant_config():
    """
    Provide test tenant configuration
    """
    return {
        'tenant_id': 'test-tenant-001',
        'name': 'Test Artisan Cooperative',
        'language_preferences': ['hi', 'te', 'ta'],
        'ondc_seller_id': 'test-seller-001',
        'ondc_api_key': 'test-api-key',
        'quota_daily_uploads': 1000
    }


@pytest.fixture(scope="function")
def test_artisan_data():
    """
    Provide test artisan data
    """
    return {
        'artisan_id': 'test-artisan-001',
        'tenant_id': 'test-tenant-001',
        'name': 'Test Artisan',
        'language': 'hi',
        'phone': '+919876543210'
    }
