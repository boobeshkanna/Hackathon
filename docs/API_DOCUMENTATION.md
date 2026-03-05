# API Documentation: Vernacular Artisan Catalog

## Overview

The Vernacular Artisan Catalog API enables rural artisans to catalog products on ONDC through simple photo and voice capture. The system provides a RESTful API for resumable uploads, asynchronous processing with AI models (Sagemaker Vision+ASR, Bedrock LLM), and ONDC integration via the Beckn protocol.

**Base URL**: `https://api.vernacular-catalog.example.com`

**API Version**: v1

**Authentication**: Bearer token (tenant-specific API keys)

**Content Type**: `application/json`

---

## Table of Contents

1. [API Gateway Endpoints](#api-gateway-endpoints)
2. [SQS Message Contracts](#sqs-message-contracts)
3. [ONDC Integration](#ondc-integration)
4. [Sagemaker Integration](#sagemaker-integration)
5. [Bedrock Integration](#bedrock-integration)
6. [Data Models](#data-models)
7. [Error Handling](#error-handling)
8. [OpenAPI Specification](#openapi-specification)

---

## API Gateway Endpoints

### 1. Initiate Upload

**Endpoint**: `POST /v1/catalog/upload/initiate`

**Description**: Initiates a resumable upload by generating presigned S3 URLs for media files.

**Requirements**: 3.1, 3.2

**Request Headers**:
```
Authorization: Bearer <tenant_api_key>
Content-Type: application/json
```

**Request Body**:
```json
{
  "tenant_id": "tenant_12345",
  "artisan_id": "artisan_67890",
  "content_type": "image/jpeg"
}
```

**Request Parameters**:
- `tenant_id` (string, required): Tenant organization identifier
- `artisan_id` (string, required): Artisan identifier
- `content_type` (string, required): MIME type (`image/jpeg`, `image/png`, `audio/opus`, `audio/mpeg`, `audio/wav`)

**Response** (200 OK):
```json
{
  "tracking_id": "trk_abc123xyz",
  "upload_url": "https://s3.amazonaws.com/bucket/path?signature=...",
  "expires_at": "2024-02-26T11:00:00Z"
}
```

**Response Fields**:
- `tracking_id` (string): Unique tracking identifier for this upload
- `upload_url` (string): Presigned S3 URL for direct upload (valid for 1 hour)
- `expires_at` (string): ISO 8601 timestamp when the upload URL expires

**Error Responses**:
- `400 Bad Request`: Invalid content type or missing required fields
- `401 Unauthorized`: Invalid or missing API key
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

**Example cURL**:
```bash
curl -X POST https://api.vernacular-catalog.example.com/v1/catalog/upload/initiate \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "tenant_12345",
    "artisan_id": "artisan_67890",
    "content_type": "image/jpeg"
  }'
```

---

### 2. Complete Upload

**Endpoint**: `POST /v1/catalog/upload/complete`

**Description**: Completes the upload and enqueues the media for AI processing.

**Requirements**: 3.4, 9.1

**Request Headers**:
```
Authorization: Bearer <tenant_api_key>
Content-Type: application/json
```

**Request Body**:
```json
{
  "tracking_id": "trk_abc123xyz",
  "photo_key": "tenant_12345/artisan_67890/trk_abc123xyz.jpg",
  "audio_key": "tenant_12345/artisan_67890/trk_abc123xyz.opus",
  "language": "hi"
}
```

**Request Parameters**:
- `tracking_id` (string, required): Tracking ID from initiate upload
- `photo_key` (string, optional): S3 key for uploaded photo
- `audio_key` (string, optional): S3 key for uploaded audio
- `language` (string, required): Language code (`hi`, `ta`, `te`, `bn`, `mr`, `gu`, `kn`, `ml`, `pa`, `or`)

**Note**: At least one of `photo_key` or `audio_key` must be provided.

**Response** (200 OK):
```json
{
  "status": "accepted",
  "tracking_id": "trk_abc123xyz",
  "message": "Upload accepted and queued for processing"
}
```

**Error Responses**:
- `400 Bad Request`: Missing tracking_id or both media keys
- `404 Not Found`: Tracking ID not found
- `500 Internal Server Error`: Server error

**Example cURL**:
```bash
curl -X POST https://api.vernacular-catalog.example.com/v1/catalog/upload/complete \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "tracking_id": "trk_abc123xyz",
    "photo_key": "tenant_12345/artisan_67890/trk_abc123xyz.jpg",
    "audio_key": "tenant_12345/artisan_67890/trk_abc123xyz.opus",
    "language": "hi"
  }'
```

---

### 3. Get Status

**Endpoint**: `GET /v1/catalog/status/{trackingId}`

**Description**: Retrieves the current processing status for a catalog entry.

**Requirements**: 10.1, 10.2

**Request Headers**:
```
Authorization: Bearer <tenant_api_key>
```

**Path Parameters**:
- `trackingId` (string, required): Tracking identifier

**Response** (200 OK):
```json
{
  "tracking_id": "trk_abc123xyz",
  "stage": "completed",
  "message": "Catalog entry successfully published to ONDC",
  "catalog_id": "ondc_cat_789",
  "timestamp": "2024-02-26T10:05:00Z"
}
```

**Response Fields**:
- `tracking_id` (string): Tracking identifier
- `stage` (string): Current processing stage
  - `uploaded`: Media uploaded, queued for processing
  - `processing`: AI models processing media
  - `extraction`: Extracting product attributes
  - `mapping`: Mapping to ONDC format
  - `completed`: Successfully published to ONDC
  - `failed`: Processing failed
- `message` (string): Human-readable status message
- `catalog_id` (string, optional): ONDC catalog ID (only present when completed)
- `error_details` (object, optional): Error information (only present when failed)
- `timestamp` (string): ISO 8601 timestamp

**Error Responses**:
- `404 Not Found`: Tracking ID not found
- `500 Internal Server Error`: Server error

**Example cURL**:
```bash
curl -X GET https://api.vernacular-catalog.example.com/v1/catalog/status/trk_abc123xyz \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

## SQS Message Contracts

### Catalog Processing Message

**Queue**: `vernacular-catalog-processing-queue`

**Message Type**: Catalog processing request

**Requirements**: 3.4, 9.1

**Message Body**:
```json
{
  "trackingId": "trk_abc123xyz",
  "tenantId": "tenant_12345",
  "artisanId": "artisan_67890",
  "photoKey": "tenant_12345/artisan_67890/trk_abc123xyz.jpg",
  "audioKey": "tenant_12345/artisan_67890/trk_abc123xyz.opus",
  "language": "hi",
  "priority": "normal",
  "timestamp": "2024-02-26T10:00:00Z",
  "metadata": {
    "location": "Jaipur",
    "category_hint": "handicraft"
  }
}
```

**Message Attributes**:
```json
{
  "TrackingId": {
    "StringValue": "trk_abc123xyz",
    "DataType": "String"
  },
  "TenantId": {
    "StringValue": "tenant_12345",
    "DataType": "String"
  },
  "Priority": {
    "StringValue": "normal",
    "DataType": "String"
  },
  "Language": {
    "StringValue": "hi",
    "DataType": "String"
  }
}
```

**Idempotency**:
- For FIFO queues: `MessageDeduplicationId` is SHA-256 hash of `trackingId|tenantId|artisanId`
- For FIFO queues: `MessageGroupId` is `tenantId` (ensures ordering per tenant)

**Processing Flow**:
1. Message published to SQS after upload completion
2. Lambda Orchestrator consumes message
3. Orchestrator invokes Sagemaker (Vision+ASR)
4. Orchestrator invokes Bedrock (attribute extraction, transcreation)
5. Orchestrator maps to ONDC schema and validates
6. Orchestrator submits to ONDC Gateway
7. Status update published to notification queue

---

### Status Update Message

**Queue**: `vernacular-catalog-status-updates`

**Message Type**: Status notification

**Requirements**: 10.1, 10.2, 10.3

**Message Body**:
```json
{
  "trackingId": "trk_abc123xyz",
  "stage": "completed",
  "status": "success",
  "message": "Catalog entry successfully published to ONDC",
  "catalogId": "ondc_cat_789",
  "timestamp": "2024-02-26T10:05:00Z"
}
```

**Message Attributes**:
```json
{
  "MessageType": {
    "StringValue": "StatusUpdate",
    "DataType": "String"
  },
  "TrackingId": {
    "StringValue": "trk_abc123xyz",
    "DataType": "String"
  },
  "Stage": {
    "StringValue": "completed",
    "DataType": "String"
  }
}
```

**Stages**:
- `uploaded`: Media uploaded successfully
- `processing`: AI processing in progress
- `extraction`: Attribute extraction in progress
- `mapping`: ONDC schema mapping in progress
- `completed`: Successfully published to ONDC
- `failed`: Processing failed

**Consumer**: Notification Service (sends push notifications to Edge Client via Firebase Cloud Messaging)

---

## ONDC Integration

### Beckn Protocol Catalog Submission

**Endpoint**: `POST /beckn/catalog/on_search`

**Description**: Submits catalog entries to ONDC using the Beckn protocol.

**Requirements**: 8.1, 9.1

**Authentication**: ONDC Seller credentials (configured per tenant)

**Request Headers**:
```
Content-Type: application/json
Authorization: Bearer <ondc_seller_token>
```

**Request Body** (Beckn Protocol):
```json
{
  "context": {
    "domain": "retail",
    "country": "IND",
    "action": "on_search",
    "bap_id": "buyer-app-id",
    "bpp_id": "seller-app-id-tenant-12345",
    "transaction_id": "txn_abc123",
    "message_id": "msg_xyz789",
    "timestamp": "2024-02-26T10:05:00Z"
  },
  "message": {
    "catalog": {
      "bpp/providers": [
        {
          "id": "provider-tenant-12345",
          "items": [
            {
              "id": "item_a1b2c3d4e5f6g7h8",
              "descriptor": {
                "name": "Handwoven Banarasi Silk Saree",
                "short_desc": "Traditional handwoven silk saree with intricate zari work",
                "long_desc": "This exquisite Banarasi silk saree is handwoven on traditional pit looms...\n\nCultural Significance:\n• बनारसी (Banarasi): Traditional weaving technique from Varanasi...\n\nCraft Technique: Handwoven on pit loom\nRegion of Origin: Varanasi, Uttar Pradesh",
                "images": [
                  "https://s3.amazonaws.com/enhanced-bucket/tenant_12345/artisan_67890/trk_abc123xyz_full.jpg",
                  "https://s3.amazonaws.com/enhanced-bucket/tenant_12345/artisan_67890/trk_abc123xyz_medium.jpg"
                ]
              },
              "price": {
                "currency": "INR",
                "value": "8500"
              },
              "category_id": "Fashion:Ethnic Wear:Sarees",
              "tags": {
                "material": "silk,zari",
                "color": "red,gold,maroon",
                "craft_technique": "Handwoven on pit loom",
                "region": "Varanasi, Uttar Pradesh",
                "csi_1_term": "बनारसी",
                "csi_1_transliteration": "Banarasi",
                "csi_1_context": "Traditional weaving technique from Varanasi"
              }
            }
          ]
        }
      ]
    }
  }
}
```

**Response** (200 OK):
```json
{
  "context": {
    "domain": "retail",
    "country": "IND",
    "action": "on_search",
    "bap_id": "buyer-app-id",
    "bpp_id": "seller-app-id-tenant-12345",
    "transaction_id": "txn_abc123",
    "message_id": "msg_xyz789",
    "timestamp": "2024-02-26T10:05:01Z"
  },
  "message": {
    "ack": {
      "status": "ACK"
    }
  },
  "catalog_id": "ondc_cat_789"
}
```

**Error Response** (400 Bad Request):
```json
{
  "context": { ... },
  "error": {
    "type": "VALIDATION_ERROR",
    "code": "30001",
    "message": "Invalid catalog schema",
    "path": "message.catalog.bpp/providers[0].items[0].descriptor.name"
  }
}
```

---

### ONDC Schema Mapping

**Source**: `ExtractedAttributes` (from Bedrock LLM)

**Target**: `ONDCCatalogItem` (Beckn protocol)

**Mapping Rules**:

| Extracted Attribute | Beckn Field | Transformation |
|---------------------|-------------|----------------|
| `category` | `category_id` | Mapped to ONDC taxonomy (see Category Mapping) |
| `short_description` | `descriptor.name` | Truncated to 100 chars |
| `short_description` | `descriptor.short_desc` | Truncated to 500 chars |
| `long_description` + `csis` | `descriptor.long_desc` | Combined with CSI section |
| `price.value` | `price.value` | Converted to string |
| `price.currency` | `price.currency` | Default "INR" |
| `material` | `tags.material` | Comma-separated list |
| `colors` | `tags.color` | Comma-separated list |
| `craft_technique` | `tags.craft_technique` | Direct mapping |
| `region_of_origin` | `tags.region` | Direct mapping |
| `csis[i].vernacular_term` | `tags.csi_{i+1}_term` | Direct mapping |
| `csis[i].transliteration` | `tags.csi_{i+1}_transliteration` | Direct mapping |
| `csis[i].english_context` | `tags.csi_{i+1}_context` | Direct mapping |

**Item ID Generation**:
```python
# Deterministic hash of core attributes
id_components = [category, subcategory, materials, colors, price]
hash_input = '|'.join(id_components)
item_id = f"item_{sha256(hash_input)[:16]}"
```

**Category Mapping** (Sample):
```
handloom saree → Fashion:Ethnic Wear:Sarees
pottery → Home & Decor:Handicrafts:Pottery
jewelry → Fashion:Jewelry:Handcrafted
wooden toy → Toys & Games:Traditional Toys:Wooden
brass → Home & Decor:Handicrafts:Brass
basket → Home & Decor:Storage:Baskets
```

---

### ONDC Validation Rules

**Requirements**: 8.2, 8.5

**Mandatory Fields**:
- `descriptor.name` (max 100 chars)
- `descriptor.short_desc` (max 500 chars)
- `descriptor.images` (at least 1 image URL)
- `price.value` (numeric string)
- `price.currency` (ISO 4217 code)
- `category_id` (valid ONDC taxonomy)

**Validation Errors**:
```json
{
  "is_valid": false,
  "errors": [
    "descriptor.name is required",
    "descriptor.name must be <= 100 characters",
    "price.value must be numeric string",
    "At least one image is required",
    "Invalid image URL: http://invalid-url"
  ]
}
```

**Auto-Correction**:
- Truncate `descriptor.name` to 100 chars (add "...")
- Truncate `descriptor.short_desc` to 500 chars (add "...")
- Convert numeric price to string
- Remove invalid image URLs

**Manual Review Flagging**:
- Missing mandatory fields that cannot be auto-corrected
- Invalid category that cannot be mapped
- All images are invalid URLs

---

## Sagemaker Integration

### Combined Vision + ASR Endpoint

**Endpoint Name**: `vernacular-vision-asr-endpoint`

**Description**: Multimodal Sagemaker endpoint that processes both image and audio inputs.

**Requirements**: 4.1, 4.2, 4.3, 6.1, 7.1

**Input Format**:
```json
{
  "image": "<base64_encoded_image>",
  "audio": "<base64_encoded_audio>",
  "language_hint": "hi"
}
```

**Input Parameters**:
- `image` (string, optional): Base64-encoded image (JPEG, PNG)
- `audio` (string, optional): Base64-encoded audio (Opus, MP3, WAV)
- `language_hint` (string, optional): Expected language code for ASR

**Output Format**:
```json
{
  "transcription": {
    "text": "यह एक हाथ से बुनी हुई रेशमी साड़ी है",
    "language": "hi",
    "confidence": 0.92,
    "low_confidence": false,
    "requires_manual_review": false,
    "segments": [
      {
        "text": "यह एक हाथ से बुनी हुई",
        "start": 0.0,
        "end": 2.5,
        "confidence": 0.95,
        "low_confidence": false
      },
      {
        "text": "रेशमी साड़ी है",
        "start": 2.5,
        "end": 4.0,
        "confidence": 0.89,
        "low_confidence": false
      }
    ]
  },
  "vision": {
    "category": "Handloom Saree",
    "subcategory": "Silk Saree",
    "colors": ["red", "gold", "maroon"],
    "materials": ["silk", "zari"],
    "confidence": 0.87,
    "low_confidence": false,
    "requires_manual_review": false,
    "bounding_box": {
      "x": 120,
      "y": 80,
      "width": 800,
      "height": 1200
    }
  },
  "processing_time_ms": 1250
}
```

**Confidence Thresholds**:
- ASR: 0.7 (segments below this are flagged for manual review)
- Vision: 0.6 (results below this are flagged for manual review)

**Supported Languages**:
- `hi` - Hindi
- `ta` - Tamil
- `te` - Telugu
- `bn` - Bengali
- `mr` - Marathi
- `gu` - Gujarati
- `kn` - Kannada
- `ml` - Malayalam
- `pa` - Punjabi
- `or` - Odia

**Error Handling**:
- Timeout: 30 seconds (configurable)
- Max Retries: 3 attempts with exponential backoff
- Transient errors (5xx, timeouts) are retried
- Permanent errors (4xx) are not retried

**Example Invocation** (Python):
```python
import boto3
import json
import base64

client = boto3.client('sagemaker-runtime', region_name='ap-south-1')

# Load media
with open('product.jpg', 'rb') as f:
    image_b64 = base64.b64encode(f.read()).decode('utf-8')

with open('product.opus', 'rb') as f:
    audio_b64 = base64.b64encode(f.read()).decode('utf-8')

# Invoke endpoint
response = client.invoke_endpoint(
    EndpointName='vernacular-vision-asr-endpoint',
    ContentType='application/json',
    Body=json.dumps({
        'image': image_b64,
        'audio': audio_b64,
        'language_hint': 'hi'
    })
)

result = json.loads(response['Body'].read())
print(result)
```

---

## Bedrock Integration

### Attribute Extraction and Transcreation

**Model**: Amazon Bedrock (Claude 3 or similar)

**Description**: LLM-based attribute extraction and cultural transcreation.

**Requirements**: 5.1, 5.2, 5.4, 7.1, 7.2, 7.3, 7.4

**Input Format**:
```json
{
  "transcription": {
    "text": "यह एक हाथ से बुनी हुई रेशमी साड़ी है...",
    "language": "hi",
    "confidence": 0.92
  },
  "vision": {
    "category": "Handloom Saree",
    "colors": ["red", "gold", "maroon"],
    "materials": ["silk", "zari"],
    "confidence": 0.87
  },
  "tenant_config": {
    "cultural_kb_id": "kb_indian_textiles",
    "default_language": "hi"
  }
}
```

**Prompt Template**:
```
You are an expert in Indian handicrafts and cultural preservation. Extract structured product attributes from the following multimodal inputs:

Transcription (Hindi): "यह एक हाथ से बुनी हुई रेशमी साड़ी है..."
Vision Analysis: Category: Handloom Saree, Colors: red, gold, maroon, Materials: silk, zari

Tasks:
1. Extract product attributes (category, subcategory, material, colors, dimensions, weight, price)
2. Identify Cultural Specific Items (CSI) - preserve vernacular terms with context
3. Generate SEO-friendly English descriptions while preserving cultural significance
4. If voice and vision conflict, prioritize voice description

Output JSON format:
{
  "category": "...",
  "subcategory": "...",
  "material": [...],
  "colors": [...],
  "price": {"value": ..., "currency": "INR"},
  "short_description": "...",
  "long_description": "...",
  "csis": [
    {
      "vernacular_term": "...",
      "transliteration": "...",
      "english_context": "...",
      "cultural_significance": "..."
    }
  ],
  "craft_technique": "...",
  "region_of_origin": "...",
  "confidence_scores": {...}
}
```

**Output Format**:
```json
{
  "category": "Handloom Saree",
  "subcategory": "Banarasi Silk",
  "material": ["silk", "zari"],
  "colors": ["red", "gold", "maroon"],
  "dimensions": {
    "length": 550,
    "width": 110,
    "unit": "cm"
  },
  "price": {
    "value": 8500,
    "currency": "INR"
  },
  "short_description": "Traditional handwoven Banarasi silk saree with intricate zari work",
  "long_description": "This exquisite Banarasi silk saree is handwoven on traditional pit looms by skilled artisans in Varanasi. The rich red silk is adorned with intricate gold and maroon zari work, featuring traditional motifs that have been passed down through generations. Each saree takes approximately 15-30 days to complete, representing the pinnacle of Indian textile craftsmanship.",
  "csis": [
    {
      "vernacular_term": "बनारसी",
      "transliteration": "Banarasi",
      "english_context": "Traditional weaving technique from Varanasi, characterized by intricate brocade work with gold and silver threads",
      "cultural_significance": "Banarasi sarees are considered auspicious for weddings and special occasions in Indian culture"
    },
    {
      "vernacular_term": "ज़री",
      "transliteration": "Zari",
      "english_context": "Fine gold or silver thread used in traditional Indian textile embroidery",
      "cultural_significance": "Zari work represents luxury and is traditionally used in bridal and ceremonial attire"
    }
  ],
  "craft_technique": "Handwoven on pit loom with traditional brocade technique",
  "region_of_origin": "Varanasi, Uttar Pradesh",
  "confidence_scores": {
    "category": 0.95,
    "material": 0.92,
    "colors": 0.88,
    "price": 0.85,
    "csi_identification": 0.90
  }
}
```

**Voice Priority Resolution**:
- If voice mentions "silk" but vision detects "cotton", use "silk" (voice is authoritative)
- If voice mentions price "8500 rupees", extract as `{"value": 8500, "currency": "INR"}`
- If voice provides dimensions, use those over vision estimates

**CSI Identification**:
- Query cultural knowledge base (RAG system) for vernacular terms
- Preserve original vernacular term in output
- Provide transliteration (Roman script)
- Add English contextual explanation
- Include cultural significance

**Example Invocation** (Python):
```python
import boto3
import json

client = boto3.client('bedrock-runtime', region_name='us-east-1')

response = client.invoke_model(
    modelId='anthropic.claude-3-sonnet-20240229-v1:0',
    contentType='application/json',
    accept='application/json',
    body=json.dumps({
        'anthropic_version': 'bedrock-2023-05-31',
        'max_tokens': 4096,
        'messages': [
            {
                'role': 'user',
                'content': prompt_template
            }
        ]
    })
)

result = json.loads(response['body'].read())
extracted_attributes = json.loads(result['content'][0]['text'])
```

---

## Data Models

### CatalogProcessingRecord

**Description**: Complete catalog processing record stored in DynamoDB.

**DynamoDB Table**: `vernacular-catalog-processing`

**Partition Key**: `tracking_id` (string)

**GSI**: `tenant_id-created_at-index` (for tenant queries)

**Schema**:
```json
{
  "tracking_id": "trk_abc123xyz",
  "tenant_id": "tenant_12345",
  "artisan_id": "artisan_67890",
  "photo_key": "tenant_12345/artisan_67890/trk_abc123xyz.jpg",
  "audio_key": "tenant_12345/artisan_67890/trk_abc123xyz.opus",
  "language": "hi",
  
  "asr_status": "completed",
  "asr_result": {
    "transcription": "यह एक हाथ से बुनी हुई रेशमी साड़ी है",
    "confidence": 0.92
  },
  
  "vision_status": "completed",
  "vision_result": {
    "category": "Handloom Saree",
    "colors": ["red", "gold", "maroon"],
    "materials": ["silk", "zari"],
    "confidence": 0.87
  },
  
  "extraction_status": "completed",
  "extraction_result": {
    "category": "Handloom Saree",
    "subcategory": "Banarasi Silk",
    "material": ["silk", "zari"],
    "colors": ["red", "gold", "maroon"],
    "price": {"value": 8500, "currency": "INR"},
    "short_description": "Traditional handwoven Banarasi silk saree...",
    "long_description": "This exquisite Banarasi silk saree...",
    "csis": [...]
  },
  
  "mapping_status": "completed",
  "ondc_payload": {
    "id": "item_a1b2c3d4e5f6g7h8",
    "descriptor": {...},
    "price": {...},
    "category_id": "Fashion:Ethnic Wear:Sarees",
    "tags": {...}
  },
  
  "submission_status": "completed",
  "ondc_catalog_id": "ondc_cat_789",
  
  "created_at": "2024-02-26T10:00:00Z",
  "updated_at": "2024-02-26T10:05:00Z",
  "completed_at": "2024-02-26T10:05:00Z",
  "error_details": null
}
```

**Processing Status Values**:
- `pending`: Not yet started
- `in_progress`: Currently processing
- `completed`: Successfully completed
- `failed`: Processing failed
- `skipped`: Skipped due to graceful degradation

---

### ExtractedAttributes

**Description**: Intermediate format for extracted product attributes.

**Schema**:
```json
{
  "category": "Handloom Saree",
  "subcategory": "Banarasi Silk",
  "material": ["silk", "zari"],
  "colors": ["red", "gold", "maroon"],
  "dimensions": {
    "length": 550,
    "width": 110,
    "unit": "cm"
  },
  "weight": {
    "value": 450,
    "unit": "g"
  },
  "price": {
    "value": 8500,
    "currency": "INR"
  },
  "short_description": "Traditional handwoven Banarasi silk saree with intricate zari work",
  "long_description": "This exquisite Banarasi silk saree is handwoven...",
  "csis": [
    {
      "vernacular_term": "बनारसी",
      "transliteration": "Banarasi",
      "english_context": "Traditional weaving technique from Varanasi...",
      "cultural_significance": "Banarasi sarees are considered auspicious..."
    }
  ],
  "craft_technique": "Handwoven on pit loom with traditional brocade technique",
  "region_of_origin": "Varanasi, Uttar Pradesh",
  "confidence_scores": {
    "category": 0.95,
    "material": 0.92,
    "colors": 0.88,
    "price": 0.85
  }
}
```

---

### ONDCCatalogItem (Beckn Protocol)

**Description**: ONDC-compliant catalog item following Beckn protocol.

**Schema**:
```json
{
  "id": "item_a1b2c3d4e5f6g7h8",
  "descriptor": {
    "name": "Handwoven Banarasi Silk Saree",
    "short_desc": "Traditional handwoven silk saree with intricate zari work",
    "long_desc": "This exquisite Banarasi silk saree is handwoven...\n\nCultural Significance:\n• बनारसी (Banarasi): Traditional weaving technique...",
    "images": [
      "https://s3.amazonaws.com/enhanced-bucket/tenant_12345/artisan_67890/trk_abc123xyz_full.jpg",
      "https://s3.amazonaws.com/enhanced-bucket/tenant_12345/artisan_67890/trk_abc123xyz_medium.jpg",
      "https://s3.amazonaws.com/enhanced-bucket/tenant_12345/artisan_67890/trk_abc123xyz_thumb.jpg"
    ]
  },
  "price": {
    "currency": "INR",
    "value": "8500"
  },
  "category_id": "Fashion:Ethnic Wear:Sarees",
  "tags": {
    "material": "silk,zari",
    "color": "red,gold,maroon",
    "craft_technique": "Handwoven on pit loom with traditional brocade technique",
    "region": "Varanasi, Uttar Pradesh",
    "length": "550 cm",
    "width": "110 cm",
    "weight": "450 g",
    "csi_1_term": "बनारसी",
    "csi_1_transliteration": "Banarasi",
    "csi_1_context": "Traditional weaving technique from Varanasi...",
    "csi_2_term": "ज़री",
    "csi_2_transliteration": "Zari",
    "csi_2_context": "Fine gold or silver thread used in traditional Indian textile embroidery"
  }
}
```

---

### LocalQueueEntry (Edge Client)

**Description**: Local queue entry for offline-first operation on mobile devices.

**Storage**: SQLite database on mobile device

**Schema**:
```json
{
  "local_id": "uuid-generated-on-device",
  "photo_path": "/storage/emulated/0/VernacularCatalog/photo_123.jpg",
  "audio_path": "/storage/emulated/0/VernacularCatalog/audio_123.opus",
  "photo_size": 2048576,
  "audio_size": 524288,
  "captured_at": "2024-02-26T09:55:00Z",
  "sync_status": "queued",
  "retry_count": 0,
  "last_retry_at": null,
  "tracking_id": null,
  "error_message": null
}
```

**Sync Status Values**:
- `queued`: Waiting for network connectivity
- `syncing`: Upload in progress
- `synced`: Successfully uploaded and removed from queue
- `failed`: Upload failed after retries

---

## Error Handling

### Error Response Format

**Standard Error Response**:
```json
{
  "error": "ValidationError",
  "message": "Invalid request data",
  "details": [
    {
      "field": "language",
      "issue": "Unsupported language code",
      "code": "INVALID_LANGUAGE"
    }
  ],
  "tracking_id": "trk_abc123xyz",
  "timestamp": "2024-02-26T10:00:00Z"
}
```

---

### HTTP Status Codes

| Status Code | Description | Retry? |
|-------------|-------------|--------|
| 200 OK | Request successful | N/A |
| 400 Bad Request | Invalid request data | No |
| 401 Unauthorized | Invalid or missing API key | No |
| 403 Forbidden | Insufficient permissions | No |
| 404 Not Found | Resource not found | No |
| 429 Too Many Requests | Rate limit exceeded | Yes (after delay) |
| 500 Internal Server Error | Server error | Yes |
| 502 Bad Gateway | Gateway error | Yes |
| 503 Service Unavailable | Service temporarily unavailable | Yes |
| 504 Gateway Timeout | Request timeout | Yes |

---

### Error Categories

**Transient Errors** (Retryable):
- Network connectivity failures
- Service timeouts (504)
- Rate limiting (429)
- Server errors (5xx)
- Queue full conditions

**Permanent Errors** (Not Retryable):
- Invalid media format (400)
- Schema validation failures (400)
- Authentication failures (401)
- Authorization failures (403)
- Resource not found (404)
- Malformed requests (400)

---

### Retry Logic

**Exponential Backoff**:
```
Attempt 1: Immediate
Attempt 2: Wait 1 second
Attempt 3: Wait 2 seconds
Attempt 4: Wait 4 seconds
Attempt 5: Wait 8 seconds
Max delay: 10 seconds
Max attempts: 5
```

**Example** (Python):
```python
import time

def retry_with_backoff(func, max_retries=5):
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            if is_transient_error(e):
                delay = min(2 ** attempt, 10)
                time.sleep(delay)
            else:
                raise
```

---

### Common Error Codes

| Error Code | Description | Resolution |
|------------|-------------|------------|
| `INVALID_LANGUAGE` | Unsupported language code | Use supported language codes (hi, ta, te, etc.) |
| `MISSING_MEDIA` | No photo or audio provided | Provide at least one media file |
| `INVALID_CONTENT_TYPE` | Unsupported media format | Use JPEG/PNG for images, Opus/MP3/WAV for audio |
| `TRACKING_ID_NOT_FOUND` | Tracking ID does not exist | Verify tracking ID from upload initiation |
| `UPLOAD_EXPIRED` | Upload URL has expired | Initiate new upload |
| `VALIDATION_ERROR` | ONDC schema validation failed | Check catalog payload against Beckn schema |
| `RATE_LIMIT_EXCEEDED` | Too many requests | Wait and retry with exponential backoff |
| `TENANT_NOT_FOUND` | Tenant ID does not exist | Verify tenant configuration |
| `QUOTA_EXCEEDED` | Tenant quota exceeded | Contact support to increase quota |

---

## OpenAPI Specification

### OpenAPI 3.0 Schema

```yaml
openapi: 3.0.3
info:
  title: Vernacular Artisan Catalog API
  description: |
    API for enabling rural artisans to catalog products on ONDC through photo and voice capture.
    
    Features:
    - Resumable multipart uploads
    - Asynchronous AI processing (Sagemaker Vision+ASR, Bedrock LLM)
    - ONDC integration via Beckn protocol
    - Offline-first mobile support
    - Multi-tenancy with tenant isolation
  version: 1.0.0
  contact:
    name: API Support
    email: api-support@vernacular-catalog.example.com

servers:
  - url: https://api.vernacular-catalog.example.com
    description: Production server
  - url: https://api-staging.vernacular-catalog.example.com
    description: Staging server

security:
  - BearerAuth: []

paths:
  /v1/catalog/upload/initiate:
    post:
      summary: Initiate resumable upload
      description: Generates presigned S3 URLs for direct media upload
      operationId: initiateUpload
      tags:
        - Upload
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - tenant_id
                - artisan_id
                - content_type
              properties:
                tenant_id:
                  type: string
                  description: Tenant organization identifier
                  example: tenant_12345
                artisan_id:
                  type: string
                  description: Artisan identifier
                  example: artisan_67890
                content_type:
                  type: string
                  description: MIME type of the content
                  enum:
                    - image/jpeg
                    - image/png
                    - audio/opus
                    - audio/mpeg
                    - audio/wav
                  example: image/jpeg
      responses:
        '200':
          description: Upload initiated successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/UploadResponse'
        '400':
          description: Bad request
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '401':
          description: Unauthorized
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '429':
          description: Rate limit exceeded
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '500':
          description: Internal server error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /v1/catalog/upload/complete:
    post:
      summary: Complete upload
      description: Completes upload and enqueues media for AI processing
      operationId: completeUpload
      tags:
        - Upload
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - tracking_id
                - language
              properties:
                tracking_id:
                  type: string
                  description: Tracking ID from initiate upload
                  example: trk_abc123xyz
                photo_key:
                  type: string
                  description: S3 key for uploaded photo
                  example: tenant_12345/artisan_67890/trk_abc123xyz.jpg
                audio_key:
                  type: string
                  description: S3 key for uploaded audio
                  example: tenant_12345/artisan_67890/trk_abc123xyz.opus
                language:
                  type: string
                  description: Language code
                  enum: [hi, ta, te, bn, mr, gu, kn, ml, pa, or]
                  example: hi
      responses:
        '200':
          description: Upload completed successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/UploadCompleteResponse'
        '400':
          description: Bad request
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '404':
          description: Tracking ID not found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '500':
          description: Internal server error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /v1/catalog/status/{trackingId}:
    get:
      summary: Get processing status
      description: Retrieves current processing status for a catalog entry
      operationId: getStatus
      tags:
        - Status
      parameters:
        - name: trackingId
          in: path
          required: true
          description: Tracking identifier
          schema:
            type: string
            example: trk_abc123xyz
      responses:
        '200':
          description: Status retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/StatusUpdate'
        '404':
          description: Tracking ID not found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '500':
          description: Internal server error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

components:
  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
      description: Tenant-specific API key

  schemas:
    UploadResponse:
      type: object
      required:
        - tracking_id
        - upload_url
        - expires_at
      properties:
        tracking_id:
          type: string
          description: Unique tracking identifier
          example: trk_abc123xyz
        upload_url:
          type: string
          format: uri
          description: Presigned S3 URL for upload (valid for 1 hour)
          example: https://s3.amazonaws.com/bucket/path?signature=...
        expires_at:
          type: string
          format: date-time
          description: Upload URL expiration timestamp
          example: '2024-02-26T11:00:00Z'

    UploadCompleteResponse:
      type: object
      required:
        - status
        - tracking_id
        - message
      properties:
        status:
          type: string
          enum: [accepted]
          example: accepted
        tracking_id:
          type: string
          example: trk_abc123xyz
        message:
          type: string
          example: Upload accepted and queued for processing

    StatusUpdate:
      type: object
      required:
        - tracking_id
        - stage
        - message
        - timestamp
      properties:
        tracking_id:
          type: string
          example: trk_abc123xyz
        stage:
          type: string
          enum: [uploaded, processing, extraction, mapping, completed, failed]
          example: completed
        message:
          type: string
          example: Catalog entry successfully published to ONDC
        catalog_id:
          type: string
          description: ONDC catalog ID (only present when completed)
          example: ondc_cat_789
        error_details:
          type: object
          description: Error information (only present when failed)
          properties:
            message:
              type: string
            code:
              type: string
            stage:
              type: string
        timestamp:
          type: string
          format: date-time
          example: '2024-02-26T10:05:00Z'

    ErrorResponse:
      type: object
      required:
        - error
        - message
      properties:
        error:
          type: string
          description: Error type
          example: ValidationError
        message:
          type: string
          description: Error message
          example: Invalid request data
        details:
          type: array
          description: Detailed error information
          items:
            type: object
            properties:
              field:
                type: string
                example: language
              issue:
                type: string
                example: Unsupported language code
              code:
                type: string
                example: INVALID_LANGUAGE
        tracking_id:
          type: string
          description: Tracking ID if available
          example: trk_abc123xyz
        timestamp:
          type: string
          format: date-time
          example: '2024-02-26T10:00:00Z'

tags:
  - name: Upload
    description: Resumable upload operations
  - name: Status
    description: Processing status queries
```

---

## Rate Limits

### API Gateway Rate Limits

**Per Tenant**:
- **Steady State**: 100 requests per second
- **Burst**: 500 requests
- **Daily Quota**: 100,000 requests per day

**Per Endpoint**:
- `POST /v1/catalog/upload/initiate`: 50 req/s per tenant
- `POST /v1/catalog/upload/complete`: 50 req/s per tenant
- `GET /v1/catalog/status/{trackingId}`: 100 req/s per tenant

**Rate Limit Headers**:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1708945200
```

**Rate Limit Exceeded Response** (429):
```json
{
  "error": "RateLimitExceeded",
  "message": "Rate limit exceeded. Please retry after 60 seconds.",
  "retry_after": 60,
  "timestamp": "2024-02-26T10:00:00Z"
}
```

---

## Authentication

### API Key Authentication

**Header Format**:
```
Authorization: Bearer <tenant_api_key>
```

**Example**:
```bash
curl -X POST https://api.vernacular-catalog.example.com/v1/catalog/upload/initiate \
  -H "Authorization: Bearer sk_live_abc123xyz..." \
  -H "Content-Type: application/json" \
  -d '{"tenant_id": "tenant_12345", "artisan_id": "artisan_67890", "content_type": "image/jpeg"}'
```

**API Key Format**:
- Production: `sk_live_<32_char_random>`
- Staging: `sk_test_<32_char_random>`

**Key Management**:
- Keys are tenant-specific
- Keys can be rotated without downtime
- Keys are stored encrypted in AWS Secrets Manager
- Keys have configurable expiration (default: 1 year)

---

## Monitoring and Observability

### CloudWatch Metrics

**API Gateway Metrics**:
- `ApiRequestCount`: Total API requests
- `ApiLatency`: Request latency (p50, p95, p99)
- `ApiErrorRate`: Error rate percentage
- `Api4xxErrors`: Client errors
- `Api5xxErrors`: Server errors

**Processing Metrics**:
- `QueueDepth`: Number of messages in SQS queue
- `ProcessingLatency`: End-to-end processing time
- `SagemakerInvocations`: Sagemaker endpoint invocations
- `BedrockInvocations`: Bedrock model invocations
- `ONDCSubmissions`: ONDC submission attempts
- `ONDCSuccessRate`: ONDC submission success rate

**Custom Metrics**:
- `LowConfidenceResults`: Results flagged for manual review
- `CostPerEntry`: Processing cost per catalog entry
- `TenantQuotaUsage`: Quota usage per tenant

### X-Ray Distributed Tracing

**Trace Context Propagation**:
```
X-Amzn-Trace-Id: Root=1-67891234-abcdef012345678901234567;Parent=463ac35c9f6413ad;Sampled=1
```

**Trace Segments**:
1. API Gateway → Lambda (upload handler)
2. Lambda → S3 (presigned URL generation)
3. Lambda → DynamoDB (record creation)
4. Lambda → SQS (message publishing)
5. SQS → Lambda (orchestrator)
6. Lambda → Sagemaker (Vision+ASR)
7. Lambda → Bedrock (attribute extraction)
8. Lambda → ONDC Gateway (submission)
9. Lambda → SNS (notification)

### CloudWatch Logs

**Log Groups**:
- `/aws/lambda/upload-handler`
- `/aws/lambda/orchestrator`
- `/aws/apigateway/vernacular-catalog-api`
- `/aws/sagemaker/vernacular-vision-asr-endpoint`

**Log Format** (JSON):
```json
{
  "timestamp": "2024-02-26T10:00:00.123Z",
  "level": "INFO",
  "message": "Upload initiated",
  "tracking_id": "trk_abc123xyz",
  "tenant_id": "tenant_12345",
  "artisan_id": "artisan_67890",
  "request_id": "req_xyz789",
  "trace_id": "1-67891234-abcdef012345678901234567"
}
```

---

## Appendix

### Supported MIME Types

**Images**:
- `image/jpeg` - JPEG images
- `image/png` - PNG images

**Audio**:
- `audio/opus` - Opus codec (recommended for mobile)
- `audio/mpeg` - MP3 audio
- `audio/wav` - WAV audio

### Language Codes (ISO 639-1)

| Code | Language | Native Name |
|------|----------|-------------|
| hi | Hindi | हिन्दी |
| ta | Tamil | தமிழ் |
| te | Telugu | తెలుగు |
| bn | Bengali | বাংলা |
| mr | Marathi | मराठी |
| gu | Gujarati | ગુજરાતી |
| kn | Kannada | ಕನ್ನಡ |
| ml | Malayalam | മലയാളം |
| pa | Punjabi | ਪੰਜਾਬੀ |
| or | Odia | ଓଡ଼ିଆ |

### ONDC Category Taxonomy (Sample)

```
Fashion
├── Ethnic Wear
│   ├── Sarees
│   ├── Kurtas
│   ├── Dupattas
│   └── Dhotis
├── Jewelry
│   ├── Necklaces
│   ├── Earrings
│   ├── Bracelets
│   └── Bangles
└── Accessories
    ├── Shawls
    └── Stoles

Home & Decor
├── Handicrafts
│   ├── Pottery
│   ├── Wood Carvings
│   ├── Brass
│   ├── Copper
│   └── Bronze
├── Wall Art
│   ├── Paintings
│   └── Hangings
├── Lighting
│   ├── Lamps
│   └── Candle Holders
└── Storage
    ├── Baskets
    └── Wooden Boxes

Toys & Games
└── Traditional Toys
    └── Wooden

General
└── Handicrafts
```

### References

- **ONDC Documentation**: https://ondc.org/
- **Beckn Protocol**: https://developers.becknprotocol.io/
- **AWS Sagemaker**: https://docs.aws.amazon.com/sagemaker/
- **AWS Bedrock**: https://docs.aws.amazon.com/bedrock/
- **OpenAPI Specification**: https://swagger.io/specification/

---

## Changelog

### Version 1.0.0 (2024-02-26)
- Initial API release
- Resumable upload endpoints
- Asynchronous processing with Sagemaker and Bedrock
- ONDC integration via Beckn protocol
- Multi-tenancy support
- Offline-first mobile support

---

**Document Version**: 1.0.0  
**Last Updated**: 2024-02-26  
**Maintained By**: Vernacular Artisan Catalog Team
