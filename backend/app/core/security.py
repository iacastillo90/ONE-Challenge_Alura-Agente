from __future__ import annotations

import re

from loguru import logger

from app.core.exceptions import RAGException

# El orden importa: sanitize_pii aplica estas expresiones secuencialmente.
# credit_card debe ejecutarse antes que phone para evitar que los números de 16 dígitos
# se consuman parcialmente por el reconocedor de teléfonos.
PII_PATTERNS = {
    "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    "credit_card": re.compile(r"\b\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{1,4}\b"),
    "phone": re.compile(r"\+?\d{1,3}[-.\s]?\d{2,3}[-.\s]?\d{4,5}[-.\s]?\d{4}"),
    "cpf": re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"),
    "cnpj": re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b"),
    "cep": re.compile(r"\b\d{5}-?\d{3}\b"),
    "rg": re.compile(r"\b\d{1,2}\.?\d{3}\.?\d{3}-?[\dxX]\b"),
    "pix_key": re.compile(r"(?i)(pix|chave\s*pix)[:\s]*[a-zA-Z0-9.@\-_]+"),
    "dni": re.compile(r"\b\d{2}\.\d{3}\.\d{3}\b"),
    "password_like": re.compile(r"(?i)(password|passwd|pwd|secret|token|api_key)\s*[:=]\s*\S+"),
}

SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|apikey|secret|token|password|passwd|credential)\s*[=:]\s*['\"]?\w{16,}"),
    re.compile(r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----"),
    re.compile(r"(?i)sk-[a-zA-Z0-9]{20,}"),
    re.compile(r"(?i)ghp_[a-zA-Z0-9]{36}"),
    re.compile(r"(?i)AKIA[0-9A-Z]{16}"),
]

INJECTION_INDICATORS = [
    re.compile(r"(?i)ignore\s+(all\s+)?(previous|above|prior)\s+instructions"),
    re.compile(r"(?i)forget\s+(all\s+)?(previous|above|prior)\s+instructions"),
    re.compile(r"(?i)system\s+prompt"),
    re.compile(r"(?i)you\s+are\s+(now\s+)?(an?\s+)?(free|unbounded|unconstrained)"),
    re.compile(r"(?i)act\s+as\s+(if\s+)?you\s+are"),
    re.compile(r"(?i)new\s+(instructions|prompt|rules)"),
    re.compile(r"(?i)do\s+not\s+(follow|obey|listen)"),
    re.compile(r"(?i)bypass\s+(safety|guardrails|restrictions)"),
]

MIME_MAGIC: dict[str, tuple[bytes, int]] = {
    "application/pdf": (b"%PDF", 0),
}

TEXT_EXTENSIONS = {".csv", ".txt", ".md", ".json", ".xml", ".yaml", ".yml"}


def matches_mime(header: bytes, mime_type: str) -> bool:
    magic, offset = MIME_MAGIC.get(mime_type)
    if magic is None:
        return False
    if not magic:
        return True
    return header[offset:].startswith(magic)


def validate_text_content(content: bytes) -> tuple[bool, str]:
    try:
        content.decode("utf-8")
    except UnicodeDecodeError:
        return False, "El archivo no contiene texto plano UTF-8 válido"
    null_count = content.count(b"\x00")
    if null_count > 0:
        return False, f"Se detectó contenido binario ({null_count} bytes nulos)"
    non_text = sum(1 for b in content[:1024] if b < 32 and b not in (9, 10, 13))
    if non_text > 50:
        return False, "El contenido parece ser binario (caracteres no imprimibles)"
    return True, ""


def detect_suspicious_content(text: str) -> list[str]:
    findings: list[str] = []
    for pattern in INJECTION_INDICATORS:
        if pattern.search(text):
            findings.append(f"Posible inyección de prompt: coincide con /{pattern.pattern}/")
    return findings


def assert_safe_content(text: str, context: str = "contenido"):
    findings = detect_suspicious_content(text)
    if findings:
        raise RAGException(
            message=f"{context.capitalize()} sospechoso detectado y bloqueado: {'; '.join(findings[:3])}"
        )


OUTPUT_MODERATION_PATTERNS = {
    "hate_speech": re.compile(r"(?i)\b(mata[rt]e?|v[áa]yase|eres\s+un\s+(in[úu]til|idiot[ae]))\b"),
    "dangerous_content": re.compile(r"(?i)(c[óo]mo\s+hacer\s+una\s+bomba|c[óo]mo\s+suicidar|\barma\s+qu[íi]mica\b)"),
    "personal_attack": re.compile(r"(?i)\b(te\s+odio|eres\s+lo\s+peor|maldit[oa])\b"),
}


MODERATION_MASK = "[CONTENIDO_BLOQUEADO]"

def moderate_output(text: str) -> str:
    for label, pattern in OUTPUT_MODERATION_PATTERNS.items():
        if pattern.search(text):
            logger.warning(f"Moderación de salida activada: {label}")
            text = pattern.sub(MODERATION_MASK, text)
    return text


PII_MASKS = {
    "email": "[EMAIL_REDACTED]",
    "phone": "[TELEFONO_REDACTED]",
    "cpf": "[CPF_REDACTED]",
    "cnpj": "[CNPJ_REDACTED]",
    "cep": "[CEP_REDACTED]",
    "rg": "[RG_REDACTED]",
    "credit_card": "****-****-****-****",
    "pix_key": "[PIX_REDACTED]",
    "dni": "[DNI_REDACTED]",
    "password_like": "******",
}


def detect_secrets(text: str) -> list[str]:
    findings: list[str] = []
    for pattern in SECRET_PATTERNS:
        matches = pattern.findall(text)
        if matches:
            findings.append(f"Posible fuga de secreto: coincide con /{pattern.pattern}/")
    return findings


def sanitize_pii(text: str) -> str:
    for label, pattern in PII_PATTERNS.items():
        text = pattern.sub(PII_MASKS.get(label, f"[{label.upper()}_REDACTED]"), text)
    return text


class StreamingSanitizer:
    def __init__(self, buffer_size: int = 500):
        self._buffer = ""
        self._buffer_size = buffer_size
        self._emitted = 0

    def process_token(self, token: str) -> str:
        self._buffer += token
        if len(self._buffer) >= self._buffer_size:
            safe_chunk = sanitize_pii(self._buffer)
            self._buffer = ""
            self._emitted += len(safe_chunk)
            return safe_chunk
        return ""

    def flush(self) -> str:
        safe = sanitize_pii(self._buffer)
        self._buffer = ""
        return safe
