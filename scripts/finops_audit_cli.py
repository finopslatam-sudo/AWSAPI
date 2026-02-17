"""
FINOPS AUDIT CLI TOOL
====================

⚠️ ESTE SCRIPT NO ES PARTE DEL BACKEND API ⚠️

Este archivo ejecuta una auditoría FinOps de forma
manual o programada (CLI / cron / job).

- NO levanta Flask
- NO registra rutas
- NO usa JWT
- NO debe importarse desde app.py

Uso recomendado:
    python scripts/finops_audit_cli.py

Este script está diseñado para:
- auditorías puntuales
- generación de reportes offline
- análisis técnico interno
"""

from AWSAPI.src.aws.finops_auditor import FinOpsAuditor
from src.reports.exporters.pdf_base import PDFBaseExporter

def main():
    print("🚀 Iniciando Auditoría FinOps (CLI)")

    auditor = FinOpsAuditor()
    results = auditor.run_comprehensive_audit()

    exporter = PDFBaseExporter()
    pdf_file = exporter.generate(results, "Empresa Cliente")

    print(f"✅ Auditoría completada")
    print(f"📄 Reporte generado: {pdf_file}")
    print(
        f"💰 Ahorros potenciales: "
        f"${results['executive_summary']['total_potential_savings']:,.2f} USD"
    )

if __name__ == "__main__":
    main()
