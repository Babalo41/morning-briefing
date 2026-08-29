"""Intelligent web scraping layer using crawl4AI for content extraction.

Supplements RSS feeds with smart scraping from sources without feeds,
and enhances RSS feeds with semantic understanding via crawl4AI.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

log = logging.getLogger("scrape")

try:
    import crawl4ai
    HAS_CRAWL4AI = True
except ImportError:
    HAS_CRAWL4AI = False
    log.warning("crawl4ai not installed; web scraping disabled (RSS only)")


class ScrapingResult:
    """Structured result from scraping a URL."""
    def __init__(self, url: str, title: str, body: str, published_at: Optional[str] = None,
                 source: str = "scraped", author: str = ""):
        self.url = url
        self.title = title
        self.body = body
        self.published_at = published_at or datetime.now(timezone.utc).isoformat()
        self.source = source
        self.author = author

    def to_item(self) -> dict:
        """Convert to briefing item format."""
        return {
            "title": self.title,
            "body": self.body[:300],
            "url": self.url,
            "source": self.source,
            "published_at": self.published_at,
            "author": self.author,
        }


def scrape_url(url: str, semantic_instructions: str = "") -> Optional[ScrapingResult]:
    """Scrape a single URL with semantic understanding.

    Args:
        url: URL to scrape
        semantic_instructions: Optional prompt guiding extraction (e.g., "Extract technical content about networking")

    Returns:
        ScrapingResult if successful, None if scraping fails
    """
    try:
        if HAS_CRAWL4AI:
            return _scrape_with_crawl4ai(url, semantic_instructions)
        else:
            return _scrape_basic(url)
    except Exception as e:
        log.error(f"Scraping {url} failed: {e}")
        return None


def _scrape_with_crawl4ai(url: str, semantic_instructions: str) -> Optional[ScrapingResult]:
    """Use crawl4AI for intelligent content extraction."""
    try:
        import asyncio
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig

        async def crawl():
            try:
                config = CrawlerRunConfig(
                    word_count_threshold=10,
                    cache_mode="bypass",  # Always fetch fresh
                )

                async with AsyncWebCrawler() as crawler:
                    result = await crawler.arun(url, config=config)
                    return result
            except TypeError:
                # Fallback if CrawlerRunConfig parameters don't match
                async with AsyncWebCrawler() as crawler:
                    result = await crawler.arun(url)
                    return result

        result = asyncio.run(crawl())
        if not result:
            return None

        # Extract content - handle different result structures
        content = ""
        if hasattr(result, 'markdown') and result.markdown:
            content = result.markdown
        elif hasattr(result, 'html') and result.html:
            content = result.html[:500]
        else:
            return None

        # Parse metadata from the crawled page
        title = url.split("/")[-1]
        if hasattr(result, 'metadata') and result.metadata:
            if isinstance(result.metadata, dict) and 'title' in result.metadata:
                title = result.metadata.get("title", title)
        elif hasattr(result, 'title') and result.title:
            title = result.title

        body = content[:500] if content else ""
        if not body:
            return None

        return ScrapingResult(
            url=url,
            title=title,
            body=body,
            source="web_scrape_crawl4ai"
        )
    except Exception as e:
        log.error(f"crawl4ai scraping failed for {url}: {e}")
        return None


def _scrape_basic(url: str) -> Optional[ScrapingResult]:
    """Fallback: basic HTML scraping."""
    try:
        import requests
        from html.parser import HTMLParser

        response = requests.get(url, timeout=10)
        response.raise_for_status()

        class TextExtractor(HTMLParser):
            def __init__(self):
                super().__init__()
                self.text = []
                self.title = ""
                self.in_title = False

            def handle_starttag(self, tag, attrs):
                if tag == "title":
                    self.in_title = True
                elif tag in ("script", "style"):
                    self.text.append("<!-- removed -->")

            def handle_endtag(self, tag):
                if tag == "title":
                    self.in_title = False

            def handle_data(self, data):
                if self.in_title:
                    self.title = data.strip()
                else:
                    self.text.append(data.strip())

        parser = TextExtractor()
        parser.feed(response.text)

        body = " ".join(parser.text).strip()[:300]
        if not body or not parser.title:
            return None

        return ScrapingResult(
            url=url,
            title=parser.title,
            body=body,
            source="web_scrape_basic"
        )
    except Exception as e:
        log.error(f"Basic scraping failed for {url}: {e}")
        return None


def scrape_urls(urls: list[str], semantic_instructions: list[str] = None) -> list[ScrapingResult]:
    """Scrape multiple URLs in parallel."""
    import concurrent.futures

    instructions = semantic_instructions or [""] * len(urls)

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(scrape_url, url, instr): url
            for url, instr in zip(urls, instructions)
        }

        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                if result:
                    results.append(result)
            except Exception as e:
                log.error(f"Scraping task failed: {e}")

    return results
