from abc import ABC, abstractmethod
from typing import List
from models import Product

class BaseScraper(ABC):
    def __init__(self):
        self.platform_name = "Unknown"

    @abstractmethod
    def scrape(self, query_or_url: str) -> List[Product]:
        """
        Scrape a given URL or query and return a list of Product models.
        """
        pass
