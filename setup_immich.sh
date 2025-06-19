#!/bin/bash
# Immich Upload Setup Script

echo "🚀 Immich Upload Setup"
echo "====================="

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found. Please install Node.js first:"
    echo "   Visit: https://nodejs.org/"
    echo "   Or use Homebrew: brew install node"
    exit 1
fi

echo "✅ Node.js found: $(node --version)"

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "❌ npm not found. Please install npm."
    exit 1
fi

echo "✅ npm found: $(npm --version)"

# Install Immich CLI
echo "📦 Installing Immich CLI..."
npm install -g @immich/cli

if [ $? -eq 0 ]; then
    echo "✅ Immich CLI installed successfully!"
    echo ""
    echo "📋 Next steps:"
    echo "1. Make sure your Immich server is running"
    echo "2. Get your API key from Immich web interface (User Settings → API Keys)"
    echo "3. Run: python upload_to_immich.py --setup"
    echo "4. Or run directly: python upload_to_immich.py . --server-url YOUR_URL --api-key YOUR_KEY"
else
    echo "❌ Failed to install Immich CLI"
    exit 1
fi
