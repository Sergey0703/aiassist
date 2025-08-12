"""
Email Tools Module - Инструменты для работы с электронной почтой

Этот модуль содержит все инструменты для отправки email:
- send_email: Отправка email через SMTP (Gmail, Outlook, Yandex, Mail.ru)
- validate_email_tools: Проверка конфигурации email сервисов
"""

import asyncio
import logging
import smtplib
import os
from email.mime.multipart import MIMEMultipart  
from email.mime.text import MIMEText
from typing import Optional, Dict, Any
from datetime import datetime
from livekit.agents import function_tool, RunContext

# -------------------- Logging Setup --------------------
logger = logging.getLogger("email-tools")

# -------------------- Email Providers Configuration --------------------
EMAIL_PROVIDERS = {
    "gmail": {
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "user_env": "GMAIL_USER",
        "password_env": "GMAIL_APP_PASSWORD",
        "name": "Gmail",
        "tls": True
    },
    "outlook": {
        "smtp_server": "smtp-mail.outlook.com", 
        "smtp_port": 587,
        "user_env": "OUTLOOK_USER",
        "password_env": "OUTLOOK_PASSWORD",
        "name": "Microsoft Outlook",
        "tls": True
    },
    "yandex": {
        "smtp_server": "smtp.yandex.ru",
        "smtp_port": 587,
        "user_env": "YANDEX_USER", 
        "password_env": "YANDEX_PASSWORD",
        "name": "Yandex Mail",
        "tls": True
    },
    "mail": {
        "smtp_server": "smtp.mail.ru",
        "smtp_port": 587,
        "user_env": "MAIL_USER",
        "password_env": "MAIL_PASSWORD", 
        "name": "Mail.ru",
        "tls": True
    }
}

DEFAULT_EMAIL_PROVIDER = "gmail"

