from loguru import logger

from app.core.exceptions import TokenLimitError

# Order matters: more specific keys (gpt-4o) must precede prefixes (gpt-4).
MODEL_ENCODINGS: dict[str, str] = {
    "gpt-4o": "o200k_base",
    "gpt-4": "cl100k_base",
    "gpt-3.5": "cl100k_base",
    "deepseek": "r50k_base",
}

MODEL_TOKEN_MULTIPLIER: dict[str, float] = {
    "gemini": 4.5,
    "llama": 3.5,
    "mixtral": 3.5,
    "deepseek": 3.0,
}


def _encoding_for_model(model_name: str | None) -> str | None:
    if model_name is None:
        return "cl100k_base"
    lower = model_name.lower()
    for key, enc in MODEL_ENCODINGS.items():
        if key in lower:
            return enc
    return None

def _char_multiplier_for_model(model_name: str | None) -> float:
    if model_name is None:
        return 4.0
    lower = model_name.lower()
    for key, mul in MODEL_TOKEN_MULTIPLIER.items():
        if key in lower:
            return mul
    return 4.0


class TokenCounter:
    def __init__(self):
        self._encoders: dict[str, object] = {}

    def _get_encoder(self, model_name: str | None = None):
        enc_name = _encoding_for_model(model_name)
        if enc_name is None:
            return None
        if enc_name not in self._encoders:
            try:
                import tiktoken
                self._encoders[enc_name] = tiktoken.get_encoding(enc_name)
            except ImportError:
                logger.warning("tiktoken not available, using char-based estimation")
                self._encoders[enc_name] = None
        return self._encoders.get(enc_name)

    def count(self, text: str, model_name: str | None = None) -> int:
        enc = self._get_encoder(model_name)
        if enc is not None:
            return len(enc.encode(text))
        chars_per_token = _char_multiplier_for_model(model_name)
        return max(1, int(len(text) / chars_per_token))

    def count_messages(self, messages: list[dict], model_name: str | None = None) -> int:
        total = 0
        for m in messages:
            total += self.count(m.get("content", ""), model_name=model_name)
            total += 4
        total += 2
        return total

    def truncate_messages(
        self,
        messages: list[dict],
        max_tokens: int,
        protected_count: int = 1,
        model_name: str | None = None,
    ) -> list[dict]:
        protected = messages[:protected_count]
        truncatable = messages[protected_count:]
        had_truncatable = bool(truncatable)

        while truncatable and self.count_messages(protected + truncatable, model_name=model_name) > max_tokens:
            truncatable.pop(0)

        # If even the protected messages alone exceed the limit and there was
        # nothing we could trim, the request is fundamentally too large.
        if (
            not had_truncatable
            and self.count_messages(protected, model_name=model_name) > max_tokens
        ):
            raise TokenLimitError(f"Protected messages exceed {max_tokens} token limit")

        return protected + truncatable


token_counter = TokenCounter()
