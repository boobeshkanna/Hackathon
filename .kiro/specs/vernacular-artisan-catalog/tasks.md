# Implementation Plan: Vernacular Artisan Catalog

## Overview

This implementation plan breaks down the Zero-UI Edge-Native AI Application into discrete coding tasks. The system enables vernacular artisans to catalog products on ONDC through photo and voice capture, with offline-first operation, AI processing, and ONDC integration.

The implementation follows the AWS serverless architecture shown in `generate_architecture_diagram.py`:
- **Client Edge**: Android App (Zero-UI)
- **Ingestion**: API Gateway → S3 (Raw Media) → SQS Queue
- **Processing**: Lambda Workflow Orchestrator
- **AI Engine**: Sagemaker (Vision & ASR combined) + Bedrock (Transcreation LLM)
- **Storage**: S3 (Raw + Enhanced buckets) + DynamoDB (Metadata)
- **External**: ONDC Network Gateway

**Architecture Note**: The design.md contains a more detailed component breakdown (separate ASR, Vision, LLM, RAG services), but the actual implementation uses AWS managed services that combine these functions. The requirements remain unchanged - this is just a different implementation approach.

## Tasks

- [x] 1. Set up AWS infrastructure and project structure
  - Create Python project structure for Lambda functions
  - Set up AWS CDK or Terraform for infrastructure as code
  - Configure AWS services: API Gateway, SQS, Lambda, S3 (2 buckets: raw + enhanced), DynamoDB
  - Set up AWS SDK (boto3) for Python with proper IAM roles
  - Configure logging with CloudWatch, environment variables via Lambda environment
  - Initialize Sagemaker client for Vision+ASR endpoint and Bedrock client for LLM
  - _Requirements: 15.4, 15.5_

- [x] 2. Implement core data models and DynamoDB schema
  - [x] 2.1 Create DynamoDB table design for catalog processing records
    - Define CatalogProcessingRecord table with partition key (tracking_id) and GSIs for tenant queries
    - Define LocalQueueEntry schema for edge client sync (used in mobile app)
    - Define tenant configuration and artisan profile tables
    - Create DynamoDB table creation scripts (CDK/Terraform)
    - _Requirements: 17.1, 17.2, 17.3_
  
  - [x] 2.2 Implement Python data models using Pydantic
    - Create CatalogProcessingRecord model with ProcessingStatus enum
    - Create ExtractedAttributes model with CSI nested model
    - Create ONDCCatalogItem and ItemDescriptor models (Beckn protocol)
    - Create UploadResponse, StatusUpdate, and error response models
    - _Requirements: 7.1, 7.2, 8.1_
  
  - [ ]* 2.3 Write property test for data model serialization
    - **Property 1: Round-trip serialization consistency**
    - **Validates: Requirements 8.1**

- [x] 3. Implement API Gateway Lambda handlers
  - [x] 3.1 Create Lambda function for resumable upload endpoints
    - Implement POST /v1/catalog/upload/initiate handler (returns presigned S3 URLs)
    - Implement POST /v1/catalog/upload/complete handler (publishes to SQS)
    - Implement GET /v1/catalog/status/{trackingId} handler (queries DynamoDB)
    - Add request validation, rate limiting, and tenant identification
    - _Requirements: 3.1, 3.2, 3.4, 17.2_
  
  - [x] 3.2 Implement S3 multipart upload with presigned URLs
    - Generate presigned URLs for multipart upload to raw media bucket
    - Implement upload state tracking in DynamoDB
    - Add upload resume logic using S3 multipart upload API
    - _Requirements: 3.2, 3.3_
  
  - [x] 3.3 Implement SQS message publishing
    - Create SQS publisher for catalog processing messages
    - Add idempotency key generation for deduplication
    - Implement message serialization and error handling
    - _Requirements: 3.4, 9.1_
  
  - [ ]* 3.4 Write property test for upload resumption
    - **Property 6: Resumable Upload Round-Trip**
    - **Validates: Requirements 3.2, 3.3**
  
  - [ ]* 3.5 Write unit tests for API Gateway handlers
    - Test upload initiation with valid/invalid requests
    - Test upload completion and status retrieval
    - Test rate limiting and authentication
    - _Requirements: 3.1, 3.4_

