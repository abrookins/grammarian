"""Tests for the Calculator and geometric mean."""

import pytest

from redpen.calculator import Calculator, geometric_mean
from redpen.core.models import MetricResult, Rating
from redpen.metrics.base import Metric


class MockMetric(Metric):
    """A mock metric for testing."""

    name = "Mock"
    description = "A mock metric"

    def __init__(self, score: float = 0.8) -> None:
        super().__init__()
        self._score = score

    def analyze(self, text: str, file_path: str | None = None) -> MetricResult:
        return MetricResult(name=self.name, score=self._score)


class TestGeometricMean:
    """Tests for geometric_mean function."""

    def test_single_value(self) -> None:
        assert geometric_mean([0.5]) == pytest.approx(0.5)

    def test_equal_values(self) -> None:
        assert geometric_mean([0.5, 0.5, 0.5]) == pytest.approx(0.5)

    def test_different_values(self) -> None:
        # (0.4 * 0.9)^0.5 = 0.6
        assert geometric_mean([0.4, 0.9]) == pytest.approx(0.6)

    def test_with_zero_floor(self) -> None:
        # Zero gets floored to 0.001, so result > 0
        result = geometric_mean([0.0, 1.0])
        assert result > 0
        assert result < 1.0

    def test_weighted(self) -> None:
        # Weight 2.0 on first value
        result = geometric_mean([0.5, 0.5], [2.0, 1.0])
        assert result == pytest.approx(0.5)

    def test_empty_list(self) -> None:
        assert geometric_mean([]) == 0.0

    def test_mismatched_weights(self) -> None:
        """Test that mismatched values and weights raises error."""
        with pytest.raises(ValueError, match="same length"):
            geometric_mean([0.5, 0.6, 0.7], weights=[1.0, 1.0])

    def test_zero_weight_sum(self) -> None:
        """Test handling when weights sum to zero."""
        result = geometric_mean([0.5, 0.6], weights=[0.0, 0.0])
        assert result == 0.0


class TestCalculator:
    """Tests for Calculator class."""

    def test_add_metric(self) -> None:
        calc = Calculator()
        calc.add_metric(MockMetric())
        assert len(calc.metrics) == 1

    def test_analyze_single_metric(self) -> None:
        calc = Calculator()
        calc.add_metric(MockMetric(score=0.8))
        result = calc.analyze("test text")
        assert result.wqi_score == pytest.approx(0.8)

    def test_analyze_multiple_metrics(self) -> None:
        calc = Calculator()
        calc.add_metric(MockMetric(score=0.8))
        calc.add_metric(MockMetric(score=0.5))
        result = calc.analyze("test text")
        # geometric mean of 0.8 and 0.5, rounded to 3 decimals
        expected = round(geometric_mean([0.8, 0.5]), 3)
        assert result.wqi_score == expected

    def test_analyze_no_metrics(self) -> None:
        calc = Calculator()
        result = calc.analyze("test text")
        assert result.wqi_score == 0.0

    def test_analyze_sets_rating(self) -> None:
        calc = Calculator()
        calc.add_metric(MockMetric(score=0.9))
        result = calc.analyze("test text")
        assert result.rating == Rating.EXCELLENT

    def test_analyze_poor_rating(self) -> None:
        calc = Calculator()
        calc.add_metric(MockMetric(score=0.3))
        result = calc.analyze("test text")
        assert result.rating == Rating.POOR

