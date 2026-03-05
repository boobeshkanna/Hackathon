import NetInfo from '@react-native-community/netinfo';
import { queueService } from './QueueService';
import { uploadService } from './UploadService';
import { LocalQueueEntry } from '../types';
import { SYNC_CONFIG } from '../config';

/**
 * Background Sync Service with exponential backoff retry
 * Requirement 2.3: Automatically sync when network restored
 * Requirement 2.4: Retry with exponential backoff up to 5 attempts
 */
export class BackgroundSyncService {
  private isSyncing: boolean = false;
  private syncInterval: NodeJS.Timeout | null = null;

  /**
   * Start background sync monitoring
   * Requirement 2.3: Detect network connectivity and begin syncing
   */
  async startSync(): Promise<void> {
    // Listen for network state changes
    NetInfo.addEventListener(state => {
      if (state.isConnected && !this.isSyncing) {
        this.syncQueue();
      }
    });

    // Check initial network state
    const netInfo = await NetInfo.fetch();
    if (netInfo.isConnected) {
      this.syncQueue();
    }

    // Set up periodic sync check (every 5 minutes)
    this.syncInterval = setInterval(() => {
      this.syncQueue();
    }, 5 * 60 * 1000);
  }

  /**
   * Stop background sync
   */
  stopSync(): void {
    if (this.syncInterval) {
      clearInterval(this.syncInterval);
      this.syncInterval = null;
    }
  }

  /**
   * Sync queued entries
   */
  async syncQueue(): Promise<void> {
    if (this.isSyncing) {
      return; // Already syncing
    }

    // Check network connectivity
    const netInfo = await NetInfo.fetch();
    if (!netInfo.isConnected) {
      return; // No network
    }

    this.isSyncing = true;

    try {
      const queuedEntries = await queueService.getQueuedEntries();

      for (const entry of queuedEntries) {
        await this.syncEntry(entry);
      }
    } catch (error) {
      console.error('Queue sync failed:', error);
    } finally {
      this.isSyncing = false;
    }
  }

  /**
   * Sync single entry with retry logic
   * Requirement 2.4: Exponential backoff retry (1min, 2min, 4min, 8min, 16min)
   */
  private async syncEntry(entry: LocalQueueEntry): Promise<void> {
    // Check if max retries exceeded
    if (entry.retryCount >= SYNC_CONFIG.MAX_RETRIES) {
      console.log(`Entry ${entry.localId} exceeded max retries`);
      return;
    }

    // Check if we should retry based on backoff
    if (entry.lastRetryAt) {
      const backoffDelay = this.calculateBackoff(entry.retryCount);
      const timeSinceLastRetry = Date.now() - entry.lastRetryAt;
      
      if (timeSinceLastRetry < backoffDelay) {
        // Not time to retry yet
        return;
      }
    }

    try {
      // Update status to syncing
      await queueService.updateStatus(entry.localId, 'syncing');

      // Attempt upload
      const trackingId = await uploadService.uploadEntry(entry);

      // Update status to synced
      await queueService.updateStatus(entry.localId, 'synced', trackingId);

      // Remove from queue after successful sync
      await queueService.removeEntry(entry.localId);

      console.log(`Entry ${entry.localId} synced successfully`);
    } catch (error: any) {
      console.error(`Failed to sync entry ${entry.localId}:`, error);

      // Increment retry count
      await queueService.incrementRetryCount(entry.localId);

      // Update status to failed
      await queueService.updateStatus(
        entry.localId,
        'failed',
        undefined,
        error.message || 'Upload failed'
      );
    }
  }

  /**
   * Calculate exponential backoff delay
   * Requirement 2.4: Exponential backoff (1min, 2min, 4min, 8min, 16min)
   */
  private calculateBackoff(retryCount: number): number {
    // 2^retryCount minutes in milliseconds
    const backoffMinutes = Math.pow(2, retryCount);
    const backoffMs = backoffMinutes * 60 * 1000;
    
    // Cap at max backoff
    return Math.min(backoffMs, SYNC_CONFIG.MAX_BACKOFF_MS);
  }

  /**
   * Force sync now (manual trigger)
   */
  async forceSyncNow(): Promise<void> {
    await this.syncQueue();
  }

  /**
   * Check if currently syncing
   */
  isSyncInProgress(): boolean {
    return this.isSyncing;
  }
}

export const backgroundSyncService = new BackgroundSyncService();
