# Integration Tests

This directory contains integration tests for the Vernacular Artisan Catalog system.

## Overview

Integration tests validate the complete system workflow and component interactions:

1. **Environment Setup** (`test_environment_setup.py`): AWS resource provisioning
2. **End-to-End Flows** (`test_end_to_end_flows.py`): Complete workflows from capture to notification
3. **Component Integration** (`test_component_integration.py`): Component-to-component interactions

## Prerequisites

### AWS Configuration

1. AWS account with appropriate permissions
2. AWS CLI configured (`aws configure`)
3. Environment variables set in `.env` file

### Python Dependencies

```bash
pip install -r requirements.txt
```

Required packages:
- boto3 (AWS SDK)
- pytest (testing framework)
- requests (HTTP client)
- fastapi, uvicorn (mock ONDC server)
- python-dotenv (environment variables)
- Pillow (image processing)

### Mock ONDC Server

The integration tests require a mock ONDC API server. It's automatically started by the test fixtures, but you can also run it manually:

```bash
python tests/integration/mock_ondc_server.py
```

The server will start on `http://localhost:8080`.

## Running Tests

### Run All Integration Tests

```bash
pytest tests/integration/ -v -s
```

### Run Specific Test Suites

```bash
# End-to-end flow tests only
pytest tests/integration/test_end_to_end_flows.py -v -s

# Component integration tests only
pytest tests/integration/test_component_integration.py -v -s
```

### Run Specific Test

```bash
pytest tests/integration/test_end_to_end_flows.py::TestEndToEndFlows::test_complete_flow_capture_to_notify -v -s
```

## Test Environment Setup

### Automatic Setup (Recommended)

The test fixtures automatically set up and tear down AWS resources:

```bash
pytest tests/integration/ -v -s
```

### Manual Setup

For debugging or manual testing:

```bash
# Set up test environment
python tests/integration/test_environment_setup.py setup

# Run tests manually
pytest tests/integration/ -v -s

# Tear down test environment
python tests/integration/test_environment_setup.py teardown
```

## Test Structure

### Session-Scoped Fixtures

These are created once per test session:

- `aws_integration_env`: AWS test environment (S3, DynamoDB, SQS, SNS)
- `mock_ondc_server`: Mock ONDC API server

### Function-Scoped Fixtures

These are created for each test:

- `clean_aws_env`: Clean AWS environment state
- `test_media_files`: Test image and audio files
- `test_tenant_config`: Test tenant configuration
- `test_artisan_data`: Test artisan data

## Test Coverage

### End-to-End Flow Tests

1. **Complete Flow**: Capture → Queue → Upload → Process → Submit → Notify
2. **Offline Sync**: Offline capture → Online sync → Process → Submit
3. **Retry Logic**: Failed processing → Retry → Success
4. **ONDC Retry**: Failed ONDC submission → Retry → Success
5. **Update Flow**: Update existing catalog entry → Version history

### Component Integration Tests

1. **Edge Client ↔ API Gateway**: Upload resumption
2. **API Gateway ↔ SQS**: Message publishing
3. **SQS ↔ Lambda**: Message consumption
4. **Lambda ↔ S3**: Media retrieval
5. **Lambda ↔ Sagemaker**: Vision + ASR processing
6. **Lambda ↔ Bedrock**: Transcreation
7. **Lambda ↔ ONDC Gateway**: Catalog submission
8. **Lambda ↔ SNS**: Notification publishing
9. **Complete Chain**: S3 → SQS → Lambda → DynamoDB → ONDC → SNS

## AWS Resources Created

The test environment creates the following AWS resources:

### S3 Buckets
- `test-artisan-raw-{timestamp}`: Raw media storage
- `test-artisan-enhanced-{timestamp}`: Enhanced media storage

### DynamoDB Tables
- `TestCatalogRecords-{timestamp}`: Catalog processing records
- `TestTenantConfig-{timestamp}`: Tenant configurations

### SQS Queues
- `test-catalog-queue-{timestamp}`: Main processing queue
- `test-catalog-dlq-{timestamp}`: Dead letter queue

### SNS Topics
- `test-catalog-notifications-{timestamp}`: Notification topic

All resources are automatically cleaned up after tests complete.

## Mock ONDC Server

The mock ONDC server simulates the ONDC Gateway API:

### Endpoints

- `POST /beckn/catalog/on_search`: Submit catalog
- `PUT /beckn/catalog/update`: Update catalog
- `GET /beckn/catalog/{catalog_id}`: Get catalog
- `GET /test/submissions`: View submission history
- `POST /test/reset`: Reset mock data
- `POST /test/simulate-error`: Simulate errors
- `GET /health`: Health check

### Test Utilities

```python
# Reset mock data between tests
requests.post("http://localhost:8080/test/reset")

# View submission history
response = requests.get("http://localhost:8080/test/submissions")
submissions = response.json()

# Simulate rate limiting
requests.post("http://localhost:8080/test/simulate-error", 
              json={"error_type": "rate_limit"})
```

## Troubleshooting

### AWS Credentials

If tests fail with authentication errors:

```bash
aws configure
# Enter your AWS credentials
```

### Resource Cleanup

If resources aren't cleaned up automatically:

```bash
# List resources
aws s3 ls | grep test-artisan
aws dynamodb list-tables | grep Test
aws sqs list-queues | grep test-catalog

# Manual cleanup
aws s3 rb s3://test-artisan-raw-{timestamp} --force
aws dynamodb delete-table --table-name TestCatalogRecords-{timestamp}
aws sqs delete-queue --queue-url {queue-url}
```

### Mock Server Issues

If the mock ONDC server doesn't start:

```bash
# Check if port 8080 is in use
lsof -i :8080

# Kill existing process
kill -9 {PID}

# Start server manually
python tests/integration/mock_ondc_server.py
```

### Test Timeouts

If tests timeout waiting for AWS resources:

```bash
# Increase timeout in conftest.py
# Or run tests with longer timeout
pytest tests/integration/ -v -s --timeout=300
```

## Cost Considerations

Integration tests create real AWS resources that may incur costs:

- S3 storage: Minimal (test files are small)
- DynamoDB: On-demand pricing (minimal for tests)
- SQS: Free tier covers test usage
- SNS: Free tier covers test usage

Estimated cost per test run: < $0.01

To minimize costs:
- Run tests in development/test AWS account
- Ensure automatic cleanup runs
- Use AWS Free Tier when possible

## CI/CD Integration

### GitHub Actions Example

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
      run: |
        pip install -r requirements.txt
    
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v1
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: ap-south-1
    
    - name: Run integration tests
      run: |
        pytest tests/integration/ -v -s
```

## Requirements Validation

These integration tests validate the following requirements:

- **Requirement 1**: Zero-UI Media Capture
- **Requirement 2**: Offline-First Local Queueing
- **Requirement 3**: Asynchronous Upload API
- **Requirement 4**: ASR for Vernacular Languages
- **Requirement 5**: Cultural Knowledge Preservation
- **Requirement 6**: Image Enhancement
- **Requirement 7**: Attribute Extraction
- **Requirement 8**: ONDC Schema Mapping
- **Requirement 9**: Deterministic ONDC Submission
- **Requirement 10**: Asynchronous Status Notification
- **Requirement 12**: Data Minimization and Privacy
- **Requirement 14**: Fault Tolerance
- **Requirement 18**: Catalog Update and Versioning

## Contributing

When adding new integration tests:

1. Follow the existing test structure
2. Use appropriate fixtures for setup/teardown
3. Add docstrings with requirement references
4. Ensure tests are idempotent
5. Clean up resources in teardown
6. Update this README with new test descriptions
