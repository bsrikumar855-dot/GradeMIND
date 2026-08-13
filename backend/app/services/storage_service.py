"""
GradeMIND Storage Service.
Local filesystem abstraction for managing uploaded answer sheets, question papers,
answer keys, OCR outputs, evaluation outputs, and generated reports.
"""

import os
import uuid
import shutil
import logging
from pathlib import Path
from typing import Optional

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


def init_storage() -> None:
    """Create all required storage directories if they do not exist."""
    for dir_name, dir_path in STORAGE_DIRS.items():
        os.makedirs(dir_path, exist_ok=True)
        logger.info(f"Storage directory verified: {dir_path}")


def validate_file(filename: str, file_size: int) -> Optional[str]:
    """
    Validate an uploaded file against allowed extensions and size limits.

    Args:
        filename: Original filename from the upload.
        file_size: Size of the file content in bytes.

    Returns:
        None if valid, or an error message string if invalid.
    """
    if not filename:
        return "Filename is empty."

    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return f"File type '{ext}' is not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"

    if file_size > MAX_FILE_SIZE_BYTES:
        size_mb = file_size / (1024 * 1024)
        return f"File size ({size_mb:.1f} MB) exceeds the maximum allowed size of 20 MB."

    return None


def generate_file_path(
    category: str,
    exam_id: str,
    identifier: str,
    original_filename: str
) -> str:
    """
    Generate a structured, unique file path for storage.

    Directory structure: storage/{category}/{exam_id}/{identifier}_{uuid_suffix}.{ext}

    Args:
        category: Storage category key (e.g., 'answer_sheets', 'ocr_outputs').
        exam_id: UUID string of the parent exam.
        identifier: Student roll number or submission identifier.
        original_filename: Original uploaded filename (used for extension).

    Returns:
        Absolute file path string.
    """
    base_dir = STORAGE_DIRS.get(category)
    if not base_dir:
        raise ValueError(f"Unknown storage category: {category}")

    ext = os.path.splitext(original_filename)[1].lower()
    unique_suffix = uuid.uuid4().hex[:8]
    safe_identifier = identifier.replace("/", "_").replace("\\", "_").replace(" ", "_")
    filename = f"{safe_identifier}_{unique_suffix}{ext}"

    # Create exam-specific subdirectory
    exam_dir = os.path.join(base_dir, str(exam_id))
    os.makedirs(exam_dir, exist_ok=True)

    return os.path.join(exam_dir, filename)


class UploadTooLarge(Exception):
    """An upload exceeded MAX_FILE_SIZE_BYTES.

    Carries the number of bytes actually observed. When the limit is hit
    mid-stream this is the count at the point of abort, not the true size —
    the whole point is that we stop reading rather than find out.
    """

    def __init__(self, observed_bytes: int, limit_bytes: int = MAX_FILE_SIZE_BYTES):
        self.observed_bytes = observed_bytes
        self.limit_bytes = limit_bytes
        super().__init__(
            f"Upload exceeds the maximum allowed size of "
            f"{limit_bytes / (1024 * 1024):.0f} MB."
        )


def validate_filename(
    filename: str, allowed_extensions: Optional[set] = None
) -> Optional[str]:
    """Extension/name check only — no size component.

    Split out from validate_file() so it can run *before* any bytes are read.
    """
    allowed = allowed_extensions if allowed_extensions is not None else ALLOWED_EXTENSIONS

    if not filename:
        return "Filename is empty."

    ext = os.path.splitext(filename)[1].lower()
    if ext not in allowed:
        return f"File type '{ext}' is not allowed. Allowed types: {', '.join(sorted(allowed))}"

    return None


def declared_size_exceeds_limit(content_length: Optional[int]) -> bool:
    """Check a client-declared Content-Length against the cap.

    Advisory only: Content-Length is client-supplied and may be absent, wrong,
    or a lie. It is a cheap way to reject an oversized upload before reading a
    single byte; stream_upload_to_file() is what actually enforces the limit.
    """
    return content_length is not None and content_length > MAX_FILE_SIZE_BYTES


async def stream_upload_to_file(
    upload,
    destination_path: str,
    max_bytes: int = MAX_FILE_SIZE_BYTES,
    chunk_size: int = 1024 * 1024,
) -> int:
    """Stream an UploadFile to disk, aborting past the cap.

    Peak memory is one chunk, not one file. Previously every upload path did
    ``content = await file.read()`` and *then* checked the length, so a client
    could force the process to buffer an arbitrarily large body before it was
    rejected (D12). A partial file is removed on abort.

    Returns the number of bytes written. Raises UploadTooLarge if the stream
    exceeds max_bytes.
    """
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
        # Includes UploadTooLarge and client disconnects. Never leave a partial
        # file behind for a later stage to treat as a complete answer sheet.
        _remove_partial(destination_path)
        raise

    logger.info("File streamed: %s (%d bytes)", destination_path, written)
    return written


def _remove_partial(path: str) -> None:
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        # Losing the cleanup must not mask the original failure, but a stray
        # partial file is worth knowing about.
        logger.exception("Failed to remove partial upload: %s", path)


async def save_file(file_content: bytes, destination_path: str) -> str:
    """
    Write file content to the designated path on disk.

    Args:
        file_content: Raw bytes of the uploaded file.
        destination_path: Full path where the file should be saved.

    Returns:
        The absolute path where the file was saved.
    """
    # Ensure parent directory exists
    os.makedirs(os.path.dirname(destination_path), exist_ok=True)

    with open(destination_path, "wb") as f:
        f.write(file_content)

    logger.info(f"File saved: {destination_path} ({len(file_content)} bytes)")
    return destination_path


def save_text_file(content: str, destination_path: str) -> str:
    """
    Write text content (e.g., JSON output from OCR/evaluation) to disk.

    Args:
        content: String content to save.
        destination_path: Full path where the file should be saved.

    Returns:
        The absolute path where the file was saved.
    """
    os.makedirs(os.path.dirname(destination_path), exist_ok=True)

    with open(destination_path, "w", encoding="utf-8") as f:
        f.write(content)

    logger.info(f"Text file saved: {destination_path} ({len(content)} chars)")
    return destination_path


def read_file(file_path: str) -> Optional[bytes]:
    """
    Read and return file content from disk.

    Args:
        file_path: Absolute path to the file.

    Returns:
        File bytes, or None if the file does not exist.
    """
    if not os.path.exists(file_path):
        logger.warning(f"File not found: {file_path}")
        return None

    with open(file_path, "rb") as f:
        return f.read()


def delete_file(file_path: str) -> bool:
    """
    Delete a file from local storage.

    Args:
        file_path: Absolute path to the file.

    Returns:
        True if deleted, False if the file did not exist.
    """
    if not os.path.exists(file_path):
        logger.warning(f"Cannot delete — file not found: {file_path}")
        return False

    os.remove(file_path)
    logger.info(f"File deleted: {file_path}")
    return True


def get_relative_path(absolute_path: str) -> str:
    """
    Convert an absolute storage path to a path relative to the storage root.
    Useful for storing portable references in the database.

    Args:
        absolute_path: The full filesystem path.

    Returns:
        Path relative to the storage root directory.
    """
    try:
        return os.path.relpath(absolute_path, STORAGE_ROOT)
    except ValueError:
        # On Windows, relpath fails across drives
        return absolute_path
