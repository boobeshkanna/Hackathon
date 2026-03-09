#!/usr/bin/env python3
"""
Create a simple test image for demo purposes
"""
from PIL import Image, ImageDraw, ImageFont
import os

# Create test_images directory
os.makedirs('test_images', exist_ok=True)

# Create a simple product image
img = Image.new('RGB', (400, 400), color='#FF6B6B')
draw = ImageDraw.Draw(img)

# Draw a simple pattern
for i in range(0, 400, 40):
    draw.line([(i, 0), (i, 400)], fill='#FFD93D', width=2)
    draw.line([(0, i), (400, i)], fill='#FFD93D', width=2)

# Add text
try:
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
except:
    font = ImageFont.load_default()

draw.text((200, 180), "Test", fill='white', anchor='mm', font=font)
draw.text((200, 220), "Product", fill='white', anchor='mm', font=font)

# Save
img.save('test_images/sample_product.jpg', 'JPEG', quality=95)
print("✅ Created test_images/sample_product.jpg")

# Create another variant
img2 = Image.new('RGB', (400, 400), color='#6C5CE7')
draw2 = ImageDraw.Draw(img2)

# Draw circles
for i in range(50, 400, 100):
    for j in range(50, 400, 100):
        draw2.ellipse([i-30, j-30, i+30, j+30], fill='#A29BFE', outline='white', width=3)

draw2.text((200, 200), "Artisan", fill='white', anchor='mm', font=font)

img2.save('test_images/sample_artisan.jpg', 'JPEG', quality=95)
print("✅ Created test_images/sample_artisan.jpg")

print("\n📸 Test images created! Use them with:")
print("  curl -X POST 'http://localhost:8000/api/analyze-image' \\")
print("    -F 'image=@test_images/sample_product.jpg' \\")
print("    -F 'language=hi'")
