# Implementation Plan: NetSol Website Chatbot

## Overview

Migrate the existing Space Exploration RAG chatbot to a NetSol website assistant by adding a Crawl4AI scraper, updating ingestion to load from a directory of markdown files, and updating the system prompt. All changes are additive or backward-compatible.

## Tasks

- [x] 1. Add `crawl4ai` to `backend/requirements.txt`
  - Append `crawl4ai==0.6.3` to `backend/requirements.txt`
  - Verify all existing packages are still present
  - _Requirements: 5.1, 5.2_

- [x] 2. Add `knowledge_dir` setting to `backend/app/config.py`
  - Add `knowledge_dir: Path = BASE_DIR / "backend" / "data" / "netsol_scraped"` field to `Settings`
  - Retain `knowledge_file` unchanged
  - _Requirements: 2.1_

  - [ ]* 2.1 Write unit test: `Settings.knowledge_dir` defaults to the expected path
    - Assert `settings.knowledge_dir` ends with `backend/data/netsol_scraped`
    - _Requirements: 2.1_

- [x] 3. Update `backend/app/ingestion.py` to support directory loading
  - [x] 3.1 Implement `load_documents_from_dir(directory: Path) -> list[Document]`
    - Glob `*.md` and `*.txt` in the directory
    - Use `TextLoader` for each file with `encoding="utf-8"`
    - Set `metadata["source"]` to the file path string
    - Skip unreadable files with a warning log; continue loading others
    - _Requirements: 2.2, 2.3_

  - [ ]* 3.2 Write property test for `load_documents_from_dir` (Property 5)
    - **Property 5: Directory loading with source metadata**
    - **Validates: Requirements 2.2, 2.3**
    - Use `hypothesis` + `tmp_path`; generate N random `.md` files; assert doc count == N and all have non-empty `metadata["source"]`

  - [x] 3.3 Update `load_or_create_vector_store` branching logic
    - After the existing FAISS-on-disk check, add: if `settings.knowledge_dir` exists and contains `.md`/`.txt` files → call `load_documents_from_dir`; else fall back to `knowledge_file`
    - If `knowledge_dir` exists but is empty, log a warning and fall back to `knowledge_file`
    - If both `knowledge_dir` is absent/empty and `knowledge_file` is missing, raise `FileNotFoundError` (preserve existing behavior)
    - _Requirements: 2.2, 2.4, 2.5, 3.1, 3.2, 3.3_

  - [ ]* 3.4 Write unit tests for `load_or_create_vector_store` branching
    - Test: loads from FAISS index when index dir exists (no re-ingestion)
    - Test: calls `load_documents_from_dir` when `knowledge_dir` has `.md` files
    - Test: falls back to `knowledge_file` when `knowledge_dir` is absent
    - Test: falls back to `knowledge_file` when `knowledge_dir` is empty
    - Test: index is persisted to `faiss_index_dir` after a fresh build
    - _Requirements: 2.4, 2.5, 3.1, 3.3_

  - [ ]* 3.5 Write property test for chunk size invariant (Property 6)
    - **Property 6: Chunk size invariant**
    - **Validates: Requirements 3.2**
    - Use `hypothesis`; generate random text documents; assert all chunks have `len(page_content) <= settings.chunk_size`

- [x] 4. Update `SYSTEM_PROMPT` in `backend/app/rag.py`
  - Replace existing `SYSTEM_PROMPT` with the NetSol-focused prompt from the design:
    ```
    "You are a helpful assistant for the NetSol Technologies website. "
    "Answer questions strictly based on the supplied context about NetSol's products, "
    "services, and company information. "
    "If the context does not contain enough information to answer the question, "
    "say that you do not have information on that topic."
    ```
  - No other changes to `rag.py`
  - _Requirements: 4.1, 4.2_

  - [ ]* 4.1 Write unit tests for `SYSTEM_PROMPT`
    - Assert `SYSTEM_PROMPT` contains "NetSol"
    - Assert `SYSTEM_PROMPT` contains "context"
    - _Requirements: 4.1_

