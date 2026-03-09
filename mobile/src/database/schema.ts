// @ts-ignore - No type definitions available
import SQLite from 'react-native-sqlite-storage';

SQLite.enablePromise(true);

const DATABASE_NAME = 'artisan_catalog.db';
const DATABASE_VERSION = '1.0';
const DATABASE_DISPLAY_NAME = 'Artisan Catalog Database';
const DATABASE_SIZE = 5 * 1024 * 1024; // 5MB

export class Database {
  private db: SQLite.SQLiteDatabase | null = null;

  async init(): Promise<void> {
    try {
      this.db = await SQLite.openDatabase({
        name: DATABASE_NAME,
        location: 'default',
      });

      await this.createTables();
    } catch (error) {
      console.error('Database initialization failed:', error);
      throw error;
    }
  }

  private async createTables(): Promise<void> {
    if (!this.db) throw new Error('Database not initialized');

    const createQueueTable = `
      CREATE TABLE IF NOT EXISTS queue_entries (
        local_id TEXT PRIMARY KEY,
        photo_path TEXT NOT NULL,
        audio_path TEXT NOT NULL,
        photo_size INTEGER NOT NULL,
        audio_size INTEGER NOT NULL,
        captured_at INTEGER NOT NULL,
        sync_status TEXT NOT NULL,
        retry_count INTEGER DEFAULT 0,
        last_retry_at INTEGER,
        tracking_id TEXT,
        error_message TEXT
      );
    `;

    const createIndexes = `
      CREATE INDEX IF NOT EXISTS idx_sync_status ON queue_entries(sync_status);
      CREATE INDEX IF NOT EXISTS idx_tracking_id ON queue_entries(tracking_id);
    `;

    await this.db.executeSql(createQueueTable);
    await this.db.executeSql(createIndexes);
  }

  async close(): Promise<void> {
    if (this.db) {
      await this.db.close();
      this.db = null;
    }
  }

  getDatabase(): SQLite.SQLiteDatabase {
    if (!this.db) throw new Error('Database not initialized');
    return this.db;
  }
}

export const database = new Database();
