from flask import Flask, render_template_string
from src.auth_system import init_auth_system, create_auth_routes
import os

def create_test_auth_app():
    """Crea una app de prueba separada para auth"""
    app = Flask(__name__)
    
    # Inicializar sistema de auth
    init_auth_system(app)
    create_auth_routes(app)
    
    # HTML completo con estilos EMBEBIDOS (no dependen de archivos externos)
    @app.route('/')
    def home():
        html_content = '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>🔐 FinOps Latam - Sistema de Auth</title>
            <meta charset="utf-8">
            <style>
                body { 
                    font-family: 'Arial', sans-serif; 
                    margin: 40px; 
                    line-height: 1.6;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                }
                .container { 
                    max-width: 900px; 
                    margin: 0 auto;
                    background: white;
                    padding: 30px;
                    border-radius: 15px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                }
                h1 { 
                    color: #333; 
                    text-align: center;
                    margin-bottom: 30px;
                }
                .card { 
                    border: 1px solid #ddd; 
                    padding: 25px; 
                    margin: 20px 0; 
                    border-radius: 10px;
                    background: #f8f9fa;
                }
                .success { 
                    background-color: #d4edda; 
                    border-color: #c3e6cb; 
                }
                .info { 
                    background-color: #d1ecf1; 
                    border-color: #bee5eb; 
                }
                .endpoint { 
                    background-color: #fff; 
                    padding: 20px; 
                    margin: 15px 0; 
                    border-left: 5px solid #007bff;
                    border-radius: 8px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                }
                code { 
                    background: #2d3748; 
                    color: #e2e8f0;
                    padding: 12px; 
                    border-radius: 6px;
                    display: block;
                    margin: 10px 0;
                    font-family: 'Courier New', monospace;
                    overflow-x: auto;
                }
                .test-buttons { 
                    margin: 30px 0; 
                    text-align: center;
                }
                .test-buttons button { 
                    padding: 12px 25px; 
                    margin: 8px; 
                    border: none; 
                    border-radius: 6px; 
                    cursor: pointer;
                    font-size: 16px;
                    font-weight: bold;
                    transition: all 0.3s ease;
                }
                .btn-primary { 
                    background: #007bff; 
                    color: white; 
                }
                .btn-primary:hover { 
                    background: #0056b3;
                    transform: translateY(-2px);
                }
                .btn-success { 
                    background: #28a745; 
                    color: white; 
                }
                .btn-success:hover { 
                    background: #1e7e34;
                    transform: translateY(-2px);
                }
                .btn-warning { 
                    background: #ffc107; 
                    color: #212529; 
                }
                .btn-warning:hover { 
                    background: #e0a800;
                    transform: translateY(-2px);
                }
                #result {
                    margin-top: 20px; 
                    padding: 20px; 
                    border-radius: 8px; 
                    display: none;
                    font-family: 'Courier New', monospace;
                    white-space: pre-wrap;
                    word-wrap: break-word;
                }
                .status-indicator {
                    display: inline-block;
                    width: 12px;
                    height: 12px;
                    border-radius: 50%;
                    margin-right: 8px;
                }
                .status-active {
                    background: #28a745;
                }
                .status-inactive {
                    background: #dc3545;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🔐 FinOps Latam - Sistema de Autenticación</h1>
                
                <div class="card info">
                    <h2>🚀 Sistema de Auth - Testing</h2>
                    <p><span class="status-indicator status-active"></span> Esta es una app <strong>separada</strong> para probar autenticación.</p>
                    <p><span class="status-indicator status-active"></span> <strong>No afecta tu aplicación principal en puerto 5001</strong></p>
                    <p><span class="status-indicator status-active"></span> Base de datos: <strong>SQLite (finops_auth.db)</strong></p>
                </div>

                <div class="card success">
                    <h3>✅ Endpoints Disponibles</h3>
                    
                    <div class="endpoint">
                        <h4>📝 POST /api/auth/register</h4>
                        <p><strong>Registro de nuevo cliente</strong></p>
                        <code>{
  "company_name": "Mi Empresa",
  "email": "empresa@ejemplo.com", 
  "password": "mi_password",
  "contact_name": "Juan Pérez",
  "phone": "+56912345678"
}</code>
                    </div>
                    
                    <div class="endpoint">
                        <h4>🔑 POST /api/auth/login</h4>
                        <p><strong>Inicio de sesión</strong></p>
                        <code>{
  "email": "empresa@ejemplo.com",
  "password": "mi_password" 
}</code>
                    </div>
                    
                    <div class="endpoint">
                        <h4>👤 GET /api/auth/profile</h4>
                        <p><strong>Perfil del cliente (requiere JWT token)</strong></p>
                        <p>Header: <code style="display: inline; padding: 2px 6px;">Authorization: Bearer &lt;token&gt;</code></p>
                    </div>
                </div>

                <div class="test-buttons">
                    <h3>🧪 Probar Endpoints</h3>
                    <button class="btn-primary" onclick="testRegister()">📝 Probar Registro</button>
                    <button class="btn-success" onclick="testLogin()">🔑 Probar Login</button>
                    <button class="btn-warning" onclick="testProfile()">👤 Probar Perfil</button>
                    <button onclick="clearResults()">🗑️ Limpiar Resultados</button>
                </div>

                <div id="result"></div>

                <div class="card">
                    <h3>📊 Estado del Sistema</h3>
                    <div id="system-status">
                        <p>🔍 Buscando base de datos...</p>
                    </div>
                </div>
            </div>

            <script>
                function showResult(message, isError = false) {
                    const resultDiv = document.getElementById('result');
                    resultDiv.style.display = 'block';
                    resultDiv.style.background = isError ? '#f8d7da' : '#d4edda';
                    resultDiv.style.border = isError ? '1px solid #f5c6cb' : '1px solid #c3e6cb';
                    resultDiv.style.color = isError ? '#721c24' : '#155724';
                    resultDiv.innerHTML = '<strong>' + (isError ? '❌ Error:' : '✅ Resultado:') + '</strong><br>' + message;
                }

                function clearResults() {
                    document.getElementById('result').style.display = 'none';
                    document.getElementById('result').innerHTML = '';
                }

                async function testRegister() {
                    try {
                        const testEmail = 'test' + Date.now() + '@ejemplo.com';
                        const response = await fetch('/api/auth/register', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                company_name: 'Empresa de Prueba ' + Date.now(),
                                email: testEmail,
                                password: 'password123',
                                contact_name: 'Test User',
                                phone: '+56987654321'
                            })
                        });
                        const data = await response.json();
                        if (response.ok) {
                            showResult('✅ REGISTRO EXITOSO\\n\\nToken: ' + data.access_token + '\\n\\nCliente: ' + JSON.stringify(data.client, null, 2));
                            localStorage.setItem('auth_token', data.access_token);
                            localStorage.setItem('test_email', testEmail);
                        } else {
                            showResult('❌ ERROR: ' + data.error, true);
                        }
                    } catch (error) {
                        showResult('❌ Error de conexión: ' + error.message, true);
                    }
                }

                async function testLogin() {
                    const testEmail = localStorage.getItem('test_email') || 'test@ejemplo.com';
                    try {
                        const response = await fetch('/api/auth/login', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                email: testEmail,
                                password: 'password123'
                            })
                        });
                        const data = await response.json();
                        if (response.ok) {
                            showResult('✅ LOGIN EXITOSO\\n\\nToken: ' + data.access_token + '\\n\\nCliente: ' + JSON.stringify(data.client, null, 2));
                            localStorage.setItem('auth_token', data.access_token);
                        } else {
                            showResult('❌ ERROR: ' + data.error + '\\n\\nPrueba primero el registro.', true);
                        }
                    } catch (error) {
                        showResult('❌ Error de conexión: ' + error.message, true);
                    }
                }

                async function testProfile() {
                    const token = localStorage.getItem('auth_token');
                    if (!token) {
                        showResult('❌ Error: Primero haz registro o login para obtener un token', true);
                        return;
                    }

                    try {
                        const response = await fetch('/api/auth/profile', {
                            method: 'GET',
                            headers: { 
                                'Content-Type': 'application/json',
                                'Authorization': 'Bearer ' + token
                            }
                        });
                        const data = await response.json();
                        if (response.ok) {
                            showResult('✅ PERFIL OBTENIDO\\n\\n' + JSON.stringify(data, null, 2));
                        } else {
                            showResult('❌ ERROR: ' + data.error, true);
                        }
                    } catch (error) {
                        showResult('❌ Error de conexión: ' + error.message, true);
                    }
                }

                // Verificar si la base de datos existe
                async function checkDatabase() {
                    try {
                        const response = await fetch('/api/auth/profile', {
                            method: 'GET',
                            headers: { 'Content-Type': 'application/json' }
                        });
                        document.getElementById('system-status').innerHTML = 
                            '<p><span class="status-indicator status-active"></span> Base de datos: <strong>Conectada</strong></p>' +
                            '<p><span class="status-indicator status-active"></span> Sistema de auth: <strong>Operativo</strong></p>';
                    } catch (error) {
                        document.getElementById('system-status').innerHTML = 
                            '<p><span class="status-indicator status-inactive"></span> Base de datos: <strong>Creando...</strong></p>';
                    }
                }

                // Ejecutar cuando la página cargue
                document.addEventListener('DOMContentLoaded', function() {
                    checkDatabase();
                });
            </script>
        </body>
        </html>
        '''
        return render_template_string(html_content)
    
    return app

if __name__ == '__main__':
    auth_app = create_test_auth_app()
    print("🚀 Iniciando Sistema de Auth en puerto 5002...")
    print("📍 URL: http://localhost:5002")
    print("📧 Endpoints de autenticación:")
    print("   POST http://localhost:5002/api/auth/register")
    print("   POST http://localhost:5002/api/auth/login") 
    print("   GET  http://localhost:5002/api/auth/profile (requiere JWT)")
    print("\n💡 Tu app principal sigue en: http://localhost:5001")
    print("🗄️  Base de datos SQLite se creará automáticamente al primer uso")
    auth_app.run(debug=True, port=5002)