- [ ] 5. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Create `scrape_netsol.py` at the project root
  - [x] 6.1 Implement `slugify(url: str) -> str`
    - Strip scheme and `www.`
    - Replace `/` and non-alphanumeric characters with `-`
    - Truncate to 200 characters
    - _Requirements: 1.6_

  - [ ]* 6.2 Write unit tests for `slugify`
    - Cover: URL with path segments, query string, fragment, spaces, special characters
    - Assert output contains no `/`, `?`, `#`, or spaces
    - Assert output length <= 200
    - _Requirements: 1.6_

  - [x] 6.3 Implement `CrawlSummary` dataclass
    - Fields: `attempted: int`, `succeeded: int`, `failed: int`, `failed_urls: list[tuple[str, str]]`
    - _Requirements: 1.7_

  - [x] 6.4 Implement `is_internal(url: str) -> bool` helper
    - Returns `True` only for URLs whose hostname is `netsoltech.com` or `www.netsoltech.com`
    - _Requirements: 1.1_

  - [ ]* 6.5 Write property test for same-domain URL filtering (Property 1)
    - **Property 1: Same-domain URL filtering**
    - **Validates: Requirements 1.1**
    - Use `hypothesis`; generate arbitrary URLs; assert `is_internal(url)` is True only for `netsoltech.com` variants

  - [x] 6.6 Implement `crawl(seed, output_dir, max_pages)` async function
    - BFS queue seeded with `seed` URL
    - Use `AsyncWebCrawler` from `crawl4ai`; extract `result.markdown`
    - Filter discovered links with `is_internal`; deduplicate via `visited` set
    - Write `<slugify(url)>.md` per successful page to `output_dir`
    - Catch per-page exceptions; append `(url, reason)` to `CrawlSummary.failed_urls`; continue
    - Respect `max_pages` limit if provided
    - Return `CrawlSummary`
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.9_

  - [ ]* 6.7 Write property test for URL deduplication (Property 2)
    - **Property 2: URL deduplication**
    - **Validates: Requirements 1.5**
    - Use `hypothesis`; generate URL lists with duplicates; assert each unique URL is visited at most once

  - [ ]* 6.8 Write property test for file-per-page count (Property 3)
    - **Property 3: File-per-page count**
    - **Validates: Requirements 1.6**
    - Generate N mock successful page results; assert output dir contains exactly N `.md` files

  - [ ]* 6.9 Write property test for max-pages limit (Property 4)
    - **Property 4: Max-pages limit**
    - **Validates: Requirements 1.9**
    - Generate `(pages_available, max_pages)` pairs; assert crawled count <= max_pages

  - [x] 6.10 Implement `main()` CLI entry point
    - Parse `--output-dir` (default: `backend/data/netsol_scraped`) and `--max-pages` args
    - Call `asyncio.run(crawl(...))`
    - Print `CrawlSummary` to stdout
    - Exit with code 1 if `succeeded == 0`
    - _Requirements: 1.7, 1.8, 1.9_

  - [ ]* 6.11 Write unit tests for `main()` CLI
    - Test: `--output-dir` arg routes output to specified directory
    - Test: `--max-pages` arg is parsed and passed to `crawl`
    - Test: HTTP error during crawl is recorded in `CrawlSummary.failed` and crawl continues
    - _Requirements: 1.4, 1.8, 1.9_

- [ ] 7. Write property test for existing dependencies retained (Property 7)
  - [ ]* 7.1 Write property test: original deps retained (Property 7)
    - **Property 7: Existing dependencies retained**
    - **Validates: Requirements 5.2**
    - Parse the original package list; assert every entry is present in the updated `backend/requirements.txt`

- [ ] 8. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP
- Property tests live in `backend/tests/test_properties.py`; unit tests in `backend/tests/test_unit.py`
- Each property test should include a comment like `# Feature: netsol-website-chatbot, Property N: <title>`
- `crawl4ai` requires a one-time Playwright browser install: `playwright install --with-deps chromium`
- All changes to `ingestion.py` and `config.py` are backward-compatible; existing `.docx` path still works
