/**
 * CatalogReviewExample
 * 
 * Example usage of CatalogReviewCard component with mock data.
 * This demonstrates how the component works with ONDC Beckn Protocol data.
 * 
 * Use this for testing and development.
 */

import React from 'react';
import { View, StyleSheet } from 'react-native';
import { CatalogReviewCard } from '../components/CatalogReviewCard';
import type { CatalogItem, PublishResponse } from '../types/catalog';

/**
 * Mock catalog data - Banarasi Silk Saree example
 */
const mockCatalogItem: CatalogItem = {
  itemId: 'item_a1b2c3d4e5f6g7h8',
  
  descriptor: {
    name: 'Handwoven Banarasi Silk Saree with Zari Work',
    shortDesc: 'Exquisite handwoven Banarasi silk saree featuring intricate gold zari work and traditional motifs. Perfect for weddings and special occasions.',
    longDesc: 'This stunning Banarasi silk saree is a masterpiece of traditional Indian craftsmanship. Handwoven on a pit loom by skilled artisans in Varanasi, it features intricate gold zari work with traditional Mughal-inspired floral motifs. The rich red color symbolizes prosperity and celebration in Indian culture. Each saree takes approximately 15-20 days to complete, representing generations of weaving expertise passed down through artisan families.',
    images: [
      'https://example.com/saree-front.jpg',
      'https://example.com/saree-detail.jpg',
      'https://example.com/saree-border.jpg',
    ],
  },
  
  price: {
    currency: 'INR',
    value: '15000.00',
    expectedValue: '18000.00',
  },
  
  categoryId: 'Fashion:Ethnic Wear:Sarees',
  
  tags: {
    material: 'Pure Silk,Gold Zari',
    color: 'Red,Gold',
    craftTechnique: 'Handwoven on Pit Loom',
    region: 'Varanasi, Uttar Pradesh',
    geographicalIndication: 'GI Tagged - Banarasi Silk',
    artisanLineage: '5th Generation Weaver',
    length: '6.5 meters',
    width: '1.2 meters',
    weight: '800 grams',
  },
  
  csis: [
    {
      vernacularTerm: 'बनारसी',
      transliteration: 'Banarasi',
      englishContext: 'Refers to the traditional silk weaving style originating from Varanasi (Banaras)',
      culturalSignificance: 'Banarasi sarees have been worn by Indian royalty for centuries and are considered auspicious for weddings',
    },
    {
      vernacularTerm: 'जरी',
      transliteration: 'Zari',
      englishContext: 'Fine gold or silver thread used in traditional Indian textile embroidery',
      culturalSignificance: 'Zari work represents luxury and is traditionally used in bridal wear and ceremonial garments',
    },
  ],
  
  trackingId: 'track_xyz123',
  tenantId: 'tenant_artisan_collective',
  artisanId: 'artisan_ramesh_kumar',
  createdAt: Date.now(),
  updatedAt: Date.now(),
};

/**
 * Example Component
 */
export const CatalogReviewExample: React.FC = () => {
  /**
   * Mock publish handler
   */
  const handlePublish = async (item: CatalogItem): Promise<PublishResponse> => {
    // Simulate API call delay
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    // Simulate successful publish
    return {
      success: true,
      ondcCatalogId: 'ondc_catalog_' + Date.now(),
      message: 'Successfully published to ONDC network',
    };
  };

  /**
   * Mock edit handler
   */
  const handleEdit = (item: CatalogItem) => {
    console.log('Edit item:', item.itemId);
  };

  /**
   * Mock success handler
   */
  const handlePublishSuccess = (ondcCatalogId: string) => {
    console.log('Published successfully! ONDC Catalog ID:', ondcCatalogId);
  };

  return (
    <View style={styles.container}>
      <CatalogReviewCard
        catalogItem={mockCatalogItem}
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
});

export default CatalogReviewExample;
