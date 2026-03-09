"""
FinOpsLatam Backend Validator (v2)
Valida backend antes de deploy
"""

import sys
import os
import traceback
from sqlalchemy import text

# ---------------------------------------------------
# ADD PROJECT ROOT
# ---------------------------------------------------

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

print(f"\n🔧 Project root: {PROJECT_ROOT}\n")

# ---------------------------------------------------
# 1. IMPORT APP
# ---------------------------------------------------

print("🔍 Checking Flask app import...")

try:

    from app import app

    print("✅ Flask app loaded")

except Exception:

    print("\n❌ ERROR importing Flask app\n")
    traceback.print_exc()
    sys.exit(1)

# ---------------------------------------------------
# 2. CHECK BLUEPRINTS
# ---------------------------------------------------

print("\n🔍 Checking blueprints...")

try:

    blueprints = list(app.blueprints.keys())

    if not blueprints:
        raise Exception("No blueprints registered")

    print(f"✅ {len(blueprints)} blueprints loaded")

    for bp in blueprints:
        print(f"   • {bp}")

except Exception:

    print("\n❌ ERROR loading blueprints\n")
    traceback.print_exc()
    sys.exit(1)

# ---------------------------------------------------
# 3. CHECK ROUTES
# ---------------------------------------------------

print("\n🔍 Checking routes...")

try:

    routes = []

    for rule in app.url_map.iter_rules():
        routes.append(str(rule))

    if not routes:
        raise Exception("No routes registered")

    print(f"✅ {len(routes)} routes registered")

except Exception:

    print("\n❌ ERROR loading routes\n")
    traceback.print_exc()
    sys.exit(1)

# ---------------------------------------------------
# 4. CHECK APP CONTEXT
# ---------------------------------------------------

print("\n🔍 Checking Flask app context...")

try:

    with app.app_context():
        pass

    print("✅ App context initialized")

except Exception:

    print("\n❌ ERROR initializing Flask context\n")
    traceback.print_exc()
    sys.exit(1)

# ---------------------------------------------------
# 5. CHECK DATABASE CONNECTION
# ---------------------------------------------------

print("\n🔍 Checking database connection...")

try:

    from src.models.database import db
    from sqlalchemy import text

    with app.app_context():

        db.session.execute(text("SELECT 1"))

    print("✅ Database connection OK")

except Exception:

    print("\n❌ ERROR connecting database\n")
    traceback.print_exc()
    sys.exit(1)

# ---------------------------------------------------
# SUCCESS
# ---------------------------------------------------

print("\n🚀 BACKEND VALIDATION PASSED\n")