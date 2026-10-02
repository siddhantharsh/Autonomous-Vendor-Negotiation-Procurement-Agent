import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from datetime import datetime
from typing import List, Dict

class EmailClient:
    def __init__(self, smtp_server=None, smtp_port=None, imap_server=None, imap_port=None, username=None, password=None):
        self.smtp_server = smtp_server or os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = smtp_port or int(os.getenv("SMTP_PORT", 587))
        self.imap_server = imap_server or os.getenv("IMAP_SERVER", "imap.gmail.com")
        self.imap_port = imap_port or int(os.getenv("IMAP_PORT", 993))
        self.username = username or os.getenv("EMAIL_USERNAME")
        self.password = password or os.getenv("EMAIL_PASSWORD")

    def send_rfq(self, to_email: str, product_name: str, quantity: int, target_price: str, agent_name: str = "Procurement Agent"):
        """Sends a Request for Quotation (RFQ) to a supplier."""
        if not self.username or not self.password:
            raise ValueError("Email credentials not configured. Please set EMAIL_USERNAME and EMAIL_PASSWORD.")

        subject = f"Request for Quotation: {product_name}"
        body = f"""Hello,

We are looking to procure {quantity} units of {product_name}.
We are currently targeting a price around {target_price}. 
Can you please confirm if you can fulfill this order and provide your best quote?

Thank you,
{agent_name}
"""
        msg = MIMEMultipart()
        msg['From'] = self.username
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            server.starttls()
            server.login(self.username, self.password)
            server.send_message(msg)
        return True

    def send_message(self, to_email: str, subject: str, body: str):
        """Sends a generic message (e.g., a reply or counter-offer)."""
        if not self.username or not self.password:
            raise ValueError("Email credentials not configured.")
            
        msg = MIMEMultipart()
        msg['From'] = self.username
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            server.starttls()
            server.login(self.username, self.password)
            server.send_message(msg)
        return True

    def check_inbox(self) -> List[Dict[str, str]]:
        """Checks the inbox for unread messages and returns them."""
        if not self.username or not self.password:
            raise ValueError("Email credentials not configured.")

        mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
        mail.login(self.username, self.password)
        mail.select('inbox')

        status, messages = mail.search(None, 'UNSEEN')
        inbound_messages = []

        if status == 'OK' and messages[0]:
            for num in messages[0].split():
                typ, data = mail.fetch(num, '(RFC822)')
                for response_part in data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        sender = msg.get('from', '')
                        subject = msg.get('subject', '')
                        body = ""
                        
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    try:
                                        body = part.get_payload(decode=True).decode()
                                    except Exception:
                                        body = str(part.get_payload())
                                    break
                        else:
                            try:
                                body = msg.get_payload(decode=True).decode()
                            except Exception:
                                body = str(msg.get_payload())
                                
                        inbound_messages.append({
                            "sender": sender,
                            "subject": subject,
                            "body": body.strip(),
                            "timestamp": datetime.now().isoformat()
                        })
        mail.close()
        mail.logout()
        return inbound_messages