# -------------------- Email Tool --------------------
@function_tool()    
async def send_email(
    context: RunContext,
    to_email: str,
    subject: str,
    message: str,
    cc_email: Optional[str] = None
) -> str:
    """
    Send an email through configured SMTP provider
    
    Args:
        to_email: Recipient email address
        subject: Email subject line
        message: Email body content
        cc_email: Optional CC email address
    
    Returns:
        str: Success or error message
    """
    logger.info("="*50)
    logger.info("🚀 [EMAIL TOOL] Starting email send process")
    logger.info(f"📧 [EMAIL] To: {to_email}")
    logger.info(f"📝 [EMAIL] Subject: {subject}")
    logger.info(f"💬 [EMAIL] Message: {message[:100]}...")
    if cc_email:
        logger.info(f"📋 [EMAIL] CC: {cc_email}")
    
    # Check for DEMO mode
    demo_mode = os.getenv("EMAIL_DEMO_MODE", "false").lower() == "true"
    
    if demo_mode:
        logger.info("🎭 [EMAIL DEMO] Demo mode enabled - simulating email send")
        return await _send_demo_email(to_email, subject, message, cc_email)
    
    # Get email provider configuration
    email_provider = os.getenv("EMAIL_PROVIDER", DEFAULT_EMAIL_PROVIDER).lower()
    
    if email_provider not in EMAIL_PROVIDERS:
        error_msg = f"Unsupported email provider '{email_provider}'. Supported: {', '.join(EMAIL_PROVIDERS.keys())}"
        logger.error(f"❌ [EMAIL ERROR] {error_msg}")
        return f"I'm afraid I cannot send email, sir. {error_msg}"
    
    provider_config = EMAIL_PROVIDERS[email_provider]
    logger.info(f"📮 [EMAIL PROVIDER] Using {provider_config['name']}")
    
    # Get credentials
    email_user = os.getenv(provider_config["user_env"])
    email_password = os.getenv(provider_config["password_env"])
    
    logger.info(f"👤 [EMAIL USER] {email_user}")
    logger.info(f"🔑 [EMAIL PASSWORD] {'Found' if email_password else 'NOT FOUND'}")
    
    if not email_user or not email_password:
        error_msg = f"I'm afraid I cannot send email, sir. The {provider_config['name']} credentials are not configured properly."
        logger.error(f"❌ [EMAIL ERROR] {error_msg}")
        return error_msg
    
    # Validate email addresses
    if not _is_valid_email(to_email):
        error_msg = f"The email address '{to_email}' doesn't look quite right, sir."
        logger.error(f"❌ [EMAIL ERROR] {error_msg}")
        return error_msg
    
    if cc_email and not _is_valid_email(cc_email):
        error_msg = f"The CC email address '{cc_email}' doesn't look quite right, sir."
        logger.error(f"❌ [EMAIL ERROR] {error_msg}")
        return error_msg
    
    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['From'] = email_user
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Add timestamp to message
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_message = f"{message}\n\n---\nSent via AI Voice Assistant at {timestamp}"
        
        # Add CC if provided
        recipients = [to_email]
        if cc_email:
            msg['Cc'] = cc_email
            recipients.append(cc_email)
            logger.info(f"📋 [EMAIL CC] Added CC recipient: {cc_email}")
        
        # Create both plain text and HTML parts
        text_part = MIMEText(full_message, 'plain', 'utf-8')
        html_part = MIMEText(
            f"<html><body><p>{full_message.replace(chr(10), '<br>')}</p></body></html>", 
            'html', 'utf-8'
        )
        
        msg.attach(text_part)
        msg.attach(html_part)
        
        logger.info(f"📦 [EMAIL MESSAGE] Created successfully. Size: {len(msg.as_string())} bytes")
        
        # Connect to SMTP server
        logger.info(f"🌐 [EMAIL SMTP] Connecting to {provider_config['smtp_server']}:{provider_config['smtp_port']}...")
        server = smtplib.SMTP(provider_config['smtp_server'], provider_config['smtp_port'])
        
        if provider_config['tls']:
            logger.info("🔒 [EMAIL TLS] Starting TLS encryption...")
            server.starttls()
        
        logger.info(f"🔐 [EMAIL LOGIN] Logging in as {email_user}...")
        server.login(email_user, email_password)
        logger.info("✅ [EMAIL LOGIN] Login successful!")
        
        # Send email
        logger.info(f"📤 [EMAIL SEND] Sending email to {recipients}...")
        text = msg.as_string()
        send_result = server.sendmail(email_user, recipients, text)
        
        logger.info(f"📊 [EMAIL RESULT] Send result: {send_result}")
        
        server.quit()
        logger.info("🔌 [EMAIL SMTP] Connection closed")
        
        success_msg = f"Email sent successfully to {to_email}, sir"
        if cc_email:
            success_msg += f" with copy to {cc_email}"
        success_msg += "."
        
        logger.info(f"✅ [EMAIL SUCCESS] {success_msg}")
        logger.info("="*50)
        
        return success_msg
        
    except smtplib.SMTPAuthenticationError as e:
        error_msg = f"I'm having trouble with email authentication, sir. Please check the {provider_config['name']} credentials."
        logger.error(f"🔐 [EMAIL AUTH ERROR] {provider_config['name']} authentication failed: {str(e)}")
        return error_msg
        
    except smtplib.SMTPRecipientsRefused as e:
        error_msg = f"The email address {to_email} was refused, sir. It may not be valid."
        logger.error(f"📧 [EMAIL RECIPIENT ERROR] Recipients refused: {str(e)}")
        return error_msg
        
    except smtplib.SMTPException as e:
        error_msg = f"I encountered an SMTP error while sending the email, sir."
        logger.error(f"📮 [EMAIL SMTP ERROR] SMTP error occurred: {str(e)}")
        return error_msg
        
    except Exception as e:
        error_msg = f"An unexpected error occurred while sending the email, sir."
        logger.error(f"💥 [EMAIL EXCEPTION] Unexpected error sending email: {str(e)}")
        logger.exception("Full email exception traceback:")
        return error_msg