- [ ] 4. Checkpoint - Ensure API Gateway tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Implement media compression utilities
  - [ ] 5.1 Create image compression module
    - Implement JPEG compression with quality parameter (80%)
    - Add image resizing to max dimensions (1920px)
    - Implement quality metrics calculation (PSNR, SSIM)
    - _Requirements: 1.2, 6.4_
  
  - [ ] 5.2 Create audio compression module
    - Implement Opus codec compression (32kbps)
    - Add audio quality metrics calculation (SNR)
    - Implement audio duration validation (max 2 minutes)
    - _Requirements: 1.4, 4.5_
  
  - [ ]* 5.3 Write property tests for compression quality
    - **Property 1: Image Compression Preserves Quality**
    - **Property 2: Audio Compression Preserves Quality**
    - **Validates: Requirements 1.2, 1.4**

- [ ] 6. Deploy and configure Sagemaker Vision & ASR endpoint
  - [ ] 6.1 Create combined Sagemaker endpoint for Vision + ASR
    - Deploy multimodal model to Sagemaker that handles both image analysis and audio transcription
    - Configure endpoint to accept both image and audio inputs
    - Implement preprocessing for images (resize, normalize) and audio (format conversion)
    - Add language detection for vernacular audio (Hindi, Telugu, Tamil, Bengali, etc.)
    - Return structured output: { transcription, language, confidence, category, colors, materials, vision_confidence }
    - _Requirements: 4.1, 4.2, 4.3, 6.1, 7.1_
  
  - [ ] 6.2 Implement Sagemaker client in Lambda
    - Create boto3 Sagemaker Runtime client
    - Implement invoke_endpoint wrapper with retry logic
    - Add timeout handling and error categorization
    - Implement low-confidence flagging (threshold 0.7 for ASR, 0.6 for vision)
    - _Requirements: 4.4, 6.5, 14.1_
  
  - [ ]* 6.3 Write property tests for Sagemaker integration
    - **Property 8: ASR Transcription Completeness**
    - **Property 9: Language Preservation**
    - **Property 13: Product Extraction Completeness**
    - **Validates: Requirements 4.1, 4.3, 6.1**
  
  - [ ]* 6.4 Write unit tests for Sagemaker client
    - Test transcription for each supported language
    - Test vision attribute extraction
    - Test low-confidence flagging
    - Test error handling for corrupted media
    - _Requirements: 4.1, 4.2, 4.4, 6.1_

- [ ] 7. Implement image enhancement utilities
  - [ ] 7.1 Create image enhancement module for Lambda
    - Implement brightness and contrast adjustment using PIL/OpenCV
    - Add sharpening filters for blurry images
    - Implement quality assessment (blur detection, brightness check)
    - Generate multiple image sizes (thumbnail, medium, full)
    - Upload enhanced images to S3 enhanced bucket
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_
  
  - [ ]* 7.2 Write property tests for image processing
    - **Property 14: Image Enhancement Improves Metrics**
    - **Property 15: Multi-Resolution Image Generation**
    - **Property 16: Poor Quality Notification**
    - **Validates: Requirements 6.2, 6.4, 6.5**
  
  - [ ]* 7.3 Write unit tests for image enhancement
    - Test enhancement on low-light images
    - Test quality assessment and poor quality detection
    - Test multi-resolution generation
    - _Requirements: 6.1, 6.2, 6.5_

