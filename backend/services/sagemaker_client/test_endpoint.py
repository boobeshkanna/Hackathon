#!/usr/bin/env python3
"""
Test script for SageMaker endpoint

This script tests the deployed SageMaker endpoint with sample data.
"""
import os
import sys
import json
import base64
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.sagemaker_client.client import SagemakerClient
from services.sagemaker_client.config import SagemakerConfig


def create_test_image() -> bytes:
    """Create a simple test image"""
    from PIL import Image
    import io
    
    # Create a simple red square
    img = Image.new('RGB', (224, 224), color='red')
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG')
    return buffer.getvalue()


def create_test_audio() -> bytes:
    """Create a simple test audio"""
    import numpy as np
    import soundfile as sf
    import io
    
    # Create a simple sine wave
    sample_rate = 16000
    duration = 2  # seconds
    frequency = 440  # Hz (A4 note)
    
    t = np.linspace(0, duration, int(sample_rate * duration))
    audio = np.sin(2 * np.pi * frequency * t)
    
    buffer = io.BytesIO()
    sf.write(buffer, audio, sample_rate, format='WAV')
    buffer.seek(0)
    return buffer.read()


def test_health_check(client: SagemakerClient):
    """Test endpoint health check"""
    print("\n" + "="*50)
    print("Testing Health Check")
    print("="*50)
    
    is_healthy = client.health_check()
    
    if is_healthy:
        print("✅ Endpoint is healthy and in service")
    else:
        print("❌ Endpoint is not available")
        sys.exit(1)


def test_vision_only(client: SagemakerClient, image_bytes: bytes):
    """Test vision-only inference"""
    print("\n" + "="*50)
    print("Testing Vision-Only Inference")
    print("="*50)
    
    try:
        result = client.invoke_vision_model(image_bytes)
        
        print("\n📊 Vision Results:")
        print(f"  Category: {result.get('category', 'N/A')}")
        print(f"  Subcategory: {result.get('subcategory', 'N/A')}")
        print(f"  Colors: {', '.join(result.get('colors', []))}")
        print(f"  Materials: {', '.join(result.get('materials', []))}")
        print(f"  Confidence: {result.get('confidence', 0):.2%}")
        
        if result.get('low_confidence'):
            print("  ⚠️  Low confidence - requires manual review")
        
        print("\n✅ Vision inference successful")
        
    except Exception as e:
        print(f"\n❌ Vision inference failed: {e}")
        raise


def test_asr_only(client: SagemakerClient, audio_bytes: bytes, language: str = 'hi'):
    """Test ASR-only inference"""
    print("\n" + "="*50)
    print(f"Testing ASR-Only Inference (Language: {language})")
    print("="*50)
    
    try:
        result = client.invoke_asr_model(audio_bytes, language_code=language)
        
        print("\n🎤 ASR Results:")
        print(f"  Text: {result.get('text', 'N/A')}")
        print(f"  Language: {result.get('language', 'N/A')}")
        print(f"  Confidence: {result.get('confidence', 0):.2%}")
        
        if result.get('low_confidence'):
            print("  ⚠️  Low confidence - requires manual review")
        
        if 'segments' in result:
            print(f"\n  Segments ({len(result['segments'])}):")
            for i, segment in enumerate(result['segments'], 1):
                print(f"    {i}. [{segment['start']:.1f}s - {segment['end']:.1f}s] "
                      f"{segment['text']} (confidence: {segment['confidence']:.2%})")
        
        print("\n✅ ASR inference successful")
        
    except Exception as e:
        print(f"\n❌ ASR inference failed: {e}")
        raise


