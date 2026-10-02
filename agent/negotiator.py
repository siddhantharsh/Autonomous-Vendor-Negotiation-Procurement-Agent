from database.db_manager import NegotiationDB
from communications.email_client import EmailClient
import rag_system
from agent.prompts import get_negotiator_prompt
import json
import re

MAX_ROUNDS = 5

class ProcurementAgent:
    def __init__(self):
        self.db = NegotiationDB()
        self.email_client = EmailClient()

    def start_negotiation(self, query_text: str, target_price: str):
        """Finds top vendors via RAG and sends them an RFQ."""
        results = rag_system.query_products(query_text, n_results=3)
        if not results.get("results"):
            return "No vendors found for that query."

        initiated_count = 0
        for r in results["results"]:
            meta = r["metadata"]
            email = meta.get("email")
            product_name = meta.get("product_name")

            if not email or email == "Not found":
                continue

            # Check if negotiation already exists
            if self.db.get_negotiation_by_email(email):
                continue
            
            try:
                self.email_client.send_rfq(
                    to_email=email,
                    product_name=product_name,
                    quantity=100, 
                    target_price=target_price
                )
                
                initial_msg = f"Request for Quotation: {product_name} at {target_price}"
                self.db.create_negotiation(email, product_name, target_price, initial_msg)
                initiated_count += 1
            except Exception as e:
                print(f"Failed to start negotiation with {email}: {e}")

        return f"Initiated negotiations with {initiated_count} vendors."

    def process_inbox(self):
        """Reads incoming emails and formulates strategic replies."""
        try:
            messages = self.email_client.check_inbox()
        except Exception as e:
            return f"Error checking inbox: {e}"
            
        processed_count = 0
        for msg in messages:
            sender = msg["sender"]
            # Extract just the email if format is "Name <email@dom.com>"
            email_matches = re.findall(r'<([^>]+)>', sender)
            sender_email = email_matches[-1] if email_matches else sender.strip()
            
            neg = self.db.get_negotiation_by_email(sender_email)
            if not neg:
                continue # Unknown sender or not an active negotiation
                
            body = msg["body"]
            # Enforce max rounds
            if len(neg["history"]) >= MAX_ROUNDS:
                action = "REJECTED"
                counter_price = neg["current_offer"]
                reply_text = "We have reached our maximum negotiation rounds without an agreement. We will pass on this offer. Thank you."
                self.db.update_negotiation(neg["id"], "REJECTED", counter_price, body, role="user")
                
                try:
                    subject = f"Re: Request for Quotation: {neg['product_name']}"
                    self.email_client.send_message(
                        to_email=sender_email, 
                        subject=subject,
                        body=reply_text
                    )
                    self.db.update_negotiation(neg["id"], "REJECTED", counter_price, reply_text, role="assistant")
                except Exception:
                    pass
                processed_count += 1
                continue
                
            llm_response = self._evaluate_with_llm(neg, body)
            
            action = llm_response.get("action", "NEGOTIATING")
            counter_price = llm_response.get("current_offer", neg["current_offer"])
            reply_text = llm_response.get("reply", "Thank you for the update.")
            
            # Update DB with vendor's message
            self.db.update_negotiation(neg["id"], "NEGOTIATING", counter_price, body, role="user")
            
            if action in ["NEGOTIATING", "REJECTED"]:
                try:
                    subject = f"Re: Request for Quotation: {neg['product_name']}"
                    self.email_client.send_message(
                        to_email=sender_email, 
                        subject=subject,
                        body=reply_text
                    )
                    self.db.update_negotiation(neg["id"], action, counter_price, reply_text, role="assistant")
                except Exception as e:
                    print(f"Failed to send reply to {sender_email}: {e}")
            elif action == "ACCEPTED":
                self.db.update_negotiation(neg["id"], "ACCEPTED", counter_price, "Offer Accepted! Awaiting final approval.", role="assistant")
                
            processed_count += 1
            
        return f"Processed {processed_count} replies."
        
    def _evaluate_with_llm(self, negotiation, new_message):
        """Prompts the LLM with negotiation state to formulate a response."""
        prompt = get_negotiator_prompt(
            target_price=negotiation['target_price'],
            history=json.dumps(negotiation['history']),
            vendor_message=new_message
        )
        
        if rag_system.ollama_available():
            raw_response = rag_system.query_ollama(prompt)
            try:
                start = raw_response.find("{")
                end = raw_response.rfind("}") + 1
                return json.loads(raw_response[start:end])
            except Exception:
                return {"action": "NEGOTIATING", "reply": "Can we negotiate further on the price?", "current_offer": "Unknown"}
        else:
            return {"action": "NEGOTIATING", "reply": "Can you do any better on the price?", "current_offer": "Unknown"}
