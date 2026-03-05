# Fix AWS Payment Issue for Bedrock

## The Error

```
AccessDeniedException: Model access is denied due to INVALID_PAYMENT_INSTRUMENT:
A valid payment instrument must be provided.
```

## What This Means

AWS Bedrock requires a valid payment method on your AWS account. Even though Bedrock has a free tier, AWS needs a credit/debit card on file.

## How to Fix (5 minutes)

### Step 1: Add Payment Method

1. Go to AWS Billing Console:
   ```
   https://console.aws.amazon.com/billing/home#/paymentmethods
   ```

2. Click "Add a payment method"

3. Enter your credit/debit card details:
   - Card number
   - Expiration date
   - CVV
   - Billing address

4. Click "Add card"

5. Make this the default payment method if prompted

### Step 2: Verify Account Status

1. Go to Account Settings:
   ```
   https://console.aws.amazon.com/billing/home#/account
   ```

2. Check that:
   - Payment method is listed
   - Account status is "Active"
   - No outstanding payments

### Step 3: Wait 2-5 Minutes

AWS needs a few minutes to process the payment method update.

### Step 4: Test Again

```bash
python test_bedrock_simple.py
```

You should now see:
```
✅ Success! Bedrock is working.
Response: Hello from Bedrock!
```

## Alternative: Use Free Tier Services Only

If you don't want to add a payment method, you can use AWS services that don't require it:

### Option A: Use Amazon Rekognition Only (No Bedrock)

Rekognition has a free tier and may not require payment method:
- 5,000 images/month free for first 12 months
- Basic product detection without detailed analysis

### Option B: Use Different Region

Some regions may have different payment requirements. Try:

```bash
# Update .env
AWS_REGION=us-east-1
```

Then test again.

### Option C: Use AWS Free Tier Account

If you're within the first 12 months of AWS account creation:
- Bedrock free tier: Limited free usage
- But still requires payment method on file

## Bedrock Pricing (After Free Tier)

Don't worry about costs - Bedrock is very cheap:

| Model | Input Cost | Output Cost |
|-------|------------|-------------|
| Claude 3 Haiku | $0.25 per 1M tokens | $1.25 per 1M tokens |
| Claude 3.5 Sonnet | $3 per 1M tokens | $15 per 1M tokens |

For 1000 products: ~$0.60 total

## What Happens After Adding Payment Method

1. AWS validates the card (may see $1 authorization that gets refunded)
2. Account status updates to "Active"
3. Bedrock access is enabled
4. You can use all AWS services

## Free Tier Limits

First 12 months:
- Bedrock: 2 months free trial (varies by model)
- Rekognition: 5,000 images/month
- Transcribe: 60 minutes/month
- Lambda: 1M requests/month
- DynamoDB: 25 GB storage
- S3: 5 GB storage

You'll stay within free tier for testing!

## Cost Protection

Set up billing alerts to avoid surprises:

1. Go to: https://console.aws.amazon.com/billing/home#/budgets

2. Click "Create budget"

3. Set up alert:
   - Budget type: Cost budget
   - Amount: $10 (or your limit)
   - Alert threshold: 80%
   - Email: your-email@example.com

4. You'll get email if costs approach $8

## Still Having Issues?

### Check Account Status
```bash
aws sts get-caller-identity
```

Should show your account ID without errors.

### Check IAM Permissions
```bash
aws iam get-user
```

Make sure you have `bedrock:InvokeModel` permission.

### Contact AWS Support

If payment method is added but still getting error:
1. Go to: https://console.aws.amazon.com/support/home
2. Create a case: "Billing and Account Support"
3. Describe the Bedrock payment issue
4. AWS usually responds within 24 hours

## Summary

1. ✅ Add payment method: https://console.aws.amazon.com/billing/home#/paymentmethods
2. ⏳ Wait 2-5 minutes
3. ✅ Test: `python test_bedrock_simple.py`
4. 🎉 Start using Bedrock!

The payment method is required but you'll stay within free tier for testing. Bedrock is very cheap even after free tier (~$4 per 1000 products).