def test_combined(client: SagemakerClient, image_bytes: bytes, audio_bytes: bytes, language: str = 'hi'):
    """Test combined multimodal inference"""
    print("\n" + "="*50)
    print(f"Testing Combined Multimodal Inference (Language: {language})")
    print("="*50)
    
    try:
        result = client.invoke_combined_endpoint(
            image_bytes=image_bytes,
            audio_bytes=audio_bytes,
            language_hint=language
        )
        
        # Vision results
        if 'vision' in result:
            vision = result['vision']
            print("\n📊 Vision Results:")
            print(f"  Category: {vision.get('category', 'N/A')}")
            print(f"  Subcategory: {vision.get('subcategory', 'N/A')}")
            print(f"  Colors: {', '.join(vision.get('colors', []))}")
            print(f"  Materials: {', '.join(vision.get('materials', []))}")
            print(f"  Confidence: {vision.get('confidence', 0):.2%}")
            
            if vision.get('low_confidence'):
                print("  ⚠️  Low confidence - requires manual review")
        
        # ASR results
        if 'transcription' in result:
            transcription = result['transcription']
            print("\n🎤 ASR Results:")
            print(f"  Text: {transcription.get('text', 'N/A')}")
            print(f"  Language: {transcription.get('language', 'N/A')}")
            print(f"  Confidence: {transcription.get('confidence', 0):.2%}")
            
            if transcription.get('low_confidence'):
                print("  ⚠️  Low confidence - requires manual review")
        
        # Processing time
        print(f"\n⏱️  Processing Time: {result.get('processing_time_ms', 0)}ms")
        
        print("\n✅ Combined inference successful")
        
    except Exception as e:
        print(f"\n❌ Combined inference failed: {e}")
        raise


def main():
    parser = argparse.ArgumentParser(description='Test SageMaker endpoint')
    parser.add_argument('--endpoint', type=str, help='Endpoint name (default: from env)')
    parser.add_argument('--region', type=str, default='ap-south-1', help='AWS region')
    parser.add_argument('--image', type=str, help='Path to test image file')
    parser.add_argument('--audio', type=str, help='Path to test audio file')
    parser.add_argument('--language', type=str, default='hi', help='Language code for ASR')
    parser.add_argument('--test', type=str, choices=['health', 'vision', 'asr', 'combined', 'all'],
                       default='all', help='Test to run')
    
    args = parser.parse_args()
    
    # Get endpoint name
    endpoint_name = args.endpoint or os.getenv('SAGEMAKER_ENDPOINT_NAME')
    if not endpoint_name:
        print("❌ Error: Endpoint name not provided")
        print("   Use --endpoint or set SAGEMAKER_ENDPOINT_NAME environment variable")
        sys.exit(1)
    
    print("="*50)
    print("SageMaker Endpoint Test")
    print("="*50)
    print(f"Endpoint: {endpoint_name}")
    print(f"Region: {args.region}")
    print(f"Language: {args.language}")
    
    # Initialize client
    client = SagemakerClient(
        endpoint_name=endpoint_name,
        region=args.region
    )
    
    # Load or create test data
    if args.image:
        print(f"Loading image from: {args.image}")
        with open(args.image, 'rb') as f:
            image_bytes = f.read()
    else:
        print("Creating test image...")
        try:
            image_bytes = create_test_image()
        except ImportError:
            print("⚠️  PIL not installed, skipping image tests")
            image_bytes = None
    
    if args.audio:
        print(f"Loading audio from: {args.audio}")
        with open(args.audio, 'rb') as f:
            audio_bytes = f.read()
    else:
        print("Creating test audio...")
        try:
            audio_bytes = create_test_audio()
        except ImportError:
            print("⚠️  soundfile not installed, skipping audio tests")
            audio_bytes = None
    
    # Run tests
    try:
        if args.test in ['health', 'all']:
            test_health_check(client)
        
        if args.test in ['vision', 'all'] and image_bytes:
            test_vision_only(client, image_bytes)
        
        if args.test in ['asr', 'all'] and audio_bytes:
            test_asr_only(client, audio_bytes, args.language)
        
        if args.test in ['combined', 'all'] and image_bytes and audio_bytes:
            test_combined(client, image_bytes, audio_bytes, args.language)
        
        print("\n" + "="*50)
        print("✅ All tests completed successfully!")
        print("="*50)
        
    except Exception as e:
        print("\n" + "="*50)
        print(f"❌ Tests failed: {e}")
        print("="*50)
        sys.exit(1)


if __name__ == '__main__':
    main()