- [ ] 8. Checkpoint - Ensure media processing tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 9. Implement Bedrock LLM integration for transcreation
  - [ ] 9.1 Create Bedrock client for attribute extraction and transcreation
    - Initialize boto3 Bedrock Runtime client
    - Create prompt templates for multimodal attribute extraction
    - Implement structured output parsing for ExtractedAttributes
    - Add CSI identification using prompt engineering (cultural terms, craft techniques)
    - Generate short and long descriptions preserving cultural context
    - _Requirements: 5.1, 5.2, 5.4, 7.1, 7.2, 7.5_
  
  - [ ] 9.2 Implement attribute extraction logic
    - Extract category, material, color, dimensions, weight from combined ASR + Vision results
    - Extract price with normalization
    - Implement voice priority resolution for conflicts (voice overrides vision)
    - Identify CSI terms from vernacular transcription
    - Generate confidence scores for each attribute
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 5.1_
  
  - [ ] 9.3 Implement transcreation with cultural preservation
    - Generate SEO-friendly English descriptions from vernacular input
    - Preserve CSI terms with contextual explanations
    - Add craft technique and region of origin
    - Format output as Beckn-compatible JSON structure
    - _Requirements: 5.2, 5.4, 5.5, 7.1_
  
  - [ ]* 9.4 Write property tests for Bedrock integration
    - **Property 12: CSI Term Preservation**
    - **Property 17: Comprehensive Attribute Extraction**
    - **Property 19: Voice Priority Resolution**
    - **Validates: Requirements 5.2, 5.5, 7.1, 7.2, 7.4, 7.5**
  
  - [ ]* 9.5 Write unit tests for LLM integration
    - Test attribute extraction from sample inputs
    - Test price extraction and normalization
    - Test conflict resolution (voice vs image)
    - Test CSI integration in descriptions
    - _Requirements: 7.1, 7.3, 7.4, 5.2_

- [ ] 10. Implement ONDC schema mapping and validation
  - [ ] 10.1 Create schema mapper for Beckn protocol
    - Implement map_to_beckn_item function in Lambda
    - Map extracted attributes to Beckn fields
    - Build long description with CSI preservation
    - Implement category mapping to ONDC taxonomy
    - Generate deterministic item IDs
    - _Requirements: 8.1, 9.1_
  
  - [ ] 10.2 Implement ONDC schema validator
    - Create JSON Schema validation for Beckn protocol
    - Validate required fields (name, price, category, images)
    - Validate field formats and length constraints
    - Implement validation error parsing
    - _Requirements: 8.2, 8.5_
  
  - [ ] 10.3 Implement auto-correction for validation errors
    - Add automatic correction for common validation errors
    - Implement manual review flagging for uncorrectable errors
    - Log specific validation violations to CloudWatch
    - _Requirements: 8.3, 8.4_
  
  - [ ]* 10.4 Write property tests for schema mapping
    - **Property 20: Beckn Schema Mapping Completeness**
    - **Property 22: Mandatory Field Enforcement**
    - **Validates: Requirements 8.1, 8.5**
  
  - [ ]* 10.5 Write unit tests for schema validation
    - Test validation with valid and invalid payloads
    - Test auto-correction for common errors
    - Test manual review flagging
    - _Requirements: 8.2, 8.3, 8.4_

