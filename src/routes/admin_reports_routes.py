from flask import Response, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.reports.admin.admin_stats_provider import get_admin_stats
from src.reports.admin.admin_pdf_report import build_admin_pdf
from src.reports.admin.admin_csv_report import build_admin_csv
from src.auth_system import require_admin


def register_admin_report_routes(app):
    # ===============================
    # Endpoint PDF
    # ===============================
    @app.route("/api/v1/reports/admin/pdf", methods=["GET"])
    @jwt_required()
    def admin_pdf_report():
        try:
            admin_id = int(get_jwt_identity())
            print("🧪 ADMIN PDF | admin_id =", admin_id)

            stats = get_admin_stats()
            print("🧪 ADMIN PDF | stats =", stats)

            pdf_data = build_admin_pdf(stats)
            print("🧪 ADMIN PDF | pdf type =", type(pdf_data))
            print("🧪 ADMIN PDF | pdf size =", len(pdf_data))

            return Response(
                pdf_data,
                mimetype="application/pdf",
                headers={
                    "Content-Disposition": "attachment; filename=admin_report.pdf"
                }
            )

        except Exception as e:
            print("❌ ADMIN PDF ERROR:", str(e))
            import traceback
            traceback.print_exc()

            return jsonify({
                "error": "Error generando PDF admin",
                "detail": str(e)
            }), 500
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
