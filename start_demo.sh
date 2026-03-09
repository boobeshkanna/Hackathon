#!/bin/bash

# Quick Start Script for Demo Server

echo "=========================================="
echo "Vernacular Artisan Catalog - Demo Setup"
echo "=========================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  No .env file found. Creating from template..."
    cp .env.example .env
    echo "✅ Created .env file"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env and add at least one API key:"
    echo "   - OPENAI_API_KEY"
    echo "   - ANTHROPIC_API_KEY"
    echo "   - GROQ_API_KEY"
    echo ""
    read -p "Press Enter after adding your API key to .env..."
fi

# Check if virtual environment exists
if [ ! -d "backend/venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv backend/venv
    echo "✅ Virtual environment created"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source backend/venv/bin/activate

# Install dependencies
echo "📦 Installing dependencies..."
pip install -q -r requirements.txt

# Install AI provider SDKs
echo "🤖 Installing AI provider SDKs..."
pip install -q openai anthropic groq

echo ""
echo "✅ Setup complete!"
echo ""

# Run tests
echo "🧪 Running tests..."
python test_demo_api.py

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "🎉 All tests passed!"
    echo "=========================================="
    echo ""
    echo "Starting demo server..."
    echo ""
    echo "📍 Server will be available at:"
    echo "   - API: http://localhost:8000"
    echo "   - Docs: http://localhost:8000/docs"
    echo "   - Web UI: Open demo_web_ui.html in browser"
    echo ""
    echo "Press Ctrl+C to stop the server"
    echo ""
    
    # Start server
    python backend/lambda_functions/api_handlers/local_demo_server.py
else
    echo ""
    echo "❌ Tests failed. Please check:"
    echo "   1. API key is set in .env"
    echo "   2. Dependencies are installed"
    echo "   3. Internet connection is working"
    echo ""
    exit 1
fi
