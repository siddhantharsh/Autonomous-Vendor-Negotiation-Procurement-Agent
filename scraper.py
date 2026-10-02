# Note: IndiaMART's markup is unstable and selectors may need periodic maintenance.
# Please respect rate limits and IndiaMART's Terms of Service/robots.txt when scraping.

import random
import tempfile
import shutil
import time
import zipfile
import hashlib
import os
import json
import re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from urllib.parse import urljoin, urlparse
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from scrapers.factory import ScraperFactory

try:
    from gdrive_utils import (
        authenticate_gdrive,
        find_or_create_folder,
        upload_file_to_gdrive,
    )
    GDRIVE_AVAILABLE = True
except ImportError:
    GDRIVE_AVAILABLE = False


def init_driver(headless=True):
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--allow-running-insecure-content")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    return driver


def sanitize_filename(text):
    if not text:
        return "unknown"
    text = re.sub(r'[<>:"/\\|?*]', "_", text)
    text = re.sub(r"\s+", "_", text)
    text = text.strip("._")
    return text[:50] if len(text) > 50 else text


def generate_content_hash(data):
    json_str = json.dumps(data, sort_keys=True)
    return hashlib.md5(json_str.encode()).hexdigest()[:8]


def create_unique_filename(product_data):
    product_name = sanitize_filename(product_data.get("name", product_data.get("product_name", "unknown")))
    if "supplier" in product_data and isinstance(product_data["supplier"], dict):
        supplier_name = sanitize_filename(product_data["supplier"].get("name", "unknown"))
    else:
        supplier_name = sanitize_filename(product_data.get("supplier_name", "unknown"))
    url = product_data.get("url", product_data.get("URL", ""))
    url_hash = hashlib.md5(url.encode()).hexdigest()[:6]
    return f"{product_name}_{supplier_name}_{url_hash}.json"