- [ ] 11. Checkpoint - Ensure ONDC mapping tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 12. Implement ONDC Gateway for catalog submission
  - [ ] 12.1 Create ONDC API client module
    - Implement Beckn protocol API client
    - Add authentication and request signing
    - Implement catalog submission endpoint (POST /beckn/catalog/on_search)
    - Add response parsing and error handling
    - _Requirements: 9.1, 9.3_
  
  - [ ] 12.2 Implement submission retry logic with exponential backoff
    - Add idempotency key preservation across retries
    - Implement error categorization (retryable vs permanent)
    - Add exponential backoff for retryable errors
    - Store retry state in DynamoDB
    - _Requirements: 9.2, 9.3_
  
  - [ ] 12.3 Implement audit logging to DynamoDB
    - Log all submission attempts with timestamps
    - Store ONDC response codes and error messages
    - Persist ONDC-assigned catalog IDs
    - _Requirements: 9.4, 9.5_
  
  - [ ] 12.4 Implement catalog update detection and API
    - Detect updates vs new entries based on attributes
    - Use ONDC update API for existing entries
    - Preserve original catalog IDs on updates
    - Maintain version history in DynamoDB
    - _Requirements: 18.1, 18.2, 18.3, 18.4_
  
  - [ ]* 12.5 Write property tests for ONDC submission
    - **Property 23: Idempotency Key Uniqueness**
    - **Property 24: Retry Idempotency Preservation**
    - **Property 26: Catalog ID Persistence**
    - **Validates: Requirements 9.1, 9.2, 9.5**
  
  - [ ]* 12.6 Write unit tests for ONDC Gateway
    - Test successful submission and catalog ID storage
    - Test retry logic with retryable errors
    - Test permanent error handling
    - Test update detection and versioning
    - _Requirements: 9.1, 9.2, 9.3, 18.1, 18.4_

- [ ] 13. Implement Lambda Workflow Orchestrator
  - [ ] 13.1 Create main SQS event handler Lambda function
    - Implement SQS event consumer that triggers on queue messages
    - Parse catalog processing message from SQS event
    - Update CatalogProcessingRecord in DynamoDB at each stage
    - Implement error handling and DLQ routing for failed messages
    - _Requirements: 10.1, 10.2_
  
  - [ ] 13.2 Orchestrate AI processing pipeline
    - Fetch raw media from S3 raw bucket
    - Call Sagemaker endpoint with audio + image
    - Parse Sagemaker response (transcription, language, vision attributes)
    - Call Bedrock with combined results for transcreation
    - Parse Bedrock response (extracted attributes, descriptions, Beckn JSON)
    - Save enhanced images to S3 enhanced bucket
    - _Requirements: 4.1, 6.1, 7.1, 7.2_
  
  - [ ] 13.3 Implement ONDC submission flow
    - Call schema mapper to generate Beckn payload
    - Validate payload against ONDC schema
    - Submit to ONDC Gateway
    - Store catalog ID in DynamoDB
    - _Requirements: 8.1, 9.1, 9.5_
  
  - [ ] 13.4 Implement notification publishing
    - Publish status events to SNS topic after each stage
    - Send push notifications via Firebase Cloud Messaging (optional integration)
    - Localize messages to artisan's vernacular language
    - _Requirements: 10.1, 10.2, 10.3, 10.4_
  
  - [ ] 13.5 Implement error handling and graceful degradation
    - Add error handlers for each processing stage
    - Implement fallback logic (skip ASR if fails, use original image if enhancement fails)
    - Ensure single component failure doesn't fail entire entry
    - Route unrecoverable errors to DLQ
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5_
  
  - [ ] 13.6 Implement batch processing optimization
    - Detect when 5+ entries are in SQS queue
    - Process entries in batches to reduce costs
    - Implement parallel invocation when resources available
    - _Requirements: 13.3, 19.3_
  
  - [ ]* 13.7 Write property test for graceful degradation
    - **Property 35: Graceful Degradation**
    - **Validates: Requirements 14.4, 14.5**
  
  - [ ]* 13.8 Write integration tests for orchestrator
    - Test end-to-end flow from SQS message to ONDC submission
    - Test error recovery and DLQ routing
    - Test batch processing
    - _Requirements: 10.1, 10.2, 13.3, 19.3_

