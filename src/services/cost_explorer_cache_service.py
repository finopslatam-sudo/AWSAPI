"""
COST EXPLORER CACHE SERVICE
============================
Wrapper sobre CostExplorerService con caché persistente en BD.

TTLs por método:
  6months          → 30 días  (histórico mensual)
  annual           → 180 días (costos año anterior no cambian)
  service_breakdown→ 24 horas (o forzado al correr Scan)
"""
import json
import logging
from datetime import datetime, timedelta

from src.models.cost_explorer_cache import CostExplorerCache
from src.models.database import db
from src.aws.cost_explorer_service import CostExplorerService

logger = logging.getLogger(__name__)

# Tiempo de vida en segundos por clave de caché
_TTL = {
    "6months":           30 * 24 * 3600,   # 30 días
    "annual":           180 * 24 * 3600,   # 6 meses
    "service_breakdown":      24 * 3600,   # 24 horas
}


def _read_cache(aws_account_id: int, cache_key: str):
    """Devuelve los datos cacheados si aún son válidos, o None si vencieron."""
    row = CostExplorerCache.query.filter_by(
        aws_account_id=aws_account_id,
        cache_key=cache_key
    ).first()

    if row is None:
        return None

    ttl = _TTL.get(cache_key, 24 * 3600)
    age = (datetime.utcnow() - row.fetched_at).total_seconds()
    if age > ttl:
        return None

    return json.loads(row.data_json)


def _write_cache(aws_account_id: int, cache_key: str, data) -> None:
    """Guarda o actualiza el caché en BD."""
    row = CostExplorerCache.query.filter_by(
        aws_account_id=aws_account_id,
        cache_key=cache_key
    ).first()

    serialized = json.dumps(data)

    if row:
        row.data_json = serialized
        row.fetched_at = datetime.utcnow()
    else:
        db.session.add(CostExplorerCache(
            aws_account_id=aws_account_id,
            cache_key=cache_key,
            data_json=serialized,
            fetched_at=datetime.utcnow()
        ))

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.warning(f"[CE_CACHE] write failed account={aws_account_id} key={cache_key}: {e}")


class CostExplorerCacheService:
    """
    Interfaz idéntica a CostExplorerService.
    Se puede usar como drop-in replacement en accumulate_cost_data().
    """

    def __init__(self, aws_account):
        self._account = aws_account
        self._ce: CostExplorerService | None = None  # lazy init

    def _get_ce(self) -> CostExplorerService:
        if self._ce is None:
            self._ce = CostExplorerService(self._account)
        return self._ce

    # ── 6 meses de costos mensuales ─────────────────────────────────
    def get_last_6_months_cost(self) -> list:
        key = "6months"
        cached = _read_cache(self._account.id, key)
        if cached is not None:
            return cached

        logger.info(f"[CE_CACHE] MISS 6months account={self._account.id} → AWS API")
        data = self._get_ce().get_last_6_months_cost()
        _write_cache(self._account.id, key, data)
        return data

    # ── Costos anuales (año anterior + YTD) ─────────────────────────
    def get_annual_costs(self) -> dict:
        key = "annual"
        cached = _read_cache(self._account.id, key)
        if cached is not None:
            return cached

        logger.info(f"[CE_CACHE] MISS annual account={self._account.id} → AWS API")
        data = self._get_ce().get_annual_costs()
        _write_cache(self._account.id, key, data)
        return data

    # ── Desglose por servicio del mes actual ─────────────────────────
    def get_service_breakdown_current_month(self) -> list:
        key = "service_breakdown"
        cached = _read_cache(self._account.id, key)
        if cached is not None:
            return cached

        logger.info(f"[CE_CACHE] MISS service_breakdown account={self._account.id} → AWS API")
        data = self._get_ce().get_service_breakdown_current_month()
        _write_cache(self._account.id, key, data)
        return data

    # ── Invalidación forzada (Scan RUN) ──────────────────────────────
    @staticmethod
    def invalidate_service_breakdown(aws_account_id: int) -> None:
        """Fuerza recarga en la próxima consulta tras un Scan RUN."""
        try:
            CostExplorerCache.query.filter_by(
                aws_account_id=aws_account_id,
                cache_key="service_breakdown"
            ).delete()
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.warning(f"[CE_CACHE] invalidate failed account={aws_account_id}: {e}")
