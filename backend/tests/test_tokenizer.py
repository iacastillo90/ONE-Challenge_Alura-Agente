import pytest
from app.core.tokenizer import token_counter, _encoding_for_model, _char_multiplier_for_model
from app.core.exceptions import TokenLimitError


class TestEncodingForModel:
    def test_gpt4_uses_cl100k(self):
        assert _encoding_for_model("gpt-4") == "cl100k_base"

    def test_gpt4o_uses_o200k(self):
        assert _encoding_for_model("gpt-4o") == "o200k_base"

    def test_gemini_returns_none(self):
        assert _encoding_for_model("gemini-2.0-flash") is None

    def test_unknown_returns_none(self):
        assert _encoding_for_model("unknown-model") is None

    def test_none_returns_cl100k(self):
        assert _encoding_for_model(None) == "cl100k_base"


class TestCharMultiplier:
    def test_gemini_has_higher_multiplier(self):
        assert _char_multiplier_for_model("gemini") == 4.5

    def test_unknown_defaults_to_4(self):
        assert _char_multiplier_for_model("unknown") == 4.0


class TestTokenCounter:
    def test_count_returns_positive(self):
        assert token_counter.count("hello world") > 0

    def test_count_messages_with_role_overhead(self):
        msgs = [{"role": "user", "content": "hi"}]
        assert token_counter.count_messages(msgs) >= 6

    def test_truncate_messages_keeps_protected(self):
        messages = [
            {"role": "system", "content": "you are a helpful assistant"},
            {"role": "user", "content": "hello"},
            {"role": "user", "content": "world"},
        ]
        truncated = token_counter.truncate_messages(messages, max_tokens=10, protected_count=1)
        assert truncated[0]["role"] == "system"
        assert len(truncated) < len(messages)

    def test_truncate_preserves_protected_on_overflow(self):
        messages = [{"role": "user", "content": "a" * 1000}]
        with pytest.raises(TokenLimitError):
            token_counter.truncate_messages(messages, max_tokens=5, protected_count=1)
