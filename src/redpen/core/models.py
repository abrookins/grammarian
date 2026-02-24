"""Core data models for Proseq."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Severity(str, Enum):
    """Issue severity levels."""

    ERROR = "error"
    WARNING = "warning"
    SUGGESTION = "suggestion"
    INFO = "info"


class Rating(str, Enum):
    """Quality rating categories."""

    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"


class Issue(BaseModel):
    """A single issue found in the text."""

    message: str
    severity: Severity = Severity.WARNING
    line: int | None = None
    column: int | None = None
    offset: int | None = None
    length: int | None = None
    rule_id: str | None = None
    context: str | None = None
    suggestion: str | None = None
    file_path: str | None = None


class MetricResult(BaseModel):
    """Result from a single metric analysis."""

    name: str
    score: float = Field(ge=0.0, le=1.0)
    raw_value: Any = None
    issues: list[Issue] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)

    @property
    def rating(self) -> Rating:
        """Get rating based on score."""
        if self.score >= 0.8:
            return Rating.EXCELLENT
        elif self.score >= 0.6:
            return Rating.GOOD
        elif self.score >= 0.4:
            return Rating.FAIR
        return Rating.POOR


class AnalysisResult(BaseModel):
    """Complete analysis result."""

    wqi_score: float = Field(ge=0.0, le=1.0)
    metrics: list[MetricResult] = Field(default_factory=list)
    files_analyzed: int = 0
    total_words: int = 0
    total_sentences: int = 0
    recommendations: list[str] = Field(default_factory=list)

    @property
    def rating(self) -> Rating:
        """Get overall rating based on WQI score."""
        if self.wqi_score >= 0.8:
            return Rating.EXCELLENT
        elif self.wqi_score >= 0.6:
            return Rating.GOOD
        elif self.wqi_score >= 0.4:
            return Rating.FAIR
        return Rating.POOR

    @property
    def all_issues(self) -> list[Issue]:
        """Get all issues from all metrics."""
        issues = []
        for metric in self.metrics:
            issues.extend(metric.issues)
        return sorted(issues, key=lambda i: (i.severity.value, i.line or 0))

