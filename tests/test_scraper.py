"""
Unit tests for scraper.py
Run with: pytest tests/ -v
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import scraper
from scraper import Article, parse_date, strip_html, polite_get


# ── Article dataclass ──────────────────────────────────────────────────────────

class TestArticleDataclass:

    def test_article_creation(self):
        a = Article(
            source="BBC News",
            title="Test Headline",
            url="https://bbc.co.uk/news/test",
            summary="Test summary text.",
            author="Jane Smith",
            published_date="2026-02-19T09:00:00Z",
        )
        assert a.source == "BBC News"
        assert a.title == "Test Headline"
        assert a.url == "https://bbc.co.uk/news/test"
        assert a.author == "Jane Smith"

    def test_article_empty_author_allowed(self):
        a = Article(
            source="BBC News",
            title="No Author Article",
            url="https://bbc.co.uk/news/test2",
            summary="Summary",
            author="",
            published_date="2026-02-19T09:00:00Z",
        )
        assert a.author == ""

    def test_csv_fieldnames_match_article_fields(self):
        expected = ["source", "title", "url", "summary", "author", "published_date"]
        assert scraper.CSV_FIELDNAMES == expected


# ── parse_date ─────────────────────────────────────────────────────────────────

class TestParseDate:

    def test_iso_format_passthrough(self):
        result = parse_date("2026-02-19T09:00:00Z")
        assert result == "2026-02-19T09:00:00Z"

    def test_rss_date_format(self):
        result = parse_date("Wed, 19 Feb 2026 09:00:00 GMT")
        assert "2026-02-19" in result

    def test_empty_string_returns_empty(self):
        assert parse_date("") == ""

    def test_none_like_empty(self):
        assert parse_date("") == ""

    def test_invalid_date_returns_raw(self):
        result = parse_date("not-a-date-at-all-xyz")
        assert result == "not-a-date-at-all-xyz"

    def test_date_without_timezone_gets_utc(self):
        result = parse_date("2026-02-19 09:00:00")
        assert "2026-02-19" in result
        assert result.endswith("Z")


# ── strip_html ─────────────────────────────────────────────────────────────────

class TestStripHtml:

    def test_removes_paragraph_tags(self):
        result = strip_html("<p>Hello world</p>")
        assert result == "Hello world"

    def test_removes_bold_tags(self):
        result = strip_html("The <b>Prime Minister</b> said")
        # lxml strips inline tags — text content is preserved even if whitespace merges
        assert "Prime Minister" in result
        assert "<b>" not in result

    def test_empty_string_returns_empty(self):
        assert strip_html("") == ""

    def test_plain_text_unchanged(self):
        result = strip_html("No HTML here")
        assert result == "No HTML here"

    def test_nested_tags(self):
        result = strip_html("<div><p><a href='#'>Link text</a></p></div>")
        assert result == "Link text"

    def test_strips_whitespace(self):
        result = strip_html("  <p>  spaced  </p>  ")
        assert "spaced" in result


# ── polite_get ─────────────────────────────────────────────────────────────────

class TestPoliteGet:

    def test_returns_none_for_empty_url(self):
        result = polite_get("")
        assert result is None

    def test_returns_none_for_none_url(self):
        result = polite_get(None)
        assert result is None

    @patch("scraper.requests.get")
    def test_successful_request(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        result = polite_get("https://example.com")
        assert result == mock_resp

    @patch("scraper.requests.get")
    def test_timeout_returns_none(self, mock_get):
        import requests as req
        mock_get.side_effect = req.exceptions.Timeout()
        result = polite_get("https://example.com")
        assert result is None

    @patch("scraper.requests.get")
    def test_http_error_returns_none(self, mock_get):
        import requests as req
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        http_error = req.exceptions.HTTPError(response=mock_resp)
        mock_get.return_value = mock_resp
        mock_resp.raise_for_status.side_effect = http_error

        result = polite_get("https://example.com/missing")
        assert result is None

    @patch("scraper.requests.get")
    def test_network_error_returns_none(self, mock_get):
        import requests as req
        mock_get.side_effect = req.exceptions.ConnectionError()
        result = polite_get("https://unreachable.example.com")
        assert result is None


# ── get_html_email_body ────────────────────────────────────────────────────────

class TestGetHtmlEmailBody:

    def _make_articles(self, source, count=5):
        return [
            Article(
                source=source,
                title=f"{source} Headline {i}",
                url=f"https://example.com/{i}",
                summary=f"Summary {i}",
                author=f"Author {i}",
                published_date="2026-02-19T09:00:00Z",
            )
            for i in range(count)
        ]

    def test_returns_html_string(self):
        articles = self._make_articles("BBC News", 3)
        result = scraper.get_html_email_body(articles)
        assert isinstance(result, str)
        assert "<div" in result

    def test_contains_source_name(self):
        articles = self._make_articles("BBC News", 3)
        result = scraper.get_html_email_body(articles)
        assert "BBC News" in result

    def test_caps_at_10_per_source(self):
        articles = self._make_articles("The Guardian", 20)
        result = scraper.get_html_email_body(articles)
        # Only first 10 titles should appear
        assert "The Guardian Headline 9" in result
        assert "The Guardian Headline 10" not in result

    def test_session_label_included(self):
        articles = self._make_articles("Sky News", 2)
        result = scraper.get_html_email_body(articles, session_label="Morning Briefing")
        assert "Morning Briefing" in result

    def test_multiple_sources_all_present(self):
        articles = (
            self._make_articles("BBC News", 3) +
            self._make_articles("The Guardian", 3) +
            self._make_articles("Sky News", 3)
        )
        result = scraper.get_html_email_body(articles)
        assert "BBC News" in result
        assert "The Guardian" in result
        assert "Sky News" in result

    def test_inline_css_no_style_block(self):
        articles = self._make_articles("BBC News", 2)
        result = scraper.get_html_email_body(articles)
        # Gmail strips <style> blocks — should use inline CSS only
        assert "<style>" not in result
        assert "style=" in result


# ── save_to_csv ────────────────────────────────────────────────────────────────

class TestSaveToCSV:

    def test_creates_file(self, tmp_path):
        articles = [
            Article("BBC News", "Title", "https://x.com", "Summary", "Author", "2026-01-01")
        ]
        filepath = str(tmp_path / "test.csv")
        scraper.save_to_csv(articles, filepath)
        assert os.path.exists(filepath)

    def test_csv_has_header(self, tmp_path):
        articles = [
            Article("BBC News", "Title", "https://x.com", "Summary", "Author", "2026-01-01")
        ]
        filepath = str(tmp_path / "test.csv")
        scraper.save_to_csv(articles, filepath)
        with open(filepath) as f:
            first_line = f.readline()
        assert "source" in first_line
        assert "title" in first_line

    def test_csv_row_count(self, tmp_path):
        import csv as csv_mod
        articles = [
            Article("BBC News", f"Title {i}", f"https://x.com/{i}", "S", "A", "2026-01-01")
            for i in range(5)
        ]
        filepath = str(tmp_path / "test.csv")
        scraper.save_to_csv(articles, filepath)
        with open(filepath) as f:
            rows = list(csv_mod.DictReader(f))
        assert len(rows) == 5


# ── save_to_json ───────────────────────────────────────────────────────────────

class TestSaveToJSON:

    def test_creates_valid_json(self, tmp_path):
        import json
        articles = [
            Article("The Guardian", "Title", "https://x.com", "Summary", "Author", "2026-01-01")
        ]
        filepath = str(tmp_path / "test.json")
        scraper.save_to_json(articles, filepath)
        with open(filepath) as f:
            data = json.load(f)
        assert data["total"] == 1
        assert len(data["articles"]) == 1
        assert data["articles"][0]["source"] == "The Guardian"

    def test_json_has_generated_at(self, tmp_path):
        import json
        articles = [
            Article("Sky News", "T", "https://x.com", "S", "A", "2026-01-01")
        ]
        filepath = str(tmp_path / "test.json")
        scraper.save_to_json(articles, filepath)
        with open(filepath) as f:
            data = json.load(f)
        assert "generated_at" in data
