import messaging from '@react-native-firebase/messaging';
import { Platform, PermissionsAndroid } from 'react-native';
import { queueService } from './QueueService';
import { StatusUpdate } from '../types';

/**
 * Notification Service for Firebase Cloud Messaging
 * Requirement 10.4: Display status in artisan's vernacular language
 * Requirement 10.5: Show preview of queued entries
 * Requirement 20.4: Update preview when AI processing completes
 */
export class NotificationService {
  private fcmToken: string | null = null;

  /**
   * Initialize Firebase Cloud Messaging
   * Requirement 20.1: Integrate Firebase Cloud Messaging
   */
  async initialize(): Promise<void> {
    try {
      // Request permission
      const authStatus = await messaging().requestPermission();
      const enabled =
        authStatus === messaging.AuthorizationStatus.AUTHORIZED ||
        authStatus === messaging.AuthorizationStatus.PROVISIONAL;

      if (!enabled) {
        console.warn('FCM permission not granted');
        return;
      }

      // Get FCM token
      this.fcmToken = await messaging().getToken();
      console.log('FCM Token:', this.fcmToken);

      // Listen for token refresh
      messaging().onTokenRefresh(token => {
        this.fcmToken = token;
        console.log('FCM Token refreshed:', token);
        // TODO: Send token to backend
      });

      // Handle foreground messages
      messaging().onMessage(async remoteMessage => {
        console.log('Foreground message:', remoteMessage);
        await this.handleNotification(remoteMessage);
      });

      // Handle background messages
      messaging().setBackgroundMessageHandler(async remoteMessage => {
        console.log('Background message:', remoteMessage);
        await this.handleNotification(remoteMessage);
      });
    } catch (error) {
      console.error('Failed to initialize FCM:', error);
    }
  }

  /**
   * Handle incoming notification
   * Requirement 20.4: Update preview when AI processing completes
   */
  private async handleNotification(remoteMessage: any): Promise<void> {
    try {
      const data = remoteMessage.data;
      
      if (!data || !data.trackingId) {
        return;
      }

      const statusUpdate: StatusUpdate = {
        trackingId: data.trackingId,
        stage: data.stage,
        message: data.message,
        catalogId: data.catalogId,
        attributes: data.attributes ? JSON.parse(data.attributes) : undefined,
      };

      // Update local queue entry status
      await this.updateLocalEntry(statusUpdate);

      // Show local notification
      await this.showLocalNotification(statusUpdate);
    } catch (error) {
      console.error('Failed to handle notification:', error);
    }
  }

  /**
   * Update local queue entry with status
   */
  private async updateLocalEntry(statusUpdate: StatusUpdate): Promise<void> {
    try {
      // Find entry by tracking ID
      const entries = await queueService.getAllEntries();
      const entry = entries.find(e => e.trackingId === statusUpdate.trackingId);

      if (!entry) {
        return;
      }

      // Update status based on stage
      if (statusUpdate.stage === 'completed') {
        await queueService.updateStatus(entry.localId, 'synced', statusUpdate.trackingId);
      } else if (statusUpdate.stage === 'failed') {
        await queueService.updateStatus(
          entry.localId,
          'failed',
          statusUpdate.trackingId,
          statusUpdate.message
        );
      }
    } catch (error) {
      console.error('Failed to update local entry:', error);
    }
  }

  /**
   * Show local notification
   * Requirement 10.4: Display in vernacular language
   */
  private async showLocalNotification(statusUpdate: StatusUpdate): Promise<void> {
    // TODO: Implement local notification display
    // This would use react-native-push-notification or similar
    console.log('Show notification:', statusUpdate);
  }

  /**
   * Get FCM token
   */
  getFCMToken(): string | null {
    return this.fcmToken;
  }

  /**
   * Request notification permissions (Android 13+)
   */
  async requestPermissions(): Promise<boolean> {
    if (Platform.OS === 'android' && Platform.Version >= 33) {
      try {
        const granted = await PermissionsAndroid.request(
          PermissionsAndroid.PERMISSIONS.POST_NOTIFICATIONS
        );
        return granted === PermissionsAndroid.RESULTS.GRANTED;
      } catch (error) {
        console.error('Failed to request notification permission:', error);
        return false;
      }
    }
    return true;
  }
}

export const notificationService = new NotificationService();
