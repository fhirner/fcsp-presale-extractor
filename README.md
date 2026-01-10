# FC St. Pauli Presale Calendar Extractor

Automatic extractor for FC St. Pauli ticket presale dates. Parses the official RSS feed and generates an iCalendar file for subscription.

## Features

- Extracts presale dates for club members from FC St. Pauli RSS feed
- Automatically filters home games (Bundesliga & DFB-Pokal)
- Generates iCalendar file (.ics) with reminders
- Runs daily via GitHub Actions
- Hosted on GitHub Pages

## Quick Start

Subscribe to the calendar in your calendar app:

```
https://{your-username}.github.io/{repo-name}/presale.ics
```

The calendar updates daily at 3:05 PM CET (2:05 PM UTC).

## Setup & Deployment

### Prerequisites

- Python 3.13+
- uv package manager
- GitHub account

### Installation

```bash
git clone <repository-url>
cd fcsp-presale-extractor
uv sync
```

### Testing

```bash
uv run python fcsp_presale_extractor.py > presale.ics  # Generate calendar
uv run pytest test_extractor.py -v                      # Run tests
uv run python check_parser.py                           # Validate parser
```

### Deploy

1. Enable GitHub Pages: Settings → Pages → Source: GitHub Actions
2. Push to GitHub
3. Calendar URL: `https://{username}.github.io/{repo-name}/presale.ics`

## How It Works

### Parser Logic

1. Fetches RSS feed from `https://www.fcstpauli.com/rss.xml`
2. Filters home games (excludes "auswärtsspiel"/"beim")
3. Extracts opponent from title:
   - Regular: "gegen [Opponent]"
   - Derby: "Derby" → "Hamburger SV"
   - Removes German articles
4. Determines competition: "pokal" → DFB-Pokal, else Bundesliga
5. Extracts presale date: `(DD.MM., [ab] HH[:MM] Uhr)` before "können Vereinsmitglieder"

### Automation

- Runs daily at 3:05 PM CET (optimized for Thu/Fri 10 AM-4 PM announcement pattern)
- GitHub Actions + GitHub Pages (completely free)

### CLI Usage

```bash
# Generate calendar (writes to stdout, redirect to save)
python fcsp_presale_extractor.py > presale.ics

# View available options
python fcsp_presale_extractor.py --help

# Use custom RSS feed URL
python fcsp_presale_extractor.py --feed-url https://example.com/rss.xml > calendar.ics

# Enable debug logging (logs go to stderr)
python fcsp_presale_extractor.py --log-level DEBUG > presale.ics 2> debug.log
```

## Development

### Code Quality

```bash
uv run ruff format              # Format code
uv run ruff check --fix        # Lint and auto-fix
uv run ty check                # Type checking
```

### Parser Validation

```bash
uv run python check_parser.py  # Validate on live RSS
```

See [.claude/parser-validation-workflow.md](.claude/parser-validation-workflow.md) for the complete workflow.

## License

MIT
