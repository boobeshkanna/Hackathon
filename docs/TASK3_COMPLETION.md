# Task 3 Completion: API Gateway Lambda Handlers

## Overview
Successfully implemented API Gateway Lambda handlers for resumable uploads with S3 multipart upload support and SQS message publishing.

## Completed Subtasks

### 3.1 Create Lambda function for resumable upload endpoints ✅
**Files Created/Modified:**
- `backend/lambda_functions/api_handlers/upload_handlers.py` (new)
- `backend/lambda_functions/api_handlers/main.py` (modified)

**Implemented Endpoints:**
1. **POST /v1/catalog/upload/initiate**
   - Generates presigned S3 URLs for upload
   - Creates tracking ID and initial DynamoDB record
   - Returns: `{ trackingId, uploadUrl, expiresAt }`
   - Supports tenant isolation in S3 keys

2. **POST /v1/catalog/upload/complete**
   - Publishes message to SQS for processing
   - Updates DynamoDB with media keys
   - Returns: `{ status: 'accepted', trackingId, message }`
   - Generates idempotency keys for deduplication

3. **GET /v1/catalog/status/{trackingId}**
   - Queries DynamoDB for processing status
   - Returns: `{ trackingId, stage, message, catalogId?, errorDetails? }`
   - Determines current stage from processing status

**Features:**
- Request validation with proper error responses
- Tenant identification and isolation
- Rate limiting support (via API Gateway configuration)
- Distributed tracing with AWS X-Ray
- Structured logging with AWS Lambda Powertools

### 3.2 Implement S3 multipart upload with presigned URLs ✅
**Files Created:**
- `backend/services/s3_upload/multipart_upload.py` (new)
- `backend/services/s3_upload/__init__.py` (new)

**Implemented Features:**
1. **Multipart Upload Initiation**
   - Creates S3 multipart upload
   - Generates presigned URLs for each part
   - Calculates optimal part size (5MB default)
   - Stores upload state in DynamoDB

2. **Upload State Tracking**
   - Tracks completed parts in DynamoDB
   - Records ETags for each part
   - Supports querying upload state for resume

3. **Upload Resume Logic**
   - `get_upload_state()` returns completed and pending parts
   - Client can resume from last successful part
   - Handles expired URLs by regenerating

4. **Upload Completion**
   - Validates all parts are uploaded
   - Completes S3 multipart upload
   - Updates state to 'completed'

5. **Upload Abort**
   - Cleans up incomplete multipart uploads
   - Frees S3 storage

**Data Model:**
```python
UploadState {
    tracking_id: str (PK)
    upload_id: str
    s3_key: str
    s3_bucket: str
    content_type: str
    file_size: int
    part_size: int
    num_parts: int
    completed_parts: List[{part_number, etag}]
    status: 'initiated' | 'completed' | 'aborted'
    created_at: timestamp
    expires_at: timestamp
}
```

### 3.3 Implement SQS message publishing ✅
**Files Created:**
- `backend/services/queue/sqs_publisher.py` (new)
- `backend/services/queue/__init__.py` (new)

**Implemented Features:**
1. **Catalog Processing Message Publishing**
   - Publishes to SQS queue with message body:
     ```json
     {
       "trackingId": "trk_...",
       "tenantId": "tenant_123",
       "artisanId": "artisan_456",
       "photoKey": "s3://bucket/path/photo.jpg",
       "audioKey": "s3://bucket/path/audio.opus",
       "language": "hi",
       "priority": "normal",
       "timestamp": "2024-02-26T10:00:00Z"
     }
     ```

2. **Idempotency Key Generation**
   - Deterministic SHA-256 hash: `hash(trackingId|tenantId|artisanId)`
   - Ensures deduplication in FIFO queues
   - Prevents duplicate processing

3. **Message Serialization**
   - JSON serialization with validation
   - Message attributes for filtering
   - Support for FIFO and standard queues

4. **Error Handling**
   - Validates required fields
   - Validates language codes
   - Validates media keys
   - Proper error logging and propagation

5. **Status Update Publishing**
   - Publishes status updates for notifications
   - Includes stage, message, catalogId, errorDetails
   - Used by notification service

## Architecture

### Request Flow
```
Client → API Gateway → Lambda Handler → S3 (presigned URL)
                                      → DynamoDB (state)
                                      → SQS (processing queue)
```

### Upload Flow
1. Client calls `/v1/catalog/upload/initiate`
2. Lambda generates presigned S3 URL and tracking ID
3. Lambda creates initial record in DynamoDB
4. Client uploads directly to S3 using presigned URL
5. Client calls `/v1/catalog/upload/complete` with tracking ID
6. Lambda publishes message to SQS queue
7. Lambda returns acknowledgment immediately

