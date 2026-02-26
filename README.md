# Vernacular Artisan Catalog - ONDC Integration

A Zero-UI Edge-Native AI Application that enables vernacular artisans in rural India to catalog products on ONDC through simple photo and voice capture.

## Problem Statement

Rural artisans face "Cataloging Paralysis" - the mismatch between high-context vernacular storytelling and low-context structured digital schemas required by ONDC. This system bridges that gap.

## Solution

Artisans simply:
1. Take a photo of their product
2. Record a voice note in their native language (Hindi, Telugu, Tamil, etc.)
3. Submit

The AI automatically:
- Transcribes vernacular audio
- Extracts product attributes from image and voice
- Preserves cultural terminology
- Generates ONDC-compliant catalog entries

## Architecture

AWS Serverless Architecture:
- **Frontend**: Android App (React Native/Flutter)
- **API**: AWS API Gateway
- **Processing**: AWS Lambda (Python)
- **AI**: AWS Sagemaker (Vision + ASR) + Bedrock (LLM)
- **Storage**: S3 (media) + DynamoDB (metadata)
- **Queue**: SQS for async processing

## Tech Stack

- **Backend**: Python 3.11, FastAPI, boto3
- **AI/ML**: AWS Sagemaker, AWS Bedrock
- **Infrastructure**: AWS CDK (TypeScript)
- **Mobile**: React Native or Flutter
- **Testing**: pytest, hypothesis (property-based testing)

## Project Structure

```
backend/
├── lambda_functions/     # Lambda function code
├── models/               # Pydantic data models
├── services/             # Business logic
└── infrastructure/       # AWS CDK code
mobile/                   # Android app
tests/                    # Unit, property, integration tests
docs/                     # Documentation
scripts/                  # Deployment scripts
```

## Prerequisites

1. **AWS Account** with credits applied
2. **Python 3.11+**
3. **Node.js 18+** (for AWS CDK)
4. **AWS CLI** configured
5. **Docker** (for local testing)

## Setup Instructions

### 1. Clone and Install Dependencies

```bash
# Install Python dependencies
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Install AWS CDK
npm install -g aws-cdk
cd infrastructure/cdk
npm install
```

### 2. Configure AWS Credentials

```bash
aws configure
# Enter your AWS Access Key ID
# Enter your AWS Secret Access Key
# Default region: ap-south-1
# Default output format: json
```

### 3. Set Environment Variables

```bash
cp .env.example .env
# Edit .env with your actual values
```

### 4. Deploy Infrastructure

```bash
cd backend/infrastructure/cdk
cdk bootstrap  # First time only
cdk deploy
```

### 5. Deploy Lambda Functions

```bash
cd backend
./scripts/deploy_lambdas.sh
```

## Development

### Run Tests

```bash
# Unit tests
pytest tests/unit

# Property-based tests
pytest tests/property

# Integration tests
pytest tests/integration

# All tests with coverage
pytest --cov=backend tests/
```

### Local Development

```bash
# Run API locally
cd backend
uvicorn lambda_functions.api_handlers.main:app --reload
```

## AWS Services Used

- **API Gateway**: REST API endpoints
- **Lambda**: Serverless compute
- **S3**: Object storage for media files
- **DynamoDB**: NoSQL database for metadata
- **SQS**: Message queue for async processing
- **Sagemaker**: AI/ML inference (Vision + ASR)
- **Bedrock**: Large Language Model (transcreation)
- **CloudWatch**: Logging and monitoring
- **X-Ray**: Distributed tracing
- **SNS**: Notifications

## Cost Estimate

For hackathon/demo (100 catalog entries):
- Lambda: ~$0.50
- S3: ~$0.10
- DynamoDB: ~$0.05
- Sagemaker: ~$5-10
- Bedrock: ~$2-5

**Total: ~$10-20**

## Requirements

See `.kiro/specs/vernacular-artisan-catalog/requirements.md` for detailed requirements.

## Design

See `.kiro/specs/vernacular-artisan-catalog/design.md` for technical design and architecture.

## Implementation Tasks

See `.kiro/specs/vernacular-artisan-catalog/tasks.md` for implementation roadmap.

## License

MIT License - Hackathon Project
