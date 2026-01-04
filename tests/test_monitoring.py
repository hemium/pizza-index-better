"""
Tests for monitoring module.
"""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aioresponses import aioresponses

from app.monitoring import (
    BaselineTracker,
    LocationData,
    PizzaData,
    PizzaMonitor,
    Signal,
    SignalDetector,
    SignalType,
)
from tests.fixtures.pizza_responses import (
    MALFORMED_API_RESPONSE,
    MISSING_FIELDS_API_RESPONSE,
    SAMPLE_PIZZA_API_RESPONSE,
    SAMPLE_PIZZA_API_RESPONSE_DEFCON_LOW,
    SAMPLE_PIZZA_API_RESPONSE_NO_SPIKES,
)


@pytest.mark.asyncio
class TestPizzaMonitor:
    """Tests for PizzaMonitor class."""

    async def test_fetch_success(self):
        """Test successful data fetch from PizzINT API."""
        api_url = "https://www.pizzint.watch/api/dashboard-data"

        with aioresponses() as m:
            m.get(api_url, status=200, payload=SAMPLE_PIZZA_API_RESPONSE)

            monitor = PizzaMonitor(api_url)
            pizza_data = await monitor.fetch()

            assert pizza_data.overall_index == 42
            assert pizza_data.defcon_level == 4
            assert pizza_data.active_spikes == 2
            
            print(f"\n[METRICS] Pizza Index: {pizza_data.overall_index}")
            print(f"[METRICS] DEFCON Level: {pizza_data.defcon_level}")
            print(f"[METRICS] Active Spikes: {pizza_data.active_spikes}")
            
            assert pizza_data.has_active_spikes is True
            assert pizza_data.data_freshness == "live"
            assert len(pizza_data.locations) == 3
            assert pizza_data.locations[0].name == "Pentagon Pizza"
            assert pizza_data.locations[0].is_spike is True
            assert pizza_data.locations[2].is_closed_now is True

            await monitor.close()

    async def test_fetch_with_cache(self):
        """Test caching behavior - same data returned within TTL."""
        api_url = "https://www.pizzint.watch/api/dashboard-data"

        with aioresponses() as m:
            m.get(api_url, status=200, payload=SAMPLE_PIZZA_API_RESPONSE)

            monitor = PizzaMonitor(api_url, cache_ttl=60)

            data1 = await monitor.fetch()
            data2 = await monitor.fetch()

            assert data1.overall_index == data2.overall_index

            m.assert_called_once()

            await monitor.close()

    async def test_fetch_api_error(self):
        """Test handling of API failures."""
        api_url = "https://www.pizzint.watch/api/dashboard-data"

        with aioresponses() as m:
            m.get(api_url, status=500, payload={"error": "Internal server error"})

            monitor = PizzaMonitor(api_url)

            with pytest.raises(Exception):
                await monitor.fetch()

            await monitor.close()

    async def test_get_defcon_change(self):
        """Test DEFCON change detection between fetches."""
        api_url = "https://www.pizzint.watch/api/dashboard-data"

        with aioresponses() as m:
            m.get(api_url, status=200, payload=SAMPLE_PIZZA_API_RESPONSE)
            m.get(api_url, status=200, payload=SAMPLE_PIZZA_API_RESPONSE_DEFCON_LOW)

            monitor = PizzaMonitor(api_url, cache_ttl=0)

            data1 = await monitor.fetch()
            assert data1.defcon_level == 4

            change = monitor.get_defcon_change()
            assert change is None

            data2 = await monitor.fetch()
            assert data2.defcon_level == 2

            change = monitor.get_defcon_change()
            assert change == 2

            await monitor.close()

    async def test_location_data_parsing(self):
        """Test parsing of location-specific data."""
        api_url = "https://www.pizzint.watch/api/dashboard-data"

        with aioresponses() as m:
            m.get(api_url, status=200, payload=SAMPLE_PIZZA_API_RESPONSE)

            monitor = PizzaMonitor(api_url)
            pizza_data = await monitor.fetch()

            location = pizza_data.locations[0]
            assert isinstance(location, LocationData)
            assert location.place_id == "ChIJW69R5k1EwokR2l1v0w0o0"
            assert location.name == "Pentagon Pizza"
            assert location.current_popularity == 85
            assert location.percentage_of_usual == 180.5
            assert location.is_spike is True
            assert location.is_closed_now is False
            assert location.spike_magnitude == 80.5

            await monitor.close()


