from flask import Flask, jsonify, render_template, request
from src.finops_auditor import FinOpsAuditor
from src.service_discovery import AWSServiceDiscovery
import json
from datetime import datetime

app = Flask(__name__)

# ==================== RUTAS DEL FRONTEND ====================

@app.route('/')
def index():
    """Página principal con dashboard integrado"""
    try:
        discovery = AWSServiceDiscovery()
        stats = discovery.get_filtered_service_statistics()
        return render_template('index.html', 
                             services=stats['services_in_use'],
                             title="FinOps Latam - Auditoría AWS")
    except Exception as e:
        # Fallback a la versión HTML simple si hay error
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>FinOps Latam - Auditoría AWS</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                .card { border: 1px solid #ddd; padding: 20px; margin: 10px; border-radius: 8px; }
                .success { background-color: #d4edda; border-color: #c3e6cb; }
                .warning { background-color: #fff3cd; border-color: #ffeaa7; }
                .danger { background-color: #f8d7da; border-color: #f5c6cb; }
                .endpoint { background-color: #e9ecef; padding: 10px; margin: 5px 0; }
            </style>
        </head>
        <body>
            <h1>🚀 FinOps Latam - API de Auditoría AWS</h1>
            
            <div class="card warning">
                <h2>⚠️ Frontend Temporal</h2>
                <p>Los templates no están disponibles. Usando versión básica.</p>
                <p>Error: {}</p>
            </div>
            
            <div class="card success">
                <h2>¡API Funcionando Correctamente! ✅</h2>
                <p>Endpoints disponibles:</p>
                
                <div class="endpoint">
                    <strong>GET</strong> <a href="/dashboard">/dashboard</a> - Dashboard visual
                </div>
                
                <div class="endpoint">
                    <strong>GET</strong> <a href="/api/health">/api/health</a> - Estado del servicio
                </div>
                
                <div class="endpoint">
                    <strong>GET</strong> <a href="/api/services/active">/api/services/active</a> - Servicios en uso
                </div>
                
                <div class="endpoint">
                    <strong>GET</strong> <a href="/api/audit/quick">/api/audit/quick</a> - Auditoría rápida
                </div>
                
                <div class="endpoint">
                    <strong>GET</strong> <a href="/api/audit/full">/api/audit/full</a> - Auditoría completa
                </div>
            </div>
        </body>
        </html>
        """.format(str(e))

@app.route('/dashboard')
def dashboard():
    """Dashboard detallado de servicios AWS"""
    try:
        discovery = AWSServiceDiscovery()
        stats = discovery.get_filtered_service_statistics()
        return render_template('dashboard.html', 
                             services=stats['services_in_use'],
                             title="Dashboard - FinOps Latam")
    except Exception as e:
        return f"Error cargando dashboard: {str(e)}", 500

@app.route('/costs')
def costs():
    """Análisis de costos y recomendaciones"""
    try:
        auditor = FinOpsAuditor()
        audit_results = auditor.run_comprehensive_audit()
        return render_template('costs.html', 
                             audit=audit_results,
                             title="Análisis de Costos - FinOps Latam")
    except Exception as e:
        return f"Error cargando análisis de costos: {str(e)}", 500

@app.route('/api-docs')
def api_docs():
    """Documentación de la API"""
    try:
        return render_template('api_docs.html', 
                             title="API Docs - FinOps Latam")
    except Exception as e:
        return f"Error cargando documentación: {str(e)}", 500

# ==================== RUTAS DE LA API ====================

@app.route('/api/health')
def health_check():
    """Verifica el estado del servicio y conexión AWS"""
    try:
        # Verificar conexión AWS básica
        import boto3
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        
        return jsonify({
            'status': 'healthy',
            'service': 'FinOps Latam API',
            'aws_identity': identity['Arn'],
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'service': 'FinOps Latam API', 
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/services/active')
def get_active_services():
    """Endpoint para obtener solo servicios EN USO"""
    try:
        discovery = AWSServiceDiscovery()
        stats = discovery.get_filtered_service_statistics()
        
        return jsonify({
            'status': 'success',
            'data': stats['services_in_use'],
            'timestamp': stats['discovery_metadata']['timestamp']
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/discovery')
def get_full_discovery():
    """Endpoint completo de descubrimiento"""
    try:
        discovery = AWSServiceDiscovery()
        stats = discovery.get_filtered_service_statistics()
        
        return jsonify({
            'status': 'success',
            'data': stats,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'error', 
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/audit/quick')
def quick_audit():
    """Auditoría rápida - solo descubrimiento de servicios"""
    try:
        discovery = AWSServiceDiscovery()
        stats = discovery.get_filtered_service_statistics()
        
        return jsonify({
            'status': 'success',
            'audit_type': 'quick',
            'results': {
                'service_discovery': stats,
                'summary': {
                    'total_services': stats['services_in_use']['total_services'],
                    'total_resources': stats['services_in_use']['total_resources'],
                    'timestamp': datetime.now().isoformat()
                }
            }
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/audit/full')
def full_audit():
    """Auditoría completa FinOps"""
    try:
        auditor = FinOpsAuditor()
        results = auditor.run_comprehensive_audit()
        
        return jsonify({
            'status': 'success', 
            'audit_type': 'full',
            'results': results,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/generate-pdf')
def generate_pdf():
    """Genera reporte PDF de la auditoría"""
    try:
        from src.pdf_reporter import PDFReporter
        from src.finops_auditor import FinOpsAuditor
        
        auditor = FinOpsAuditor()
        results = auditor.run_comprehensive_audit()
        
        reporter = PDFReporter()
        pdf_filename = reporter.generate_finops_report(results, "Cliente Prueba")
        
        return jsonify({
            'status': 'success',
            'pdf_file': pdf_filename,
            'download_url': f'/download/{pdf_filename}',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# ==================== RUTA PARA DESCARGAR PDF ====================

@app.route('/download/<filename>')
def download_pdf(filename):
    """Descargar archivo PDF generado"""
    try:
        from flask import send_file
        return send_file(filename, as_attachment=True)
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': f'Archivo no encontrado: {filename}',
            'timestamp': datetime.now().isoformat()
        }), 404

if __name__ == '__main__':
    print("🚀 Iniciando FinOps Latam API...")
    print("📊 Endpoints disponibles:")
    print("   http://localhost:5001/              - Dashboard principal")
    print("   http://localhost:5001/dashboard     - Dashboard visual")
    print("   http://localhost:5001/costs         - Análisis de costos")
    print("   http://localhost:5001/api-docs      - Documentación API")
    print("   http://localhost:5001/api/health    - Estado del servicio")
    print("   http://localhost:5001/api/services/active - Servicios en uso")
    print("   http://localhost:5001/api/audit/quick     - Auditoría rápida")
    print("   http://localhost:5001/api/audit/full      - Auditoría completa")
    print("   http://localhost:5001/api/generate-pdf    - Generar reporte PDF")
    
    app.run(debug=True, host='0.0.0.0', port=5001)