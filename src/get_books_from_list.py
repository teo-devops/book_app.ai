"""Scrape Goodreads Listopia pages and collect book IDs.

Usage examples
--------------
# Single list (original behaviour):
python get_books_from_list.py --url_path "https://www.goodreads.com/list/show/29013"

# Multiple lists, append to existing file without duplicates:
python get_books_from_list.py \
    --url_paths "https://www.goodreads.com/list/show/29013,https://www.goodreads.com/list/show/268" \
    --output_directory_path my_list_of_books.txt

# Recommended lists for Historia/Biografía niche:
#   29013  - Best Biographies
#   268    - Best History Books of the 20th Century
#   7441   - Best Non Fiction Books of All Time
#   25001  - Best Military History
"""

import argparse
import os
from datetime import datetime

import bs4
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


DEFAULT_URL    = "https://www.goodreads.com/list/show/29013.Best_Biographies_"
DEFAULT_OUTPUT = "my_list_of_books.txt"


def _espera(driver, tag, locator):
    """Wait up to 3 s for an element; return -1 on timeout."""
    try:
        by = By.ID if tag == "id" else By.XPATH
        WebDriverWait(driver, 3).until(EC.presence_of_element_located((by, locator)))
    except Exception:
        return -1


def _get_book_ids(soup) -> list[str]:
    """Extract book IDs from one page of a Listopia list."""
    return [
        a["href"].split("/book/show/")[1]
        for a in soup.find_all("a", class_="bookTitle", itemprop="url")
        if "/book/show/" in a.get("href", "")
    ]


def scrape_list(url: str, driver: webdriver.Chrome) -> list[str]:
    """Scrape all book IDs from a Goodreads Listopia URL."""
    book_ids: list[str] = []
    driver.get(url)

    while True:
        while _espera(driver, "xpath", '//*[@id="all_votes"]/table/tbody/tr[1]/td[3]/a') == -1:
            pass


        soup = bs4.BeautifulSoup(driver.page_source, "html.parser")
        page_ids = _get_book_ids(soup)
        book_ids.extend(page_ids)
        print(f"  {len(book_ids)} IDs acumulados...", flush=True)

        # Dismiss login popup if present
        try:
            popup = WebDriverWait(driver, 1).until(
                EC.presence_of_element_located((By.XPATH, "/html/body/div[3]/div/div/div[2]"))
            )
            if popup.is_displayed():
                btn = popup.find_element(By.XPATH, "/html/body/div[3]/div/div/div[1]/button")
                btn.click()
        except Exception:
            pass

        # Next page
        try:
            next_btn = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "next_page"))
            )
            if "disabled" in (next_btn.get_attribute("class") or ""):
                break
            next_btn.click()
        except TimeoutException:
            break

    return book_ids


def load_existing_ids(path: str) -> set[str]:
    """Load IDs already saved in the output file."""
    if not os.path.exists(path):
        return set()
    with open(path, encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip()}


def main():
    start = datetime.now()
    parser = argparse.ArgumentParser(description="Scrape Goodreads Listopia book IDs.")

    # Legacy single-URL argument kept for backwards compatibility
    parser.add_argument("--url_path",  type=str, default=DEFAULT_URL,
                        help="Single Goodreads list URL (legacy).")
    # New multi-URL argument takes priority if provided
    parser.add_argument("--url_paths", type=str, default=None,
                        help="Comma-separated list of Goodreads list URLs.")
    parser.add_argument("--output_directory_path", type=str, default=DEFAULT_OUTPUT,
                        help="Output .txt file path (appends without duplicates).")
    args = parser.parse_args()

    urls = (
        [u.strip() for u in args.url_paths.split(",") if u.strip()]
        if args.url_paths
        else [args.url_path]
    )

    existing_ids = load_existing_ids(args.output_directory_path)
    print(f"IDs ya existentes en '{args.output_directory_path}': {len(existing_ids)}")

    driver = webdriver.Chrome(options=Options())
    all_new_ids: list[str] = []

    for url in urls:
        print(f"\nScraping lista: {url}", flush=True)
        ids = scrape_list(url, driver)
        new = [bid for bid in ids if bid not in existing_ids]
        all_new_ids.extend(new)
        existing_ids.update(new)
        print(f"  Nuevos IDs de esta lista: {len(new)}")

    driver.quit()

    # Write merged, deduplicated list
    with open(args.output_directory_path, "w", encoding="utf-8") as f:
        for bid in sorted(existing_ids):
            f.write(bid + "\n")

    elapsed = datetime.now() - start
    print(f"\n{'='*55}")
    print(f"IDs nuevos añadidos  : {len(all_new_ids)}")
    print(f"Total IDs en fichero : {len(existing_ids)}")
    print(f"Guardado en          : {args.output_directory_path}")
    print(f"Tiempo total         : {elapsed}")
    print("=== Scraping completado ===")


if __name__ == "__main__":
    main()
