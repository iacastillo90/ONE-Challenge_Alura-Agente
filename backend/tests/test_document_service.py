from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import DocumentNotFoundError, DocumentProcessingError
from app.services.document_service import DocumentService


def _make_mock_doc(
    doc_id: str = "doc-123",
    user_id: str = "user-abc",
    filename: str = "test.txt",
    status: str = "processing",
    chunks: int = 0,
    file_size: int = 100,
    error: str | None = None,
):
    doc = MagicMock()
    doc.id = doc_id
    doc.user_id = user_id
    doc.filename = filename
    doc.status = status
    doc.chunks = chunks
    doc.file_size = file_size
    doc.created_at = datetime.now(UTC)
    doc.error = error
    return doc


@pytest.fixture
def mock_vector_store():
    store = AsyncMock()
    return store


@pytest.fixture
def mock_storage():
    storage = AsyncMock()
    storage.save.return_value = "/tmp/uploads/documents/user-abc/doc-123.txt"
    return storage


@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.get = AsyncMock()
    session.execute = AsyncMock()
    session.delete = AsyncMock()
    return session


@pytest.fixture
def mock_task_queue():
    queue = AsyncMock()
    queue.enqueue = AsyncMock(return_value="job-123")
    return queue


@pytest.fixture
def doc_service(mock_vector_store, mock_storage):
    with patch("app.services.document_service.get_storage_backend", return_value=mock_storage):
        yield DocumentService(vector_store=mock_vector_store)


@pytest.mark.asyncio
async def test_upload_txt_file(mock_vector_store, mock_storage, mock_db_session, mock_task_queue):
    with (
        patch("app.services.document_service.get_storage_backend", return_value=mock_storage),
        patch("app.services.document_service.async_session_factory") as mock_sf,
        patch("app.services.document_service.get_task_queue", return_value=mock_task_queue),
        patch("app.services.document_service.DOCUMENTS_UPLOADED") as mock_metrics,
    ):
        doc_service = DocumentService(vector_store=mock_vector_store)
        mock_sf.return_value.__aenter__.return_value = mock_db_session
        mock_db_session.get.return_value = _make_mock_doc()

        result = await doc_service.upload(
            filename="test.txt",
            content=b"contenido de prueba",
            user_id="user-abc",
        )

        assert result["filename"] == "test.txt"
        assert result["status"] == "processing"
        assert result["file_size"] == 100
        assert isinstance(result["id"], str)
        assert isinstance(result["created_at"], str)
        mock_storage.save.assert_awaited_once()
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_awaited_once()
        mock_task_queue.enqueue.assert_awaited_once()
        call_kwargs = mock_task_queue.enqueue.await_args.kwargs
        assert call_kwargs["user_id"] == "user-abc"
        assert call_kwargs["file_size"] == len(b"contenido de prueba")
        assert call_kwargs["doc_id"] is not None
        assert call_kwargs["storage_key"] is not None
        assert call_kwargs["ext"] == ".txt"
        assert call_kwargs["filename"] == "test.txt"
        mock_metrics.labels.assert_called_once_with(status="processing")
        mock_metrics.labels.return_value.inc.assert_called_once()


@pytest.mark.asyncio
async def test_upload_pdf_file(mock_vector_store, mock_storage, mock_db_session, mock_task_queue):
    with (
        patch("app.services.document_service.get_storage_backend", return_value=mock_storage),
        patch("app.services.document_service.async_session_factory") as mock_sf,
        patch("app.services.document_service.get_task_queue", return_value=mock_task_queue),
        patch("app.services.document_service.DOCUMENTS_UPLOADED"),
    ):
        doc_service = DocumentService(vector_store=mock_vector_store)
        mock_sf.return_value.__aenter__.return_value = mock_db_session
        mock_db_session.get.return_value = _make_mock_doc(filename="report.pdf")

        result = await doc_service.upload(
            filename="report.pdf",
            content=b"%PDF-1.4 fake pdf content",
            user_id="user-abc",
        )

        assert result["filename"] == "report.pdf"
        mock_storage.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_upload_rejects_invalid_extension(doc_service):
    with pytest.raises(DocumentProcessingError, match="Formato no soportado: .exe"):
        await doc_service.upload(
            filename="malware.exe",
            content=b"fake exe content",
            user_id="user-abc",
        )