@pytest.mark.asyncio
class TestSignalDetector:
    """Tests for SignalDetector class."""

    async def test_defcon_change(self):
        """Test DEFCON change signal detection."""
        detector = SignalDetector(defcon_threshold=3)

        historical_data = PizzaData(
            timestamp=datetime.now(timezone.utc),
            overall_index=50,
            defcon_level=4,
            active_spikes=0,
            has_active_spikes=False,
            data_freshness="live",
            locations=[],
        )

        detector._history.append(historical_data)

        new_data = PizzaData(
            timestamp=datetime.now(timezone.utc),
            overall_index=65,
            defcon_level=2,
            active_spikes=3,
            has_active_spikes=True,
            data_freshness="live",
            locations=[],
        )

        signals = detector.analyze(new_data)

        assert len(signals) == 1
        assert signals[0].type == SignalType.DEFCON_CHANGE
        assert signals[0].confidence == 0.8
        assert signals[0].data["previous_defcon"] == 4
        assert signals[0].data["current_defcon"] == 2
        assert signals[0].data["drop"] == 2
        assert signals[0].metadata["severity"] == "high"

    async def test_defcon_no_change(self):
        """Test no signal when DEFCON unchanged."""
        detector = SignalDetector(defcon_threshold=3)

        historical_data = PizzaData(
            timestamp=datetime.now(timezone.utc),
            overall_index=50,
            defcon_level=4,
            active_spikes=0,
            has_active_spikes=False,
            data_freshness="live",
            locations=[],
        )

        detector._history.append(historical_data)

        new_data = PizzaData(
            timestamp=datetime.now(timezone.utc),
            overall_index=52,
            defcon_level=4,
            active_spikes=0,
            has_active_spikes=False,
            data_freshness="live",
            locations=[],
        )

        signals = detector.analyze(new_data)

        defcon_signals = [s for s in signals if s.type == SignalType.DEFCON_CHANGE]
        assert len(defcon_signals) == 0

    async def test_single_spike(self):
        """Test single location spike detection."""
        detector = SignalDetector(spike_threshold=1)

        data = PizzaData(
            timestamp=datetime.now(timezone.utc),
            overall_index=60,
            defcon_level=4,
            active_spikes=1,
            has_active_spikes=True,
            data_freshness="live",
            locations=[
                LocationData(
                    place_id="1",
                    name="Pizza Place",
                    current_popularity=85,
                    is_spike=True,
                    is_closed_now=False,
                )
            ],
        )

        signals = detector.analyze(data)

        assert len(signals) == 1
        assert signals[0].type == SignalType.SPIKE_DETECTED
        assert signals[0].confidence == 0.5

    async def test_multi_spike(self):
        """Test multi-location spike detection."""
        detector = SignalDetector(spike_threshold=2)

        data = PizzaData(
            timestamp=datetime.now(timezone.utc),
            overall_index=70,
            defcon_level=3,
            active_spikes=3,
            has_active_spikes=True,
            data_freshness="live",
            locations=[
                LocationData(
                    place_id="1",
                    name="Pizza Place 1",
                    current_popularity=85,
                    is_spike=True,
                    is_closed_now=False,
                ),
                LocationData(
                    place_id="2",
                    name="Pizza Place 2",
                    current_popularity=80,
                    is_spike=True,
                    is_closed_now=False,
                ),
                LocationData(
                    place_id="3",
                    name="Pizza Place 3",
                    current_popularity=75,
                    is_spike=True,
                    is_closed_now=False,
                ),
            ],
        )

        signals = detector.analyze(data)

        spike_signals = [s for s in signals if s.type == SignalType.MULTI_SPIKE]
        assert len(spike_signals) == 1
        assert spike_signals[0].confidence == pytest.approx(0.7)

    async def test_spike_ignores_closed(self):
        """Test spikes at closed locations are ignored."""
        detector = SignalDetector(spike_threshold=2)

        data = PizzaData(
            timestamp=datetime.now(timezone.utc),
            overall_index=55,
            defcon_level=4,
            active_spikes=2,
            has_active_spikes=True,
            data_freshness="live",
            locations=[
                LocationData(
                    place_id="1",
                    name="Pizza Place 1",
                    current_popularity=85,
                    is_spike=True,
                    is_closed_now=False,
                ),
                LocationData(
                    place_id="2",
                    name="Pizza Place 2",
                    current_popularity=90,
                    is_spike=True,
                    is_closed_now=True,
                ),
            ],
        )

        signals = detector.analyze(data)

        assert len(signals) == 0

    async def test_off_hours_surge(self):
        """Test off-hours surge detection (midnight-6am ET)."""
        detector = SignalDetector()

        # 3 AM ET = 8 AM UTC (EST) or 7 AM UTC (EDT)
        # Using a specific datetime that represents 3 AM ET
        off_hours_time = datetime(2025, 1, 4, 8, 0, 0, tzinfo=timezone.utc)

        data = PizzaData(
            timestamp=off_hours_time,
            overall_index=70,
            defcon_level=2,
            active_spikes=2,
            has_active_spikes=True,
            data_freshness="live",
            locations=[],
        )

        signals = detector.analyze(data)

        off_hours_signals = [
            s for s in signals if s.type == SignalType.OFF_HOURS_SURGE
        ]
        assert len(off_hours_signals) == 1
        assert off_hours_signals[0].confidence == 0.85

    async def test_z_score_insufficient_history(self):
        """Test Z-score requires 30+ data points."""
        detector = SignalDetector()

        for i in range(29):
            data = PizzaData(
                timestamp=datetime.now(timezone.utc),
                overall_index=50,
                defcon_level=4,
                active_spikes=0,
                has_active_spikes=False,
                data_freshness="live",
                locations=[],
            )
            detector.analyze(data)

        new_data = PizzaData(
            timestamp=datetime.now(timezone.utc),
            overall_index=90,
            defcon_level=1,
            active_spikes=5,
            has_active_spikes=True,
            data_freshness="live",
            locations=[],
        )

        signals = detector.analyze(new_data)

        zscore_signals = [s for s in signals if s.type == SignalType.Z_SCORE_ANOMALY]
        assert len(zscore_signals) == 0

    async def test_z_score_anomaly(self):
        """Test Z-score anomaly detection."""
        detector = SignalDetector()

        for i in range(50):
            data = PizzaData(
                timestamp=datetime.now(timezone.utc),
                overall_index=50 + (i % 5) * 2,
                defcon_level=4,
                active_spikes=0,
                has_active_spikes=False,
                data_freshness="live",
                locations=[],
            )
            detector.analyze(data)

        new_data = PizzaData(
            timestamp=datetime.now(timezone.utc),
            overall_index=80,
            defcon_level=2,
            active_spikes=3,
            has_active_spikes=True,
            data_freshness="live",
            locations=[],
        )

        signals = detector.analyze(new_data)

        zscore_signals = [s for s in signals if s.type == SignalType.Z_SCORE_ANOMALY]
        assert len(zscore_signals) == 1
        z_score = zscore_signals[0].data["z_score"]
        print(f"\n[ANOMALY] Captured Z-Score: {z_score:.2f}")
        assert abs(z_score) >= 2.0

    async def test_multiple_signals(self):
        """Test detection of multiple signal types simultaneously."""
        detector = SignalDetector()

        historical_data = PizzaData(
            timestamp=datetime.now(timezone.utc),
            overall_index=50,
            defcon_level=4,
            active_spikes=0,
            has_active_spikes=False,
            data_freshness="live",
            locations=[],
        )
        detector._history.append(historical_data)

        new_data = PizzaData(
            timestamp=datetime.now(timezone.utc),
            overall_index=80,
            defcon_level=2,
            active_spikes=3,
            has_active_spikes=True,
            data_freshness="live",
            locations=[
                LocationData(
                    place_id="1",
                    name="Pizza Place 1",
                    current_popularity=85,
                    is_spike=True,
                    is_closed_now=False,
                ),
                LocationData(
                    place_id="2",
                    name="Pizza Place 2",
                    current_popularity=80,
                    is_spike=True,
                    is_closed_now=False,
                ),
            ],
        )

        signals = detector.analyze(new_data)

        signal_types = [s.type for s in signals]
        assert SignalType.DEFCON_CHANGE in signal_types
        assert SignalType.MULTI_SPIKE in signal_types

    async def test_confidence_threshold(self):
        """Test signals below threshold are still returned."""
        detector = SignalDetector(confidence_threshold=0.7, spike_threshold=1)

        data = PizzaData(
            timestamp=datetime.now(timezone.utc),
            overall_index=55,
            defcon_level=4,
            active_spikes=1,
            has_active_spikes=True,
            data_freshness="live",
            locations=[
                LocationData(
                    place_id="1",
                    name="Pizza Place",
                    current_popularity=75,
                    is_spike=True,
                    is_closed_now=False,
                )
            ],
        )

        signals = detector.analyze(data)

        assert len(signals) == 1
        assert signals[0].confidence == 0.5


