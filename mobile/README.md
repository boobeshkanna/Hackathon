# Vernacular Artisan Catalog - Mobile Edge Client

Zero-UI mobile application for Android that enables vernacular artisans to catalog products through photo and voice capture with offline-first operation.

## Features

- **Zero-UI Design**: Single-button camera interface with no forms or dropdowns
- **Offline-First**: Persistent local queue with background sync
- **Low-RAM Optimized**: Operates within 512MB RAM budget on Android 8.0+
- **Resumable Uploads**: S3 multipart upload with automatic resume on connection drop
- **Vernacular Language Support**: UI in artisan's native language (Hindi, Tamil, Telugu, etc.)
- **Background Sync**: Automatic sync with exponential backoff retry (1min, 2min, 4min, 8min, 16min)
- **Push Notifications**: Firebase Cloud Messaging for status updates
- **Bulk Capture**: Sequential capture of multiple products

## Architecture

### Core Services

1. **MediaCaptureService**: Handles photo capture and voice recording with on-device compression
2. **QueueService**: Manages persistent local queue using SQLite
3. **BackgroundSyncService**: Automatic sync with network detection and retry logic
4. **UploadService**: Resumable multipart upload using tus protocol
5. **NotificationService**: Firebase Cloud Messaging integration

### Data Flow

```
Capture → Compress → Queue → Background Sync → Upload → Process → Notify
```

### Local Storage

- **SQLite Database**: Queue entries with sync status
- **File System**: Compressed media files (photos and audio)
- **AsyncStorage**: User preferences and language settings

## Requirements

- Android 8.0+ (API level 26+)
- Node.js 16+
- React Native 0.72+
- Android Studio (for development)

## Installation

### 1. Install Dependencies

```bash
cd mobile
npm install
```

### 2. Configure Firebase

1. Create a Firebase project at https://console.firebase.google.com
2. Add an Android app to your Firebase project
3. Download `google-services.json`
4. Place it in `mobile/android/app/`

### 3. Configure API Endpoint

Edit `mobile/src/config/index.ts`:

```typescript
export const API_CONFIG = {
  BASE_URL: 'https://your-api-gateway-url.com',
  // ...
};
```

### 4. Build and Run

```bash
# Start Metro bundler
npm start

# Run on Android device/emulator
npm run android
```

## Configuration

### Compression Settings

Edit `mobile/src/config/index.ts`:

```typescript
export const COMPRESSION_CONFIG = {
  IMAGE: {
    QUALITY: 0.8,        // JPEG quality (0-1)
    MAX_WIDTH: 1920,     // Max width in pixels
    MAX_HEIGHT: 1920,    // Max height in pixels
  },
  AUDIO: {
    SAMPLE_RATE: 16000,  // Hz
    BIT_RATE: 32000,     // bps
    CHANNELS: 1,         // Mono
  },
};
```

### Sync Settings

```typescript
export const SYNC_CONFIG = {
  MAX_RETRIES: 5,                    // Maximum retry attempts
  INITIAL_BACKOFF_MS: 60000,         // 1 minute
  MAX_BACKOFF_MS: 960000,            // 16 minutes
  CHUNK_SIZE: 1024 * 1024,           // 1MB upload chunks
};
```

### Language Settings

```typescript
export const LANGUAGE_CONFIG = {
  DEFAULT_LANGUAGE: 'hi',            // Hindi
  SUPPORTED_LANGUAGES: [
    'hi', 'ta', 'te', 'bn', 'mr',   // Hindi, Tamil, Telugu, Bengali, Marathi
    'gu', 'kn', 'ml', 'pa', 'or',   // Gujarati, Kannada, Malayalam, Punjabi, Odia
  ],
};
```

## Usage

### Single Product Capture

1. Open the app
2. Tap the camera button to take a photo
3. Tap the microphone button to record voice description
4. Entry is automatically queued and synced when online

### Bulk Product Capture

1. Navigate to "Bulk" tab
2. Capture multiple products sequentially
3. Review captured items
4. Delete any unwanted items
5. Finish batch to queue all items

### Queue Management

1. Navigate to "Queue" tab
2. View all queued entries with sync status
3. Pull to refresh to force sync
4. Tap entry to view preview
5. Delete entries if needed

## API Integration

### Upload Initiate

```
POST /v1/catalog/upload/initiate
Request: { tenantId, artisanId, contentType }
Response: { trackingId, uploadUrl, expiresAt }
```

### Upload Complete

```
POST /v1/catalog/upload/complete
Request: { trackingId, photoKey, audioKey }
Response: { status: 'accepted', trackingId }
```

### Status Check

```
GET /v1/catalog/status/{trackingId}
Response: { stage, message, catalogId?, errorDetails? }
```

## Low-RAM Optimization

The app is optimized for devices with limited RAM:

- **Streaming Compression**: Media is compressed in chunks, not loaded fully in memory
- **Immediate Memory Release**: Memory is released after each operation
- **Minimal Dependencies**: APK size kept under 15MB
- **Background Process Limits**: Only essential sync operations run in background
- **No Large Heap**: `largeHeap=false` in AndroidManifest.xml

## Offline-First Design

The app works seamlessly offline:

- **Local Queue**: All captures stored in SQLite
- **Automatic Sync**: Syncs when network becomes available
- **Retry Logic**: Exponential backoff for failed uploads
- **Resume Support**: Uploads resume from last successful chunk
- **Status Tracking**: Real-time sync status for each entry

## Security

- **TLS 1.3**: All network communication encrypted
- **No PII Collection**: Only catalog-related data transmitted
- **Local Encryption**: Media files encrypted at rest (TODO)
- **Secure Storage**: Sensitive data in Android Keystore (TODO)

## Testing

```bash
# Run unit tests
npm test

# Run on device
npm run android
```

## Troubleshooting

### Camera Permission Denied

Ensure camera permission is granted in Android settings.

### Upload Fails

1. Check network connectivity
2. Verify API endpoint configuration
3. Check Firebase configuration
4. Review logs: `adb logcat`

### High Memory Usage

1. Clear old media files: Settings → Storage
2. Reduce queue size in configuration
3. Restart app

## Performance Benchmarks

- **Photo Capture**: < 2 seconds (including compression)
- **Audio Recording**: Real-time with < 100ms latency
- **Queue Operation**: < 50ms per entry
- **Upload Speed**: Depends on network (typically 30s for 5MB)
- **Memory Usage**: < 512MB peak

## License

Copyright © 2024 Vernacular Artisan Catalog Project
