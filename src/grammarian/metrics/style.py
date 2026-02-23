"""Style and clarity metrics."""

import re
from typing import Any

from grammarian.core.models import Issue, MetricResult, Severity
from grammarian.metrics.base import Metric


class StyleMetric(Metric):
    """
    Style and clarity analysis.

    Checks for:
    - Passive voice usage
    - Sentence length
    - Paragraph length
    - Weasel words
    - Clichés
    """

    name = "Style"
    description = "Checks writing style and clarity"

    # Common passive voice patterns
    PASSIVE_PATTERNS = [
        r"\b(is|are|was|were|be|been|being)\s+(\w+ed)\b",
        r"\b(is|are|was|were|be|been|being)\s+(\w+en)\b",
    ]

    # Weasel words that weaken writing
    WEASEL_WORDS = [
        "very", "really", "quite", "rather", "somewhat", "fairly",
        "basically", "actually", "literally", "simply", "just",
        "maybe", "perhaps", "probably", "possibly", "might",
        "various", "several", "many", "few", "some",
    ]

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self.max_sentence_words = self.config.get("max_sentence_words", 30)
        self.max_paragraph_sentences = self.config.get("max_paragraph_sentences", 6)
        self.check_passive = self.config.get("check_passive", True)
        self.check_weasel = self.config.get("check_weasel", True)

    def _find_passive_voice(self, text: str, file_path: str | None) -> list[Issue]:
        """Find passive voice constructions."""
        issues = []
        for pattern in self.PASSIVE_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                line_num = text[:match.start()].count("\n") + 1
                issues.append(
                    Issue(
                        message=f"Passive voice: '{match.group()}'",
                        severity=Severity.SUGGESTION,
                        line=line_num,
                        offset=match.start(),
                        length=len(match.group()),
                        rule_id="passive_voice",
                        file_path=file_path,
                    )
                )
        return issues

    def _check_sentence_length(self, text: str, file_path: str | None) -> list[Issue]:
        """Check for overly long sentences."""
        issues = []
        # Split into sentences (simple approach)
        sentences = re.split(r"[.!?]+", text)

        pos = 0
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            words = sentence.split()
            if len(words) > self.max_sentence_words:
                line_num = text[:pos].count("\n") + 1
                issues.append(
                    Issue(
                        message=f"Long sentence ({len(words)} words, max {self.max_sentence_words})",
                        severity=Severity.SUGGESTION,
                        line=line_num,
                        rule_id="sentence_length",
                        file_path=file_path,
                    )
                )
            pos = text.find(sentence, pos) + len(sentence)

        return issues

    def _find_weasel_words(self, text: str, file_path: str | None) -> list[Issue]:
        """Find weasel words."""
        issues = []
        for word in self.WEASEL_WORDS:
            pattern = rf"\b{word}\b"
            for match in re.finditer(pattern, text, re.IGNORECASE):
                line_num = text[:match.start()].count("\n") + 1
                issues.append(
                    Issue(
                        message=f"Weasel word: '{match.group()}'",
                        severity=Severity.INFO,
                        line=line_num,
                        offset=match.start(),
                        length=len(match.group()),
                        rule_id="weasel_word",
                        file_path=file_path,
                    )
                )
        return issues

    def analyze(self, text: str, file_path: str | None = None) -> MetricResult:
        """Analyze text for style issues."""
        if not text.strip():
            return MetricResult(name=self.name, score=1.0, details={"error": "Empty"})

        issues: list[Issue] = []

        if self.check_passive:
            issues.extend(self._find_passive_voice(text, file_path))

        issues.extend(self._check_sentence_length(text, file_path))

        if self.check_weasel:
            issues.extend(self._find_weasel_words(text, file_path))

        # Calculate score
        word_count = len(text.split())
        if word_count == 0:
            return MetricResult(name=self.name, score=1.0, issues=issues)

        # Weight issues by severity
        weighted_issues = sum(
            1.0 if i.severity == Severity.ERROR else
            0.5 if i.severity == Severity.WARNING else
            0.25 if i.severity == Severity.SUGGESTION else 0.1
            for i in issues
        )

        issues_per_100 = (weighted_issues / word_count) * 100
        score = max(0.0, 1.0 - (issues_per_100 / 10.0))

        return MetricResult(
            name=self.name,
            score=round(score, 3),
            raw_value=len(issues),
            issues=issues,
            details={
                "total_issues": len(issues),
                "passive_voice_count": sum(1 for i in issues if i.rule_id == "passive_voice"),
                "long_sentences": sum(1 for i in issues if i.rule_id == "sentence_length"),
                "weasel_words": sum(1 for i in issues if i.rule_id == "weasel_word"),
            },
        )

