"""Pluggable file storage backends.

Both backends expose an async interface. The Supabase client is
synchronous, so its network calls are offloaded to a worker thread and
bounded by ``settings.storage_timeout_seconds`` — this keeps the event
loop responsive and prevents indefinite hangs when the provider is slow.
Local disk I/O gets the same treatment: even "fast" blocking writes can
stall the loop under load or on network-mounted volumes.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)


async def _run_bounded(operation, *args) -> object:
    """Run a blocking operation in a thread with a hard timeout.

    On timeout the event loop is unblocked immediately; the worker thread
    may finish in the background but its result is discarded.
    """
    return await asyncio.wait_for(
        asyncio.to_thread(operation, *args),
        timeout=settings.storage_timeout_seconds,
    )


class StorageBackend(ABC):
    @abstractmethod
    async def upload(
        self, path: str, content: bytes, content_type: str = "application/octet-stream"
    ) -> str:
        """Upload file and return the storage path/key."""
        ...

    @abstractmethod
    async def download(self, path: str) -> bytes:
        """Download file content."""
        ...

    @abstractmethod
    async def delete(self, path: str) -> bool:
        """Delete a file. Returns True if deleted."""
        ...

    @abstractmethod
    async def exists(self, path: str) -> bool:
        """Check if file exists."""
        ...


class LocalStorage(StorageBackend):
    def __init__(self, base_dir: str | Path | None = None):
        self.base_dir = Path(base_dir or settings.upload_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _full(self, path: str) -> Path:
        return self.base_dir / path

    async def upload(
        self, path: str, content: bytes, content_type: str = "application/octet-stream"
    ) -> str:
        def _write() -> None:
            full_path = self._full(path)
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_bytes(content)

        await _run_bounded(_write)
        return path

    async def download(self, path: str) -> bytes:
        return await _run_bounded(self._full(path).read_bytes)

    async def delete(self, path: str) -> bool:
        try:
            return await _run_bounded(self._delete_sync, path)
        except FileNotFoundError:
            return False
        except TimeoutError:
            logger.error("Timed out deleting %s from local storage", path)
            return False

    def _delete_sync(self, path: str) -> bool:
        full_path = self._full(path)
        if full_path.exists():
            full_path.unlink()
            return True
        return False

    async def exists(self, path: str) -> bool:
        return await _run_bounded(lambda: self._full(path).exists())


class SupabaseStorage(StorageBackend):
    def __init__(self):
        from supabase import create_client

        self.client = create_client(settings.supabase_url, settings.supabase_key)
        self.bucket = settings.supabase_storage_bucket

    def _bucket(self):
        return self.client.storage.from_(self.bucket)

    async def upload(
        self, path: str, content: bytes, content_type: str = "application/octet-stream"
    ) -> str:
        await _run_bounded(
            lambda: self._bucket().upload(path, content, {"content-type": content_type})
        )
        return path

    async def download(self, path: str) -> bytes:
        return await _run_bounded(lambda: self._bucket().download(path))

    async def delete(self, path: str) -> bool:
        try:
            await _run_bounded(lambda: self._bucket().remove([path]))
            return True
        except TimeoutError:
            logger.error("Timed out deleting %s from Supabase", path)
            return False
        except Exception:
            logger.exception("Failed to delete %s from Supabase", path)
            return False

    async def exists(self, path: str) -> bool:
        try:
            # NOTE: preserved legacy semantics — any successful listing
            # (even empty) counts as "exists". See REFACTOR_CHANGELOG.md.
            await _run_bounded(lambda: self._bucket().list(str(Path(path).parent)))
            return True
        except Exception:
            return False


def get_storage() -> StorageBackend:
    """Return the appropriate storage backend based on config."""
    if settings.supabase_url and settings.supabase_key:
        return SupabaseStorage()
    return LocalStorage()
