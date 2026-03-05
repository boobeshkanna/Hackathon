export const API_CONFIG = {
  BASE_URL: process.env.API_BASE_URL || 'https://api.example.com',
  UPLOAD_INITIATE_ENDPOINT: '/v1/catalog/upload/initiate',
  UPLOAD_COMPLETE_ENDPOINT: '/v1/catalog/upload/complete',
  STATUS_ENDPOINT: '/v1/catalog/status',
  TIMEOUT: 30000, // 30 seconds
};

export const COMPRESSION_CONFIG = {
  IMAGE: {
    QUALITY: 0.8,
    MAX_WIDTH: 1920,
    MAX_HEIGHT: 1920,
    FORMAT: 'JPEG',
  },
  AUDIO: {
    SAMPLE_RATE: 16000,
    BIT_RATE: 32000,
    CHANNELS: 1,
    FORMAT: 'opus',
  },
};

export const SYNC_CONFIG = {
  MAX_RETRIES: 5,
  INITIAL_BACKOFF_MS: 60000, // 1 minute
  MAX_BACKOFF_MS: 960000, // 16 minutes
  CHUNK_SIZE: 1024 * 1024, // 1MB chunks for upload
};

export const STORAGE_CONFIG = {
  MEDIA_DIR: 'artisan_media',
  MAX_QUEUE_SIZE: 100,
  RETENTION_DAYS: 30,
};

export const LANGUAGE_CONFIG = {
  DEFAULT_LANGUAGE: 'hi', // Hindi
  SUPPORTED_LANGUAGES: [
    'hi', // Hindi
    'ta', // Tamil
    'te', // Telugu
    'bn', // Bengali
    'mr', // Marathi
    'gu', // Gujarati
    'kn', // Kannada
    'ml', // Malayalam
    'pa', // Punjabi
    'or', // Odia
  ],
};
