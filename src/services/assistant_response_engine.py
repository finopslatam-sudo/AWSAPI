"""
assistant_response_engine.py
Motor de respuestas local para Finops.ia — sin API externa.
Detecta intención por palabras clave y delega a los handlers.
"""
from src.models.aws_finding import AWSFinding
from src.models.aws_resource_inventory import AWSResourceInventory
from src.models.risk_snapshot import RiskSnapshot
from src.services.assistant_response_handlers import _HANDLERS, _h_greeting

# ── Detección de intención ────────────────────────────────────
_INTENTS = {
    "account_info": [
        "a qué cuenta", "a que cuenta", "qué cuenta", "que cuenta",
        "cuál es mi cuenta", "cual es mi cuenta", "mis cuentas", "cuentas aws",
        "cuentas tengo", "corresponde", "pertenece esta cuenta", "qué cuentas tengo",
        "que cuentas tengo", "recursos que me muestras", "de qué cuenta",
    ],
    "savings_total": [
        "cuánto puedo ahorrar", "cuanto puedo ahorrar", "ahorro total",
        "potencial de ahorro", "ahorrar en total", "cuánto ahorro",
        "cuanto ahorro", "dinero puedo ahorrar", "optimizar costos",
        "cuánto me puedo ahorrar",
    ],
    "why_increase": [
        "por qué subió", "por que subio", "subio", "subió", "aumentó",
        "aumento", "incremento", "costo este mes", "factura alta",
        "por qué es tan caro", "por que es tan caro", "gasto alto",
        "costos altos", "por que sube", "por qué sube",
    ],
    "critical_findings": [
        "crítico", "critico", "critical", "hallazgos críticos",
        "más grave", "mas grave", "severo", "urgente", "alta severidad",
    ],
    "unused_resources": [
        "sin usar", "idle", "subutilizado", "no se usa", "recursos sin",
        "no están siendo usados", "desperdicio", "recursos inutilizados",
        "recursos parados", "apagados",
    ],
    "risk_level": [
        "nivel de riesgo", "riesgo actual", "score", "exposición", "exposicion",
        "cómo estoy", "como estoy", "situación actual", "situacion actual",
        "estado actual", "cómo está mi cuenta", "como esta mi cuenta",
    ],
    "services_in_use": [
        "qué servicios", "que servicios", "servicios aws", "estoy usando",
        "qué uso", "que uso", "qué recursos tengo", "que recursos tengo",
        "qué tengo", "que tengo", "inventario", "qué corre",
    ],
    "most_expensive": [
        "más costoso", "mas costoso", "más caro", "mas caro", "mayor costo",
        "qué me cuesta más", "que me cuesta mas", "mayor gasto", "más dinero",
    ],
    "changes_previous": [
        "cambió", "cambio", "vs el", "mes anterior", "snapshot anterior",
        "mes pasado", "comparado con", "diferencia vs", "qué cambió", "que cambio",
    ],
    "regions": [
        "regiones", "región", "region", "dónde tengo", "donde tengo",
        "en qué zona", "en que zona", "availability zone",
    ],
    "resolve_first": [
        "resolver primero", "prioridad", "qué debo resolver", "que debo resolver",
        "empezar por", "qué hacer", "que hacer", "recomendaciones",
        "qué me recomiendas", "que me recomiendas", "por dónde empiezo",
        "por donde empiezo", "sugerencias", "qué acciones", "que acciones",
    ],
    "ec2_cost": [
        "ec2", "instancias ec2", "costo ec2", "mis instancias",
        "virtual machine", "máquinas virtuales",
    ],
    "rds_findings": [
        "rds", "base de datos", "database", "bases de datos",
        "mysql", "postgres", "aurora", "sql server", "oracle rds",
    ],
    "lambda_findings": [
        "lambda", "funciones serverless", "serverless", "mis funciones",
        "funciones lambda",
    ],
    "s3_findings": [
        "s3", "bucket", "almacenamiento s3", "objetos s3", "buckets",
        "almacenamiento de objetos",
    ],
    "savings_plans": [
        "savings plan", "reserved instance", "instancias reservadas",
        "compromisos", "descuentos aws", "ahorro comprometido",
    ],
    "all_findings": [
        "todos los hallazgos", "lista de hallazgos", "qué hallazgos",
        "que hallazgos", "hallazgos activos", "muéstrame hallazgos",
        "muestrame hallazgos", "qué problemas", "que problemas",
        "problemas detectados", "issues", "findings",
    ],
    "health": [
        "health", "salud del inventario", "gobernanza", "governance",
        "etiquetado", "tags", "compliance", "etiquetas", "tagging",
        "qué tan sano", "que tan sano",
    ],
}

_NON_AWS = [
    "receta", "cocina", "fútbol", "futbol", "película", "pelicula",
    "música", "musica", "chiste", "broma", "política", "politica",
    "medicina", "geografía", "geografia", "deporte", "clima",
]

_ONLY_AWS = (
    "Solo puedo responder preguntas relacionadas con AWS y FinOps. "
    "¿En qué aspecto de tu infraestructura AWS puedo ayudarte?"
)

_UNKNOWN = (
    "No entendí esa pregunta. Puedo responderte sobre:\n\n"
    "  • ¿A qué cuenta corresponden mis recursos?\n"
    "  • Ahorro potencial total\n"
    "  • Hallazgos críticos activos\n"
    "  • Por qué subió tu cuenta\n"
    "  • Recursos sin usar\n"
    "  • Nivel de riesgo actual\n"
    "  • Servicios AWS en uso (EC2, RDS, Lambda, S3...)\n"
    "  • Prioridad de resolución\n"
    "  • Regiones con recursos\n\n"
    "Usa los botones de sugerencias o reformula tu pregunta."
)


def _detect_intent(text: str) -> str:
    t = text.lower()
    for intent, keywords in _INTENTS.items():
        if any(kw in t for kw in keywords):
            return intent
    return "unknown"


# ── Helpers de BD (compartidos con handlers) ─────────────────
def _findings(client_id, account_id=None):
    q = AWSFinding.query.filter_by(client_id=client_id, resolved=False)
    if account_id:
        q = q.filter_by(aws_account_id=account_id)
    return q.all()


def _inventory(client_id, account_id=None):
    q = AWSResourceInventory.query.filter_by(client_id=client_id, is_active=True)
    if account_id:
        q = q.filter_by(aws_account_id=account_id)
    return q.all()


def _snapshots(client_id, n=2):
    return (RiskSnapshot.query.filter_by(client_id=client_id)
            .order_by(RiskSnapshot.created_at.desc()).limit(n).all())


# ── Entry point ───────────────────────────────────────────────
def get_response(message: str, client_id: int, aws_account_id: int | None, is_new: bool) -> str:
    if is_new or not message:
        return _h_greeting(client_id, aws_account_id)
    if any(kw in message.lower() for kw in _NON_AWS):
        return _ONLY_AWS
    handler = _HANDLERS.get(_detect_intent(message))
    return handler(client_id, aws_account_id) if handler else _UNKNOWN
