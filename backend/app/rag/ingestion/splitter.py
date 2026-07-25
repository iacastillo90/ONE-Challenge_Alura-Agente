import re
from dataclasses import dataclass, field


@dataclass
class Chunk:
    content: str
    metadata: dict


@dataclass
class SemanticChunker:
    chunk_size: int = 512
    chunk_overlap: int = 64

    SEPARATORS: list[str] = field(default_factory=lambda: ["\n\n", "\n", ".", "?", "!", " ", ""])

    def split_text(self, text: str, source: str = "") -> list[Chunk]:
        paragraphs = text.split("\n\n")
        chunks: list[Chunk] = []
        buffer = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if len(buffer) + len(para) < self.chunk_size:
                buffer = f"{buffer}\n\n{para}".strip()
                continue

            if buffer:
                chunks.append(Chunk(content=buffer, metadata={"source": source}))
                buffer = self._get_overlap(buffer)

            if len(para) > self.chunk_size:
                sub_chunks = self._split_long_paragraph(para, source)
                chunks.extend(sub_chunks)
            else:
                buffer = para

        if buffer:
            chunks.append(Chunk(content=buffer, metadata={"source": source}))

        return chunks

    def _split_long_paragraph(self, text: str, source: str) -> list[Chunk]:
        chunks: list[Chunk] = []
        buffer = ""

        segments = re.split(r"(?<=[.!?])\s+", text)
        for seg in segments:
            if len(buffer) + len(seg) < self.chunk_size:
                buffer = f"{buffer} {seg}".strip()
                continue

            if buffer:
                chunks.append(Chunk(content=buffer, metadata={"source": source}))
                buffer = self._get_overlap(buffer)

            buffer = seg

        if buffer:
            chunks.append(Chunk(content=buffer, metadata={"source": source}))

        return chunks

    def _get_overlap(self, text: str) -> str:
        words = text.split()
        if len(words) <= self.chunk_overlap:
            return ""
        return " ".join(words[-self.chunk_overlap:])
