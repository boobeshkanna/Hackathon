export type QueueStatus = 'queued' | 'syncing' | 'synced' | 'failed';

export interface LocalQueueEntry {
  localId: string;
  photoPath: string;
  audioPath: string;
  photoSize: number;
  audioSize: number;
  capturedAt: number;
  syncStatus: QueueStatus;
  retryCount: number;
  lastRetryAt?: number;
  trackingId?: string;
  errorMessage?: string;
}

export interface UploadResponse {
  trackingId: string;
  uploadUrl: string;
  expiresAt: number;
}

export interface StatusUpdate {
  trackingId: string;
  stage: 'uploaded' | 'processing' | 'completed' | 'failed';
  message: string;
  catalogId?: string;
  attributes?: ExtractedAttributes;
}

export interface ExtractedAttributes {
  category?: string;
  subcategory?: string;
  material?: string[];
  colors?: string[];
  price?: { value: number; currency: string };
  shortDescription?: string;
  longDescription?: string;
}

export interface CaptureResult {
  photoPath: string;
  audioPath: string;
  photoSize: number;
  audioSize: number;
}

export interface UploadProgress {
  localId: string;
  bytesUploaded: number;
  totalBytes: number;
  percentage: number;
}
