#!/bin/bash

# KeepThisClip - One-Command Deployment Script
# This script installs Docker (if needed) and deploys the web downloader

set -e

echo "🎬 KeepThisClip - Deployment Script"
echo "=================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "📦 Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
    usermod -aG docker $USER
    echo "✅ Docker installed"
else
    echo "✅ Docker already installed"
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "📦 Installing Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    echo "✅ Docker Compose installed"
else
    echo "✅ Docker Compose already installed"
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚙️  Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env and set your DOMAIN before running this script again"
    echo "   nano .env"
    exit 1
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p DOWNLOADS youtube_api/downloads

# Build and start services
echo "🚀 Building and starting services..."
docker-compose build
docker-compose up -d

echo ""
echo "✅ Deployment complete!"
echo "🌐 Your KeepThisClip is now running"
echo "📋 Access it at: https://$(grep DOMAIN .env | cut -d '=' -f2)"
echo "🔐 Admin panel: https://$(grep DOMAIN .env | cut -d '=' -f2)/admin"
echo ""
echo "📊 View logs: docker-compose logs -f"
echo "🛑 Stop services: docker-compose down"
