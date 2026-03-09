#!/bin/bash

set -e

echo "📥 Pull latest code..."
git pull origin main

echo "🐍 Activating venv..."
source venv/bin/activate

echo "🔍 Validating backend..."

python scripts/validate_backend.py

echo "♻️ Restarting API..."

sudo systemctl restart finops-api

echo "✅ Deploy successful"