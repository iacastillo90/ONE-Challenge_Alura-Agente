from fastapi import APIRouter, Depends, UploadFile, File
from pydantic import BaseModel

from app.core.dependencies import get_document_service
from app.core.exceptions import DocumentNotFoundError
from app.services.document_service import DocumentService

router = APIRouter()


class DocumentResponse(BaseModel):
    id: str
    filename: str
    status: str
    chunks: int
    created_at: str
    error: str | None = None


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    doc_service: DocumentService = Depends(get_document_service),
):
    content = await file.read()
    result = await doc_service.upload(filename=file.filename or "unknown", content=content)
    return DocumentResponse(**result)


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: str,
    doc_service: DocumentService = Depends(get_document_service),
):
    try:
        await doc_service.delete(doc_id)
        return {"status": "deleted", "id": doc_id}
    except DocumentNotFoundError as e:
        return {"status": "not_found", "message": str(e)}


@router.get("")
async def list_documents(
    doc_service: DocumentService = Depends(get_document_service),
):
    docs = await doc_service.list_documents()
    return {"documents": docs}
