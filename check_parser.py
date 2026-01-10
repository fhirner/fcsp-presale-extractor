#!/usr/bin/env python3
"""
Parser check script - displays parsing results from latest RSS data.

Uses only the main program's logic (no duplicate parsing decisions).
Run anytime to check parser performance on latest data.
"""

import pytz

from fcsp_presale_extractor import extract_presale_info, fetch_rss_feed

# Configuration
RSS_FEED_URL = "https://www.fcstpauli.com/rss.xml"
TIMEZONE = pytz.timezone("Europe/Berlin")


def main():
    print("=" * 80)
    print("FC ST. PAULI PRESALE PARSER CHECK")
    print("=" * 80)
    print()

    # Fetch RSS using main program logic
    print(f"Fetching RSS feed from {RSS_FEED_URL}...")
    feed = fetch_rss_feed(RSS_FEED_URL)
    print()

    # Track results using ONLY main program logic
    parsed_presales = []
    unparsed_ticket_infos = []

    for entry in feed.entries:
        title = entry.get("title", "")

        # Only track Ticket-Infos entries
        if not title.startswith("Ticket-Infos"):
            continue

        # Use ONLY main program logic - extract_presale_info handles ALL filtering
        presale_info = extract_presale_info(entry, TIMEZONE)

        if presale_info:
            parsed_presales.append(presale_info)
        else:
            # Not parsed (could be away game, no presale date, test game, etc.)
            unparsed_ticket_infos.append({"title": title, "link": entry.get("link", "")})

    # Display results
    display_results(parsed_presales, unparsed_ticket_infos, len(feed.entries))


def display_results(parsed_presales, unparsed_ticket_infos, total_entries):
    """Display parsing results in human-readable format."""

    # Summary
    print("SUMMARY")
    print("-" * 80)
    print(f"Total entries in feed: {total_entries}")
    print(f"Ticket-Infos entries: {len(parsed_presales) + len(unparsed_ticket_infos)}")
    print(f"Successfully parsed presales: {len(parsed_presales)}")
    print(f"Unparsed Ticket-Infos: {len(unparsed_ticket_infos)}")
    print()

    # Successfully parsed presales
    if parsed_presales:
        print("SUCCESSFULLY PARSED PRESALES")
        print("=" * 80)
        print()

        # Sort by presale datetime
        parsed_presales.sort(key=lambda x: x["presale_datetime"])

        for i, presale in enumerate(parsed_presales, 1):
            print(f"{i}. {presale['opponent']} ({presale['competition']})")
            print(f"   Presale: {presale['presale_datetime'].strftime('%d.%m.%Y %H:%M Uhr')}")
            print(f"   Title: {presale['title']}")
            print(f"   Link: {presale['link']}")
            print()
    else:
        print("NO PRESALES PARSED")
        print("-" * 80)
        print()

    # Unparsed Ticket-Infos (for manual review)
    if unparsed_ticket_infos:
        print("UNPARSED TICKET-INFOS (FOR MANUAL REVIEW)")
        print("-" * 80)
        for entry in unparsed_ticket_infos:
            print(f"  • {entry['title']}")
            print(f"    Link: {entry['link']}")
            print()

    print("=" * 80)
    print("PARSING COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
