let authToken = localStorage.getItem('auth_token');
let currentUser = null;
let pendingMfaChallenge = null;
let pendingMfaEnrollment = false;

document.addEventListener('DOMContentLoaded', function() {
    checkAuthStatus();
});

function showLoginModal() {
    resetLoginFlow();
    const modal = new bootstrap.Modal(document.getElementById('loginModal'));
    modal.show();
}

function showRegisterModal() {
    const modal = new bootstrap.Modal(document.getElementById('registerModal'));
    modal.show();
}

function getLoginErrorDiv() {
    return document.getElementById('loginError');
}

function showLoginError(message) {
    const errorDiv = getLoginErrorDiv();
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
}

function clearLoginError() {
    const errorDiv = getLoginErrorDiv();
    errorDiv.textContent = '';
    errorDiv.style.display = 'none';
}

function resetLoginFlow() {
    pendingMfaChallenge = null;
    pendingMfaEnrollment = false;
    clearLoginError();

    const passwordSection = document.getElementById('loginPasswordSection');
    const mfaSection = document.getElementById('loginMfaSection');
    const enrollmentSection = document.getElementById('loginMfaEnrollment');
    const submitButton = document.getElementById('loginSubmitButton');
    const codeInput = document.getElementById('loginMfaCode');
    const recoveryToggle = document.getElementById('loginUseRecoveryCode');

    passwordSection.style.display = 'block';
    mfaSection.style.display = 'none';
    enrollmentSection.style.display = 'none';
    submitButton.textContent = 'Iniciar Sesión';
    codeInput.value = '';
    recoveryToggle.checked = false;
}

function renderMfaStep(data, enrollment = false) {
    pendingMfaChallenge = data.challenge_token;
    pendingMfaEnrollment = enrollment;

    document.getElementById('loginPasswordSection').style.display = 'none';
    document.getElementById('loginMfaSection').style.display = 'block';
    document.getElementById('loginSubmitButton').textContent = enrollment
        ? 'Confirmar MFA'
        : 'Verificar Código';

    const instructions = document.getElementById('loginMfaInstructions');
    instructions.textContent = enrollment
        ? 'Configura tu aplicación autenticadora y luego ingresa el código de 6 dígitos.'
        : 'Ingresa el código de tu aplicación autenticadora o un recovery code.';
}

function renderMfaEnrollment(setupData) {
    const enrollmentSection = document.getElementById('loginMfaEnrollment');
    enrollmentSection.style.display = 'block';
    document.getElementById('loginMfaSecret').textContent = setupData.secret;

    const setupLink = document.getElementById('loginMfaSetupLink');
    setupLink.href = setupData.otpauth_url;
    setupLink.textContent = 'Abrir configuración en tu app';
}

function completeLogin(data) {
    authToken = data.access_token;
    currentUser = data.user || data.client;

    localStorage.setItem('auth_token', authToken);
    localStorage.setItem('user_data', JSON.stringify(currentUser));

    updateUI();

    const modal = bootstrap.Modal.getInstance(document.getElementById('loginModal'));
    modal.hide();
    resetLoginFlow();

    showAlert('Login exitoso', 'success');

    if (Array.isArray(data.recovery_codes) && data.recovery_codes.length) {
        showAlert(`Guarda tus recovery codes: ${data.recovery_codes.join(', ')}`, 'warning');
    }
}

async function beginMfaEnrollment(challengeToken) {
    const response = await fetch('/api/auth/mfa/setup', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            challenge_token: challengeToken
        })
    });

    const data = await response.json();
    if (!response.ok) {
        throw new Error(data.error || 'No fue posible iniciar MFA');
    }

    renderMfaStep(data, true);
    renderMfaEnrollment(data);
}

async function submitMfaStep() {
    const code = document.getElementById('loginMfaCode').value.trim();
    const useRecoveryCode = document.getElementById('loginUseRecoveryCode').checked;

    if (!pendingMfaChallenge) {
        showLoginError('No existe un desafío MFA activo.');
        return;
    }

    if (!code) {
        showLoginError('Ingresa tu código MFA.');
        return;
    }

    const endpoint = pendingMfaEnrollment
        ? '/api/auth/mfa/confirm'
        : (useRecoveryCode ? '/api/auth/mfa/recovery' : '/api/auth/mfa/verify');

    const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            challenge_token: pendingMfaChallenge,
            code: code
        })
    });

    const data = await response.json();

    if (!response.ok) {
        showLoginError(data.error || 'Código MFA inválido');
        return;
    }

    completeLogin(data);
}

async function login() {
    clearLoginError();

    if (pendingMfaChallenge) {
        try {
            await submitMfaStep();
        } catch (error) {
            showLoginError('Error de conexión: ' + error.message);
        }
        return;
    }

    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;

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

        if (!response.ok) {
            showLoginError(data.error || 'Error en el login');
            return;
        }

        if (data.mfa_enrollment_required) {
            await beginMfaEnrollment(data.challenge_token);
            return;
        }

        if (data.mfa_required) {
            renderMfaStep(data, false);
            return;
        }

        completeLogin(data);
    } catch (error) {
        showLoginError('Error de conexión: ' + error.message);
    }
}

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
            authToken = data.access_token;
            currentUser = data.user || data.client;

            localStorage.setItem('auth_token', authToken);
            localStorage.setItem('user_data', JSON.stringify(currentUser));

            updateUI();

            const modal = bootstrap.Modal.getInstance(document.getElementById('registerModal'));
            modal.hide();

            showAlert('Cuenta creada exitosamente', 'success');
        } else {
            errorDiv.textContent = data.error || 'Error en el registro';
            errorDiv.style.display = 'block';
        }
    } catch (error) {
        errorDiv.textContent = 'Error de conexión: ' + error.message;
        errorDiv.style.display = 'block';
    }
}

function logout() {
    authToken = null;
    currentUser = null;

    localStorage.removeItem('auth_token');
    localStorage.removeItem('user_data');

    updateUI();
    showAlert('Sesión cerrada', 'info');
}

async function checkAuthStatus() {
    const token = localStorage.getItem('auth_token');
    const userData = localStorage.getItem('user_data');

    if (token && userData) {
        authToken = token;
        currentUser = JSON.parse(userData);

        try {
            const response = await fetch('/api/auth/profile', {
                method: 'GET',
                headers: {
                    'Authorization': 'Bearer ' + authToken,
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                logout();
                return;
            }

            const data = await response.json();
            currentUser = data.user || currentUser;
            localStorage.setItem('user_data', JSON.stringify(currentUser));
        } catch (error) {
            console.error('Error verificando token:', error);
        }
    }

    updateUI();
}

function updateUI() {
    const guestButtons = document.getElementById('guest-buttons');
    const userButtons = document.getElementById('user-buttons');
    const userEmail = document.getElementById('user-email');

    if (authToken && currentUser) {
        guestButtons.style.display = 'none';
        userButtons.style.display = 'block';
        userEmail.textContent = currentUser.email;
    } else {
        guestButtons.style.display = 'block';
        userButtons.style.display = 'none';
    }
}

function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    const container = document.querySelector('.container');
    container.insertBefore(alertDiv, container.firstChild);

    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 5000);
}

async function authenticatedFetch(url, options = {}) {
    if (!authToken) {
        showAlert('Debes iniciar sesión para acceder a esta función', 'warning');
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
