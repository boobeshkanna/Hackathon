# Requirements Document: Vernacular Artisan Catalog

## Introduction

This document specifies requirements for a Zero-UI Edge-Native AI Application that enables vernacular artisans in rural India to catalog products on the Open Network for Digital Commerce (ONDC). The system addresses "Cataloging Paralysis" - the fundamental mismatch between high-context vernacular storytelling and low-context structured digital schemas required by ONDC.

The solution enables artisans to capture a photo and record a voice note in their native language. AI processing then generates ONDC-compliant catalog entries without requiring form-filling, English proficiency, or continuous connectivity.

## Glossary

- **Artisan**: A vernacular craftsperson in rural India who is WhatsApp-literate but app-illiterate
- **Cataloging_Paralysis**: The cognitive and technical barrier preventing artisans from creating structured digital product catalogs
- **CSI**: Cultural Specific Item - culturally significant product attributes that must be preserved during processing
- **Edge_Client**: The mobile application running on the artisan's low-RAM Android device
- **AI_Pipeline**: The backend service that processes media into structured catalog data
- **ONDC_Gateway**: The service that formats and submits catalog entries to ONDC using Beckn protocol
- **Async_Queue**: The message queue system that enables offline-first operation and retry logic
- **Transcreation**: Cultural adaptation that preserves meaning and context, not literal translation
- **RAG_System**: Retrieval-Augmented Generation system with cultural knowledge base
- **Schema_Validator**: Component that enforces ONDC/Beckn protocol compliance

## Requirements

### Requirement 1: Zero-UI Media Capture

**User Story:** As an artisan, I want to capture product information by taking a photo and recording a voice note, so that I can catalog products without filling forms or typing text.

#### Acceptance Criteria

1. WHEN the artisan opens the application, THE Edge_Client SHALL display a camera interface with a single capture button
2. WHEN the artisan captures a photo, THE Edge_Client SHALL immediately compress the image to reduce file size while preserving product details
3. WHEN the artisan presses the voice recording button, THE Edge_Client SHALL record audio in the artisan's vernacular language
4. WHEN the artisan completes voice recording, THE Edge_Client SHALL compress the audio file for efficient transmission
5. THE Edge_Client SHALL support photo capture and voice recording without requiring text input or dropdown selections

### Requirement 2: Offline-First Local Queueing

**User Story:** As an artisan with intermittent connectivity, I want my catalog submissions to be queued locally, so that network interruptions don't cause data loss.

#### Acceptance Criteria

1. WHEN media is captured, THE Edge_Client SHALL store the compressed photo and audio in a persistent local queue
2. WHEN network connectivity is unavailable, THE Edge_Client SHALL continue accepting new catalog entries and adding them to the local queue
3. WHEN network connectivity is restored, THE Edge_Client SHALL automatically begin syncing queued entries in background
4. IF a sync attempt fails, THEN THE Edge_Client SHALL retry with exponential backoff up to 5 attempts
5. WHEN a queued entry is successfully synced, THE Edge_Client SHALL remove it from the local queue and notify the artisan

### Requirement 3: Asynchronous Upload API

**User Story:** As an artisan, I want uploads to continue even if my connection drops mid-transfer, so that I don't waste time and data re-uploading.

#### Acceptance Criteria

1. WHEN the Edge_Client initiates an upload, THE Async_API_Gateway SHALL accept multipart resumable uploads
2. IF a connection drops during upload, THEN THE Async_API_Gateway SHALL preserve the partial upload state
3. WHEN the Edge_Client reconnects, THE Async_API_Gateway SHALL allow resuming the upload from the last successful chunk
4. WHEN an upload completes, THE Async_API_Gateway SHALL enqueue the media for AI processing and return an acknowledgment immediately
5. THE Async_API_Gateway SHALL not block or timeout during AI processing

### Requirement 4: Automatic Speech Recognition for Vernacular Languages

