#!/bin/bash

# Quick Start Script for Crawler Microservice
# This script sets up and runs the crawler service

set -e

echo "🕷️  Crawler Microservice - Quick Start"
echo "======================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.11+"
    exit 1
fi

echo "✅ Python found: $(python3 --version)"
echo ""

# Check if we're in the right directory
if [ ! -f "requirements.txt" ]; then
    echo "❌ Error: requirements.txt not found"
    echo "Please run this script from the crowler-service directory"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt > /dev/null 2>&1
echo "✅ Dependencies installed"

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "⚙️  Creating .env file from example..."
    cp .env.example .env
    echo "✅ .env file created"
else
    echo "✅ .env file already exists"
fi

echo ""
echo "======================================"
echo "🚀 Starting Crawler Microservice..."
echo "======================================"
echo ""
echo "Service will be available at:"
echo "  📍 http://localhost:8001"
echo "  📚 Docs: http://localhost:8001/docs"
echo "  📖 ReDoc: http://localhost:8001/redoc"
echo ""
echo "Press Ctrl+C to stop the service"
echo ""

# Run the application
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
