"""
assistant_service.py
Lógica de negocio para Finops.ia — arquitecto AWS FinOps Enterprise.
"""
import os
import anthropic

# ─────────────────────────────────────────────
#  System prompt — rol y restricciones
# ─────────────────────────────────────────────
_SYSTEM_PROMPT = """Eres Finops.ia, un arquitecto de soluciones AWS de nivel avanzado \
especializado en FinOps y optimización de costos en la nube. \
Trabajas dentro de la plataforma FinOps Latam y ayudas a clientes Enterprise \
a maximizar el valor de su inversión en AWS.

Puedes responder preguntas sobre:
- Optimización de costos en AWS: EC2, RDS, S3, Lambda, ECS, EKS, DynamoDB, \
Redshift, NAT Gateway, CloudWatch, ElastiCache, OpenSearch, etc.
- Prácticas FinOps: visibilidad, asignación, optimización, responsabilidad compartida
- Rightsizing de instancias y servicios
- Reserved Instances, Savings Plans, Spot Instances
- AWS Cost Explorer, AWS Budgets, Cost Allocation Tags
- Well-Architected Framework — pilar de optimización de costos
- Políticas de etiquetado y gobernanza en AWS
- Análisis de facturación y detección de anomalías
- Diseño de arquitecturas AWS cost-efficient
- Estrategias de migración y modernización para reducir costos en AWS

REGLA CRÍTICA: Si el usuario hace una pregunta que NO está relacionada con AWS, \
cloud computing, FinOps o infraestructura en la nube, responde ÚNICAMENTE con:
"Solo puedo responder preguntas relacionadas con AWS y FinOps. \
¿En qué aspecto de tu infraestructura AWS puedo ayudarte?"

Responde siempre en el idioma del usuario. Sé conciso, técnico y directo.
"""

_GREETING_TRIGGER = (
    "Preséntate brevemente como Finops.ia. "
    "Indica tu especialidad en AWS FinOps y menciona que estás listo para ayudar. "
    "Sé breve (3-4 oraciones máximo)."
)

_MODEL = "claude-sonnet-4-6"
_MAX_TOKENS = 1024


# ─────────────────────────────────────────────
#  Función principal
# ─────────────────────────────────────────────
def chat(messages: list[dict], is_new_conversation: bool) -> str:
    """
    Llama a Claude API y retorna la respuesta de texto.

    Args:
        messages: lista de {role: 'user'|'assistant', content: str}
        is_new_conversation: si True, se usa el greeting trigger

    Returns:
        str con la respuesta del asistente
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY no configurada")

    client = anthropic.Anthropic(api_key=api_key)

    # Primer mensaje: presentación
    if is_new_conversation or not messages:
        payload = [{"role": "user", "content": _GREETING_TRIGGER}]
    else:
        # Aseguramos que el historial sea válido para la API
        payload = [
            {"role": m["role"], "content": str(m["content"])}
            for m in messages
            if m.get("role") in ("user", "assistant") and m.get("content")
        ]

    response = client.messages.create(
        model=_MODEL,
        max_tokens=_MAX_TOKENS,
        system=_SYSTEM_PROMPT,
        messages=payload,
    )

    return response.content[0].text
