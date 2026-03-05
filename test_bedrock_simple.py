#!/usr/bin/env python3
"""
Simple Bedrock test script
"""
import json
import os
import sys
import boto3
from botocore.exceptions import ClientError

def test_bedrock():
    """Test Bedrock access"""
    
    # Load environment
    region = os.getenv('AWS_REGION', 'ap-south-1')
    
    print("=" * 60)
    print("Testing Bedrock Model Access")
    print("=" * 60)
    print(f"\nRegion: {region}\n")
    
    # Step 1: Check credentials
    print("Step 1: Checking AWS Credentials")
    print("-" * 60)
    try:
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        print(f"✅ AWS credentials configured")
        print(f"   Account ID: {identity['Account']}")
        print(f"   User/Role: {identity['Arn'].split('/')[-1]}")
    except Exception as e:
        print(f"❌ AWS credentials not configured: {e}")
        print("   Run: aws configure")
        return False
    
    print()
    
    # Step 2: List available models
    print("Step 2: Checking Available Models")
    print("-" * 60)
    try:
        bedrock = boto3.client('bedrock', region_name=region)
        response = bedrock.list_foundation_models(byProvider='anthropic')
        
        models = response.get('modelSummaries', [])
        anthropic_models = [m['modelId'] for m in models if 'claude' in m['modelId'].lower()]
        
        if anthropic_models:
            print(f"✅ Found {len(anthropic_models)} Anthropic models")
            
            # Check for specific models we need
            needed_models = [
                'anthropic.claude-3-haiku-20240307-v1:0',
                'anthropic.claude-3-5-sonnet-20240620-v1:0',
                'anthropic.claude-3-sonnet-20240229-v1:0'
            ]
            
            for model_id in needed_models:
                if model_id in anthropic_models:
                    print(f"   ✅ {model_id}")
                else:
                    print(f"   ⚠️  {model_id} (not found)")
        else:
            print("❌ No Anthropic models found")
            return False
            
    except Exception as e:
        print(f"❌ Error listing models: {e}")
        return False
    
    print()
    
    # Step 3: Test invocation
    print("Step 3: Testing Model Invocation")
    print("-" * 60)
    
    model_id = 'anthropic.claude-3-haiku-20240307-v1:0'
    
    try:
        bedrock_runtime = boto3.client('bedrock-runtime', region_name=region)
        
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 50,
            "messages": [
                {
                    "role": "user",
                    "content": "Say 'Hello from Bedrock!' in one sentence."
                }
            ]
        }
        
        print(f"Invoking: {model_id}")
        
        response = bedrock_runtime.invoke_model(
            modelId=model_id,
            body=json.dumps(request_body)
        )
        
        response_body = json.loads(response['body'].read())
        
        # Extract response text
        content = response_body.get('content', [])
        if content:
            text = content[0].get('text', '')
            print(f"✅ Success! Bedrock is working.")
            print(f"\nResponse:")
            print(f"  {text}")
        else:
            print("⚠️  Got response but no content")
            print(f"   Response: {response_body}")
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        print(f"❌ Bedrock invocation failed")
        print(f"   Error Code: {error_code}")
        print(f"   Error Message: {error_message}")
        print()
        
        if error_code == 'AccessDeniedException':
            if 'INVALID_PAYMENT_INSTRUMENT' in error_message:
                print("🚨 PAYMENT METHOD REQUIRED")
                print()
                print("AWS Bedrock requires a valid payment method on your account.")
                print()
                print("Quick fix (5 minutes):")
                print("  1. Go to: https://console.aws.amazon.com/billing/home#/paymentmethods")
                print("  2. Click 'Add a payment method'")
                print("  3. Enter your credit/debit card details")
                print("  4. Wait 2-5 minutes")
                print("  5. Run this script again")
                print()
                print("Don't worry about costs:")
                print("  • Free tier covers testing (first 12 months)")
                print("  • After free tier: ~$4 per 1000 products")
                print("  • Set up billing alerts to stay safe")
                print()
                print("📖 Detailed guide: FIX_PAYMENT_ISSUE.md")
                print("📖 Quick guide: PAYMENT_SETUP_QUICK.md")
            else:
                print("Possible reasons:")
                print("  1. Model access not enabled in Bedrock console")
                print("  2. IAM permissions missing (bedrock:InvokeModel)")
                print()
                print("To enable model access:")
                print(f"  1. Go to: https://{region}.console.aws.amazon.com/bedrock/home?region={region}#/modelaccess")
                print("  2. Click 'Manage model access'")
                print("  3. Enable: Claude 3 Haiku, Claude 3.5 Sonnet, Claude 3 Sonnet")
                print("  4. Wait 2-3 minutes")
                print("  5. Run this script again")
        elif error_code == 'ValidationException':
            print("Possible reasons:")
            print("  1. Model not available in this region")
            print("  2. Model ID incorrect")
            print(f"  3. Try a different region (current: {region})")
        
        return False
    
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print()
    print("=" * 60)
    print("✅ Bedrock Access Confirmed")
    print("=" * 60)
    print()
    print("Next steps:")
    print("  1. Test AI stack: python backend/test_ai_stack.py")
    print("  2. Deploy to AWS: cd backend/infrastructure/cdk && npm run deploy")
    print()
    
    return True


if __name__ == '__main__':
    # Load .env if exists
    if os.path.exists('.env'):
        with open('.env') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
    
    success = test_bedrock()
    sys.exit(0 if success else 1)
