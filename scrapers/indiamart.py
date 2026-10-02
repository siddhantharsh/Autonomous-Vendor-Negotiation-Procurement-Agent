import time
import re
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
import requests

from .base import BaseScraper
from models import Product, Supplier

class IndiaMartScraper(BaseScraper):
    def __init__(self, driver):
        super().__init__()
        self.platform_name = "IndiaMART"
        self.driver = driver

    def safe_element_text(self, by, selector):
        try:
            element = self.driver.find_element(by, selector)
            return element.text.strip()
        except Exception:
            return ""

    def extract_category_from_url(self, url):
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

    def attempt_deep_contact_extraction(self, supplier_profile_url):
        # We look for a website link in IndiaMART profile
        # For phase 1, we just mock the logic or do a fast request if we can find external link
        # Since IndiaMART often hides it or opens via JS, we'll try to find any link to external domain.
        try:
            links = self.driver.find_elements(By.TAG_NAME, "a")
            for link in links:
                href = link.get_attribute("href")
                if href and "http" in href and "indiamart.com" not in href:
                    # found external link!
                    try:
                        resp = requests.get(href, timeout=5)
                        # search for email
                        emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", resp.text)
                        # filter out false positives
                        valid_emails = [e for e in emails if not any(x in e for x in ['png', 'jpg', 'gif', 'w3.org'])]
                        if valid_emails:
                            return href, valid_emails[0]
                    except Exception:
                        pass
        except Exception:
            pass
        return None, None

    def scrape(self, url: str) -> Product:
        # Assumes driver is already at the product URL
        self.driver.get(url)
        time.sleep(2)
        
        product_name = self.safe_element_text(By.XPATH, "//h1[@class='bo center-heading centerHeadHeight ']")
        if not product_name:
            product_name = self.safe_element_text(By.XPATH, "//h1")
        if not product_name:
            product_name = "Product name not found"

        price = "Not found"
        price_unit = "N/A"
        try:
            price_element = None
            try:
                price_element = self.driver.find_element(By.XPATH, "//span[@class='bo price-unit']")
            except NoSuchElementException:
                try:
                    price_element = self.driver.find_element(By.XPATH, "//span[contains(@class, 'price')]")
                except NoSuchElementException:
                    pass

            if price_element:
                price_text = price_element.text.strip()
                price_match = re.search(r"₹\s*([\d,]+(?:\.\d+)?)", price_text)
                if price_match:
                    price = price_match.group(1).replace(",", "")
                else:
                    price = price_text
                
                try:
                    unit_element = self.driver.find_element(By.XPATH, "//span[@class='units pcl76']")
                    unit_text = unit_element.text.strip()
                    price_unit = f"Per {unit_text}" if unit_text else "Per Unit"
                except Exception:
                    price_unit = "Per Unit"
        except Exception:
            pass

        specifications = {}
        try:
            table = self.driver.find_element(By.XPATH, "//table//tbody")
            rows = table.find_elements(By.TAG_NAME, "tr")
            for row in rows:
                try:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 2:
                        key = cells[0].text.strip()
                        value = cells[1].text.strip()
                        if key and value:
                            specifications[key] = value
                except Exception:
                    continue
        except Exception:
            pass

        supplier_name = self.safe_element_text(By.XPATH, "//div[@class='pdflx1 pdBw asc']//h2[@class='fs15']")
        if not supplier_name:
            supplier_name = self.safe_element_text(By.XPATH, "//h2")
        supplier_name = supplier_name if supplier_name else "Not found"

        location = self.safe_element_text(By.XPATH, "//span[@class='city-highlight']")
        if not location:
            location = self.safe_element_text(By.XPATH, "//span[contains(@class, 'city')]")
        location = location if location else "Not found"

        trustseal = self.safe_element_text(By.XPATH, "//span[@class='lh11'][contains(text(), 'TrustSEAL')]")
        trust_score = trustseal if trustseal else "Not verified"

        try:
            rating = self.driver.find_element(By.XPATH, "//span[@class='bo color']").text.strip()
            review_count = self.driver.find_element(By.XPATH, "//span[@class='tcund']").text.strip()
            rating_str = f"{rating} ({review_count} reviews)"
        except Exception:
            rating_raw = self.safe_element_text(By.XPATH, "//span[contains(@class, 'rating')]")
            rating_str = rating_raw if rating_raw else "Not found"

        # Attempt deep contact extraction
        ext_site, email = self.attempt_deep_contact_extraction(url)

        supplier = Supplier(
            name=supplier_name,
            location=location,
            rating=rating_str,
            trust_score=trust_score,
            external_website=ext_site,
            email=email
        )

        category = self.extract_category_from_url(url)
        price_str = f"₹ {price} {price_unit}" if price != "Not found" else "Price not found"

        return Product(
            source_platform=self.platform_name,
            url=url,
            name=product_name,
            price=price_str,
            category=category,
            specifications=specifications,
            supplier=supplier,
            raw_data={"extracted_price": price, "extracted_unit": price_unit}
        )
