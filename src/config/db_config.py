# =====================================================
#   DATABASE CONFIG — init + sanity check (crítico en prod)
# =====================================================
import os

from src.models.database import init_db, db


def configure_database(app) -> None:
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("SQLALCHEMY_DATABASE_URI")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    if not app.config["SQLALCHEMY_DATABASE_URI"]:
        raise RuntimeError("❌ SQLALCHEMY_DATABASE_URI no definida")

    init_db(app)

    with app.app_context():
        engine_url = str(db.engine.url)
        safe_engine_url = db.engine.url.render_as_string(hide_password=True)
        print(f"🔌 Connected DB: {safe_engine_url}")

        require_prod_check = os.getenv("REQUIRE_PROD_DB_CHECK", "true").lower() == "true"

        if require_prod_check and "finops_prod" not in engine_url:
            raise RuntimeError(f"❌ API conectada a BD incorrecta: {safe_engine_url}")
