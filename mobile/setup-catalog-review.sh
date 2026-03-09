#!/bin/bash

# Setup script for Catalog Review & Publish feature
# Run this after pulling the new code

set -e

echo "🚀 Setting up Catalog Review & Publish feature..."
echo ""

# Check if we're in the mobile directory
if [ ! -f "package.json" ]; then
    echo "❌ Error: Please run this script from the mobile/ directory"
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
npm install

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚙️  Creating .env file..."
    cat > .env << EOF
# API Configuration
API_BASE_URL=https://your-api-gateway.amazonaws.com/prod

# Optional: Override specific endpoints
# CATALOG_GET_ENDPOINT=/v1/catalog
# CATALOG_PUBLISH_ENDPOINT=/v1/catalog/publish
EOF
    echo "✅ Created .env file - Please update API_BASE_URL with your actual endpoint"
else
    echo "✅ .env file already exists"
fi

# Check TypeScript compilation
echo "🔍 Checking TypeScript compilation..."
npx tsc --noEmit

if [ $? -eq 0 ]; then
    echo "✅ TypeScript compilation successful"
else
    echo "⚠️  TypeScript compilation has errors - please fix them"
fi

# Create a test file to verify setup
echo "📝 Creating test file..."
cat > src/test-catalog-review.ts << 'EOF'
/**
 * Test file to verify Catalog Review setup
 * Run: npx ts-node src/test-catalog-review.ts
 */

import type { CatalogItem } from './types/catalog';

const testCatalogItem: CatalogItem = {
  itemId: 'test_item_123',
  descriptor: {
    name: 'Test Product',
    shortDesc: 'Test description',
    longDesc: 'Test long description',
    images: ['https://example.com/image.jpg'],
  },
  price: {
    currency: 'INR',
    value: '1000.00',
  },
  categoryId: 'Test:Category',
  tags: {
    material: 'Test Material',
    color: 'Test Color',
  },
};

console.log('✅ Catalog Review types are working correctly!');
console.log('Test item:', testCatalogItem.descriptor.name);
EOF

echo "✅ Created test file: src/test-catalog-review.ts"

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "1. Update .env file with your API endpoint"
echo "2. Run 'npm start' to start Metro bundler"
echo "3. Run 'npm run android' or 'npm run ios' to launch app"
echo "4. Test with example: import { CatalogReviewExample } from './examples/CatalogReviewExample'"
echo ""
echo "📚 Documentation:"
echo "- CATALOG_REVIEW_IMPLEMENTATION.md - Full technical docs"
echo "- INTEGRATION_GUIDE.md - Quick start guide"
echo "- COMPONENT_SHOWCASE.md - Visual design reference"
echo ""
echo "Happy coding! 🚀"
