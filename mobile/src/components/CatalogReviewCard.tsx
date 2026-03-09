/**
 * CatalogReviewCard Component
 * 
 * Production-ready React Native component for the "Review & Publish" screen.
 * Designed for rural artisans with low digital literacy on low-end Android devices.
 * 
 * Key Features:
 * - Zero-UI design philosophy: highly visual, minimal text
 * - Large touch targets (min 48x48dp)
 * - Lightweight for 512MB RAM devices
 * - ONDC Beckn Protocol compliant data display
 * - Cultural storytelling through rich attributes
 * 
 * @requirements React Native 0.72+
 */

import React, { useState } from 'react';
import {
  View,
  Text,
  Image,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  Dimensions,
  Alert,
  ActivityIndicator,
} from 'react-native';
import type { CatalogItem, PublishResponse } from '../types/catalog';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

/**
 * Props for CatalogReviewCard component
 */
interface CatalogReviewCardProps {
  /** The catalog item to display */
  catalogItem: CatalogItem;
  
  /** Callback when user taps "Publish to ONDC" */
  onPublish: (item: CatalogItem) => Promise<PublishResponse>;
  
  /** Optional: Callback when user taps "Edit" */
  onEdit?: (item: CatalogItem) => void;
  
  /** Optional: Callback after successful publish */
  onPublishSuccess?: (ondcCatalogId: string) => void;
}

/**
 * CatalogReviewCard Component
 * 
 * Displays catalog item data in a visually rich, easy-to-understand format
 * for artisan review before publishing to ONDC network.
 */
