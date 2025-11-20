from src.finops_auditor import FinOpsAuditor
from src.pdf_reporter import PDFReporter

def main():
    print("🚀 Iniciando Auditoría FinOps Latam...")
    
    # Ejecutar auditoría
    auditor = FinOpsAuditor()
    results = auditor.run_comprehensive_audit()
    
    # Generar reporte PDF
    reporter = PDFReporter()
    pdf_file = reporter.generate_finops_report(results, "Empresa Cliente")
    
    print(f"✅ Auditoría completada. Reporte generado: {pdf_file}")
    print(f"💰 Ahorros potenciales identificados: ${results['executive_summary']['total_potential_savings']:,.2f} USD")

if __name__ == "__main__":
    main()