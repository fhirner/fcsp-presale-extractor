#!/usr/bin/env python3
"""
FC St. Pauli Presale Calendar Extractor

Extracts ticket presale dates for club members from FC St. Pauli RSS feed
and generates an iCalendar file.

Outputs iCalendar data to stdout - use shell redirection to save to file:
    python fcsp_presale_extractor.py > presale.ics

Parsing Strategy:
- Match type: Determined from title ("auswärtsspiel"/"beim" → away, skip)
- Opponent: Extracted from title ("gegen OPPONENT")
- Competition: Extracted from title ("pokal" → DFB-Pokal, else Bundesliga)
- Presale date: Extracted from description (date before "können Vereinsmitglieder")
"""

import argparse
import logging
import re
import sys
from datetime import datetime, timedelta
from html import unescape

import feedparser
import pytz
from icalendar import Alarm, Calendar, Event

# Module-level logger (will be configured in main)
logger = logging.getLogger(__name__)

# Regex pattern for presale date extraction
# Find date in format (DD.MM., [ab] HH[:MM] Uhr) that appears before "können Vereinsmitglieder"
# Examples: "(23.10., 15 Uhr)", "(7.10., 15:30 Uhr)", "(15.1., ab 15 Uhr)"
# "ab" prefix is optional (means "from/starting at")
# Minutes are optional (defaults to 00 if not specified)
PRESALE_PATTERN = re.compile(
    r"\((\d{1,2})\.(\d{1,2})\.,?\s+(?:ab\s+)?(\d{1,2})(?::(\d{2}))?\s+Uhr\)[^(]*können\s+Vereinsmitglieder",
    re.IGNORECASE | re.DOTALL,
)


def fetch_rss_feed(url: str) -> feedparser.FeedParserDict:
    """Fetch and parse RSS feed."""
    logger.info(f"Fetching RSS feed from {url}")
    feed = feedparser.parse(url)
    if feed.bozo:
        logger.warning(f"Feed parsing warning: {feed.bozo_exception}")
    logger.info(f"Found {len(feed.entries)} entries in feed")
    return feed


def is_home_game_ticket(title: str) -> bool:
    """
    Check if title indicates a home game ticket sale.

    Args:
        title: RSS entry title

    Returns:
        True if this is a home game ticket announcement, False otherwise
    """
    if not title.startswith("Ticket-Infos"):
        return False
    title_lower = title.lower()
    return "auswärtsspiel" not in title_lower and "beim" not in title_lower


def extract_opponent(title: str) -> str:
    """
    Extract opponent name from title.

    Args:
        title: RSS entry title

    Returns:
        Opponent name with German articles removed

    Example:
        "Ticket-Infos zum Heimspiel gegen den 1. FC Union Berlin"
        → "1. FC Union Berlin"
        "Ticket-Infos zum Derby-Heimspiel"
        → "Hamburger SV"
    """
    # Special case: Derby games (Hamburg Derby vs HSV)
    if "derby" in title.lower():
        return "Hamburger SV"

    # Pattern: "gegen OPPONENT [optional year suffix like 2526]"
    # Remove German articles (den, die, das, der, dem) and optional year
    opponent_match = re.search(
        r"gegen\s+(?:den|die|das|der|dem)?\s*(.+?)(?:\s+\d{4})?$", title, re.IGNORECASE
    )
    return opponent_match.group(1).strip() if opponent_match else "Gegner unbekannt"


def extract_competition(title: str) -> str:
    """
    Extract competition type from title.

    Args:
        title: RSS entry title

    Returns:
        "DFB-Pokal" if title contains "pokal", otherwise "Bundesliga"
    """
    return "DFB-Pokal" if "pokal" in title.lower() else "Bundesliga"