- [ ] 14. Checkpoint - Ensure orchestrator tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 15. Implement tenant management and multi-tenancy
  - [ ] 15.1 Create tenant configuration service
    - Implement tenant data isolation in DynamoDB queries (using tenant_id partition key)
    - Create tenant-specific configuration management in DynamoDB
    - Add language preferences, ONDC credentials, cultural KB references per tenant
    - Implement tenant-level quotas and rate limiting in API Gateway
    - _Requirements: 17.1, 17.2, 17.3, 17.4_
  
  - [ ] 15.2 Implement tenant analytics and reporting
    - Create tenant-level metrics aggregation using CloudWatch Insights
    - Implement dashboard data endpoints (Lambda + API Gateway)
    - Add tenant-specific reporting queries
    - _Requirements: 17.5_
  
  - [ ]* 15.3 Write property tests for tenant isolation
    - **Property 39: Tenant Data Isolation**
    - **Property 40: Tenant Configuration Scoping**
    - **Validates: Requirements 17.1, 17.2, 17.3, 17.4**
  
  - [ ]* 15.4 Write unit tests for tenant management
    - Test data isolation between tenants
    - Test tenant-specific configuration application
    - Test quota enforcement
    - _Requirements: 17.1, 17.3, 17.4_

- [ ] 16. Implement security and encryption
  - [ ] 16.1 Configure TLS 1.3 for API Gateway
    - Set up ACM certificates for custom domain
    - Configure API Gateway with TLS 1.3 minimum version
    - Enforce HTTPS for all connections
    - _Requirements: 12.3_
  
  - [ ] 16.2 Implement data encryption at rest
    - Enable S3 bucket encryption (AES-256) for both raw and enhanced buckets
    - Enable DynamoDB encryption at rest
    - Enable SQS encryption for queue messages
    - _Requirements: 12.4_
  
  - [ ] 16.3 Implement data minimization and privacy
    - Add PII filtering in voice transcription (Bedrock prompt engineering)
    - Remove location data and device identifiers in API Gateway
    - Implement S3 lifecycle policy for media retention (30-day deletion)
    - _Requirements: 12.1, 12.2, 12.5_
  
  - [ ]* 16.4 Write property tests for encryption
    - **Property 30: Comprehensive Encryption**
    - **Validates: Requirements 12.3, 12.4**
  
  - [ ]* 16.5 Write security tests
    - Test TLS enforcement
    - Test data encryption verification
    - Test PII filtering
    - Test media deletion after retention period
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5_

- [ ] 17. Implement observability and monitoring
  - [ ] 17.1 Set up CloudWatch metrics and alarms
    - Configure Lambda to emit custom metrics (queue depth, latency, error rates, success rates)
    - Add per-operation metrics (upload, Sagemaker calls, Bedrock calls, ONDC submission)
    - Create CloudWatch dashboards for system health
    - _Requirements: 15.1, 15.5_
  
  - [ ] 17.2 Implement distributed tracing with X-Ray
    - Enable X-Ray tracing for all Lambda functions
    - Add trace context propagation across Lambda invocations
    - Instrument API Gateway, SQS, Sagemaker, and Bedrock calls
    - _Requirements: 15.4_
  
  - [ ] 17.3 Create CloudWatch alarms
    - Configure alarms for Lambda duration > 60s
    - Configure alarms for error rate > 5% over 10 minutes
    - Add cost threshold alerts ($0.50 per entry) using Cost Explorer
    - Set up SNS topics for alarm notifications
    - _Requirements: 15.2, 15.3, 13.5_
  
  - [ ]* 17.4 Write property tests for observability
    - **Property 36: Metrics Emission**
    - **Property 37: Distributed Trace Propagation**
    - **Validates: Requirements 15.1, 15.4**

- [ ] 18. Implement auto-scaling and resource management
  - [ ] 18.1 Configure Lambda auto-scaling
    - Set Lambda reserved concurrency limits based on queue depth
    - Configure SQS trigger batch size and visibility timeout
    - Set up Lambda provisioned concurrency for API Gateway handlers (optional)
    - _Requirements: 16.1, 16.2, 16.3_
  
  - [ ] 18.2 Configure API Gateway throttling
    - Set up API Gateway usage plans with rate limits
    - Configure burst limits and steady-state limits
    - Ensure stateless request handling
    - _Requirements: 16.3, 16.4_
  
  - [ ]* 18.3 Write property test for stateless scalability
    - **Property 38: Stateless Worker Scalability**
    - **Validates: Requirements 16.3, 16.4**