class TestBaselineTracker:
    """Tests for BaselineTracker class."""

    def test_initialization(self):
        """Test BaselineTracker creates hourly arrays."""
        tracker = BaselineTracker(window_size=24)

        assert tracker.window_size == 24
        assert isinstance(tracker._hourly_baselines, dict)

    def test_add_observation(self):
        """Test adding observations updates hourly baseline."""
        tracker = BaselineTracker(window_size=24)

        data = PizzaData(
            timestamp=datetime(2026, 1, 3, 14, 0, 0, tzinfo=timezone.utc),
            overall_index=55,
            defcon_level=4,
            active_spikes=0,
            has_active_spikes=False,
            data_freshness="live",
            locations=[],
        )

        tracker.add_observation(data)

        assert 14 in tracker._hourly_baselines
        assert len(tracker._hourly_baselines[14]) == 1
        assert tracker._hourly_baselines[14][0] == 55

    def test_window_size_limit(self):
        """Test window_size limit enforced."""
        tracker = BaselineTracker(window_size=5)

        for i in range(10):
            data = PizzaData(
                timestamp=datetime(2026, 1, 3, 14, i, 0, tzinfo=timezone.utc),
                overall_index=50 + i,
                defcon_level=4,
                active_spikes=0,
                has_active_spikes=False,
                data_freshness="live",
                locations=[],
            )
            tracker.add_observation(data)

        assert len(tracker._hourly_baselines[14]) == 5
        assert tracker._hourly_baselines[14][0] == 55

    def test_get_expected_range(self):
        """Test expected range calculation (mean ± 2std)."""
        tracker = BaselineTracker()

        for i in range(50):
            data = PizzaData(
                timestamp=datetime(2026, 1, 3, 14, i, 0, tzinfo=timezone.utc),
                overall_index=50 + (i % 10) - 5,
                defcon_level=4,
                active_spikes=0,
                has_active_spikes=False,
                data_freshness="live",
                locations=[],
            )
            tracker.add_observation(data)

        lower, upper = tracker.get_expected_range(14)

        assert lower < 50.0
        assert upper > 50.0
        assert upper > lower

    def test_get_expected_range_no_data(self):
        """Test expected range with no data returns default."""
        tracker = BaselineTracker()

        lower, upper = tracker.get_expected_range(14)

        assert lower == 30.0
        assert upper == 70.0

    def test_is_anomalous(self):
        """Test anomaly detection."""
        tracker = BaselineTracker()

        for i in range(50):
            data = PizzaData(
                timestamp=datetime(2026, 1, 3, 14, i, 0, tzinfo=timezone.utc),
                overall_index=50,
                defcon_level=4,
                active_spikes=0,
                has_active_spikes=False,
                data_freshness="live",
                locations=[],
            )
            tracker.add_observation(data)

        normal_data = PizzaData(
            timestamp=datetime(2026, 1, 3, 14, 50, 0, tzinfo=timezone.utc),
            overall_index=50,
            defcon_level=4,
            active_spikes=0,
            has_active_spikes=False,
            data_freshness="live",
            locations=[],
        )

        assert tracker.is_anomalous(normal_data) is False

        high_data = PizzaData(
            timestamp=datetime(2026, 1, 3, 14, 51, 0, tzinfo=timezone.utc),
            overall_index=90,
            defcon_level=2,
            active_spikes=3,
            has_active_spikes=True,
            data_freshness="live",
            locations=[],
        )

        assert tracker.is_anomalous(high_data) is True

    def test_hourly_separation(self):
        """Test observations separated by hour."""
        tracker = BaselineTracker()

        data1 = PizzaData(
            timestamp=datetime(2026, 1, 3, 0, 0, 0, tzinfo=timezone.utc),
            overall_index=50,
            defcon_level=4,
            active_spikes=0,
            has_active_spikes=False,
            data_freshness="live",
            locations=[],
        )

        data2 = PizzaData(
            timestamp=datetime(2026, 1, 3, 1, 0, 0, tzinfo=timezone.utc),
            overall_index=55,
            defcon_level=4,
            active_spikes=0,
            has_active_spikes=False,
            data_freshness="live",
            locations=[],
        )

        tracker.add_observation(data1)
        tracker.add_observation(data2)

        assert len(tracker._hourly_baselines[0]) == 1
        assert len(tracker._hourly_baselines[1]) == 1

    async def test_summary_metrics_display(self):
        """Hidden test to just dump metrics for visibility when requested."""
        from tests.fixtures.pizza_responses import SAMPLE_PIZZA_API_RESPONSE
        
        print("\n" + "="*40)
        print("PIZZA INDEX MONITORING SUMMARY")
        print("="*40)
        print(f"Overall Index: {SAMPLE_PIZZA_API_RESPONSE['overall_index']}")
        print(f"DEFCON Level:  {SAMPLE_PIZZA_API_RESPONSE['defcon_level']}")
        print(f"Active Spikes: {SAMPLE_PIZZA_API_RESPONSE['active_spikes']}")
        print("-"*40)
        for loc in SAMPLE_PIZZA_API_RESPONSE['data']:
            spike_str = "!!! SPIKE !!!" if loc['is_spike'] else "Normal"
            print(f"Location: {loc['name']:<20} | Status: {spike_str:<12} | Pop: {loc['current_popularity']}%")
        print("="*40)