**User Story:** As an artisan speaking in my native language, I want my voice description to be accurately transcribed, so that my product story is captured correctly.

#### Acceptance Criteria

1. WHEN audio is received, THE AI_Pipeline SHALL transcribe it using a vernacular-capable ASR model
2. THE AI_Pipeline SHALL support transcription for Hindi, Tamil, Telugu, Bengali, Marathi, Gujarati, Kannada, Malayalam, Punjabi, and Odia
3. WHEN transcription is complete, THE AI_Pipeline SHALL preserve the original vernacular text without forcing English translation
4. IF the ASR model cannot confidently transcribe a segment, THEN THE AI_Pipeline SHALL flag it for manual review rather than generating incorrect text
5. THE AI_Pipeline SHALL complete transcription within 30 seconds for audio files up to 2 minutes in duration

### Requirement 5: Cultural Knowledge Preservation

**User Story:** As an artisan describing traditional products, I want culturally specific terms and concepts to be preserved, so that my product's cultural significance is not lost.

#### Acceptance Criteria

1. WHEN processing vernacular descriptions, THE RAG_System SHALL query a cultural knowledge base for CSI identification
2. WHEN a CSI is identified, THE AI_Pipeline SHALL preserve the original vernacular term and add contextual metadata
3. THE RAG_System SHALL maintain knowledge of traditional craft techniques, regional product names, and cultural significance markers
4. WHEN generating catalog descriptions, THE AI_Pipeline SHALL use transcreation that preserves cultural context rather than literal translation
5. THE AI_Pipeline SHALL not replace culturally specific terms with generic English equivalents

### Requirement 6: Image Enhancement and Product Extraction

**User Story:** As an artisan taking photos in variable lighting conditions, I want the system to enhance my product images, so that they look professional in the catalog.

#### Acceptance Criteria

1. WHEN an image is received, THE AI_Pipeline SHALL detect and extract the primary product from the background
2. WHEN lighting is poor, THE AI_Pipeline SHALL enhance brightness and contrast to improve product visibility
3. WHEN the image is blurry, THE AI_Pipeline SHALL apply sharpening filters within acceptable quality thresholds
4. THE AI_Pipeline SHALL generate multiple image sizes optimized for different display contexts
5. IF the image quality is too poor for enhancement, THEN THE AI_Pipeline SHALL notify the artisan to retake the photo

### Requirement 7: Attribute Extraction from Multimodal Input

**User Story:** As an artisan, I want the system to automatically extract product attributes from my photo and voice description, so that I don't have to fill structured forms.

#### Acceptance Criteria

1. WHEN processing a catalog entry, THE AI_Pipeline SHALL extract product category from both image and transcribed text
2. WHEN extracting attributes, THE AI_Pipeline SHALL identify material, color, dimensions, weight, and craftsmanship technique
3. WHEN voice description mentions price, THE AI_Pipeline SHALL extract and normalize the price value
4. WHEN attributes conflict between image and voice, THE AI_Pipeline SHALL prioritize voice description as authoritative
5. THE AI_Pipeline SHALL generate confidence scores for each extracted attribute

### Requirement 8: ONDC Schema Mapping and Validation

**User Story:** As a system operator, I want extracted attributes to be mapped to ONDC-compliant schemas, so that catalog entries are accepted by the ONDC network.

#### Acceptance Criteria

1. WHEN attributes are extracted, THE ONDC_Gateway SHALL map them to Beckn protocol schema fields
2. THE Schema_Validator SHALL validate the mapped payload against ONDC catalog specification before submission
3. IF validation fails, THEN THE ONDC_Gateway SHALL log specific schema violations and attempt automatic correction
4. WHEN automatic correction is not possible, THE ONDC_Gateway SHALL flag the entry for manual review
5. THE ONDC_Gateway SHALL ensure all mandatory ONDC fields are populated before submission

### Requirement 9: Deterministic ONDC Submission

**User Story:** As a system operator, I want catalog submissions to ONDC to be reliable and traceable, so that I can debug failures and ensure data integrity.

