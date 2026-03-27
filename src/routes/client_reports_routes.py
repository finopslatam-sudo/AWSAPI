from flask import Response, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.models.user import User
from src.reports.client.client_stats_provider import get_client_stats
from src.reports.client.client_pdf_report import build_client_pdf
from src.reports.client.client_csv_report import build_client_csv
from src.reports.client.client_xlsx_report import build_client_xlsx
from src.reports.client.executive_pdf_report import build_executive_pdf
from src.reports.client.cost_pdf_report import build_cost_pdf
from src.reports.client.cost_xlsx_report import build_cost_xlsx
from src.reports.client.risk import build_risk_pdf
from src.reports.client.risk_xlsx_report import build_risk_xlsx
from src.reports.client.inventory_stats_provider import get_inventory_stats
from src.reports.client.inventory_csv_report import build_inventory_csv
from src.reports.client.inventory_xlsx_report import build_inventory_xlsx


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

    # ===============================
    # REPORTE DE COSTOS — PDF
    # ===============================
    @app.route("/api/client/reports/costs/pdf", methods=["GET"])
    @jwt_required()
    def client_costs_pdf():
        user = require_client_user(int(get_jwt_identity()))
        if not user:
            return jsonify({"error": "Acceso denegado"}), 403

        account_id_raw = request.args.get("account_id")
        aws_account_id = int(account_id_raw) if account_id_raw else None

        pdf_data = build_cost_pdf(user.client_id, aws_account_id)

        return Response(
            pdf_data,
            mimetype="application/pdf",
            headers={
                "Content-Disposition":
                "attachment; filename=reporte-costos-finops.pdf"
            }
        )

    # ===============================
    # REPORTE DE COSTOS — XLSX
    # ===============================
    @app.route("/api/client/reports/costs/xlsx", methods=["GET"])
    @jwt_required()
    def client_costs_xlsx():
        user = require_client_user(int(get_jwt_identity()))
        if not user:
            return jsonify({"error": "Acceso denegado"}), 403

        account_id_raw = request.args.get("account_id")
        aws_account_id = int(account_id_raw) if account_id_raw else None

        xlsx_data = build_cost_xlsx(user.client_id, aws_account_id)

        return Response(
            xlsx_data,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition":
                "attachment; filename=reporte-costos-finops.xlsx"
            }
        )

    # ===============================
    # REPORTE DE RIESGO — PDF
    # ===============================
    @app.route("/api/client/reports/risk/pdf", methods=["GET"])
    @jwt_required()
    def client_risk_pdf():
        user = require_client_user(int(get_jwt_identity()))
        if not user:
            return jsonify({"error": "Acceso denegado"}), 403

        account_id_raw = request.args.get("account_id")
        aws_account_id = int(account_id_raw) if account_id_raw else None

        pdf_data = build_risk_pdf(user.client_id, aws_account_id)

        return Response(
            pdf_data,
            mimetype="application/pdf",
            headers={
                "Content-Disposition":
                "attachment; filename=reporte-riesgo-compliance-finops.pdf"
            }
        )

    # ===============================
    # REPORTE DE RIESGO — XLSX
    # ===============================
    @app.route("/api/client/reports/risk/xlsx", methods=["GET"])
    @jwt_required()
    def client_risk_xlsx():
        user = require_client_user(int(get_jwt_identity()))
        if not user:
            return jsonify({"error": "Acceso denegado"}), 403

        account_id_raw = request.args.get("account_id")
        aws_account_id = int(account_id_raw) if account_id_raw else None

        xlsx_data = build_risk_xlsx(user.client_id, aws_account_id)

        return Response(
            xlsx_data,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition":
                "attachment; filename=reporte-riesgo-compliance-finops.xlsx"
            }
        )

    # ===============================
    # INVENTARIO DE RECURSOS — CSV
    # ===============================
    @app.route("/api/client/reports/inventory/csv", methods=["GET"])
    @jwt_required()
    def client_inventory_csv():
        user = require_client_user(int(get_jwt_identity()))
        if not user:
            return jsonify({"error": "Acceso denegado"}), 403

        account_id_raw = request.args.get("account_id")
        aws_account_id = int(account_id_raw) if account_id_raw else None

        stats    = get_inventory_stats(user.client_id, aws_account_id)
        csv_data = build_inventory_csv(stats)

        return Response(
            csv_data,
            mimetype="text/csv",
            headers={
                "Content-Disposition":
                "attachment; filename=inventario-recursos-aws.csv"
            }
        )

    # ===============================
    # INVENTARIO DE RECURSOS — XLSX
    # ===============================
    @app.route("/api/client/reports/inventory/xlsx", methods=["GET"])
    @jwt_required()
    def client_inventory_xlsx():
        user = require_client_user(int(get_jwt_identity()))
        if not user:
            return jsonify({"error": "Acceso denegado"}), 403

        account_id_raw = request.args.get("account_id")
        aws_account_id = int(account_id_raw) if account_id_raw else None

        stats     = get_inventory_stats(user.client_id, aws_account_id)
        xlsx_data = build_inventory_xlsx(stats)

        return Response(
            xlsx_data,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition":
                "attachment; filename=inventario-recursos-aws.xlsx"
            }
        )
