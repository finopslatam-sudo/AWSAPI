# =====================================================
#   OBSERVABILITY — Sentry opcional (no-op si falta SENTRY_DSN)
# =====================================================
import os


def init_observability() -> None:
    dsn = (os.getenv("SENTRY_DSN") or "").strip()
    if not dsn:
        return

    import sentry_sdk
    from sentry_sdk.integrations.flask import FlaskIntegration

    sentry_sdk.init(
        dsn=dsn,
        integrations=[FlaskIntegration()],
        environment=os.getenv("APP_ENV", "production"),
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
    )
