import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Alert,
  ActivityIndicator,
  Image,
} from 'react-native';
import { mediaCaptureService } from '../services/MediaCapture';
import { queueService } from '../services/QueueService';
import { useLanguage } from '../hooks/useLanguage';

/**
 * Zero-UI Capture Screen
 * Requirement 1.1: Single-button camera interface
 * Requirement 1.5: No text input or dropdown forms
 */
export const CaptureScreen: React.FC = () => {
  const [isCapturing, setIsCapturing] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [capturedPhoto, setCapturedPhoto] = useState<string | null>(null);
  const [step, setStep] = useState<'photo' | 'audio' | 'done'>('photo');
  const { t } = useLanguage();

  useEffect(() => {
    // Cleanup old files on mount
    mediaCaptureService.cleanupOldFiles();
  }, []);

  /**
   * Handle photo capture
   */
  const handleCapturePhoto = async () => {
    setIsCapturing(true);
    try {
      const photoPath = await mediaCaptureService.capturePhoto();
      setCapturedPhoto(photoPath);
      setStep('audio');
    } catch (error: any) {
      if (error.message !== 'User cancelled photo capture') {
        Alert.alert(t('error'), t('photo_capture_failed'));
      }
    } finally {
      setIsCapturing(false);
    }
  };

  /**
   * Handle audio recording start
   */
  const handleStartRecording = async () => {
    try {
      await mediaCaptureService.startRecording();
      setIsRecording(true);
    } catch (error) {
      Alert.alert(t('error'), t('audio_recording_failed'));
    }
  };

  /**
   * Handle audio recording stop and queue entry
   */
  const handleStopRecording = async () => {
    if (!capturedPhoto) {
      Alert.alert(t('error'), t('no_photo_captured'));
      return;
    }

    try {
      const audioPath = await mediaCaptureService.stopRecording();
      setIsRecording(false);

      // Get file sizes
      const photoSize = await mediaCaptureService.getFileSize(capturedPhoto);
      const audioSize = await mediaCaptureService.getFileSize(audioPath);

      // Add to queue
      await queueService.addEntry({
        photoPath: capturedPhoto,
        audioPath,
        photoSize,
        audioSize,
      });

      // Reset for next capture
      setCapturedPhoto(null);
      setStep('photo');
      
      Alert.alert(t('success'), t('entry_queued'));
    } catch (error) {
      Alert.alert(t('error'), t('failed_to_queue'));
    }
  };

  /**
   * Handle cancel
   */
  const handleCancel = async () => {
    if (isRecording) {
      await mediaCaptureService.stopRecording();
      setIsRecording(false);
    }
    
    if (capturedPhoto) {
      await mediaCaptureService.deleteFile(capturedPhoto);
      setCapturedPhoto(null);
    }
    
    setStep('photo');
  };

  return (
    <View style={styles.container}>
      {/* Photo Step */}
      {step === 'photo' && (
        <View style={styles.stepContainer}>
          <Text style={styles.instruction}>{t('capture_photo_instruction')}</Text>
          
          <TouchableOpacity
            style={[styles.captureButton, isCapturing && styles.buttonDisabled]}
            onPress={handleCapturePhoto}
            disabled={isCapturing}
          >
            {isCapturing ? (
              <ActivityIndicator size="large" color="#fff" />
            ) : (
              <Text style={styles.buttonText}>{t('capture_photo')}</Text>
            )}
          </TouchableOpacity>
        </View>
      )}

      {/* Audio Step */}
      {step === 'audio' && (
        <View style={styles.stepContainer}>
          {capturedPhoto && (
            <Image source={{ uri: `file://${capturedPhoto}` }} style={styles.preview} />
          )}
          
          <Text style={styles.instruction}>{t('record_audio_instruction')}</Text>
          
          {!isRecording ? (
            <TouchableOpacity
              style={styles.captureButton}
              onPress={handleStartRecording}
            >
              <Text style={styles.buttonText}>{t('start_recording')}</Text>
            </TouchableOpacity>
          ) : (
            <TouchableOpacity
              style={[styles.captureButton, styles.recordingButton]}
              onPress={handleStopRecording}
            >
              <Text style={styles.buttonText}>{t('stop_recording')}</Text>
            </TouchableOpacity>
          )}

          <TouchableOpacity
            style={styles.cancelButton}
            onPress={handleCancel}
          >
            <Text style={styles.cancelButtonText}>{t('cancel')}</Text>
          </TouchableOpacity>
        </View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  stepContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  instruction: {
    fontSize: 20,
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: 40,
    color: '#333',
  },
  captureButton: {
    backgroundColor: '#007AFF',
    width: 200,
    height: 200,
    borderRadius: 100,
    justifyContent: 'center',
    alignItems: 'center',
    elevation: 5,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 3.84,
  },
  recordingButton: {
    backgroundColor: '#FF3B30',
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  buttonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: 'bold',
  },
  preview: {
    width: 200,
    height: 200,
    borderRadius: 10,
    marginBottom: 20,
  },
  cancelButton: {
    marginTop: 20,
    padding: 15,
  },
  cancelButtonText: {
    color: '#FF3B30',
    fontSize: 16,
  },
});
