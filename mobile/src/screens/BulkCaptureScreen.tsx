import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Alert,
  FlatList,
  Image,
} from 'react-native';
import { mediaCaptureService } from '../services/MediaCapture';
import { queueService } from '../services/QueueService';
import { LocalQueueEntry } from '../types';
import { useLanguage } from '../hooks/useLanguage';

interface CapturedItem {
  id: string;
  photoPath: string;
  audioPath?: string;
  status: 'photo_captured' | 'audio_captured' | 'queued';
}

/**
 * Bulk Capture Screen - Sequential product capture
 * Requirement 19.1: Allow sequential capture of multiple products
 * Requirement 19.2: Display progress for each entry independently
 * Requirement 19.4: Allow review and deletion before sync
 */
export const BulkCaptureScreen: React.FC = () => {
  const [capturedItems, setCapturedItems] = useState<CapturedItem[]>([]);
  const [currentItem, setCurrentItem] = useState<CapturedItem | null>(null);
  const [isCapturing, setIsCapturing] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const { t } = useLanguage();

  /**
   * Start new product capture
   * Requirement 19.1: Sequential capture without returning to home screen
   */
  const handleStartNewCapture = async () => {
    setIsCapturing(true);
    try {
      const photoPath = await mediaCaptureService.capturePhoto();
      
      const newItem: CapturedItem = {
        id: Date.now().toString(),
        photoPath,
        status: 'photo_captured',
      };

      setCurrentItem(newItem);
    } catch (error: any) {
      if (error.message !== 'User cancelled photo capture') {
        Alert.alert(t('error'), t('photo_capture_failed'));
      }
    } finally {
      setIsCapturing(false);
    }
  };

  /**
   * Start audio recording for current item
   */
  const handleStartRecording = async () => {
    if (!currentItem) return;

    try {
      await mediaCaptureService.startRecording();
      setIsRecording(true);
    } catch (error) {
      Alert.alert(t('error'), t('audio_recording_failed'));
    }
  };

  /**
   * Stop audio recording and add to batch
   */
  const handleStopRecording = async () => {
    if (!currentItem) return;

    try {
      const audioPath = await mediaCaptureService.stopRecording();
      setIsRecording(false);

      const completedItem: CapturedItem = {
        ...currentItem,
        audioPath,
        status: 'audio_captured',
      };

      // Add to captured items list
      setCapturedItems(prev => [...prev, completedItem]);

      // Queue the item
      await queueItem(completedItem);

      // Reset for next capture
      setCurrentItem(null);
    } catch (error) {
      Alert.alert(t('error'), t('failed_to_complete_capture'));
    }
  };

  /**
   * Queue captured item
   */
  const queueItem = async (item: CapturedItem) => {
    if (!item.audioPath) return;

    try {
      const photoSize = await mediaCaptureService.getFileSize(item.photoPath);
      const audioSize = await mediaCaptureService.getFileSize(item.audioPath);

      await queueService.addEntry({
        photoPath: item.photoPath,
        audioPath: item.audioPath,
        photoSize,
        audioSize,
      });

      // Update item status
      setCapturedItems(prev =>
        prev.map(i => (i.id === item.id ? { ...i, status: 'queued' } : i))
      );
    } catch (error) {
      console.error('Failed to queue item:', error);
    }
  };

  /**
   * Delete captured item
   * Requirement 19.4: Allow deletion before sync
   */
  const handleDeleteItem = async (item: CapturedItem) => {
    Alert.alert(
      t('confirm_delete'),
      t('confirm_delete_item_message'),
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
              // Delete media files
              await mediaCaptureService.deleteFile(item.photoPath);
              if (item.audioPath) {
                await mediaCaptureService.deleteFile(item.audioPath);
              }

              // Remove from list
              setCapturedItems(prev => prev.filter(i => i.id !== item.id));
            } catch (error) {
              Alert.alert(t('error'), t('failed_to_delete'));
            }
          },
        },
      ]
    );
  };

  /**
   * Cancel current capture
   */
  const handleCancelCurrent = async () => {
    if (isRecording) {
      await mediaCaptureService.stopRecording();
      setIsRecording(false);
    }

    if (currentItem) {
      await mediaCaptureService.deleteFile(currentItem.photoPath);
      setCurrentItem(null);
    }
  };

  /**
   * Finish batch and return
   */
  const handleFinishBatch = () => {
    Alert.alert(
      t('finish_batch'),
      t('finish_batch_message', { count: capturedItems.length }),
      [
        {
          text: t('cancel'),
          style: 'cancel',
        },
        {
          text: t('finish'),
          onPress: () => {
            // TODO: Navigate back or show summary
            setCapturedItems([]);
          },
        },
      ]
    );
  };

  /**
   * Render captured item
   * Requirement 19.2: Display progress independently
   */
  const renderItem = ({ item }: { item: CapturedItem }) => (
    <View style={styles.itemCard}>
      <Image source={{ uri: `file://${item.photoPath}` }} style={styles.itemThumbnail} />
      
      <View style={styles.itemInfo}>
        <Text style={styles.itemStatus}>{t(`item_status_${item.status}`)}</Text>
      </View>

      <TouchableOpacity
        style={styles.itemDeleteButton}
        onPress={() => handleDeleteItem(item)}
      >
        <Text style={styles.itemDeleteText}>✕</Text>
      </TouchableOpacity>
    </View>
  );

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>{t('bulk_capture')}</Text>
        <Text style={styles.headerSubtitle}>
          {capturedItems.length} {t('items_captured')}
        </Text>
      </View>

      {/* Current Capture */}
      {currentItem ? (
        <View style={styles.currentCapture}>
          <Image
            source={{ uri: `file://${currentItem.photoPath}` }}
            style={styles.currentPhoto}
          />

          <Text style={styles.instruction}>{t('record_audio_instruction')}</Text>

          {!isRecording ? (
            <TouchableOpacity
              style={styles.recordButton}
              onPress={handleStartRecording}
            >
              <Text style={styles.buttonText}>{t('start_recording')}</Text>
            </TouchableOpacity>
          ) : (
            <TouchableOpacity
              style={[styles.recordButton, styles.stopButton]}
              onPress={handleStopRecording}
            >
              <Text style={styles.buttonText}>{t('stop_recording')}</Text>
            </TouchableOpacity>
          )}

          <TouchableOpacity style={styles.cancelButton} onPress={handleCancelCurrent}>
            <Text style={styles.cancelButtonText}>{t('cancel')}</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <View style={styles.capturePrompt}>
          <TouchableOpacity
            style={styles.captureButton}
            onPress={handleStartNewCapture}
            disabled={isCapturing}
          >
            <Text style={styles.buttonText}>{t('capture_next_product')}</Text>
          </TouchableOpacity>

          {capturedItems.length > 0 && (
            <TouchableOpacity
              style={styles.finishButton}
              onPress={handleFinishBatch}
            >
              <Text style={styles.finishButtonText}>{t('finish_batch')}</Text>
            </TouchableOpacity>
          )}
        </View>
      )}

      {/* Captured Items List */}
      <View style={styles.itemsList}>
        <Text style={styles.listTitle}>{t('captured_items')}</Text>
        <FlatList
          data={capturedItems}
          renderItem={renderItem}
          keyExtractor={item => item.id}
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.listContent}
        />
      </View>
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
  currentCapture: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  currentPhoto: {
    width: 200,
    height: 200,
    borderRadius: 10,
    marginBottom: 20,
  },
  instruction: {
    fontSize: 18,
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: 30,
    color: '#333',
  },
  recordButton: {
    backgroundColor: '#007AFF',
    paddingHorizontal: 40,
    paddingVertical: 15,
    borderRadius: 25,
  },
  stopButton: {
    backgroundColor: '#FF3B30',
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
  cancelButton: {
    marginTop: 20,
    padding: 10,
  },
  cancelButtonText: {
    color: '#FF3B30',
    fontSize: 16,
  },
  capturePrompt: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  captureButton: {
    backgroundColor: '#007AFF',
    paddingHorizontal: 40,
    paddingVertical: 15,
    borderRadius: 25,
  },
  finishButton: {
    marginTop: 20,
    paddingHorizontal: 30,
    paddingVertical: 12,
    borderRadius: 20,
    borderWidth: 2,
    borderColor: '#34C759',
  },
  finishButtonText: {
    color: '#34C759',
    fontSize: 16,
    fontWeight: 'bold',
  },
  itemsList: {
    backgroundColor: '#fff',
    padding: 15,
    borderTopWidth: 1,
    borderTopColor: '#e0e0e0',
  },
  listTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 10,
  },
  listContent: {
    paddingRight: 10,
  },
  itemCard: {
    width: 120,
    marginRight: 10,
    backgroundColor: '#f9f9f9',
    borderRadius: 8,
    padding: 10,
    position: 'relative',
  },
  itemThumbnail: {
    width: 100,
    height: 100,
    borderRadius: 8,
    marginBottom: 8,
  },
  itemInfo: {
    alignItems: 'center',
  },
  itemStatus: {
    fontSize: 12,
    color: '#666',
  },
  itemDeleteButton: {
    position: 'absolute',
    top: 5,
    right: 5,
    backgroundColor: 'rgba(255, 255, 255, 0.9)',
    width: 24,
    height: 24,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
  },
  itemDeleteText: {
    fontSize: 16,
    color: '#FF3B30',
  },
});
