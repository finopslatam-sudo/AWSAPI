let authToken = localStorage.getItem('auth_token');
let currentUser = null;

// Verificar estado de autenticación al cargar la página
document.addEventListener('DOMContentLoaded', function() {
    checkAuthStatus();
});

// Mostrar modal de login
function showLoginModal() {
    const modal = new bootstrap.Modal(document.getElementById('loginModal'));
    modal.show();
}

// Mostrar modal de registro
function showRegisterModal() {
    const modal = new bootstrap.Modal(document.getElementById('registerModal'));
    modal.show();
}

// Función de login
async function login() {
    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;
    const errorDiv = document.getElementById('loginError');

    try {
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                email: email,
                password: password
            })
        });

        const data = await response.json();

        if (response.ok) {
            // Login exitoso
            authToken = data.access_token;
            currentUser = data.client;
            
            localStorage.setItem('auth_token', authToken);
            localStorage.setItem('user_data', JSON.stringify(data.client));
            
            updateUI();
            
            // Cerrar modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('loginModal'));
            modal.hide();
            
            // Mostrar mensaje de éxito
            showAlert('✅ Login exitoso!', 'success');
            
        } else {
            // Error de login
            errorDiv.textContent = data.error || 'Error en el login';
            errorDiv.style.display = 'block';
        }
    } catch (error) {
        errorDiv.textContent = 'Error de conexión: ' + error.message;
        errorDiv.style.display = 'block';
    }
}

// Función de registro
async function register() {
    const company = document.getElementById('registerCompany').value;
    const email = document.getElementById('registerEmail').value;
    const contact = document.getElementById('registerContact').value;
    const password = document.getElementById('registerPassword').value;
    const errorDiv = document.getElementById('registerError');

    try {
        const response = await fetch('/api/auth/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                company_name: company,
                email: email,
                contact_name: contact,
                password: password
            })
        });

        const data = await response.json();

        if (response.ok) {
            // Registro exitoso
            authToken = data.access_token;
            currentUser = data.client;
            
            localStorage.setItem('auth_token', authToken);
            localStorage.setItem('user_data', JSON.stringify(data.client));
            
            updateUI();
            
            // Cerrar modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('registerModal'));
            modal.hide();
            
            // Mostrar mensaje de éxito
            showAlert('🎉 Cuenta creada exitosamente!', 'success');
            
        } else {
            // Error de registro
            errorDiv.textContent = data.error || 'Error en el registro';
            errorDiv.style.display = 'block';
        }
    } catch (error) {
        errorDiv.textContent = 'Error de conexión: ' + error.message;
        errorDiv.style.display = 'block';
    }
}

// Función de logout
function logout() {
    authToken = null;
    currentUser = null;
    
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user_data');
    
    updateUI();
    showAlert('👋 Sesión cerrada', 'info');
}

// Verificar estado de autenticación
async function checkAuthStatus() {
    const token = localStorage.getItem('auth_token');
    const userData = localStorage.getItem('user_data');
    
    if (token && userData) {
        authToken = token;
        currentUser = JSON.parse(userData);
        
        // Verificar si el token sigue siendo válido
        try {
            const response = await fetch('/api/auth/profile', {
                method: 'GET',
                headers: {
                    'Authorization': 'Bearer ' + authToken,
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                // Token inválido, hacer logout
                logout();
                return;
            }
        } catch (error) {
            console.error('Error verificando token:', error);
        }
    }
    
    updateUI();
}

// Actualizar la UI según el estado de autenticación
function updateUI() {
    const guestButtons = document.getElementById('guest-buttons');
    const userButtons = document.getElementById('user-buttons');
    const userEmail = document.getElementById('user-email');
    
    if (authToken && currentUser) {
        // Usuario logueado
        guestButtons.style.display = 'none';
        userButtons.style.display = 'block';
        userEmail.textContent = currentUser.email;
    } else {
        // Usuario no logueado
        guestButtons.style.display = 'block';
        userButtons.style.display = 'none';
    }
}

// Mostrar alertas
function showAlert(message, type = 'info') {
    // Crear elemento de alerta
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // Insertar al inicio del container
    const container = document.querySelector('.container');
    container.insertBefore(alertDiv, container.firstChild);
    
    // Auto-remover después de 5 segundos
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 5000);
}

// Función para hacer requests autenticados
async function authenticatedFetch(url, options = {}) {
    if (!authToken) {
        showAlert('🔐 Debes iniciar sesión para acceder a esta función', 'warning');
        return null;
    }
    
    const defaultOptions = {
        headers: {
            'Authorization': 'Bearer ' + authToken,
            'Content-Type': 'application/json'
        }
    };
    
    const mergedOptions = { ...defaultOptions, ...options };
    
    try {
        const response = await fetch(url, mergedOptions);
        return response;
    } catch (error) {
        showAlert('Error de conexión: ' + error.message, 'danger');
        return null;
    }
}