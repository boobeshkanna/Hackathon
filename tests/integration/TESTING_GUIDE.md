# Integration Testing Guide

## Overview

This guide provides comprehensive information about integration testing for the Vernacular Artisan Catalog system.

## Test Architecture

### Test Layers

```
┌─────────────────────────────────────────────────────────┐
│                   Integration Tests                      │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────────┐  ┌──────────────────┐            │
│  │  End-to-End      │  │   Component      │            │
│  │  Flow Tests      │  │   Integration    │            │
│  │                  │  │   Tests          │            │
│  └──────────────────┘  └──────────────────┘            │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │         Test Environment Setup                    │  │
│  │  (AWS Resources + Mock ONDC Server)              │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### Test Components

1. **Test Environment Setup** (`test_environment_setup.py`)
   - Creates AWS resources (S3, DynamoDB, SQS, SNS)
   - Manages resource lifecycle
   - Provides fixtures for tests

2. **Mock ONDC Server** (`mock_ondc_server.py`)
   - Simulates ONDC Gateway API
   - Validates Beckn protocol payloads
   - Provides test utilities

3. **End-to-End Tests** (`test_end_to_end_flows.py`)
   - Complete workflow validation
   - Multi-component integration
   - Retry and error handling

4. **Component Tests** (`test_component_integration.py`)
   - Point-to-point integration
   - Individual component validation
   - Data flow verification

## Test Scenarios

### End-to-End Flow Tests

#### 1. Complete Flow: Capture → Queue → Upload → Process → Submit → Notify

**Purpose**: Validate the complete happy path from media capture to ONDC submission.

**Steps**:
1. Simulate media capture and local queue
2. Upload media to S3
3. Publish message to SQS
4. Create processing record in DynamoDB
5. Simulate AI processing (ASR, Vision, Extraction)
6. Map to ONDC schema
7. Submit to ONDC Gateway
8. Verify final state

**Requirements Validated**: All

**Expected Outcome**: 
- All processing stages complete successfully
- Catalog entry submitted to ONDC
- Catalog ID returned and stored

#### 2. Offline Capture → Online Sync Flow

**Purpose**: Validate offline-first workflow with delayed sync.

**Steps**:
1. Simulate offline capture (local queue only)
2. Queue multiple entries locally
3. Simulate network coming online
4. Background sync uploads all entries
5. Verify all entries synced

**Requirements Validated**: 2.1, 2.2, 2.3, 2.4, 2.5

**Expected Outcome**:
- Entries queued locally without network
- All entries sync when network available
- No data loss during offline period

#### 3. Failed Processing → Retry → Success

**Purpose**: Validate retry logic for transient failures.

**Steps**:
1. Create processing record with failed status
2. Simulate retry with exponential backoff
3. Retry processing
4. Verify successful completion on retry

**Requirements Validated**: 2.4, 14.1, 14.2, 14.3, 14.4

**Expected Outcome**:
- Failed processing is retried
- Retry count incremented
- Processing succeeds on retry

#### 4. Failed ONDC Submission → Retry → Success

**Purpose**: Validate ONDC submission retry with idempotency.

**Steps**:
1. Create record with failed ONDC submission
2. Retry submission with same idempotency key
3. Verify successful submission
4. Verify no duplicate entries

**Requirements Validated**: 9.2, 9.3

**Expected Outcome**:
- Submission retried with same idempotency key
- No duplicate catalog entries
- Catalog ID returned and stored

#### 5. Update Existing Catalog Entry → Version History

**Purpose**: Validate catalog update workflow.

**Steps**:
1. Create initial catalog entry
2. Submit to ONDC
3. Create updated version
4. Submit update
5. Verify version history

**Requirements Validated**: 18.1, 18.2, 18.3, 18.4, 18.5

**Expected Outcome**:
- Update detected correctly
- Catalog ID preserved
- Version history maintained

### Component Integration Tests

#### 1. Edge Client ↔ API Gateway (Upload Resumption)

**Purpose**: Validate resumable upload functionality.

**Test**: Multipart upload with simulated interruption and resume.

**Requirements**: 3.1, 3.2, 3.3

#### 2. API Gateway ↔ SQS (Message Publishing)

**Purpose**: Validate message publishing after upload.

**Test**: Publish message to SQS and verify receipt.

**Requirements**: 3.4

#### 3. SQS ↔ Lambda Orchestrator (Message Consumption)

**Purpose**: Validate Lambda consuming messages from SQS.

**Test**: Consume message and create processing record.

**Requirements**: All

#### 4. Lambda ↔ S3 (Media Retrieval)

**Purpose**: Validate Lambda retrieving media from S3.

**Test**: Upload media, retrieve, and verify integrity.

**Requirements**: All

#### 5. Lambda ↔ Sagemaker (Vision + ASR)

**Purpose**: Validate Sagemaker endpoint invocation.

**Test**: Mock Sagemaker responses for vision and ASR.

**Requirements**: 4.1, 4.2, 4.3, 6.1, 6.2

#### 6. Lambda ↔ Bedrock (Transcreation)

**Purpose**: Validate Bedrock invocation for transcreation.

**Test**: Mock Bedrock responses for attribute extraction.

**Requirements**: 5.1, 5.2, 5.3, 5.4, 7.1, 7.2

#### 7. Lambda ↔ ONDC Gateway (Submission)

**Purpose**: Validate ONDC catalog submission.

**Test**: Submit catalog to mock ONDC server.

**Requirements**: 8.1, 8.2, 8.5, 9.1, 9.2

#### 8. Lambda ↔ SNS (Notification Publishing)

**Purpose**: Validate notification publishing.

**Test**: Publish notification to SNS topic.

**Requirements**: 10.1, 10.2, 10.3

#### 9. Complete Component Chain

**Purpose**: Validate data flow through all components.

**Test**: S3 → SQS → Lambda → DynamoDB → ONDC → SNS

**Requirements**: All

## Test Data

### Test Media Files

Integration tests use generated test media:

- **Image**: 800x600 RGB JPEG (random pixels)
- **Audio**: Minimal WAV file (16kHz mono PCM)

### Test Tenant Configuration

```json
{
  "tenant_id": "test-tenant-001",
  "name": "Test Artisan Cooperative",
  "language_preferences": ["hi", "te", "ta"],
  "ondc_seller_id": "test-seller-001",
  "ondc_api_key": "test-api-key",
  "quota_daily_uploads": 1000
}
```

### Test Artisan Data

```json
{
  "artisan_id": "test-artisan-001",
  "tenant_id": "test-tenant-001",
  "name": "Test Artisan",
  "language": "hi",
  "phone": "+919876543210"
}
```

## Mock ONDC Server

### API Endpoints

#### POST /beckn/catalog/on_search

Submit catalog entry.

**Request**:
```json
{
  "context": {
    "domain": "retail",
    "country": "IND",
    "action": "on_search",
    "bap_id": "buyer-app-id",
    "bpp_id": "seller-app-id"
  },
  "message": {
    "catalog": {
      "bpp/providers": [...]
    }
  }
}
```

**Response**:
```json
{
  "message": {
    "ack": {
      "status": "ACK"
    }
  },
  "catalog_ids": {
    "item-123": "ondc-catalog-abc123"
  }
}
```

#### PUT /beckn/catalog/update

Update existing catalog entry.

**Request**:
```json
{
  "catalog_id": "ondc-catalog-abc123",
  "item": {...}
}
```

#### GET /beckn/catalog/{catalog_id}

Retrieve catalog entry.

#### GET /test/submissions

View submission history (test utility).

#### POST /test/reset

Reset mock data (test utility).

#### POST /test/simulate-error

Simulate error conditions (test utility).

**Request**:
```json
{
  "error_type": "rate_limit" | "timeout" | "server_error"
}
```

## Running Tests

### Quick Start

```bash
# Run all tests
./scripts/run_integration_tests.sh

