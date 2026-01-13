from flask import Response, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from reports.admin.admin_stats_provider import get_admin_stats
from reports.admin.admin_pdf_report import build_admin_pdf
from reports.admin.admin_csv_report import build_admin_csv
from auth_system import require_admin
from app import app  # ⚠️ ajusta si tu Flask app vive en otro archivo

# ===============================
# Endpoint PDF
# ===============================

@app.route("/api/v1/reports/admin/pdf", methods=["GET"])
@jwt_required()
def admin_pdf_report():
    admin_id = int(get_jwt_identity())

    if not require_admin(admin_id):
        return jsonify({"error": "Acceso denegado"}), 403

    stats = get_admin_stats()
    pdf_data = build_admin_pdf(stats)

    return Response(
        pdf_data,
        mimetype="application/pdf",
        headers={
            "Content-Disposition": "attachment; filename=finopslatam_admin_report.pdf"
        }
    )

# ===============================
# Endpoint CSV
# ===============================
@app.route("/api/v1/reports/admin/csv", methods=["GET"])
@jwt_required()
def admin_csv_report():
    admin_id = int(get_jwt_identity())

    if not require_admin(admin_id):
        return jsonify({"error": "Acceso denegado"}), 403

    stats = get_admin_stats()
    csv_data = build_admin_csv(stats)

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=finopslatam_admin_report.csv"
        }
    )
