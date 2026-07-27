import asyncio
from pathlib import Path

import fitz
import pandas as pd
from loguru import logger

from app.core.config import settings
from app.core.exceptions import DocumentProcessingError


class DocumentLoader:
    SUPPORTED_EXTENSIONS: set[str] = {".pdf", ".csv", ".txt", ".md"}
    MAX_CHARS = settings.max_extracted_chars

    async def load(self, file_path: str | Path, original_size: int = 0) -> str:
        path = Path(file_path)
        ext = path.suffix.lower()

        if ext not in self.SUPPORTED_EXTENSIONS:
            raise DocumentProcessingError(
                f"Unsupported format: {ext}. Supported: {self.SUPPORTED_EXTENSIONS}"
            )

        if ext == ".pdf":
            return await self._load_pdf(path)
        if ext == ".csv":
            return await self._load_csv(path)
        return await self._load_text(path)

    async def _load_pdf(self, path: Path) -> str:
        logger.info(f"Loading PDF: {path}")
        loop = asyncio.get_running_loop()
        try:
            def _read_pdf():
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

            result = await loop.run_in_executor(None, _read_pdf)
            if len(result) > self.MAX_CHARS:
                logger.warning(f"PDF text exceeds {self.MAX_CHARS} chars, truncating")
                result = result[: self.MAX_CHARS]
            return result
        except fitz.FileDataError as e:
            raise DocumentProcessingError(f"Invalid PDF file: {e}")

    async def _load_csv(self, path: Path) -> str:
        logger.info(f"Loading CSV: {path}")
        loop = asyncio.get_running_loop()
        try:
            def _read_csv():
                try:
                    return pd.read_csv(path, encoding="utf-8")
                except UnicodeDecodeError:
                    logger.warning("UTF-8 decode failed, trying latin1 for CSV")
                    return pd.read_csv(path, encoding="latin1")

            df = await loop.run_in_executor(None, _read_csv)

            rows = []
            for _, row in df.iterrows():
                row_text = " | ".join(
                    f"{col}: {val}" for col, val in row.items() if pd.notna(val)
                )
                rows.append(row_text)

            result = "\n".join(rows)
            if len(result) > self.MAX_CHARS:
                logger.warning(f"CSV text exceeds {self.MAX_CHARS} chars, truncating")
                result = result[: self.MAX_CHARS]
            return result
        except Exception as e:
            raise DocumentProcessingError(f"Failed to read CSV: {e}")

    async def _load_text(self, path: Path) -> str:
        logger.info(f"Loading text file: {path}")
        loop = asyncio.get_running_loop()

        def _read_text():
            try:
                return path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                return path.read_text(encoding="latin1")

        result = await loop.run_in_executor(None, _read_text)
        if len(result) > self.MAX_CHARS:
            logger.warning(f"Text file exceeds {self.MAX_CHARS} chars, truncating")
            result = result[: self.MAX_CHARS]
        return result