# Run specific suite
./scripts/run_integration_tests.sh --suite e2e
./scripts/run_integration_tests.sh --suite component

# Setup environment only
./scripts/run_integration_tests.sh --setup-only

# Teardown environment only
./scripts/run_integration_tests.sh --teardown-only
```

### Using Pytest Directly

```bash
# All tests
pytest tests/integration/ -v -s

# Specific test file
pytest tests/integration/test_end_to_end_flows.py -v -s

# Specific test
pytest tests/integration/test_end_to_end_flows.py::TestEndToEndFlows::test_complete_flow_capture_to_notify -v -s

# With coverage
pytest tests/integration/ -v -s --cov=backend --cov-report=html
```

## Debugging Tests

### Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Inspect AWS Resources

```bash
# List S3 buckets
aws s3 ls | grep test-artisan

# List DynamoDB tables
aws dynamodb list-tables | grep Test

# List SQS queues
aws sqs list-queues | grep test-catalog

# View DynamoDB table contents
aws dynamodb scan --table-name TestCatalogRecords-{timestamp}

# View S3 bucket contents
aws s3 ls s3://test-artisan-raw-{timestamp}/
```

### View Mock ONDC Server Logs

```bash
# Start server with debug logging
python tests/integration/mock_ondc_server.py

# View submission history
curl http://localhost:8080/test/submissions
```

### Pytest Debugging

```bash
# Stop on first failure
pytest tests/integration/ -x

