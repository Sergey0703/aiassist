import logging
from livekit.agents import function_tool, RunContext
import requests
from langchain_community.tools import DuckDuckGoSearchRun
import os
import smtplib
from email.mime.multipart import MIMEMultipart  
from email.mime.text import MIMEText
from typing import Optional
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('email_debug.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@function_tool()
async def get_weather(
    context: RunContext,  # type: ignore
    city: str) -> str:
    """
    Get the current weather for a given city.
    """
    try:
        response = requests.get(
            f"https://wttr.in/{city}?format=3")
        if response.status_code == 200:
            logger.info(f"Weather for {city}: {response.text.strip()}")
            return response.text.strip()   
        else:
            logger.error(f"Failed to get weather for {city}: {response.status_code}")
            return f"Could not retrieve weather for {city}."
    except Exception as e:
        logger.error(f"Error retrieving weather for {city}: {e}")
        return f"An error occurred while retrieving weather for {city}." 

@function_tool()
async def search_web(
    context: RunContext,  # type: ignore
    query: str) -> str:
    """
    Search the web using DuckDuckGo.
    """
    try:
        results = DuckDuckGoSearchRun().run(tool_input=query)
        logger.info(f"Search results for '{query}': {results}")
        return results
    except Exception as e:
        logger.error(f"Error searching the web for '{query}': {e}")
        return f"An error occurred while searching the web for '{query}'."    

@function_tool()    
async def send_email(
    context: RunContext,  # type: ignore
    to_email: str,
    subject: str,
    message: str,
    cc_email: Optional[str] = None
) -> str:
    """
    Send an email through Gmail.
    
    Args:
        to_email: Recipient email address
        subject: Email subject line
        message: Email body content
        cc_email: Optional CC email address
    """
    logger.info("="*50)
    logger.info("STARTING EMAIL SEND PROCESS")
    logger.info(f"To: {to_email}")
    logger.info(f"Subject: {subject}")
    logger.info(f"Message: {message[:100]}...")
    logger.info(f"CC: {cc_email}")
    
    try:
        # Email provider configuration
        email_provider = os.getenv("EMAIL_PROVIDER", "gmail").lower()
        
        if email_provider == "outlook":
            smtp_server = "smtp-mail.outlook.com"
            smtp_port = 587
            email_user = os.getenv("OUTLOOK_USER")
            email_password = os.getenv("OUTLOOK_PASSWORD")
        elif email_provider == "yandex":
            smtp_server = "smtp.yandex.ru"
            smtp_port = 587
            email_user = os.getenv("YANDEX_USER")
            email_password = os.getenv("YANDEX_PASSWORD")
        elif email_provider == "mail":
            smtp_server = "smtp.mail.ru"
            smtp_port = 587
            email_user = os.getenv("MAIL_USER")
            email_password = os.getenv("MAIL_PASSWORD")
        else:  # gmail
            smtp_server = "smtp.gmail.com"
            smtp_port = 587
            email_user = os.getenv("GMAIL_USER")
            email_password = os.getenv("GMAIL_APP_PASSWORD")
        
        logger.info(f"Email provider: {email_provider}")
        logger.info(f"Email user: {email_user}")
        logger.info(f"Password exists: {'Yes' if email_password else 'No'}")
        logger.info(f"Password length: {len(email_password) if email_password else 0}")
        
        if not email_user or not email_password:
            error_msg = f"Email sending failed: {email_provider.upper()} credentials not configured."
            logger.error(error_msg)
            logger.error(f"Email user env var: {email_user}")
            logger.error(f"Email password exists: {bool(email_password)}")
            return error_msg
        
        # Validate email addresses
        if "@" not in to_email:
            error_msg = f"Invalid recipient email address: {to_email}"
            logger.error(error_msg)
            return error_msg
            
        # Create message
        msg = MIMEMultipart('alternative')
        msg['From'] = email_user
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Add timestamp to message
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_message = f"{message}\n\n---\nSent via AIAssist at {timestamp}"
        
        # Add CC if provided
        recipients = [to_email]
        if cc_email and "@" in cc_email:
            msg['Cc'] = cc_email
            recipients.append(cc_email)
            logger.info(f"Added CC recipient: {cc_email}")
        
        # Create both plain text and HTML parts
        text_part = MIMEText(full_message, 'plain', 'utf-8')
        html_part = MIMEText(f"<html><body><p>{full_message.replace(chr(10), '<br>')}</p></body></html>", 'html', 'utf-8')
        
        msg.attach(text_part)
        msg.attach(html_part)
        
        logger.info(f"Message created successfully. Size: {len(msg.as_string())} bytes")
        
        # Connect to Gmail SMTP server
        logger.info(f"Connecting to {smtp_server}:{smtp_port}...")
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.set_debuglevel(2)  # Enable SMTP debug output
        
        logger.info("Starting TLS...")
        server.starttls()
        
        logger.info(f"Logging in as {email_user}...")
        server.login(email_user, email_password)
        logger.info("Login successful!")
        
        # Send email
        logger.info(f"Sending email to {recipients}...")
        text = msg.as_string()
        send_result = server.sendmail(email_user, recipients, text)
        
        logger.info(f"Send result: {send_result}")
        
        server.quit()
        logger.info("SMTP connection closed")
        
        success_msg = f"Email sent successfully to {to_email}"
        if cc_email:
            success_msg += f" (CC: {cc_email})"
        
        logger.info(success_msg)
        logger.info("="*50)
        
        # Also save a copy locally for debugging
        debug_filename = f"sent_email_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(debug_filename, 'w', encoding='utf-8') as f:
            f.write(f"From: {email_user}\n")
            f.write(f"To: {to_email}\n")
            f.write(f"Subject: {subject}\n")
            f.write(f"Message:\n{full_message}\n")
        logger.info(f"Debug copy saved to {debug_filename}")
        
        return success_msg
        
    except smtplib.SMTPAuthenticationError as e:
        error_msg = f"{email_provider.upper()} authentication failed: {str(e)}"
        logger.error(error_msg)
        if email_provider == "gmail":
            logger.error("For Gmail: Use App Password or enable 'Less secure apps'")
            logger.error("Generate App Password at: https://myaccount.google.com/apppasswords")
        else:
            logger.error(f"Make sure your {email_provider} credentials are correct")
        return f"Email sending failed: Authentication error. Please check your {email_provider} credentials."
        
    except smtplib.SMTPRecipientsRefused as e:
        error_msg = f"Recipients refused: {str(e)}"
        logger.error(error_msg)
        return f"Email sending failed: Invalid recipient address {to_email}"
        
    except smtplib.SMTPException as e:
        error_msg = f"SMTP error occurred: {str(e)}"
        logger.error(error_msg)
        return f"Email sending failed: SMTP error - {str(e)}"
        
    except Exception as e:
        error_msg = f"Unexpected error sending email: {str(e)}"
        logger.error(error_msg)
        logger.exception("Full traceback:")
        return f"An error occurred while sending email: {str(e)}"