"""Tests for Git integration."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from grammarian.git.diff import (
    get_repo,
    get_changed_files,
    get_changed_content,
    get_changed_text,
)


class TestGetRepo:
    """Tests for get_repo function."""

    def test_get_repo_invalid_path(self, tmp_path: Path) -> None:
        """Non-git directory returns None."""
        result = get_repo(tmp_path)
        assert result is None

    def test_get_repo_valid(self, tmp_path: Path) -> None:
        """Valid git repo returns Repo object."""
        # Initialize a git repo
        import subprocess
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        
        result = get_repo(tmp_path)
        assert result is not None
        assert result.working_dir == str(tmp_path)


class TestGetChangedFiles:
    """Tests for get_changed_files function."""

    def test_no_repo_returns_empty(self, tmp_path: Path) -> None:
        """When no repo exists, returns empty list."""
        with patch("grammarian.git.diff.get_repo", return_value=None):
            result = get_changed_files(repo=None)
            assert result == []

    def test_with_mock_repo_unstaged(self) -> None:
        """Test with mocked repo for unstaged changes."""
        mock_repo = MagicMock()
        mock_repo.working_dir = "/fake/path"
        mock_repo.untracked_files = []
        
        mock_diff_item = MagicMock()
        mock_diff_item.a_path = "test.md"
        mock_diff_item.b_path = "test.md"
        mock_repo.index.diff.return_value = [mock_diff_item]
        
        result = get_changed_files(repo=mock_repo, staged=False)
        assert len(result) == 1

    def test_with_mock_repo_staged(self) -> None:
        """Test with mocked repo for staged changes."""
        mock_repo = MagicMock()
        mock_repo.working_dir = "/fake/path"
        
        mock_diff_item = MagicMock()
        mock_diff_item.a_path = "readme.md"
        mock_diff_item.b_path = None
        mock_repo.index.diff.return_value = [mock_diff_item]
        
        result = get_changed_files(repo=mock_repo, staged=True, against="HEAD")
        assert len(result) == 1

    def test_extension_filter(self) -> None:
        """Test filtering by file extensions."""
        mock_repo = MagicMock()
        mock_repo.working_dir = "/fake/path"
        mock_repo.untracked_files = ["file.py", "readme.md"]
        mock_repo.index.diff.return_value = []
        
        result = get_changed_files(repo=mock_repo, extensions=[".md"])
        assert len(result) == 1
        assert result[0].suffix == ".md"


class TestGetChangedContent:
    """Tests for get_changed_content function."""

    def test_no_repo_returns_empty(self) -> None:
        """When no repo exists, returns empty dict."""
        with patch("grammarian.git.diff.get_repo", return_value=None):
            result = get_changed_content()
            assert result == {}

    def test_parse_diff_output(self) -> None:
        """Test parsing git diff output."""
        mock_repo = MagicMock()
        mock_repo.git.diff.return_value = """diff --git a/test.md b/test.md
--- a/test.md
+++ b/test.md
@@ -1,3 +1,4 @@
 Line 1
+Added line
 Line 2
-Deleted line
"""
        result = get_changed_content(repo=mock_repo, staged=False)
        assert "test.md" in result
        assert "Added line" in result["test.md"]["additions"]
        assert "Deleted line" in result["test.md"]["deletions"]

    def test_staged_diff(self) -> None:
        """Test getting staged changes."""
        mock_repo = MagicMock()
        mock_repo.git.diff.return_value = ""
        
        get_changed_content(repo=mock_repo, staged=True)
        mock_repo.git.diff.assert_called_with("HEAD", cached=True)


class TestGetChangedText:
    """Tests for get_changed_text function."""

    def test_empty_when_no_files(self) -> None:
        """Returns empty string when no changed files."""
        with patch("grammarian.git.diff.get_changed_files", return_value=[]):
            result = get_changed_text()
            assert result == ""

    def test_combines_file_contents(self, tmp_path: Path) -> None:
        """Combines content from multiple files."""
        file1 = tmp_path / "file1.md"
        file2 = tmp_path / "file2.md"
        file1.write_text("Content 1")
        file2.write_text("Content 2")
        
        with patch("grammarian.git.diff.get_changed_files", return_value=[file1, file2]):
            result = get_changed_text()
            assert "Content 1" in result
            assert "Content 2" in result

    def test_handles_unreadable_files(self, tmp_path: Path) -> None:
        """Gracefully handles files that can't be read."""
        nonexistent = tmp_path / "missing.md"
        
        with patch("grammarian.git.diff.get_changed_files", return_value=[nonexistent]):
            result = get_changed_text()
            assert result == ""

    def test_default_extensions(self) -> None:
        """Default extensions are .md, .txt, .rst."""
        with patch("grammarian.git.diff.get_changed_files") as mock:
            mock.return_value = []
            get_changed_text()
            mock.assert_called_with(repo=None, staged=False, extensions=[".md", ".txt", ".rst"])

    def test_handles_unicode_decode_error(self, tmp_path: Path) -> None:
        """Gracefully handles files with encoding issues."""
        binary_file = tmp_path / "binary.md"
        binary_file.write_bytes(b"\x80\x81\x82")

        with patch("grammarian.git.diff.get_changed_files", return_value=[binary_file]):
            result = get_changed_text()
            assert result == ""


class TestGetChangedFilesAdditional:
    """Additional tests for edge cases."""

    def test_b_path_different_from_a_path(self) -> None:
        """Test when b_path differs from a_path (renames)."""
        mock_repo = MagicMock()
        mock_repo.working_dir = "/fake/path"
        mock_repo.untracked_files = []

        mock_diff_item = MagicMock()
        mock_diff_item.a_path = "old.md"
        mock_diff_item.b_path = "new.md"
        mock_repo.index.diff.return_value = [mock_diff_item]

        result = get_changed_files(repo=mock_repo, staged=False, extensions=[".md"])
        # Both paths should be included
        assert len(result) == 2


class TestGetChangedContentAdditional:
    """Additional tests for get_changed_content."""

    def test_file_path_filter(self) -> None:
        """Test filtering by specific file path."""
        mock_repo = MagicMock()
        mock_repo.git.diff.return_value = """diff --git a/test.md b/test.md
--- a/test.md
+++ b/test.md
@@ -1 +1 @@
-old
+new
diff --git a/other.md b/other.md
--- a/other.md
+++ b/other.md
@@ -1 +1 @@
-foo
+bar
"""
        result = get_changed_content(repo=mock_repo, file_path="test.md")
        # When file_path is specified, only that file's changes are returned
        assert "test.md" in result

