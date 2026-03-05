# Quick Fix: Add Payment Method to AWS

## The Problem

```
❌ Model access is denied due to INVALID_PAYMENT_INSTRUMENT
```

## The Solution (5 minutes)

### 1. Open AWS Billing

Click this link: https://console.aws.amazon.com/billing/home#/paymentmethods

### 2. Add Your Card

```
┌─────────────────────────────────────────┐
│  AWS Billing - Payment Methods          │
├─────────────────────────────────────────┤
│                                         │
│  [+ Add a payment method]               │
│                                         │
│  Card number:  [________________]       │
│  Expiration:   [MM] / [YY]              │
│  CVV:          [___]                    │
│  Name on card: [________________]       │
│                                         │
│  Billing address:                       │
│  [________________________________]     │
│                                         │
│  [ Add card ]                           │
│                                         │
└─────────────────────────────────────────┘
```

### 3. Wait 2-5 Minutes

AWS needs time to validate your payment method.

### 4. Test Again

```bash
python test_bedrock_simple.py
```

Expected output:
```
✅ Success! Bedrock is working.
Response: Hello from Bedrock!
```

## Why Is This Required?

- AWS requires payment method for all paid services
- Bedrock is a paid service (even with free tier)
- You won't be charged during testing (free tier covers it)
- After free tier: ~$4 per 1000 products (very cheap!)

## Cost Protection

Set up a billing alert so you don't get surprised:

1. Go to: https://console.aws.amazon.com/billing/home#/budgets
2. Create budget: $10 limit
3. Alert at 80% ($8)
4. You'll get email if costs approach limit

## Free Tier Coverage

First 12 months:
- ✅ Bedrock: 2 months free trial
- ✅ Rekognition: 5,000 images/month
- ✅ Transcribe: 60 minutes/month
- ✅ Lambda: 1M requests/month
- ✅ DynamoDB: 25 GB storage

Testing 100-500 products? You'll stay within free tier!

## What If I Don't Want to Add Payment?

You have 3 options:

### Option 1: Use Different AWS Account
- Create new AWS account with payment method
- Transfer your code
- Deploy there

### Option 2: Use Rekognition Only (No Bedrock)
- Remove Bedrock from your stack
- Use only Rekognition for product detection
- Less detailed analysis but still works

### Option 3: Use Local AI Models
- Run models locally (requires GPU)
- No AWS costs
- More complex setup

## Still Having Issues?

### Error: "Card declined"
- Check card details are correct
- Try different card
- Contact your bank

### Error: "Account suspended"
- Contact AWS Support
- May have outstanding payment

### Error: Still getting INVALID_PAYMENT_INSTRUMENT after adding card
- Wait 5 minutes (not 2)
- Clear browser cache
- Try different browser
- Contact AWS Support

## Summary

```
1. Add card: https://console.aws.amazon.com/billing/home#/paymentmethods
2. Wait 5 minutes
3. Test: python test_bedrock_simple.py
4. ✅ Done!
```

You'll stay within free tier for testing. Bedrock is very affordable even after free tier.

## Next Steps After Adding Payment

1. ✅ Test Bedrock: `python test_bedrock_simple.py`
2. ✅ Enable models: https://ap-south-1.console.aws.amazon.com/bedrock/home?region=ap-south-1#/modelaccess
3. ✅ Test AI stack: `python backend/test_ai_stack.py`
4. ✅ Deploy: `cd backend/infrastructure/cdk && npm run deploy`
