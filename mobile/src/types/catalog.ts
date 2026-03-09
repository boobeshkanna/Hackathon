/**
 * Catalog Schema - ONDC Beckn Protocol Compliant
 * 
 * This schema represents the structured catalog data that will be:
 * 1. Saved to DynamoDB
 * 2. Pushed to the ONDC Beckn Gateway
 * 3. Displayed to artisans for review before publishing
 * 
 * Designed for low-bandwidth, offline-first mobile environments
 */

/**
 * Cultural Specific Item (CSI)
 * Preserves cultural storytelling and vernacular context
 */
export interface CSI {
  /** Original term in artisan's language (e.g., "बनारसी") */
  vernacularTerm: string;
  
  /** Roman script representation (e.g., "Banarasi") */
  transliteration: string;
  
  /** Contextual explanation in English */
  englishContext: string;
  
  /** Cultural significance explanation */
  culturalSignificance: string;
}

/**
 * Price Information
 * ONDC Beckn Protocol compliant
 */
export interface Price {
  /** Currency code (ISO 4217) - default "INR" */
  currency: string;
  
  /** Price value as string for precision (e.g., "1500.00") */
  value: string;
  
  /** Optional: Expected/suggested retail price */
  expectedValue?: string;
}

/**
 * Item Descriptor
 * ONDC Beckn Protocol descriptor object
 */
export interface ItemDescriptor {
  /** Product name - SEO optimized, max 100 chars */
  name: string;
  
  /** Short description - max 500 chars */
  shortDesc: string;
  
  /** Detailed description with cultural context */
  longDesc: string;
  
  /** Array of image URLs (S3 or CDN) */
  images: string[];
  
  /** Optional: Audio description URL */
  audio?: string;
  
  /** Optional: Video URL */
  video?: string;
}

/**
 * Rich Attributes (Tags)
 * Key-value pairs for cultural storytelling and product attributes
 */
export interface CatalogTags {
  /** Material(s) used (e.g., "silk,cotton") */
  material?: string;
  
  /** Color(s) (e.g., "red,gold") */
  color?: string;
  
  /** Craft technique (e.g., "Handwoven on pit loom") */
  craftTechnique?: string;
  
  /** Region of origin (e.g., "Varanasi, Uttar Pradesh") */
  region?: string;
  
  /** Geographical Indication tag (e.g., "GI Tagged") */
  geographicalIndication?: string;
  
  /** Artisan lineage/tradition (e.g., "5th generation weaver") */
  artisanLineage?: string;
  
  /** Dimensions */
  length?: string;
  width?: string;
  height?: string;
  
  /** Weight */
  weight?: string;
  
  /** CSI terms - dynamically added */
  [key: string]: string | undefined;
}

/**
 * Main Catalog Item
 * ONDC Beckn Protocol compliant catalog item
 * 
 * This is the primary data structure for the "Review & Publish" screen
 */
export interface CatalogItem {
  /** Unique item ID (SKU) - deterministic hash-based */
  itemId: string;
  
  /** Item descriptor with name, descriptions, and media */
  descriptor: ItemDescriptor;
  
  /** Price information */
  price: Price;
  
  /** ONDC category taxonomy ID (e.g., "Fashion:Ethnic Wear:Sarees") */
  categoryId: string;
  
  /** Rich attributes for cultural storytelling */
  tags: CatalogTags;
  
  /** Optional: Cultural Specific Items array */
  csis?: CSI[];
  
  /** Optional: Fulfillment ID */
  fulfillmentId?: string;
  
  /** Optional: Location ID */
  locationId?: string;
  
  /** Metadata: Tracking ID from backend */
  trackingId?: string;
  
  /** Metadata: Tenant ID */
  tenantId?: string;
  
  /** Metadata: Artisan ID */
  artisanId?: string;
  
  /** Metadata: Creation timestamp */
  createdAt?: number;
  
  /** Metadata: Last updated timestamp */
  updatedAt?: number;
}

/**
 * Catalog Review State
 * Local state for the review screen
 */
export interface CatalogReviewState {
  /** The catalog item being reviewed */
  item: CatalogItem;
  
  /** Loading state for publish action */
  isPublishing: boolean;
  
  /** Error message if publish fails */
  publishError?: string;
  
  /** Success flag */
  publishSuccess: boolean;
  
  /** ONDC catalog ID after successful publish */
  ondcCatalogId?: string;
}

/**
 * Publish Response
 * Response from backend after publishing to ONDC
 */
export interface PublishResponse {
  success: boolean;
  ondcCatalogId?: string;
  message: string;
  errors?: string[];
}
