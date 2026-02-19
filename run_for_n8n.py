"""
run_for_n8n.py
--------------
CLI wrapper called by N8N's Execute Command node.

What it does:
  1. Runs all 4 UK news scrapers (BBC, Guardian, Independent, Sky News)
  2. Keeps the top 10 articles per source
  3. Builds a Gmail-safe HTML email body
  4. Saves a timestamped HTML file to output/digests/ for archiving
  5. Prints a JSON envelope to stdout for N8N to consume

N8N reads stdout as $json — the envelope contains:
  {
    "subject":   "UK News Morning Briefing – Wed 18 Feb 2026",
    "htmlBody":  "<div>...</div>",
    "session":   "Morning Briefing",
    "articles":  151,
    "savedFile": "output/digests/2026-02-18_07-00_morning.html"
  }

Exit codes:
  0 - success
  1 - fatal error (nothing collected)
"""

import sys
import os
import json
import logging
from datetime import datetime, UTC, timezone
from zoneinfo import ZoneInfo

# Ensure scraper module is importable regardless of working directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import scraper

# Suppress scraper INFO logs — only the JSON envelope must reach stdout
logging.getLogger().setLevel(logging.WARNING)

DIGEST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "digests")
LONDON_TZ  = ZoneInfo("Europe/London")


def get_session(london_dt: datetime) -> str:
    return "Morning Briefing" if london_dt.hour < 12 else "Evening Roundup"


def build_subject(session: str, london_dt: datetime) -> str:
    date_str = london_dt.strftime("%a %d %b %Y")
    return f"UK News {session} \u2013 {date_str}"


def save_html_digest(html: str, session: str, london_dt: datetime) -> str:
    """Save HTML to a timestamped file. Returns the saved filepath."""
    os.makedirs(DIGEST_DIR, exist_ok=True)
    tag = "morning" if "Morning" in session else "evening"
    filename = london_dt.strftime(f"%Y-%m-%d_%H-%M_{tag}.html")
    filepath = os.path.join(DIGEST_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)
    return filepath


def main():
    london_now = datetime.now(LONDON_TZ)
    session    = get_session(london_now)
    subject    = build_subject(session, london_now)

    all_articles = []
    scrapers = [
        ("BBC News",        scraper.scrape_bbc),
        ("The Guardian",    scraper.scrape_guardian),
        ("The Independent", scraper.scrape_independent),
        ("Sky News",        scraper.scrape_sky_news),
    ]

    for name, fn in scrapers:
        try:
            results = fn()
            all_articles.extend(results)
        except Exception as exc:
            print(f"[WARN] {name} failed: {exc}", file=sys.stderr)

    if not all_articles:
        print("ERROR: No articles collected from any source.", file=sys.stderr)
        sys.exit(1)

    html      = scraper.get_html_email_body(all_articles, session_label=session)
    saved     = save_html_digest(html, session, london_now)

    # Emit a single JSON line to stdout — N8N parses this automatically
    envelope = {
        "subject":   subject,
        "htmlBody":  html,
        "session":   session,
        "articles":  len(all_articles),
        "savedFile": saved,
    }
    print(json.dumps(envelope, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