- [ ] 19. Checkpoint - Ensure infrastructure tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 20. Implement Edge Client (React Native or Flutter)
  - [ ] 20.1 Set up mobile project structure
    - Initialize React Native or Flutter project for Android
    - Configure for Android 8.0+ with low-RAM optimization
    - Set up local storage (SQLite) and background sync (WorkManager)
    - _Requirements: 11.1, 11.2_
  
  - [ ] 20.2 Implement camera and voice recording interface
    - Create single-button camera interface
    - Implement photo capture with on-device compression
    - Add voice recording button with audio compression
    - Ensure no text input or dropdown forms
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_
  
  - [ ] 20.3 Implement local queue management
    - Create SQLite schema for LocalQueueEntry
    - Implement queue operations (add, remove, update status)
    - Add queue persistence across app restarts
    - _Requirements: 2.1, 2.2_
  
  - [ ] 20.4 Implement background sync with retry logic
    - Create background sync worker using WorkManager
    - Implement exponential backoff retry (1min, 2min, 4min, 8min, 16min)
    - Add network connectivity detection
    - Limit retries to 5 attempts
    - _Requirements: 2.3, 2.4_
  
  - [ ] 20.5 Implement upload client with S3 multipart upload
    - Call API Gateway /upload/initiate to get presigned URLs
    - Implement chunked upload directly to S3 using presigned URLs
    - Add upload progress tracking
    - Implement upload resume on connection drop using S3 multipart upload
    - Call API Gateway /upload/complete when done
    - _Requirements: 3.1, 3.2, 3.3_
  
  - [ ] 20.6 Implement status display and notifications
    - Integrate Firebase Cloud Messaging for push notifications
    - Display status in artisan's vernacular language
    - Show preview of queued entries
    - Update preview when AI processing completes
    - _Requirements: 10.4, 10.5, 20.1, 20.4, 20.5_
  
  - [ ] 20.7 Implement preview and validation
    - Generate local preview from captured media
    - Allow artisan to review and delete queued entries
    - Display preview in vernacular language
    - _Requirements: 20.1, 20.2, 20.3, 20.5_
  
  - [ ] 20.8 Implement bulk catalog operations
    - Allow sequential capture of multiple products
    - Display progress for each entry independently
    - Allow review and deletion before sync
    - _Requirements: 19.1, 19.2, 19.4_
  
  - [ ]* 20.9 Write property tests for Edge Client
    - **Property 3: Queue Lifecycle Consistency**
    - **Property 4: Offline Queue Persistence**
    - **Property 5: Exponential Backoff Retry**
    - **Validates: Requirements 2.1, 2.2, 2.4, 2.5**
  
  - [ ]* 20.10 Write unit tests for Edge Client
    - Test camera and voice capture
    - Test local queue operations
    - Test background sync and retry logic
    - Test upload resumption
    - Test status display and preview
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.3, 3.2, 20.1_

