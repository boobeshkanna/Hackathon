# CatalogReviewCard Component Showcase

## Visual Design Reference

### Component Layout

```
┌─────────────────────────────────────────────────────┐
│                                                       │
│                   HERO IMAGE                         │
│              (Full-width, Square)                    │
│                                                       │
├─────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────┐  │
│  │                                                 │  │
│  │  Handwoven Banarasi Silk Saree                 │  │ ← 24pt Bold
│  │                                                 │  │
│  │  ┌──────────────────────────────┐              │  │
│  │  │ Fashion:Ethnic Wear:Sarees   │              │  │ ← Category Badge
│  │  └──────────────────────────────┘              │  │
│  │                                                 │  │
│  │  ┌────────────────────────────────────────┐    │  │
│  │  │ Price    INR 15000.00                  │    │  │ ← 28pt Bold
│  │  └────────────────────────────────────────┘    │  │
│  │                                                 │  │
│  │  📝 Description                                 │  │
│  │  Exquisite handwoven Banarasi silk saree...    │  │
│  │                                                 │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐       │  │
│  │  │🧵 Material│ │🎨 Color  │ │✋ Craft  │       │  │ ← Attribute Pills
│  │  │Pure Silk  │ │Red,Gold  │ │Handwoven│       │  │
│  │  └──────────┘ └──────────┘ └──────────┘       │  │
│  │                                                 │  │
│  │  ┌──────────┐ ┌──────────┐                     │  │
│  │  │📍 Origin │ │🏅 GI Tag │                     │  │
│  │  │Varanasi  │ │GI Tagged │                     │  │
│  │  └──────────┘ └──────────┘                     │  │
│  │                                                 │  │
│  │  🌟 Cultural Story                             │  │
│  │  ┌─────────────────────────────────────────┐   │  │
│  │  │ बनारसी (Banarasi)                        │   │  │ ← CSI Card
│  │  │ Traditional silk weaving style from      │   │  │
│  │  │ Varanasi. Worn by Indian royalty...      │   │  │
│  │  └─────────────────────────────────────────┘   │  │
│  │                                                 │  │
│  │  ┌─────────────────────────────────────────┐   │  │
│  │  │         ✏️ Edit                          │   │  │ ← Edit Button
│  │  └─────────────────────────────────────────┘   │  │
│  │                                                 │  │
│  │  ┌─────────────────────────────────────────┐   │  │
│  │  │      🚀 Publish to ONDC                  │   │  │ ← Publish Button
│  │  └─────────────────────────────────────────┘   │  │
│  │                                                 │  │
│  └─────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

## Color Palette

### Primary Colors
```
Publish Button:    #4CAF50  ████  (Green)
Edit Button:       #2196F3  ████  (Blue)
Price Text:        #2E7D32  ████  (Dark Green)
CSI Highlight:     #F57C00  ████  (Orange)
```

### Neutral Colors
```
Background:        #F5F5F5  ████  (Light Gray)
Card Background:   #FFFFFF  ████  (White)
Text Primary:      #1A1A1A  ████  (Near Black)
Text Secondary:    #757575  ████  (Gray)
Border:            #E0E0E0  ████  (Light Gray)
```

### Semantic Colors
```
Success:           #4CAF50  ████  (Green)
Error:             #D32F2F  ████  (Red)
Warning:           #F57C00  ████  (Orange)
Info:              #2196F3  ████  (Blue)
```

## Typography Scale

```
Product Name:      24pt / 700 (Bold)
Price Value:       28pt / 700 (Bold)
Section Title:     18pt / 600 (Semibold)
Body Text:         16pt / 400 (Regular)
Price Label:       16pt / 500 (Medium)
Pill Value:        14pt / 500 (Medium)
Pill Label:        12pt / 600 (Semibold)
Category Badge:    12pt / 600 (Semibold)
```

## Spacing System

```
Card Padding:      20px
Section Margin:    20px
Hero Overlap:      -24px (negative margin)
Pill Gap:          10px
Button Height:     56dp (minimum touch target)
Border Radius:     12px (buttons, card)
Pill Radius:       20px
Badge Radius:      16px
```

## Component States

### Default State
```
┌─────────────────────────────────────┐
│      🚀 Publish to ONDC             │  ← Green background
└─────────────────────────────────────┘
```

### Loading State
```
┌─────────────────────────────────────┐
│           ⟳ Loading...              │  ← Light green, spinner
└─────────────────────────────────────┘
```

### Disabled State
```
┌─────────────────────────────────────┐
│      🚀 Publish to ONDC             │  ← Faded green
└─────────────────────────────────────┘
```

## Responsive Behavior

### Small Screen (320px width)
- Hero image: 320x320px
- 2 pills per row
- Reduced padding: 16px

### Medium Screen (375px width)
- Hero image: 375x375px
- 2-3 pills per row
- Standard padding: 20px

### Large Screen (414px+ width)
- Hero image: 414x414px
- 3-4 pills per row
- Standard padding: 20px

## Interaction Patterns

### Tap Publish Button
```
1. User taps "Publish to ONDC"
2. Confirmation dialog appears:
   ┌─────────────────────────────────┐
   │  🚀 Publish to ONDC?            │
   │                                 │
   │  Your product will be visible   │
   │  to buyers across India.        │
   │  Continue?                      │
   │                                 │
   │  [Cancel]  [Publish]            │
   └─────────────────────────────────┘
