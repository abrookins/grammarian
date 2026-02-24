"""WQI (Writing Quality Index) calculator using geometric mean."""

import math
from typing import Sequence

from redpen.core.models import AnalysisResult, MetricResult
from redpen.metrics.base import Metric


def geometric_mean(values: Sequence[float], weights: Sequence[float] | None = None) -> float:
    """
    Calculate weighted geometric mean of values.

    Uses the formula: (v1^w1 * v2^w2 * ... * vn^wn)^(1/sum(weights))

    Args:
        values: Sequence of values (must be > 0)
        weights: Optional weights for each value (defaults to 1.0)

    Returns:
        Geometric mean of the values
    """
    if not values:
        return 0.0

    if weights is None:
        weights = [1.0] * len(values)

    if len(values) != len(weights):
        raise ValueError("Values and weights must have same length")

    # Ensure no zero values (would make product 0)
    # Use small epsilon for zero scores
    epsilon = 0.001
    safe_values = [max(v, epsilon) for v in values]

    # Calculate weighted geometric mean
    log_sum = sum(w * math.log(v) for v, w in zip(safe_values, weights))
    weight_sum = sum(weights)

    if weight_sum == 0:
        return 0.0

    return math.exp(log_sum / weight_sum)


class Calculator:
    """Calculate Writing Quality Index from multiple metrics."""

    def __init__(self, metrics: list[Metric] | None = None) -> None:
        """Initialize calculator with metrics."""
        self.metrics = metrics or []

    def add_metric(self, metric: Metric) -> None:
        """Add a metric to the calculator."""
        self.metrics.append(metric)

    def analyze(
        self,
        text: str,
        file_path: str | None = None,
    ) -> AnalysisResult:
        """
        Analyze text using all configured metrics.

        Args:
            text: Text to analyze
            file_path: Optional source file path

        Returns:
            Complete analysis result with WQI score
        """
        if not self.metrics:
            return AnalysisResult(
                wqi_score=0.0,
                metrics=[],
                files_analyzed=1 if file_path else 0,
            )

        results: list[MetricResult] = []
        scores: list[float] = []
        weights: list[float] = []

        for metric in self.metrics:
            result = metric.analyze(text, file_path)
            results.append(result)
            scores.append(result.score)
            weights.append(metric.weight)

        wqi = geometric_mean(scores, weights)

        # Count words and sentences for stats
        words = len(text.split())
        sentences = text.count(".") + text.count("!") + text.count("?")

        return AnalysisResult(
            wqi_score=round(wqi, 3),
            metrics=results,
            files_analyzed=1 if file_path else 0,
            total_words=words,
            total_sentences=max(sentences, 1),
        )