# Drop into debugger on failure
pytest tests/integration/ --pdb

# Show local variables on failure
pytest tests/integration/ -l

# Increase verbosity
pytest tests/integration/ -vv
```

## Best Practices

### Test Isolation

- Each test should be independent
- Use function-scoped fixtures for clean state
- Clean up resources in teardown

### Idempotency

- Tests should be repeatable
- Use unique identifiers (UUIDs)
- Don't rely on external state

### Error Handling

- Test both success and failure paths
- Verify error messages and codes
- Test retry logic

### Performance

- Use session-scoped fixtures for expensive setup
- Parallelize independent tests
- Mock external services when possible

### Documentation

- Add docstrings to all tests
- Reference requirements being validated
- Document expected outcomes

## Troubleshooting

### Common Issues

#### AWS Credentials Not Configured

```bash
aws configure
# Enter your credentials
```

#### Port 8080 Already in Use

```bash
# Find process using port
lsof -i :8080

# Kill process
kill -9 {PID}
```

#### Resources Not Cleaned Up

```bash
# Manual cleanup
aws s3 rb s3://test-artisan-raw-{timestamp} --force
aws dynamodb delete-table --table-name TestCatalogRecords-{timestamp}
aws sqs delete-queue --queue-url {queue-url}
aws sns delete-topic --topic-arn {topic-arn}
```

#### Tests Timeout

Increase timeout in pytest.ini:

```ini
[pytest]
timeout = 300
```

#### Mock Server Not Starting

```bash
# Check dependencies
pip install fastapi uvicorn

# Start manually
python tests/integration/mock_ondc_server.py
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Integration Tests

on: [push, pull_request]

jobs:
  integration-tests:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: pip install -r requirements.txt
    
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v1
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: ap-south-1
    
    - name: Run integration tests
      run: ./scripts/run_integration_tests.sh
```

### GitLab CI

```yaml
integration-tests:
  stage: test
  image: python:3.11
  
  before_script:
    - pip install -r requirements.txt
    - aws configure set aws_access_key_id $AWS_ACCESS_KEY_ID
    - aws configure set aws_secret_access_key $AWS_SECRET_ACCESS_KEY
    - aws configure set region ap-south-1
  
  script:
    - ./scripts/run_integration_tests.sh
  
  only:
    - main
    - develop
```

## Metrics and Reporting

### Test Coverage

```bash
pytest tests/integration/ --cov=backend --cov-report=html
open htmlcov/index.html
```

### Test Duration

```bash
pytest tests/integration/ --durations=10
```

### Test Report

```bash
pytest tests/integration/ --html=report.html --self-contained-html
```

## Maintenance

### Adding New Tests

1. Identify requirement to validate
2. Choose appropriate test suite (e2e or component)
3. Write test with descriptive name
4. Add docstring with requirement reference
5. Use appropriate fixtures
6. Verify test passes
7. Update documentation

### Updating Mock ONDC Server

1. Update endpoint handlers
2. Add new validation rules
3. Update test utilities
4. Document changes

### Updating Test Environment

1. Modify `test_environment_setup.py`
2. Update resource creation/cleanup
3. Update fixtures
4. Test setup/teardown

## Resources

- [AWS SDK for Python (Boto3)](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
- [Pytest Documentation](https://docs.pytest.org/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [ONDC Beckn Protocol](https://github.com/beckn/protocol-specifications)
