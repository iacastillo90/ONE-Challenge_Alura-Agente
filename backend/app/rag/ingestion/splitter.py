from dataclasses import dataclass, field

from app.core.tokenizer import token_counter


@dataclass
class Chunk:
    content: str
    metadata: dict


@dataclass
class RecursiveChunker:
    chunk_size: int = 256
    chunk_overlap: int = 32

    # NOTE: chunk_size is in TOKENS (via token_counter).
    # Config's chunk_size (512) is for retrieval config, NOT used here.

    SEPARATORS: list[str] = field(default_factory=lambda: ["\n\n", "\n", ".", "?", "!", " ", ""])

    def _count(self, text: str) -> int:
        return token_counter.count(text)

    def split_text(self, text: str, source: str = "") -> list[Chunk]:
        return self._split(text, source, separators=self.SEPARATORS)

    def _split(self, text: str, source: str, separators: list[str]) -> list[Chunk]:
        final_chunks: list[Chunk] = []

        separator = separators[-1]
        for s in separators:
            if s == "":
                separator = s
                break
            if s in text:
                separator = s
                break

        if separator:
            splits = text.split(separator)
        else:
            splits = list(text)

        good_splits: list[str] = []
        for s in splits:
            if self._count(s) < self.chunk_size:
                good_splits.append(s)
            else:
                if good_splits:
                    merged = self._merge(good_splits, source)
                    final_chunks.extend(merged)
                    good_splits = []
                remaining = s
                while self._count(remaining) >= self.chunk_size:
                    chunk = remaining[: self.chunk_size]
                    final_chunks.append(
                        Chunk(content=chunk, metadata={"source": source})
                    )
                    remaining = remaining[self.chunk_size - self.chunk_overlap:]
                if remaining:
                    good_splits.append(remaining)

        if good_splits:
            merged = self._merge(good_splits, source)
            final_chunks.extend(merged)

        return final_chunks

    def _merge(self, splits: list[str], source: str) -> list[Chunk]:
        chunks: list[Chunk] = []
        current = ""
        for s in splits:
            if self._count(current) + self._count(s) + 1 > self.chunk_size:
                if current:
                    chunks.append(Chunk(content=current.strip(), metadata={"source": source}))
                    overlap_tokens = current.split()[-self.chunk_overlap:] if self.chunk_overlap else []
                    current = " ".join(overlap_tokens) + " " if overlap_tokens else ""
                current += s
            else:
                current = (current + " " + s).strip()
        if current:
            chunks.append(Chunk(content=current.strip(), metadata={"source": source}))
        return chunks



