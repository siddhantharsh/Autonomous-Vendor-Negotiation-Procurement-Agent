from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, Dict, Any

class Supplier(BaseModel):
    name: str = "Unknown"
    location: str = "Unknown"
    rating: str = "Not found"
    trust_score: str = "Unverified"
    external_website: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

class Product(BaseModel):
    source_platform: str = "IndiaMART"
    url: Optional[str] = None
    name: str
    price: str = "Price not found" # Keeping as string for now since scraper extracts strings like "₹ 1,500/ Piece"
    category: str = "Uncategorized"
    specifications: Dict[str, str] = Field(default_factory=dict)
    supplier: Supplier
    raw_data: Dict[str, Any] = Field(default_factory=dict) # For any extra fields
