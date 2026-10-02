import sys
from unittest.mock import MagicMock, patch
# Mock Heavy Libraries for Phase 1
sys.modules['chromadb'] = MagicMock()
sys.modules['chromadb.utils'] = MagicMock()
sys.modules['chromadb.utils.embedding_functions'] = MagicMock()

import pytest
import os
import json

from models import Product, Supplier
from database.db_manager import NegotiationDB
from agent.negotiator import ProcurementAgent

# ==========================================
# PHASE 3 EDGE CASES (DATABASE)
# ==========================================

@pytest.fixture
def db():
    db_path = "test_bulk_phase3.db"
    db_instance = NegotiationDB(db_path=db_path)
    yield db_instance
    if os.path.exists(db_path):
        os.remove(db_path)

def test_db_sql_injection_protection(db):
    """Test that the DB protects against SQL injection in strings."""
    malicious_email = "test@v.com'; DROP TABLE negotiations;--"
    db.create_negotiation(malicious_email, "Pipe", "Rs 100", "Hi")
    
    # Should still be able to retrieve safely
    neg = db.get_negotiation_by_email(malicious_email)
    assert neg is not None
    assert neg["vendor_email"] == malicious_email

def test_db_update_non_existent(db):
    """Test updating a negotiation that doesn't exist."""
    success = db.update_negotiation(9999, "NEGOTIATING", "100", "msg")
    assert success is False

def test_db_duplicate_active_negotiations(db):
    """Ensure get_negotiation_by_email gets the latest ACTIVE one."""
    db.create_negotiation("dup@v.com", "Pipe1", "10", "msg1")
    db.create_negotiation("dup@v.com", "Pipe2", "20", "msg2")
    
    neg = db.get_negotiation_by_email("dup@v.com")
    # Should return the most recently inserted
    assert neg["product_name"] == "Pipe2"

# ==========================================
# PHASE 3 EDGE CASES (AGENT ORCHESTRATION)
# ==========================================

@patch("rag_system.query_products")
def test_agent_start_neg_no_vendors(mock_query, db):
    """Test agent handles zero search results gracefully."""
    agent = ProcurementAgent()
    agent.db = db
    mock_query.return_value = {"results": []}
    
    result = agent.start_negotiation("Spaceships", "Rs 100")
    assert "No vendors found" in result

@patch("rag_system.query_products")
@patch("communications.email_client.EmailClient.send_rfq")
def test_agent_start_neg_partial_failure(mock_send, mock_query, db):
    """Test agent continues if sending to one vendor fails."""
    agent = ProcurementAgent()
    agent.db = db
    
    # RAG returns 2 vendors
    mock_query.return_value = {
        "results": [
            {"metadata": {"email": "fail@v.com", "product_name": "P1"}},
            {"metadata": {"email": "success@v.com", "product_name": "P2"}}
        ]
    }
    
    # Make send_rfq fail on the first call, succeed on the second
    mock_send.side_effect = [Exception("Network error"), True]
    
    result = agent.start_negotiation("Pipes", "Rs 100")
    
    # Only 1 vendor should be successfully initiated
    assert "Initiated negotiations with 1 vendors" in result
    assert db.get_negotiation_by_email("success@v.com") is not None
    assert db.get_negotiation_by_email("fail@v.com") is None

@patch("communications.email_client.EmailClient.check_inbox")
def test_agent_process_inbox_unknown_sender(mock_inbox, db):
    """Test inbox processing ignores emails from unknown senders."""
    agent = ProcurementAgent()
    agent.db = db
    
    mock_inbox.return_value = [
        {"sender": "spam@spam.com", "body": "Buy our stuff", "subject": "Spam"}
    ]
    
    result = agent.process_inbox()
    assert "Processed 0 replies" in result

@patch("communications.email_client.EmailClient.check_inbox")
@patch("agent.negotiator.ProcurementAgent._evaluate_with_llm")
def test_agent_process_inbox_complex_sender(mock_llm, mock_inbox, db):
    """Test agent correctly extracts email from complex sender strings."""
    agent = ProcurementAgent()
    agent.db = db
    
    # Create DB entry for raw email
    db.create_negotiation("real@vendor.com", "Pipe", "Rs 10", "Hi")
    
    # Incoming email has complex sender format
    mock_inbox.return_value = [
        {"sender": '"Real Vendor" <real@vendor.com>', "body": "Ok", "subject": "Re:"}
    ]
    
    mock_llm.return_value = {"action": "ACCEPTED", "reply": "Ok", "current_offer": "Rs 10"}
    
    result = agent.process_inbox()
    assert "Processed 1 replies" in result

