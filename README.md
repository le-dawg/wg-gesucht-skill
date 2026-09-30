# Rental Listing Syndicator 🏠

[![AgentSkills.io Standard](https://img.shields.io/badge/AgentSkills.io-Standard-00D084?style=flat-square)](https://agentskills.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](LICENSE)
[![CI](https://github.com/le-dawg/wg-gesucht-skill/actions/workflows/ci.yml/badge.svg)](https://github.com/le-dawg/wg-gesucht-skill/actions/workflows/ci.yml)

> Durable, 4-sigma grade automated agent skill for extracting, sanitizing, optimizing, and syndicating rental listings from source platforms (Airbnb, unstructured text) to German rental portals like [WG-Gesucht](https://www.wg-gesucht.de).

Compatible with **Cursor**, **Claude Code**, **Antigravity CLI (`agy`)**, **OpenCode**, **Codex**, and any agent supporting the [Agent Skills](https://skills.sh) standard.

---

## Quick Install

### Using `npx skills` (Recommended)

Install directly into your AI coding assistant:

```bash
npx skills add le-dawg/wg-gesucht-skill
```

### Manual Install (Git Clone)

Clone into your global or project skills directory:

```bash
# Antigravity CLI
git clone https://github.com/le-dawg/wg-gesucht-skill.git ~/.gemini/config/skills/wg-gesucht-skill

# Claude Code
git clone https://github.com/le-dawg/wg-gesucht-skill.git ~/.claude/skills/wg-gesucht-skill

# Cursor
git clone https://github.com/le-dawg/wg-gesucht-skill.git .cursor/skills/wg-gesucht-skill
```

---

## Key Capabilities

- **Zero-Defect Schema Hygiene:** Pydantic models (`extra='forbid'`) enforce strict boundaries on rent, deposits, dates, and flat geometry.
- **Strict Zero-Emoji Policy:** Unicode regex filters guarantee clean, professional, enterprise-grade rental copy with zero emojis across all fields.
- **Dual-Language Parity:** Generates verified, mirrored German and English descriptions without hallucinating unmentioned amenities.
- **Media Privacy & EXIF Scrubbing:** Strips GPS coordinates, device serials, and camera metadata using pure Pillow. Re-encodes to normalized $\le 1920\times 1080$, $<2$ MB JPEGs.
- **Deterministic Idempotency:** SHA-256 idempotency key prevents duplicate ad creation on re-runs.
- **Anti-Bot Circuit Breakers:** Automatic circuit-breaker tripping on Cloudflare/Turnstile challenges with jittered exponential backoff.
- **Automated Credential Masking:** Masks all passwords, access tokens, and bearer headers in diagnostic logs.

---

## Browser Automation Fallback Ladder

When live browser interaction or visual verification is needed, this skill follows a strict 3-tier escalation ladder:

1. **Tier 1 (Preferred): ModCDP (`modcdp-browser`)**
   - Reverse WebSocket proxy to live user tabs (ports `29292` / `29293`).
   - Zero consent modals, preserves active login sessions, and inspects focused tabs.
2. **Tier 2 (Fallback): Chrome DevTools MCP (`chrome-devtools`)**
   - Headless or dedicated sandbox CDP session when ModCDP is unavailable.
3. **Tier 3 (Terminal Fallback): AppleScript (`osascript`)**
   - Native macOS GUI scripting for active Chrome window inspection.

---

## Tooling & Execution

All scripts include standard PEP 723 headers and are designed for portable, hermetic execution using `uvx` or `uv`:

```bash
# 1. Validate listing payload
uvx --with pydantic python scripts/schema_validator.py listing_payload.json

# 2. Extract, sanitize, and downsample photos
uvx --with pillow --with urllib3 python scripts/extract_and_optimize_assets.py \
  --input-dir /path/to/raw_photos \
  --output-dir /path/to/clean_photos

# 3. Authenticate and syndicate ad draft
uvx --with pydantic --with pillow python scripts/wg_gesucht_syndicator.py \
  --config listing_payload.json \
  --photos-dir /path/to/clean_photos

# 4. Run full 7-gate 4-sigma compliance test suite
uv run scripts/test_syndicator.py
```

---

## Configuration & Environment Variables

For automated draft creation and API syndication on WG-Gesucht:

| Variable | Description |
| :--- | :--- |
| `WG_GESUCHT_EMAIL` | Account login email address |
| `WG_GESUCHT_PASSWORD` | Account login password |

---

## License

MIT © [le-dawg](https://github.com/le-dawg)