export const CatalogReviewCard: React.FC<CatalogReviewCardProps> = ({
  catalogItem,
  onPublish,
  onEdit,
  onPublishSuccess,
}) => {
  // Local state for publish action
  const [isPublishing, setIsPublishing] = useState(false);

  /**
   * Handle publish button press
   * Shows confirmation dialog before publishing
   */
  const handlePublish = () => {
    Alert.alert(
      '🚀 Publish to ONDC?',
      'Your product will be visible to buyers across India. Continue?',
      [
        {
          text: 'Cancel',
          style: 'cancel',
        },
        {
          text: 'Publish',
          onPress: executePublish,
          style: 'default',
        },
      ],
      { cancelable: true }
    );
  };

  /**
   * Execute the publish action
   */
  const executePublish = async () => {
    try {
      setIsPublishing(true);
      
      const response = await onPublish(catalogItem);
      
      if (response.success && response.ondcCatalogId) {
        // Success feedback
        Alert.alert(
          '✅ Published Successfully!',
          'Your product is now live on ONDC network.',
          [{ text: 'OK', onPress: () => onPublishSuccess?.(response.ondcCatalogId!) }]
        );
      } else {
        // Failure feedback
        Alert.alert(
          '❌ Publish Failed',
          response.message || 'Please try again later.',
          [{ text: 'OK' }]
        );
      }
    } catch (error) {
      console.error('Publish error:', error);
      Alert.alert(
        '❌ Error',
        'Network error. Please check your connection and try again.',
        [{ text: 'OK' }]
      );
    } finally {
      setIsPublishing(false);
    }
  };

  /**
   * Render attribute pills/badges
   */
  const renderAttributePills = () => {
    const pills: { label: string; value: string }[] = [];

    // Material
    if (catalogItem.tags.material) {
      pills.push({ label: '🧵 Material', value: catalogItem.tags.material });
    }

    // Color
    if (catalogItem.tags.color) {
      pills.push({ label: '🎨 Color', value: catalogItem.tags.color });
    }

    // Craft Technique
    if (catalogItem.tags.craftTechnique) {
      pills.push({ label: '✋ Craft', value: catalogItem.tags.craftTechnique });
    }

    // Region
    if (catalogItem.tags.region) {
      pills.push({ label: '📍 Origin', value: catalogItem.tags.region });
    }

    // GI Tag
    if (catalogItem.tags.geographicalIndication) {
      pills.push({ label: '🏅 GI Tag', value: catalogItem.tags.geographicalIndication });
    }

    // Artisan Lineage
    if (catalogItem.tags.artisanLineage) {
      pills.push({ label: '👨‍🎨 Artisan', value: catalogItem.tags.artisanLineage });
    }

    return (
      <View style={styles.pillsContainer}>
        {pills.map((pill, index) => (
          <View key={index} style={styles.pill}>
            <Text style={styles.pillLabel}>{pill.label}</Text>
            <Text style={styles.pillValue}>{pill.value}</Text>
          </View>
        ))}
      </View>
    );
  };

  /**
   * Render Cultural Specific Items (CSIs)
   */
  const renderCSIs = () => {
    if (!catalogItem.csis || catalogItem.csis.length === 0) {
      return null;
    }

    return (
      <View style={styles.csiSection}>
        <Text style={styles.sectionTitle}>🌟 Cultural Story</Text>
        {catalogItem.csis.map((csi, index) => (
          <View key={index} style={styles.csiCard}>
            <Text style={styles.csiVernacular}>{csi.vernacularTerm}</Text>
            <Text style={styles.csiTransliteration}>({csi.transliteration})</Text>
            <Text style={styles.csiContext}>{csi.englishContext}</Text>
          </View>
        ))}
      </View>
    );
  };

  // Get primary image (first image or placeholder)
  const primaryImage = catalogItem.descriptor.images[0] || 'https://via.placeholder.com/400x400?text=No+Image';

  return (
    <ScrollView style={styles.container} showsVerticalScrollIndicator={false}>
      {/* Hero Image Section */}
      <View style={styles.heroSection}>
        <Image
          source={{ uri: primaryImage }}
          style={styles.heroImage}
          resizeMode="cover"
        />
      </View>

      {/* Content Card */}
      <View style={styles.contentCard}>
        {/* Product Name */}
        <Text style={styles.productName}>{catalogItem.descriptor.name}</Text>

        {/* Category Badge */}
        <View style={styles.categoryBadge}>
          <Text style={styles.categoryText}>{catalogItem.categoryId}</Text>
        </View>

        {/* Price Section */}
        <View style={styles.priceSection}>
          <Text style={styles.priceLabel}>Price</Text>
          <Text style={styles.priceValue}>
            {catalogItem.price.currency} {catalogItem.price.value}
          </Text>
        </View>

        {/* Short Description */}
        <View style={styles.descriptionSection}>
          <Text style={styles.sectionTitle}>📝 Description</Text>
          <Text style={styles.descriptionText}>{catalogItem.descriptor.shortDesc}</Text>
        </View>

        {/* Attribute Pills */}
        {renderAttributePills()}

        {/* Cultural Specific Items */}
        {renderCSIs()}

        {/* Action Buttons */}
        <View style={styles.actionSection}>
          {/* Edit Button (Optional) */}
          {onEdit && (
            <TouchableOpacity
              style={styles.editButton}
              onPress={() => onEdit(catalogItem)}
              disabled={isPublishing}
            >
              <Text style={styles.editButtonText}>✏️ Edit</Text>
            </TouchableOpacity>
          )}

          {/* Publish Button */}
          <TouchableOpacity
            style={[styles.publishButton, isPublishing && styles.publishButtonDisabled]}
            onPress={handlePublish}
            disabled={isPublishing}
            activeOpacity={0.8}
          >
            {isPublishing ? (
              <ActivityIndicator color="#FFFFFF" size="small" />
            ) : (
              <Text style={styles.publishButtonText}>🚀 Publish to ONDC</Text>
            )}
          </TouchableOpacity>
        </View>
      </View>
    </ScrollView>
  );
};

/**
 * Styles
 * Optimized for low-end Android devices with large touch targets
 */
