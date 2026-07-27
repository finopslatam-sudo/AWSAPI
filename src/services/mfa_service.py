"""
MFA SERVICE
===========

Re-exporta la API pública de MFA desde los módulos divididos por
responsabilidad (cifrado, enrolamiento, verificación, política), para
que el código existente que hace `from src.services.mfa_service import
...` siga funcionando sin cambios.
"""

from src.services.mfa_crypto import (  # noqa: F401
    build_otpauth_url,
    decrypt_secret,
    encrypt_secret,
    generate_recovery_codes,
    generate_totp_secret,
    hash_recovery_codes,
    issue_login_challenge,
    parse_login_challenge,
    verify_totp_code,
)
from src.services.mfa_enrollment import (  # noqa: F401
    disable_mfa,
    finalize_totp_enrollment,
    regenerate_recovery_codes,
    start_totp_enrollment,
)
from src.services.mfa_verification import (  # noqa: F401
    is_mfa_temporarily_locked,
    register_mfa_failure,
    register_mfa_success,
    verify_recovery_code,
    verify_user_totp,
)
from src.services.mfa_policy import (  # noqa: F401
    CLIENT_ADMIN_ROLES,
    SYSTEM_MFA_ROLES,
    can_disable_mfa,
    get_client_mfa_policy,
    get_mfa_status,
    is_mfa_required_for_user,
    must_enroll_mfa,
)
