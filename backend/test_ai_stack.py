#!/usr/bin/env python3
"""
Test script for AI Stack

Run this locally to test the AI services before deploying to Lambda.
"""
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from services.ai_orchestrator import AIOrchestrator


def test_image_only():
    """Test with image only"""
    print("\n" + "="*60)
    print("Testing Image-Only Processing")
    print("="*60)
    
    # Initialize orchestrator
    orchestrator = AIOrchestrator(
        region=os.getenv('AWS_REGION', 'us-east-1'),
        rekognition_project_arn=os.getenv('REKOGNITION_PROJECT_ARN'),
        transcribe_s3_bucket=os.getenv('TRANSCRIBE_S3_BUCKET')
    )
    
    # Load test image
    test_image_path = input("Enter path to test image (or press Enter to skip): ").strip()
    if not test_image_path:
        print("Skipping image test")
        return
    
    try:
        with open(test_image_path, 'rb') as f:
            image_bytes = f.read()
        
        print(f"\nProcessing image: {test_image_path}")
        print(f"Image size: {len(image_bytes)} bytes")
        
        # Process
        result = orchestrator.process_image_only(image_bytes)
        
        # Display results
        print("\n📊 Detection Results:")
        detection = result.get('detection', {})
        print(f"  Primary Category: {detection.get('primary_category')}")
        print(f"  Confidence: {detection.get('primary_confidence', 0):.2%}")
        print(f"  Model Type: {detection.get('model_type')}")
        
        print("\n🔍 Vision Analysis:")
        vision = result.get('vision_analysis', {})
        print(f"  Category: {vision.get('category')}")
        print(f"  Subcategory: {vision.get('subcategory')}")
        print(f"  Materials: {vision.get('materials', [])}")
        print(f"  Colors: {vision.get('colors', {})}")
        print(f"  Confidence: {vision.get('confidence', 0):.2%}")
        
        if vision.get('craftsmanship'):
            craft = vision['craftsmanship']
            print(f"\n🎨 Craftsmanship:")
            print(f"  Technique: {craft.get('technique')}")
            print(f"  Details: {craft.get('details')}")
        
        print(f"\n✅ Overall Confidence: {result.get('confidence', 0):.2%}")
        
    except FileNotFoundError:
        print(f"❌ Error: File not found: {test_image_path}")
    except Exception as e:
        print(f"❌ Error: {e}")


