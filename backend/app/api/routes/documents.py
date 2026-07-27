from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from loguru import logger
from pydantic import BaseModel

from app.core.auth import verify_jwt
from app.core.config import settings
from app.core.dependencies import get_document_service
from app.core.exceptions import DocumentNotFoundError
from app.core.security import MIME_MAGIC, matches_mime, validate_text_content, TEXT_EXTENSIONS
from app.services.document_service import DocumentService

router = APIRouter()

MAX_UPLOAD_BYTES = settings.max_upload_size_mb * 1024 * 1024

MIME_MAP = {
    ".pdf": "application/pdf",
    ".csv": "text/csv",
    ".txt": "text/plain",
    ".md": "text/markdown",
}


class DocumentResponse(BaseModel):
    id: str
    filename: str
    status: str
    chunks: int
    created_at: str
    error: str | None = None


class DeleteResponse(BaseModel):
    status: str
    id: str


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]


class BulkUploadError(BaseModel):
    filename: str | None = None
    error: str


class BulkUploadResponse(BaseModel):
    results: list[DocumentResponse]
    errors: list[BulkUploadError]
    total: int
    failed: int


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    doc_service: DocumentService = Depends(get_document_service),
    user_id: str = Depends(verify_jwt),
):
    ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename and "." in file.filename else ""
    if ext:
        ext = f".{ext}"
    if ext and ext not in doc_service.ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=422, detail=f"Extensión no soportada: {ext}")

    content = await file.read()

    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Archivo demasiado grande (máx {settings.max_upload_size_mb}MB)",
        )

    if content and ext in MIME_MAP:
        expected_mime = MIME_MAP[ext]
        if expected_mime in MIME_MAGIC:
            if not matches_mime(content, expected_mime):
                raise HTTPException(status_code=422, detail=f"Tipo MIME real no coincide con la extensión .{ext}")
        elif ext in TEXT_EXTENSIONS:
            valid, err = validate_text_content(content)
            if not valid:
                raise HTTPException(status_code=422, detail=err)

    result = await doc_service.upload(
        filename=file.filename or "unknown",
        content=content,
        user_id=user_id,
    )
    return DocumentResponse(**result)


@router.post("/upload/bulk", response_model=BulkUploadResponse)
async def upload_documents_bulk(
    files: list[UploadFile] = File(...),
    doc_service: DocumentService = Depends(get_document_service),
    user_id: str = Depends(verify_jwt),
):
    results = []
    errors = []
    for file in files:
        ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename and "." in file.filename else ""
        if ext:
            ext = f".{ext}"
        if ext and ext not in doc_service.ALLOWED_EXTENSIONS:
            msg = f"Extensión no soportada: {ext} para {file.filename}"
            errors.append({"filename": file.filename, "error": msg})
            logger.warning(f"Carga masiva omitida: {msg}")
            continue

        content = await file.read()
        if len(content) > MAX_UPLOAD_BYTES:
            msg = f"Archivo demasiado grande: {file.filename} ({len(content)} bytes, máx {MAX_UPLOAD_BYTES})"
            errors.append({"filename": file.filename, "error": msg})
            logger.warning(f"Carga masiva omitida: {msg}")
            continue

        try:
            result = await doc_service.upload(
                filename=file.filename or "desconocido",
                content=content,
                user_id=user_id,
            )
            results.append(DocumentResponse(**result))
        except Exception as e:
            msg = f"Error procesando {file.filename}: {e}"
            errors.append({"filename": file.filename, "error": str(e)})
            logger.warning(f"Carga masiva omitida: {msg}")

    if errors:
        logger.warning(f"Carga masiva completada con {len(errors)} errores y {len(results)} aciertos")

    return BulkUploadResponse(
        results=results,
        errors=[BulkUploadError(**e) for e in errors],
        total=len(results) + len(errors),
        failed=len(errors),
    )


@router.delete("/{doc_id}", response_model=DeleteResponse)
async def delete_document(
    doc_id: str,
    doc_service: DocumentService = Depends(get_document_service),
    user_id: str = Depends(verify_jwt),
):
    try:
        await doc_service.delete(doc_id, user_id)
        return DeleteResponse(status="deleted", id=doc_id)
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    doc_service: DocumentService = Depends(get_document_service),
    user_id: str = Depends(verify_jwt),
):
    docs, _ = await doc_service.list_documents(user_id=user_id)
    return DocumentListResponse(documents=docs)
