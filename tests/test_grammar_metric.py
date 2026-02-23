"""Tests for GrammarMetric."""

import pytest
from unittest.mock import MagicMock, patch
import subprocess

from grammarian.metrics.grammar import GrammarMetric
from grammarian.core.models import Severity


class TestGrammarMetricBasic:
    """Basic tests for GrammarMetric."""

    def test_name_and_description(self) -> None:
        metric = GrammarMetric()
        assert metric.name == "Grammar"
        assert "grammar" in metric.description.lower()

    def test_empty_text(self) -> None:
        metric = GrammarMetric()
        result = metric.analyze("")
        assert result.score == 1.0
        assert "error" in result.details

    def test_whitespace_only(self) -> None:
        metric = GrammarMetric()
        result = metric.analyze("   \n\t  ")
        assert result.score == 1.0


class TestGrammarMetricWithProselint:
    """Tests for proselint integration."""

    def test_proselint_subprocess_success(self) -> None:
        """Test successful proselint subprocess call."""
        metric = GrammarMetric()
        # Ensure LanguageTool is not used
        metric._use_languagetool = False
        metric._tool = None
        
        mock_result = MagicMock()
        mock_result.stdout = '{"result": {"file:///tmp/test.txt": {"diagnostics": []}}}'
        
        with patch("subprocess.run", return_value=mock_result):
            result = metric._analyze_with_proselint("Clean text.", None)
            assert result.score == 1.0
            assert result.details["tool"] == "proselint"

    def test_proselint_with_issues(self) -> None:
        """Test proselint finding issues."""
        metric = GrammarMetric()
        
        mock_result = MagicMock()
        mock_result.stdout = '''{"result": {"file:///tmp/test.txt": {"diagnostics": [
            {"check_path": "test.rule", "message": "Test issue", "pos": [1, 1], "span": [0, 5], "replacements": null}
        ]}}}'''
        
        with patch("subprocess.run", return_value=mock_result):
            result = metric._analyze_with_proselint("Test text here.", None)
            assert len(result.issues) == 1
            assert result.issues[0].rule_id == "test.rule"

    def test_proselint_subprocess_error(self) -> None:
        """Test handling subprocess errors."""
        metric = GrammarMetric()
        
        with patch("subprocess.run", side_effect=subprocess.SubprocessError("Failed")):
            result = metric._analyze_with_proselint("Text", None)
            assert result.score == 1.0  # No issues found due to error

    def test_proselint_invalid_json(self) -> None:
        """Test handling invalid JSON from proselint."""
        metric = GrammarMetric()
        
        mock_result = MagicMock()
        mock_result.stdout = "not valid json"
        
        with patch("subprocess.run", return_value=mock_result):
            result = metric._analyze_with_proselint("Text", None)
            assert result.score == 1.0

    def test_proselint_empty_word_count(self) -> None:
        """Test with no words."""
        metric = GrammarMetric()
        
        mock_result = MagicMock()
        mock_result.stdout = '{"result": {}}'
        
        with patch("subprocess.run", return_value=mock_result):
            # Pass text that becomes empty after processing
            result = metric._analyze_with_proselint("", None)
            assert result.score == 1.0