# -------------------- Demo Email Function --------------------
async def _send_demo_email(to_email: str, subject: str, message: str, cc_email: Optional[str] = None) -> str:
    """
    Send demo email (save to file instead of actually sending)
    
    Args:
        to_email: Recipient email address
        subject: Email subject line
        message: Email body content
        cc_email: Optional CC email address
    
    Returns:
        str: Demo success message
    """
    try:
        # Add timestamp to message
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_message = f"{message}\n\n---\nSent via AI Voice Assistant at {timestamp}"
        
        # Save email locally
        demo_filename = f"demo_email_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(demo_filename, 'w', encoding='utf-8') as f:
            f.write(f"=== DEMO EMAIL (NOT SENT) ===\n")
            f.write(f"From: demo@aiassist.local\n")
            f.write(f"To: {to_email}\n")
            if cc_email:
                f.write(f"CC: {cc_email}\n")
            f.write(f"Subject: {subject}\n")
            f.write(f"Date: {timestamp}\n")
            f.write(f"\nMessage:\n{full_message}\n")
            f.write("="*30 + "\n")
        
        logger.info(f"📁 [EMAIL DEMO] Demo email saved to {demo_filename}")
        
        success_msg = f"Email simulated successfully to {to_email}, sir"
        if cc_email:
            success_msg += f" with copy to {cc_email}"
        success_msg += f". Demo file saved as {demo_filename}."
        
        logger.info(f"✅ [EMAIL DEMO] {success_msg}")
        logger.info("="*50)
        
        return success_msg
        
    except Exception as e:
        error_msg = f"Failed to create demo email file: {str(e)}"
        logger.error(f"💥 [EMAIL DEMO ERROR] {error_msg}")
        return error_msg

# -------------------- Email Validation --------------------
def _is_valid_email(email: str) -> bool:
    """
    Basic email validation
    
    Args:
        email: Email address to validate
    
    Returns:
        bool: True if email looks valid
    """
    return "@" in email and "." in email.split("@")[-1]

async def validate_email_tools() -> Dict[str, Any]:
    """
    Validate email tools and their configuration
    
    Returns:
        dict: Status of email tools and providers
    """
    results = {
        "timestamp": asyncio.get_event_loop().time(),
        "send_email": False,
        "demo_mode": os.getenv("EMAIL_DEMO_MODE", "false").lower() == "true",
        "providers": {}
    }
    
    logger.info("🔍 [EMAIL VALIDATION] Validating email tools...")
    
    # Check configured provider
    current_provider = os.getenv("EMAIL_PROVIDER", DEFAULT_EMAIL_PROVIDER).lower()
    results["current_provider"] = current_provider
    
    # Validate all providers
    for provider_name, provider_config in EMAIL_PROVIDERS.items():
        user = os.getenv(provider_config["user_env"])
        password = os.getenv(provider_config["password_env"])
        
        results["providers"][provider_name] = {
            "name": provider_config["name"],
            "user_configured": bool(user),
            "password_configured": bool(password),
            "fully_configured": bool(user and password),
            "is_current": provider_name == current_provider
        }
    
    # Determine if email sending is possible
    if results["demo_mode"]:
        results["send_email"] = True
        logger.info("✅ [EMAIL VALIDATION] Demo mode enabled - email tool available")
    else:
        current_provider_config = results["providers"].get(current_provider, {})
        results["send_email"] = current_provider_config.get("fully_configured", False)
        
        if results["send_email"]:
            logger.info(f"✅ [EMAIL VALIDATION] {EMAIL_PROVIDERS[current_provider]['name']} configured properly")
        else:
            logger.warning(f"⚠️ [EMAIL VALIDATION] {current_provider} not properly configured")
    
    logger.info(f"📊 [EMAIL VALIDATION] Results: {results}")
    return results

