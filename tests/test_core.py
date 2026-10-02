import sys
from unittest.mock import MagicMock
sys.modules['chromadb'] = MagicMock()
sys.modules['chromadb.utils'] = MagicMock()
sys.modules['chromadb.utils.embedding_functions'] = MagicMock()

import pytest
import scraper
import rag_system

def test_sanitize_filename():
    assert scraper.sanitize_filename("Valid Name 123") == "Valid_Name_123"
    assert scraper.sanitize_filename("Name/with\\invalid:chars?") == "Name_with_invalid_chars"
    assert scraper.sanitize_filename("") == "unknown"

def test_generate_content_hash():
    data1 = {"a": 1, "b": 2}
    data2 = {"b": 2, "a": 1}
    # Should be the same hash due to sort_keys=True
    assert scraper.generate_content_hash(data1) == scraper.generate_content_hash(data2)

def test_extract_filters_from_query():
    # Test max price extraction
    filters1 = rag_system.extract_filters_from_query("Find products under ₹500")
    assert filters1.get("max_price") == 500

    filters2 = rag_system.extract_filters_from_query("less than 1000")
    assert filters2.get("max_price") == 1000
    
    # Test location extraction
    filters3 = rag_system.extract_filters_from_query("products from Mumbai")
    assert filters3.get("location").lower() == "mumbai"
    
    filters4 = rag_system.extract_filters_from_query("products from New Delhi")
    assert filters4.get("location").lower() == "new delhi"

    # Test case-insensitivity and ignore stopwords
    filters5 = rag_system.extract_filters_from_query("products from mumbai")
    assert filters5.get("location").lower() == "mumbai"

    filters6 = rag_system.extract_filters_from_query("products from the best supplier")
    # "the" should be ignored, it should pick "best supplier" or just "best" if it's considered location
    # Since our regex does negative lookahead for "the", it might extract "best supplier"
    # Either way, we just want to ensure it works for simple cases and ignores "the"
    assert filters6.get("location") != "the"

def test_apply_filters():
    results = [
        {"metadata": {"price": "₹ 500", "supplier_location": "Mumbai, Maharashtra"}},
        {"metadata": {"price": "₹ 1500", "supplier_location": "Delhi"}},
        {"metadata": {"price": "Not found", "supplier_location": "Chennai"}},
    ]
    
    # Filter by price
    filtered_price = rag_system.apply_filters(results, {"max_price": 1000})
    assert len(filtered_price) == 2  # 500 and Not found
    
    # Filter by location
    filtered_loc = rag_system.apply_filters(results, {"location": "Mumbai"})
    assert len(filtered_loc) == 1
    assert filtered_loc[0]["metadata"]["supplier_location"] == "Mumbai, Maharashtra"
    
    # Filter by both
    filtered_both = rag_system.apply_filters(results, {"max_price": 600, "location": "Mumbai"})
    assert len(filtered_both) == 1

def test_build_product_text():
    product = {
        "product_name": "Steel Pipe",
        "price": "500",
        "price_unit": "Piece",
        "supplier_name": "ABC Steels",
        "supplier_location": "Mumbai",
        "category": "Pipes",
        "specifications": {"Material": "Steel", "Length": "2m"},
        "supplier_rating": "4.5",
        "trustseal_verified": "Yes",
        "years_experience": "10 yrs"
    }
    
    text = rag_system.build_product_text(product)
    
    assert "Product: Steel Pipe" in text
    assert "Price: Rs 500 Piece" in text
    assert "Supplier: ABC Steels" in text
    assert "Location: Mumbai" in text
    assert "Category: Pipes" in text
    assert "Specifications: Material: Steel; Length: 2m" in text
    assert "Rating: 4.5" in text
    assert "TrustSEAL Verified" in text
    assert "Experience: 10 yrs" in text