@patch("rag_system.ollama_available")
@patch("rag_system.query_ollama")
def test_agent_llm_malformed_json(mock_query, mock_avail, db):
    """Test agent handles bad JSON from LLM gracefully."""
    agent = ProcurementAgent()
    mock_avail.return_value = True
    
    # Mock LLM returning broken JSON text with extra chatter
    mock_query.return_value = "Sure, here is your action: { \"action\": \"REJECTED\", \"reply\": \"No thanks\" "
    
    neg = {"target_price": "100", "history": []}
    response = agent._evaluate_with_llm(neg, "Price is 1000")
    
    # Should fallback gracefully since parsing fails
    assert response["action"] == "NEGOTIATING"
    assert "current_offer" in response

# ==========================================
# FULL INTEGRATION (PHASES 1, 2, AND 3)
# ==========================================

@patch("requests.get")
@patch("smtplib.SMTP")
@patch("imaplib.IMAP4_SSL")
@patch("rag_system.query_products")
@patch("rag_system.query_ollama")
@patch("rag_system.ollama_available")
@patch.dict(os.environ, {"EMAIL_USERNAME": "agent@v.com", "EMAIL_PASSWORD": "123"})
def test_full_pipeline_end_to_end(mock_avail, mock_ollama, mock_rag, mock_imap, mock_smtp, mock_get, db):
    """
    Simulates the entire system lifecycle:
    1. Agent searches RAG (Phase 1).
    2. Agent sends outbound email via EmailClient (Phase 2).
    3. DB records the state (Phase 3).
    4. Vendor replies, EmailClient fetches it (Phase 2).
    5. Agent parses reply, LLM evaluates (Phase 3).
    6. Agent sends counter-offer (Phase 2).
    7. DB state is updated (Phase 3).
    """
    agent = ProcurementAgent()
    agent.db = db
    
    # STEP 1: RAG Search returns a scraped vendor
    mock_rag.return_value = {
        "results": [
            {"metadata": {"email": "vendor@indiamart.com", "product_name": "Industrial Valve"}}
        ]
    }
    
    # Mock SMTP setup
    mock_smtp_server = MagicMock()
    mock_smtp.return_value.__enter__.return_value = mock_smtp_server
    
    mock_avail.return_value = True
    
    # TRIGGER 1: User says "Start negotiating"
    result1 = agent.start_negotiation("Industrial Valve", "Rs 500")
    assert "Initiated negotiations with 1 vendors" in result1
    
    # Verify DB State
    neg = db.get_negotiation_by_email("vendor@indiamart.com")
    assert neg["status"] == "AWAITING_REPLY"
    
    # STEP 2: Vendor replies
    mock_imap_server = MagicMock()
    mock_imap.return_value = mock_imap_server
    mock_imap_server.search.return_value = ('OK', [b'1'])
    
    import email
    from email.message import Message
    msg = Message()
    msg['From'] = "vendor@indiamart.com"
    msg['Subject'] = "Re: Quotation"
    msg.set_payload("Our best price is Rs 600.")
    mock_imap_server.fetch.return_value = ('OK', [(b'1 (RFC822)', msg.as_bytes())])
    
    # STEP 3: LLM evaluates reply
    # LLM decides to counter-offer
    mock_ollama.return_value = '{"action": "NEGOTIATING", "reply": "Can you do Rs 550?", "current_offer": "Rs 600"}'
    
    # TRIGGER 2: Agent checks inbox
    result2 = agent.process_inbox()
    assert "Processed 1 replies" in result2
    
    # Verify DB State updated
    neg_updated = db.get_negotiation_by_email("vendor@indiamart.com")
    assert neg_updated["status"] == "NEGOTIATING"
    assert neg_updated["current_offer"] == "Rs 600"
    assert len(neg_updated["history"]) == 3 # Initial Request -> Vendor Reply -> Counter Offer
    
    # Verify Outbound Counter-Offer Sent
    assert mock_smtp_server.send_message.call_count == 2 # 1 RFQ + 1 Counter Offer
    last_sent_msg = mock_smtp_server.send_message.call_args[0][0]
    assert last_sent_msg['To'] == "vendor@indiamart.com"
    assert "Can you do Rs 550?" in last_sent_msg.get_payload()[0].get_payload(decode=True).decode("utf-8")
