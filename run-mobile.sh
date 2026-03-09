#!/bin/bash

# Helper script to run the mobile app from root directory

echo "🚀 Starting Mobile App..."
echo ""

# Check if we're in the root directory
if [ ! -d "mobile" ]; then
    echo "❌ Error: mobile directory not found"
    echo "Please run this script from the project root directory"
    exit 1
fi

# Navigate to mobile directory
cd mobile

echo "📦 Checking dependencies..."
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

echo ""
echo "✅ Ready to run!"
echo ""
echo "Choose an option:"
echo "1. Start Metro bundler only"
echo "2. Run Android app (requires Metro in another terminal)"
echo "3. Start Metro AND run Android (opens 2 terminals)"
echo ""
read -p "Enter choice (1-3): " choice

case $choice in
    1)
        echo "Starting Metro bundler..."
        npm start
        ;;
    2)
        echo "Running Android app..."
        npm run android
        ;;
    3)
        echo "Starting Metro bundler in background..."
        npm start &
        METRO_PID=$!
        echo "Metro PID: $METRO_PID"
        sleep 5
        echo "Running Android app..."
        npm run android
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac
