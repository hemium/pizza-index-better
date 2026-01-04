"""
Signal detection - analyzes pizza data to detect trading signals.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from zoneinfo import ZoneInfo

from app.config import settings
from app.monitoring.pizza_monitor import PizzaData


logger = logging.getLogger(__name__)


class SignalType(Enum):
    """Types of signals that can be detected."""

    DEFCON_CHANGE = "defcon_change"
    SPIKE_DETECTED = "spike_detected"
    MULTI_SPIKE = "multi_spike"
    OFF_HOURS_SURGE = "off_hours_surge"
    Z_SCORE_ANOMALY = "z_score_anomaly"


@dataclass
class Signal:
    """A detected trading signal."""

    type: SignalType
    confidence: float
    timestamp: datetime
    data: dict[str, Any]
    metadata: dict[str, Any]
    processed: bool = False


class BaselineTracker:
    """Tracks historical baselines for anomaly detection."""

    def __init__(self, window_size: int = 168):
        self.window_size = window_size
        self._hourly_baselines: dict[int, list[float]] = {}

    def add_observation(self, data: PizzaData) -> None:
        """Add a new observation to the baseline."""
        hour = data.timestamp.hour
        if hour not in self._hourly_baselines:
            self._hourly_baselines[hour] = []

        self._hourly_baselines[hour].append(data.overall_index)

        if len(self._hourly_baselines[hour]) > self.window_size:
            self._hourly_baselines[hour].pop(0)

    def get_expected_range(self, hour: int) -> tuple[float, float]:
        """Get expected range (mean ± 2std) for given hour."""
        if hour not in self._hourly_baselines or len(self._hourly_baselines[hour]) < 2:
            return (30.0, 70.0)

        values = self._hourly_baselines[hour]
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        std = variance ** 0.5

        if std == 0:
            return (mean - 10, mean + 10)

        return (mean - 2 * std, mean + 2 * std)

    def is_anomalous(self, data: PizzaData) -> bool:
        """Check if current data is anomalous for this time."""
        hour = data.timestamp.hour
        lower, upper = self.get_expected_range(hour)
        return data.overall_index < lower or data.overall_index > upper


class SignalDetector:
    """Detects trading signals from pizza index data."""

    def __init__(
        self,
        defcon_threshold: int = 3,
        spike_threshold: int = 2,
        confidence_threshold: float = 0.7,
    ):
        self.defcon_threshold = defcon_threshold
        self.spike_threshold = spike_threshold
        self.confidence_threshold = confidence_threshold
        self._history: list[PizzaData] = []
        self._baseline = BaselineTracker()

    def analyze(self, data: PizzaData) -> list[Signal]:
        """Analyze pizza data and return detected signals."""
        signals = []

        if signal := self._check_defcon_change(data):
            signals.append(signal)

        if signal := self._check_spikes(data):
            signals.append(signal)

        if signal := self._check_off_hours(data):
            signals.append(signal)

        if signal := self._check_z_score(data):
            signals.append(signal)

        self._history.append(data)
        self._baseline.add_observation(data)

        if len(self._history) > 1000:
            self._history = self._history[-500:]

        return signals

    def _check_defcon_change(self, data: PizzaData) -> Signal | None:
        """Check for DEFCON level change."""
        if not self._history:
            return None

        prev_defcon = self._history[-1].defcon_level
        curr_defcon = data.defcon_level

        if curr_defcon <= self.defcon_threshold and curr_defcon < prev_defcon:
            drop = prev_defcon - curr_defcon
            confidence = min(0.5 + (drop * 0.15), 1.0)

            severity = "high" if curr_defcon <= 2 else "medium"

            return Signal(
                type=SignalType.DEFCON_CHANGE,
                confidence=confidence,
                timestamp=datetime.now(timezone.utc),
                data={
                    "previous_defcon": prev_defcon,
                    "current_defcon": curr_defcon,
                    "drop": drop,
                },
                metadata={"severity": severity},
            )

        return None

    def _check_spikes(self, data: PizzaData) -> Signal | None:
        """Check for location spikes."""
        spiking_locations = [
            loc for loc in data.locations
            if loc.is_spike and not loc.is_closed_now
        ]

        if len(spiking_locations) >= self.spike_threshold:
            confidence = min(0.4 + (len(spiking_locations) * 0.1), 0.95)

            signal_type = (
                SignalType.MULTI_SPIKE
                if len(spiking_locations) > 1
                else SignalType.SPIKE_DETECTED
            )

            return Signal(
                type=signal_type,
                confidence=confidence,
                timestamp=datetime.now(timezone.utc),
                data={
                    "spike_count": len(spiking_locations),
                    "locations": [loc.name for loc in spiking_locations],
                },
                metadata={},
            )

        return None

    def _check_off_hours(self, data: PizzaData) -> Signal | None:
        """Check for off-hours surge (midnight-6am ET)."""
        current_hour = data.timestamp.astimezone(ZoneInfo("America/New_York")).hour

        off_hours_start = settings.OFF_HOURS_START
        off_hours_end = settings.OFF_HOURS_END

        is_off_hours = off_hours_start <= current_hour < off_hours_end

        if is_off_hours and (data.has_active_spikes or data.defcon_level <= 3):
            return Signal(
                type=SignalType.OFF_HOURS_SURGE,
                confidence=0.85,
                timestamp=datetime.now(timezone.utc),
                data={
                    "defcon": data.defcon_level,
                    "active_spikes": data.active_spikes,
                },
                metadata={"hour": current_hour},
            )

        return None

    def _check_z_score(self, data: PizzaData) -> Signal | None:
        """Check for statistical anomaly using Z-score."""
        if len(self._history) < 30:
            return None

        indices = [h.overall_index for h in self._history[-100:]]
        mean = sum(indices) / len(indices)
        variance = sum((x - mean) ** 2 for x in indices) / len(indices)
        std = variance ** 0.5

        if std == 0:
            return None

        z_score = (data.overall_index - mean) / std

        if abs(z_score) >= 2.0:
            confidence = min(0.6 + (abs(z_score) - 2.0) * 0.1, 0.95)

            return Signal(
                type=SignalType.Z_SCORE_ANOMALY,
                confidence=confidence,
                timestamp=datetime.now(timezone.utc),
                data={
                    "z_score": z_score,
                    "current_index": data.overall_index,
                    "mean": mean,
                    "std": std,
                },
                metadata={"direction": "high" if z_score > 0 else "low"},
            )

        return None
