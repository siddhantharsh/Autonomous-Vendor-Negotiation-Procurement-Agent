import os
import sys

# Ensure we're in the right directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scraper import scrape_category_and_products

def run_real_test():
    print("--- STARTING REAL SITE SCRAPING TEST ---")
    test_url = "https://dir.indiamart.com/impcat/pipe-fittings.html"
    
    print(f"Scraping 2 products from {test_url}...")
    try:
        scraped_data, zip_path, gdrive_id = scrape_category_and_products(
            test_url,
            products_per_category=2,
            headless=True
        )
        
        print(f"\nScrape finished. Found {len(scraped_data)} products.")
        if len(scraped_data) > 0:
            for prod in scraped_data:
                print(f" - Product: {prod.get('name', 'N/A')}")
                print(f"   Supplier: {prod.get('supplier', {}).get('name', 'N/A')}")
                print(f"   Price: {prod.get('price', 'N/A')} {prod.get('price_unit', '')}")
                print(f"   URL: {prod.get('url', 'N/A')}")
        else:
            print("WARNING: No products found, might be blocked or selector changed.")
            
        if not zip_path or not os.path.exists(zip_path):
            print("ERROR: ZIP file was not created!")
            return
        print(f"\nSUCCESS: Data successfully packaged into {zip_path}")
        print("\n--- REAL SITE SCRAPING TEST SUCCESSFUL ---")
        
    except Exception as e:
        print(f"\n--- REAL SITE TEST FAILED: {e} ---")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_real_test()
