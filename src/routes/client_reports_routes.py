from flask import Response
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.reports.client.client_stats_provider import get_client_stats
from reports.client.client_pdf_report import build_client_pdf
from reports.client.client_csv_report import build_client_csv
from app import app

# ===============================
# Endpoint PDF
# ===============================

@app.route("/api/v1/reports/client/pdf", methods=["GET"])
@jwt_required()
def client_pdf_report():
    client_id = int(get_jwt_identity())

    stats = get_client_stats(client_id)
    pdf_data = build_client_pdf(stats)

    return Response(
        pdf_data,
        mimetype="application/pdf",
        headers={
            "Content-Disposition": "attachment; filename=finopslatam_client_report.pdf"
        }
    )

# ===============================
# Endpoint CSV
# ===============================
@app.route("/api/v1/reports/client/csv", methods=["GET"])
@jwt_required()
def client_csv_report():
    client_id = int(get_jwt_identity())

    stats = get_client_stats(client_id)
    csv_data = build_client_csv(stats)

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=finopslatam_client_report.csv"
        }
    )

