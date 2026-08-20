"""
GradeMIND Storage Service.
Storage abstraction for managing uploaded answer sheets, question papers,
answer keys, OCR outputs, evaluation outputs, and generated reports.
Supports local filesystem and prepares for S3/MinIO.
"""

import os
import uuid
import logging
from typing import Optional
from abc import ABC, abstractmethod

from app.core.config import BASE_DIR

logger = logging.getLogger("GradeMIND.StorageService")

# Root storage directory (sibling to backend/app)
STORAGE_ROOT = os.path.join(BASE_DIR, "storage")

# Subdirectory layout
STORAGE_DIRS = {
    "answer_sheets": os.path.join(STORAGE_ROOT, "answer_sheets"),
    "question_papers": os.path.join(STORAGE_ROOT, "question_papers"),
    "answer_keys": os.path.join(STORAGE_ROOT, "answer_keys"),
    "reports": os.path.join(STORAGE_ROOT, "reports"),
    "ocr_outputs": os.path.join(STORAGE_ROOT, "ocr_outputs"),
    "evaluation_outputs": os.path.join(STORAGE_ROOT, "evaluation_outputs"),
}

# Allowed file extensions and max size
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}
MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB

class UploadTooLarge(Exception):
    def __init__(self, observed_bytes: int, limit_bytes: int = MAX_FILE_SIZE_BYTES):
        self.observed_bytes = observed_bytes
        self.limit_bytes = limit_bytes
        super().__init__(
            f"Upload exceeds the maximum allowed size of "
            f"{limit_bytes / (1024 * 1024):.0f} MB."
        )


class BaseStorageProvider(ABC):
    @abstractmethod
    def init_storage(self) -> None:
        pass

    @abstractmethod
    def generate_file_path(self, category: str, exam_id: str, identifier: str, original_filename: str) -> str:
        pass

    @abstractmethod
    async def stream_upload_to_file(self, upload, destination_path: str, max_bytes: int = MAX_FILE_SIZE_BYTES, chunk_size: int = 1024 * 1024) -> int:
        pass

    @abstractmethod
    async def save_file(self, file_content: bytes, destination_path: str) -> str:
        pass

    @abstractmethod
    def save_text_file(self, content: str, destination_path: str) -> str:
        pass

    @abstractmethod
    def read_file(self, file_path: str) -> Optional[bytes]:
        pass

    @abstractmethod
    def delete_file(self, file_path: str) -> bool:
        pass

    @abstractmethod
    def get_relative_path(self, absolute_path: str) -> str:
        pass

    @abstractmethod
    def file_exists(self, file_path: str) -> bool:
        pass


class LocalStorageProvider(BaseStorageProvider):
    def init_storage(self) -> None:
        for dir_name, dir_path in STORAGE_DIRS.items():
            os.makedirs(dir_path, exist_ok=True)
            logger.info(f"Storage directory verified: {dir_path}")

    def generate_file_path(self, category: str, exam_id: str, identifier: str, original_filename: str) -> str:
        base_dir = STORAGE_DIRS.get(category)
        if not base_dir:
            raise ValueError(f"Unknown storage category: {category}")

        ext = os.path.splitext(original_filename)[1].lower()
        unique_suffix = uuid.uuid4().hex[:8]
        safe_identifier = identifier.replace("/", "_").replace("\\", "_").replace(" ", "_")
        filename = f"{safe_identifier}_{unique_suffix}{ext}"

        exam_dir = os.path.join(base_dir, str(exam_id))
        os.makedirs(exam_dir, exist_ok=True)

        return os.path.join(exam_dir, filename)

    async def stream_upload_to_file(self, upload, destination_path: str, max_bytes: int = MAX_FILE_SIZE_BYTES, chunk_size: int = 1024 * 1024) -> int:
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
        written = 0
        try:
            with open(destination_path, "wb") as out:
                while True:
                    chunk = await upload.read(chunk_size)
                    if not chunk:
                        break

                    written += len(chunk)
                    if written > max_bytes:
                        raise UploadTooLarge(observed_bytes=written, limit_bytes=max_bytes)

                    out.write(chunk)
        except BaseException:
            self._remove_partial(destination_path)
            raise

        logger.info("File streamed: %s (%d bytes)", destination_path, written)
        return written

    def _remove_partial(self, path: str) -> None:
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError:
            logger.exception("Failed to remove partial upload: %s", path)

    async def save_file(self, file_content: bytes, destination_path: str) -> str:
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
        with open(destination_path, "wb") as f:
            f.write(file_content)
        logger.info(f"File saved: {destination_path} ({len(file_content)} bytes)")
        return destination_path

    def save_text_file(self, content: str, destination_path: str) -> str:
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
        with open(destination_path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"Text file saved: {destination_path} ({len(content)} chars)")
        return destination_path

    def read_file(self, file_path: str) -> Optional[bytes]:
        if not os.path.exists(file_path):
            return None
        with open(file_path, "rb") as f:
            return f.read()

    def delete_file(self, file_path: str) -> bool:
        if not os.path.exists(file_path):
            return False
        os.remove(file_path)
        return True

    def get_relative_path(self, absolute_path: str) -> str:
        try:
            return os.path.relpath(absolute_path, STORAGE_ROOT)
        except ValueError:
            return absolute_path

    def file_exists(self, file_path: str) -> bool:
        return os.path.exists(file_path)


# Global provider instance
# If S3 is configured, we would swap this out here
storage_provider: BaseStorageProvider = LocalStorageProvider()

# Validation helpers
def validate_file(filename: str, file_size: int) -> Optional[str]:
    if not filename:
        return "Filename is empty."
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return f"File type '{ext}' is not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
    if file_size > MAX_FILE_SIZE_BYTES:
        size_mb = file_size / (1024 * 1024)
        return f"File size ({size_mb:.1f} MB) exceeds the maximum allowed size of 20 MB."
    return None

def validate_filename(filename: str, allowed_extensions: Optional[set] = None) -> Optional[str]:
    allowed = allowed_extensions if allowed_extensions is not None else ALLOWED_EXTENSIONS
    if not filename:
        return "Filename is empty."
    ext = os.path.splitext(filename)[1].lower()
    if ext not in allowed:
        return f"File type '{ext}' is not allowed. Allowed types: {', '.join(sorted(allowed))}"
    return None

def declared_size_exceeds_limit(content_length: Optional[int]) -> bool:
    return content_length is not None and content_length > MAX_FILE_SIZE_BYTES

# Backward compatibility wrappers
def init_storage() -> None:
    storage_provider.init_storage()

def generate_file_path(category: str, exam_id: str, identifier: str, original_filename: str) -> str:
    return storage_provider.generate_file_path(category, exam_id, identifier, original_filename)

async def stream_upload_to_file(upload, destination_path: str, max_bytes: int = MAX_FILE_SIZE_BYTES, chunk_size: int = 1024 * 1024) -> int:
    return await storage_provider.stream_upload_to_file(upload, destination_path, max_bytes, chunk_size)

async def save_file(file_content: bytes, destination_path: str) -> str:
    return await storage_provider.save_file(file_content, destination_path)

def save_text_file(content: str, destination_path: str) -> str:
    return storage_provider.save_text_file(content, destination_path)

def read_file(file_path: str) -> Optional[bytes]:
    return storage_provider.read_file(file_path)

def delete_file(file_path: str) -> bool:
    return storage_provider.delete_file(file_path)

def get_relative_path(absolute_path: str) -> str:
    return storage_provider.get_relative_path(absolute_path)

def file_exists(file_path: str) -> bool:
    return storage_provider.file_exists(file_path)
