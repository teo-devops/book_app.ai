# AGENTS.md

This file provides guidance to coding agents working with code in this repository.

## Project Overview

A book recommendation pipeline built on Goodreads data. The intended flow is:

1. **Scrape list** — `get_books_from_list.py` crawls a Goodreads Listopia page and outputs book IDs to `src/my_list_of_books.txt`
2. **Scrape metadata** — `get_books.py` reads that ID list and fetches per-book metadata from Goodreads, saving each as a JSON file under `src/data/<list_name>/`
3. **EDA & cleaning** — `notebooks/01_eda_and_cleaning.ipynb` (currently a scaffold)
4. **Embeddings & vector DB** — `notebooks/02_embeddings_and_vector_db.ipynb` (scaffold)
5. **LLM interface** — `notebooks/03_LLM_interface.ipynb` (scaffold)

## Environment Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Both scraping scripts require **Chrome** (headless) and the `chromedriver` binary to be available. `geckodriver-autoinstaller` is in requirements but the scripts currently use `webdriver.Chrome`, not Firefox.

## Running the Scripts

**Step 1 — collect book IDs from a Goodreads list:**
```bash
cd src
python get_books_from_list.py --url_path "https://www.goodreads.com/list/show/<ID>" --output_directory_path my_list_of_books.txt
```
This opens a **non-headless** Chrome window and pages through the list; the script must run in a GUI environment.

**Step 2 — scrape per-book metadata (headless, parallel):**
```bash
cd src
python get_books.py
```
Skips books already scraped (checks for existing JSON files). Parallelism is controlled by `MAX_WORKERS` (default 3). Output goes to `./data/Best_History_Books/`.

## Data Schema

Each scraped book produces one JSON file named `<book_id>_book-metadata.json`:

```json
{
  "book_id": "22551730-dead-wake",
  "book_title": "...",
  "author": "...",
  "book_description": "...",
  "genres": ["Nonfiction", "History", ...],
  "average_rating": "4.13",
  "num_ratings": "164026",
  "num_pages": "430",
  "year_published": "2015",
  "scrape_date": "2026-04-16 21:25:17.329923"
}
```

## Key Architecture Notes

- `get_books.py` uses `ProcessPoolExecutor` (not threads) because each worker creates its own `webdriver.Chrome` instance — Chrome drivers are not thread-safe.
- Scraping targets Goodreads `data-testid` attributes (e.g. `bookTitle`, `description`, `ratingsCount`). These are brittle; Goodreads can change them without notice.
- `unidecode` is applied to all text fields at scrape time to strip non-ASCII characters. Keep this in mind when doing text matching or search.
- The `credentials` package is listed in `requirements.txt` but not yet used in any source file — likely reserved for future API key management.