def is_duplicate_content(new_data, existing_files_dir):
    new_hash = generate_content_hash(new_data)
    if not os.path.exists(existing_files_dir):
        return False
    for filename in os.listdir(existing_files_dir):
        if filename.endswith(".json"):
            try:
                filepath = os.path.join(existing_files_dir, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
                if generate_content_hash(existing_data) == new_hash:
                    return True
            except Exception:
                continue
    return False


def cleanup_local_files(json_files, zip_filepath, temp_dir):
    try:
        for json_file in json_files:
            if json_file and os.path.exists(json_file):
                os.remove(json_file)
        if zip_filepath and os.path.exists(zip_filepath):
            os.remove(zip_filepath)
        if os.path.exists(temp_dir) and not os.listdir(temp_dir):
            os.rmdir(temp_dir)
    except Exception as e:
        print(f"Warning: Could not clean up some local files: {e}")


def save_product_as_json(product_data, temp_dir):
    if is_duplicate_content(product_data, temp_dir):
        return None
    os.makedirs(temp_dir, exist_ok=True)
    filename = create_unique_filename(product_data)
    filepath = os.path.join(temp_dir, filename)
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(product_data, f, indent=2, ensure_ascii=False)
        return filepath
    except Exception as e:
        print(f"Save failed: {e}")
        return None


def safe_element_text(driver, by, selector):
    try:
        element = driver.find_element(by, selector)
        return element.text.strip()
    except Exception:
        return ""


def extract_category_from_url(url):
    try:
        parsed = urlparse(url)
        path_parts = parsed.path.strip("/").split("/")
        if "impcat" in parsed.path:
            return path_parts[-1].replace(".html", "").replace("-", " ").title()
        elif "proddetail" in parsed.path:
            return "Product Detail"
        return "General"
    except Exception:
        return "Unknown"


def extract_product_details(product_url, driver):
    scraper = ScraperFactory.get_scraper("indiamart", driver)
    try:
        product_model = scraper.scrape(product_url)
        return product_model.model_dump()
    except Exception as e:
        print(f"Extraction failed: {e}")
        return {"name": "Extraction failed", "url": product_url}


def collect_product_urls(soup, base_url, limit=10):
    product_urls = set()
    try:
        links = soup.find_all("a", href=True)
        for link in links:
            href = link.get("href", "")
            if "/proddetail/" in href:
                full_url = urljoin(base_url, href)
                product_urls.add(full_url)
                if len(product_urls) >= limit:
                    break
    except Exception as e:
        print(f"Error collecting URLs: {e}")
    return list(product_urls)[:limit]


def create_zip_and_upload(json_files, category_name, temp_dir):
    if not json_files:
        return None, None
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    category_clean = sanitize_filename(category_name)
    zip_filename = f"indiamart_{category_clean}_{timestamp}.zip"
    zip_filepath = os.path.join(temp_dir, zip_filename)
    try:
        with zipfile.ZipFile(zip_filepath, "w", zipfile.ZIP_DEFLATED) as zipf:
            for json_file in json_files:
                if json_file and os.path.exists(json_file):
                    arcname = os.path.basename(json_file)
                    zipf.write(json_file, arcname)

        gdrive_file_id = None
        if GDRIVE_AVAILABLE:
            try:
                service = authenticate_gdrive()
                if service:
                    folder_id = find_or_create_folder(service, "scraped_files")
                    gdrive_file_id = upload_file_to_gdrive(service, zip_filepath, folder_id)
                    if gdrive_file_id:
                        print(f"Uploaded to Google Drive: {zip_filename}")
            except Exception as e:
                print(f"Google Drive upload error: {e}")

        if gdrive_file_id:
            cleanup_local_files(json_files, zip_filepath, temp_dir)
            return None, gdrive_file_id

        return zip_filepath, None

    except Exception as e:
        print(f"ZIP creation failed: {e}")
        return None, None


def scrape_category_and_products(category_url, products_per_category=10, headless=True):
    scraped_data = []
    saved_json_files = []
    driver = None
    temp_dir = tempfile.mkdtemp(prefix="procurement_scrape_")

    try:
        print(f"Starting scrape: {category_url}")
        driver = init_driver(headless=headless)

        driver.get(category_url)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(3)

        soup = BeautifulSoup(driver.page_source, "html.parser")
        product_urls = collect_product_urls(soup, category_url, products_per_category)

        if not product_urls:
            print("No product URLs found on this page.")
            return scraped_data, None, None

        print(f"Found {len(product_urls)} product URLs")

        for idx, product_url in enumerate(product_urls, 1):
            print(f"[{idx}/{len(product_urls)}] Scraping: {product_url[-50:]}")
            try:
                driver.get(product_url)
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                time.sleep(random.uniform(2, 4))

                product_data = extract_product_details(product_url, driver)

                # The name key might be 'name' or 'product_name' depending on fallback
                name_val = product_data.get("name", product_data.get("product_name", ""))
                if name_val not in ["Product name not found", "Extraction failed", ""]:
                    json_filepath = save_product_as_json(product_data, temp_dir)
                    if json_filepath:
                        saved_json_files.append(json_filepath)
                        scraped_data.append(product_data)
                        print(f"  Saved: {name_val[:50]}")
                    else:
                        print("  Skipped (duplicate)")
                else:
                    print("  Failed: could not extract product name")
            except Exception as e:
                print(f"  Error processing {product_url[-30:]}: {e}")

            time.sleep(random.uniform(1, 3))

        category_name = extract_category_from_url(category_url)
        zip_filepath, gdrive_id = create_zip_and_upload(saved_json_files, category_name, temp_dir)

        return scraped_data, zip_filepath, gdrive_id

    except Exception as e:
        print(f"Critical error: {e}")
        return scraped_data, None, None
    finally:
        if driver:
            driver.quit()
        try:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
        except Exception:
            pass


if __name__ == "__main__":
    result, zip_path, gdrive_id = scrape_category_and_products(
        "https://www.indiamart.com/impcat/stainless-steel-elbow.html",
        products_per_category=2,
    )
    print(f"Scraped {len(result)} products")
    if gdrive_id:
        print(f"Uploaded to Google Drive: {gdrive_id}")
    elif zip_path:
        print(f"Saved locally: {zip_path}")