3. User taps "Publish"
4. Button shows loading spinner
5. API call to backend
6. Success dialog appears:
   ┌─────────────────────────────────┐
   │  ✅ Published Successfully!     │
   │                                 │
   │  Your product is now live on    │
   │  ONDC network.                  │
   │                                 │
   │  [OK]                           │
   └─────────────────────────────────┘
7. Navigate back to Queue
```

### Tap Edit Button
```
1. User taps "Edit"
2. Navigate to Edit screen (future)
```

### Scroll Behavior
```
- Smooth scrolling
- Hero image scrolls with content
- No sticky headers
- Scroll indicator hidden
```

## Accessibility Features

### Touch Targets
```
Minimum size: 56dp x 56dp
Spacing: 8dp between interactive elements
```

### Color Contrast
```
Text on White:     4.5:1 (WCAG AA)
Button Text:       7:1 (WCAG AAA)
Price Text:        4.5:1 (WCAG AA)
```

### Screen Reader
```
Hero Image:        "Product image"
Publish Button:    "Publish to ONDC network"
Edit Button:       "Edit product details"
Price:             "Price: 15000 rupees"
```

## Animation Timing

```
Button Press:      150ms ease-out
Dialog Fade:       200ms ease-in-out
Loading Spinner:   1000ms linear infinite
```

## Shadow Specifications

### Card Shadow
```
shadowColor:       #000
shadowOffset:      { width: 0, height: -2 }
shadowOpacity:     0.1
shadowRadius:      8
elevation:         4 (Android)
```

### Button Shadow
```
shadowColor:       #4CAF50
shadowOffset:      { width: 0, height: 4 }
shadowOpacity:     0.3
shadowRadius:      8
elevation:         6 (Android)
```

## Example Variations

### Minimal Product (No CSI)
```
┌─────────────────────────────────────┐
│         HERO IMAGE                  │
├─────────────────────────────────────┤
│  Product Name                       │
│  [Category Badge]                   │
│  Price: INR 500.00                  │
│  Description text...                │
│  [Material] [Color]                 │
│  [🚀 Publish to ONDC]               │
└─────────────────────────────────────┘
```

### Rich Product (With CSI)
```
┌─────────────────────────────────────┐
│         HERO IMAGE                  │
├─────────────────────────────────────┤
│  Product Name                       │
│  [Category Badge]                   │
│  Price: INR 15000.00                │
│  Description text...                │
│  [Material] [Color] [Craft]         │
│  [Origin] [GI Tag] [Artisan]        │
│  🌟 Cultural Story                  │
│  [CSI Card 1]                       │
│  [CSI Card 2]                       │
│  [✏️ Edit]                          │
│  [🚀 Publish to ONDC]               │
└─────────────────────────────────────┘
```

## Error States

### Network Error
```
┌─────────────────────────────────────┐
│  ❌ Error                           │
│                                     │
│  Network error. Please check your   │
│  connection and try again.          │
│                                     │
│  [OK]                               │
└─────────────────────────────────────┘
```

### Validation Error
```
┌─────────────────────────────────────┐
│  ❌ Publish Failed                  │
│                                     │
│  Invalid product data. Please       │
│  contact support.                   │
│                                     │
│  [OK]                               │
└─────────────────────────────────────┘
```

## Performance Targets

```
Initial Render:    < 100ms
Re-render:         < 16ms (60fps)
Image Load:        < 500ms
API Call:          < 1000ms
Memory Usage:      < 5MB
```

## Browser/Device Support

```
✅ Android 8.0+
✅ iOS 12.0+
✅ React Native 0.72+
✅ Screen sizes: 320px - 768px width
✅ RAM: 512MB minimum
```

## Implementation Notes

### Image Optimization
- Use WebP format when possible
- Lazy load images
- Cache images locally
- Compress to 80% quality

### Performance Tips
- Memoize expensive computations
- Use FlatList for long lists (future)
- Avoid inline functions in render
- Use React.memo for pure components

### Testing Checklist
- [ ] Test on low-end device (512MB RAM)
- [ ] Test with slow network (3G)
- [ ] Test with no network (offline)
- [ ] Test with long product names
- [ ] Test with many attributes (10+)
- [ ] Test with multiple CSIs (5+)
- [ ] Test with missing images
- [ ] Test publish success flow
- [ ] Test publish failure flow
- [ ] Test edit button (if implemented)

## Code Example

```typescript
import { CatalogReviewCard } from './components/CatalogReviewCard';

<CatalogReviewCard
  catalogItem={myCatalogItem}
  onPublish={async (item) => {
    const response = await publishToONDC(item);
    return response;
  }}
  onEdit={(item) => {
    navigation.navigate('Edit', { item });
  }}
  onPublishSuccess={(id) => {
    console.log('Published:', id);
    navigation.goBack();
  }}
/>
```

## Resources

- Figma Design: [Link to design file]
- Style Guide: [Link to style guide]
- Component Library: React Native built-in components only
- Icons: Unicode emoji (no external library)

---

**Last Updated:** 2024
**Version:** 1.0.0
**Maintainer:** Story-to-Catalog Team
