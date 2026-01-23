from flask import Response, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.models.user import User
from src.reports.admin.admin_stats_provider import get_admin_stats
from src.reports.admin.admin_pdf_report import build_admin_pdf
from src.reports.admin.admin_csv_report import build_admin_csv
from src.reports.admin.admin_xlsx_report import build_admin_xlsx


def register_admin_report_routes(app):

    def _require_admin():
        user = User.query.get(int(get_jwt_identity()))
        if not user or user.global_role not in ("root", "admin"):
            return None
        return user

    # ===============================
    # PDF
    # ===============================
    @app.route("/api/v1/reports/admin/pdf", methods=["GET"])
    @jwt_required()
    def admin_pdf_report():
        actor = _require_admin()
        if not actor:
            return jsonify({"error": "Acceso denegado"}), 403

        stats = get_admin_stats()
        pdf_data = build_admin_pdf(stats)

        return Response(
            pdf_data,
            mimetype="application/pdf",
            headers={
                "Content-Disposition":
                "attachment; filename=finopslatam_admin_report.pdf"
            }
        )

    # ===============================
    # CSV
    # ===============================
    @app.route("/api/v1/reports/admin/csv", methods=["GET"])
    @jwt_required()
    def admin_csv_report():
        actor = _require_admin()
        if not actor:
            return jsonify({"error": "Acceso denegado"}), 403

        stats = get_admin_stats()
        csv_data = build_admin_csv(stats)

        return Response(
            csv_data,
            mimetype="text/csv",
            headers={
                "Content-Disposition":
                "attachment; filename=finopslatam_admin_report.csv"
            }
        )

    # ===============================
    # XLSX
    # ===============================
    @app.route("/api/v1/reports/admin/xlsx", methods=["GET"])
    @jwt_required()
    def admin_xlsx_report():
        actor = _require_admin()
        if not actor:
            return jsonify({"error": "Acceso denegado"}), 403

        stats = get_admin_stats()
        xlsx_data = build_admin_xlsx(stats)

        return Response(
            xlsx_data,
            mimetype=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            headers={
                "Content-Disposition":
                "attachment; filename=finopslatam_admin_report.xlsx"
            }
        )