#### Acceptance Criteria

1. WHEN submitting to ONDC, THE ONDC_Gateway SHALL generate a unique idempotency key for each catalog entry
2. IF a submission fails, THEN THE ONDC_Gateway SHALL retry with the same idempotency key to prevent duplicates
3. WHEN ONDC returns an error, THE ONDC_Gateway SHALL parse the error response and categorize it as retryable or permanent
4. THE ONDC_Gateway SHALL maintain an audit log of all submission attempts with timestamps and response codes
5. WHEN a submission succeeds, THE ONDC_Gateway SHALL store the ONDC-assigned catalog ID for future updates

### Requirement 10: Asynchronous Status Notification

**User Story:** As an artisan, I want to be notified when my catalog entry is successfully published, so that I know my product is live on ONDC.

#### Acceptance Criteria

1. WHEN AI processing completes, THE AI_Pipeline SHALL publish a status event to the Async_Queue
2. WHEN ONDC submission completes, THE ONDC_Gateway SHALL publish a status event to the Async_Queue
3. WHEN a status event is published, THE Notification_Service SHALL send a push notification to the Edge_Client
4. THE Edge_Client SHALL display status updates in the artisan's vernacular language
5. IF processing fails at any stage, THE Notification_Service SHALL notify the artisan with a simple explanation in their language

### Requirement 11: Low-RAM Device Optimization

**User Story:** As an artisan using a budget Android device with limited RAM, I want the application to run smoothly, so that I can catalog products without the app crashing.

#### Acceptance Criteria

1. THE Edge_Client SHALL operate within 512MB RAM budget on Android devices
2. WHEN capturing media, THE Edge_Client SHALL stream compressed data to storage rather than loading full files in memory
3. THE Edge_Client SHALL release memory immediately after media capture and compression
4. THE Edge_Client SHALL limit background processes to essential sync operations only
5. WHEN memory pressure is detected, THE Edge_Client SHALL pause non-critical operations and prioritize core capture functionality

### Requirement 12: Data Minimization and Privacy

**User Story:** As an artisan, I want my personal data to be protected, so that my privacy is respected and my data is not misused.

#### Acceptance Criteria

1. THE Edge_Client SHALL not collect or transmit location data, device identifiers, or personal information beyond what is necessary for catalog creation
2. WHEN processing voice recordings, THE AI_Pipeline SHALL extract only product-related information and discard personal conversations
3. THE System SHALL encrypt all media files in transit using TLS 1.3
4. THE System SHALL encrypt all media files at rest using AES-256
5. WHEN a catalog entry is published, THE System SHALL delete the original media files after 30 days unless the artisan opts to retain them

### Requirement 13: Cost-Optimized Processing

**User Story:** As a system operator, I want AI processing costs to be minimized, so that the service remains economically sustainable for rural artisans.

#### Acceptance Criteria

1. THE AI_Pipeline SHALL use the smallest model that meets accuracy requirements for each processing task
2. WHEN processing images, THE AI_Pipeline SHALL resize to minimum dimensions required for attribute extraction before running vision models
3. THE AI_Pipeline SHALL batch multiple catalog entries for processing when possible to reduce per-item costs
4. THE System SHALL use spot instances or preemptible VMs for non-time-critical processing tasks
5. THE System SHALL monitor per-catalog-entry processing costs and alert when costs exceed defined thresholds

### Requirement 14: Fault Tolerance and Graceful Degradation

**User Story:** As an artisan, I want the system to continue working even when some components fail, so that I can still catalog products during partial outages.

#### Acceptance Criteria

1. IF the ASR service fails, THEN THE AI_Pipeline SHALL allow manual transcription as a fallback
2. IF the image enhancement service fails, THEN THE AI_Pipeline SHALL proceed with the original image
3. IF the RAG_System is unavailable, THEN THE AI_Pipeline SHALL proceed with basic attribute extraction without cultural context
4. WHEN a non-critical service fails, THE System SHALL log the failure and continue processing with degraded functionality
5. THE System SHALL not fail the entire catalog entry due to a single component failure

