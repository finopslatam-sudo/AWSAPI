from flask import Flask, jsonify, render_template, request, redirect, url_for, send_file
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity, create_access_token
from src.finops_auditor import FinOpsAuditor
from src.service_discovery import AWSServiceDiscovery
from src.auth_system import init_auth_system, create_auth_routes, Client, ClientSubscription
from datetime import datetime
from flask_cors import CORS
import json

# =====================================================
#   CONFIGURACIÓN BASE DEL SERVICIO
# =====================================================

app = Flask(__name__)

# CORS para permitir conexión desde el frontend
CORS(
    app,
    resources={
        r"/api/*": {
            "origins": [
                "http://localhost:3000",
                "https://finopslatam.vercel.app",
                "https://finopslatam.com",
                "https://www.finopslatam.com"
            ]
        }
    },
    supports_credentials=True
)
# Inicializar sistema de autenticación
init_auth_system(app)
create_auth_routes(app)

# ==================== DETECCIÓN INTELIGENTE ====================

def usuario_autenticado():
    """Verificar si el usuario está logueado vía JWT"""
    try:
        get_jwt_identity()
        return True
    except:
        return False


# =====================================================
#   RUTAS FRONTEND
# =====================================================

@app.route('/')
def pagina_principal_inteligente():
    """Si usuario está logueado → dashboard. Si no → landing."""
    if usuario_autenticado():
        return redirect('/dashboard')
    return render_template('landing_public.html', title="FinOps Latam - Optimización AWS")


@app.route('/public')
def landing_publica():
    return render_template('landing_public.html', title="FinOps Latam - Optimización AWS")


@app.route('/plataforma')
def info_plataforma():
    return render_template('plataforma.html', title="Nuestra Plataforma - FinOps Latam")


# =====================================================
#   DASHBOARD PROTEGIDO
# =====================================================

@app.route('/dashboard')
@jwt_required()
def dashboard():
    client_id = get_jwt_identity()
    client = Client.query.get(client_id)

    try:
        discovery = AWSServiceDiscovery()
        stats = discovery.get_filtered_service_statistics()

        return render_template(
            'dashboard.html',
            client=client,
            services=stats['services_in_use'],
            title=f"Dashboard - {client.company_name}"
        )

    except Exception:
        return render_template(
            'dashboard.html',
            client=client,
            services={'total_services': 0, 'total_resources': 0, 'breakdown': {}},
            title=f"Dashboard - {client.company_name}"
        )


# =====================================================
#   ANÁLISIS DE COSTOS
# =====================================================

@app.route('/costs')
def costs():
    try:
        auditor = FinOpsAuditor()
        audit_results = auditor.run_comprehensive_audit()
        return render_template(
            'costs.html',
            audit=audit_results,
            title="Análisis de Costos - FinOps Latam"
        )
    except Exception as e:
        return f"Error cargando análisis de costos: {str(e)}", 500


@app.route('/api-docs')
def api_docs():
    try:
        return render_template('api_docs.html', title="API Docs - FinOps Latam")
    except Exception as e:
        return f"Error cargando documentación: {str(e)}", 500


# =====================================================
#   ENDPOINTS API
# =====================================================

@app.route('/api/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'service': 'FinOps Latam API',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    }), 200

@app.route('/api/services/active')
def get_active_services():
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


@app.route('/api/protected/services')
@jwt_required()
def protected_services():
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


# =====================================================
#   DESCARGA PDF
# =====================================================

@app.route('/download/<filename>')
def download_pdf(filename):
    try:
        return send_file(filename, as_attachment=True)
    except:
        return jsonify({
            'status': 'error',
            'error': f'Archivo no encontrado: {filename}',
            'timestamp': datetime.now().isoformat()
        }), 404


# =====================================================
#   RUN SERVER
# =====================================================

if __name__ == '__main__':
    print("🚀 Iniciando FinOps Latam Platform...")
    print("📍 URL Principal: http://localhost:5001")
    app.run(debug=True, host='0.0.0.0', port=5001)
