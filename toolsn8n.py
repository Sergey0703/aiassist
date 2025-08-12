import asyncio
import logging
import aiohttp
import json
import os
import smtplib
from email.mime.multipart import MIMEMultipart  
from email.mime.text import MIMEText
from typing import Optional
from datetime import datetime
from livekit.agents import function_tool, RunContext

# -------------------- Logging Setup --------------------
logger = logging.getLogger("n8n-tools")

# -------------------- n8n Configuration --------------------
N8N_WEATHER_URL = "https://auto2025system.duckdns.org/webhook/smart-weather"

# Можно добавить другие n8n endpoints здесь
# N8N_EMAIL_URL = "https://auto2025system.duckdns.org/webhook/smart-email"
# N8N_ANALYTICS_URL = "https://auto2025system.duckdns.org/webhook/smart-analytics"

# -------------------- n8n Weather Tool --------------------
@function_tool()
async def get_weather_n8n(
    context: RunContext,
    city: str,
    units: str = "celsius"
) -> str:
    """
    Get weather information through n8n workflow
    
    Args:
        city: City name (e.g., "London", "Paris", "Tokyo")
        units: Temperature units ("celsius" or "fahrenheit")
    
    Returns:
        str: Weather information or error message
    """
    logger.info(f"🌤️ [N8N WEATHER] Getting weather for '{city}' in {units}")
    print(f"🌤️ [N8N WEATHER] Requesting weather for {city}...")
    
    try:
        # Подготавливаем данные для n8n в формате который ожидает workflow
        payload = {
            "action": "weather",
            "city": city.strip(),
            "units": units.lower(),
            "date": "today",
            "user_id": "livekit_user",
            "timestamp": asyncio.get_event_loop().time()
        }
        
        logger.info(f"🌐 [N8N REQUEST] Sending to {N8N_WEATHER_URL}")
        logger.info(f"🌐 [N8N PAYLOAD] {payload}")
        
        # Делаем HTTP запрос к n8n workflow
        async with aiohttp.ClientSession() as session:
            async with session.post(
                N8N_WEATHER_URL,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "LiveKit-N8N-Agent/1.0"
                },
                timeout=aiohttp.ClientTimeout(total=15)
            ) as response:
                
                logger.info(f"📡 [N8N RESPONSE] Status: {response.status}")
                
                if response.status == 200:
                    result = await response.json()
                    
                    logger.info(f"📊 [N8N DATA] Success: {result.get('success', False)}")
                    logger.info(f"📊 [N8N MESSAGE] {result.get('message', 'No message')[:100]}...")
                    
                    if result.get('success', False):
                        message = result.get('message', 'Weather information retrieved successfully.')
                        
                        print(f"✅ [N8N SUCCESS] {message[:100]}...")
                        logger.info(f"✅ [N8N SUCCESS] Weather retrieved for {city}")
                        
                        return message
                    else:
                        error_message = result.get('message', 'Failed to get weather information.')
                        logger.error(f"❌ [N8N ERROR] {error_message}")
                        print(f"❌ [N8N ERROR] {error_message}")
                        return f"Weather service error: {error_message}"
                        
                else:
                    error_text = await response.text()
                    error_msg = f"Weather service returned status {response.status}. Please try again."
                    logger.error(f"❌ [N8N HTTP ERROR] Status {response.status}: {error_text[:200]}")
                    print(f"❌ [N8N HTTP ERROR] Status {response.status}")
                    return error_msg
                    
    except asyncio.TimeoutError:
        error_msg = "Weather request timed out. The service might be busy, please try again."
        logger.error(f"⏰ [N8N TIMEOUT] Weather request timed out for {city}")
        print(f"⏰ [N8N TIMEOUT] Request timed out")
        return error_msg
        
    except aiohttp.ClientError as e:
        error_msg = f"Failed to connect to weather service. Please check your connection and try again."
        logger.error(f"🌐 [N8N CONNECTION ERROR] {str(e)}")
        print(f"🌐 [N8N CONNECTION ERROR] {str(e)}")
        return error_msg
        
    except json.JSONDecodeError as e:
        error_msg = f"Weather service returned invalid data. Please try again."
        logger.error(f"📄 [N8N JSON ERROR] {str(e)}")
        print(f"📄 [N8N JSON ERROR] Invalid response format")
        return error_msg
        
    except Exception as e:
        error_msg = f"An unexpected error occurred while getting weather information for {city}. Please try again."
        logger.error(f"💥 [N8N EXCEPTION] Weather error for '{city}': {e}")
        logger.exception("Full n8n weather exception traceback:")
        print(f"💥 [N8N EXCEPTION] {str(e)}")
        return error_msg

