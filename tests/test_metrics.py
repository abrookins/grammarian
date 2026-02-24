"""Tests for individual metrics."""

import pytest

from redpen.metrics.readability import ReadabilityMetric
from redpen.metrics.spelling import SpellingMetric
from redpen.metrics.style import StyleMetric


class TestReadabilityMetric:
    """Tests for ReadabilityMetric."""

    def test_simple_text(self) -> None:
        metric = ReadabilityMetric()
        result = metric.analyze("The cat sat on the mat. It was a nice day.")
        assert 0.0 <= result.score <= 1.0
        assert result.name == "Readability"

    def test_complex_text(self) -> None:
        metric = ReadabilityMetric()
        text = (
            "The implementation of sophisticated algorithmic paradigms "
            "necessitates comprehensive understanding of computational complexity."
        )
        result = metric.analyze(text)
        assert 0.0 <= result.score <= 1.0
        # Complex text should have higher grade level
        assert "consensus_grade" in result.details

    def test_empty_text(self) -> None:
        metric = ReadabilityMetric()
        result = metric.analyze("")
        assert result.score == 1.0

    def test_custom_target_grade(self) -> None:
        metric = ReadabilityMetric({"target_grade": 8})
        result = metric.analyze("Simple words for kids to read.")
        assert "target_grade" in result.details
        assert result.details["target_grade"] == 8


class TestSpellingMetric:
    """Tests for SpellingMetric."""

    def test_correct_spelling(self) -> None:
        metric = SpellingMetric()
        result = metric.analyze("The quick brown fox jumps over the lazy dog.")
        assert result.score > 0.9

    def test_misspelled_words(self) -> None:
        metric = SpellingMetric()
        result = metric.analyze("Teh qiuck borwn fox jmups over the lzay dog.")
        assert result.score < 0.5
        assert len(result.issues) > 0

    def test_empty_text(self) -> None:
        metric = SpellingMetric()
        result = metric.analyze("")
        assert result.score == 1.0

    def test_technical_terms_accepted(self) -> None:
        metric = SpellingMetric()
        result = metric.analyze("The API returns JSON data via HTTP.")
        # Technical terms should not be flagged
        assert result.score > 0.8

    def test_code_blocks_ignored(self) -> None:
        metric = SpellingMetric()
        text = """Here is some text.

```python
def foo_bar_baz():
    pass
```

More text here."""
        result = metric.analyze(text)
        # Code block content should not affect spelling score
        assert result.score > 0.8


class TestStyleMetric:
    """Tests for StyleMetric."""

    def test_clean_text(self) -> None:
        metric = StyleMetric()
        result = metric.analyze("The dog runs fast. It catches the ball.")
        assert result.score > 0.8

    def test_passive_voice(self) -> None:
        metric = StyleMetric()
        text = "The ball was thrown. The game was played. The trophy was won."
        result = metric.analyze(text)
        passive_count = result.details.get("passive_voice_count", 0)
        assert passive_count > 0

    def test_weasel_words(self) -> None:
        metric = StyleMetric()
        text = "This is very good. It is really quite amazing."
        result = metric.analyze(text)
        weasel_count = result.details.get("weasel_words", 0)
        assert weasel_count > 0

    def test_long_sentences(self) -> None:
        metric = StyleMetric({"max_sentence_words": 10})
        text = "This sentence has way more than ten words and should be flagged as too long."
        result = metric.analyze(text)
        long_count = result.details.get("long_sentences", 0)
        assert long_count > 0

    def test_passive_check_disabled(self) -> None:
        metric = StyleMetric({"check_passive": False})
        text = "The ball was thrown by the player."
        result = metric.analyze(text)
        # With passive check disabled, no passive issues
        passive_count = result.details.get("passive_voice_count", 0)
        assert passive_count == 0

    def test_empty_text(self) -> None:
        metric = StyleMetric()
        result = metric.analyze("")
        assert result.score == 1.0

    def test_whitespace_only(self) -> None:
        """Test style metric with whitespace-only text."""
        metric = StyleMetric()
        result = metric.analyze("   \n\t  ")
        assert result.score == 1.0


class TestSpellingMetricCustomWords:
    """Tests for SpellingMetric custom words."""

    def test_custom_words_loaded(self) -> None:
        """Test that custom words are loaded into spell checker."""
        custom = ["xyzabc", "customword"]
        metric = SpellingMetric({"custom_words": custom})
        result = metric.analyze("The xyzabc customword feature.")
        # Custom words should not be flagged as misspellings
        assert result.score > 0.9

    def test_zero_words(self) -> None:
        """Test spelling with text that has no recognizable words."""
        metric = SpellingMetric()
        result = metric.analyze("   ")  # Just whitespace
        assert result.score == 1.0

    def test_no_alphabetic_words(self) -> None:
        """Test spelling with text that has no alphabetic words after extraction."""
        metric = SpellingMetric()
        # Only numbers and punctuation - no actual words
        result = metric.analyze("123 456 789! @#$ %^& *().")
        # Should return 1.0 score since no words to check
        assert result.score == 1.0


class TestStyleMetricEdgeCases:
    """Edge case tests for StyleMetric."""

    def test_no_words_after_split(self) -> None:
        """Test style metric with text that produces zero words after split."""
        metric = StyleMetric()
        # Only punctuation/symbols - no actual words
        result = metric.analyze("!@#$%^&*()")
        assert result.score == 1.0

