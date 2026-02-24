"""Base metric class for Proseq."""

from abc import ABC, abstractmethod
from typing import Any

from redpen.core.models import MetricResult


class Metric(ABC):
    """Base class for all metrics."""

    name: str = "base"
    description: str = "Base metric"
    weight: float = 1.0

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """Initialize metric with optional config."""
        self.config = config or {}

    @abstractmethod
    def analyze(self, text: str, file_path: str | None = None) -> MetricResult:
        """
        Analyze text and return a metric result.

        Args:
            text: The text to analyze
            file_path: Optional path to the source file

        Returns:
            MetricResult with score between 0.0 and 1.0
        """
        ...

    def normalize_score(
        self,
        value: float,
        min_val: float,
        max_val: float,
        invert: bool = False,
    ) -> float:
        """
        Normalize a value to 0.0-1.0 range.

        Args:
            value: Raw value to normalize
            min_val: Minimum expected value (maps to 0.0 or 1.0)
            max_val: Maximum expected value (maps to 1.0 or 0.0)
            invert: If True, higher raw values = lower scores

        Returns:
            Normalized score between 0.0 and 1.0
        """
        if max_val == min_val:
            return 1.0

        normalized = (value - min_val) / (max_val - min_val)
        normalized = max(0.0, min(1.0, normalized))

        if invert:
            normalized = 1.0 - normalized

        return normalized

