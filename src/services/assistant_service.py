"""
assistant_service.py
Lógica de negocio para Finops.ia — arquitecto AWS FinOps Enterprise con RAG.
"""
import os
import anthropic

# ─────────────────────────────────────────────
#  System prompt base
# ─────────────────────────────────────────────
_SYSTEM_BASE = """Eres Finops.ia, un arquitecto de soluciones AWS de nivel avanzado \
especializado en FinOps y optimización de costos en la nube. \
Trabajas dentro de la plataforma FinOps Latam y ayudas a clientes Enterprise \
a maximizar el valor de su inversión en AWS.

Cuando se proporcionen datos reales de la cuenta del cliente (sección DATOS REALES DEL CLIENTE), \
úsalos para dar respuestas precisas y personalizadas. Si los datos no cubren la pregunta, \
responde con tu conocimiento experto en AWS.

Puedes responder preguntas sobre:
- Costos y facturación AWS: análisis, tendencias, causas de incremento
- Hallazgos y recomendaciones de rightsizing específicos del cliente
- Recursos activos: inventario, regiones, servicios en uso
- Riesgo y cumplimiento: score, exposición financiera, gobernanza
- Optimización: EC2, RDS, S3, Lambda, ECS, EKS, DynamoDB, Redshift, NAT, CloudWatch
- Prácticas FinOps: Reserved Instances, Savings Plans, Spot Instances
- AWS Cost Explorer, Budgets, Cost Allocation Tags
- Well-Architected Framework — pilar de optimización de costos
- Estrategias de migración y modernización para reducir costos

REGLA CRÍTICA: Si la pregunta NO está relacionada con AWS, cloud computing, FinOps \
o infraestructura en la nube, responde ÚNICAMENTE con:
"Solo puedo responder preguntas relacionadas con AWS y FinOps. \
¿En qué aspecto de tu infraestructura AWS puedo ayudarte?"

Responde siempre en el idioma del usuario. Sé conciso, técnico y directo.
Cuando cites datos del cliente, sé específico (usa los números reales).
"""

_GREETING_TRIGGER = (
    "Preséntate brevemente como Finops.ia. "
    "Indica que tienes acceso a los datos reales de su cuenta AWS. "
    "Menciona ejemplos de preguntas que puedes responder. "
    "Sé amigable pero profesional (máximo 5 oraciones)."
)

_MODEL = "claude-sonnet-4-6"
_MAX_TOKENS = 1024


# ─────────────────────────────────────────────
#  Función principal
# ─────────────────────────────────────────────
def chat(messages: list[dict], is_new_conversation: bool, context: str = "") -> str:
    """
    Llama a Claude API con el contexto real del cliente y retorna la respuesta.

    Args:
        messages: lista de {role: 'user'|'assistant', content: str}
        is_new_conversation: si True se usa el greeting trigger
        context: bloque de texto con datos reales del cliente (RAG)

    Returns:
        str con la respuesta del asistente
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY no configurada")

    client = anthropic.Anthropic(api_key=api_key)

    # Combinar system prompt con contexto real del cliente
    system = _SYSTEM_BASE
    if context:
        system = f"{_SYSTEM_BASE}\n\n{context}"

    if is_new_conversation or not messages:
        payload = [{"role": "user", "content": _GREETING_TRIGGER}]
    else:
        payload = [
            {"role": m["role"], "content": str(m["content"])}
            for m in messages
            if m.get("role") in ("user", "assistant") and m.get("content")
        ]

    response = client.messages.create(
        model=_MODEL,
        max_tokens=_MAX_TOKENS,
        system=system,
        messages=payload,
    )

    return response.content[0].text