def extract_presale_datetime(
    description: str, pub_date_struct, title: str, timezone: pytz.timezone
) -> datetime | None:
    """
    Extract presale datetime from description.

    Finds date pattern (DD.MM., HH:MM Uhr) before "können Vereinsmitglieder"
    and determines the correct year based on publication date.

    Args:
        description: RSS entry description (may contain HTML)
        pub_date_struct: Publication date struct from RSS entry
        title: Title for logging purposes
        timezone: Timezone for presale datetime

    Returns:
        datetime object with presale datetime, or None if not found
    """
    # Strip HTML tags from description
    clean_description = re.sub(r"<[^>]+>", "", description)
    # Decode HTML entities
    clean_description = unescape(clean_description)

    # Search for presale date pattern
    match = PRESALE_PATTERN.search(clean_description)

    if not match:
        logger.debug(f"No presale pattern match in: {title}")
        logger.debug(f"Clean description snippet: {clean_description[:200]}")
        return None

    day, month, hour, minute = match.groups()

    # Handle optional minutes (default to 00 if not specified)
    if minute is None:
        minute = "00"

    # Determine year based on RSS publication date
    if pub_date_struct:
        pub_year = pub_date_struct.tm_year
        pub_date = datetime(
            pub_date_struct.tm_year,
            pub_date_struct.tm_mon,
            pub_date_struct.tm_mday,
            tzinfo=timezone,
        )
    else:
        # Fallback if no publication date (shouldn't happen)
        logger.warning(f"No publication date found for {title}, using current year")
        pub_year = datetime.now(timezone).year
        pub_date = datetime.now(timezone)

    presale_month = int(month)
    presale_day = int(day)
    year = pub_year

    try:
        # Create test presale date to check if it's before publication
        test_presale_date = timezone.localize(
            datetime(year=year, month=presale_month, day=presale_day, hour=0, minute=0)
        )

        # If presale date is before publication date, it must be next year
        # (e.g., article published Dec 2025, mentions presale in Jan → must be Jan 2026)
        if test_presale_date.replace(tzinfo=None) < pub_date.replace(tzinfo=None):
            year += 1
            logger.debug(
                f"Presale date {presale_day}.{presale_month}. before publication, using year {year}"
            )

        # Create final presale datetime with correct year
        return timezone.localize(
            datetime(
                year=year, month=presale_month, day=presale_day, hour=int(hour), minute=int(minute)
            )
        )

    except (ValueError, OverflowError) as e:
        logger.error(f"Error parsing date from {title}: {e}")
        return None


def extract_presale_info(entry: dict, timezone: pytz.timezone) -> dict | None:
    """
    Extract presale information from RSS entry using helper functions.

    Uses title-based logic to filter and extract:
    - Filters home game ticket announcements
    - Extracts opponent, competition, and presale datetime

    Args:
        entry: RSS feed entry with 'title', 'description', 'link', 'published_parsed'
        timezone: Timezone for presale datetime

    Returns:
        Dictionary with presale_datetime, opponent, competition, title, link, description
        or None if not a valid presale announcement
    """
    title = entry.get("title", "")
    description = entry.get("description", "")
    link = entry.get("link", "")

    # Check if this is a home game ticket announcement
    if not is_home_game_ticket(title):
        if title.startswith("Ticket-Infos"):
            logger.debug(f"Skipping away game: {title}")
        return None

    logger.debug(f"Found Ticket-Infos entry: {title}")

    # Extract presale datetime
    presale_dt = extract_presale_datetime(
        description, entry.get("published_parsed"), title, timezone
    )
    if not presale_dt:
        return None

    # Extract opponent and competition from title
    opponent = extract_opponent(title)
    competition = extract_competition(title)

    return {
        "presale_datetime": presale_dt,
        "opponent": opponent,
        "competition": competition,
        "title": title,
        "link": link,
        "description": description,
    }


def create_calendar_event(presale_info: dict, timezone: pytz.timezone) -> Event:
    """
    Create iCalendar event for presale.

    Args:
        presale_info: Dictionary with presale information
        timezone: Timezone for timestamp

    Returns:
        iCalendar Event object
    """
    event = Event()

    presale_dt = presale_info["presale_datetime"]
    opponent = presale_info["opponent"]
    competition = presale_info["competition"]
    link = presale_info["link"]

    # Event summary (title)
    event.add("summary", f"Ticketvorverkauf: {opponent} ({competition})")

    # Event description
    description = (
        f"Vorverkauf für Vereinsmitglieder\n"
        f"Spiel: FC St. Pauli vs. {opponent}\n"
        f"Wettbewerb: {competition}\n"
        f"Vorverkaufsstart: {presale_dt.strftime('%d.%m.%Y um %H:%M Uhr')}\n\n"
        f"Weitere Informationen:\n{link}"
    )
    event.add("description", description)

    # Event time (presale start time)
    event.add("dtstart", presale_dt)
    event.add("dtend", presale_dt + timedelta(hours=1))  # 1 hour duration

    # URL
    event.add("url", link)

    # UID (unique identifier)
    uid = f"{presale_dt.strftime('%Y%m%d%H%M')}-{opponent.replace(' ', '-')}@fcstpauli.com"
    event.add("uid", uid)

    # Timestamp
    event.add("dtstamp", datetime.now(timezone))

    # Alarms/Reminders
    # Alarm 1: 9 AM same day
    alarm_morning = Alarm()
    alarm_morning.add("action", "DISPLAY")
    alarm_morning.add("description", f"Heute: Ticketvorverkauf {opponent}")
    morning_9am = presale_dt.replace(hour=9, minute=0, second=0)
    if morning_9am < presale_dt:
        trigger_delta = morning_9am - presale_dt
        alarm_morning.add("trigger", trigger_delta)
        event.add_component(alarm_morning)

    # Alarm 2: 15 minutes before presale
    alarm_before = Alarm()
    alarm_before.add("action", "DISPLAY")
    alarm_before.add("description", f"In 15 Minuten: Ticketvorverkauf {opponent}")
    alarm_before.add("trigger", timedelta(minutes=-15))
    event.add_component(alarm_before)

    return event


