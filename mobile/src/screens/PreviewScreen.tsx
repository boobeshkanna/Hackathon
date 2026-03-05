import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Image,
  ScrollView,
  TouchableOpacity,
  Alert,
} from 'react-native';
import { queueService } from '../services/QueueService';
import { mediaCaptureService } from '../services/MediaCapture';
import { LocalQueueEntry, ExtractedAttributes } from '../types';
import { useLanguage } from '../hooks/useLanguage';

interface PreviewScreenProps {
  entryId: string;
  onClose: () => void;
  onDelete: () => void;
}

/**
 * Preview Screen - Display entry preview
 * Requirement 20.1: Generate local preview from captured media
 * Requirement 20.2: Allow artisan to review and delete queued entries
 * Requirement 20.5: Display preview in vernacular language
 */
export const PreviewScreen: React.FC<PreviewScreenProps> = ({
  entryId,
  onClose,
  onDelete,
}) => {
  const [entry, setEntry] = useState<LocalQueueEntry | null>(null);
  const [attributes, setAttributes] = useState<ExtractedAttributes | null>(null);
  const { t } = useLanguage();

  useEffect(() => {
    loadEntry();
  }, [entryId]);

  /**
   * Load entry details
   * Requirement 20.1: Generate preview within 1 second
   */
  const loadEntry = async () => {
    try {
      const loadedEntry = await queueService.getEntry(entryId);
      if (loadedEntry) {
        setEntry(loadedEntry);
        // TODO: Load extracted attributes if available
      }
    } catch (error) {
      console.error('Failed to load entry:', error);
    }
  };

  /**
   * Handle delete
   * Requirement 20.2: Allow deletion before sync
   */
  const handleDelete = () => {
    Alert.alert(
      t('confirm_delete'),
      t('confirm_delete_preview_message'),
      [
        {
          text: t('cancel'),
          style: 'cancel',
        },
        {
          text: t('delete'),
          style: 'destructive',
          onPress: async () => {
            if (!entry) return;

            try {
              // Delete media files
              await mediaCaptureService.deleteFile(entry.photoPath);
              await mediaCaptureService.deleteFile(entry.audioPath);

              // Remove from queue
              await queueService.removeEntry(entry.localId);

              onDelete();
            } catch (error) {
              Alert.alert(t('error'), t('failed_to_delete'));
            }
          },
        },
      ]
    );
  };

  if (!entry) {
    return (
      <View style={styles.container}>
        <Text style={styles.loadingText}>{t('loading')}</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={onClose} style={styles.closeButton}>
          <Text style={styles.closeButtonText}>✕</Text>
        </TouchableOpacity>
        <Text style={styles.headerTitle}>{t('preview')}</Text>
        <TouchableOpacity onPress={handleDelete} style={styles.deleteButton}>
          <Text style={styles.deleteButtonText}>{t('delete')}</Text>
        </TouchableOpacity>
      </View>

      <ScrollView style={styles.content}>
        {/* Photo Preview */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>{t('photo')}</Text>
          <Image
            source={{ uri: `file://${entry.photoPath}` }}
            style={styles.photoPreview}
            resizeMode="contain"
          />
          <Text style={styles.fileInfo}>
            {t('size')}: {(entry.photoSize / 1024).toFixed(2)} KB
          </Text>
        </View>

        {/* Audio Preview */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>{t('audio')}</Text>
          <View style={styles.audioPreview}>
            <Text style={styles.audioIcon}>🎤</Text>
            <Text style={styles.fileInfo}>
              {t('size')}: {(entry.audioSize / 1024).toFixed(2)} KB
            </Text>
          </View>
        </View>

        {/* Status */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>{t('status')}</Text>
          <View style={styles.statusCard}>
            <Text style={styles.statusLabel}>{t('sync_status')}:</Text>
            <Text style={styles.statusValue}>{t(`status_${entry.syncStatus}`)}</Text>
          </View>

          {entry.trackingId && (
            <View style={styles.statusCard}>
              <Text style={styles.statusLabel}>{t('tracking_id')}:</Text>
              <Text style={styles.statusValue}>{entry.trackingId}</Text>
            </View>
          )}

          {entry.retryCount > 0 && (
            <View style={styles.statusCard}>
              <Text style={styles.statusLabel}>{t('retry_count')}:</Text>
              <Text style={styles.statusValue}>{entry.retryCount}</Text>
            </View>
          )}

          {entry.errorMessage && (
            <View style={styles.statusCard}>
              <Text style={styles.statusLabel}>{t('error')}:</Text>
              <Text style={[styles.statusValue, styles.errorText]}>
                {entry.errorMessage}
              </Text>
            </View>
          )}
        </View>

        {/* Extracted Attributes (if available) */}
        {attributes && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>{t('extracted_info')}</Text>
            
            {attributes.category && (
              <View style={styles.attributeCard}>
                <Text style={styles.attributeLabel}>{t('category')}:</Text>
                <Text style={styles.attributeValue}>{attributes.category}</Text>
              </View>
            )}

            {attributes.material && attributes.material.length > 0 && (
              <View style={styles.attributeCard}>
                <Text style={styles.attributeLabel}>{t('material')}:</Text>
                <Text style={styles.attributeValue}>
                  {attributes.material.join(', ')}
                </Text>
              </View>
            )}

            {attributes.colors && attributes.colors.length > 0 && (
              <View style={styles.attributeCard}>
                <Text style={styles.attributeLabel}>{t('colors')}:</Text>
                <Text style={styles.attributeValue}>
                  {attributes.colors.join(', ')}
                </Text>
              </View>
            )}

            {attributes.price && (
              <View style={styles.attributeCard}>
                <Text style={styles.attributeLabel}>{t('price')}:</Text>
                <Text style={styles.attributeValue}>
                  {attributes.price.currency} {attributes.price.value}
                </Text>
              </View>
            )}

            {attributes.shortDescription && (
              <View style={styles.attributeCard}>
                <Text style={styles.attributeLabel}>{t('description')}:</Text>
                <Text style={styles.attributeValue}>
                  {attributes.shortDescription}
                </Text>
              </View>
            )}
          </View>
        )}

        {/* Metadata */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>{t('metadata')}</Text>
          <View style={styles.metadataCard}>
            <Text style={styles.metadataLabel}>{t('captured_at')}:</Text>
            <Text style={styles.metadataValue}>
              {new Date(entry.capturedAt).toLocaleString()}
            </Text>
          </View>
        </View>
      </ScrollView>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: '#fff',
    padding: 15,
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  closeButton: {
    padding: 5,
  },
  closeButtonText: {
    fontSize: 24,
    color: '#007AFF',
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
  },
  deleteButton: {
    padding: 5,
  },
  deleteButtonText: {
    fontSize: 16,
    color: '#FF3B30',
  },
  content: {
    flex: 1,
  },
  section: {
    backgroundColor: '#fff',
    marginTop: 10,
    padding: 15,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 10,
  },
  photoPreview: {
    width: '100%',
    height: 300,
    borderRadius: 10,
    backgroundColor: '#f0f0f0',
  },
  audioPreview: {
    padding: 20,
    backgroundColor: '#f0f0f0',
    borderRadius: 10,
    alignItems: 'center',
  },
  audioIcon: {
    fontSize: 48,
    marginBottom: 10,
  },
  fileInfo: {
    fontSize: 14,
    color: '#666',
    marginTop: 10,
  },
  statusCard: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  statusLabel: {
    fontSize: 14,
    color: '#666',
  },
  statusValue: {
    fontSize: 14,
    color: '#333',
    fontWeight: '500',
  },
  errorText: {
    color: '#FF3B30',
  },
  attributeCard: {
    marginBottom: 15,
  },
  attributeLabel: {
    fontSize: 14,
    color: '#666',
    marginBottom: 5,
  },
  attributeValue: {
    fontSize: 16,
    color: '#333',
  },
  metadataCard: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  metadataLabel: {
    fontSize: 14,
    color: '#666',
  },
  metadataValue: {
    fontSize: 14,
    color: '#333',
  },
  loadingText: {
    fontSize: 16,
    color: '#999',
    textAlign: 'center',
    marginTop: 50,
  },
});
