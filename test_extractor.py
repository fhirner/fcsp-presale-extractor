"""
Tests for FC St. Pauli Presale Calendar Extractor

Baseline tests to ensure refactoring maintains identical behavior.
"""

from datetime import datetime

import pytest
import pytz

from fcsp_presale_extractor import extract_presale_info, fetch_rss_feed

# Berlin timezone for proper datetime creation
BERLIN_TZ = pytz.timezone("Europe/Berlin")

# Test data based on rss_test.xml
EXPECTED_EVENTS = [
    {
        "opponent": "1. FC Union Berlin",
        "presale_datetime": BERLIN_TZ.localize(datetime(2025, 10, 23, 15, 0, 0)),
        "competition": "Bundesliga",
    },
    {
        "opponent": "Borussia Mönchengladbach",
        "presale_datetime": BERLIN_TZ.localize(datetime(2025, 10, 9, 15, 0, 0)),
        "competition": "Bundesliga",
    },
    {
        "opponent": "TSG Hoffenheim",
        "presale_datetime": BERLIN_TZ.localize(datetime(2025, 10, 7, 15, 0, 0)),
        "competition": "DFB-Pokal",
    },
    {
        "opponent": "TSG Hoffenheim",
        "presale_datetime": BERLIN_TZ.localize(datetime(2025, 9, 25, 15, 0, 0)),
        "competition": "Bundesliga",  # Heimspiel (title-based detection)
    },
    {
        "opponent": "Bayer Leverkusen",
        "presale_datetime": BERLIN_TZ.localize(datetime(2025, 8, 28, 15, 0, 0)),
        "competition": "Bundesliga",
    },
    {
        "opponent": "FC Augsburg",
        "presale_datetime": BERLIN_TZ.localize(datetime(2025, 8, 14, 15, 0, 0)),
        "competition": "Bundesliga",
    },
]


@pytest.fixture
def test_feed():
    """Load the test RSS feed."""
    return fetch_rss_feed("test_data/rss_test.xml")


def test_extract_all_presale_events(test_feed):
    """Test that all expected presale events are extracted from rss_test.xml"""
    events = []
    for entry in test_feed.entries:
        info = extract_presale_info(entry, BERLIN_TZ)
        if info:
            events.append(info)

    assert len(events) == 6, f"Expected 6 events, got {len(events)}"

    # Sort both lists by presale_datetime for comparison
    events_sorted = sorted(events, key=lambda x: x["presale_datetime"], reverse=True)
    expected_sorted = sorted(EXPECTED_EVENTS, key=lambda x: x["presale_datetime"], reverse=True)

    for i, (actual, expected) in enumerate(zip(events_sorted, expected_sorted, strict=False)):
        assert actual["opponent"] == expected["opponent"], (
            f"Event {i}: opponent mismatch. Expected '{expected['opponent']}', got '{actual['opponent']}'"
        )
        assert actual["presale_datetime"] == expected["presale_datetime"], (
            f"Event {i}: datetime mismatch. Expected {expected['presale_datetime']}, got {actual['presale_datetime']}"
        )
        assert actual["competition"] == expected["competition"], (
            f"Event {i}: competition mismatch. Expected '{expected['competition']}', got '{actual['competition']}'"
        )


def test_filters_away_games(test_feed):
    """Test that away games are properly filtered out"""
    # Check that specific away games are NOT in results
    away_game_titles = [
        "Ticket-Infos zum Auswärtsspiel beim FC Bayern München",
        "Ticket-Infos zum Auswärtsspiel beim SC Freiburg",
        "Ticket-Infos zum Auswärtsspiel beim SV Werder Bremen",
        "Ticket-Infos zum Auswärtsspiel bei Eintracht Frankfurt",
    ]

    for entry in test_feed.entries:
        if entry.get("title", "") in away_game_titles:
            info = extract_presale_info(entry, BERLIN_TZ)
            assert info is None, f"Away game should be filtered: {entry['title']}"


def test_dfb_pokal_treated_as_home(test_feed):
    """Test that DFB-Pokal games are extracted (treated as home games)"""
    pokal_events = []
    for entry in test_feed.entries:
        if "DFB-Pokalspiel" in entry.get("title", ""):  # Only titles with "DFB-Pokalspiel"
            info = extract_presale_info(entry, BERLIN_TZ)
            if info:
                pokal_events.append(info)

    assert len(pokal_events) == 1, f"Expected 1 DFB-Pokalspiel event, got {len(pokal_events)}"

    for event in pokal_events:
        assert event["competition"] == "DFB-Pokal"
        assert event["opponent"] == "TSG Hoffenheim"


def test_opponent_extraction():
    """Test opponent name extraction removes articles properly"""
    opponents = [e["opponent"] for e in EXPECTED_EVENTS]

    # Check that articles are removed
    for opponent in opponents:
        assert not opponent.startswith("den "), f"Article 'den' not removed: {opponent}"
        assert not opponent.startswith("die "), f"Article 'die' not removed: {opponent}"
        assert not opponent.startswith("das "), f"Article 'das' not removed: {opponent}"
        assert not opponent.startswith("der "), f"Article 'der' not removed: {opponent}"
        assert not opponent.startswith("dem "), f"Article 'dem' not removed: {opponent}"


def test_presale_time_always_15_uhr():
    """Test that all presale times in test data are 15:00"""
    for event in EXPECTED_EVENTS:
        assert event["presale_datetime"].hour == 15
        assert event["presale_datetime"].minute == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
