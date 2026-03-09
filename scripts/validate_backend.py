"""
Backend validation script
Detecta errores antes de deploy
"""

import sys
import os
import traceback

# ---------------------------------------------------
# Add project root to PYTHONPATH
# ---------------------------------------------------

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

print(f"🔧 Project root added: {PROJECT_ROOT}")

print("🔍 Validating backend imports...")

try:

    from app import app

    print("✅ app import OK")

except Exception:

    print("❌ ERROR importing app")
    traceback.print_exc()
    sys.exit(1)

# ---------------------------------------------------

try:

    print("🔍 Checking routes...")

    routes = []

    for rule in app.url_map.iter_rules():
        routes.append(str(rule))

    print(f"✅ {len(routes)} routes loaded")

except Exception:

    print("❌ ERROR loading routes")
    traceback.print_exc()
    sys.exit(1)

# ---------------------------------------------------

try:

    print("🔍 Testing app context...")

    with app.app_context():
        pass

    print("✅ App context OK")

except Exception:

    print("❌ ERROR initializing app context")
    traceback.print_exc()
    sys.exit(1)

print("🚀 Backend validation PASSED")