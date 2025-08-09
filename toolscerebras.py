import logging
import os
import smtplib
import aiohttp
from email.mime.multipart import MIMEMultipart  
from email.mime.text import MIMEText
from datetime import datetime
from livekit.agents import function_tool, RunContext

# Настройка логирования для инструментов
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("toolscerebras.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("toolscerebras")


@function_tool()
async def get_weather(
    context: RunContext,
    city: str
) -> str:
    """
    Get current weather for a city using WeatherAPI.com
    
    Args:
        city: City name (e.g., "London", "New York", "Moscow")
    """
    print("=" * 80)
    print(f"🌤️ [WEATHER TOOL STARTED] Getting weather for '{city}'")
    logger.info(f"🌤️ [WEATHER TOOL STARTED] city='{city}'")
    
    # Get WeatherAPI key from environment
    weather_api_key = os.getenv("WEATHER_API_KEY")
    print(f"🔑 [WEATHER API KEY] {'Found' if weather_api_key else 'NOT FOUND'}")
    logger.info(f"🔑 [WEATHER API KEY] {'Found' if weather_api_key else 'NOT FOUND'}")
    
    if not weather_api_key:
        error_msg = "Weather service is not configured properly."
        print(f"❌ [WEATHER ERROR] {error_msg}")
        logger.error(f"❌ [WEATHER ERROR] {error_msg}")
        print("=" * 80)
        return error_msg
    
    try:
        # WeatherAPI.com endpoint - только текущая погода для упрощения
        url = f"http://api.weatherapi.com/v1/current.json"
        params = {
            "key": weather_api_key,
            "q": city,
            "aqi": "no"
        }
        
        print(f"🌐 [WEATHER API] Calling URL: {url}")
        logger.info(f"🌐 [WEATHER API] URL: {url}, params: {params}")
        
        async with aiohttp.ClientSession() as session:
            print("🔄 [WEATHER HTTP] Making HTTP request...")
            logger.info("🔄 [WEATHER HTTP] Making HTTP request...")
            
            async with session.get(url, params=params) as response:
                print(f"📡 [WEATHER RESPONSE] Status: {response.status}")
                logger.info(f"📡 [WEATHER RESPONSE] Status: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    print(f"📊 [WEATHER DATA] Raw response received")
                    logger.info(f"📊 [WEATHER DATA] Raw response keys: {list(data.keys())}")
                    
                    # Parse current weather
                    current = data["current"]
                    location = data["location"]
                    
                    print(f"📍 [WEATHER LOCATION] {location['name']}, {location['country']}")
                    print(f"🌡️ [WEATHER CURRENT] {current['temp_c']}°C, {current['condition']['text']}")
                    logger.info(f"📍 [WEATHER LOCATION] {location}")
                    logger.info(f"🌡️ [WEATHER CURRENT] {current}")
                    
                    # Build simplified response for Cerebras
                    current_temp = int(current["temp_c"])
                    current_condition = current["condition"]["text"].lower()
                    feels_like = int(current["feelslike_c"])
                    humidity = current["humidity"]
                    wind_speed = current["wind_kph"]
                    
                    result = f"Weather in {location['name']}, {location['country']}: Currently {current_temp}°C, {current_condition}. Feels like {feels_like}°C. Humidity {humidity}%, wind {wind_speed} km/h."
                    
                    print(f"✅ [WEATHER SUCCESS] Final result: {result}")
                    logger.info(f"✅ [WEATHER SUCCESS] Weather data retrieved successfully for {city}")
                    logger.info(f"✅ [WEATHER FINAL] {result}")
                    print("=" * 80)
                    return result
                    
                elif response.status == 400:
                    error_msg = f"Could not find weather information for '{city}'. Please check the city name."
                    print(f"❌ [WEATHER ERROR 400] {error_msg}")
                    logger.error(f"❌ [WEATHER ERROR 400] {error_msg}")
                    print("=" * 80)
                    return error_msg
                else:
                    error_msg = "Having trouble accessing the weather service right now."
                    print(f"❌ [WEATHER ERROR {response.status}] {error_msg}")
                    logger.error(f"❌ [WEATHER ERROR {response.status}] {error_msg}")
                    print("=" * 80)
                    return error_msg
                    
    except Exception as e:
        error_msg = f"Encountered an issue while getting weather for {city}. Please try again."
        print(f"💥 [WEATHER EXCEPTION] {str(e)}")
        logger.error(f"💥 [WEATHER EXCEPTION] Weather API error for {city}: {e}")
        logger.exception("Full weather exception traceback:")
        print("=" * 80)
        return error_msg


@function_tool()
async def search_web(
    context: RunContext,
    query: str
) -> str:
    """
    Search the web using Tavily AI Search API
    
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
        error_msg = "Cannot search the web - the search service is not properly configured."
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
            "search_depth": "basic",
            "include_answer": True,
            "include_images": False,
            "include_raw_content": False,
            "max_results": 3,
            "include_domains": [],
            "exclude_domains": []
        }
        
        print(f"🌐 [SEARCH API] Calling URL: {url}")
        logger.info(f"🌐 [SEARCH API] URL: {url}")
        
        async with aiohttp.ClientSession() as session:
            print("🔄 [SEARCH HTTP] Making HTTP request...")
            logger.info("🔄 [SEARCH HTTP] Making HTTP request...")
            
            async with session.post(url, json=payload, headers=headers) as response:
                print(f"📡 [SEARCH RESPONSE] Status: {response.status}")
                logger.info(f"📡 [SEARCH RESPONSE] Status: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    print(f"📊 [SEARCH DATA] Raw response received")
                    logger.info(f"📊 [SEARCH DATA] Raw response keys: {list(data.keys())}")
                    
                    # Get AI-generated answer if available
                    if data.get("answer"):
                        answer = data['answer']
                        print(f"🤖 [SEARCH ANSWER] Found AI answer")
                        logger.info(f"🤖 [SEARCH ANSWER] {answer}")
                        
                        # Simplified result for Cerebras
                        result = f"Search results for '{query}': {answer}"
                        
                        # Add top source for credibility
                        if data.get("results") and len(data["results"]) > 0:
                            top_result = data["results"][0]
                            title = top_result.get("title", "")
                            if title and len(title) < 100:
                                result += f" Source: {title}."
                    
                    # Fallback to search results if no answer
                    elif data.get("results") and len(data["results"]) > 0:
                        print(f"📄 [SEARCH FALLBACK] No AI answer, using search results")
                        top_result = data["results"][0]
                        title = top_result.get("title", "")
                        snippet = top_result.get("content", "")
                        
                        if snippet:
                            # Limit snippet length for voice
                            snippet = snippet[:200] + "..." if len(snippet) > 200 else snippet
                            result = f"Search results for '{query}': {title}. {snippet}"
                        else:
                            result = f"Found results for '{query}' but limited details available."
                    
                    else:
                        result = f"Searched for '{query}' but found limited information. Try a more specific search."
                        print(f"⚠️ [SEARCH WARNING] No results found")
                        logger.warning(f"⚠️ [SEARCH WARNING] No results found for '{query}'")
                    
                    print(f"✅ [SEARCH SUCCESS] Result ready")
                    logger.info(f"✅ [SEARCH SUCCESS] Web search completed successfully for: {query}")
                    logger.info(f"✅ [SEARCH FINAL] {result}")
                    print("=" * 80)
                    return result
                    
                elif response.status == 401:
                    error_msg = "Having authentication issues with the search service."
                    print(f"❌ [SEARCH ERROR 401] {error_msg}")
                    logger.error(f"❌ [SEARCH ERROR 401] {error_msg}")
                    print("=" * 80)
                    return error_msg
                elif response.status == 429:
                    error_msg = "Reached the search limit for now. Please try again later."
                    print(f"❌ [SEARCH ERROR 429] {error_msg}")
                    logger.error(f"❌ [SEARCH ERROR 429] {error_msg}")
                    print("=" * 80)
                    return error_msg
                else:
                    error_msg = "Having trouble with the search service right now."
                    print(f"❌ [SEARCH ERROR {response.status}] {error_msg}")
                    logger.error(f"❌ [SEARCH ERROR {response.status}] {error_msg}")
                    print("=" * 80)
                    return error_msg
                    
    except Exception as e:
        error_msg = f"Encountered an issue while searching for '{query}'. Please try again."
        print(f"💥 [SEARCH EXCEPTION] {str(e)}")
        logger.error(f"💥 [SEARCH EXCEPTION] Web search error for '{query}': {e}")
        logger.exception("Full search exception traceback:")
        print("=" * 80)
        return error_msg


@function_tool()    
async def send_email(
    context: RunContext,
    to_email: str,
    subject: str,
    message: str
) -> str:
    """
    Send an email through Gmail (simplified version for Cerebras compatibility)
    
    Args:
        to_email: Recipient email address
        subject: Email subject line
        message: Email body content
    """
    logger.info("="*50)
    logger.info("STARTING EMAIL SEND PROCESS")
    logger.info(f"To: {to_email}")
    logger.info(f"Subject: {subject}")
    logger.info(f"Message: {message[:100]}...")
    
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
            f.write(f"Subject: {subject}\n")
            f.write(f"Date: {timestamp}\n")
            f.write(f"\nMessage:\n{full_message}\n")
            f.write("="*30 + "\n")
        
        logger.info(f"Demo email saved to {demo_filename}")
        
        success_msg = f"Email simulated successfully to {to_email}. Demo file saved as {demo_filename}."
        
        logger.info(success_msg)
        logger.info("="*50)
        
        return success_msg
    
    try:
        # Email provider configuration (simplified to Gmail only for Cerebras)
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        email_user = os.getenv("GMAIL_USER")
        email_password = os.getenv("GMAIL_APP_PASSWORD")
        
        logger.info(f"Email user: {email_user}")
        logger.info(f"Password exists: {'Yes' if email_password else 'No'}")
        
        if not email_user or not email_password:
            error_msg = "Cannot send email - Gmail credentials are not configured properly."
            logger.error(error_msg)
            return error_msg
        
        # Validate email addresses
        if "@" not in to_email:
            error_msg = f"The email address '{to_email}' doesn't look valid."
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
        logger.info(f"Sending email to {to_email}...")
        text = msg.as_string()
        send_result = server.sendmail(email_user, [to_email], text)
        
        logger.info(f"Send result: {send_result}")
        
        server.quit()
        logger.info("SMTP connection closed")
        
        success_msg = f"Email sent successfully to {to_email}."
        
        logger.info(success_msg)
        logger.info("="*50)
        
        return success_msg
        
    except smtplib.SMTPAuthenticationError as e:
        error_msg = "Having trouble with email authentication. Please check the Gmail credentials."
        logger.error(f"Gmail authentication failed: {str(e)}")
        return error_msg
        
    except smtplib.SMTPRecipientsRefused as e:
        error_msg = f"The email address {to_email} was refused. It may not be valid."
        logger.error(f"Recipients refused: {str(e)}")
        return error_msg
        
    except smtplib.SMTPException as e:
        error_msg = "Encountered an SMTP error while sending the email."
        logger.error(f"SMTP error occurred: {str(e)}")
        return error_msg
        
    except Exception as e:
        error_msg = "An unexpected error occurred while sending the email."
        logger.error(f"Unexpected error sending email: {str(e)}")
        logger.exception("Full traceback:")
        return error_msg


# Дополнительная функция для тестирования совместимости
@function_tool()
async def test_cerebras(
    context: RunContext,
    test_message: str
) -> str:
    """
    Simple test function for Cerebras compatibility
    
    Args:
        test_message: Any test message
    """
    logger.info(f"🧪 [TEST CEREBRAS] Received: {test_message}")
    result = f"Cerebras test successful! You said: {test_message}"
    logger.info(f"🧪 [TEST CEREBRAS] Returning: {result}")
    return result