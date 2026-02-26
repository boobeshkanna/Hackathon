# Quick Start Guide

This guide will help you get the Vernacular Artisan Catalog project up and running.

## Step 1: Set Up Python Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Step 2: Configure Environment Variables

```bash
# Copy the example file
cp .env.example .env

# Edit .env with your actual values
# You'll need:
# - AWS Account ID
# - AWS Region (default: ap-south-1)
# - ONDC API credentials
```

## Step 3: Configure AWS CLI

```bash
aws configure
```

Enter:
- AWS Access Key ID
- AWS Secret Access Key
- Default region: `ap-south-1`
- Default output format: `json`

## Step 4: Verify Setup

```bash
# Check Python version (should be 3.11+)
python --version

# Check AWS CLI
aws --version

# Check AWS credentials
aws sts get-caller-identity
```

## Next Steps

Once setup is complete, proceed to:
- Deploy infrastructure (see `docs/DEPLOYMENT.md`)
- Run tests (see `docs/TESTING.md`)
- Develop locally (see `docs/DEVELOPMENT.md`)