def generate_icalendar(presale_events: list[dict], timezone: pytz.timezone) -> bytes:
    """
    Generate iCalendar file from presale events.

    Args:
        presale_events: List of presale info dictionaries
        timezone: Timezone for calendar

    Returns:
        iCalendar file content as bytes
    """
    cal = Calendar()
    cal.add("prodid", "-//FC St. Pauli Presale Calendar//fcsp-presale-extractor//DE")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")
    cal.add("x-wr-calname", "FC St. Pauli Ticketvorverkauf")
    cal.add(
        "x-wr-caldesc",
        "Vorverkaufstermine für Vereinsmitglieder (Heimspiele Bundesliga & DFB-Pokal)",
    )
    cal.add("x-wr-timezone", str(timezone))

    for presale_info in presale_events:
        event = create_calendar_event(presale_info, timezone)
        cal.add_component(event)

    logger.info(f"Generated calendar with {len(presale_events)} events")
    return cal.to_ical()


def process_presales(rss_feed_url: str, timezone: pytz.timezone) -> bytes:
    """
    Main processing function - fetches RSS feed and generates iCalendar data.

    Args:
        rss_feed_url: URL of the FC St. Pauli RSS feed
        timezone: Timezone for presale dates

    Returns:
        iCalendar file content as bytes
    """
    # Fetch RSS feed
    feed = fetch_rss_feed(rss_feed_url)

    # Extract presale information from all entries
    presale_events = []
    for entry in feed.entries:
        presale_info = extract_presale_info(entry, timezone)
        if presale_info:
            logger.info(
                f"Found presale: {presale_info['opponent']} on {presale_info['presale_datetime']}"
            )
            presale_events.append(presale_info)

    if not presale_events:
        logger.warning("No presale events found in RSS feed")

    # Generate iCalendar
    ical_content = generate_icalendar(presale_events, timezone)

    logger.info(f"Total events: {len(presale_events)}")
    return ical_content


if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="FC St. Pauli Presale Calendar Extractor - outputs iCalendar to stdout",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate calendar and save to file
  python fcsp_presale_extractor.py > presale.ics

  # Use custom RSS feed URL
  python fcsp_presale_extractor.py --feed-url https://example.com/rss.xml > calendar.ics

  # Enable debug logging
  python fcsp_presale_extractor.py --log-level DEBUG > presale.ics 2> debug.log
        """,
    )
    parser.add_argument(
        "--feed-url",
        default="https://www.fcstpauli.com/rss.xml",
        help="URL of the FC St. Pauli RSS feed (default: %(default)s)",
    )
    parser.add_argument(
        "--timezone",
        default="Europe/Berlin",
        help="Timezone for presale dates (default: %(default)s)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level (default: %(default)s)",
    )
    args = parser.parse_args()

    # Configure logging to stderr (so it doesn't interfere with stdout)
    logging.basicConfig(
        stream=sys.stderr,
        level=getattr(logging, args.log_level),
        format="%(levelname)s:%(name)s:%(message)s",
    )

    # Parse timezone
    try:
        tz = pytz.timezone(args.timezone)
    except pytz.UnknownTimeZoneError:
        logger.error(f"Unknown timezone: {args.timezone}")
        sys.exit(1)

    # Process presales and write to stdout
    try:
        ical_bytes = process_presales(args.feed_url, tz)
        sys.stdout.buffer.write(ical_bytes)
    except Exception as e:
        logger.error(f"Failed to generate calendar: {e}")
        sys.exit(1)