@pytest.mark.asyncio
async def test_upload_rejects_unknown_extension(doc_service):
    with pytest.raises(DocumentProcessingError, match="Formato no soportado: .xyz"):
        await doc_service.upload(
            filename="data.xyz",
            content=b"some content",
            user_id="user-abc",
        )


@pytest.mark.asyncio
async def test_upload_accepts_large_content(mock_vector_store, mock_storage, mock_db_session, mock_task_queue):
    large_content = b"x" * (500 * 1024)

    with (
        patch("app.services.document_service.get_storage_backend", return_value=mock_storage),
        patch("app.services.document_service.async_session_factory") as mock_sf,
        patch("app.services.document_service.get_task_queue", return_value=mock_task_queue),
        patch("app.services.document_service.DOCUMENTS_UPLOADED"),
    ):
        doc_service = DocumentService(vector_store=mock_vector_store)
        mock_sf.return_value.__aenter__.return_value = mock_db_session
        mock_db_session.get.return_value = _make_mock_doc(filename="large.txt", file_size=len(large_content))

        result = await doc_service.upload(
            filename="large.txt",
            content=large_content,
            user_id="user-abc",
        )

        assert result["filename"] == "large.txt"
        mock_storage.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_upload_scans_for_secrets(doc_service, mock_vector_store, mock_storage, mock_db_session, mock_task_queue):
    with (
        patch("app.services.document_service.get_storage_backend", return_value=mock_storage),
        patch("app.services.document_service.async_session_factory") as mock_sf,
        patch("app.services.document_service.get_task_queue", return_value=mock_task_queue),
        patch("app.services.document_service.DOCUMENTS_UPLOADED"),
        patch("app.services.document_service.detect_secrets") as mock_detect,
    ):
        mock_sf.return_value.__aenter__.return_value = mock_db_session
        mock_db_session.get.return_value = _make_mock_doc(filename="credentials.txt")
        mock_detect.return_value = ["Possible secret: API key pattern"]

        result = await doc_service.upload(
            filename="credentials.txt",
            content=b"api_key = sk-12345678901234567890",
            user_id="user-abc",
        )

        assert result["filename"] == "credentials.txt"
        mock_detect.assert_called_once()


@pytest.mark.asyncio
async def test_upload_binary_content_rejected(doc_service):
    with pytest.raises(DocumentProcessingError, match="Formato no soportado: .bin"):
        await doc_service.upload(
            filename="binary.bin",
            content=b"\x00\x01\x02\x03\xff\xfe",
            user_id="user-abc",
        )


@pytest.mark.asyncio
async def test_list_documents(doc_service, mock_vector_store, mock_db_session):
    docs = [
        _make_mock_doc(doc_id="doc-1", filename="a.txt", chunks=5),
        _make_mock_doc(doc_id="doc-2", filename="b.pdf", chunks=3),
    ]

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = docs
    mock_db_session.execute.return_value = mock_result

    mock_count = MagicMock()
    mock_count.scalar.return_value = 2
    mock_db_session.execute = AsyncMock(side_effect=[mock_count, mock_result])

    with patch("app.services.document_service.async_session_factory") as mock_sf:
        mock_sf.return_value.__aenter__.return_value = mock_db_session

        result_list, total = await doc_service.list_documents(user_id="user-abc")

        assert total == 2
        assert len(result_list) == 2
        assert result_list[0]["filename"] == "a.txt"
        assert result_list[1]["filename"] == "b.pdf"
        assert result_list[0]["chunks"] == 5
        assert result_list[1]["chunks"] == 3


