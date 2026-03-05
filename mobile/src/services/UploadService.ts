import axios from 'axios';
import * as tus from 'tus-js-client';
import RNFS from 'react-native-fs';
import { LocalQueueEntry, UploadResponse, UploadProgress } from '../types';
import { API_CONFIG, SYNC_CONFIG } from '../config';

/**
 * Upload Service with resumable multipart upload
 * Requirement 3.1: Call API Gateway to get presigned URLs
 * Requirement 3.2: Implement chunked upload with S3 multipart
 * Requirement 3.3: Resume upload on connection drop
 */
export class UploadService {
  private uploadProgressCallbacks: Map<string, (progress: UploadProgress) => void> = new Map();

  /**
   * Upload entry to backend
   * Requirement 3.1: Initiate upload and get presigned URLs
   */
  async uploadEntry(entry: LocalQueueEntry): Promise<string> {
    try {
      // Step 1: Initiate upload
      const uploadResponse = await this.initiateUpload();
      const { trackingId, uploadUrl } = uploadResponse;

      // Step 2: Upload photo
      const photoKey = await this.uploadFile(
        entry.photoPath,
        uploadUrl + '/photo',
        entry.localId,
        'photo'
      );

      // Step 3: Upload audio
      const audioKey = await this.uploadFile(
        entry.audioPath,
        uploadUrl + '/audio',
        entry.localId,
        'audio'
      );

      // Step 4: Complete upload
      await this.completeUpload(trackingId, photoKey, audioKey);

      return trackingId;
    } catch (error) {
      console.error('Upload failed:', error);
      throw error;
    }
  }

  /**
   * Initiate upload and get presigned URLs
   * Requirement 3.1: POST /v1/catalog/upload/initiate
   */
  private async initiateUpload(): Promise<UploadResponse> {
    try {
      const response = await axios.post(
        `${API_CONFIG.BASE_URL}${API_CONFIG.UPLOAD_INITIATE_ENDPOINT}`,
        {
          tenantId: 'default', // TODO: Get from user context
          artisanId: 'artisan-001', // TODO: Get from user context
          contentType: 'multipart/form-data',
        },
        {
          timeout: API_CONFIG.TIMEOUT,
        }
      );

      return response.data;
    } catch (error) {
      console.error('Failed to initiate upload:', error);
      throw new Error('Failed to initiate upload');
    }
  }

  /**
   * Upload file using tus protocol for resumable uploads
   * Requirement 3.2: Chunked upload directly to S3
   * Requirement 3.3: Resume on connection drop
   */
  private async uploadFile(
    filePath: string,
    uploadUrl: string,
    localId: string,
    fileType: 'photo' | 'audio'
  ): Promise<string> {
    return new Promise(async (resolve, reject) => {
      try {
        // Read file as blob
        const fileData = await RNFS.readFile(filePath, 'base64');
        const blob = this.base64ToBlob(fileData);

        // Create tus upload
        const upload = new tus.Upload(blob, {
          endpoint: uploadUrl,
          retryDelays: [0, 1000, 3000, 5000],
          chunkSize: SYNC_CONFIG.CHUNK_SIZE,
          metadata: {
            filename: filePath.split('/').pop() || 'file',
            filetype: fileType === 'photo' ? 'image/jpeg' : 'audio/m4a',
          },
          onError: (error) => {
            console.error(`Upload failed for ${fileType}:`, error);
            reject(error);
          },
          onProgress: (bytesUploaded, bytesTotal) => {
            const progress: UploadProgress = {
              localId,
              bytesUploaded,
              totalBytes: bytesTotal,
              percentage: (bytesUploaded / bytesTotal) * 100,
            };

            // Notify progress callback
            const callback = this.uploadProgressCallbacks.get(localId);
            if (callback) {
              callback(progress);
            }
          },
          onSuccess: () => {
            // Extract S3 key from upload URL
            const s3Key = upload.url?.split('/').pop() || '';
            resolve(s3Key);
          },
        });

        // Start upload
        upload.start();
      } catch (error) {
        reject(error);
      }
    });
  }

  /**
   * Complete upload
   * Requirement 3.1: POST /v1/catalog/upload/complete
   */
  private async completeUpload(
    trackingId: string,
    photoKey: string,
    audioKey: string
  ): Promise<void> {
    try {
      await axios.post(
        `${API_CONFIG.BASE_URL}${API_CONFIG.UPLOAD_COMPLETE_ENDPOINT}`,
        {
          trackingId,
          photoKey,
          audioKey,
        },
        {
          timeout: API_CONFIG.TIMEOUT,
        }
      );
    } catch (error) {
      console.error('Failed to complete upload:', error);
      throw new Error('Failed to complete upload');
    }
  }

  /**
   * Get upload status
   * GET /v1/catalog/status/{trackingId}
   */
  async getUploadStatus(trackingId: string): Promise<any> {
    try {
      const response = await axios.get(
        `${API_CONFIG.BASE_URL}${API_CONFIG.STATUS_ENDPOINT}/${trackingId}`,
        {
          timeout: API_CONFIG.TIMEOUT,
        }
      );

      return response.data;
    } catch (error) {
      console.error('Failed to get upload status:', error);
      throw new Error('Failed to get upload status');
    }
  }

  /**
   * Register progress callback
   */
  onUploadProgress(localId: string, callback: (progress: UploadProgress) => void): void {
    this.uploadProgressCallbacks.set(localId, callback);
  }

  /**
   * Unregister progress callback
   */
  offUploadProgress(localId: string): void {
    this.uploadProgressCallbacks.delete(localId);
  }

  /**
   * Convert base64 to blob
   */
  private base64ToBlob(base64: string): Blob {
    const byteCharacters = atob(base64);
    const byteNumbers = new Array(byteCharacters.length);
    
    for (let i = 0; i < byteCharacters.length; i++) {
      byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    
    const byteArray = new Uint8Array(byteNumbers);
    return new Blob([byteArray]);
  }
}

export const uploadService = new UploadService();
