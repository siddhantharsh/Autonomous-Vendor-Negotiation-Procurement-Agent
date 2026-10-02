import sys
from unittest.mock import MagicMock, patch
sys.modules['chromadb'] = MagicMock()
sys.modules['chromadb.utils'] = MagicMock()
sys.modules['chromadb.utils.embedding_functions'] = MagicMock()

import pytest

from models import Product, Supplier
from scrapers.factory import ScraperFactory
from scrapers.indiamart import IndiaMartScraper
from pydantic import ValidationError
import rag_system

def test_supplier_schema_defaults():
    supplier = Supplier(name="Test Corp")
    assert supplier.location == "Unknown"
    assert supplier.trust_score == "Unverified"
    assert supplier.email is None

def test_product_schema_validation():
    supplier = Supplier(name="Test Corp")
    product = Product(
        name="Steel Pipe",
        category="Pipes",
        supplier=supplier
    )
    assert product.source_platform == "IndiaMART"
    assert product.price == "Price not found"
    
    # Missing required field 'name' should raise ValidationError
    with pytest.raises(ValidationError):
        Product(category="Pipes", supplier=supplier)

def test_scraper_factory():
    # Valid scraper
    scraper = ScraperFactory.get_scraper("indiamart", driver=MagicMock())
    assert isinstance(scraper, IndiaMartScraper)
    
    # Invalid scraper
    with pytest.raises(ValueError, match="No scraper found for platform"):
        ScraperFactory.get_scraper("alibaba", driver=MagicMock())

@patch("requests.get")
def test_deep_contact_extraction(mock_get):
    # Mocking driver
    mock_driver = MagicMock()
    mock_link = MagicMock()
    mock_link.get_attribute.return_value = "http://external-supplier.com"
    mock_driver.find_elements.return_value = [mock_link]
    
    # Mocking requests.get response
    mock_resp = MagicMock()
    mock_resp.text = "<html><body>Contact us at sales@external-supplier.com or info@external-supplier.com</body></html>"
    mock_get.return_value = mock_resp
    
    scraper = IndiaMartScraper(driver=mock_driver)
    url, email = scraper.attempt_deep_contact_extraction("http://indiamart.com/fake-profile")
    
    assert url == "http://external-supplier.com"
    assert email == "sales@external-supplier.com"

def test_rag_system_build_product_text_new_schema():
    # Simulate a product dumped from the new Pydantic schema
    product_dict = {
        "source_platform": "IndiaMART",
        "name": "Heavy Duty Steel Pipe",
        "price": "₹ 500 Per Unit",
        "category": "Pipes",
        "specifications": {"Material": "Steel", "Grade": "304"},
        "supplier": {
            "name": "Global Pipes Ltd",
            "location": "Mumbai",
            "rating": "4.5 (10 reviews)",
            "trust_score": "TrustSEAL",
            "email": "contact@globalpipes.com"
        }
    }
    
    text = rag_system.build_product_text(product_dict)
    
    # Check if critical components are present
    assert "Heavy Duty Steel Pipe" in text
    assert "₹ 500 Per Unit" in text
    assert "Global Pipes Ltd" in text
    assert "Mumbai" in text
    assert "TrustSEAL" in text
    assert "contact@globalpipes.com" in text
    assert "Material: Steel" in text