### Requirement 15: Observability and Monitoring

**User Story:** As a system operator, I want comprehensive monitoring of system health, so that I can proactively identify and resolve issues.

#### Acceptance Criteria

1. THE System SHALL emit metrics for queue depth, processing latency, error rates, and ONDC submission success rates
2. WHEN processing latency exceeds 60 seconds, THE System SHALL trigger an alert
3. WHEN error rates exceed 5% over a 10-minute window, THE System SHALL trigger an alert
4. THE System SHALL maintain distributed traces across all components for end-to-end request tracking
5. THE System SHALL provide a dashboard showing real-time system health and key performance indicators

### Requirement 16: Horizontal Scalability

**User Story:** As a system operator, I want the system to scale automatically during peak usage, so that artisans experience consistent performance.

#### Acceptance Criteria

1. WHEN queue depth exceeds 100 entries, THE System SHALL automatically scale up AI_Pipeline workers
2. WHEN queue depth falls below 20 entries, THE System SHALL automatically scale down AI_Pipeline workers to reduce costs
3. THE Async_API_Gateway SHALL support horizontal scaling without session affinity requirements
4. THE System SHALL use stateless processing workers that can be added or removed without data loss
5. THE System SHALL complete auto-scaling operations within 5 minutes of threshold breach

### Requirement 17: Multi-Tenancy Support

**User Story:** As a system operator, I want to support multiple artisan cooperatives or organizations, so that the platform can serve diverse communities.

#### Acceptance Criteria

1. THE System SHALL isolate data between different tenant organizations
2. WHEN an artisan registers, THE Edge_Client SHALL associate them with a specific tenant identifier
3. THE System SHALL apply tenant-specific configuration for language preferences, cultural knowledge bases, and ONDC seller credentials
4. THE System SHALL enforce tenant-level quotas for API usage and storage
5. THE System SHALL provide tenant-level analytics and reporting

### Requirement 18: Catalog Update and Versioning

**User Story:** As an artisan, I want to update my product catalog entries, so that I can correct errors or update product information.

#### Acceptance Criteria

1. WHEN an artisan submits a new catalog entry for an existing product, THE System SHALL detect it as an update rather than a new entry
2. THE ONDC_Gateway SHALL use the ONDC update API to modify existing catalog entries
3. THE System SHALL maintain version history of catalog entries for audit purposes
4. WHEN an update is submitted, THE System SHALL preserve the original ONDC catalog ID
5. THE System SHALL notify the artisan when the update is successfully published to ONDC

### Requirement 19: Bulk Catalog Operations

**User Story:** As an artisan with multiple products, I want to catalog several products in a batch session, so that I can efficiently manage my inventory.

#### Acceptance Criteria

1. THE Edge_Client SHALL allow capturing multiple product entries in sequence without returning to a home screen
2. WHEN multiple entries are queued, THE Edge_Client SHALL display progress for each entry independently
3. THE System SHALL process queued entries in parallel when resources are available
4. THE Edge_Client SHALL allow the artisan to review and delete queued entries before they are synced
5. WHEN all entries in a batch are processed, THE System SHALL send a summary notification to the artisan

### Requirement 20: Offline Preview and Validation

**User Story:** As an artisan, I want to preview how my catalog entry will look before it's published, so that I can verify the information is correct.

#### Acceptance Criteria

1. WHEN a catalog entry is queued locally, THE Edge_Client SHALL generate a preview using the captured media
2. THE Edge_Client SHALL display the preview in a simple card format with product image and basic details
3. THE Edge_Client SHALL allow the artisan to delete or retake a queued entry before sync
4. WHEN AI processing completes, THE Edge_Client SHALL update the preview with extracted attributes
5. THE Edge_Client SHALL display the preview in the artisan's vernacular language
