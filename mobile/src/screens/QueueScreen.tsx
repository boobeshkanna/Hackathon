import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  FlatList,
  StyleSheet,
  Image,
  TouchableOpacity,
  RefreshControl,
  Alert,
} from 'react-native';
import { queueService } from '../services/QueueService';
import { backgroundSyncService } from '../services/BackgroundSync';
import { LocalQueueEntry } from '../types';
import { useLanguage } from '../hooks/useLanguage';

/**
 * Queue Screen - Display queued entries
 * Requirement 10.5: Show preview of queued entries
 * Requirement 20.1: Display preview in vernacular language
 */
export const QueueScreen: React.FC = () => {
  const [entries, setEntries] = useState<LocalQueueEntry[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  const { t } = useLanguage();

  useEffect(() => {
    loadEntries();
  }, []);

  /**
   * Load queue entries
   */
  const loadEntries = async () => {
    try {
      const allEntries = await queueService.getAllEntries();
      setEntries(allEntries);
    } catch (error) {
      console.error('Failed to load entries:', error);
    }
  };

  /**
   * Handle refresh
   */
  const handleRefresh = async () => {
    setRefreshing(true);
    await loadEntries();
    await backgroundSyncService.forceSyncNow();
    setRefreshing(false);
  };

  /**
   * Handle delete entry
   */
  const handleDelete = async (entry: LocalQueueEntry) => {
    Alert.alert(
      t('confirm_delete'),
      t('confirm_delete_message'),
      [
        {
          text: t('cancel'),
          style: 'cancel',
        },
        {
          text: t('delete'),
          style: 'destructive',
          onPress: async () => {
            try {
              await queueService.removeEntry(entry.localId);
              await loadEntries();
            } catch (error) {
              Alert.alert(t('error'), t('failed_to_delete'));
            }
          },
        },
      ]
    );
  };

  /**
   * Get status color
   */
  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'queued':
        return '#FFA500';
      case 'syncing':
        return '#007AFF';
      case 'synced':
        return '#34C759';
      case 'failed':
        return '#FF3B30';
      default:
        return '#8E8E93';
    }
  };

  /**
   * Render queue entry
   */
  const renderEntry = ({ item }: { item: LocalQueueEntry }) => (
    <View style={styles.entryCard}>
      <Image
        source={{ uri: `file://${item.photoPath}` }}
        style={styles.thumbnail}
      />
      
      <View style={styles.entryInfo}>
        <Text style={styles.entryDate}>
          {new Date(item.capturedAt).toLocaleString()}
        </Text>
        
        <View style={styles.statusContainer}>
          <View
            style={[
              styles.statusBadge,
              { backgroundColor: getStatusColor(item.syncStatus) },
            ]}
          >
            <Text style={styles.statusText}>{t(`status_${item.syncStatus}`)}</Text>
          </View>
          
          {item.retryCount > 0 && (
            <Text style={styles.retryText}>
              {t('retry_count')}: {item.retryCount}
            </Text>
          )}
        </View>

        {item.errorMessage && (
          <Text style={styles.errorText}>{item.errorMessage}</Text>
        )}

        {item.trackingId && (
          <Text style={styles.trackingId}>
            {t('tracking_id')}: {item.trackingId.substring(0, 8)}...
          </Text>
        )}
      </View>

      <TouchableOpacity
        style={styles.deleteButton}
        onPress={() => handleDelete(item)}
      >
        <Text style={styles.deleteButtonText}>✕</Text>
      </TouchableOpacity>
    </View>
  );

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>{t('queue_title')}</Text>
        <Text style={styles.headerSubtitle}>
          {entries.length} {t('entries')}
        </Text>
      </View>

      <FlatList
        data={entries}
        renderItem={renderEntry}
        keyExtractor={item => item.localId}
        contentContainerStyle={styles.listContent}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={handleRefresh} />
        }
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Text style={styles.emptyText}>{t('no_entries')}</Text>
          </View>
        }
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  header: {
    backgroundColor: '#fff',
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
  },
  headerSubtitle: {
    fontSize: 14,
    color: '#666',
    marginTop: 5,
  },
  listContent: {
    padding: 10,
  },
  entryCard: {
    backgroundColor: '#fff',
    borderRadius: 10,
    padding: 15,
    marginBottom: 10,
    flexDirection: 'row',
    alignItems: 'center',
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.2,
    shadowRadius: 2,
  },
  thumbnail: {
    width: 80,
    height: 80,
    borderRadius: 8,
    marginRight: 15,
  },
  entryInfo: {
    flex: 1,
  },
  entryDate: {
    fontSize: 14,
    color: '#666',
    marginBottom: 8,
  },
  statusContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 5,
  },
  statusBadge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
    marginRight: 10,
  },
  statusText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: 'bold',
  },
  retryText: {
    fontSize: 12,
    color: '#666',
  },
  errorText: {
    fontSize: 12,
    color: '#FF3B30',
    marginTop: 5,
  },
  trackingId: {
    fontSize: 11,
    color: '#999',
    marginTop: 5,
  },
  deleteButton: {
    width: 30,
    height: 30,
    justifyContent: 'center',
    alignItems: 'center',
  },
  deleteButtonText: {
    fontSize: 24,
    color: '#FF3B30',
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingTop: 100,
  },
  emptyText: {
    fontSize: 16,
    color: '#999',
  },
});
