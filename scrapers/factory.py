from .indiamart import IndiaMartScraper

class ScraperFactory:
    @staticmethod
    def get_scraper(platform: str, driver=None):
        if platform.lower() == "indiamart":
            return IndiaMartScraper(driver)
        # We can add TradeIndiaScraper here later
        raise ValueError(f"No scraper found for platform: {platform}")
