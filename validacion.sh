#!/bin/bash

# =====================================================
# Este script es invocado por el workflow de GitHub
# Actions (.github/workflows/ci.yml, job "deploy") vía
# SSH como el usuario "deploy". NO está pensado para
# ejecución manual ad-hoc — el único camino de deploy
# soportado es push a "main" en GitHub.
#
# IMPORTANTE: este script NUNCA debe hacer git fetch/reset
# sobre sí mismo. Un script bash que se automodifica
# mientras corre (porque "git reset --hard" reescribe este
# mismo archivo en medio de su propia ejecución) hace que
# bash salte o corrompa líneas de forma silenciosa e
# impredecible (bug real encontrado y corregido en la
# primera prueba de este pipeline). El fetch/reset/rollback
# vive en el workflow (ci.yml), que se envía completo por
# SSH en cada corrida y nunca lee este archivo del disco.
# =====================================================

set -e

echo ""
echo "========================================="
echo "🚀 FinOpsLatam Safe Deploy"
echo "========================================="
echo ""

cd /opt/apps/finopslatam/AWSAPI

echo "📂 Project directory:"
pwd

echo ""
echo "🐍 Activating Python virtual environment..."
source venv/bin/activate

echo ""
echo "📦 Installing dependencies..."
pip install -q -r requirements.txt

echo ""
echo "🔍 Running backend validation..."
python scripts/validate_backend.py

echo ""
echo "✅ Backend validation passed"

echo ""
echo "♻️ Restarting FinOps API..."
sudo systemctl restart finops-api

sleep 10

if ! systemctl is-active --quiet finops-api; then
    echo "❌ API failed to start"
    exit 1
fi

echo ""
echo "🧪 Running API healthcheck..."
HEALTH=$(curl -s -H "Host: api.finopslatam.com" http://127.0.0.1:5001/api/health || true)

if [[ "$HEALTH" != *"healthy"* ]]; then
    echo "❌ Healthcheck failed"
    exit 1
fi

echo "$HEALTH"

echo ""
echo ""
echo "========================================="
echo "✅ DEPLOY COMPLETED SUCCESSFULLY"
echo "========================================="
echo ""