# -------------------- Email Tools Information --------------------
def get_email_tools_info() -> Dict[str, Any]:
    """
    Get information about available email tools
    
    Returns:
        dict: Information about all email tools
    """
    return {
        "module": "email_tools",
        "version": "1.0.0",
        "default_provider": DEFAULT_EMAIL_PROVIDER,
        "supported_providers": {
            name: {
                "name": config["name"],
                "server": config["smtp_server"],
                "port": config["smtp_port"],
                "user_env": config["user_env"],
                "password_env": config["password_env"],
                "tls": config["tls"]
            }
            for name, config in EMAIL_PROVIDERS.items()
        },
        "tools": {
            "send_email": {
                "description": "Send email through SMTP providers",
                "parameters": ["to_email", "subject", "message", "cc_email"],
                "supported_providers": list(EMAIL_PROVIDERS.keys()),
                "demo_mode_available": True,
                "status": "active"
            }
        },
        "features": [
            "Multiple SMTP providers support",
            "Demo mode for testing", 
            "HTML and plain text emails",
            "CC support",
            "Automatic timestamping",
            "Email validation"
        ]
    }

# -------------------- Future Email Tools --------------------
@function_tool()
async def send_sms(
    context: RunContext,
    phone_number: str,
    message: str
) -> str:
    """
    Send SMS message (placeholder for future implementation)
    
    Args:
        phone_number: Phone number to send SMS to
        message: SMS message content
    
    Returns:
        str: Success or error message
    """
    logger.info(f"📱 [SMS] Would send SMS to {phone_number}: '{message}'")
    
    # Пока что заглушка - в будущем здесь будет реальная реализация
    placeholder_msg = f"SMS tool is not yet implemented. Would send '{message}' to {phone_number}."
    
    print(f"⚠️ [EMAIL PLACEHOLDER] {placeholder_msg}")
    return placeholder_msg

# -------------------- Module Exports --------------------
__all__ = [
    # Основные инструменты
    'send_email',
    'send_sms',  # пока заглушка
    
    # Валидация и управление
    'validate_email_tools',
    'get_email_tools_info',
    
    # Конфигурация
    'EMAIL_PROVIDERS',
    'DEFAULT_EMAIL_PROVIDER',
]

# -------------------- Module Testing --------------------
if __name__ == "__main__":
    print("🛠️ [EMAIL TOOLS] Module Information:")
    info = get_email_tools_info()
    print(f"   📦 Module: {info['module']} v{info['version']}")
    print(f"   📮 Default Provider: {info['default_provider']}")
    print(f"   🔧 Tools: {len(info['tools'])}")
    
    for tool_name, tool_info in info['tools'].items():
        print(f"      • {tool_name}: {tool_info['status']}")
    
    print(f"   📧 Supported Providers: {len(info['supported_providers'])}")
    for provider_name, provider_info in info['supported_providers'].items():
        print(f"      • {provider_name}: {provider_info['name']}")
    
    # Тестируем email инструменты
    async def test_module():
        print("\n🧪 [TESTING] Testing email tools...")
        
        # Валидация всех инструментов
        validation_results = await validate_email_tools()
        
        print(f"   📧 Send Email: {'✅ Working' if validation_results['send_email'] else '❌ Failed'}")
        print(f"   🎭 Demo Mode: {'✅ Enabled' if validation_results['demo_mode'] else '❌ Disabled'}")
        print(f"   📮 Current Provider: {validation_results.get('current_provider', 'not set')}")
        
        print("\n📋 [PROVIDER STATUS]:")
        for provider_name, provider_status in validation_results['providers'].items():
            status_emoji = "✅" if provider_status['fully_configured'] else "⚠️" if provider_status['user_configured'] or provider_status['password_configured'] else "❌"
            current_marker = " (current)" if provider_status['is_current'] else ""
            print(f"   {status_emoji} {provider_name}{current_marker}: {provider_status['name']}")
    
    asyncio.run(test_module())