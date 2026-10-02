import pytest
from unittest.mock import patch, MagicMock
from communications.email_client import EmailClient
import os

@patch.dict(os.environ, {"EMAIL_USERNAME": "agent@test.com", "EMAIL_PASSWORD": "password123"})
@patch("smtplib.SMTP")
def test_send_rfq(mock_smtp):
    mock_server = MagicMock()
    mock_smtp.return_value.__enter__.return_value = mock_server

    client = EmailClient()
    result = client.send_rfq(
        to_email="vendor@example.com",
        product_name="Steel Pipe",
        quantity=100,
        target_price="₹ 50,000"
    )
    
    assert result is True
    mock_server.starttls.assert_called_once()
    mock_server.login.assert_called_once_with("agent@test.com", "password123")
    mock_server.send_message.assert_called_once()
    
    # Check the actual message generated
    sent_msg = mock_server.send_message.call_args[0][0]
    assert sent_msg['To'] == "vendor@example.com"
    assert sent_msg['Subject'] == "Request for Quotation: Steel Pipe"

@patch.dict(os.environ, {"EMAIL_USERNAME": "agent@test.com", "EMAIL_PASSWORD": "password123"})
@patch("imaplib.IMAP4_SSL")
def test_check_inbox(mock_imap):
    mock_server = MagicMock()
    mock_imap.return_value = mock_server
    
    # Mock search to return one unread email
    mock_server.search.return_value = ('OK', [b'1'])
    
    # Create a mock email bytes response
    mock_email_bytes = b"From: vendor@example.com\r\nSubject: Re: Request for Quotation: Steel Pipe\r\n\r\nWe can do Rs 45,000."
    mock_server.fetch.return_value = ('OK', [(b'1 (RFC822)', mock_email_bytes)])
    
    client = EmailClient()
    messages = client.check_inbox()
    
    assert len(messages) == 1
    assert messages[0]["sender"] == "vendor@example.com"
    assert messages[0]["subject"] == "Re: Request for Quotation: Steel Pipe"
    assert "We can do Rs 45,000." in messages[0]["body"]
    
    mock_server.login.assert_called_once_with("agent@test.com", "password123")
    mock_server.select.assert_called_once_with('inbox')