- [ ] 21. Integration and end-to-end testing
  - [ ] 21.1 Set up AWS integration test environment
    - Deploy all Lambda functions, API Gateway, SQS, S3, DynamoDB in test AWS account
    - Configure test Sagemaker endpoint and Bedrock access
    - Set up mock ONDC API endpoint
    - _Requirements: All_
  
  - [ ] 21.2 Write end-to-end flow tests
    - Test: Capture → Queue → Upload → Process → Submit → Notify
    - Test: Offline capture → Online sync → Process → Submit
    - Test: Failed processing → Retry → Success
    - Test: Failed ONDC submission → Retry → Success
    - Test: Update existing catalog entry → Version history
    - _Requirements: All_
  
  - [ ] 21.3 Write component integration tests
    - Test Edge Client ↔ API Gateway (upload resumption)
    - Test API Gateway ↔ SQS (message publishing)
    - Test SQS ↔ Lambda Orchestrator (message consumption)
    - Test Lambda ↔ S3 (media retrieval)
    - Test Lambda ↔ Sagemaker (Vision + ASR)
    - Test Lambda ↔ Bedrock (transcreation)
    - Test Lambda ↔ ONDC Gateway (submission)
    - Test Lambda ↔ SNS (notification publishing)
    - _Requirements: All_
  
  - [ ]* 21.4 Run performance and load tests
    - Test 1000 concurrent uploads
    - Test 10,000 queued entries processing
    - Test 100 requests/second to API Gateway
    - Test burst traffic (0 → 500 requests in 1 minute)
    - Verify p95 latency benchmarks
    - _Requirements: 15.1, 16.1, 16.2_

- [ ] 22. Final checkpoint - Ensure all tests pass
  - Run complete test suite (unit, property, integration, e2e)
  - Verify all 49 correctness properties pass
  - Ensure performance benchmarks are met
  - Ask the user if questions arise.

- [ ] 23. Documentation and deployment preparation
  - [ ] 23.1 Create AWS deployment documentation
    - Document AWS infrastructure requirements (CDK/Terraform)
    - Create deployment scripts and CI/CD pipeline configuration
    - Document environment variables and AWS secrets
    - Document IAM roles and permissions
    - _Requirements: All_
  
  - [ ] 23.2 Create API documentation
    - Generate OpenAPI/Swagger documentation for API Gateway
    - Document SQS message contracts
    - Document ONDC integration details
    - Document Sagemaker and Bedrock integration
    - _Requirements: 3.1, 8.1, 9.1_
  
  - [ ] 23.3 Create operational runbooks
    - Document CloudWatch monitoring and alerting setup
    - Create troubleshooting guides for common issues
    - Document backup and recovery procedures for DynamoDB
    - Document cost optimization strategies
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5_

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties (49 total)
- Unit tests validate specific examples and edge cases
- Implementation uses AWS serverless architecture: Lambda (Python), API Gateway, SQS, S3, DynamoDB, Sagemaker, Bedrock
- Edge Client uses React Native or Flutter (to be decided during implementation)
- All 49 correctness properties from the design document should have corresponding property tests
- Integration tests verify end-to-end flows across all AWS components

## Architecture Alignment Notes

The actual implementation (shown in `generate_architecture_diagram.py`) uses AWS managed services that simplify the detailed design.md architecture:

**Simplifications**:
- **Vision + ASR Combined**: Single Sagemaker endpoint handles both image analysis and audio transcription (instead of separate services)
- **Bedrock for LLM**: AWS Bedrock provides transcreation and attribute extraction (replaces separate LLM orchestrator)
- **No Separate RAG System**: Cultural knowledge and CSI identification handled via Bedrock prompt engineering or knowledge bases (not separate vector DB)
- **Lambda Orchestrator**: Single Lambda function coordinates the entire pipeline (replaces separate worker services)
- **DynamoDB**: NoSQL database for metadata (instead of PostgreSQL)
- **SNS for Notifications**: AWS SNS publishes notifications (Firebase integration is optional in Edge Client)
- **Schema Mapping in Lambda**: ONDC schema mapping and validation happens inside Lambda Orchestrator (not separate service)

**What Stays the Same**:
- All 20 requirements remain valid and must be implemented
- All 49 correctness properties must be tested
- Edge Client architecture (offline-first, local queue, background sync)
- ONDC integration and Beckn protocol compliance
- Security, encryption, multi-tenancy, observability requirements

This is an implementation choice - the requirements define WHAT the system must do, the architecture defines HOW using AWS services.