# -------------------- Web Search Tool --------------------
@function_tool()
async def search_web(
    context: RunContext,
    query: str
) -> str:
    """
    Search the web using Tavily AI Search API for comprehensive and AI-optimized results
    
    Args:
        query: Search query (e.g., "latest news about AI", "how to cook pasta")
    """
    print("=" * 80)
    print(f"🔍 [SEARCH TOOL STARTED] Searching for: '{query}'")
    logger.info(f"🔍 [SEARCH TOOL STARTED] query='{query}'")
    
    # Get Tavily API key from environment
    tavily_api_key = os.getenv("TAVILY_API_KEY")
    print(f"🔑 [TAVILY API KEY] {'Found' if tavily_api_key else 'NOT FOUND'}")
    logger.info(f"🔑 [TAVILY API KEY] {'Found' if tavily_api_key else 'NOT FOUND'}")
    
    if not tavily_api_key:
        error_msg = "I'm sorry sir, I cannot search the web - the search service is not properly configured."
        print(f"❌ [SEARCH ERROR] {error_msg}")
        logger.error(f"❌ [SEARCH ERROR] {error_msg}")
        print("=" * 80)
        return error_msg
    
    try:
        # Tavily AI Search API
        url = "https://api.tavily.com/search"
        headers = {
            "Content-Type": "application/json"
        }
        
        payload = {
            "api_key": tavily_api_key,
            "query": query,
            "search_depth": "basic",  # basic or advanced
            "include_answer": True,   # Get AI-generated answer
            "include_images": False,  # Don't need images for voice
            "include_raw_content": False,  # Don't need full content
            "max_results": 3,         # Limit results for voice response
            "include_domains": [],    # No domain restrictions
            "exclude_domains": []     # No domain exclusions
        }
        
        print(f"🌐 [SEARCH API] Calling URL: {url}")
        print(f"🌐 [SEARCH PAYLOAD] {payload}")
        logger.info(f"🌐 [SEARCH API] URL: {url}, payload: {payload}")
        
        async with aiohttp.ClientSession() as session:
            print("🔄 [SEARCH HTTP] Making HTTP request...")
            logger.info("🔄 [SEARCH HTTP] Making HTTP request...")
            
            async with session.post(url, json=payload, headers=headers) as response:
                print(f"📡 [SEARCH RESPONSE] Status: {response.status}")
                logger.info(f"📡 [SEARCH RESPONSE] Status: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    print(f"📊 [SEARCH DATA] Raw response length: {len(str(data))}")
                    logger.info(f"📊 [SEARCH DATA] Raw response keys: {list(data.keys())}")
                    
                    # Get AI-generated answer if available
                    if data.get("answer"):
                        answer = data['answer']
                        print(f"🤖 [SEARCH ANSWER] Found AI answer: {answer[:100]}...")
                        logger.info(f"🤖 [SEARCH ANSWER] {answer}")
                        
                        result = f"I found information about '{query}'. {answer}"
                        
                        # Add a few top sources for credibility
                        if data.get("results") and len(data["results"]) > 0:
                            sources = []
                            print(f"📄 [SEARCH SOURCES] Processing {len(data['results'])} results")
                            
                            for i, result_item in enumerate(data["results"][:2]):  # Top 2 sources
                                title = result_item.get("title", "")
                                url_source = result_item.get("url", "")
                                print(f"📄 [SEARCH SOURCE {i+1}] {title} - {url_source}")
                                logger.info(f"📄 [SEARCH SOURCE {i+1}] {title} - {url_source}")
                                
                                if title and len(title) < 100:  # Keep titles short for voice
                                    sources.append(title)
                            
                            if sources:
                                result += f" This information comes from sources including: {', '.join(sources)}."
                                print(f"✅ [SEARCH SOURCES] Added sources: {sources}")
                    
                    # Fallback to search results if no answer
                    elif data.get("results") and len(data["results"]) > 0:
                        print(f"📄 [SEARCH FALLBACK] No AI answer, using search results")
                        result = f"I found several results for '{query}': "
                        
                        for i, result_item in enumerate(data["results"][:3]):  # Top 3 results
                            title = result_item.get("title", "")
                            snippet = result_item.get("content", "")
                            
                            print(f"📄 [SEARCH RESULT {i+1}] {title}: {snippet[:50]}...")
                            logger.info(f"📄 [SEARCH RESULT {i+1}] {title}: {snippet}")
                            
                            if snippet:
                                # Limit snippet length for voice
                                snippet = snippet[:200] + "..." if len(snippet) > 200 else snippet
                                result += f" {title}: {snippet}"
                                
                                if i < 2:  # Add separator between results
                                    result += " ... "
                    
                    else:
                        result = f"I searched for '{query}' but found limited information, sir. Would you like me to try a more specific search?"
                        print(f"⚠️ [SEARCH WARNING] No results found")
                        logger.warning(f"⚠️ [SEARCH WARNING] No results found for '{query}'")
                    
                    print(f"✅ [SEARCH SUCCESS] Final result: {result[:100]}...")
                    logger.info(f"✅ [SEARCH SUCCESS] Web search completed successfully for: {query}")
                    logger.info(f"✅ [SEARCH FINAL] {result}")
                    print("=" * 80)
                    return result
                    
                elif response.status == 401:
                    error_msg = "I'm having authentication issues with the search service, sir."
                    print(f"❌ [SEARCH ERROR 401] {error_msg}")
                    logger.error(f"❌ [SEARCH ERROR 401] {error_msg}")
                    print("=" * 80)
                    return error_msg
                elif response.status == 429:
                    error_msg = "I've reached the search limit for now, sir. Please try again later."
                    print(f"❌ [SEARCH ERROR 429] {error_msg}")
                    logger.error(f"❌ [SEARCH ERROR 429] {error_msg}")
                    print("=" * 80)
                    return error_msg
                else:
                    error_msg = "I'm having trouble with the search service right now, sir."
                    print(f"❌ [SEARCH ERROR {response.status}] {error_msg}")
                    logger.error(f"❌ [SEARCH ERROR {response.status}] {error_msg}")
                    print("=" * 80)
                    return error_msg
                    
    except Exception as e:
        error_msg = f"I encountered an issue while searching for '{query}', sir. Please try again."
        print(f"💥 [SEARCH EXCEPTION] {str(e)}")
        logger.error(f"💥 [SEARCH EXCEPTION] Web search error for '{query}': {e}")
        logger.exception("Full search exception traceback:")
        print("=" * 80)
        return error_msg

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
    
    # Check for DEMO mode
    demo_mode = os.getenv("EMAIL_DEMO_MODE", "false").lower() == "true"
    
    if demo_mode:
        logger.info("DEMO MODE ENABLED - Simulating email send")
        
        # Add timestamp to message
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_message = f"{message}\n\n---\nSent via AIAssist at {timestamp}"
        
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
        
        logger.info(f"Demo email saved to {demo_filename}")
        
        success_msg = f"Email simulated successfully to {to_email}, sir"
        if cc_email:
            success_msg += f" with copy to {cc_email}"
        success_msg += f". Demo file saved as {demo_filename}."
        
        logger.info(success_msg)
        logger.info("="*50)
        
        return success_msg
    
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
        
        if not email_user or not email_password:
            error_msg = f"I'm afraid I cannot send email, sir. The {email_provider} credentials are not configured properly."
            logger.error(error_msg)
            return error_msg
        
        # Validate email addresses
        if "@" not in to_email:
            error_msg = f"The email address '{to_email}' doesn't look quite right, sir."
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
        
        # Connect to SMTP server
        logger.info(f"Connecting to {smtp_server}:{smtp_port}...")
        server = smtplib.SMTP(smtp_server, smtp_port)
        
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
        
        success_msg = f"Email sent successfully to {to_email}, sir"
        if cc_email:
            success_msg += f" with copy to {cc_email}"
        success_msg += "."
        
        logger.info(success_msg)
        logger.info("="*50)
        
        return success_msg
        
    except smtplib.SMTPAuthenticationError as e:
        error_msg = f"I'm having trouble with email authentication, sir. Please check the {email_provider} credentials."
        logger.error(f"{email_provider.upper()} authentication failed: {str(e)}")
        return error_msg
        
    except smtplib.SMTPRecipientsRefused as e:
        error_msg = f"The email address {to_email} was refused, sir. It may not be valid."
        logger.error(f"Recipients refused: {str(e)}")
        return error_msg
        
    except smtplib.SMTPException as e:
        error_msg = f"I encountered an SMTP error while sending the email, sir."
        logger.error(f"SMTP error occurred: {str(e)}")
        return error_msg
        
    except Exception as e:
        error_msg = f"An unexpected error occurred while sending the email, sir."
        logger.error(f"Unexpected error sending email: {str(e)}")
        logger.exception("Full traceback:")
        return error_msg

# -------------------- n8n Connection Test --------------------
async def test_n8n_connection() -> bool:
    """
    Test if n8n workflow is accessible
    
    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        logger.info(f"🧪 [N8N TEST] Testing connection to {N8N_WEATHER_URL}")
        
        test_payload = {
            "action": "weather",
            "city": "London",
            "units": "celsius",
            "user_id": "test_user",
            "test": True
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                N8N_WEATHER_URL,
                json=test_payload,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "LiveKit-N8N-Agent/1.0-Test"
                },
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    if result.get('success', False):
                        logger.info("✅ [N8N TEST] Connection successful")
                        print("✅ [N8N TEST] Weather service is working")
                        return True
                    else:
                        logger.warning(f"⚠️ [N8N TEST] Service responded but failed: {result.get('message', 'Unknown error')}")
                        print("⚠️ [N8N TEST] Service responded but returned an error")
                        return False
                else:
                    logger.error(f"❌ [N8N TEST] HTTP error {response.status}")
                    print(f"❌ [N8N TEST] HTTP error {response.status}")
                    return False
                    
    except asyncio.TimeoutError:
        logger.error("⏰ [N8N TEST] Connection test timed out")
        print("⏰ [N8N TEST] Connection timed out")
        return False
        
    except aiohttp.ClientError as e:
        logger.error(f"🌐 [N8N TEST] Connection error: {e}")
        print(f"🌐 [N8N TEST] Connection failed: {e}")
        return False
        
    except Exception as e:
        logger.error(f"💥 [N8N TEST] Connection test failed: {e}")
        print(f"💥 [N8N TEST] Connection failed: {e}")
        return False

# -------------------- Additional n8n Tools (Examples) --------------------

# Пример дополнительного n8n инструмента для будущего использования
@function_tool()
async def send_notification_n8n(
    context: RunContext,
    message: str,
    channel: str = "general",
    priority: str = "normal"
) -> str:
    """
    Send notification through n8n workflow (example for future use)
    
    Args:
        message: Notification message
        channel: Channel to send to (e.g., "general", "alerts")
        priority: Priority level ("low", "normal", "high", "urgent")
    
    Returns:
        str: Success or error message
    """
    # Пока что возвращаем заглушку
    logger.info(f"📢 [N8N NOTIFICATION] Would send: '{message}' to {channel} (priority: {priority})")
    return f"Notification tool is not yet implemented. Would send '{message}' to {channel}."

# -------------------- Tool Management --------------------

def get_tool_info() -> dict:
    """
    Get information about available tools
    
    Returns:
        dict: Information about all available tools
    """
    return {
        "n8n_tools": {
            "get_weather_n8n": {
                "description": "Get weather information via n8n workflow",
                "endpoint": N8N_WEATHER_URL,
                "status": "active"
            },
            "send_notification_n8n": {
                "description": "Send notifications via n8n (placeholder)",
                "status": "placeholder"
            }
        },
        "integrated_tools": {
            "search_web": {
                "description": "Search the web using Tavily AI",
                "api": "Tavily",
                "status": "active"
            },
            "send_email": {
                "description": "Send email messages via SMTP",
                "providers": ["gmail", "outlook", "yandex", "mail.ru"],
                "status": "active"
            }
        }
    }

async def validate_all_tools() -> dict:
    """
    Validate all tools and their availability
    
    Returns:
        dict: Status of all tools
    """
    results = {
        "n8n_weather": False,
        "search_web": False,
        "send_email": False,
        "timestamp": asyncio.get_event_loop().time()
    }
    
    # Тестируем n8n подключение
    try:
        results["n8n_weather"] = await test_n8n_connection()
    except Exception as e:
        logger.error(f"❌ [TOOL VALIDATION] n8n test failed: {e}")
        results["n8n_weather"] = False
    
    # Проверяем Tavily API ключ
    tavily_key = os.getenv("TAVILY_API_KEY")
    results["search_web"] = bool(tavily_key)
    
    # Проверяем email конфигурацию
    gmail_user = os.getenv("GMAIL_USER")
    gmail_password = os.getenv("GMAIL_APP_PASSWORD")
    results["send_email"] = bool(gmail_user and gmail_password)
    
    logger.info(f"🔍 [TOOL VALIDATION] Results: {results}")
    return results

# -------------------- All Available Tools --------------------
# Список всех доступных инструментов для импорта в основной агент
AVAILABLE_TOOLS = [
    # n8n инструменты
    get_weather_n8n,           # Активный n8n инструмент для погоды
    
    # Интегрированные инструменты (ранее внешние)
    search_web,                # Tavily web search
    send_email,                # SMTP email sending
    
    # send_notification_n8n,   # Пока заглушка, можно активировать когда готов
]

# Список инструментов в разработке (не включены в AVAILABLE_TOOLS)
DEVELOPMENT_TOOLS = [
    send_notification_n8n,     # Пока что заглушка
]

# -------------------- Tool Categories --------------------
TOOL_CATEGORIES = {
    "weather": [get_weather_n8n],
    "communication": [send_email, send_notification_n8n],
    "information": [search_web],
    "n8n_integrated": [get_weather_n8n, send_notification_n8n],
    "web_services": [search_web, send_email]
}

# -------------------- Initialization --------------------
def initialize_tools():
    """Initialize tools and log their status"""
    logger.info("🛠️ [TOOLS] Initializing all tools...")
    
    tool_info = get_tool_info()
    logger.info(f"📋 [TOOLS] Available tools: {len(AVAILABLE_TOOLS)} active, {len(DEVELOPMENT_TOOLS)} in development")
    
    for category, tools in TOOL_CATEGORIES.items():
        logger.info(f"📂 [TOOLS] Category '{category}': {len(tools)} tools")
    
    print("🛠️ [TOOLS] All tools initialized successfully")
    return True

# -------------------- Module Initialization --------------------
if __name__ == "__main__":
    # Если запускаем файл напрямую - показываем информацию об инструментах
    print("🛠️ [N8N TOOLS] Tool information:")
    print(f"   Active tools: {len(AVAILABLE_TOOLS)}")
    print(f"   Development tools: {len(DEVELOPMENT_TOOLS)}")
    print(f"   Categories: {list(TOOL_CATEGORIES.keys())}")
    
    # Можно добавить тестирование инструментов
    import asyncio
    
    async def test_tools():
        print("\n🧪 [TESTING] Running tool validation...")
        results = await validate_all_tools()
        print(f"📊 [RESULTS] Tool validation: {results}")
    
    asyncio.run(test_tools())
else:
    # При импорте - просто инициализируем
    initialize_tools()