### Multipart Upload Flow (for large files)
1. Client calls `initiate_multipart_upload()` with file size
2. Lambda creates S3 multipart upload
3. Lambda generates presigned URLs for each part
4. Client uploads parts in parallel
5. Client calls `record_part_completion()` for each part
6. Client calls `complete_multipart_upload()` when done
7. Lambda completes S3 multipart upload

### Resume Flow
1. Upload interrupted mid-transfer
2. Client calls `get_upload_resume_info(tracking_id)`
3. Lambda returns completed and pending parts
4. Client resumes upload from last successful part

## Requirements Validated

### Requirement 3.1: Zero-UI Media Capture
- ✅ API accepts media uploads without forms
- ✅ Supports photo and audio content types

### Requirement 3.2: Asynchronous Upload API
- ✅ Accepts multipart resumable uploads
- ✅ Preserves partial upload state in DynamoDB

### Requirement 3.3: Upload Resume
- ✅ Allows resuming from last successful chunk
- ✅ Tracks upload state per part

### Requirement 3.4: Async Processing
- ✅ Enqueues media for AI processing
- ✅ Returns acknowledgment immediately
- ✅ Does not block during processing

### Requirement 9.1: Idempotency
- ✅ Generates unique idempotency key per entry
- ✅ Uses deterministic hash for deduplication

### Requirement 17.2: Multi-Tenancy
- ✅ Tenant identification in requests
- ✅ Tenant isolation in S3 keys
- ✅ Tenant-based message grouping

## Testing Recommendations

### Unit Tests (to be implemented in task 3.5)
1. Test upload initiation with valid/invalid requests
2. Test upload completion and SQS publishing
3. Test status retrieval for different stages
4. Test multipart upload state tracking
5. Test idempotency key generation
6. Test message validation

### Integration Tests
1. Test end-to-end upload flow
2. Test multipart upload with resume
3. Test SQS message consumption
4. Test DynamoDB state updates

### Property Tests (to be implemented in task 3.4)
- **Property 6: Resumable Upload Round-Trip**
  - For any upload interrupted at any chunk position, resuming should complete successfully
  - Final uploaded file should be identical to original

## API Documentation

### POST /v1/catalog/upload/initiate
**Request:**
```json
{
  "tenantId": "tenant_123",
  "artisanId": "artisan_456",
  "contentType": "image/jpeg"
}
```

**Response:**
```json
{
  "trackingId": "trk_abc123xyz",
  "uploadUrl": "https://s3.amazonaws.com/bucket/path?signature=...",
  "expiresAt": "2024-02-26T11:00:00Z"
}
```

### POST /v1/catalog/upload/complete
**Request:**
```json
{
  "trackingId": "trk_abc123xyz",
  "photoKey": "tenant_123/artisan_456/trk_abc123xyz.jpg",
  "audioKey": "tenant_123/artisan_456/trk_abc123xyz.opus",
  "language": "hi"
}
```

**Response:**
```json
{
  "status": "accepted",
  "trackingId": "trk_abc123xyz",
  "message": "Upload accepted and queued for processing"
}
```

### GET /v1/catalog/status/{trackingId}
**Response:**
```json
{
  "trackingId": "trk_abc123xyz",
  "stage": "processing",
  "message": "Processing media with AI models",
  "timestamp": "2024-02-26T10:05:00Z"
}
```

## Configuration

### Environment Variables Required
- `AWS_REGION`: AWS region (default: ap-south-1)
- `S3_RAW_MEDIA_BUCKET`: S3 bucket for raw media
- `DYNAMODB_CATALOG_TABLE`: DynamoDB table for catalog records
- `SQS_QUEUE_URL`: SQS queue URL for processing messages

### IAM Permissions Required
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:CreateMultipartUpload",
        "s3:UploadPart",
        "s3:CompleteMultipartUpload",
        "s3:AbortMultipartUpload"
      ],
      "Resource": "arn:aws:s3:::raw-media-bucket/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:UpdateItem",
        "dynamodb:Query"
      ],
      "Resource": [
        "arn:aws:dynamodb:*:*:table/CatalogProcessingRecords",
        "arn:aws:dynamodb:*:*:table/CatalogProcessingRecords_UploadState"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "sqs:SendMessage"
      ],
      "Resource": "arn:aws:sqs:*:*:catalog-processing-queue"
    }
  ]
}
```

## Next Steps

1. **Task 3.4**: Write property test for upload resumption (Property 6)
2. **Task 3.5**: Write unit tests for API Gateway handlers
3. **Task 4**: Checkpoint - Ensure API Gateway tests pass
4. **Task 5**: Implement media compression utilities

## Notes

- All endpoints use AWS Lambda Powertools for logging and tracing
- Presigned URLs expire after 1 hour
- Upload state is tracked in DynamoDB for resume capability
- SQS messages use idempotency keys for deduplication
- Tenant isolation is enforced at S3 key level
- Legacy catalog endpoints remain for backward compatibility
