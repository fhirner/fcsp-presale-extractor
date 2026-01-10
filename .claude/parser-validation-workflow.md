# Parser Validation Workflow

This document describes the process for validating the FC St. Pauli presale parser to ensure it's correctly extracting ticket presale information from the RSS feed.

## Quick Start

To run a full parser validation check, simply say:

> **"Hey Claude, let's confirm the parser is still working!"**

Claude will then follow this workflow automatically.

## Validation Workflow

### 1. Run Tests
```bash
uv run pytest test_extractor.py -v
```

**Expected Result**: All 5 tests should pass
- `test_extract_all_presale_events` - Validates all presale events extracted correctly
- `test_filters_away_games` - Ensures away games are filtered out
- `test_dfb_pokal_treated_as_home` - DFB-Pokal home games are included
- `test_opponent_extraction` - German articles properly removed
- `test_presale_time_always_15_uhr` - Time parsing works correctly

### 2. Run Parser Check
```bash
uv run python check_parser.py
```

This script fetches the latest RSS feed and displays:
- **Successfully parsed presales**: Home games with valid presale dates
- **Unparsed Ticket-Infos**: Entries that weren't parsed (with links for verification)

### 3. Review Parsed Presales

For each successfully parsed presale, verify:
- ✓ **Opponent name** is correct and properly extracted
- ✓ **Presale date/time** matches the RSS entry
- ✓ **Competition** (Bundesliga or DFB-Pokal) is correct
- ✓ **Link** points to the correct RSS article

### 4. Review Unparsed Entries

Check unparsed Ticket-Infos entries (excluding obvious away games):
- Away games with "Auswärtsspiel" or "beim" → Correct to skip ✓
- Test games with "Testspiel" → Correct to skip ✓
- DFB-Pokal away games → Correct to skip ✓
- Home games (with "Heimspiel gegen") → Should be parsed! 🔍

**If a home game is unparsed**, investigate why:
1. Check if presale date pattern is in description
2. Verify the date format matches the regex pattern
3. Look for edge cases (e.g., "ab" prefix, Derby games)

## Parser Logic Reference

### What Gets Parsed (Home Games)
- Title contains "Ticket-Infos"
- Title does NOT contain "Auswärtsspiel" or "beim"
- Description contains presale date pattern before "können Vereinsmitglieder"

### Presale Date Pattern
The parser looks for this pattern in the description:
```regex
(DD.MM., [ab] HH[:MM] Uhr) ... können Vereinsmitglieder
```

Examples:
- `(23.10., 15 Uhr)` → October 23, 3:00 PM
- `(7.10., 15:30 Uhr)` → October 7, 3:30 PM
- `(15.1., ab 15 Uhr)` → January 15, from 3:00 PM

### Opponent Extraction
- **Derby games**: Title contains "Derby" → Returns "Hamburger SV"
- **Regular games**: Extracts from "gegen OPPONENT" pattern
- **Articles removed**: "den", "die", "das", "der", "dem"
- **Year suffix removed**: "2526" at end of title

### Competition Detection
- Title contains "pokal" (case-insensitive) → "DFB-Pokal"
- Otherwise → "Bundesliga"

## Common Issues & Fixes

### Issue: Derby game shows "Gegner unbekannt"
**Fix**: Already handled! Derby games detected by "derby" in title → "Hamburger SV"

### Issue: Home game not parsed (e.g., "Heimspiel gegen Werder Bremen")
**Possible causes**:
1. Presale date uses "ab" prefix → Already supported in regex
2. No presale date in description → Entry correctly skipped
3. Different date format → May need regex update

### Issue: Wrong opponent name
**Check**:
1. Does title use "gegen OPPONENT" format?
2. Are German articles being removed correctly?
3. Is it a special case like Derby?

### Issue: Wrong competition type
**Check**: Does title contain "pokal"? If yes → DFB-Pokal, else → Bundesliga

## Making Changes

If parser fixes are needed:

1. **Edit the parser**: [fcsp_presale_extractor.py](../fcsp_presale_extractor.py)
   - `is_home_game_ticket()` - Home/away detection
   - `extract_opponent()` - Opponent name extraction
   - `extract_competition()` - Competition type
   - `extract_presale_datetime()` - Date/time parsing
   - `PRESALE_PATTERN` - Regex for presale date

2. **Update tests if needed**: [test_extractor.py](../test_extractor.py)
   - Update `EXPECTED_EVENTS` if behavior changes
   - Add new test cases for edge cases

3. **Run validation workflow** (steps 1-4 above)

4. **Commit changes**:
   ```bash
   git add fcsp_presale_extractor.py test_extractor.py
   git commit -m "fix: description of fix"
   ```

## Current Parser Performance

**Last validated**: 2026-01-09

**Successfully parsing**: 6/6 expected home games ✓
- 1. FC Union Berlin (Bundesliga) - 23.10.2025 15:00 Uhr
- 1. FC Heidenheim (Bundesliga) - 13.11.2025 15:00 Uhr
- Leipzig (Bundesliga) - 27.11.2025 15:00 Uhr
- Hamburger SV (Bundesliga) - Derby - 11.12.2025 15:00 Uhr
- VfB Stuttgart (Bundesliga) - 08.01.2026 15:00 Uhr
- Werder Bremen (Bundesliga) - 15.01.2026 15:00 Uhr

**Correctly filtering**: Away games, test games, DFB-Pokal away games

**All tests passing**: 5/5 ✓

---

## Usage Examples

### Example 1: Full validation
```
User: Hey Claude, let's confirm the parser is still working!

Claude: [Runs tests] → All passing ✓
Claude: [Runs parser check] → Shows results
Claude: [Asks about each parsed game using popups]
Claude: [Implements any fixes based on feedback]
Claude: [Commits changes]
```

### Example 2: Quick check
```
User: Run the parser check

Claude: [Runs check_parser.py and shows results]
```

### Example 3: Fix specific issue
```
User: The Derby game is showing "Gegner unbekannt" but it should be "Hamburger SV"

Claude: [Investigates extract_opponent() function]
Claude: [Adds Derby special case]
Claude: [Runs tests and parser check]
Claude: [Commits fix]
```

## Files Reference

- **Main parser**: [fcsp_presale_extractor.py](../fcsp_presale_extractor.py)
- **Tests**: [test_extractor.py](../test_extractor.py)
- **Parser check script**: [check_parser.py](../check_parser.py)
- **Test data**: [test_data/rss_test.xml](../test_data/rss_test.xml)
- **Configuration**: [pyproject.toml](../pyproject.toml)

## Context for Claude

When the user asks to validate the parser, follow this sequence:

1. **Run tests**: `uv run pytest test_extractor.py -v`
2. **Run parser check**: `uv run python check_parser.py`
3. **Ask user for feedback** using AskUserQuestion tool:
   - Review each successfully parsed presale game
   - Review unparsed entries (excluding obvious away games)
   - Use popups to make it easy for user to respond
4. **Implement fixes** based on feedback
5. **Re-run tests and parser check** to verify
6. **Commit changes** with descriptive messages

Remember:
- Use markdown links for file references: `[filename.py](filename.py)` or `[filename.py:42](filename.py#L42)`
- Show links in all output for easy verification
- Ask game-by-game using AskUserQuestion popups
- Always run tests after making changes
- Create focused git commits (one logical fix per commit)
