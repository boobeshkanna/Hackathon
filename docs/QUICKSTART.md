# Quick Start Guide

This guide will help you get the Vernacular Artisan Catalog project up and running.

## Step 1: Install System Dependencies

The audio compression module requires ffmpeg to be installed on your system.

### Linux (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install -y ffmpeg
```

### Linux (Fedora/RHEL/CentOS)

```bash
sudo dnf install -y ffmpeg
```

### macOS

```bash
brew install ffmpeg
```

### Windows

Download ffmpeg from [https://ffmpeg.org/download.html](https://ffmpeg.org/download.html) and add it to your PATH.

### Verify Installation

```bash
ffmpeg -version
ffprobe -version
```

## Step 2: Set Up Python Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Step 3: Configure Environment Variables

```bash
# Copy the example file
cp .env.example .env

# Edit .env with your actual values
# You'll need:
# - AWS Account ID
# - AWS Region (default: ap-south-1)
# - ONDC API credentials
```

## Step 4: Configure AWS CLI

```bash
aws configure
```

Enter:
- AWS Access Key ID
- AWS Secret Access Key
- Default region: `ap-south-1`
- Default output format: `json`

## Step 5: Verify Setup

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
