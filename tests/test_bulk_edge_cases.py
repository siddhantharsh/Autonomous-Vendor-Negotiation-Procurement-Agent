import sys
from unittest.mock import MagicMock, patch
# Mock Heavy Libraries for Phase 1
sys.modules['chromadb'] = MagicMock()
sys.modules['chromadb.utils'] = MagicMock()
sys.modules['chromadb.utils.embedding_functions'] = MagicMock()

import pytest
import os
from pydantic import ValidationError
from email.message import Message
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from models import Product, Supplier
from scrapers.factory import ScraperFactory
from scrapers.indiamart import IndiaMartScraper
from communications.email_client import EmailClient

# ==========================================
# PHASE 1 EDGE CASES
# ==========================================

def test_pydantic_edge_cases_unicode():
    """Test schemas handle emojis and unicode seamlessly."""
    supplier = Supplier(name="Supplier 🚀", location="Mumbai 📍")
    assert supplier.name == "Supplier 🚀"
    
    prod = Product(name="Pipe 🔧", supplier=supplier)
    assert prod.name == "Pipe 🔧"

def test_pydantic_extra_fields():
    """Test raw_data captures extra fields implicitly."""
    supplier = Supplier(name="Test")
    prod = Product(name="Test Pipe", supplier=supplier, raw_data={"hidden_sku": "12345"})
    assert prod.raw_data.get("hidden_sku") == "12345"

def test_scraper_factory_case_insensitive():
    """Test factory handles strange casing."""
    scraper1 = ScraperFactory.get_scraper("inDIAMarT", driver=MagicMock())
    assert isinstance(scraper1, IndiaMartScraper)

def test_deep_contact_extraction_no_links():
    """Test extraction when there are no links."""
    mock_driver = MagicMock()
    mock_driver.find_elements.return_value = []
    scraper = IndiaMartScraper(mock_driver)
    url, email = scraper.attempt_deep_contact_extraction("http://test.com")
    assert url is None
    assert email is None

@patch("requests.get")
def test_deep_contact_extraction_regex_filters(mock_get):
    """Test regex ignores false positives like images or w3 URLs."""
    mock_driver = MagicMock()
    mock_link = MagicMock()
    mock_link.get_attribute.return_value = "http://external.com"
    mock_driver.find_elements.return_value = [mock_link]
    
    mock_resp = MagicMock()
    mock_resp.text = "<html><body>logo.png@2x some.name@w3.org real.contact@vendor.in</body></html>"
    mock_get.return_value = mock_resp
    
    scraper = IndiaMartScraper(mock_driver)
    url, email = scraper.attempt_deep_contact_extraction("http://test.com")
    
    assert url == "http://external.com"
    assert email == "real.contact@vendor.in"

# ==========================================
# PHASE 2 EDGE CASES
# ==========================================

def test_email_client_missing_creds():
    """Email client should raise ValueError if no credentials exist."""
    with patch.dict(os.environ, {}, clear=True):
        client = EmailClient(username=None, password=None)
        with pytest.raises(ValueError, match="credentials not configured"):
            client.send_rfq("test@test.com", "Pipe", 10, "$10")
        with pytest.raises(ValueError, match="credentials not configured"):
            client.check_inbox()

@patch.dict(os.environ, {"EMAIL_USERNAME": "test@test.com", "EMAIL_PASSWORD": "123"})
@patch("smtplib.SMTP")
def test_send_rfq_special_chars(mock_smtp):
    """Test sending an RFQ with special unicode characters and large numbers."""
    mock_server = MagicMock()
    mock_smtp.return_value.__enter__.return_value = mock_server
    client = EmailClient()
    
    client.send_rfq("vendor@v.com", "Super 🚀 Pipe Ø 50mm", 1000000, "₹ 50,000.00")
    
    sent_msg = mock_server.send_message.call_args[0][0]
    body = sent_msg.get_payload()[0].get_payload(decode=True).decode("utf-8")
    assert "Super 🚀 Pipe Ø 50mm" in body
    assert "1000000 units" in body
    assert "₹ 50,000.00" in body

