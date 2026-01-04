"""
Pizza Index monitor - fetches data from PizzINT.watch API.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import aiohttp

from app.config import settings


logger = logging.getLogger(__name__)


@dataclass
class LocationData:
    """Data for a single monitored location."""

    place_id: str
    name: str
    current_popularity: int
    percentage_of_usual: float | None = None
    is_spike: bool = False
    is_closed_now: bool = False
    spike_magnitude: float | None = None


@dataclass
class PizzaData:
    """Raw pizza index data from API."""

    timestamp: datetime
    overall_index: int
    defcon_level: int
    active_spikes: int
    has_active_spikes: bool
    data_freshness: str
    locations: list[LocationData]


class PizzaMonitor:
    """Monitors Pizza Index data from PizzINT API."""

    def __init__(self, api_url: str, cache_ttl: int = 60):
        self.api_url = api_url
        self.cache_ttl = cache_ttl
        self._last_data: PizzaData | None = None
        self._last_fetch: datetime | None = None
        self._last_defcon: int | None = None
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                skip_auto_headers=["Accept-Encoding"],
            )
        return self._session

    async def fetch(self) -> PizzaData:
        """Fetch current pizza index data."""
        now = datetime.now(timezone.utc)

        if self._last_data and self._last_fetch:
            age_seconds = (now - self._last_fetch).total_seconds()
            if age_seconds < self.cache_ttl:
                logger.debug(f"Returning cached data (age: {age_seconds:.1f}s)")
                return self._last_data

        logger.info(f"Fetching pizza index data from {self.api_url}")

        try:
            session = await self._get_session()
            headers = {"Accept-Encoding": "identity"}
            async with session.get(self.api_url, headers=headers) as response:
                response.raise_for_status()
                data = await response.json()

                pizza_data = self._parse_response(data)

                self._last_defcon = self._last_data.defcon_level if self._last_data else None
                self._last_data = pizza_data
                self._last_fetch = now

                logger.info(
                    f"Fetched: Index={pizza_data.overall_index}, "
                    f"DEFCON={pizza_data.defcon_level}, "
                    f"Spikes={pizza_data.active_spikes}, "
                    f"Freshness={pizza_data.data_freshness}"
                )

                return pizza_data

        except aiohttp.ClientError as e:
            logger.error(f"Failed to fetch pizza data: {e}")
            if self._last_data:
                logger.warning("Returning cached data due to fetch failure")
                return self._last_data
            raise

        except Exception as e:
            logger.error(f"Unexpected error fetching pizza data: {e}", exc_info=True)
            raise

    def _parse_response(self, data: dict[str, Any]) -> PizzaData:
        """Parse API response into PizzaData object."""
        if not data.get("success", False):
            raise ValueError(f"API returned unsuccessful response: {data}")

        timestamp_str = data.get("timestamp")
        if timestamp_str:
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        else:
            timestamp = datetime.now(timezone.utc)

        locations = []
        for loc_data in data.get("data", []):
            location = LocationData(
                place_id=loc_data.get("place_id", ""),
                name=loc_data.get("name", ""),
                current_popularity=loc_data.get("current_popularity", 0),
                percentage_of_usual=loc_data.get("percentage_of_usual"),
                is_spike=loc_data.get("is_spike", False),
                is_closed_now=loc_data.get("is_closed_now", False),
                spike_magnitude=loc_data.get("spike_magnitude"),
            )
            locations.append(location)

        return PizzaData(
            timestamp=timestamp,
            overall_index=data.get("overall_index", 0),
            defcon_level=data.get("defcon_level", 5),
            active_spikes=data.get("active_spikes", 0),
            has_active_spikes=data.get("has_active_spikes", False),
            data_freshness=data.get("data_freshness", "unknown"),
            locations=locations,
        )

    def get_defcon_change(self) -> int | None:
        """Get DEFCON level change since last fetch."""
        if self._last_data is None or self._last_defcon is None:
            return None
        return self._last_defcon - self._last_data.defcon_level

    async def close(self) -> None:
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
