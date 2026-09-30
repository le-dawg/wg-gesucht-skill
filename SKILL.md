---
name: rental-listing-syndicator
description: Use when syndicating or publishing rental listings from external sources (such as Airbnb or unstructured text) to German rental portals like WG-Gesucht, ensuring photo optimization, EXIF stripping, factual schema validation, and zero-emoji compliance.
---

# Rental Listing Syndicator

Durable, 4-sigma grade automated skill for parsing, sanitizing, optimizing, and syndicating rental listings from source platforms (Airbnb, direct user input) to German rental portals (specifically `wg-gesucht.de`).

## Key Principles & Quality Gates

1. **Portable Hermetic Execution (`uv` & `uvx`):**
   - Execution uses `uvx` for ephemeral, dependency-isolated command runner operations (`uvx --with <pkg> python ...`), with inline PEP 723 dependency headers (`uv run`) supported across all scripts.
   - Zero reliance on ambient global Python packages or manual virtualenvs.
2. **Zero Defect Data Hygiene:**
   - Strict zero-emoji policy enforced across all German and English listing fields.
   - Pydantic schema validation (`extra='forbid'`) prevents hallucinated amenities and enforces numeric boundaries.
   - Deterministic SHA-256 idempotency key prevents duplicate ad creation.
3. **Media Privacy & Optimization:**
   - Strips all EXIF, GPS, and camera metadata prior to upload.
   - Downsamples and normalizes images to max 1920x1080 and <2 MB JPEG.
4. **Resilience & Security:**
   - Automatic credential and token masking in logs and traces.
   - Circuit breaker on bot detection/CAPTCHA challenges.

## Browser Automation Fallback Ladder

When browser interaction or visual verification is required on the user's active session, strictly follow this tiered escalation ladder:

1. **Tier 1 (Preferred): ModCDP (`modcdp-browser`)**
   - Direct reverse WebSocket proxy to live user tabs (ports `29292` / `29293`).
   - Zero consent modals, preserves active login sessions/cookies, and accurately inspects focused tabs (`get_active_tab`, `eval_in_tab`, `capture_active_tab_screenshot`).
2. **Tier 2 (Fallback): Chrome DevTools MCP (`chrome-devtools`)**
   - Headless or dedicated CDP session when ModCDP is offline or when interacting in an isolated sandbox profile (`navigate_page`, `take_snapshot`, `click`, `fill`).
3. **Tier 3 (Terminal Fallback): AppleScript / `osascript`**
   - Native macOS GUI scripting for triggering keystrokes, clipboard paste, or activating the Chrome window if MCP layers are unavailable:
     ```bash
     osascript -e 'tell application "Google Chrome" to get URL of active tab of front window'
     ```

## Directory Structure

- `scripts/`
  - [`schema_validator.py`](file:///Users/thedawgctor/.gemini/config/skills/rental-listing-syndicator/scripts/schema_validator.py): Pydantic models, numeric boundaries, and zero-emoji enforcement.
  - [`extract_and_optimize_assets.py`](file:///Users/thedawgctor/.gemini/config/skills/rental-listing-syndicator/scripts/extract_and_optimize_assets.py): Image optimization and metadata stripping.
  - [`wg_gesucht_syndicator.py`](file:///Users/thedawgctor/.gemini/config/skills/rental-listing-syndicator/scripts/wg_gesucht_syndicator.py): REST/AJAX syndicator client for WG-Gesucht.
  - [`test_syndicator.py`](file:///Users/thedawgctor/.gemini/config/skills/rental-listing-syndicator/scripts/test_syndicator.py): 7-gate automated test suite.
- `references/`
  - [`wg_gesucht_api_reference.md`](file:///Users/thedawgctor/.gemini/config/skills/rental-listing-syndicator/references/wg_gesucht_api_reference.md): Endpoint specifications and schema mapping.

## Step-by-Step Workflow

### Step 1: Validate Listing Payload
Validate incoming listing details against strict boundaries and zero-emoji constraints using `uvx` (or `uv run`):

```bash
uvx --with pydantic python ~/.gemini/config/skills/rental-listing-syndicator/scripts/schema_validator.py listing_payload.json
```

### Step 2: Download & Optimize Listing Photos
Sanitize photos, strip EXIF metadata, and downsample to web-ready JPEG format:

```bash
uvx --with pillow --with urllib3 python ~/.gemini/config/skills/rental-listing-syndicator/scripts/extract_and_optimize_assets.py \
  --input-dir /path/to/raw_photos \
  --output-dir /path/to/clean_photos
```

### Step 3: Run Portal Syndication
Execute authenticated draft creation and asset upload:

```bash
uvx --with pydantic --with pillow python ~/.gemini/config/skills/rental-listing-syndicator/scripts/wg_gesucht_syndicator.py \
  --config listing_payload.json \
  --photos-dir /path/to/clean_photos
```

### Step 4: Verification & Test Execution
Run the full 7-gate 4-sigma compliance suite:

```bash
uv run ~/.gemini/config/skills/rental-listing-syndicator/scripts/test_syndicator.py
```
