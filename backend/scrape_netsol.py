"""
scrape_netsol.py — Standalone web scraper for https://www.netsoltech.com

Crawls the entire NetSol Technologies public website using Crawl4AI and writes
one markdown file per page into an output directory (default:
backend/data/netsol_scraped/).

Usage:
    python scrape_netsol.py [--output-dir PATH] [--max-pages N]

Examples:
    python scrape_netsol.py
    python scrape_netsol.py --output-dir /tmp/netsol --max-pages 50

Prerequisites (one-time setup):
    pip install crawl4ai
    crawl4ai-setup   # installs Playwright browsers required by Crawl4AI
"""

import io
import sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import argparse
import asyncio
import logging
import re
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from crawl4ai import AsyncWebCrawler

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
SEED_URLS = ["https://careers.netsoltech.com"]
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "data" / "raw_scraped"
_INTERNAL_HOSTNAMES = {"careers.netsoltech.com"}

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class CrawlSummary:
    """Aggregated statistics for a completed crawl run."""

    attempted: int = 0
    succeeded: int = 0
    failed: int = 0
    failed_urls: list[tuple[str, str]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def slugify(url: str) -> str:
    """Convert a URL into a safe filesystem filename (without extension).

    Steps:
    1. Strip scheme (https://, http://) and leading www.
    2. Replace forward slashes and non-alphanumeric characters with hyphens.
    3. Collapse consecutive hyphens into one.
    4. Strip leading/trailing hyphens.
    5. Truncate to 200 characters.
    6. Return "index" if the result is empty.
    """
    # Remove scheme
    slug = re.sub(r"^https?://", "", url)
    # Remove leading www.
    slug = re.sub(r"^www\.", "", slug)
    # Replace any non-alphanumeric character (including / ? # = & etc.) with -
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", slug)
    # Collapse consecutive dashes
    slug = re.sub(r"-{2,}", "-", slug)
    # Strip leading/trailing dashes
    slug = slug.strip("-")
    # Truncate
    slug = slug[:200]
    # Fallback
    return slug if slug else "index"


def is_internal(url: str) -> bool:
    """Return True only if *url* belongs to netsoltech.com (with or without www.)."""
    try:
        hostname = urlparse(url).hostname or ""
        return hostname in _INTERNAL_HOSTNAMES
    except Exception:
        return False


def clean_markdown(text: str) -> str:
    """Clean raw Crawl4AI markdown output for use as RAG knowledge.

    Removes navigation boilerplate, excessive whitespace, cookie banners,
    repeated separators, and other noise that degrades retrieval quality.
    """
    # Drop lines that are pure horizontal rules (--- / *** / ___)
    text = re.sub(r"^[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)

    # Drop image-only lines: ![...](...) with nothing else
    text = re.sub(r"^!\[.*?\]\(.*?\)\s*$", "", text, flags=re.MULTILINE)

    # Drop lines that look like nav/cookie/footer noise (common patterns)
    noise_patterns = [
        r"(?i)^(skip to (main )?content|cookie policy|accept (all )?cookies?|privacy policy)",
        r"(?i)^(all rights reserved|copyright ©|\u00a9)",
        r"(?i)^(home\s*[>|/]|breadcrumb)",
        r"(?i)^\s*(menu|navigation|search\.\.\.)\s*$",
        r"(?i)^(subscribe to|sign up for|follow us on)",
    ]
    for pat in noise_patterns:
        text = re.sub(pat, "", text, flags=re.MULTILINE)

    # Collapse 3+ consecutive blank lines into 2
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# ---------------------------------------------------------------------------
# Async crawl engine
# ---------------------------------------------------------------------------


async def crawl(
    seeds: list[str],
    output_dir: Path,
    max_pages: int | None = None,
) -> CrawlSummary:
    """BFS async crawl starting from *seeds*, writing one .md file per page.

    Args:
        seeds: The starting URLs.
        output_dir: Directory where markdown files are written.
        max_pages: Optional upper bound on pages to crawl.

    Returns:
        A :class:`CrawlSummary` with counts of attempted/succeeded/failed pages.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    summary = CrawlSummary()
    visited: set[str] = set()
    queue: deque[str] = deque(seeds)
    for seed in seeds:
        visited.add(seed)

    # Track used filenames to avoid collisions (same slug from different URLs)
    used_filenames: set[str] = set()

    async with AsyncWebCrawler() as crawler:
        while queue:
            if max_pages is not None and summary.attempted >= max_pages:
                break

            url = queue.popleft()
            summary.attempted += 1
            logger.info("Crawling (%d): %s", summary.attempted, url)

            try:
                result = await crawler.arun(url=url)
            except Exception as exc:
                reason = f"{type(exc).__name__}: {exc}"
                logger.warning("Failed to crawl %s — %s", url, reason)
                summary.failed += 1
                summary.failed_urls.append((url, reason))
                continue

            # ------------------------------------------------------------------
            # Extract markdown content
            # ------------------------------------------------------------------
            markdown_content: str | None = None
            raw = getattr(result, "markdown", None)

            if raw is None:
                # No markdown at all — skip
                pass
            elif isinstance(raw, str):
                markdown_content = raw if raw.strip() else None
            else:
                # Likely a MarkdownGenerationResult object
                raw_md = getattr(raw, "raw_markdown", None)
                if isinstance(raw_md, str) and raw_md.strip():
                    markdown_content = raw_md

            if not markdown_content:
                logger.warning("No markdown content for %s — skipping file write", url)
                summary.failed += 1
                summary.failed_urls.append((url, "empty or missing markdown content"))
                # Still enqueue discovered links below
            else:
                # ------------------------------------------------------------------
                # Write file (handle filename collisions)
                # ------------------------------------------------------------------
                base_slug = slugify(url)
                filename = f"{base_slug}.md"
                counter = 1
                while filename in used_filenames:
                    filename = f"{base_slug}-{counter}.md"
                    counter += 1
                used_filenames.add(filename)

                file_path = output_dir / filename
                file_path.write_text(clean_markdown(markdown_content), encoding="utf-8")
                logger.info("Wrote %s", file_path)
                summary.succeeded += 1

            # ------------------------------------------------------------------
            # Discover and enqueue internal links
            # ------------------------------------------------------------------
            links: list[dict] = []

            # Internal links reported by Crawl4AI
            links.extend(result.links.get("internal", []) if result.links else [])

            # External links that are actually on the same domain
            for link in result.links.get("external", []) if result.links else []:
                href = link.get("href", "")
                if is_internal(href):
                    links.append(link)

            for link in links:
                href = link.get("href", "")
                if not href:
                    continue
                # Normalise: drop fragments
                parsed = urlparse(href)
                normalised = parsed._replace(fragment="").geturl()
                if normalised and normalised not in visited and is_internal(normalised):
                    visited.add(normalised)
                    queue.append(normalised)

    return summary


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Parse CLI arguments, run the crawl, and print a summary."""
    parser = argparse.ArgumentParser(
        description="Crawl https://www.netsoltech.com and save pages as markdown.",
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help="Directory to write scraped markdown files (default: %(default)s)",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        metavar="N",
        help="Stop after crawling N pages (default: no limit)",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    summary = asyncio.run(crawl(SEED_URLS, output_dir, args.max_pages))

    print(
        f"\nCrawl complete. "
        f"Attempted: {summary.attempted} | "
        f"Succeeded: {summary.succeeded} | "
        f"Failed: {summary.failed}"
    )

    if summary.failed_urls:
        print("\nFailed URLs:")
        for url, reason in summary.failed_urls:
            print(f"  {url}  —  {reason}")

    if summary.succeeded == 0:
        print("\nNo pages were successfully scraped. Exiting with error.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
