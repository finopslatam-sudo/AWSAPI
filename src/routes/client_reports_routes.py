from flask import Response, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.models.user import User
from src.reports.client.client_stats_provider import get_client_stats
from src.reports.client.client_pdf_report import build_client_pdf
from src.reports.client.client_csv_report import build_client_csv
from src.reports.client.client_xlsx_report import build_client_xlsx


def require_client_user(user_id: int) -> User | None:
    user = User.query.get(user_id)
    if not user:
        return None
    if user.global_role != "client":
        return None
    if not user.client_id:
        return None
    return user


def register_client_report_routes(app):

    # ===============================
    # CLIENT — PDF
    # ===============================
    @app.route("/api/client/reports/pdf", methods=["GET"])
    @jwt_required()
    def client_pdf_report():
        user = require_client_user(int(get_jwt_identity()))
        if not user:
            return jsonify({"error": "Acceso denegado"}), 403

        stats = get_client_stats(user.client_id)
        pdf_data = build_client_pdf(stats)

        return Response(
            pdf_data,
            mimetype="application/pdf",
            headers={
                "Content-Disposition":
                "attachment; filename=finopslatam_client_report.pdf"
            }
        )

    # ===============================
    # CLIENT — CSV
    # ===============================
    @app.route("/api/client/reports/csv", methods=["GET"])
    @jwt_required()
    def client_csv_report():
        user = require_client_user(int(get_jwt_identity()))
        if not user:
            return jsonify({"error": "Acceso denegado"}), 403

        stats = get_client_stats(user.client_id)
        csv_data = build_client_csv(stats)

        return Response(
            csv_data,
            mimetype="text/csv",
            headers={
                "Content-Disposition":
                "attachment; filename=finopslatam_client_report.csv"
            }
        )

    # ===============================
    # CLIENT — XLSX
    # ===============================
    @app.route("/api/client/reports/xlsx", methods=["GET"])
    @jwt_required()
    def client_xlsx_report():
        user = require_client_user(int(get_jwt_identity()))
        if not user:
            return jsonify({"error": "Acceso denegado"}), 403

        stats = get_client_stats(user.client_id)
        xlsx_data = build_client_xlsx(stats)

        return Response(
            xlsx_data,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition":
                "attachment; filename=finopslatam_client_report.xlsx"
            }
        )
