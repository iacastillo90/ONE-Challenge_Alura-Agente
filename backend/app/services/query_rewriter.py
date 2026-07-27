import re

from app.llm.base import Message


STOP_WORDS = {
    "un", "una", "unos", "unas", "el", "la", "los", "las",
    "y", "e", "o", "u", "de", "del", "en", "por", "para",
    "con", "sin", "a", "ante", "bajo", "cabe", "contra",
    "es", "son", "fue", "era", "ser", "estar", "tener",
    "hay", "hacer", "puede", "como", "qué", "que", "se",
    "su", "sus", "le", "les", "lo", "la", "las", "los",
}


class QueryRewriter:
    def __init__(self, llm_generate=None):
        self._llm = llm_generate

    async def rewrite(self, query: str, history: list[dict] | None = None) -> str:
        if self._llm and len(query) > 10:
            result = await self._llm_rewrite(query, history)
            if result and len(result) > 3:
                return result
        return self._simple_rewrite(query)

    async def _llm_rewrite(self, query: str, history: list[dict] | None = None) -> str | None:
        context = ""
        if history:
            recent = [m for m in history[-4:] if m.get("role") in ("user", "assistant")]
            if recent:
                context = "\n".join(
                    f"{'Usuario' if m['role'] == 'user' else 'Asistente'}: {m['content'][:200]}"
                    for m in recent
                )
                context = f"\nHistorial reciente:\n{context}\n"

        prompt = (
            "Reescribe la siguiente pregunta del usuario para mejorar la búsqueda "
            "semántica en una base de documentos. Debe ser una consulta autónoma, "
            "clara y específica. Responde SOLO con la pregunta reescrita, sin explicaciones.\n\n"
            f"Pregunta original: {query}"
            f"{context}"
        )

        try:
            parts = []
            async for event in self._llm(
                messages=[Message(role="user", content=prompt)],
                max_tokens=256,
                temperature=0.3,
            ):
                if event.token:
                    parts.append(event.token)
                    if event.done:
                        break
            return "".join(parts).strip() if parts else None
        except Exception:
            return None

    def _simple_rewrite(self, query: str) -> str:
        cleaned = re.sub(r"[^\w\sáéíóúñü]", " ", query)
        words = cleaned.split()
        important = [w for w in words if w.lower() not in STOP_WORDS and len(w) > 2]
        if not important:
            important = words
        return " ".join(important[:20])
