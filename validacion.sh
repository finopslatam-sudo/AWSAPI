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
# GUARDAR COMMIT ACTUAL (para rollback)
# =====================================================

CURRENT_COMMIT=$(git rev-parse HEAD)

echo ""
echo "📌 Current running commit:"
echo "$CURRENT_COMMIT"

# =====================================================
# TRAER NUEVO CÓDIGO
# =====================================================

echo ""
echo "📥 Fetching latest code..."

git fetch origin

echo ""
echo "🔄 Resetting working tree to origin/main..."

git reset --hard origin/main

echo ""
echo "📦 Deploying commit:"
git log -1 --pretty=format:"%h - %s (%ci)"
echo ""

# =====================================================
# VALIDAR BACKEND
# =====================================================

echo ""
echo "🔍 Running backend validation..."

if ! python scripts/validate_backend.py; then

    echo ""
    echo "❌ Backend validation failed"
    echo "↩️ Rolling back..."

    git reset --hard $CURRENT_COMMIT

    exit 1
fi

echo ""
echo "✅ Backend validation passed"

# =====================================================
# RESTART API
# =====================================================

echo ""
echo "♻️ Restarting FinOps API..."

sudo systemctl restart finops-api

sleep 5

# =====================================================
# VERIFICAR SERVICIO
# =====================================================

if ! systemctl is-active --quiet finops-api; then

    echo ""
    echo "❌ API failed to start"
    echo "↩️ Rolling back..."

    git reset --hard $CURRENT_COMMIT

    sudo systemctl restart finops-api

    exit 1
fi

# =====================================================
# HEALTHCHECK
# =====================================================

echo ""
echo "🧪 Running API healthcheck..."

HEALTH=$(curl -s http://127.0.0.1:5001/api/health || true)

if [[ "$HEALTH" != *"healthy"* ]]; then

    echo ""
    echo "❌ Healthcheck failed"
    echo "↩️ Rolling back..."

    git reset --hard $CURRENT_COMMIT

    sudo systemctl restart finops-api

    exit 1
fi

echo "$HEALTH"

echo ""
echo ""
echo "========================================="
echo "✅ DEPLOY COMPLETED SUCCESSFULLY"
echo "========================================="
echo ""