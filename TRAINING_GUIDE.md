# UK News Scraper — Python Beginner Training Guide

**Document type:** Internal Training Document
**Audience:** Python beginners (0–6 months experience)
**Project:** UK News Scraper (`scraper.py`)
**Trainer:** Internal Python Training Team
**Date:** February 2026

---

## Table of Contents

1. [What Does This Script Do?](#1-what-does-this-script-do)
2. [Prerequisites — What You Need to Know First](#2-prerequisites)
3. [Project Structure](#3-project-structure)
4. [Installing Dependencies](#4-installing-dependencies)
5. [Section-by-Section Code Walkthrough](#5-code-walkthrough)
   - 5.1 Imports
   - 5.2 Configuration Constants
   - 5.3 The Article Data Model
   - 5.4 Utility / Helper Functions
   - 5.5 BBC News Scraper
   - 5.6 The Guardian Scraper
   - 5.7 Independent & Sky News Scrapers
   - 5.8 Output Writers (CSV, HTML, JSON, ODT)
   - 5.9 Email HTML Builder
   - 5.10 The `main()` Function
6. [Key Python Concepts Used](#6-key-python-concepts)
7. [How the Internet Works (For Scrapers)](#7-how-the-internet-works)
8. [Exercises](#8-exercises)
9. [Common Errors and Fixes](#9-common-errors-and-fixes)
10. [Glossary](#10-glossary)

---

## 1. What Does This Script Do?

`scraper.py` is a **web scraper** — a program that automatically visits websites,
reads their content, and saves the data for later use.

This specific scraper:

1. Visits four UK news websites: **BBC News, The Guardian, The Independent, Sky News**
2. Collects up to ~30–50 articles from each source
3. Extracts: **title, URL, summary, author, published date** for each article
4. Saves the results in four different file formats: **CSV, HTML, JSON, LibreOffice ODT**
5. Can also build a **Gmail-ready HTML email** digest of the top 10 articles per source

**How long does it take to run?**
Approximately 5–10 minutes. The script deliberately pauses between web requests
to be polite to the news servers (more on this in Section 7).

---

## 2. Prerequisites

Before reading this guide, you should be comfortable with:

| Concept | Example |
|---------|---------|
| Variables | `name = "Alice"` |
| Functions | `def greet(name): return "Hello " + name` |
| Lists | `fruits = ["apple", "banana"]` |
| Dictionaries | `person = {"name": "Alice", "age": 30}` |
| For loops | `for item in my_list: print(item)` |
| If/else | `if x > 0: print("positive")` |
| Importing modules | `import os` |
| Try/except | `try: ... except Exception as e: ...` |

If any of the above are unfamiliar, review them before continuing.

---

## 3. Project Structure

```
uk-news-scraper/
├── scraper.py          ← main script (this training guide covers this file)
├── scraper_server.py   ← HTTP server wrapper (advanced — covered separately)
├── run_for_n8n.py      ← command-line wrapper for automation
├── requirements.txt    ← list of third-party packages to install
├── venv/               ← virtual environment folder (created by you)
└── output/             ← generated output files go here
    ├── news_articles.csv
    ├── news_articles.html
    ├── news_articles.json
    └── news_articles.odt
```

---

## 4. Installing Dependencies

### Step 1 — Create a virtual environment

A **virtual environment** is an isolated Python workspace. It keeps packages for
this project separate from your system Python installation.

```bash
cd /home/sufideen/Documents/uk-news-scraper
python3 -m venv venv
```

### Step 2 — Activate the virtual environment

```bash
source venv/bin/activate
```

Your terminal prompt will change to show `(venv)` at the start.

### Step 3 — Install packages

```bash
pip install -r requirements.txt
```

**What is in `requirements.txt`?**

```
requests==2.31.0        # make HTTP web requests
beautifulsoup4==4.12.3  # parse HTML pages
lxml>=5.2.0             # fast HTML/XML parser (used by BeautifulSoup)
feedparser==6.0.11      # read RSS/Atom news feeds
python-dateutil==2.9.0  # convert date strings to Python date objects
odfpy==1.4.1            # create LibreOffice documents
```

### Step 4 — Run the scraper

```bash
python3 scraper.py
```

Watch the terminal — you will see log messages like:
```
2026-02-19 10:00:01 [INFO] Fetching RSS feed: https://feeds.bbci.co.uk/news/uk/rss.xml
2026-02-19 10:00:03 [INFO] BBC: found 30 RSS entries
...
2026-02-19 10:08:45 [INFO] Done. Output files:
2026-02-19 10:08:45 [INFO]   output/news_articles.csv
```

---

## 5. Code Walkthrough

### 5.1 Imports (lines 11–24)

```python
import csv        # built-in: read/write CSV files
import json       # built-in: read/write JSON files
import os         # built-in: file paths, create folders
import time       # built-in: pause execution (sleep)
import logging    # built-in: structured status messages
import random     # built-in: random number generation

from dataclasses import dataclass, fields   # built-in: create data containers
from datetime import datetime, timezone, UTC # built-in: date and time handling
from typing import Optional                  # built-in: type hints

import requests        # 3rd party: make HTTP web requests
import feedparser      # 3rd party: parse RSS/Atom feeds
from bs4 import BeautifulSoup  # 3rd party: parse and search HTML
from dateutil import parser as dateparser   # 3rd party: flexible date parsing
```

**Built-in vs third-party imports**

Python comes with a large "standard library" — modules you can import immediately
without installing anything. The modules at the top (`csv`, `json`, `os`, etc.)
are all built-in.

Modules like `requests`, `feedparser`, and `BeautifulSoup` are **third-party** —
they were written by the community and must be installed via `pip`.

**The `as` keyword**

```python
from dateutil import parser as dateparser
```

This imports the `parser` module from `dateutil` but gives it the local name
`dateparser`. This avoids confusion with Python's built-in `parser` if one existed.

---

### 5.2 Configuration Constants (lines 26–52)

```python
USER_AGENT = (
    "Mozilla/5.0 (compatible; UKNewsScraper/1.0; "
    "for personal/research use)"
)
REQUEST_TIMEOUT = 15   # seconds to wait before giving up on a request
MIN_DELAY = 2.0        # minimum seconds to pause between requests
MAX_DELAY = 5.0        # maximum seconds to pause between requests
```

**Why are these at the top of the file?**

By putting all settings in one place near the top, they are easy to find and
change. If you wanted to increase the timeout from 15 to 30 seconds, you change
one line, not ten scattered across the file.

**Naming convention:** Constants (values that never change) are written in
`ALL_CAPS_WITH_UNDERSCORES`. This is a Python convention — the language does not
technically enforce it, but all experienced Python programmers follow it.

**What is a User-Agent?**

When your browser visits a website, it sends a header called `User-Agent` that
identifies what software is making the request. Without it, many websites assume
the request is malicious and block it. The string above identifies this scraper
politely as a research tool.

```python
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept-Language": "en-GB,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,...",
}
```

This is a dictionary of **HTTP headers** sent with every web request. Think of
headers as metadata — extra information attached to the request, like a cover
letter.

**Logging setup:**

```python
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)
```

The `logging` module is better than `print()` for real programs because:
- Each message includes a **timestamp** automatically
- Messages have **severity levels**: DEBUG, INFO, WARNING, ERROR
- You can turn off verbose messages by changing `level=logging.INFO` to
  `level=logging.WARNING`

Usage throughout the file:
```python
log.info("BBC: found %d entries", 30)   # normal progress message
log.warning("Timeout fetching: %s", url) # something went wrong but recoverable
log.error("Scraper crashed: %s", error)  # serious failure
```

---

### 5.3 The Article Data Model (lines 56–65)

```python
@dataclass
class Article:
    source: str
    title: str
    url: str
    summary: str
    author: str
    published_date: str
```

**What is a class?**

A class is a **blueprint** for creating objects. An object is a bundle of related
data. Here, each `Article` object holds all the information about one news article.

**What is a dataclass?**

`@dataclass` is a **decorator** — it modifies the class automatically. Without it,
you would have to write a lot of repetitive code:

```python
# Without @dataclass — you would need to write this:
class Article:
    def __init__(self, source, title, url, summary, author, published_date):
        self.source = source
        self.title = title
        self.url = url
        self.summary = summary
        self.author = author
        self.published_date = published_date
```

The `@dataclass` decorator generates all of this automatically.

**Creating an Article object:**
```python
article = Article(
    source="BBC News",
    title="UK Inflation Falls",
    url="https://bbc.co.uk/news/...",
    summary="UK inflation fell to 3.2% in January...",
    author="Jane Smith",
    published_date="2026-02-19T09:00:00Z",
)

# Accessing fields:
print(article.title)   # "UK Inflation Falls"
print(article.author)  # "Jane Smith"
```

**Type hints** (`str`, `int`, etc.) tell other programmers what type of data
each field expects. Python does not enforce them at runtime, but they make the
code much easier to read.

```python
CSV_FIELDNAMES = [f.name for f in fields(Article)]
# Result: ["source", "title", "url", "summary", "author", "published_date"]
```

This is a **list comprehension** — a compact way to build a list. It calls the
`fields()` function (from `dataclasses`) which returns information about each
field, then extracts just the `name`. The result automatically stays in sync with
the `Article` class — if you add a new field, `CSV_FIELDNAMES` updates itself.

---

### 5.4 Utility / Helper Functions (lines 69–118)

Helper functions are small, reusable functions that do one specific thing. They
are defined once and called many times throughout the file.

---

#### `polite_get(url)` — Safe HTTP request (lines 69–83)

```python
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
```

**Breaking this down:**

`-> Optional[requests.Response]` is the **return type hint**. `Optional` means
the function can return either a `requests.Response` object OR `None` (if the
request failed).

`requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)` makes the HTTP GET
request. This is equivalent to typing a URL in your browser and pressing Enter.

`resp.raise_for_status()` checks the HTTP status code. If the website returned
an error (404 Not Found, 500 Server Error, etc.), this line raises an exception.
Without it, `requests` would return the error response silently.

**Multiple except blocks:** Different errors are caught and handled differently.
This is more precise than a single `except Exception` that catches everything.

| Exception | Meaning |
|-----------|---------|
| `Timeout` | Server did not respond within 15 seconds |
| `HTTPError` | Server responded with 4xx or 5xx status code |
| `RequestException` | Network failure, DNS error, etc. |

---

#### `parse_date(raw)` — Normalise date strings (lines 86–96)

```python
def parse_date(raw: str) -> str:
    if not raw:
        return ""
    try:
        dt = dateparser.parse(raw)
        if dt and dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ") if dt else raw
    except Exception:
        return raw
```

**The problem:** Different websites write dates in different formats:
- BBC: `"Wed, 19 Feb 2026 09:00:00 GMT"`
- Guardian: `"2026-02-19T09:00:00Z"`
- Independent: `"February 19, 2026"`

`dateparser.parse(raw)` converts any of these into a Python `datetime` object.
Then `.strftime("%Y-%m-%dT%H:%M:%SZ")` formats it consistently as ISO 8601
(`2026-02-19T09:00:00Z`).

**Why check `dt.tzinfo is None`?** Some date strings do not include timezone
information. We add UTC as a default to ensure consistency.

---

#### `delay()` — Polite pause (lines 99–101)

```python
def delay():
    time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
```

`time.sleep(seconds)` pauses the program for the given number of seconds.

`random.uniform(2.0, 5.0)` picks a random decimal number between 2.0 and 5.0.

**Why random?** A fixed delay (always exactly 2 seconds) can look automated.
A random delay between 2–5 seconds mimics human reading speed more naturally.

---

#### `parse_feed(url)` — Read an RSS feed (lines 104–110)

```python
def parse_feed(url: str) -> list:
    feed = feedparser.parse(url, agent=USER_AGENT)
    if feed.get("bozo") and not feed.entries:
        log.warning("Feed parse error for %s: %s", url, feed.get("bozo_exception"))
    return feed.entries
```

**What is RSS?**
RSS (Really Simple Syndication) is a standard format that news websites use to
publish article lists as XML. Every major news site has an RSS feed. RSS is
designed to be machine-readable, which makes it ideal for scrapers.

`feedparser.parse(url)` downloads the RSS feed and converts the XML into a Python
list of dictionaries (`feed.entries`). Each entry contains the article's title,
URL, summary, and publication date.

`feed.get("bozo")` — `feedparser` sets this to `True` if the feed XML was
malformed. "Bozo" is feedparser's own terminology for bad feeds.

---

#### `strip_html(raw)` — Remove HTML tags (lines 113–117)

```python
def strip_html(raw: str) -> str:
    if not raw:
        return ""
    return BeautifulSoup(raw, "lxml").get_text(strip=True)
```

RSS feed summaries often contain embedded HTML:
```
"<p>The <b>Prime Minister</b> said today that...</p>"
```

`BeautifulSoup(raw, "lxml")` parses that HTML string.
`.get_text(strip=True)` extracts only the plain text, removing all tags:
```
"The Prime Minister said today that..."
```

---

### 5.5 BBC News Scraper (lines 120–174)

BBC requires **two steps per article** because the RSS feed does not include the
author name — only the article's HTML page does.

```python
BBC_RSS_URL = "https://feeds.bbci.co.uk/news/uk/rss.xml"
```

#### Step 1 — Get the author from the article page

```python
def _bbc_get_author(article_url: str) -> str:
    resp = polite_get(article_url)
    if not resp:
        return ""
    soup = BeautifulSoup(resp.text, "lxml")

    # Try CSS selector 1: new BBC byline format
    node = soup.select_one('[data-testid="byline-new-contributors"] span')
    if node:
        return node.get_text(strip=True)

    # Try CSS selector 2: older BBC byline format
    node = soup.select_one('[data-component="byline-block"] a')
    if node:
        return node.get_text(strip=True)

    # Try HTML meta tag
    meta = soup.find("meta", {"name": "author"})
    if meta:
        return meta.get("content", "").strip()

    return ""  # give up — no author found
```

**The leading underscore in `_bbc_get_author`** is a convention meaning "this is
a private helper function — it is only meant to be used within this file, not
imported by other scripts."

**CSS Selectors:**
`soup.select_one('[data-testid="byline-new-contributors"] span')` finds the first
HTML element matching that CSS selector. This is the same selector syntax used in
web development and browser developer tools.

For example, this HTML:
```html
<div data-testid="byline-new-contributors">
    <span>Jane Smith</span>
</div>
```
...would return the `<span>` element, and `.get_text(strip=True)` would give
`"Jane Smith"`.

**Why three different selectors?** BBC has redesigned its website multiple times.
The function tries the newest format first, then falls back to older formats,
then the meta tag. This makes the scraper more resilient to website changes.

#### Step 2 — The main BBC scraper function

```python
def scrape_bbc() -> list:
    articles = []
    entries = parse_feed(BBC_RSS_URL)
    log.info("BBC: found %d RSS entries", len(entries))

    for entry in entries:
        title   = entry.get("title", "").strip()
        url     = entry.get("link", "").strip()
        summary = strip_html(entry.get("summary", ""))
        pub     = parse_date(entry.get("published", ""))
        author  = _bbc_get_author(url)
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
```

**`entry.get("title", "")`** — dictionary `.get()` with a default value.
If the key `"title"` does not exist in the dictionary, it returns `""` instead
of raising a `KeyError`. This prevents crashes when a feed entry is missing a field.

**`articles.append(...)`** — adds one `Article` object to the list for each RSS entry.

**`return articles`** — returns the completed list to whoever called the function.

---

### 5.6 The Guardian Scraper (lines 177–226)

The Guardian uses a different approach: a **JSON API** instead of HTML scraping.

```python
GUARDIAN_API_URL = "https://content.guardianapis.com/search"

def scrape_guardian(api_key: str = "test") -> list:
    params = {
        "section": "uk-news",
        "order-by": "newest",
        "page-size": "50",
        "show-fields": "byline,trailText",
        "api-key": api_key,       # "test" key works for low-volume personal use
    }

    resp = requests.get(GUARDIAN_API_URL, params=params, ...)
    data = resp.json()            # parse the JSON response
    results = data.get("response", {}).get("results", [])
```

**What is an API?**
An API (Application Programming Interface) is a service designed specifically for
programs to read data from. Instead of parsing messy HTML, you get clean, structured
JSON data. The Guardian offers a free API for personal use with `api-key=test`.

**Query parameters** (`params` dictionary) are appended to the URL:
```
https://content.guardianapis.com/search?section=uk-news&order-by=newest&...
```

**Chained `.get()` calls:**
`data.get("response", {}).get("results", [])` safely navigates a nested dictionary.
If `"response"` key is missing, it returns `{}` (empty dict), then `.get("results", [])`
on that returns `[]` (empty list) instead of crashing.

**The JSON response structure looks like:**
```json
{
  "response": {
    "results": [
      {
        "webTitle": "Article Title",
        "webUrl": "https://...",
        "webPublicationDate": "2026-02-19T09:00:00Z",
        "fields": {
          "byline": "Jane Smith",
          "trailText": "Summary text..."
        }
      }
    ]
  }
}
```

```python
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
```

---

### 5.7 Independent & Sky News Scrapers (lines 229–348)

Both follow the same pattern as BBC: RSS feed for the article list, with an
HTML fallback to find the author.

```python
def scrape_independent() -> list:
    entries = parse_feed(INDEPENDENT_RSS_URL)

    for entry in entries:
        author = entry.get("author", "").strip()  # try RSS first

        if not author:                             # RSS had no author?
            author = _independent_get_author(url) # visit the article page

        delay()
        articles.append(Article(...))
```

The key difference from BBC: the Independent and Sky News RSS feeds *sometimes*
include an author (in the `dc:creator` field). So the code tries the RSS feed
first, and only visits the article page if the author is missing. This saves
unnecessary HTTP requests.

---

### 5.8 Output Writers (lines 351–562)

All four output functions follow the same pattern:
1. Create the output folder if it does not exist
2. Build the data
3. Write to file
4. Log a confirmation message

#### CSV Writer (lines 353–367)

```python
def save_to_csv(articles: list, filepath: str) -> None:
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()
        for article in articles:
            writer.writerow({
                "source": article.source,
                "title": article.title,
                ...
            })
```

**`os.makedirs(..., exist_ok=True)`** — creates the `output/` folder if it does
not exist. `exist_ok=True` means it will not raise an error if the folder already
exists.

**`with open(...) as f:`** — the `with` statement (context manager) opens the
file and automatically closes it when the block ends, even if an error occurs.

**`newline=""`** — required for CSV files on Windows to prevent double line breaks.

**`csv.DictWriter`** — writes dictionaries as CSV rows. `writeheader()` writes
the column names in the first row. `writerow()` writes one data row.

---

#### HTML Writer (lines 372–428)

```python
def save_to_html(articles: list, filepath: str) -> None:
    generated_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    rows = ""
    for a in articles:
        rows += f"  <tr>\n    <td>{a.source}</td>\n    ..."

    html = f"""<!DOCTYPE html>
<html lang="en">
...
{rows}
...
</html>"""
```

**f-strings (formatted string literals):** Strings that start with `f"..."` or
`f"""..."""` allow embedding Python expressions inside `{}`:

```python
name = "Alice"
greeting = f"Hello, {name}!"  # "Hello, Alice!"
count = 42
message = f"Found {count} articles"  # "Found 42 articles"
```

**Escaped braces in f-strings:** Inside CSS, curly braces `{}` have a special
meaning in Python f-strings. To include a literal `{` in an f-string, write `{{`:

```python
html = f"body {{ color: red; }}"
# Result: "body { color: red; }"
```

---

#### JSON Writer (lines 433–452)

```python
def save_to_json(articles: list, filepath: str) -> None:
    payload = {
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total": len(articles),
        "articles": [
            {
                "source": a.source,
                "title": a.title,
                ...
            }
            for a in articles          # ← list comprehension
        ],
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
```

**List comprehension inside a dictionary:**
The `"articles"` key maps to a list comprehension that builds a list of
dictionaries — one per article. This is equivalent to:
```python
article_list = []
for a in articles:
    article_list.append({"source": a.source, "title": a.title, ...})
payload["articles"] = article_list
```

**`json.dump(payload, f, ensure_ascii=False, indent=2)`**
- `ensure_ascii=False` — allows non-ASCII characters (e.g., `é`, `ü`, `£`)
- `indent=2` — pretty-prints the JSON with 2-space indentation

---

#### ODT Writer — LibreOffice Document (lines 457–562)

This is the most complex writer. It uses the `odfpy` library to programmatically
build a LibreOffice Writer document.

```python
def save_to_odt(articles: list, filepath: str) -> None:
    from odf.opendocument import OpenDocumentText
    from odf.text import H, P, A
    from odf.table import Table, TableRow, TableCell
    ...
    doc = OpenDocumentText()        # create blank document

    # Define styles (fonts, colours, sizes)
    h1_style = Style(name="Heading1", family="paragraph")
    h1_style.addElement(TextProperties(fontsize="18pt", fontweight="bold"))
    doc.styles.addElement(h1_style)

    # Add content
    title = H(outlinelevel=1, stylename=h1_style)
    title.addText("UK News Articles")
    doc.text.addElement(title)

    # Build table
    table = Table()
    for a in articles:
        row = TableRow()
        row.addElement(make_cell(a.source))
        row.addElement(make_link_cell(a.title, a.url))
        table.addElement(row)

    doc.text.addElement(table)
    doc.save(filepath)
```

**Imports inside a function:** The `odf` imports are placed inside the function
rather than at the top of the file. This means `odfpy` is only loaded when
`save_to_odt()` is actually called, not when the script first starts.

**Helper functions defined inside a function:**
```python
def make_cell(text: str) -> TableCell:
    cell = TableCell()
    p = P(stylename=cell_style)
    p.addText(str(text) if text else "")
    cell.addElement(p)
    return cell
```

Functions can be defined inside other functions. These **inner functions**
(also called **nested functions**) are only accessible within the function
that contains them.

---

### 5.9 Email HTML Builder (lines 567–676)

```python
def get_html_email_body(articles: list, session_label: str = "") -> str:
```

**Purpose:** Build a Gmail-safe HTML email showing the top 10 articles per source.

**Special constraints for email HTML:**
- Gmail and other email clients **strip `<style>` blocks** — all CSS must be
  written inline: `style="color: red; font-size: 14px;"`
- Layout must use HTML `<table>` elements — email clients do not support CSS
  flexbox or grid layout
- Maximum width of 700px for compatibility with all email clients

```python
from collections import defaultdict

by_source: dict = defaultdict(list)
for a in articles:
    by_source[a.source].append(a)
```

**`defaultdict(list)`** is a special dictionary where any new key is automatically
assigned an empty list as its default value:
```python
d = defaultdict(list)
d["BBC"].append("article1")   # works — no KeyError
d["BBC"].append("article2")
print(d["BBC"])  # ["article1", "article2"]
```

With a regular `dict`, `d["BBC"].append(...)` would raise `KeyError: 'BBC'` the
first time. `defaultdict` eliminates that boilerplate.

```python
source_order = ["BBC News", "The Guardian", "The Independent", "Sky News"]
ordered_sources = [s for s in source_order if s in by_source]
ordered_sources += [s for s in by_source if s not in source_order]
```

This ensures the email always shows sources in a consistent order (BBC first,
then Guardian, etc.), while still including any unexpected sources at the end.

```python
top10 = by_source[source][:10]   # Python list slice: take first 10 items
```

**List slicing:** `my_list[start:end]` — if `start` is omitted it defaults to 0,
if `end` is omitted it defaults to the end of the list.
- `my_list[:10]` — first 10 items
- `my_list[5:]`  — everything from index 5 onwards
- `my_list[2:7]` — items at index 2, 3, 4, 5, 6

```python
bg = "#ffffff" if i % 2 == 0 else "#f7f9fc"
```

**Ternary expression:** A compact one-line if/else.
`value_if_true if condition else value_if_false`

`i % 2 == 0` checks if the row index is even (0, 2, 4...).
Even rows get white background, odd rows get light grey — this is called
**zebra striping** and makes tables easier to read.

---

### 5.10 The `main()` Function and Entry Point (lines 681–715)

```python
def main():
    all_articles = []

    scrapers = [
        ("BBC News",        scrape_bbc),
        ("The Guardian",    scrape_guardian),
        ("The Independent", scrape_independent),
        ("Sky News",        scrape_sky_news),
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
```

**List of tuples:**
```python
scrapers = [
    ("BBC News", scrape_bbc),
    ("The Guardian", scrape_guardian),
    ...
]
```
Each element is a **tuple** containing a string (display name) and a **function
reference** (the scraper function itself, not called yet — no `()` at the end).

**Tuple unpacking:**
```python
for name, fn in scrapers:
```
Each iteration gives us two variables at once: `name` (the string) and `fn`
(the function). Then `fn()` calls the function.

**Storing functions in variables** is a powerful Python feature. Functions are
"first-class objects" — they can be stored in lists, passed as arguments, etc.

**`all_articles.extend(results)`** — `.extend()` adds all items from `results`
into `all_articles`. Compare with `.append()` which would add the whole list as
a single element:
```python
a = [1, 2]
a.extend([3, 4])  # a is now [1, 2, 3, 4]

b = [1, 2]
b.append([3, 4])  # b is now [1, 2, [3, 4]]  ← probably not what you want
```

**The entry point guard:**
```python
if __name__ == "__main__":
    main()
```

This is one of the most important patterns in Python. When Python runs a script
directly (`python3 scraper.py`), it sets `__name__` to `"__main__"`. When another
script *imports* this file (`import scraper`), `__name__` is set to `"scraper"`
instead. So `main()` only runs when the file is executed directly — not when it
is imported. This is what allows `scraper_server.py` to do `import scraper` and
call individual scraper functions without triggering a full run.

---

## 6. Key Python Concepts

| Concept | Where Used | Quick Summary |
|---------|-----------|---------------|
| `@dataclass` | `Article` class | Auto-generates `__init__` and other methods |
| `Optional[T]` | `polite_get()` | Return type can be T or None |
| `try/except` | Throughout | Catch errors without crashing |
| List comprehension | `CSV_FIELDNAMES`, `save_to_json()` | Build lists in one line |
| `dict.get(key, default)` | Throughout | Safe dict lookup with fallback |
| `defaultdict` | `get_html_email_body()` | Dict with auto-initialised values |
| f-strings | `save_to_html()`, email builder | Embed variables in strings |
| `with open(...) as f:` | All file writers | Auto-close files |
| Nested functions | `save_to_odt()` | Functions defined inside functions |
| Functions in variables | `main()` scrapers list | Pass functions as data |
| Tuple unpacking | `for name, fn in scrapers:` | Assign multiple vars in one line |
| List slicing | `[:10]` | Extract part of a list |
| Ternary expression | zebra striping | One-line if/else |
| `__name__ == "__main__"` | Entry point | Run only when executed directly |

---

## 7. How the Internet Works (For Scrapers)

Understanding this context makes the code much clearer.

### HTTP Requests

When you type a URL in your browser:
1. Your browser sends an **HTTP GET request** to the server
2. The server responds with the **HTML** of the page
3. Your browser **renders** (displays) the HTML

A web scraper does steps 1 and 2, but instead of rendering the HTML, it **parses**
it — searching for specific data.

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | OK — success |
| 404 | Not Found — page does not exist |
| 403 | Forbidden — you are blocked |
| 429 | Too Many Requests — you are sending requests too fast |
| 500 | Internal Server Error — the website has a bug |

`resp.raise_for_status()` converts any non-2xx code into a Python exception.

### RSS Feeds

RSS is an XML format that websites publish to let readers/scrapers get a list
of recent articles without scraping the HTML. It looks like:

```xml
<rss version="2.0">
  <channel>
    <title>BBC News - UK</title>
    <item>
      <title>UK Inflation Falls</title>
      <link>https://bbc.co.uk/news/uk-12345</link>
      <description>UK inflation fell to 3.2%...</description>
      <pubDate>Wed, 19 Feb 2026 09:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
```

`feedparser` converts this XML into Python dictionaries automatically.

### BeautifulSoup and CSS Selectors

HTML is a tree of nested elements:
```html
<div class="article">
    <h1>Article Title</h1>
    <p class="byline">By <a href="/author/jane">Jane Smith</a></p>
</div>
```

**CSS selectors** let you target specific elements:
- `.byline` — element with class `byline`
- `div.article h1` — `h1` inside a `div` with class `article`
- `[data-testid="byline"]` — element with attribute `data-testid="byline"`

`soup.select_one(selector)` finds the first matching element.
`soup.find("meta", {"name": "author"})` finds a `<meta>` tag with that attribute.

---

## 8. Exercises

Complete these exercises to test your understanding. Use the actual `scraper.py`
code as reference.

### Exercise 1 — Read the data
Run the scraper and open `output/news_articles.json` in a text editor.
- How many articles were collected in total?
- What fields does each article have?
- Which source had the most articles?

### Exercise 2 — Understand `polite_get()`
Read the `polite_get()` function and answer:
- What does it return if the URL is an empty string?
- What does it return if the server responds with a 404 error?
- What exception does `raise_for_status()` raise for a 404?

### Exercise 3 — Trace `scrape_bbc()`
Follow the execution of `scrape_bbc()` step by step:
1. What URL does it fetch first?
2. For each RSS entry, what four pieces of data does it extract from the feed?
3. Which piece of data requires an extra HTTP request?
4. What object does it create for each entry?
5. What does it return?

### Exercise 4 — List comprehensions
Rewrite this list comprehension as a regular for loop:
```python
CSV_FIELDNAMES = [f.name for f in fields(Article)]
```

Then confirm both produce the same result.

### Exercise 5 — defaultdict
Without running the code, predict what this produces:
```python
from collections import defaultdict

by_source = defaultdict(list)
articles = ["BBC:story1", "Guardian:story1", "BBC:story2", "Sky:story1"]
for a in articles:
    source, title = a.split(":")
    by_source[source].append(title)

print(dict(by_source))
```

### Exercise 6 — Modify the scraper (guided)
The `save_to_csv()` function saves all articles. Modify it to save only
articles where the author is not an empty string.

Hint: add an `if` statement inside the for loop before `writer.writerow(...)`.

### Exercise 7 — Add a new output format (advanced)
Write a new function `save_to_txt(articles, filepath)` that saves a plain
text file with one article per line in this format:
```
[BBC News] UK Inflation Falls | Jane Smith | 2026-02-19
[The Guardian] Budget Plans Announced | Tom Brown | 2026-02-19
```

---

## 9. Common Errors and Fixes

| Error Message | Likely Cause | Fix |
|---------------|-------------|-----|
| `ModuleNotFoundError: No module named 'requests'` | Virtual environment not activated, or packages not installed | Run `source venv/bin/activate` then `pip install -r requirements.txt` |
| `lxml` build error during pip install | Old version of lxml specified | Ensure `requirements.txt` has `lxml>=5.2.0` (not `==5.1.0`) |
| `FileNotFoundError: [Errno 2] No such file or directory: 'output/...'` | `output/` folder missing | The script creates it automatically — if you see this, check `os.makedirs` line |
| `requests.exceptions.ConnectionError` | No internet connection or site is down | Check your internet connection; the scraper will log a warning and continue |
| `json.decoder.JSONDecodeError` | The Guardian API returned non-JSON | API may be overloaded; try again later |
| `DeprecationWarning: datetime.utcnow()` | Old datetime usage | Use `datetime.now(UTC)` instead (already correct in this file) |
| Script runs but produces 0 articles | CSS selectors on news sites changed | Inspect the website HTML and update selectors in the `_get_author` functions |

---

## 10. Glossary

| Term | Definition |
|------|-----------|
| **API** | Application Programming Interface — a service designed for programs to read data from, returning structured JSON |
| **BeautifulSoup** | Python library for parsing and searching HTML/XML documents |
| **Class** | A blueprint for creating objects with predefined fields and methods |
| **Constant** | A variable whose value is set once and never changed; written in ALL_CAPS by convention |
| **Context manager** | A `with` statement that handles setup and teardown automatically (e.g., opening and closing files) |
| **CSS selector** | A pattern for targeting specific HTML elements, e.g., `.byline` or `[data-testid="author"]` |
| **dataclass** | A Python class created with the `@dataclass` decorator that auto-generates common methods |
| **defaultdict** | A dictionary subclass that assigns a default value to new keys automatically |
| **decorator** | A function that modifies another function or class, written with `@` syntax |
| **entry point** | The `if __name__ == "__main__":` guard that runs code only when a script is executed directly |
| **f-string** | A Python string prefixed with `f` that allows embedding expressions: `f"Hello, {name}"` |
| **feedparser** | Python library for reading and parsing RSS/Atom feeds |
| **HTTP** | HyperText Transfer Protocol — the communication standard used on the web |
| **HTTP GET** | A type of HTTP request used to retrieve data from a web server |
| **ISO 8601** | International date/time format: `2026-02-19T09:00:00Z` |
| **JSON** | JavaScript Object Notation — a text format for structured data, widely used for APIs |
| **list comprehension** | A compact Python syntax for building lists: `[x*2 for x in my_list]` |
| **logging** | Built-in Python module for structured status messages with timestamps and severity levels |
| **Optional** | A type hint indicating a value can be a specific type OR `None` |
| **polite scraping** | Adding delays between requests to avoid overloading web servers |
| **RSS** | Really Simple Syndication — an XML format for publishing article lists from news sites |
| **tuple unpacking** | Assigning multiple variables from a tuple in one line: `a, b = (1, 2)` |
| **type hint** | An annotation showing expected data types: `def greet(name: str) -> str:` |
| **User-Agent** | An HTTP header that identifies the software making a web request |
| **virtual environment** | An isolated Python workspace that keeps project packages separate from the system Python |
| **web scraper** | A program that automatically visits websites and extracts structured data from them |

---

*End of Training Document*
*For questions, contact the internal Python Training Team.*
