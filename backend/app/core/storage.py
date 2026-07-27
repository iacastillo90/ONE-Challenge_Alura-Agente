from abc import ABC, abstractmethod
from pathlib import Path

from loguru import logger

from app.core.config import settings
from app.core.exceptions import StorageError


class StorageBackend(ABC):
    @abstractmethod
    async def save(self, path: str, content: bytes) -> str: ...

    @abstractmethod
    async def read(self, path: str) -> bytes: ...

    @abstractmethod
    async def delete(self, path: str): ...

    @abstractmethod
    async def exists(self, path: str) -> bool: ...


class LocalStorage(StorageBackend):
    def __init__(self, base_path: Path | str):
        self._base = Path(base_path).resolve()
        self._base.mkdir(parents=True, exist_ok=True)
        logger.info(f"Local storage initialized at {self._base}")

    def _resolve(self, path: str) -> Path:
        p = (self._base / path).resolve()
        if not str(p).startswith(str(self._base)):
            raise StorageError("Path traversal detected")
        return p

    async def save(self, path: str, content: bytes) -> str:
        fp = self._resolve(path)
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_bytes(content)
        return str(fp)

    async def read(self, path: str) -> bytes:
        return self._resolve(path).read_bytes()

    async def delete(self, path: str):
        self._resolve(path).unlink(missing_ok=True)

    async def exists(self, path: str) -> bool:
        return self._resolve(path).exists()


class S3Storage(StorageBackend):
    def __init__(self):
        import aioboto3

        self._session = aioboto3.Session(
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
        )
        self._endpoint = settings.s3_endpoint_url or None
        self._bucket = settings.s3_bucket
        self._bucket_ready = False
        logger.info(f"S3 storage initialized: bucket={self._bucket} endpoint={self._endpoint}")

    async def _ensure_bucket(self) -> None:
        """Create the bucket on first use if it does not exist (MinIO-friendly)."""
        if self._bucket_ready:
            return
        async with self._session.client("s3", endpoint_url=self._endpoint) as client:
            try:
                await client.head_bucket(Bucket=self._bucket)
            except Exception:
                try:
                    await client.create_bucket(Bucket=self._bucket)
                    logger.info(f"Created object storage bucket: {self._bucket}")
                except Exception as exc:
                    # Race with another worker or already-owned bucket — tolerate.
                    logger.debug(f"Bucket ensure note for {self._bucket}: {exc}")
        self._bucket_ready = True

    async def save(self, path: str, content: bytes) -> str:
        await self._ensure_bucket()
        async with self._session.client("s3", endpoint_url=self._endpoint) as client:
            await client.put_object(Bucket=self._bucket, Key=path, Body=content)
        return path

    async def read(self, path: str) -> bytes:
        async with self._session.client("s3", endpoint_url=self._endpoint) as client:
            resp = await client.get_object(Bucket=self._bucket, Key=path)
            return await resp["Body"].read()

    async def delete(self, path: str):
        async with self._session.client("s3", endpoint_url=self._endpoint) as client:
            await client.delete_object(Bucket=self._bucket, Key=path)

    async def exists(self, path: str) -> bool:
        async with self._session.client("s3", endpoint_url=self._endpoint) as client:
            try:
                await client.head_object(Bucket=self._bucket, Key=path)
                return True
            except Exception:
                return False


UPLOAD_DIR = Path("./uploads")


def get_storage_backend() -> StorageBackend:
    if settings.storage_backend == "s3":
        return S3Storage()
    return LocalStorage(UPLOAD_DIR)
