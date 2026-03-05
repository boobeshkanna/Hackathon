import { database } from '../database/schema';
import { LocalQueueEntry, QueueStatus, CaptureResult } from '../types';
import { v4 as uuidv4 } from 'react-native-uuid';

/**
 * Queue Service for managing local catalog entries
 * Requirement 2.1: Store compressed photo and audio in persistent local queue
 * Requirement 2.2: Continue accepting entries when network unavailable
 */
export class QueueService {
  /**
   * Add new entry to queue
   * Requirement 2.1: Store in persistent local queue
   */
  async addEntry(capture: CaptureResult): Promise<LocalQueueEntry> {
    const entry: LocalQueueEntry = {
      localId: uuidv4(),
      photoPath: capture.photoPath,
      audioPath: capture.audioPath,
      photoSize: capture.photoSize,
      audioSize: capture.audioSize,
      capturedAt: Date.now(),
      syncStatus: 'queued',
      retryCount: 0,
    };

    const db = database.getDatabase();
    
    await db.executeSql(
      `INSERT INTO queue_entries 
       (local_id, photo_path, audio_path, photo_size, audio_size, 
        captured_at, sync_status, retry_count) 
       VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
      [
        entry.localId,
        entry.photoPath,
        entry.audioPath,
        entry.photoSize,
        entry.audioSize,
        entry.capturedAt,
        entry.syncStatus,
        entry.retryCount,
      ]
    );

    return entry;
  }

  /**
   * Get all queued entries
   */
  async getQueuedEntries(): Promise<LocalQueueEntry[]> {
    const db = database.getDatabase();
    
    const [result] = await db.executeSql(
      `SELECT * FROM queue_entries 
       WHERE sync_status IN ('queued', 'failed') 
       ORDER BY captured_at ASC`
    );

    return this.mapResultsToEntries(result.rows);
  }

  /**
   * Get all entries (for display)
   */
  async getAllEntries(): Promise<LocalQueueEntry[]> {
    const db = database.getDatabase();
    
    const [result] = await db.executeSql(
      `SELECT * FROM queue_entries 
       ORDER BY captured_at DESC`
    );

    return this.mapResultsToEntries(result.rows);
  }

  /**
   * Get entry by local ID
   */
  async getEntry(localId: string): Promise<LocalQueueEntry | null> {
    const db = database.getDatabase();
    
    const [result] = await db.executeSql(
      `SELECT * FROM queue_entries WHERE local_id = ?`,
      [localId]
    );

    if (result.rows.length === 0) {
      return null;
    }

    return this.mapRowToEntry(result.rows.item(0));
  }

  /**
   * Update entry status
   */
  async updateStatus(
    localId: string,
    status: QueueStatus,
    trackingId?: string,
    errorMessage?: string
  ): Promise<void> {
    const db = database.getDatabase();
    
    await db.executeSql(
      `UPDATE queue_entries 
       SET sync_status = ?, tracking_id = ?, error_message = ?
       WHERE local_id = ?`,
      [status, trackingId || null, errorMessage || null, localId]
    );
  }

  /**
   * Update retry count
   * Requirement 2.4: Track retry attempts
   */
  async incrementRetryCount(localId: string): Promise<void> {
    const db = database.getDatabase();
    
    await db.executeSql(
      `UPDATE queue_entries 
       SET retry_count = retry_count + 1, last_retry_at = ?
       WHERE local_id = ?`,
      [Date.now(), localId]
    );
  }

  /**
   * Remove entry from queue
   * Requirement 2.5: Remove successfully synced entries
   */
  async removeEntry(localId: string): Promise<void> {
    const db = database.getDatabase();
    
    await db.executeSql(
      `DELETE FROM queue_entries WHERE local_id = ?`,
      [localId]
    );
  }

  /**
   * Get queue count by status
   */
  async getQueueCount(status?: QueueStatus): Promise<number> {
    const db = database.getDatabase();
    
    let query = 'SELECT COUNT(*) as count FROM queue_entries';
    const params: any[] = [];
    
    if (status) {
      query += ' WHERE sync_status = ?';
      params.push(status);
    }

    const [result] = await db.executeSql(query, params);
    return result.rows.item(0).count;
  }

  /**
   * Clear all synced entries
   */
  async clearSyncedEntries(): Promise<void> {
    const db = database.getDatabase();
    
    await db.executeSql(
      `DELETE FROM queue_entries WHERE sync_status = 'synced'`
    );
  }

  /**
   * Reset failed entries to queued for retry
   */
  async resetFailedEntries(): Promise<void> {
    const db = database.getDatabase();
    
    await db.executeSql(
      `UPDATE queue_entries 
       SET sync_status = 'queued', error_message = NULL
       WHERE sync_status = 'failed'`
    );
  }

  /**
   * Map database rows to entries
   */
  private mapResultsToEntries(rows: any): LocalQueueEntry[] {
    const entries: LocalQueueEntry[] = [];
    
    for (let i = 0; i < rows.length; i++) {
      entries.push(this.mapRowToEntry(rows.item(i)));
    }
    
    return entries;
  }

  /**
   * Map single database row to entry
   */
  private mapRowToEntry(row: any): LocalQueueEntry {
    return {
      localId: row.local_id,
      photoPath: row.photo_path,
      audioPath: row.audio_path,
      photoSize: row.photo_size,
      audioSize: row.audio_size,
      capturedAt: row.captured_at,
      syncStatus: row.sync_status as QueueStatus,
      retryCount: row.retry_count,
      lastRetryAt: row.last_retry_at || undefined,
      trackingId: row.tracking_id || undefined,
      errorMessage: row.error_message || undefined,
    };
  }
}

export const queueService = new QueueService();
