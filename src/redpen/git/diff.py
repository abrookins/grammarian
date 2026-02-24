"""Git diff utilities for analyzing changed content."""

from pathlib import Path
from typing import Any

from git import Repo
from git.exc import InvalidGitRepositoryError


def get_repo(path: Path | None = None) -> Repo | None:
    """Get the git repository at the given path."""
    try:
        return Repo(path or Path.cwd(), search_parent_directories=True)
    except InvalidGitRepositoryError:
        return None


def get_changed_files(
    repo: Repo | None = None,
    staged: bool = False,
    against: str = "HEAD",
    extensions: list[str] | None = None,
) -> list[Path]:
    """
    Get list of changed files in the repository.

    Args:
        repo: Git repository (uses cwd if None)
        staged: If True, only return staged changes
        against: Commit/branch to compare against (default: HEAD)
        extensions: Filter by file extensions (e.g., [".md", ".txt"])

    Returns:
        List of Path objects for changed files
    """
    if repo is None:
        repo = get_repo()
        if repo is None:
            return []

    changed: list[Path] = []
    repo_root = Path(repo.working_dir)

    if staged:
        # Get staged changes
        diff = repo.index.diff(against)
    else:
        # Get unstaged changes + untracked
        diff = repo.index.diff(None)
        # Add untracked files
        for untracked in repo.untracked_files:
            path = repo_root / untracked
            if extensions is None or path.suffix in extensions:
                changed.append(path)

    # Process diff
    for item in diff:
        if item.a_path:
            path = repo_root / item.a_path
            if extensions is None or path.suffix in extensions:
                changed.append(path)
        if item.b_path and item.b_path != item.a_path:
            path = repo_root / item.b_path
            if extensions is None or path.suffix in extensions:
                changed.append(path)

    return list(set(changed))


def get_changed_content(
    repo: Repo | None = None,
    file_path: Path | None = None,
    staged: bool = False,
    against: str = "HEAD",
) -> dict[str, Any]:
    """
    Get the changed content (additions only) from git diff.

    Args:
        repo: Git repository (uses cwd if None)
        file_path: Specific file to get changes for (None for all)
        staged: If True, only return staged changes
        against: Commit/branch to compare against

    Returns:
        Dict with file paths as keys and changed line content as values
    """
    if repo is None:
        repo = get_repo()
        if repo is None:
            return {}

    result: dict[str, Any] = {}

    # Get diff text
    if staged:
        diff_text = repo.git.diff(against, cached=True)
    else:
        diff_text = repo.git.diff()

    # Parse diff to extract additions
    current_file = None
    for line in diff_text.split("\n"):
        if line.startswith("diff --git"):
            # Extract file path
            parts = line.split(" b/")
            if len(parts) > 1:
                current_file = parts[1]
                if file_path and current_file != str(file_path):
                    current_file = None
                elif current_file:
                    result[current_file] = {"additions": [], "deletions": []}
        elif current_file:
            if line.startswith("+") and not line.startswith("+++"):
                result[current_file]["additions"].append(line[1:])
            elif line.startswith("-") and not line.startswith("---"):
                result[current_file]["deletions"].append(line[1:])

    return result


def get_changed_text(
    repo: Repo | None = None,
    staged: bool = False,
    extensions: list[str] | None = None,
) -> str:
    """
    Get all changed text content as a single string.

    Useful for analyzing all changed prose in one pass.
    """
    if extensions is None:
        extensions = [".md", ".txt", ".rst"]

    files = get_changed_files(repo=repo, staged=staged, extensions=extensions)
    content_parts = []

    for file_path in files:
        if file_path.exists():
            try:
                content_parts.append(file_path.read_text())
            except (OSError, UnicodeDecodeError):
                pass

    return "\n\n".join(content_parts)