@patch.dict(os.environ, {"EMAIL_USERNAME": "test@test.com", "EMAIL_PASSWORD": "123"})
@patch("imaplib.IMAP4_SSL")
def test_check_inbox_no_messages(mock_imap):
    """Test inbox check when search returns empty."""
    mock_server = MagicMock()
    mock_imap.return_value = mock_server
    mock_server.search.return_value = ('OK', [b''])
    
    client = EmailClient()
    messages = client.check_inbox()
    assert len(messages) == 0

@patch.dict(os.environ, {"EMAIL_USERNAME": "test@test.com", "EMAIL_PASSWORD": "123"})
@patch("imaplib.IMAP4_SSL")
def test_check_inbox_html_only(mock_imap):
    """Test inbox parsing when email is HTML only (no plaintext part)."""
    mock_server = MagicMock()
    mock_imap.return_value = mock_server
    mock_server.search.return_value = ('OK', [b'1'])
    
    msg = Message()
    msg['From'] = "vendor@v.com"
    msg['Subject'] = "HTML Quote"
    msg.set_payload("<html><body>Quote is $50</body></html>")
    
    mock_server.fetch.return_value = ('OK', [(b'1 (RFC822)', msg.as_bytes())])
    
    client = EmailClient()
    messages = client.check_inbox()
    assert len(messages) == 1
    assert "Quote is $50" in messages[0]["body"]

@patch.dict(os.environ, {"EMAIL_USERNAME": "test@test.com", "EMAIL_PASSWORD": "123"})
@patch("imaplib.IMAP4_SSL")
def test_check_inbox_multipart_complex(mock_imap):
    """Test inbox parsing with complex multipart (HTML + Text + Attachment)."""
    mock_server = MagicMock()
    mock_imap.return_value = mock_server
    mock_server.search.return_value = ('OK', [b'1'])
    
    msg = MIMEMultipart()
    msg['From'] = '"Vendor Bob" <bob@v.com>'
    msg['Subject'] = "Complex Quote"
    msg.attach(MIMEText("<html><body>Ignore HTML</body></html>", 'html'))
    msg.attach(MIMEText("This is the plain text quote.", 'plain'))
    
    mock_server.fetch.return_value = ('OK', [(b'1 (RFC822)', msg.as_bytes())])
    
    client = EmailClient()
    messages = client.check_inbox()
    
    assert len(messages) == 1
    assert messages[0]["sender"] == '"Vendor Bob" <bob@v.com>'
    assert messages[0]["body"] == "This is the plain text quote."

# ==========================================
# COMBINED PHASE 1 & 2 WORKFLOW
# ==========================================

@patch("requests.get")
@patch("smtplib.SMTP")
@patch.dict(os.environ, {"EMAIL_USERNAME": "agent@test.com", "EMAIL_PASSWORD": "123"})
def test_combined_workflow(mock_smtp, mock_get):
    """
    Test End-to-End: 
    1. Scrape vendor
    2. Extract email from external site
    3. Generate product Pydantic model
    4. Send RFQ to extracted email
    """
    # 1. Mock the scrape to find a website link
    mock_driver = MagicMock()
    mock_link = MagicMock()
    mock_link.get_attribute.return_value = "http://vendor.com"
    mock_driver.find_elements.return_value = [mock_link]
    
    # 2. Mock external site responding with an email
    mock_resp = MagicMock()
    mock_resp.text = "Contact: sales@vendor.com"
    mock_get.return_value = mock_resp
    
    # Run the scraper
    scraper = IndiaMartScraper(mock_driver)
    scraper.safe_element_text = MagicMock(return_value="Valid Data")
    
    product = scraper.scrape("http://indiamart.com/product")
    
    # Verify Phase 1 worked
    assert product.supplier.email == "sales@vendor.com"
    assert product.name == "Valid Data"
    
    # 3. Use Phase 2 client to send RFQ
    mock_smtp_server = MagicMock()
    mock_smtp.return_value.__enter__.return_value = mock_smtp_server
    
    client = EmailClient()
    client.send_rfq(
        to_email=product.supplier.email,
        product_name=product.name,
        quantity=500,
        target_price="Rs 200"
    )
    
    # Verify Phase 2 worked based on Phase 1 data
    sent_msg = mock_smtp_server.send_message.call_args[0][0]
    assert sent_msg['To'] == "sales@vendor.com"
    assert sent_msg['Subject'] == "Request for Quotation: Valid Data"
