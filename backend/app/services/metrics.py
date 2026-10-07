"""
Observability metrics for the orchestration pipeline.

Tracks:
- end-to-end generation duration
- candidate count before and after shortlisting
- weather provider latency/error/cache rates
- forecast coverage status
- reason a Plan A changes
- LLM latency/failure/fallback rate
- plan option selection/switching by users once analytics is available
"""

import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

MAX_STORED_METRICS = 1000


@dataclass
class PipelineMetrics:
    """Metrics collected during a single plan generation."""

    plan_id: str = ""
    start_time: float = 0.0
    end_time: float = 0.0
    duration_ms: float = 0.0

    # Candidate counts
    candidates_before_shortlist: int = 0
    candidates_after_shortlist: int = 0

    # Weather metrics
    weather_latency_ms: list[float] = field(default_factory=list)
    weather_errors: int = 0
    weather_cache_hits: int = 0
    weather_cache_misses: int = 0

    # Forecast coverage
    forecast_coverage_status: str = ""

    # Plan A change tracking
    plan_a_change_reason: str = ""

    # LLM metrics
    llm_latency_ms: list[float] = field(default_factory=list)
    llm_failures: int = 0
    llm_fallbacks: int = 0

    # Option selection
    selected_option_label: str = ""
    option_switches: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "duration_ms": round(self.duration_ms, 2),
            "candidates_before_shortlist": self.candidates_before_shortlist,
            "candidates_after_shortlist": self.candidates_after_shortlist,
            "weather_latency_ms": [round(ms, 2) for ms in self.weather_latency_ms],
            "weather_errors": self.weather_errors,
            "weather_cache_hits": self.weather_cache_hits,
            "weather_cache_misses": self.weather_cache_misses,
            "forecast_coverage_status": self.forecast_coverage_status,
            "plan_a_change_reason": self.plan_a_change_reason,
            "llm_latency_ms": [round(ms, 2) for ms in self.llm_latency_ms],
            "llm_failures": self.llm_failures,
            "llm_fallbacks": self.llm_fallbacks,
            "selected_option_label": self.selected_option_label,
            "option_switches": self.option_switches,
        }


class MetricsCollector:
    """Collects and logs pipeline metrics across multiple plan generations."""

    def __init__(self, max_stored: int = MAX_STORED_METRICS):
        self._metrics: deque[PipelineMetrics] = deque(maxlen=max_stored)
        self._aggregated: dict[str, Any] = defaultdict(int)

    def start_generation(self) -> PipelineMetrics:
        """Start tracking a new plan generation."""
        metrics = PipelineMetrics(start_time=time.perf_counter())
        return metrics

    def finish_generation(self, metrics: PipelineMetrics) -> None:
        """Finish tracking and store metrics."""
        metrics.end_time = time.perf_counter()
        metrics.duration_ms = (metrics.end_time - metrics.start_time) * 1000
        self._metrics.append(metrics)
        self._log_metrics(metrics)

    def record_weather_latency(self, metrics: PipelineMetrics, latency_ms: float) -> None:
        metrics.weather_latency_ms.append(latency_ms)

    def record_weather_error(self, metrics: PipelineMetrics) -> None:
        metrics.weather_errors += 1

    def record_weather_cache_hit(self, metrics: PipelineMetrics) -> None:
        metrics.weather_cache_hits += 1

    def record_weather_cache_miss(self, metrics: PipelineMetrics) -> None:
        metrics.weather_cache_misses += 1

    def record_llm_latency(self, metrics: PipelineMetrics, latency_ms: float) -> None:
        metrics.llm_latency_ms.append(latency_ms)

    def record_llm_failure(self, metrics: PipelineMetrics) -> None:
        metrics.llm_failures += 1

    def record_llm_fallback(self, metrics: PipelineMetrics) -> None:
        metrics.llm_fallbacks += 1

    def record_option_switch(self, metrics: PipelineMetrics) -> None:
        metrics.option_switches += 1

    def _log_metrics(self, metrics: PipelineMetrics) -> None:
        logger.info(
            "📊 [Metrics] plan_id=%s duration=%.0fms candidates=%d→%d weather_errors=%d llm_failures=%d",
            metrics.plan_id or "unknown",
            metrics.duration_ms,
            metrics.candidates_before_shortlist,
            metrics.candidates_after_shortlist,
            metrics.weather_errors,
            metrics.llm_failures,
        )

    def get_summary(self) -> dict[str, Any]:
        """Get aggregated metrics summary."""
        if not self._metrics:
            return {"total_generations": 0}

        total = len(self._metrics)
        total_duration = sum(m.duration_ms for m in self._metrics)
        total_weather_errors = sum(m.weather_errors for m in self._metrics)
        total_llm_failures = sum(m.llm_failures for m in self._metrics)
        total_llm_fallbacks = sum(m.llm_fallbacks for m in self._metrics)

        return {
            "total_generations": total,
            "avg_duration_ms": round(total_duration / total, 2) if total else 0,
            "total_weather_errors": total_weather_errors,
            "total_llm_failures": total_llm_failures,
            "total_llm_fallbacks": total_llm_fallbacks,
            "weather_error_rate": round(total_weather_errors / total, 3) if total else 0,
            "llm_failure_rate": round(total_llm_failures / total, 3) if total else 0,
        }


metrics_collector = MetricsCollector()