const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F5',
  },

  // Hero Image Section
  heroSection: {
    width: SCREEN_WIDTH,
    height: SCREEN_WIDTH, // Square aspect ratio
    backgroundColor: '#E0E0E0',
  },
  heroImage: {
    width: '100%',
    height: '100%',
  },

  // Content Card
  contentCard: {
    backgroundColor: '#FFFFFF',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    marginTop: -24, // Overlap with hero image
    paddingHorizontal: 20,
    paddingTop: 24,
    paddingBottom: 32,
    // Soft shadow for depth
    shadowColor: '#000',
    shadowOffset: { width: 0, height: -2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 4,
  },

  // Product Name
  productName: {
    fontSize: 24,
    fontWeight: '700',
    color: '#1A1A1A',
    marginBottom: 12,
    lineHeight: 32,
  },

  // Category Badge
  categoryBadge: {
    alignSelf: 'flex-start',
    backgroundColor: '#E3F2FD',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    marginBottom: 16,
  },
  categoryText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#1976D2',
  },

  // Price Section
  priceSection: {
    flexDirection: 'row',
    alignItems: 'baseline',
    marginBottom: 20,
    paddingVertical: 16,
    borderTopWidth: 1,
    borderBottomWidth: 1,
    borderColor: '#E0E0E0',
  },
  priceLabel: {
    fontSize: 16,
    fontWeight: '500',
    color: '#757575',
    marginRight: 12,
  },
  priceValue: {
    fontSize: 28,
    fontWeight: '700',
    color: '#2E7D32',
  },

  // Description Section
  descriptionSection: {
    marginBottom: 20,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#424242',
    marginBottom: 8,
  },
  descriptionText: {
    fontSize: 16,
    lineHeight: 24,
    color: '#616161',
  },

  // Attribute Pills
  pillsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginBottom: 20,
    gap: 10,
  },
  pill: {
    backgroundColor: '#F5F5F5',
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: '#E0E0E0',
    marginRight: 8,
    marginBottom: 8,
  },
  pillLabel: {
    fontSize: 12,
    fontWeight: '600',
    color: '#757575',
    marginBottom: 2,
  },
  pillValue: {
    fontSize: 14,
    fontWeight: '500',
    color: '#212121',
  },

  // CSI Section
  csiSection: {
    marginBottom: 24,
    padding: 16,
    backgroundColor: '#FFF9E6',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#FFE082',
  },
  csiCard: {
    marginTop: 12,
  },
  csiVernacular: {
    fontSize: 20,
    fontWeight: '700',
    color: '#F57C00',
    marginBottom: 4,
  },
  csiTransliteration: {
    fontSize: 14,
    fontStyle: 'italic',
    color: '#757575',
    marginBottom: 6,
  },
  csiContext: {
    fontSize: 15,
    lineHeight: 22,
    color: '#424242',
  },

  // Action Section
  actionSection: {
    marginTop: 24,
    gap: 12,
  },

  // Edit Button
  editButton: {
    backgroundColor: '#FFFFFF',
    borderWidth: 2,
    borderColor: '#2196F3',
    borderRadius: 12,
    paddingVertical: 16,
    alignItems: 'center',
    justifyContent: 'center',
    // Large touch target
    minHeight: 56,
  },
  editButtonText: {
    fontSize: 18,
    fontWeight: '600',
    color: '#2196F3',
  },

  // Publish Button
  publishButton: {
    backgroundColor: '#4CAF50',
    borderRadius: 12,
    paddingVertical: 18,
    alignItems: 'center',
    justifyContent: 'center',
    // Large touch target
    minHeight: 56,
    // Prominent shadow
    shadowColor: '#4CAF50',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 6,
  },
  publishButtonDisabled: {
    backgroundColor: '#A5D6A7',
    shadowOpacity: 0.1,
  },
  publishButtonText: {
    fontSize: 20,
    fontWeight: '700',
    color: '#FFFFFF',
    letterSpacing: 0.5,
  },
});

export default CatalogReviewCard;
