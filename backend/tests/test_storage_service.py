"""
Unit tests for app.services.storage_service — previously had zero dedicated
test coverage (only indirectly exercised through submission-upload
integration tests). Covers validation, path generation, and file I/O
directly against a real temp filesystem.
"""

import os

import pytest

from app.services import storage_service


# ─────────────────────────────────────────────────────────────────────────
# validate_file
# ─────────────────────────────────────────────────────────────────────────

class TestValidateFile:
    def test_empty_filename_rejected(self):
        assert storage_service.validate_file("", 100) == "Filename is empty."

    def test_disallowed_extension_rejected(self):
        error = storage_service.validate_file("notes.docx", 100)
        assert error is not None
        assert "not allowed" in error.lower()

    def test_oversized_file_rejected(self):
        error = storage_service.validate_file("sheet.pdf", storage_service.MAX_FILE_SIZE_BYTES + 1)
        assert error is not None
        assert "exceeds" in error.lower()

    def test_valid_pdf_accepted(self):
        assert storage_service.validate_file("sheet.pdf", 1024) is None

    def test_valid_png_at_exact_size_limit_accepted(self):
        assert storage_service.validate_file("sheet.png", storage_service.MAX_FILE_SIZE_BYTES) is None

    def test_case_insensitive_extension(self):
        assert storage_service.validate_file("SHEET.PDF", 1024) is None


# ─────────────────────────────────────────────────────────────────────────
# generate_file_path
# ─────────────────────────────────────────────────────────────────────────

class TestGenerateFilePath:
    def test_unknown_category_raises(self):
        with pytest.raises(ValueError, match="Unknown storage category"):
            storage_service.generate_file_path("bogus_category", "exam1", "student1", "sheet.pdf")

    def test_path_contains_category_and_exam_id(self):
        path = storage_service.generate_file_path("answer_sheets", "exam-123", "CS001", "sheet.pdf")
        normalized = path.replace("\\", "/")
        assert "answer_sheets" in normalized
        assert "exam-123" in normalized
        assert normalized.endswith(".pdf")

    def test_identifier_is_filesystem_sanitized(self):
        """Roll numbers containing slashes/spaces must not create nested directories."""
        path = storage_service.generate_file_path(
            "answer_sheets", "exam-1", "CS 001/A\\B", "sheet.pdf"
        )
        filename = os.path.basename(path)
        assert "/" not in filename
        assert "\\" not in filename
        assert filename.startswith("CS_001_A_B_")

    def test_paths_are_unique_for_same_inputs(self):
        """Two calls with identical inputs must not collide (random suffix)."""
        path1 = storage_service.generate_file_path("answer_sheets", "exam-1", "CS001", "sheet.pdf")
        path2 = storage_service.generate_file_path("answer_sheets", "exam-1", "CS001", "sheet.pdf")
        assert path1 != path2

    def test_extension_preserved_from_original_filename(self):
        path = storage_service.generate_file_path("answer_keys", "exam-1", "key", "rubric.JSON")
        assert path.lower().endswith(".json")

    def test_creates_exam_subdirectory(self, tmp_path, monkeypatch):
        monkeypatch.setitem(storage_service.STORAGE_DIRS, "answer_sheets", str(tmp_path / "answer_sheets"))
        path = storage_service.generate_file_path("answer_sheets", "exam-xyz", "CS001", "sheet.pdf")
        assert os.path.isdir(os.path.dirname(path))


# ─────────────────────────────────────────────────────────────────────────
# save_file / save_text_file / read_file / delete_file
# ─────────────────────────────────────────────────────────────────────────

class TestFileIO:
    @pytest.mark.asyncio
    async def test_save_and_read_file_roundtrip(self, tmp_path):
        dest = str(tmp_path / "nested" / "sheet.pdf")
        content = b"%PDF-1.4\nsome binary content"

        saved_path = await storage_service.save_file(content, dest)
        assert saved_path == dest
        assert os.path.exists(dest)

        read_back = storage_service.read_file(dest)
        assert read_back == content

    def test_save_text_file_and_read_back(self, tmp_path):
        dest = str(tmp_path / "reports" / "report.json")
        storage_service.save_text_file('{"key": "value"}', dest)

        assert os.path.exists(dest)
        with open(dest, "r", encoding="utf-8") as f:
            assert f.read() == '{"key": "value"}'

    def test_read_nonexistent_file_returns_none(self):
        assert storage_service.read_file("/nonexistent/path/file.pdf") is None

    def test_delete_existing_file_returns_true(self, tmp_path):
        target = tmp_path / "to_delete.pdf"
        target.write_bytes(b"data")
        assert storage_service.delete_file(str(target)) is True
        assert not target.exists()

    def test_delete_nonexistent_file_returns_false(self):
        assert storage_service.delete_file("/nonexistent/path/file.pdf") is False


# ─────────────────────────────────────────────────────────────────────────
# get_relative_path
# ─────────────────────────────────────────────────────────────────────────

class TestGetRelativePath:
    def test_path_under_storage_root_made_relative(self):
        absolute = os.path.join(storage_service.STORAGE_ROOT, "answer_sheets", "exam1", "sheet.pdf")
        relative = storage_service.get_relative_path(absolute)
        assert not os.path.isabs(relative)
        assert relative == os.path.join("answer_sheets", "exam1", "sheet.pdf")

    def test_unrelated_absolute_path_falls_back_gracefully(self):
        """A path outside STORAGE_ROOT (e.g. cross-drive on Windows) must not raise."""
        result = storage_service.get_relative_path("Z:\\totally\\unrelated\\path.pdf")
        assert isinstance(result, str)


# ─────────────────────────────────────────────────────────────────────────
# init_storage
# ─────────────────────────────────────────────────────────────────────────

class TestInitStorage:
    def test_creates_all_category_directories(self, tmp_path, monkeypatch):
        fake_dirs = {name: str(tmp_path / name) for name in storage_service.STORAGE_DIRS}
        monkeypatch.setattr(storage_service, "STORAGE_DIRS", fake_dirs)

        storage_service.init_storage()

        for dir_path in fake_dirs.values():
            assert os.path.isdir(dir_path)

    def test_idempotent_when_directories_already_exist(self, tmp_path, monkeypatch):
        fake_dirs = {name: str(tmp_path / name) for name in storage_service.STORAGE_DIRS}
        monkeypatch.setattr(storage_service, "STORAGE_DIRS", fake_dirs)

        storage_service.init_storage()
        storage_service.init_storage()  # must not raise on second call

        for dir_path in fake_dirs.values():
            assert os.path.isdir(dir_path)
