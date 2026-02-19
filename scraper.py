"""
UK News Scraper
Scrapes BBC News, The Guardian, The Independent, and Sky News.
Saves results to:
  output/news_articles.csv
  output/news_articles.html
  output/news_articles.json
  output/news_articles.odt  (LibreOffice Writer document)
"""

import csv
import json
import os
import time
import logging
import random
from dataclasses import dataclass, fields
from datetime import datetime, timezone, UTC
from typing import Optional

import requests
import feedparser
from bs4 import BeautifulSoup
from dateutil import parser as dateparser

# ── Configuration ─────────────────────────────────────────────────────────────

USER_AGENT = (
    "Mozilla/5.0 (compatible; UKNewsScraper/1.0; "
    "for personal/research use)"
)
REQUEST_TIMEOUT = 15
MIN_DELAY = 2.0
MAX_DELAY = 5.0
OUTPUT_DIR  = "output"
OUTPUT_CSV  = "output/news_articles.csv"
OUTPUT_HTML = "output/news_articles.html"
OUTPUT_JSON = "output/news_articles.json"
OUTPUT_ODT  = "output/news_articles.odt"

HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept-Language": "en-GB,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Data Model ────────────────────────────────────────────────────────────────

@dataclass
class Article:
    source: str
    title: str
    url: str
    summary: str
    author: str
    published_date: str

CSV_FIELDNAMES = [f.name for f in fields(Article)]

# ── Shared Utilities ──────────────────────────────────────────────────────────

def polite_get(url: str) -> Optional[requests.Response]:
    """HTTP GET with User-Agent, timeout, and error handling."""
    if not url:
        return None
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp
    except requests.exceptions.Timeout:
        log.warning("Timeout fetching: %s", url)
    except requests.exceptions.HTTPError as e:
        log.warning("HTTP %s for: %s", e.response.status_code, url)
    except requests.exceptions.RequestException as e:
        log.warning("Network error for %s: %s", url, e)
    return None


def parse_date(raw: str) -> str:
    """Normalise any date string to ISO 8601 (YYYY-MM-DDTHH:MM:SSZ)."""
    if not raw:
        return ""
    try:
        dt = dateparser.parse(raw)
        if dt and dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ") if dt else raw
    except Exception:
        return raw


def delay():
    """Random polite delay between requests."""
    time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))


def parse_feed(url: str) -> list:
    """Parse an RSS/Atom feed using feedparser."""
    log.info("Fetching RSS feed: %s", url)
    feed = feedparser.parse(url, agent=USER_AGENT)
    if feed.get("bozo") and not feed.entries:
        log.warning("Feed parse error for %s: %s", url, feed.get("bozo_exception"))
    return feed.entries


def strip_html(raw: str) -> str:
    """Remove HTML tags from a string."""
    if not raw:
        return ""
    return BeautifulSoup(raw, "lxml").get_text(strip=True)


# ── BBC News ──────────────────────────────────────────────────────────────────

BBC_RSS_URL = "https://feeds.bbci.co.uk/news/uk/rss.xml"


def _bbc_get_author(article_url: str) -> str:
    """Scrape author from a BBC article page."""
    resp = polite_get(article_url)
    if not resp:
        return ""
    soup = BeautifulSoup(resp.text, "lxml")

    node = soup.select_one('[data-testid="byline-new-contributors"] span')
    if node:
        return node.get_text(strip=True)

    node = soup.select_one('[data-component="byline-block"] a')
    if node:
        return node.get_text(strip=True)

    meta = soup.find("meta", {"name": "author"})
    if meta:
        return meta.get("content", "").strip()

    return ""


def scrape_bbc() -> list:
    """
    BBC News: RSS feed for title/url/summary/date.
    Per-article HTML fetch for author.
    """
    articles = []
    entries = parse_feed(BBC_RSS_URL)
    log.info("BBC: found %d RSS entries", len(entries))

    for entry in entries:
        title = entry.get("title", "").strip()
        url = entry.get("link", "").strip()
        summary = strip_html(entry.get("summary", ""))
        pub = parse_date(entry.get("published", ""))

        author = _bbc_get_author(url)
        delay()

        articles.append(Article(
            source="BBC News",
            title=title,
            url=url,
            summary=summary,
            author=author,
            published_date=pub,
        ))

    return articles


