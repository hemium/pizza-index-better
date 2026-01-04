"""
Test fixtures for monitoring module tests.
"""

from datetime import datetime, timezone


SAMPLE_PIZZA_API_RESPONSE = {
    "success": True,
    "timestamp": "2026-01-03T10:56:49Z",
    "overall_index": 42,
    "defcon_level": 4,
    "active_spikes": 2,
    "has_active_spikes": True,
    "data_freshness": "live",
    "data": [
        {
            "place_id": "ChIJW69R5k1EwokR2l1v0w0o0",
            "name": "Pentagon Pizza",
            "current_popularity": 85,
            "percentage_of_usual": 180.5,
            "is_spike": True,
            "is_closed_now": False,
            "spike_magnitude": 80.5,
        },
        {
            "place_id": "ChIJW8R5k2EwokR2l1v0w1o1",
            "name": "White House Pizza",
            "current_popularity": 72,
            "percentage_of_usual": 145.0,
            "is_spike": True,
            "is_closed_now": False,
            "spike_magnitude": 45.0,
        },
        {
            "place_id": "ChIJW9R5k3EwokR2l1v0w2o2",
            "name": "Capitol Pizza",
            "current_popularity": 15,
            "percentage_of_usual": 30.0,
            "is_spike": False,
            "is_closed_now": True,
            "spike_magnitude": None,
        },
    ],
}

SAMPLE_PIZZA_API_RESPONSE_NO_SPIKES = {
    "success": True,
    "timestamp": "2026-01-03T11:00:00Z",
    "overall_index": 35,
    "defcon_level": 5,
    "active_spikes": 0,
    "has_active_spikes": False,
    "data_freshness": "live",
    "data": [
        {
            "place_id": "ChIJW69R5k1EwokR2l1v0w0o0",
            "name": "Pentagon Pizza",
            "current_popularity": 45,
            "percentage_of_usual": 95.0,
            "is_spike": False,
            "is_closed_now": False,
            "spike_magnitude": None,
        },
    ],
}

SAMPLE_PIZZA_API_RESPONSE_DEFCON_LOW = {
    "success": True,
    "timestamp": "2026-01-03T12:00:00Z",
    "overall_index": 78,
    "defcon_level": 2,
    "active_spikes": 5,
    "has_active_spikes": True,
    "data_freshness": "live",
    "data": [
        {
            "place_id": "ChIJW69R5k1EwokR2l1v0w0o0",
            "name": "Pentagon Pizza",
            "current_popularity": 95,
            "percentage_of_usual": 210.0,
            "is_spike": True,
            "is_closed_now": False,
            "spike_magnitude": 90.0,
        },
        {
            "place_id": "ChIJW8R5k2EwokR2l1v0w1o1",
            "name": "White House Pizza",
            "current_popularity": 88,
            "percentage_of_usual": 195.0,
            "is_spike": True,
            "is_closed_now": False,
            "spike_magnitude": 88.0,
        },
    ],
}

MALFORMED_API_RESPONSE = {
    "success": False,
    "error": "Internal server error",
}

MISSING_FIELDS_API_RESPONSE = {
    "success": True,
    "timestamp": "2026-01-03T10:56:49Z",
}
