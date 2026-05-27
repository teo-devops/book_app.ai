"""Scrape individual book metadata from Goodreads book pages.

Reads book IDs from my_list_of_books.txt, fetches each page with a headless
Chrome driver, and saves one JSON per book to ./data/Best_History_Books/.

Extracted fields (original + new):
  book_id, book_title, author, book_description, genres,
  average_rating, num_ratings, num_pages, year_published, scrape_date,
  series, language, isbn

Selectors last verified: 2026-04-16.  Goodreads can change HTML structure
without notice; check data-testid attributes and class names if extraction
starts returning empty strings.
"""

import json
import os
import random
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime

import bs4
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from unidecode import unidecode


BASE_DIR               = ""
FICHERO_LIBROS_ALUMNOS = os.path.join(BASE_DIR, "my_list_of_books.txt")
CARPETA_SALIDA         = os.path.join(BASE_DIR, "./data/Best_History_Books")
MAX_WORKERS            = 3

os.makedirs(CARPETA_SALIDA, exist_ok=True)


def get_driver() -> webdriver.Chrome:
    opts = Options()
    opts.add_argument("--headless")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    opts.add_experimental_option("prefs", {"profile.managed_default_content_settings.images": 2})
    return webdriver.Chrome(options=opts)


def _extract_book_details(soup: bs4.BeautifulSoup) -> dict[str, str]:
    """Parse the BookDetails block for language and ISBN.

    The block contains <div data-testid="bookDetails"> with pairs of
    <div class="DescListItem"> children, each with a dt (label) and dd (value).
    """
    result = {"language": "", "isbn": ""}
    details_block = soup.find("div", {"data-testid": "bookDetails"})
    if not details_block:
        return result

    for item in details_block.find_all("div", recursive=False):
        label_el = item.find(["dt", "span"])
        value_el = item.find(["dd", "div"])
        if not (label_el and value_el):
            continue
        label = label_el.get_text(strip=True).lower()
        value = value_el.get_text(strip=True)
        if "language" in label:
            result["language"] = unidecode(value)
        elif "isbn" in label:
            result["isbn"] = value.split()[0] if value else ""

    return result


def scrape_book_process(book_id: str) -> None:
    time.sleep(random.uniform(1, 3))
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Scraping: {book_id}", flush=True)

    driver = get_driver()
    try:
        driver.get(f"https://www.goodreads.com/book/show/{book_id}")

        wait = WebDriverWait(driver, 10)
        title_el = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "h1[data-testid='bookTitle']")))

        soup = bs4.BeautifulSoup(driver.page_source, "html.parser")

        title = unidecode(title_el.text.strip())

        desc_el = soup.find("div", {"data-testid": "description"})
        description = unidecode(desc_el.get_text(strip=True)) if desc_el else ""

        author_el = soup.find("span", class_="ContributorLink__name")
        author = unidecode(author_el.text.strip()) if author_el else ""

        genres_container = soup.find("div", {"data-testid": "genresList"})
        genres = (
            [unidecode(b.text.strip()) for b in genres_container.find_all("span", class_="Button__labelItem")]
            if genres_container else []
        )

        avg_rating  = soup.find("div", class_="RatingStatistics__rating")
        num_ratings = soup.find("span", {"data-testid": "ratingsCount"})
        pages_el    = soup.find("p",   {"data-testid": "pagesFormat"})
        pub_info_el = soup.find("p",   {"data-testid": "publicationInfo"})

        # Series: italic heading above the title area
        series_el = soup.find("h3", class_=lambda c: c and "italic" in c.lower())
        series = unidecode(series_el.text.strip()) if series_el else ""

        details = _extract_book_details(soup)

        data = {
            "book_id":        book_id,
            "book_title":     title,
            "author":         author,
            "book_description": description,
            "genres":         genres,
            "average_rating": avg_rating.text.strip() if avg_rating else "",
            "num_ratings":    num_ratings.text.split()[0].replace(",", "") if num_ratings else "0",
            "num_pages":      pages_el.text.split()[0] if pages_el else "",
            "year_published": pub_info_el.text.split()[-1] if pub_info_el else "",
            "series":         series,
            "language":       details["language"],
            "isbn":           details["isbn"],
            "scrape_date":    str(datetime.now()),
        }

        file_path = os.path.join(CARPETA_SALIDA, f"{book_id}_book-metadata.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        print(f"   OK: {title[:40]}", flush=True)

    except Exception as e:
        print(f"   ERROR {book_id}: {str(e)[:60]}", flush=True)
    finally:
        driver.quit()


def main():
    with open(FICHERO_LIBROS_ALUMNOS, "r") as f:
        book_ids = [line.strip() for line in f if line.strip()]

    existentes = [f.split("_book-metadata.json")[0] for f in os.listdir(CARPETA_SALIDA) if f.endswith(".json")]
    to_scrape  = [bid for bid in book_ids if bid not in existentes]

    print(f"Libros pendientes: {len(to_scrape):,}  |  Workers: {MAX_WORKERS}", flush=True)

    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        executor.map(scrape_book_process, to_scrape)


if __name__ == "__main__":
    main()
