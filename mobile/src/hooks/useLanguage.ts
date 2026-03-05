import { useState, useEffect } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { LANGUAGE_CONFIG } from '../config';

// Language translations
const translations: Record<string, Record<string, string>> = {
  hi: {
    // Hindi translations
    capture_photo_instruction: 'उत्पाद की फोटो लें',
    capture_photo: 'फोटो लें',
    record_audio_instruction: 'उत्पाद के बारे में बोलें',
    start_recording: 'रिकॉर्डिंग शुरू करें',
    stop_recording: 'रिकॉर्डिंग बंद करें',
    cancel: 'रद्द करें',
    delete: 'हटाएं',
    error: 'त्रुटि',
    success: 'सफलता',
    photo_capture_failed: 'फोटो लेने में विफल',
    audio_recording_failed: 'रिकॉर्डिंग में विफल',
    no_photo_captured: 'कोई फोटो नहीं ली गई',
    failed_to_queue: 'कतार में जोड़ने में विफल',
    entry_queued: 'प्रविष्टि कतार में जोड़ी गई',
    queue_title: 'कतार',
    entries: 'प्रविष्टियाँ',
    no_entries: 'कोई प्रविष्टि नहीं',
    status_queued: 'कतार में',
    status_syncing: 'सिंक हो रहा है',
    status_synced: 'सिंक हो गया',
    status_failed: 'विफल',
    retry_count: 'पुनः प्रयास',
    tracking_id: 'ट्रैकिंग आईडी',
    confirm_delete: 'हटाने की पुष्टि करें',
    confirm_delete_message: 'क्या आप इस प्रविष्टि को हटाना चाहते हैं?',
    failed_to_delete: 'हटाने में विफल',
    preview: 'पूर्वावलोकन',
    photo: 'फोटो',
    audio: 'ऑडियो',
    size: 'आकार',
    status: 'स्थिति',
    sync_status: 'सिंक स्थिति',
    extracted_info: 'निकाली गई जानकारी',
    category: 'श्रेणी',
    material: 'सामग्री',
    colors: 'रंग',
    price: 'मूल्य',
    description: 'विवरण',
    metadata: 'मेटाडेटा',
    captured_at: 'कैप्चर किया गया',
    loading: 'लोड हो रहा है...',
    bulk_capture: 'बल्क कैप्चर',
    items_captured: 'आइटम कैप्चर किए गए',
    capture_next_product: 'अगला उत्पाद कैप्चर करें',
    finish_batch: 'बैच समाप्त करें',
    finish_batch_message: 'क्या आप {count} आइटम के साथ बैच समाप्त करना चाहते हैं?',
    finish: 'समाप्त करें',
    captured_items: 'कैप्चर किए गए आइटम',
    item_status_photo_captured: 'फोटो ली गई',
    item_status_audio_captured: 'ऑडियो रिकॉर्ड किया गया',
    item_status_queued: 'कतार में',
    confirm_delete_preview_message: 'क्या आप इस प्रविष्टि और इसकी मीडिया फ़ाइलों को हटाना चाहते हैं?',
    confirm_delete_item_message: 'क्या आप इस आइटम को हटाना चाहते हैं?',
  },
  en: {
    // English translations (fallback)
    capture_photo_instruction: 'Take a photo of the product',
    capture_photo: 'Capture Photo',
    record_audio_instruction: 'Describe the product',
    start_recording: 'Start Recording',
    stop_recording: 'Stop Recording',
    cancel: 'Cancel',
    delete: 'Delete',
    error: 'Error',
    success: 'Success',
    photo_capture_failed: 'Failed to capture photo',
    audio_recording_failed: 'Failed to record audio',
    no_photo_captured: 'No photo captured',
    failed_to_queue: 'Failed to add to queue',
    entry_queued: 'Entry added to queue',
    queue_title: 'Queue',
    entries: 'Entries',
    no_entries: 'No entries',
    status_queued: 'Queued',
    status_syncing: 'Syncing',
    status_synced: 'Synced',
    status_failed: 'Failed',
    retry_count: 'Retry Count',
    tracking_id: 'Tracking ID',
    confirm_delete: 'Confirm Delete',
    confirm_delete_message: 'Are you sure you want to delete this entry?',
    failed_to_delete: 'Failed to delete',
    preview: 'Preview',
    photo: 'Photo',
    audio: 'Audio',
    size: 'Size',
    status: 'Status',
    sync_status: 'Sync Status',
    extracted_info: 'Extracted Information',
    category: 'Category',
    material: 'Material',
    colors: 'Colors',
    price: 'Price',
    description: 'Description',
    metadata: 'Metadata',
    captured_at: 'Captured At',
    loading: 'Loading...',
    bulk_capture: 'Bulk Capture',
    items_captured: 'Items Captured',
    capture_next_product: 'Capture Next Product',
    finish_batch: 'Finish Batch',
    finish_batch_message: 'Do you want to finish the batch with {count} items?',
    finish: 'Finish',
    captured_items: 'Captured Items',
    item_status_photo_captured: 'Photo Captured',
    item_status_audio_captured: 'Audio Recorded',
    item_status_queued: 'Queued',
    confirm_delete_preview_message: 'Are you sure you want to delete this entry and its media files?',
    confirm_delete_item_message: 'Are you sure you want to delete this item?',
  },
};

/**
 * Language hook for vernacular language support
 * Requirement 10.4: Display in artisan's vernacular language
 */
export const useLanguage = () => {
  const [language, setLanguage] = useState<string>(LANGUAGE_CONFIG.DEFAULT_LANGUAGE);

  useEffect(() => {
    loadLanguage();
  }, []);

  const loadLanguage = async () => {
    try {
      const savedLanguage = await AsyncStorage.getItem('app_language');
      if (savedLanguage && LANGUAGE_CONFIG.SUPPORTED_LANGUAGES.includes(savedLanguage)) {
        setLanguage(savedLanguage);
      }
    } catch (error) {
      console.error('Failed to load language:', error);
    }
  };

  const changeLanguage = async (newLanguage: string) => {
    if (!LANGUAGE_CONFIG.SUPPORTED_LANGUAGES.includes(newLanguage)) {
      console.warn('Unsupported language:', newLanguage);
      return;
    }

    try {
      await AsyncStorage.setItem('app_language', newLanguage);
      setLanguage(newLanguage);
    } catch (error) {
      console.error('Failed to save language:', error);
    }
  };

  const t = (key: string, params?: Record<string, any>): string => {
    let translation = translations[language]?.[key] || translations.en[key] || key;

    // Replace parameters
    if (params) {
      Object.keys(params).forEach(param => {
        translation = translation.replace(`{${param}}`, params[param]);
      });
    }

    return translation;
  };

  return {
    language,
    changeLanguage,
    t,
  };
};
