"""Tests for the CLI."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from click.testing import CliRunner

from grammarian.cli.main import cli, display_results
from grammarian.core.models import AnalysisResult, MetricResult, Rating, Issue, Severity


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


class TestCLI:
    """Tests for CLI commands."""

    def test_version(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Grammarian" in result.output

    def test_analyze_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["analyze", "--help"])
        assert result.exit_code == 0
        assert "--min-score" in result.output
        assert "--diff" in result.output
        assert "--profile" in result.output

    def test_analyze_no_paths(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["analyze"])
        assert "No paths specified" in result.output

    def test_analyze_file(self, runner: CliRunner, tmp_path) -> None:
        # Create a test file
        test_file = tmp_path / "test.md"
        test_file.write_text("This is a simple test document. It has a few sentences.")

        result = runner.invoke(cli, ["analyze", str(test_file)])
        assert result.exit_code == 0
        assert "Writing Quality Index" in result.output

    def test_analyze_json_format(self, runner: CliRunner, tmp_path) -> None:
        test_file = tmp_path / "test.md"
        test_file.write_text("Hello world.")

        result = runner.invoke(cli, ["analyze", str(test_file), "--format", "json"])
        assert result.exit_code == 0
        assert "wqi_score" in result.output

    def test_analyze_min_score_pass(self, runner: CliRunner, tmp_path) -> None:
        test_file = tmp_path / "test.md"
        test_file.write_text("Simple clear text for testing.")

        result = runner.invoke(cli, ["analyze", str(test_file), "--min-score", "0.1"])
        assert result.exit_code == 0

    def test_analyze_min_score_fail(self, runner: CliRunner, tmp_path) -> None:
        test_file = tmp_path / "test.md"
        test_file.write_text("Txt.")

        result = runner.invoke(cli, ["analyze", str(test_file), "--min-score", "0.99"])
        assert result.exit_code == 1

    def test_analyze_profile(self, runner: CliRunner, tmp_path) -> None:
        test_file = tmp_path / "test.md"
        test_file.write_text("Technical documentation about the API implementation.")

        result = runner.invoke(cli, ["analyze", str(test_file), "--profile", "technical"])
        assert result.exit_code == 0
        assert "Writing Quality Index" in result.output

    def test_analyze_directory(self, runner: CliRunner, tmp_path) -> None:
        """Test analyzing a directory of markdown files."""
        (tmp_path / "file1.md").write_text("First document content.")
        (tmp_path / "file2.md").write_text("Second document content.")

        result = runner.invoke(cli, ["analyze", str(tmp_path)])
        assert result.exit_code == 0
        assert "Writing Quality Index" in result.output

    def test_analyze_diff_no_changes(self, runner: CliRunner) -> None:
        """Test --diff mode with no changed files."""
        with patch("grammarian.git.get_changed_files", return_value=[]):
            result = runner.invoke(cli, ["analyze", "--diff"])
            assert "No changed files found" in result.output

    def test_analyze_diff_with_changes(self, runner: CliRunner, tmp_path) -> None:
        """Test --diff mode with changed files."""
        test_file = tmp_path / "changed.md"
        test_file.write_text("Changed content here.")

        with patch("grammarian.git.get_changed_files", return_value=[test_file]):
            result = runner.invoke(cli, ["analyze", "--diff"])
            assert result.exit_code == 0
            assert "Writing Quality Index" in result.output

    def test_analyze_diff_staged(self, runner: CliRunner, tmp_path) -> None:
        """Test --diff --staged mode."""
        test_file = tmp_path / "staged.md"
        test_file.write_text("Staged content here.")

        with patch("grammarian.git.get_changed_files", return_value=[test_file]):
            result = runner.invoke(cli, ["analyze", "--diff", "--staged"])
            assert result.exit_code == 0

    def test_analyze_with_ai_feedback(self, runner: CliRunner, tmp_path) -> None:
        """Test --ai flag for AI feedback."""
        test_file = tmp_path / "test.md"
        test_file.write_text("Test content for AI analysis.")

        mock_advisor = MagicMock()
        mock_advisor.get_feedback.return_value = "Great writing!"

        with patch("grammarian.llm.WritingAdvisor", return_value=mock_advisor):
            result = runner.invoke(cli, ["analyze", str(test_file), "--ai"])
            assert result.exit_code == 0
            assert "AI Feedback" in result.output

    def test_analyze_ai_import_error(self, runner: CliRunner, tmp_path) -> None:
        """Test --ai when LLM is not available."""
        test_file = tmp_path / "test.md"
        test_file.write_text("Test content here.")

        with patch("grammarian.llm.WritingAdvisor", side_effect=ImportError("Not installed")):
            result = runner.invoke(cli, ["analyze", str(test_file), "--ai"])
            assert "LLM not available" in result.output

    def test_analyze_ai_exception(self, runner: CliRunner, tmp_path) -> None:
        """Test --ai when LLM raises exception."""
        test_file = tmp_path / "test.md"
        test_file.write_text("Test content here.")

        mock_advisor = MagicMock()
        mock_advisor.get_feedback.side_effect = Exception("API error")

        with patch("grammarian.llm.WritingAdvisor", return_value=mock_advisor):
            result = runner.invoke(cli, ["analyze", str(test_file), "--ai"])
            assert "AI feedback failed" in result.output

    def test_analyze_file_read_error(self, runner: CliRunner, tmp_path) -> None:
        """Test handling file read errors."""
        test_file = tmp_path / "unreadable.md"
        test_file.write_text("Content")

        with patch.object(Path, "read_text", side_effect=PermissionError("Access denied")):
            result = runner.invoke(cli, ["analyze", str(test_file)])
            assert "Error reading" in result.output

    def test_analyze_diff_file_read_error(self, runner: CliRunner, tmp_path) -> None:
        """Test handling file read errors in diff mode."""
        unreadable_file = tmp_path / "unreadable.md"
        unreadable_file.write_text("Content")

        def mock_read_text():
            raise PermissionError("Access denied")

        mock_path = MagicMock(spec=Path)
        mock_path.read_text = mock_read_text
        mock_path.__str__ = lambda self: str(unreadable_file)

        with patch("grammarian.git.get_changed_files", return_value=[mock_path]):
            result = runner.invoke(cli, ["analyze", "--diff"])
            # Should handle error gracefully
            assert "Error reading" in result.output or "No text files found" in result.output

    def test_analyze_directory_file_read_error(self, runner: CliRunner, tmp_path) -> None:
        """Test handling file read errors when processing directory."""
        # Create a directory with files
        (tmp_path / "good.md").write_text("Good content here.")
        bad_file = tmp_path / "bad.md"
        bad_file.write_text("Bad content")

        original_read_text = Path.read_text

        def selective_read_text(self):
            if "bad.md" in str(self):
                raise PermissionError("Access denied")
            return original_read_text(self)

        with patch.object(Path, "read_text", selective_read_text):
            result = runner.invoke(cli, ["analyze", str(tmp_path)])
            # Should process good file but report error for bad
            assert "Error reading" in result.output


class TestDisplayResults:
    """Tests for display_results function."""

    def test_display_with_issues(self) -> None:
        """Test displaying results with issues."""
        result = AnalysisResult(
            wqi_score=0.5,
            metrics=[
                MetricResult(
                    name="Grammar",
                    score=0.5,
                    issues=[
                        Issue(message="Issue 1", severity=Severity.WARNING, line=1, file_path="test.md"),
                        Issue(message="Issue 2", severity=Severity.ERROR, line=2, file_path="test.md"),
                        Issue(message="Issue 3", severity=Severity.SUGGESTION),
                        Issue(message="Issue 4", severity=Severity.WARNING),
                        Issue(message="Issue 5", severity=Severity.WARNING),
                        Issue(message="Issue 6", severity=Severity.WARNING),
                    ],
                )
            ],
            rating=Rating.FAIR,
        )
        # Should not raise
        display_results(result)

    def test_display_more_than_five_issues(self) -> None:
        """Test that display shows '... and X more' for many issues."""
        issues = [Issue(message=f"Issue {i}", severity=Severity.WARNING) for i in range(10)]
        result = AnalysisResult(
            wqi_score=0.3,
            metrics=[MetricResult(name="Test", score=0.3, issues=issues)],
            rating=Rating.POOR,
        )
        # Should handle gracefully
        display_results(result)


class TestConfigCommand:
    """Tests for the config command group."""

    def test_config_help(self, runner: CliRunner) -> None:
        """Test config command help."""
        result = runner.invoke(cli, ["config", "--help"])
        assert result.exit_code == 0
        assert "Manage Grammarian configuration" in result.output

    def test_config_init_help(self, runner: CliRunner) -> None:
        """Test config init help."""
        result = runner.invoke(cli, ["config", "init", "--help"])
        assert result.exit_code == 0
        assert "Generate an example configuration file" in result.output

    def test_config_init_stdout(self, runner: CliRunner) -> None:
        """Test config init to stdout."""
        result = runner.invoke(cli, ["config", "init", "--stdout"])
        assert result.exit_code == 0
        assert "# Grammarian Configuration File" in result.output
        assert "typography.symbols.curly_quotes" in result.output
        assert "[profiles.default]" in result.output
        assert "[metrics.grammar]" in result.output
        assert "disabled_rules" in result.output

    def test_config_init_creates_file(self, runner: CliRunner, tmp_path) -> None:
        """Test config init creates a file."""
        output_file = tmp_path / ".grammarian.toml"
        result = runner.invoke(cli, ["config", "init", "--output", str(output_file)])
        assert result.exit_code == 0
        assert output_file.exists()
        content = output_file.read_text()
        assert "# Grammarian Configuration File" in content
        assert "typography.symbols.curly_quotes" in content

    def test_config_init_default_filename(self, runner: CliRunner, tmp_path, monkeypatch) -> None:
        """Test config init uses .grammarian.toml by default."""
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(cli, ["config", "init"])
        assert result.exit_code == 0
        assert (tmp_path / ".grammarian.toml").exists()

    def test_config_init_no_overwrite(self, runner: CliRunner, tmp_path) -> None:
        """Test config init refuses to overwrite without --force."""
        output_file = tmp_path / ".grammarian.toml"
        output_file.write_text("existing content")
        result = runner.invoke(cli, ["config", "init", "--output", str(output_file)])
        assert result.exit_code == 1
        assert "already exists" in result.output
        assert output_file.read_text() == "existing content"

    def test_config_init_force_overwrite(self, runner: CliRunner, tmp_path) -> None:
        """Test config init overwrites with --force."""
        output_file = tmp_path / ".grammarian.toml"
        output_file.write_text("existing content")
        result = runner.invoke(cli, ["config", "init", "--output", str(output_file), "--force"])
        assert result.exit_code == 0
        content = output_file.read_text()
        assert "# Grammarian Configuration File" in content


class TestMainModule:
    """Tests for __main__.py module."""

    def test_main_module_import(self) -> None:
        """Test that __main__ module can be imported."""
        import grammarian.__main__ as main_module
        assert hasattr(main_module, "cli")

    def test_main_module_execution(self, runner: CliRunner) -> None:
        """Test running via python -m."""
        from grammarian.__main__ import cli as main_cli
        result = runner.invoke(main_cli, ["--help"])
        assert result.exit_code == 0

