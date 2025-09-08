#!/bin/bash

# Deploy secrets to Fly.io from .env.local
# Usage: bash deploy-secrets.sh

set -e

echo "🚀 Deploying secrets to Fly.io from .env.local..."
echo ""

# Check if .env.local exists
if [ ! -f ".env.local" ]; then
    echo "❌ Error: .env.local file not found!"
    echo "Make sure you're running this from the /api directory"
    exit 1
fi

echo "📤 Uploading secrets to Fly.io..."
echo ""

# Transform and import:
# 1. Remove comments and empty lines
# 2. Skip CORS settings (handled in code)
# 3. Set production flags
# 4. Remove quotes from values
# Note: DATABASE_URL protocol is handled by the app's clean_database_url function
grep -v '^#\|^$\|ALLOWED_' .env.local | \
    sed 's/ENVIRONMENT=development/ENVIRONMENT=production/' | \
    sed 's/PRODUCTION=false/PRODUCTION=true/' | \
    sed 's/"//g' | \
    flyctl secrets import

echo ""
echo "✅ Secrets deployed successfully!"
echo "❌ WAIT! Make sure you manually use the Clerk production keys"
echo "  for CLERK_JWKS_URL, CLERK_SECRET_KEY, and CLERK_PUBLISHABLE_KEY"
echo ""
echo "You can verify with: flyctl secrets list"
echo "To deploy your app, run: flyctl deploy"