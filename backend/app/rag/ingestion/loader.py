from pathlib import Path

import fitz
import pandas as pd
from loguru import logger

from app.core.exceptions import DocumentProcessingError


class DocumentLoader:
    SUPPORTED_EXTENSIONS = {".pdf", ".csv"}

    async def load(self, file_path: str | Path) -> str:
        path = Path(file_path)
        ext = path.suffix.lower()

        if ext not in self.SUPPORTED_EXTENSIONS:
            raise DocumentProcessingError(f"Unsupported format: {ext}. Supported: {self.SUPPORTED_EXTENSIONS}")

        if ext == ".pdf":
            return await self._load_pdf(path)
        return await self._load_csv(path)

    async def _load_pdf(self, path: Path) -> str:
        logger.info(f"Loading PDF: {path}")
        try:
            doc = fitz.open(path)
            pages = []
            for page_num, page in enumerate(doc, start=1):
                text = page.get_text()
                if text.strip():
                    pages.append(f"[Página {page_num}]\n{text}")
            doc.close()

            if not pages:
                raise DocumentProcessingError(f"No text extracted from PDF: {path}")

            return "\n\n".join(pages)
        except fitz.FileDataError as e:
            raise DocumentProcessingError(f"Invalid PDF file: {e}")

    async def _load_csv(self, path: Path) -> str:
        logger.info(f"Loading CSV: {path}")
        try:
            df = pd.read_csv(path, encoding="utf-8")
        except UnicodeDecodeError:
            df = pd.read_csv(path, encoding="latin1")

        rows = []
        for _, row in df.iterrows():
            row_text = " | ".join(f"{col}: {val}" for col, val in row.items() if pd.notna(val))
            rows.append(row_text)

        return "\n".join(rows)
