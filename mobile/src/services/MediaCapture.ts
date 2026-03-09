import { launchCamera, ImagePickerResponse } from 'react-native-image-picker';
import AudioRecorderPlayer from 'react-native-audio-recorder-player';
import { Image } from 'react-native-compressor';
import RNFS from 'react-native-fs';
import { COMPRESSION_CONFIG, STORAGE_CONFIG } from '../config';
import { CaptureResult } from '../types';

export class MediaCaptureService {
  private audioRecorder: AudioRecorderPlayer;
  private isRecording: boolean = false;
  private currentRecordingPath: string | null = null;

  constructor() {
    this.audioRecorder = new AudioRecorderPlayer();
  }

  /**
   * Capture photo with on-device compression
   * Requirement 1.1, 1.2: Single-button camera interface with immediate compression
   */
  async capturePhoto(): Promise<string> {
    return new Promise((resolve, reject) => {
      launchCamera(
        {
          mediaType: 'photo',
          quality: 1, // Capture at highest quality, compress later
          saveToPhotos: false,
          includeBase64: false,
        },
        async (response: ImagePickerResponse) => {
          if (response.didCancel) {
            reject(new Error('User cancelled photo capture'));
            return;
          }

          if (response.errorCode) {
            reject(new Error(`Camera error: ${response.errorMessage}`));
            return;
          }

          if (!response.assets || response.assets.length === 0) {
            reject(new Error('No photo captured'));
            return;
          }

          const asset = response.assets[0];
          if (!asset.uri) {
            reject(new Error('Invalid photo URI'));
            return;
          }

          try {
            // Compress image to reduce file size while preserving details
            const compressedPath = await this.compressImage(asset.uri);
            resolve(compressedPath);
          } catch (error) {
            reject(error);
          }
        }
      );
    });
  }

  /**
   * Compress image according to configuration
   * Requirement 1.2: Compress image to reduce file size while preserving product details
   */
  private async compressImage(imagePath: string): Promise<string> {
    try {
      const timestamp = Date.now();
      const outputPath = `${RNFS.DocumentDirectoryPath}/${STORAGE_CONFIG.MEDIA_DIR}/photo_${timestamp}.jpg`;

      // Ensure directory exists
      await this.ensureDirectoryExists(`${RNFS.DocumentDirectoryPath}/${STORAGE_CONFIG.MEDIA_DIR}`);

      const compressedPath = await Image.compress(imagePath, {
        compressionMethod: 'auto',
        quality: COMPRESSION_CONFIG.IMAGE.QUALITY,
        maxWidth: COMPRESSION_CONFIG.IMAGE.MAX_WIDTH,
        maxHeight: COMPRESSION_CONFIG.IMAGE.MAX_HEIGHT,
        output: 'jpg',
      });

      // Move compressed file to our storage directory
      await RNFS.moveFile(compressedPath, outputPath);

      return outputPath;
    } catch (error) {
      console.error('Image compression failed:', error);
      throw new Error('Failed to compress image');
    }
  }

  /**
   * Start voice recording
   * Requirement 1.3: Record audio in artisan's vernacular language
   */
  async startRecording(): Promise<void> {
    if (this.isRecording) {
      throw new Error('Recording already in progress');
    }

    try {
      const timestamp = Date.now();
      const recordingPath = `${RNFS.DocumentDirectoryPath}/${STORAGE_CONFIG.MEDIA_DIR}/audio_${timestamp}.m4a`;

      // Ensure directory exists
      await this.ensureDirectoryExists(`${RNFS.DocumentDirectoryPath}/${STORAGE_CONFIG.MEDIA_DIR}`);

      await this.audioRecorder.startRecorder(recordingPath, {
        // @ts-ignore - SampleRate is valid but not in type definition
        SampleRate: COMPRESSION_CONFIG.AUDIO.SAMPLE_RATE,
        Channels: COMPRESSION_CONFIG.AUDIO.CHANNELS,
        AudioQuality: 'Low', // Low quality for smaller file size
        AudioEncoding: 'aac',
      });

      this.isRecording = true;
      this.currentRecordingPath = recordingPath;
    } catch (error) {
      console.error('Failed to start recording:', error);
      throw new Error('Failed to start audio recording');
    }
  }

  /**
   * Stop voice recording and compress
   * Requirement 1.4: Compress audio file for efficient transmission
   */
  async stopRecording(): Promise<string> {
    if (!this.isRecording || !this.currentRecordingPath) {
      throw new Error('No recording in progress');
    }

    try {
      await this.audioRecorder.stopRecorder();
      this.isRecording = false;

      const recordingPath = this.currentRecordingPath;
      this.currentRecordingPath = null;

      // Audio is already compressed during recording with low quality settings
      return recordingPath;
    } catch (error) {
      console.error('Failed to stop recording:', error);
      throw new Error('Failed to stop audio recording');
    }
  }

  /**
   * Get recording status
   */
  isCurrentlyRecording(): boolean {
    return this.isRecording;
  }

  /**
   * Get file size
   */
  async getFileSize(filePath: string): Promise<number> {
    try {
      const stat = await RNFS.stat(filePath);
      return stat.size;
    } catch (error) {
      console.error('Failed to get file size:', error);
      return 0;
    }
  }

  /**
   * Ensure directory exists
   */
  private async ensureDirectoryExists(dirPath: string): Promise<void> {
    const exists = await RNFS.exists(dirPath);
    if (!exists) {
      await RNFS.mkdir(dirPath);
    }
  }

  /**
   * Delete media file
   */
  async deleteFile(filePath: string): Promise<void> {
    try {
      const exists = await RNFS.exists(filePath);
      if (exists) {
        await RNFS.unlink(filePath);
      }
    } catch (error) {
      console.error('Failed to delete file:', error);
    }
  }

  /**
   * Cleanup old media files
   */
  async cleanupOldFiles(retentionDays: number = STORAGE_CONFIG.RETENTION_DAYS): Promise<void> {
    try {
      const mediaDir = `${RNFS.DocumentDirectoryPath}/${STORAGE_CONFIG.MEDIA_DIR}`;
      const exists = await RNFS.exists(mediaDir);
      
      if (!exists) return;

      const files = await RNFS.readDir(mediaDir);
      const cutoffTime = Date.now() - (retentionDays * 24 * 60 * 60 * 1000);

      for (const file of files) {
        const stat = await RNFS.stat(file.path);
        const fileTime = new Date(stat.mtime).getTime();

        if (fileTime < cutoffTime) {
          await RNFS.unlink(file.path);
        }
      }
    } catch (error) {
      console.error('Failed to cleanup old files:', error);
    }
  }
}

export const mediaCaptureService = new MediaCaptureService();
