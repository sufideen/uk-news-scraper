"""
scraper_server.py
-----------------
Lightweight HTTP server that wraps the UK news scraper.
Runs as a Docker sidecar alongside N8N.

N8N calls: GET http://scraper:8765/run
Response:  JSON envelope with subject + htmlBody (same as run_for_n8n.py)

Endpoints:
  GET /run     - runs all scrapers, returns JSON digest
  GET /health  - returns {"status": "ok"} for Docker healthcheck
"""

import json
import logging
import sys
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime, UTC
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

LONDON_TZ = ZoneInfo("Europe/London")
PORT = 8765


def run_scraper() -> dict:
    """Run all scrapers and return the JSON envelope."""
    london_now = datetime.now(LONDON_TZ)
    hour = london_now.hour
    session = "Morning Briefing" if hour < 12 else "Evening Roundup"
    date_str = london_now.strftime("%a %d %b %Y")
    subject = f"UK News {session} \u2013 {date_str}"

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
            log.info("%s: %d articles", name, len(results))
        except Exception as exc:
            log.warning("%s failed: %s", name, exc)

    if not all_articles:
        raise RuntimeError("No articles collected from any source")

    html = scraper.get_html_email_body(all_articles, session_label=session)

    # Save timestamped HTML file to disk
    digest_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "digests")
    os.makedirs(digest_dir, exist_ok=True)
    tag = "morning" if "Morning" in session else "evening"
    filename = london_now.strftime(f"%Y-%m-%d_%H-%M_{tag}.html")
    filepath = os.path.join(digest_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)
    log.info("Saved digest: %s", filepath)

    return {
        "subject":   subject,
        "htmlBody":  html,
        "session":   session,
        "articles":  len(all_articles),
        "savedFile": filepath,
    }


class ScraperHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        log.info("HTTP %s", fmt % args)

    def send_json(self, code: int, payload: dict):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self.send_json(200, {"status": "ok"})

        elif self.path == "/run":
            log.info("Scrape request received")
            try:
                result = run_scraper()
                self.send_json(200, result)
                log.info("Scrape complete: %d articles", result["articles"])
            except Exception as exc:
                log.error("Scrape failed: %s", exc, exc_info=True)
                self.send_json(500, {"error": str(exc)})

        else:
            self.send_json(404, {"error": "Not found. Use GET /run or GET /health"})


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), ScraperHandler)
    log.info("Scraper HTTP server listening on port %d", PORT)
    server.serve_forever()
