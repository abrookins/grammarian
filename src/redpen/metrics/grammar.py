"""Grammar checking metric using language-tool-python or proselint fallback."""

from typing import Any

from redpen.core.models import Issue, MetricResult, Severity
from redpen.metrics.base import Metric


class GrammarMetric(Metric):
    """
    Grammar and punctuation analysis.

    Uses language-tool-python if available, falls back to proselint.
    """

    name = "Grammar"
    description = "Checks grammar, punctuation, and style"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self.language = self.config.get("language", "en-US")
        self.disabled_rules = self.config.get("disabled_rules", [])
        self._tool = None
        self._use_languagetool = False

    def _get_languagetool(self) -> Any:
        """Lazily initialize LanguageTool."""
        if self._tool is None:
            try:
                import language_tool_python

                self._tool = language_tool_python.LanguageTool(self.language)
                self._use_languagetool = True
            except ImportError:
                self._tool = None
                self._use_languagetool = False
        return self._tool

    def _analyze_with_languagetool(
        self, text: str, file_path: str | None
    ) -> MetricResult:
        """Analyze using LanguageTool."""
        tool = self._get_languagetool()
        matches = tool.check(text)

        # Filter disabled rules
        matches = [m for m in matches if m.ruleId not in self.disabled_rules]

        issues = []
        for match in matches:
            # Map LanguageTool categories to severity
            severity = Severity.WARNING
            if match.category == "TYPOS":
                severity = Severity.ERROR
            elif match.category in ("STYLE", "REDUNDANCY"):
                severity = Severity.SUGGESTION

            suggestion = match.replacements[0] if match.replacements else None

            issues.append(
                Issue(
                    message=match.message,
                    severity=severity,
                    offset=match.offset,
                    length=match.errorLength,
                    rule_id=match.ruleId,
                    context=match.context,
                    suggestion=suggestion,
                    file_path=file_path,
                )
            )

        # Score based on issues per 100 words
        word_count = len(text.split())
        if word_count == 0:
            return MetricResult(name=self.name, score=1.0, issues=issues)

        issues_per_100 = (len(issues) / word_count) * 100
        # 0 issues = 1.0, 5+ issues per 100 words = 0.0
        score = max(0.0, 1.0 - (issues_per_100 / 5.0))

        return MetricResult(
            name=self.name,
            score=round(score, 3),
            raw_value=len(issues),
            issues=issues,
            details={
                "total_issues": len(issues),
                "issues_per_100_words": round(issues_per_100, 2),
                "word_count": word_count,
                "tool": "languagetool",
            },
        )

    def _analyze_with_proselint(
        self, text: str, file_path: str | None
    ) -> MetricResult:
        """Analyze using proselint via subprocess."""
        import json
        import subprocess
        import tempfile

        issues = []

        # Write text to temp file and run proselint
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(text)
            temp_path = f.name

        try:
            result = subprocess.run(
                ["proselint", "check", temp_path, "--output-format", "json"],
                capture_output=True,
                text=True,
            )
            if result.stdout:
                data = json.loads(result.stdout)
                file_results = data.get("result", {})
                for file_uri, file_data in file_results.items():
                    diagnostics = file_data.get("diagnostics", [])
                    for diag in diagnostics:
                        # Filter disabled rules for proselint
                        check_path = diag.get("check_path", "proselint")
                        if check_path in self.disabled_rules:
                            continue

                        line, col = diag.get("pos", [1, 1])
                        span = diag.get("span", [0, 0])
                        issues.append(
                            Issue(
                                message=diag.get("message", ""),
                                severity=Severity.SUGGESTION,
                                line=line,
                                column=col,
                                offset=span[0] if span else None,
                                length=span[1] - span[0] if span and len(span) > 1 else None,
                                rule_id=check_path,
                                suggestion=diag.get("replacements"),
                                file_path=file_path,
                            )
                        )
        except (subprocess.SubprocessError, json.JSONDecodeError):
            pass  # Proselint not available or failed
        finally:
            import os
            os.unlink(temp_path)

        word_count = len(text.split())
        if word_count == 0:
            return MetricResult(name=self.name, score=1.0, issues=issues)

        issues_per_100 = (len(issues) / word_count) * 100
        score = max(0.0, 1.0 - (issues_per_100 / 5.0))

        return MetricResult(
            name=self.name,
            score=round(score, 3),
            raw_value=len(issues),
            issues=issues,
            details={
                "total_issues": len(issues),
                "issues_per_100_words": round(issues_per_100, 2),
                "word_count": word_count,
                "tool": "proselint",
            },
        )

    def analyze(self, text: str, file_path: str | None = None) -> MetricResult:
        """Analyze text for grammar issues."""
        if not text.strip():
            return MetricResult(name=self.name, score=1.0, details={"error": "Empty text"})

        # Try LanguageTool first, fall back to proselint
        if self._get_languagetool() is not None:
            return self._analyze_with_languagetool(text, file_path)
        return self._analyze_with_proselint(text, file_path)

