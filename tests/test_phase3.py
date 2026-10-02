import sys
from unittest.mock import MagicMock, patch
# Mock Heavy Libraries
sys.modules['chromadb'] = MagicMock()
sys.modules['chromadb.utils'] = MagicMock()
sys.modules['chromadb.utils.embedding_functions'] = MagicMock()

import pytest
import os
import json

from database.db_manager import NegotiationDB
from agent.negotiator import ProcurementAgent

# ==========================================
# PHASE 3 TESTS
# ==========================================

@pytest.fixture
def temp_db():
    db_path = "test_negotiations.db"
    db = NegotiationDB(db_path=db_path)
    yield db
    if os.path.exists(db_path):
        os.remove(db_path)

def test_db_manager_creation(temp_db):
    neg_id = temp_db.create_negotiation("vendor@v.com", "Pipe", "Rs 100", "Initial request")
    assert neg_id == 1
    
    neg = temp_db.get_negotiation_by_email("vendor@v.com")
    assert neg["vendor_email"] == "vendor@v.com"
    assert neg["product_name"] == "Pipe"
    assert neg["status"] == "AWAITING_REPLY"
    assert len(neg["history"]) == 1

def test_db_manager_update(temp_db):
    temp_db.create_negotiation("vendor@v.com", "Pipe", "Rs 100", "Initial request")
    neg = temp_db.get_negotiation_by_email("vendor@v.com")
    
    success = temp_db.update_negotiation(neg["id"], "NEGOTIATING", "Rs 120", "We can do 120", role="user")
    assert success is True
    
    updated_neg = temp_db.get_negotiation_by_email("vendor@v.com")
    assert updated_neg["status"] == "NEGOTIATING"
    assert updated_neg["current_offer"] == "Rs 120"
    assert len(updated_neg["history"]) == 2
    assert updated_neg["history"][1]["role"] == "user"

@patch("rag_system.query_products")
@patch("communications.email_client.EmailClient.send_rfq")
def test_agent_start_negotiation(mock_send, mock_query, temp_db):
    agent = ProcurementAgent()
    agent.db = temp_db # override db
    
    # Mock RAG returning one valid supplier
    mock_query.return_value = {
        "results": [
            {"metadata": {"email": "vendor1@v.com", "product_name": "Steel Pipe"}}
        ]
    }
    
    result = agent.start_negotiation("Steel pipes", "Rs 500")
    assert "Initiated negotiations with 1 vendors" in result
    
    mock_send.assert_called_once()
    
    neg = temp_db.get_negotiation_by_email("vendor1@v.com")
    assert neg is not None
    assert neg["product_name"] == "Steel Pipe"

@patch("communications.email_client.EmailClient.check_inbox")
@patch("agent.negotiator.ProcurementAgent._evaluate_with_llm")
def test_agent_process_inbox(mock_llm, mock_inbox, temp_db):
    agent = ProcurementAgent()
    agent.db = temp_db
    
    # Setup active negotiation
    temp_db.create_negotiation("vendor@v.com", "Steel Pipe", "Rs 500", "Initial request")
    
    # Mock incoming email
    mock_inbox.return_value = [
        {"sender": "vendor@v.com", "body": "Best price is Rs 450", "subject": "Re: Request"}
    ]
    
    # Mock LLM choosing to ACCEPT
    mock_llm.return_value = {
        "action": "ACCEPTED",
        "reply": "We accept",
        "current_offer": "Rs 450"
    }
    
    result = agent.process_inbox()
    assert "Processed 1 replies" in result
    
    # Verify DB update
    neg = temp_db._get_connection().cursor().execute("SELECT status, current_offer FROM negotiations WHERE vendor_email='vendor@v.com'").fetchone()
    assert neg[0] == "ACCEPTED"
    assert neg[1] == "Rs 450"
