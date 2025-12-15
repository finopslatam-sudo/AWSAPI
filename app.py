from flask import Flask, jsonify, render_template, request, redirect, url_for, send_file
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity, create_access_token
from src.finops_auditor import FinOpsAuditor
from src.service_discovery import AWSServiceDiscovery
from src.auth_system import init_auth_system, create_auth_routes, Client, ClientSubscription
import json
from datetime import datetime

app = Flask(__name__)

# ==================== INICIALIZAR SISTEMA DE AUTH ====================
init_auth_system(app)
create_auth_routes(app)

# ==================== DETECCIÓN INTELIGENTE de usuarios ====================

def usuario_autenticado():
    """Verificar si el usuario está logueado"""
    try:
        get_jwt_identity()  # Esto lanzará error si no hay token válido
        return True
    except:
        return False

@app.route('/')
def pagina_principal_inteligente():
    """Página principal que detecta automáticamente qué mostrar"""
    if usuario_autenticado():
        # Usuario LOGUEADO → ir al dashboard
        return redirect('/dashboard')
    else:
        # Usuario NO logueado → mostrar landing page
        return render_template('landing_public.html', title="FinOps Latam - Optimización AWS")

# ==================== LANDING PÚBLICA ====================

@app.route('/public')
def landing_publica():
    """Landing page pública (acceso directo)"""
    return render_template('landing_public.html', title="FinOps Latam - Optimización AWS")

@app.route('/plataforma')
def info_plataforma():
    """Información sobre la plataforma"""
    return render_template('plataforma.html', title="Nuestra Plataforma - FinOps Latam")

# ==================== DASHBOARD PROTEGIDO ====================

@app.route('/dashboard')
@jwt_required()
def dashboard():
    """Dashboard principal SOLO para usuarios logueados"""
    client_id = get_jwt_identity()
    client = Client.query.get(client_id)
    
    try:
        discovery = AWSServiceDiscovery()
        stats = discovery.get_filtered_service_statistics()
        
        return render_template('dashboard.html', 
                             client=client,
                             services=stats['services_in_use'],
                             title=f"Dashboard - {client.company_name}")
    except Exception as e:
        # Fallback si hay error en AWS
        return render_template('dashboard.html',
                             client=client,
                             services={'total_services': 0, 'total_resources': 0, 'breakdown': {}},
                             title=f"Dashboard - {client.company_name}")

# ==================== TUS RUTAS EXISTENTES (SE MANTIENEN) ====================

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

# ==================== RUTAS DE LA API (SE MANTIENEN) ====================

@app.route('/api/health')
def health_check():
    """Verifica el estado del servicio y conexión AWS"""
    try:
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

# ==================== RUTAS PROTEGIDAS CON AUTH ====================

@app.route('/api/protected/services')
@jwt_required()
def protected_services():
    """Versión protegida de tus servicios - requiere login"""
    client_id = get_jwt_identity()
    
    try:
        discovery = AWSServiceDiscovery()
        stats = discovery.get_filtered_service_statistics()
        
        return jsonify({
            'status': 'success',
            'client_id': client_id,
            'data': stats['services_in_use'],
            'timestamp': stats['discovery_metadata']['timestamp']
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
        return send_file(filename, as_attachment=True)
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': f'Archivo no encontrado: {filename}',
            'timestamp': datetime.now().isoformat()
        }), 404

if __name__ == '__main__':
    print("🚀 Iniciando FinOps Latam Platform...")
    print("📍 URL Principal: http://localhost:5001")
    print("📊 Páginas Disponibles:")
    print("   /              - Landing (público) o Dashboard (logueado)")
    print("   /public        - Landing page pública")
    print("   /plataforma    - Información de la plataforma")
    print("   /dashboard     - Dashboard clientes (requiere login)")
    print("   /costs         - Análisis de costos")
    print("📧 Autenticación:")
    print("   /register      - Registro nuevos clientes")
    print("   /login         - Login clientes existentes")
    
    app.run(debug=True, host='0.0.0.0', port=5001)
