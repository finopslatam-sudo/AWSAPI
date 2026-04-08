"""
ENV LOADER
==========

Carga variables de entorno priorizando `/etc/finops-api.env`.
Si ese archivo no existe, usa fallback a `.env` local para desarrollo.
"""

import os
from dotenv import load_dotenv


SYSTEM_ENV_PATH = "/etc/finops-api.env"


def load_environment() -> None:
    """
    Carga variables de entorno para el backend.
    Prioridad:
    1) /etc/finops-api.env
    2) .env (fallback dev)
    """
    if os.path.exists(SYSTEM_ENV_PATH):
        # No sobreescribe variables ya exportadas por systemd/shell.
        load_dotenv(SYSTEM_ENV_PATH, override=False)
    else:
        # Fallback local para desarrollo.
        load_dotenv(override=True)
