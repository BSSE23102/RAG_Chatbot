# Requirements Document

## Introduction

This feature converts the existing Space Exploration RAG chatbot into a NetSol website chatbot. A web scraping script will crawl all public pages of https://www.netsoltech.com using Crawl4AI and output clean text/markdown content. That content replaces the current `.docx` knowledge source and is ingested into the existing FAISS vector store. The rest of the pipeline (LangChain, LangGraph, Groq LLM, FastAPI backend, React frontend) remains unchanged.

## Glossary

- **Scraper**: The standalone Python script that uses Crawl4AI to crawl and extract content from the NetSol website.
- **Crawl4AI**: The open-source Python library used to perform async, browser-based web crawling with markdown extraction.
- **Knowledge_File**: The file (or directory of files) containing scraped NetSol content, used as input to the ingestion pipeline.
- **Ingestion_Pipeline**: The existing `backend/app/ingestion.py` module that loads documents, chunks them, and builds the FAISS index.
- **Vector_Store**: The FAISS index persisted in `backend/data/faiss_index/`.
- **RAG_Service**: The existing LangChain + LangGraph pipeline in `backend/app/rag.py` that retrieves context and generates answers.
- **Config**: The `backend/app/config.py` settings module.
- **System_Prompt**: The LLM instruction string in `backend/app/rag.py` that scopes answers to the supplied context.

---

## Requirements

### Requirement 1: Web Scraping Script

**User Story:** As a developer, I want a scraping script that crawls the entire NetSol website, so that I can collect all public content as a knowledge base for the chatbot.

#### Acceptance Criteria

1. THE Scraper SHALL use Crawl4AI (latest stable version) to crawl https://www.netsoltech.com and all internally linked pages discovered during the crawl.
2. WHEN the Scraper visits a page, THE Scraper SHALL extract the main body content and output it in markdown format, excluding navigation menus, footers, cookie banners, and other boilerplate elements.
3. THE Scraper SHALL perform crawling asynchronously to reduce total crawl time.
4. WHEN a page returns an HTTP error (4xx or 5xx) or is unreachable, THE Scraper SHALL log the URL and error code and continue crawling the remaining pages.
5. THE Scraper SHALL deduplicate URLs so that each unique page is scraped at most once per run.
6. WHEN the crawl is complete, THE Scraper SHALL write the collected content to `backend/data/netsol_scraped/` as one markdown file per page, with the filename derived from the page URL slug.
7. THE Scraper SHALL print a summary to stdout after completion showing total pages attempted, pages succeeded, and pages failed.
8. WHERE a `--output-dir` CLI argument is provided, THE Scraper SHALL write files to that directory instead of the default.
9. WHERE a `--max-pages` CLI argument is provided, THE Scraper SHALL stop after crawling that many pages.

---

### Requirement 2: Knowledge Source Replacement

**User Story:** As a developer, I want the ingestion pipeline to load scraped NetSol markdown files instead of the Space Exploration `.docx`, so that the chatbot answers questions about NetSol.

#### Acceptance Criteria

1. THE Config SHALL provide a `knowledge_dir` setting pointing to the scraped content directory (`backend/data/netsol_scraped/`) in addition to the existing `knowledge_file` setting.
2. WHEN `knowledge_dir` is set and the directory exists and contains `.md` or `.txt` files, THE Ingestion_Pipeline SHALL load all files from that directory as documents instead of loading `knowledge_file`.
3. THE Ingestion_Pipeline SHALL assign each loaded document a `source` metadata field containing the originating file path.
4. IF `knowledge_dir` is not set or does not exist, THEN THE Ingestion_Pipeline SHALL fall back to loading `knowledge_file`, preserving backward compatibility.
5. WHEN the FAISS index already exists on disk, THE Ingestion_Pipeline SHALL load it without re-ingesting documents, matching existing behavior.

---

### Requirement 3: FAISS Index Rebuild

**User Story:** As a developer, I want to rebuild the FAISS vector store from the scraped NetSol content, so that the RAG pipeline retrieves relevant NetSol information.

#### Acceptance Criteria

1. WHEN the existing FAISS index directory is deleted and the application starts, THE Ingestion_Pipeline SHALL build a new FAISS index from the scraped NetSol documents.
2. THE Ingestion_Pipeline SHALL chunk documents using `RecursiveCharacterTextSplitter` with the `chunk_size` and `chunk_overlap` values from Config, preserving existing chunking behavior.
3. WHEN the index is built, THE Ingestion_Pipeline SHALL persist it to `faiss_index_dir` so subsequent startups load from disk.

---

### Requirement 4: Chatbot Persona Update

**User Story:** As a product owner, I want the chatbot to present itself as a NetSol website assistant, so that users understand the scope of questions it can answer.

#### Acceptance Criteria

1. THE System_Prompt SHALL instruct the LLM to act as a helpful assistant for the NetSol website, answering only from the supplied context.
2. WHEN a user asks a question outside the scope of the provided NetSol context, THE RAG_Service SHALL respond that it does not have information on that topic rather than hallucinating an answer.

---

### Requirement 5: Dependency Management

**User Story:** As a developer, I want all new dependencies declared explicitly, so that the environment can be reproduced reliably.

#### Acceptance Criteria

1. THE `backend/requirements.txt` SHALL include `crawl4ai` pinned to the latest stable version available at implementation time.
2. THE `backend/requirements.txt` SHALL retain all existing dependencies without modification.
3. IF `crawl4ai` requires additional system-level dependencies (e.g., Playwright browsers), THEN THE Scraper's README section SHALL document the one-time setup command required.