@pytest.mark.asyncio
async def test_list_documents_empty(doc_service, mock_vector_store, mock_db_session):
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db_session.execute.return_value = mock_result

    mock_count = MagicMock()
    mock_count.scalar.return_value = 0
    mock_db_session.execute = AsyncMock(side_effect=[mock_count, mock_result])

    with patch("app.services.document_service.async_session_factory") as mock_sf:
        mock_sf.return_value.__aenter__.return_value = mock_db_session

        result_list, total = await doc_service.list_documents(user_id="user-empty")

        assert total == 0
        assert result_list == []


@pytest.mark.asyncio
async def test_list_documents_respects_limit(doc_service, mock_vector_store, mock_db_session):
    docs = [_make_mock_doc(doc_id="doc-1")]

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = docs
    mock_db_session.execute.return_value = mock_result

    mock_count = MagicMock()
    mock_count.scalar.return_value = 10
    mock_db_session.execute = AsyncMock(side_effect=[mock_count, mock_result])

    with patch("app.services.document_service.async_session_factory") as mock_sf:
        mock_sf.return_value.__aenter__.return_value = mock_db_session

        result_list, total = await doc_service.list_documents(user_id="user-abc", limit=1)

        assert len(result_list) == 1
        assert total == 10


@pytest.mark.asyncio
async def test_delete_document(doc_service, mock_vector_store, mock_storage, mock_db_session):
    mock_db_session.get.return_value = _make_mock_doc(doc_id="doc-123", user_id="user-abc")

    with (
        patch("app.services.document_service.get_storage_backend", return_value=mock_storage),
        patch("app.services.document_service.async_session_factory") as mock_sf,
    ):
        mock_sf.return_value.__aenter__.return_value = mock_db_session

        await doc_service.delete(doc_id="doc-123", user_id="user-abc")

        assert mock_storage.delete.await_count == len(DocumentService.ALLOWED_EXTENSIONS)
        mock_vector_store.delete_document.assert_awaited_once_with("doc-123")
        mock_db_session.get.assert_awaited()
        mock_db_session.delete.assert_awaited_once()
        mock_db_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_document_not_found(doc_service, mock_vector_store, mock_db_session):
    mock_db_session.get.return_value = None

    with (
        patch("app.services.document_service.get_storage_backend") as mock_storage_fn,
        patch("app.services.document_service.async_session_factory") as mock_sf,
    ):
        mock_sf.return_value.__aenter__.return_value = mock_db_session
        mock_storage = AsyncMock()
        mock_storage_fn.return_value = mock_storage

        with pytest.raises(DocumentNotFoundError, match="Documento no encontrado: doc-404"):
            await doc_service.delete(doc_id="doc-404", user_id="user-abc")


@pytest.mark.asyncio
async def test_delete_other_users_document_raises(doc_service, mock_vector_store, mock_storage, mock_db_session):
    mock_db_session.get.return_value = _make_mock_doc(doc_id="doc-123", user_id="other-user")

    with (
        patch("app.services.document_service.get_storage_backend", return_value=mock_storage),
        patch("app.services.document_service.async_session_factory") as mock_sf,
    ):
        mock_sf.return_value.__aenter__.return_value = mock_db_session

        with pytest.raises(DocumentNotFoundError, match="Documento no encontrado: doc-123"):
            await doc_service.delete(doc_id="doc-123", user_id="user-abc")


@pytest.mark.asyncio
async def test_upload_doc_not_found_in_get_doc(doc_service, mock_vector_store, mock_storage, mock_db_session, mock_task_queue):
    with (
        patch("app.services.document_service.get_storage_backend", return_value=mock_storage),
        patch("app.services.document_service.async_session_factory") as mock_sf,
        patch("app.services.document_service.get_task_queue", return_value=mock_task_queue),
        patch("app.services.document_service.DOCUMENTS_UPLOADED"),
    ):
        mock_sf.return_value.__aenter__.return_value = mock_db_session
        mock_db_session.get.return_value = None

        with pytest.raises(DocumentNotFoundError):
            await doc_service.upload(
                filename="test.txt",
                content=b"content",
                user_id="user-abc",
            )

