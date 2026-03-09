/**
 * ReviewScreen
 * 
 * Screen for reviewing and publishing catalog items to ONDC network.
 * Fetches processed catalog data from backend and displays it using CatalogReviewCard.
 * 
 * Flow:
 * 1. User uploads photo + audio (CaptureScreen)
 * 2. Backend processes and returns catalog data
 * 3. User reviews here (ReviewScreen)
 * 4. User publishes to ONDC
 */

import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { CatalogReviewCard } from '../components/CatalogReviewCard';
import type { CatalogItem, PublishResponse } from '../types/catalog';
import axios from 'axios';
import { API_BASE_URL } from '../config';

interface ReviewScreenProps {
  route: {
    params: {
      trackingId: string;
    };
  };
  navigation: any;
}

/**
 * ReviewScreen Component
 * 
 * Fetches catalog data by trackingId and displays for review
 */
export const ReviewScreen: React.FC<ReviewScreenProps> = ({ route, navigation }) => {
  const { trackingId } = route.params;

  const [catalogItem, setCatalogItem] = useState<CatalogItem | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  /**
   * Fetch catalog data from backend
   */
  useEffect(() => {
    fetchCatalogData();
  }, [trackingId]);

  const fetchCatalogData = async () => {
    try {
      setIsLoading(true);
      setError(null);

      // Fetch catalog data from backend
      const response = await axios.get(`${API_BASE_URL}/catalog/${trackingId}`);

      if (response.data && response.data.catalogItem) {
        setCatalogItem(response.data.catalogItem);
      } else {
        setError('Catalog data not found');
      }
    } catch (err: any) {
      console.error('Failed to fetch catalog data:', err);
      setError(err.response?.data?.message || 'Failed to load catalog data');
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Handle publish action
   */
  const handlePublish = async (item: CatalogItem): Promise<PublishResponse> => {
    try {
      // Call backend API to publish to ONDC
      const response = await axios.post(`${API_BASE_URL}/catalog/publish`, {
        trackingId: item.trackingId,
        catalogItem: item,
      });

      return {
        success: response.data.success,
        ondcCatalogId: response.data.ondcCatalogId,
        message: response.data.message,
      };
    } catch (err: any) {
      console.error('Publish failed:', err);
      return {
        success: false,
        message: err.response?.data?.message || 'Publish failed',
        errors: err.response?.data?.errors,
      };
    }
  };

  /**
   * Handle edit action
   */
  const handleEdit = (item: CatalogItem) => {
    Alert.alert(
      'Edit Product',
      'Edit functionality coming soon!',
      [{ text: 'OK' }]
    );
    // TODO: Navigate to edit screen
    // navigation.navigate('Edit', { catalogItem: item });
  };

  /**
   * Handle successful publish
   */
  const handlePublishSuccess = (ondcCatalogId: string) => {
    // Navigate back to queue or home
    navigation.navigate('Queue');
  };

  // Loading state
  if (isLoading) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color="#4CAF50" />
        <Text style={styles.loadingText}>Loading catalog data...</Text>
      </View>
    );
  }

  // Error state
  if (error || !catalogItem) {
    return (
      <View style={styles.centerContainer}>
        <Text style={styles.errorIcon}>❌</Text>
        <Text style={styles.errorText}>{error || 'Failed to load catalog'}</Text>
        <Text style={styles.errorHint}>Please try again later</Text>
      </View>
    );
  }

  // Success state - display catalog review card
  return (
    <View style={styles.container}>
      <CatalogReviewCard
        catalogItem={catalogItem}
        onPublish={handlePublish}
        onEdit={handleEdit}
        onPublishSuccess={handlePublishSuccess}
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F5',
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#F5F5F5',
    padding: 20,
  },
  loadingText: {
    marginTop: 16,
    fontSize: 16,
    color: '#757575',
  },
  errorIcon: {
    fontSize: 64,
    marginBottom: 16,
  },
  errorText: {
    fontSize: 18,
    fontWeight: '600',
    color: '#D32F2F',
    textAlign: 'center',
    marginBottom: 8,
  },
  errorHint: {
    fontSize: 14,
    color: '#757575',
    textAlign: 'center',
  },
});

export default ReviewScreen;
