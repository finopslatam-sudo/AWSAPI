#!/bin/bash

set -e

echo ""
echo "========================================="
echo "🚀 FinOpsLatam Safe Deploy"
echo "========================================="
echo ""

# =====================================================
# IR AL PROYECTO
# =====================================================

cd /opt/finops-api/AWSAPI

echo "📂 Project directory:"
pwd

# =====================================================
# ACTIVAR VENV
# =====================================================

echo ""
echo "🐍 Activating Python virtual environment..."

source venv/bin/activate

# =====================================================
# TRAER CAMBIOS (SIN git pull)
# =====================================================

echo ""
echo "📥 Fetching latest code..."

git fetch origin

echo ""
echo "🔄 Resetting working tree to origin/main..."

git reset --hard origin/main

echo ""
echo "📊 Current commit deployed:"

git log -1 --oneline

# =====================================================
# VALIDAR BACKEND
# =====================================================

echo ""
echo "🔍 Running backend validation..."

python scripts/validate_backend.py

echo ""
echo "✅ Backend validation passed"

# =====================================================
# RESTART API
# =====================================================

echo ""
echo "♻️ Restarting FinOps API..."

sudo systemctl restart finops-api

sleep 2

echo ""
echo "📊 Service status:"

sudo systemctl status finops-api --no-pager

# =====================================================
# HEALTHCHECK
# =====================================================

echo ""
echo "🧪 Running API healthcheck..."

curl -s http://127.0.0.1:5001/api/health

echo ""
echo ""
echo "========================================="
echo "✅ DEPLOY COMPLETED SUCCESSFULLY"
echo "========================================="
echo ""
