"""Spelling check metric using pyspellchecker."""

import re
from typing import Any

from spellchecker import SpellChecker

from redpen.core.models import Issue, MetricResult, Severity
from redpen.metrics.base import Metric


class SpellingMetric(Metric):
    """
    Spelling analysis using pyspellchecker.

    Identifies misspelled words and provides suggestions.
    """

    name = "Spelling"
    description = "Checks for spelling errors"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self.language = self.config.get("language", "en")
        self.custom_words = self.config.get("custom_words", [])
        self._spell = None

    def _get_spellchecker(self) -> SpellChecker:
        """Lazily initialize spellchecker."""
        if self._spell is None:
            self._spell = SpellChecker(language=self.language)
            # Add custom words
            if self.custom_words:
                self._spell.word_frequency.load_words(self.custom_words)
            # Add common technical terms
            tech_words = [
                # Programming terms
                "api", "apis", "cli", "json", "yaml", "toml", "html", "css",
                "http", "https", "url", "urls", "sdk", "async", "config",
                "readme", "github", "pypi", "npm", "webpack", "pytest",
                "venv", "virtualenv", "env", "dev", "prod", "deps",
                # File types
                "md", "txt", "py", "js", "ts", "tsx", "jsx", "css", "scss",
                # Common abbreviations
                "etc", "eg", "ie", "vs", "ci", "cd",
                # This project
                "redpen", "mfcqi", "wqi", "proselint", "textstat",
                "litellm", "pydantic", "readability", "flesch", "kincaid",
                "gunning", "smog", "liau", "gitpython",
            ]
            self._spell.word_frequency.load_words(tech_words)
        return self._spell

    def _remove_code_blocks(self, text: str) -> str:
        """Remove code blocks from markdown text."""
        # Remove fenced code blocks (```...```)
        text = re.sub(r"```[\s\S]*?```", "", text)
        # Remove inline code (`...`)
        text = re.sub(r"`[^`]+`", "", text)
        return text

    def _extract_words(self, text: str) -> list[tuple[str, int]]:
        """Extract words with their positions from text."""
        # Remove code blocks first
        clean_text = self._remove_code_blocks(text)
        # Match words, capturing position (min 2 chars to avoid single letters)
        word_pattern = re.compile(r"\b[a-zA-Z]{2,}(?:'[a-zA-Z]+)?\b")
        words = []
        for match in word_pattern.finditer(clean_text):
            words.append((match.group(), match.start()))
        return words

    def analyze(self, text: str, file_path: str | None = None) -> MetricResult:
        """Analyze text for spelling errors."""
        if not text.strip():
            return MetricResult(
                name=self.name,
                score=1.0,
                details={"error": "Empty text"},
            )

        spell = self._get_spellchecker()
        words_with_pos = self._extract_words(text)

        # Get just the words for spell checking
        words = [w.lower() for w, _ in words_with_pos]
        misspelled = spell.unknown(words)

        # Build issues list
        issues = []
        for word, pos in words_with_pos:
            if word.lower() in misspelled:
                correction = spell.correction(word.lower())
                candidates = list(spell.candidates(word.lower()) or [])[:3]

                # Find line number
                line_num = text[:pos].count("\n") + 1

                issues.append(
                    Issue(
                        message=f"Possible spelling error: '{word}'",
                        severity=Severity.WARNING,
                        line=line_num,
                        offset=pos,
                        length=len(word),
                        rule_id="spelling",
                        suggestion=correction,
                        context=f"Suggestions: {', '.join(candidates)}" if candidates else None,
                        file_path=file_path,
                    )
                )

        # Score based on misspellings per 100 words
        total_words = len(words)
        if total_words == 0:
            return MetricResult(name=self.name, score=1.0, issues=issues)

        # Unique misspellings to avoid counting same word multiple times
        unique_misspellings = len(misspelled)
        error_rate = (unique_misspellings / total_words) * 100

        # 0 errors = 1.0, 5%+ error rate = 0.0
        score = max(0.0, 1.0 - (error_rate / 5.0))

        return MetricResult(
            name=self.name,
            score=round(score, 3),
            raw_value=unique_misspellings,
            issues=issues,
            details={
                "total_words": total_words,
                "misspelled_count": unique_misspellings,
                "error_rate_percent": round(error_rate, 2),
            },
        )

