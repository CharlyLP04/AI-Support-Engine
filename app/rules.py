import re

from app.schemas import AnalysisResult, Category, Mode, Priority


_SECURITY = re.compile(
    r"vulnerab|exploit|explot|datos? privados?|extraer datos|filtraci[oó]n|"
    r"sin autorizaci[oó]n|otra cuenta|ransomware|brecha de seguridad|"
    r"cuenta comprometida|token expuesto|acceso no autorizado|data leak|"
    r"exfiltrat|unauthorized|cross.?account",
    re.IGNORECASE,
)
_ACCESS = re.compile(
    r"iniciar sesi[oó]n|login|acceder|entrar|contrase[nñ]a|restablecer|"
    r"recuperaci[oó]n de contrase[nñ]a|no puedo abrir|no puedo entrar|"
    r"acceso|permisos?",
    re.IGNORECASE,
)
_FEATURE = re.compile(
    r"agregar|a[nñ]adir|incorporar|nueva funci[oó]n|modo oscuro|"
    r"me gustar[ií]a|podr[ií]an|solicito|necesitamos|exportaci[oó]n a pdf|"
    r"feature request",
    re.IGNORECASE,
)
_CRITICAL_SECURITY = re.compile(
    r"vulnerab|exploit|explot|datos? privados?|extraer datos|otra cuenta|"
    r"sin autorizaci[oó]n|brecha|comprometid|ransomware|filtraci[oó]n|exfiltrat",
    re.IGNORECASE,
)
_CRITICAL_OUTAGE = re.compile(
    r"plataforma completa.*ca[ií]da|ca[ií]da.*todos|todos los clientes.*no pueden|"
    r"ning[uú]n cliente.*procesar|no pueden procesar pedidos|servicio ca[ií]do|outage",
    re.IGNORECASE,
)
_HIGH_ACCESS_IMPACT = re.compile(
    r"todos (?:los )?(?:agentes|usuarios|empleados|clientes).*no pueden.*(?:iniciar|entrar)|"
    r"llamadas est[aá]n bloqueadas|equipo completo.*sin acceso",
    re.IGNORECASE,
)
_LOW_BUG = re.compile(r"error tipogr[aá]fico|typo|etiqueta.*mal escrita", re.IGNORECASE)

_RESPONSES = {
    Category.ACCESS: (
        "Lamentamos el inconveniente. Verifica tus credenciales y prueba la recuperación de contraseña. "
        "Si continúa, comparte el mensaje de error con soporte."
    ),
    Category.BUG: (
        "Gracias por reportarlo. Comparte los pasos para reproducir la falla y la hora aproximada "
        "para que podamos investigarla."
    ),
    Category.FEATURE: (
        "Gracias por la sugerencia. La registraremos para evaluar su utilidad y alcance."
    ),
    Category.SECURITY: (
        "Gracias por avisarnos. El reporte requiere revisión humana; evita compartir datos sensibles "
        "y conserva la evidencia del incidente."
    ),
}


def detect_security_priority(message: str) -> Priority | None:
    """Return the minimum safe priority for high-confidence security language."""
    if not _SECURITY.search(message):
        return None
    return Priority.CRITICAL if _CRITICAL_SECURITY.search(message) else Priority.HIGH


def classify_traditional(message: str) -> AnalysisResult:
    """Classify a support request with deterministic rules only."""
    text = message.strip()
    if not text:
        raise ValueError("message must not be blank")

    security_priority = detect_security_priority(text)
    if security_priority is not None:
        category = Category.SECURITY
    elif _ACCESS.search(text):
        category = Category.ACCESS
    elif _FEATURE.search(text):
        category = Category.FEATURE
    else:
        category = Category.BUG

    if category is Category.SECURITY:
        priority = security_priority or Priority.HIGH
    elif category is Category.ACCESS:
        priority = Priority.HIGH if _HIGH_ACCESS_IMPACT.search(text) else Priority.MEDIUM
    elif category is Category.FEATURE:
        priority = Priority.LOW
    elif _CRITICAL_OUTAGE.search(text):
        priority = Priority.CRITICAL
    elif _LOW_BUG.search(text):
        priority = Priority.LOW
    else:
        priority = Priority.MEDIUM

    return AnalysisResult(
        category=category,
        priority=priority,
        response=_RESPONSES[category],
        requiresHumanReview=(category is Category.SECURITY),
        mode=Mode.TRADITIONAL,
    )
