"""Tests for LLM advisor."""

import pytest
from unittest.mock import MagicMock, patch

from grammarian.core.models import AnalysisResult, MetricResult, Rating, Issue, Severity
from grammarian.llm.advisor import WritingAdvisor


@pytest.fixture
def sample_result() -> AnalysisResult:
    """Create a sample analysis result for testing."""
    return AnalysisResult(
        wqi_score=0.7,
        metrics=[
            MetricResult(name="Readability", score=0.8),
            MetricResult(name="Grammar", score=0.6),
        ],
        rating=Rating.GOOD,
        files_analyzed=1,
    )


@pytest.fixture
def sample_issues() -> list[Issue]:
    """Create sample issues for testing."""
    return [
        Issue(message="Passive voice detected", severity=Severity.SUGGESTION),
        Issue(message="Long sentence", severity=Severity.WARNING),
    ]


class TestWritingAdvisor:
    """Tests for WritingAdvisor class."""

    def test_init_defaults(self) -> None:
        advisor = WritingAdvisor()
        assert advisor.model == "gpt-4o-mini"
        assert advisor.temperature == 0.3
        assert advisor.context == ""

    def test_init_custom(self) -> None:
        advisor = WritingAdvisor(model="gpt-4", temperature=0.5, context="Tech docs")
        assert advisor.model == "gpt-4"
        assert advisor.temperature == 0.5
        assert advisor.context == "Tech docs"

    def test_get_client_import_error(self) -> None:
        advisor = WritingAdvisor()
        with patch.dict("sys.modules", {"litellm": None}):
            with patch("builtins.__import__", side_effect=ImportError("No module")):
                with pytest.raises(ImportError, match="LiteLLM not installed"):
                    advisor._get_client()

    def test_get_client_success(self) -> None:
        advisor = WritingAdvisor()
        mock_litellm = MagicMock()
        with patch.dict("sys.modules", {"litellm": mock_litellm}):
            with patch("builtins.__import__", return_value=mock_litellm):
                # Force reimport
                advisor._client = None
                client = advisor._get_client()
                assert client is not None

    def test_build_prompt(self, sample_result: AnalysisResult) -> None:
        advisor = WritingAdvisor()
        prompt = advisor._build_prompt("Test text content", sample_result)
        
        assert "Overall Score" in prompt
        assert "0.70" in prompt
        assert "Readability" in prompt
        assert "Grammar" in prompt
        assert "Test text content" in prompt

    def test_build_prompt_with_context(self, sample_result: AnalysisResult) -> None:
        advisor = WritingAdvisor(context="Technical documentation")
        prompt = advisor._build_prompt("Test text", sample_result)
        
        assert "Writing Context" in prompt
        assert "Technical documentation" in prompt

    def test_build_prompt_with_issues(self) -> None:
        result = AnalysisResult(
            wqi_score=0.5,
            metrics=[
                MetricResult(
                    name="Grammar",
                    score=0.5,
                    issues=[Issue(message="Test issue", severity=Severity.WARNING)],
                )
            ],
            rating=Rating.FAIR,
        )
        advisor = WritingAdvisor()
        prompt = advisor._build_prompt("Test", result)
        
        assert "Test issue" in prompt

    def test_get_feedback(self, sample_result: AnalysisResult) -> None:
        advisor = WritingAdvisor()
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Great writing! Consider..."
        
        mock_client = MagicMock()
        mock_client.completion.return_value = mock_response
        advisor._client = mock_client
        
        feedback = advisor.get_feedback("Sample text", sample_result)
        
        assert feedback == "Great writing! Consider..."
        mock_client.completion.assert_called_once()

    def test_suggest_rewrites_success(self, sample_issues: list[Issue]) -> None:
        advisor = WritingAdvisor()
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '[{"original": "was done", "rewrite": "completed", "reason": "Active voice"}]'
        
        mock_client = MagicMock()
        mock_client.completion.return_value = mock_response
        advisor._client = mock_client
        
        suggestions = advisor.suggest_rewrites("The task was done", sample_issues)
        
        assert len(suggestions) == 1
        assert suggestions[0]["original"] == "was done"

    def test_suggest_rewrites_invalid_json(self, sample_issues: list[Issue]) -> None:
        advisor = WritingAdvisor()
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Not valid JSON"
        
        mock_client = MagicMock()
        mock_client.completion.return_value = mock_response
        advisor._client = mock_client
        
        suggestions = advisor.suggest_rewrites("Text", sample_issues)
        
        assert suggestions == []

    def test_system_prompt_exists(self) -> None:
        assert WritingAdvisor.DEFAULT_SYSTEM_PROMPT
        assert "writing coach" in WritingAdvisor.DEFAULT_SYSTEM_PROMPT.lower()

