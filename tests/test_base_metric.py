"""Tests for base metric classes."""

import pytest

from redpen.metrics.base import Metric
from redpen.core.models import MetricResult


class ConcreteMetric(Metric):
    """Concrete implementation of Metric for testing."""

    name = "Concrete"
    description = "A concrete test metric"

    def analyze(self, text: str, file_path: str | None = None) -> MetricResult:
        return MetricResult(name=self.name, score=0.75)


class TestMetricBase:
    """Tests for Metric base class."""

    def test_init_default_config(self) -> None:
        metric = ConcreteMetric()
        assert metric.config == {}

    def test_init_custom_config(self) -> None:
        metric = ConcreteMetric({"key": "value"})
        assert metric.config == {"key": "value"}

    def test_name_attribute(self) -> None:
        metric = ConcreteMetric()
        assert metric.name == "Concrete"

    def test_description_attribute(self) -> None:
        metric = ConcreteMetric()
        assert metric.description == "A concrete test metric"

    def test_analyze_returns_result(self) -> None:
        metric = ConcreteMetric()
        result = metric.analyze("test")
        assert isinstance(result, MetricResult)
        assert result.score == 0.75

    def test_analyze_with_file_path(self) -> None:
        metric = ConcreteMetric()
        result = metric.analyze("test", file_path="/path/to/file.md")
        assert result.score == 0.75


class TestNormalizeScore:
    """Tests for normalize_score method."""

    @pytest.fixture
    def metric(self) -> ConcreteMetric:
        return ConcreteMetric()

    def test_value_at_min(self, metric: ConcreteMetric) -> None:
        """Value at min returns 0.0."""
        result = metric.normalize_score(0, min_val=0, max_val=100)
        assert result == 0.0

    def test_value_at_max(self, metric: ConcreteMetric) -> None:
        """Value at max returns 1.0."""
        result = metric.normalize_score(100, min_val=0, max_val=100)
        assert result == 1.0

    def test_value_in_middle(self, metric: ConcreteMetric) -> None:
        """Value in middle returns 0.5."""
        result = metric.normalize_score(50, min_val=0, max_val=100)
        assert result == 0.5

    def test_value_below_min(self, metric: ConcreteMetric) -> None:
        """Value below min is clamped to 0.0."""
        result = metric.normalize_score(-10, min_val=0, max_val=100)
        assert result == 0.0

    def test_value_above_max(self, metric: ConcreteMetric) -> None:
        """Value above max is clamped to 1.0."""
        result = metric.normalize_score(150, min_val=0, max_val=100)
        assert result == 1.0

    def test_inverted_range(self, metric: ConcreteMetric) -> None:
        """Test with inverted=True (higher raw = lower score)."""
        result = metric.normalize_score(0, min_val=0, max_val=100, invert=True)
        assert result == 1.0

        result = metric.normalize_score(100, min_val=0, max_val=100, invert=True)
        assert result == 0.0

    def test_custom_range(self, metric: ConcreteMetric) -> None:
        """Test with custom min/max range."""
        result = metric.normalize_score(75, min_val=50, max_val=100)
        assert result == 0.5

    def test_equal_min_max(self, metric: ConcreteMetric) -> None:
        """Test when min equals max returns 1.0."""
        result = metric.normalize_score(50, min_val=50, max_val=50)
        assert result == 1.0