def test_audio_only():
    """Test with audio only"""
    print("\n" + "="*60)
    print("Testing Audio-Only Processing")
    print("="*60)
    
    # Check if S3 bucket is configured
    s3_bucket = os.getenv('TRANSCRIBE_S3_BUCKET')
    if not s3_bucket:
        print("❌ Error: TRANSCRIBE_S3_BUCKET environment variable not set")
        print("   Set it with: export TRANSCRIBE_S3_BUCKET=your-bucket-name")
        return
    
    # Initialize orchestrator
    orchestrator = AIOrchestrator(
        region=os.getenv('AWS_REGION', 'us-east-1'),
        transcribe_s3_bucket=s3_bucket
    )
    
    # Load test audio
    test_audio_path = input("Enter path to test audio file (or press Enter to skip): ").strip()
    if not test_audio_path:
        print("Skipping audio test")
        return
    
    language = input("Enter language code (hi/ta/te/mr) [default: hi]: ").strip() or 'hi'
    audio_format = input("Enter audio format (opus/mp3/wav) [default: opus]: ").strip() or 'opus'
    
    try:
        with open(test_audio_path, 'rb') as f:
            audio_bytes = f.read()
        
        print(f"\nProcessing audio: {test_audio_path}")
        print(f"Audio size: {len(audio_bytes)} bytes")
        print(f"Language: {language}")
        print(f"Format: {audio_format}")
        print("\n⏳ Transcribing... (this may take 5-10 seconds)")
        
        # Process
        result = orchestrator.process_audio_only(
            audio_bytes,
            language_code=language,
            audio_format=audio_format
        )
        
        # Display results
        print("\n🎤 Transcription Results:")
        print(f"  Text: {result.get('text')}")
        print(f"  Language: {result.get('language')}")
        print(f"  Confidence: {result.get('confidence', 0):.2%}")
        
        if result.get('segments'):
            print(f"\n  Segments ({len(result['segments'])}):")
            for i, segment in enumerate(result['segments'][:3], 1):  # Show first 3
                print(f"    {i}. [{segment['start']:.1f}s - {segment['end']:.1f}s]")
                print(f"       {segment['text']}")
                print(f"       Confidence: {segment['confidence']:.2%}")
        
        if result.get('low_confidence'):
            print("\n  ⚠️  Low confidence - may require manual review")
        
    except FileNotFoundError:
        print(f"❌ Error: File not found: {test_audio_path}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


def test_complete_pipeline():
    """Test complete pipeline with image and audio"""
    print("\n" + "="*60)
    print("Testing Complete Pipeline (Image + Audio)")
    print("="*60)
    
    # Check if S3 bucket is configured
    s3_bucket = os.getenv('TRANSCRIBE_S3_BUCKET')
    if not s3_bucket:
        print("❌ Error: TRANSCRIBE_S3_BUCKET environment variable not set")
        print("   Set it with: export TRANSCRIBE_S3_BUCKET=your-bucket-name")
        return
    
    # Initialize orchestrator
    orchestrator = AIOrchestrator(
        region=os.getenv('AWS_REGION', 'us-east-1'),
        rekognition_project_arn=os.getenv('REKOGNITION_PROJECT_ARN'),
        transcribe_s3_bucket=s3_bucket
    )
    
    # Load test files
    test_image_path = input("Enter path to test image: ").strip()
    test_audio_path = input("Enter path to test audio: ").strip()
    
    if not test_image_path or not test_audio_path:
        print("❌ Both image and audio paths are required")
        return
    
    language = input("Enter language code (hi/ta/te/mr) [default: hi]: ").strip() or 'hi'
    audio_format = input("Enter audio format (opus/mp3/wav) [default: opus]: ").strip() or 'opus'
    
    try:
        with open(test_image_path, 'rb') as f:
            image_bytes = f.read()
        
        with open(test_audio_path, 'rb') as f:
            audio_bytes = f.read()
        
        print(f"\nProcessing:")
        print(f"  Image: {test_image_path} ({len(image_bytes)} bytes)")
        print(f"  Audio: {test_audio_path} ({len(audio_bytes)} bytes)")
        print(f"  Language: {language}")
        print("\n⏳ Processing... (this may take 10-15 seconds)")
        
        # Process
        result = orchestrator.process_product(
            image_bytes=image_bytes,
            audio_bytes=audio_bytes,
            language_code=language,
            audio_format=audio_format
        )
        
        # Display results
        print("\n" + "="*60)
        print("RESULTS")
        print("="*60)
        
        print("\n📊 Detection:")
        detection = result.get('detection', {})
        print(f"  Category: {detection.get('primary_category')}")
        print(f"  Confidence: {detection.get('primary_confidence', 0):.2%}")
        
        print("\n🔍 Vision Analysis:")
        vision = result.get('vision_analysis', {})
        print(f"  Category: {vision.get('category')}")
        print(f"  Materials: {vision.get('materials', [])}")
        print(f"  Colors: {vision.get('colors', {})}")
        
        print("\n🎤 Transcription:")
        transcription = result.get('transcription', {})
        print(f"  Text: {transcription.get('text')}")
        print(f"  Confidence: {transcription.get('confidence', 0):.2%}")
        
        print("\n📝 Catalog Entry:")
        catalog = result.get('catalog_entry', {})
        print(f"  Product Name: {catalog.get('product_name')}")
        print(f"  Category: {catalog.get('category')}")
        print(f"  Short Description: {catalog.get('short_description')}")
        print(f"\n  Long Description:")
        print(f"  {catalog.get('long_description', '')[:200]}...")
        
        print(f"\n✅ Overall Status: {result.get('status')}")
        print(f"✅ Overall Confidence: {result.get('overall_confidence', 0):.2%}")
        
        if result.get('requires_manual_review'):
            print("\n⚠️  Requires manual review")
        
        # Show processing stages
        print("\n📋 Processing Stages:")
        for stage in result.get('processing_stages', []):
            status_icon = "✅" if stage['status'] == 'success' else "⚠️"
            print(f"  {status_icon} {stage['stage']}: {stage['status']}")
        
    except FileNotFoundError as e:
        print(f"❌ Error: File not found: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


def check_configuration():
    """Check if environment is configured correctly"""
    print("\n" + "="*60)
    print("Configuration Check")
    print("="*60)
    
    print("\n📋 Environment Variables:")
    
    aws_region = os.getenv('AWS_REGION', 'us-east-1')
    print(f"  AWS_REGION: {aws_region}")
    
    s3_bucket = os.getenv('TRANSCRIBE_S3_BUCKET')
    if s3_bucket:
        print(f"  ✅ TRANSCRIBE_S3_BUCKET: {s3_bucket}")
    else:
        print(f"  ⚠️  TRANSCRIBE_S3_BUCKET: Not set (required for audio)")
    
    project_arn = os.getenv('REKOGNITION_PROJECT_ARN')
    if project_arn:
        print(f"  ✅ REKOGNITION_PROJECT_ARN: {project_arn[:50]}...")
    else:
        print(f"  ℹ️  REKOGNITION_PROJECT_ARN: Not set (optional, will use standard Rekognition)")
    
    print("\n📋 AWS Credentials:")
    if os.getenv('AWS_ACCESS_KEY_ID'):
        print("  ✅ AWS credentials configured")
    else:
        print("  ⚠️  AWS credentials not found in environment")
        print("     Make sure AWS CLI is configured or credentials are set")
    
    print("\n📋 Required Services:")
    print("  - Amazon Rekognition: For product detection")
    print("  - Amazon Bedrock: For vision analysis and catalog generation")
    print("  - AWS Transcribe: For audio transcription")
    
    print("\n💡 To set environment variables:")
    print("  export AWS_REGION=us-east-1")
    print("  export TRANSCRIBE_S3_BUCKET=your-bucket-name")
    print("  export REKOGNITION_PROJECT_ARN=arn:aws:rekognition:...")


def main():
    """Main test menu"""
    print("\n" + "="*60)
    print("AI Stack Test Script")
    print("="*60)
    
    while True:
        print("\nSelect a test:")
        print("  1. Check configuration")
        print("  2. Test image-only processing")
        print("  3. Test audio-only processing")
        print("  4. Test complete pipeline (image + audio)")
        print("  5. Exit")
        
        choice = input("\nEnter choice (1-5): ").strip()
        
        if choice == '1':
            check_configuration()
        elif choice == '2':
            test_image_only()
        elif choice == '3':
            test_audio_only()
        elif choice == '4':
            test_complete_pipeline()
        elif choice == '5':
            print("\nGoodbye!")
            break
        else:
            print("Invalid choice, please try again")


if __name__ == '__main__':
    main()