class TestGrammarMetricWithLanguageTool:
    """Tests for LanguageTool integration."""

    def test_languagetool_not_installed(self) -> None:
        """Test fallback when LanguageTool not installed."""
        metric = GrammarMetric()
        
        with patch.dict("sys.modules", {"language_tool_python": None}):
            tool = metric._get_languagetool()
            # Should return None or handle gracefully
            # The actual behavior depends on import handling

    def test_languagetool_with_matches(self) -> None:
        """Test LanguageTool finding matches."""
        metric = GrammarMetric()
        
        mock_tool = MagicMock()
        mock_match = MagicMock()
        mock_match.ruleId = "TEST_RULE"
        mock_match.message = "Test message"
        mock_match.category = "GRAMMAR"
        mock_match.offset = 0
        mock_match.errorLength = 4
        mock_match.context = "Test context"
        mock_match.replacements = ["suggestion"]
        mock_tool.check.return_value = [mock_match]
        
        metric._tool = mock_tool
        metric._use_languagetool = True
        
        result = metric._analyze_with_languagetool("Test text here.", None)
        assert len(result.issues) == 1
        assert result.issues[0].rule_id == "TEST_RULE"
        assert result.details["tool"] == "languagetool"

    def test_languagetool_typos_severity(self) -> None:
        """Test TYPOS category maps to ERROR severity."""
        metric = GrammarMetric()
        
        mock_tool = MagicMock()
        mock_match = MagicMock()
        mock_match.ruleId = "TYPO_RULE"
        mock_match.message = "Typo found"
        mock_match.category = "TYPOS"
        mock_match.offset = 0
        mock_match.errorLength = 4
        mock_match.context = ""
        mock_match.replacements = []
        mock_tool.check.return_value = [mock_match]
        
        metric._tool = mock_tool
        metric._use_languagetool = True
        
        result = metric._analyze_with_languagetool("Tset", None)
        assert result.issues[0].severity == Severity.ERROR

    def test_languagetool_style_severity(self) -> None:
        """Test STYLE category maps to SUGGESTION severity."""
        metric = GrammarMetric()
        
        mock_tool = MagicMock()
        mock_match = MagicMock()
        mock_match.ruleId = "STYLE_RULE"
        mock_match.message = "Style issue"
        mock_match.category = "STYLE"
        mock_match.offset = 0
        mock_match.errorLength = 4
        mock_match.context = ""
        mock_match.replacements = []
        mock_tool.check.return_value = [mock_match]
        
        metric._tool = mock_tool
        metric._use_languagetool = True
        
        result = metric._analyze_with_languagetool("Text", None)
        assert result.issues[0].severity == Severity.SUGGESTION

    def test_disabled_rules_filtered(self) -> None:
        """Test that disabled rules are filtered out."""
        metric = GrammarMetric({"disabled_rules": ["IGNORE_ME"]})

        mock_tool = MagicMock()
        mock_match1 = MagicMock()
        mock_match1.ruleId = "IGNORE_ME"
        mock_match2 = MagicMock()
        mock_match2.ruleId = "KEEP_ME"
        mock_match2.message = "Keep"
        mock_match2.category = "GRAMMAR"
        mock_match2.offset = 0
        mock_match2.errorLength = 4
        mock_match2.context = ""
        mock_match2.replacements = []
        mock_tool.check.return_value = [mock_match1, mock_match2]

        metric._tool = mock_tool
        metric._use_languagetool = True

        result = metric._analyze_with_languagetool("Text", None)
        assert len(result.issues) == 1
        assert result.issues[0].rule_id == "KEEP_ME"


class TestGrammarMetricAnalyze:
    """Tests for main analyze method."""

    def test_analyze_uses_languagetool_when_available(self) -> None:
        """Test that analyze uses LanguageTool when installed."""
        metric = GrammarMetric()

        mock_tool = MagicMock()
        mock_tool.check.return_value = []
        metric._tool = mock_tool
        metric._use_languagetool = True

        result = metric.analyze("Clean text here.")
        assert result.details.get("tool") == "languagetool"

    def test_analyze_falls_back_to_proselint(self) -> None:
        """Test that analyze falls back to proselint."""
        metric = GrammarMetric()
        metric._tool = None
        metric._use_languagetool = False

        mock_result = MagicMock()
        mock_result.stdout = '{"result": {}}'

        with patch("subprocess.run", return_value=mock_result):
            result = metric.analyze("Clean text here.")
            assert result.details.get("tool") == "proselint"

    def test_languagetool_zero_word_count(self) -> None:
        """Test LanguageTool with zero word count."""
        metric = GrammarMetric()

        mock_tool = MagicMock()
        mock_match = MagicMock()
        mock_match.ruleId = "TEST"
        mock_match.message = "Issue"
        mock_match.category = "GRAMMAR"
        mock_match.offset = 0
        mock_match.errorLength = 1
        mock_match.context = ""
        mock_match.replacements = []
        mock_tool.check.return_value = [mock_match]

        metric._tool = mock_tool
        metric._use_languagetool = True

        # Empty text after stripping
        result = metric._analyze_with_languagetool("   ", None)
        # Should handle gracefully
        assert result.score == 1.0

    def test_languagetool_init_import_error(self) -> None:
        """Test LanguageTool initialization when import fails."""
        metric = GrammarMetric()
        metric._tool = None
        metric._use_languagetool = False

        with patch.dict("sys.modules", {"language_tool_python": None}):
            with patch("builtins.__import__", side_effect=ImportError):
                tool = metric._get_languagetool()
                # Should return None and set _use_languagetool to False
                assert tool is None
                assert metric._use_languagetool is False

