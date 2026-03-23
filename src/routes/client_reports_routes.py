from flask import Response, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.models.user import User
from src.reports.client.client_stats_provider import get_client_stats
from src.reports.client.client_pdf_report import build_client_pdf
from src.reports.client.client_csv_report import build_client_csv
from src.reports.client.client_xlsx_report import build_client_xlsx
from src.reports.client.executive_pdf_report import build_executive_pdf


def require_client_user(user_id: int) -> User | None:
    user = User.query.get(user_id)
    if not user:
        return None

    # No debe ser staff
    if user.global_role is not None:
        return None

    # Debe tener cliente asociado
    if not user.client_id:
        return None

    if not user.is_active:
        return None

    return user


def register_client_report_routes(app):

    # ===============================
    # CLIENT — STATS
    # ===============================
    @app.route("/api/v1/reports/client/stats", methods=["GET"])
    @jwt_required()
    def client_stats():
        user = require_client_user(int(get_jwt_identity()))
        if not user:
            return jsonify({"error": "Acceso denegado"}), 403

        stats = get_client_stats(user.client_id)

        return jsonify(stats), 200


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
                "attachment; filename=findings.csv"
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
                "attachment; filename=findings.xlsx"
            }
        )

    # ===============================
    # CLIENT — RESUMEN EJECUTIVO PDF
    # ===============================
    @app.route("/api/client/reports/executive/pdf", methods=["GET"])
    @jwt_required()
    def client_executive_pdf():
        user = require_client_user(int(get_jwt_identity()))
        if not user:
            return jsonify({"error": "Acceso denegado"}), 403

        account_id_raw = request.args.get("account_id")
        aws_account_id = int(account_id_raw) if account_id_raw else None

        pdf_data = build_executive_pdf(user.client_id, aws_account_id)

        return Response(
            pdf_data,
            mimetype="application/pdf",
            headers={
                "Content-Disposition":
                "attachment; filename=resumen-ejecutivo-finops.pdf"
            }
        )
