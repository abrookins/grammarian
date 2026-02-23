"""Readability metrics using textstat."""

from typing import Any

import textstat

from grammarian.core.models import MetricResult
from grammarian.metrics.base import Metric


class ReadabilityMetric(Metric):
    """
    Readability analysis using textstat.

    Combines multiple readability formulas:
    - Flesch Reading Ease
    - Flesch-Kincaid Grade Level
    - Gunning Fog Index
    - SMOG Index
    - Coleman-Liau Index
    """

    name = "Readability"
    description = "Measures how easy the text is to read"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self.target_grade = self.config.get("target_grade", 10)  # Default: 10th grade
        self.formula = self.config.get("formula", "flesch_kincaid")

    def analyze(self, text: str, file_path: str | None = None) -> MetricResult:
        """Analyze text readability."""
        if not text.strip():
            return MetricResult(
                name=self.name,
                score=1.0,
                raw_value=None,
                details={"error": "Empty text"},
            )

        # Calculate various readability metrics
        flesch_ease = textstat.flesch_reading_ease(text)
        flesch_grade = textstat.flesch_kincaid_grade(text)
        gunning_fog = textstat.gunning_fog(text)
        smog = textstat.smog_index(text)
        coleman_liau = textstat.coleman_liau_index(text)
        ari = textstat.automated_readability_index(text)

        # Get consensus grade level
        consensus = textstat.text_standard(text, float_output=True)

        # Calculate score based on how close to target grade
        # Perfect score if grade matches target, decreasing as it diverges
        grade_diff = abs(consensus - self.target_grade)

        # Score: 1.0 if perfect match, decreasing by 0.1 per grade level difference
        # Capped at 0.0 for very large differences
        score = max(0.0, 1.0 - (grade_diff * 0.1))

        # Adjust score based on Flesch Reading Ease
        # 60-70 is standard, bonus for being in good range
        if 50 <= flesch_ease <= 80:
            score = min(1.0, score + 0.05)

        details = {
            "flesch_reading_ease": round(flesch_ease, 1),
            "flesch_kincaid_grade": round(flesch_grade, 1),
            "gunning_fog": round(gunning_fog, 1),
            "smog_index": round(smog, 1),
            "coleman_liau_index": round(coleman_liau, 1),
            "automated_readability_index": round(ari, 1),
            "consensus_grade": round(consensus, 1),
            "target_grade": self.target_grade,
            "word_count": textstat.lexicon_count(text),
            "sentence_count": textstat.sentence_count(text),
            "syllable_count": textstat.syllable_count(text),
        }

        return MetricResult(
            name=self.name,
            score=round(score, 3),
            raw_value=consensus,
            details=details,
        )