# ── The Guardian ──────────────────────────────────────────────────────────────

GUARDIAN_API_URL = "https://content.guardianapis.com/search"


def scrape_guardian(api_key: str = "test") -> list:
    """
    The Guardian: uses the free Content API.
    api_key='test' works for low-volume personal/research use.
    Register a free key at https://open-platform.theguardian.com/access/
    """
    articles = []
    params = {
        "section": "uk-news",
        "order-by": "newest",
        "page-size": "50",
        "show-fields": "byline,trailText",
        "api-key": api_key,
    }
    log.info("Fetching Guardian Content API (section=uk-news)")

    try:
        resp = requests.get(
            GUARDIAN_API_URL,
            params=params,
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        log.error("Guardian API request failed: %s", e)
        return articles

    results = data.get("response", {}).get("results", [])
    log.info("Guardian: found %d articles", len(results))

    for item in results:
        f = item.get("fields", {})
        articles.append(Article(
            source="The Guardian",
            title=item.get("webTitle", "").strip(),
            url=item.get("webUrl", "").strip(),
            summary=strip_html(f.get("trailText", "")),
            author=f.get("byline", "").strip(),
            published_date=parse_date(item.get("webPublicationDate", "")),
        ))
        delay()

    return articles


# ── The Independent ───────────────────────────────────────────────────────────

INDEPENDENT_RSS_URL = "https://www.independent.co.uk/news/uk/rss"


def _independent_get_author(article_url: str) -> str:
    """Fallback: scrape author from an Independent article page."""
    resp = polite_get(article_url)
    if not resp:
        return ""
    soup = BeautifulSoup(resp.text, "lxml")

    meta = soup.find("meta", {"name": "author"})
    if meta:
        return meta.get("content", "").strip()

    for selector in [
        'a[data-testid="author-name"]',
        ".author__name",
        '[itemprop="author"] [itemprop="name"]',
    ]:
        node = soup.select_one(selector)
        if node:
            return node.get_text(strip=True)

    return ""


def scrape_independent() -> list:
    """
    The Independent: RSS feed for title/url/summary/date/author (dc:creator).
    Falls back to HTML scrape for author when not in feed.
    """
    articles = []
    entries = parse_feed(INDEPENDENT_RSS_URL)
    log.info("Independent: found %d RSS entries", len(entries))

    for entry in entries:
        title = entry.get("title", "").strip()
        url = entry.get("link", "").strip()
        summary = strip_html(entry.get("summary", ""))
        pub = parse_date(entry.get("published", ""))
        author = entry.get("author", "").strip()

        if not author:
            author = _independent_get_author(url)

        delay()

        articles.append(Article(
            source="The Independent",
            title=title,
            url=url,
            summary=summary,
            author=author,
            published_date=pub,
        ))

    return articles


# ── Sky News ──────────────────────────────────────────────────────────────────

SKY_RSS_URL = "https://feeds.skynews.com/feeds/rss/uk.xml"


def _sky_get_author(article_url: str) -> str:
    """Fallback: scrape author from a Sky News article page."""
    resp = polite_get(article_url)
    if not resp:
        return ""
    soup = BeautifulSoup(resp.text, "lxml")

    meta = soup.find("meta", {"name": "author"})
    if meta:
        return meta.get("content", "").strip()

    for selector in [
        ".author-name",
        '[data-testid="author-name"]',
        "article header p a",
    ]:
        node = soup.select_one(selector)
        if node:
            return node.get_text(strip=True)

    return ""


def scrape_sky_news() -> list:
    """
    Sky News: RSS feed for title/url/summary/date/author (dc:creator).
    Falls back to HTML scrape for author when not in feed.
    """
    articles = []
    entries = parse_feed(SKY_RSS_URL)
    log.info("Sky News: found %d RSS entries", len(entries))

    for entry in entries:
        title = entry.get("title", "").strip()
        url = entry.get("link", "").strip()
        summary = strip_html(entry.get("summary", ""))
        pub = parse_date(entry.get("published", ""))
        author = entry.get("author", "").strip()

        if not author:
            author = _sky_get_author(url)

        delay()

        articles.append(Article(
            source="Sky News",
            title=title,
            url=url,
            summary=summary,
            author=author,
            published_date=pub,
        ))

    return articles


# ── CSV Writer ────────────────────────────────────────────────────────────────

def save_to_csv(articles: list, filepath: str) -> None:
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()
        for article in articles:
            writer.writerow({
                "source": article.source,
                "title": article.title,
                "url": article.url,
                "summary": article.summary,
                "author": article.author,
                "published_date": article.published_date,
            })
    log.info("Saved %d articles to %s", len(articles), filepath)


# ── HTML Writer ───────────────────────────────────────────────────────────────

def save_to_html(articles: list, filepath: str) -> None:
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    generated_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    rows = ""
    for a in articles:
        rows += (
            f"  <tr>\n"
            f"    <td>{a.source}</td>\n"
            f"    <td><a href=\"{a.url}\" target=\"_blank\">{a.title}</a></td>\n"
            f"    <td>{a.summary}</td>\n"
            f"    <td>{a.author}</td>\n"
            f"    <td>{a.published_date}</td>\n"
            f"  </tr>\n"
        )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>UK News Articles</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 2rem; color: #222; }}
    h1   {{ font-size: 1.6rem; margin-bottom: 0.25rem; }}
    p.meta {{ color: #666; font-size: 0.85rem; margin-bottom: 1.5rem; }}
    table {{ border-collapse: collapse; width: 100%; font-size: 0.9rem; }}
    th    {{ background: #1a73e8; color: #fff; padding: 0.6rem 0.8rem; text-align: left; }}
    td    {{ padding: 0.5rem 0.8rem; border-bottom: 1px solid #ddd; vertical-align: top; }}
    tr:hover td {{ background: #f0f7ff; }}
    td:nth-child(3) {{ max-width: 380px; }}
    a {{ color: #1a73e8; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
  </style>
</head>
<body>
  <h1>UK News Articles</h1>
  <p class="meta">Generated: {generated_at} &mdash; {len(articles)} articles</p>
  <table>
    <thead>
      <tr>
        <th>Source</th>
        <th>Title</th>
        <th>Summary</th>
        <th>Author</th>
        <th>Published</th>
      </tr>
    </thead>
    <tbody>
{rows}    </tbody>
  </table>
</body>
</html>
"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)
    log.info("Saved %d articles to %s", len(articles), filepath)


# ── JSON Writer ───────────────────────────────────────────────────────────────

def save_to_json(articles: list, filepath: str) -> None:
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    payload = {
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total": len(articles),
        "articles": [
            {
                "source": a.source,
                "title": a.title,
                "url": a.url,
                "summary": a.summary,
                "author": a.author,
                "published_date": a.published_date,
            }
            for a in articles
        ],
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    log.info("Saved %d articles to %s", len(articles), filepath)


# ── ODT Writer (LibreOffice) ──────────────────────────────────────────────────

def save_to_odt(articles: list, filepath: str) -> None:
    from odf.opendocument import OpenDocumentText
    from odf.style import Style, TextProperties, ParagraphProperties, TableColumnProperties
    from odf.text import H, P, A
    from odf.table import Table, TableColumn, TableRow, TableCell

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    doc = OpenDocumentText()

    # ── Styles ────────────────────────────────────────────────────────────────
    # Heading style
    h1_style = Style(name="Heading1", family="paragraph")
    h1_style.addElement(ParagraphProperties(breakbefore="auto"))
    h1_style.addElement(TextProperties(fontsize="18pt", fontweight="bold", color="#1a73e8"))
    doc.styles.addElement(h1_style)

    # Sub-heading / meta style
    meta_style = Style(name="Meta", family="paragraph")
    meta_style.addElement(TextProperties(fontsize="9pt", color="#666666", fontstyle="italic"))
    doc.styles.addElement(meta_style)

    # Table header cell style
    th_style = Style(name="TableHeader", family="table-cell")
    th_style.addElement(TextProperties(fontweight="bold", color="#ffffff"))
    doc.styles.addElement(th_style)

    # Table header paragraph style (background colour set on cell via table-cell style)
    th_para_style = Style(name="TableHeaderPara", family="paragraph")
    th_para_style.addElement(ParagraphProperties(backgroundcolor="#1a73e8"))
    th_para_style.addElement(TextProperties(fontweight="bold", color="#ffffff"))
    doc.styles.addElement(th_para_style)

    # Normal cell paragraph style
    cell_style = Style(name="CellPara", family="paragraph")
    cell_style.addElement(TextProperties(fontsize="9pt"))
    doc.styles.addElement(cell_style)

    # Column width styles
    col_widths = ["3.0cm", "7.0cm", "8.5cm", "4.0cm", "3.5cm"]
    col_styles = []
    for i, w in enumerate(col_widths):
        cs = Style(name=f"Col{i}", family="table-column")
        cs.addElement(TableColumnProperties(columnwidth=w))
        doc.automaticstyles.addElement(cs)
        col_styles.append(cs)

    # ── Document title ────────────────────────────────────────────────────────
    title = H(outlinelevel=1, stylename=h1_style)
    title.addText("UK News Articles")
    doc.text.addElement(title)

    generated_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    meta_p = P(stylename=meta_style)
    meta_p.addText(f"Generated: {generated_at}  |  Total articles: {len(articles)}")
    doc.text.addElement(meta_p)

    # ── Table ─────────────────────────────────────────────────────────────────
    table = Table()
    for i, cs in enumerate(col_styles):
        table.addElement(TableColumn(stylename=cs))

    def make_header_cell(text: str) -> TableCell:
        cell = TableCell()
        p = P(stylename=th_para_style)
        p.addText(text)
        cell.addElement(p)
        return cell

    def make_cell(text: str) -> TableCell:
        cell = TableCell()
        p = P(stylename=cell_style)
        p.addText(str(text) if text else "")
        cell.addElement(p)
        return cell

    def make_link_cell(text: str, url: str) -> TableCell:
        cell = TableCell()
        p = P(stylename=cell_style)
        if url:
            link = A(href=url)
            link.addText(text)
            p.addElement(link)
        else:
            p.addText(text)
        cell.addElement(p)
        return cell

    # Header row
    header_row = TableRow()
    for col_name in ("Source", "Title", "Summary", "Author", "Published"):
        header_row.addElement(make_header_cell(col_name))
    table.addElement(header_row)

    # Data rows
    for a in articles:
        row = TableRow()
        row.addElement(make_cell(a.source))
        row.addElement(make_link_cell(a.title, a.url))
        row.addElement(make_cell(a.summary))
        row.addElement(make_cell(a.author))
        row.addElement(make_cell(a.published_date))
        table.addElement(row)

    doc.text.addElement(table)
    doc.save(filepath)
    log.info("Saved %d articles to %s", len(articles), filepath)


# ── Email HTML Builder (N8N / Gmail) ─────────────────────────────────────────

def get_html_email_body(articles: list, session_label: str = "") -> str:
    """
    Build a Gmail-safe HTML email body from a list of Article objects.

    - Groups articles by source
    - Takes the first 10 per source (already newest-first from RSS/API)
    - Uses only inline CSS (Gmail strips <style> blocks)
    - Max-width 700px, works in all major email clients
    - session_label: e.g. "Morning Briefing" or "Evening Roundup"
    """
    from collections import defaultdict

    generated_at = datetime.now(UTC).strftime("%d %B %Y, %H:%M UTC")

    # Group and cap at 10 per source
    by_source: dict = defaultdict(list)
    for a in articles:
        by_source[a.source].append(a)

    source_order = ["BBC News", "The Guardian", "The Independent", "Sky News"]
    # Ensure consistent order, include any unexpected sources at the end
    ordered_sources = [s for s in source_order if s in by_source]
    ordered_sources += [s for s in by_source if s not in source_order]

    # ── Colour map per source ────────────────────────────────────────────────
    source_colours = {
        "BBC News":        "#bb1919",
        "The Guardian":    "#052962",
        "The Independent": "#e8173d",
        "Sky News":        "#003e7e",
    }

    # ── Build sections ───────────────────────────────────────────────────────
    sections_html = ""
    for source in ordered_sources:
        colour = source_colours.get(source, "#333333")
        top10 = by_source[source][:10]

        rows_html = ""
        for i, a in enumerate(top10):
            bg = "#ffffff" if i % 2 == 0 else "#f7f9fc"
            rows_html += f"""
      <tr>
        <td style="padding:10px 12px;border-bottom:1px solid #e0e0e0;background:{bg};vertical-align:top;width:42%;">
          <a href="{a.url}" style="color:{colour};text-decoration:none;font-weight:600;font-size:13px;line-height:1.4;" target="_blank">{a.title}</a>
        </td>
        <td style="padding:10px 12px;border-bottom:1px solid #e0e0e0;background:{bg};vertical-align:top;font-size:12px;color:#555;line-height:1.5;">
          {a.summary}
        </td>
        <td style="padding:10px 12px;border-bottom:1px solid #e0e0e0;background:{bg};vertical-align:top;font-size:11px;color:#888;white-space:nowrap;">
          {a.author or "—"}<br>{a.published_date[:10] if a.published_date else ""}
        </td>
      </tr>"""

        sections_html += f"""
  <tr>
    <td colspan="3" style="padding:18px 12px 6px;background:#ffffff;">
      <div style="border-left:4px solid {colour};padding-left:10px;">
        <span style="font-size:15px;font-weight:700;color:{colour};">{source}</span>
        <span style="font-size:11px;color:#999;margin-left:8px;">{len(top10)} articles</span>
      </div>
    </td>
  </tr>
{rows_html}
  <tr><td colspan="3" style="padding:8px;background:#ffffff;"></td></tr>"""

    label_text = f" — {session_label}" if session_label else ""

    return f"""<div style="font-family:Arial,Helvetica,sans-serif;max-width:700px;margin:0 auto;background:#f0f2f5;padding:20px;">

  <!-- Header -->
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0d1b2a;border-radius:8px 8px 0 0;">
    <tr>
      <td style="padding:20px 24px;">
        <div style="font-size:22px;font-weight:700;color:#ffffff;letter-spacing:-0.3px;">
          UK News Digest{label_text}
        </div>
        <div style="font-size:12px;color:#aab4c0;margin-top:4px;">{generated_at}</div>
      </td>
      <td style="padding:20px 24px;text-align:right;vertical-align:middle;">
        <span style="font-size:28px;">🇬🇧</span>
      </td>
    </tr>
  </table>

  <!-- Articles table -->
  <table width="100%" cellpadding="0" cellspacing="0"
         style="background:#ffffff;border-radius:0 0 8px 8px;border:1px solid #e0e0e0;border-top:none;">

    <!-- Column headers -->
    <tr style="background:#f5f5f5;">
      <th style="padding:9px 12px;text-align:left;font-size:11px;font-weight:600;color:#666;text-transform:uppercase;letter-spacing:0.5px;border-bottom:2px solid #e0e0e0;width:42%;">Title</th>
      <th style="padding:9px 12px;text-align:left;font-size:11px;font-weight:600;color:#666;text-transform:uppercase;letter-spacing:0.5px;border-bottom:2px solid #e0e0e0;">Summary</th>
      <th style="padding:9px 12px;text-align:left;font-size:11px;font-weight:600;color:#666;text-transform:uppercase;letter-spacing:0.5px;border-bottom:2px solid #e0e0e0;width:14%;">Author / Date</th>
    </tr>

    {sections_html}

  </table>

  <!-- Footer -->
  <table width="100%" cellpadding="0" cellspacing="0" style="margin-top:12px;">
    <tr>
      <td style="text-align:center;font-size:11px;color:#aaa;padding:8px;">
        Delivered by UK News Scraper &mdash; BBC News &bull; The Guardian &bull; The Independent &bull; Sky News
      </td>
    </tr>
  </table>

</div>"""


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    all_articles = []

    scrapers = [
        ("BBC News", scrape_bbc),
        ("The Guardian", scrape_guardian),
        ("The Independent", scrape_independent),
        ("Sky News", scrape_sky_news),
    ]

    for name, fn in scrapers:
        log.info("── Starting scraper: %s ──", name)
        try:
            results = fn()
            log.info("%s: collected %d articles", name, len(results))
            all_articles.extend(results)
        except Exception as e:
            log.error("%s scraper crashed: %s", name, e, exc_info=True)
        delay()

    log.info("Total articles collected: %d", len(all_articles))

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    save_to_csv(all_articles,  OUTPUT_CSV)
    save_to_html(all_articles, OUTPUT_HTML)
    save_to_json(all_articles, OUTPUT_JSON)
    save_to_odt(all_articles,  OUTPUT_ODT)

    log.info("Done. Output files:")
    for path in (OUTPUT_CSV, OUTPUT_HTML, OUTPUT_JSON, OUTPUT_ODT):
        log.info("  %s", path)


if __name__ == "__main__":
    main()
