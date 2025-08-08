import logging
import os
import smtplib
import aiohttp
from email.mime.multipart import MIMEMultipart  
from email.mime.text import MIMEText
from typing import Optional
from datetime import datetime
from livekit.agents import function_tool, RunContext

# Настройка логирования для инструментов
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("aitools.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("aitools")


@function_tool()
async def get_weather(
    context: RunContext,
    city: str,
    days: int = 1
) -> str:
    """
    Get current weather and forecast for a city using WeatherAPI.com
    
    Args:
        city: City name (e.g., "London", "New York", "Moscow")
        days: Number of days for forecast (1-3, default 1 for current weather only)
    """
    print("=" * 80)
    print(f"🌤️ [WEATHER TOOL STARTED] Getting weather for '{city}', {days} days")
    logger.info(f"🌤️ [WEATHER TOOL STARTED] city='{city}', days={days}")
    
    # Get WeatherAPI key from environment
    weather_api_key = os.getenv("WEATHER_API_KEY")
    print(f"🔑 [WEATHER API KEY] {'Found' if weather_api_key else 'NOT FOUND'}")
    logger.info(f"🔑 [WEATHER API KEY] {'Found' if weather_api_key else 'NOT FOUND'}")
    
    if not weather_api_key:
        error_msg = "I'm afraid I cannot get weather information - the weather service is not configured properly, sir."
        print(f"❌ [WEATHER ERROR] {error_msg}")
        logger.error(f"❌ [WEATHER ERROR] {error_msg}")
        print("=" * 80)
        return error_msg
    
    # Limit days to avoid API issues
    days = min(max(days, 1), 3)
    print(f"📅 [WEATHER DAYS] Adjusted to {days} days")
    logger.info(f"📅 [WEATHER DAYS] Adjusted to {days} days")
    
    try:
        # WeatherAPI.com endpoint
        url = f"http://api.weatherapi.com/v1/forecast.json"
        params = {
            "key": weather_api_key,
            "q": city,
            "days": days,
            "aqi": "no",  # No air quality data
            "alerts": "no"  # No weather alerts
        }
        
        print(f"🌐 [WEATHER API] Calling URL: {url}")
        print(f"🌐 [WEATHER PARAMS] {params}")
        logger.info(f"🌐 [WEATHER API] URL: {url}, params: {params}")
        
        async with aiohttp.ClientSession() as session:
            print("🔄 [WEATHER HTTP] Making HTTP request...")
            logger.info("🔄 [WEATHER HTTP] Making HTTP request...")
            
            async with session.get(url, params=params) as response:
                print(f"📡 [WEATHER RESPONSE] Status: {response.status}")
                logger.info(f"📡 [WEATHER RESPONSE] Status: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    print(f"📊 [WEATHER DATA] Raw response length: {len(str(data))}")
                    logger.info(f"📊 [WEATHER DATA] Raw response keys: {list(data.keys())}")
                    
                    # Parse current weather
                    current = data["current"]
                    location = data["location"]
                    forecast_days = data["forecast"]["forecastday"]
                    
                    print(f"📍 [WEATHER LOCATION] {location['name']}, {location['country']}")
                    print(f"🌡️ [WEATHER CURRENT] {current['temp_c']}°C, {current['condition']['text']}")
                    logger.info(f"📍 [WEATHER LOCATION] {location}")
                    logger.info(f"🌡️ [WEATHER CURRENT] {current}")
                    
                    # Build response
                    result = f"Weather in {location['name']}, {location['country']}: "
                    
                    # Current weather
                    current_temp = int(current["temp_c"])
                    current_condition = current["condition"]["text"].lower()
                    
                    result += f"Currently {current_temp} degrees Celsius, {current_condition}."
                    print(f"✅ [WEATHER RESULT] Current: {current_temp}°C, {current_condition}")
                    
                    # Forecast if requested
                    if days > 1:
                        result += " Forecast: "
                        print(f"📊 [WEATHER FORECAST] Processing {len(forecast_days)} days")
                        
                        for i, day_data in enumerate(forecast_days):
                            if i == 0:  # Skip today (we already have current)
                                continue
                                
                            day_info = day_data["day"]
                            date = day_data["date"]
                            
                            max_temp = int(day_info["maxtemp_c"])
                            min_temp = int(day_info["mintemp_c"])
                            condition = day_info["condition"]["text"].lower()
                            rain_chance = day_info["daily_chance_of_rain"]
                            snow_chance = day_info["daily_chance_of_snow"]
                            
                            print(f"📅 [WEATHER DAY {i+1}] {date}: {min_temp}-{max_temp}°C, {condition}, rain:{rain_chance}%, snow:{snow_chance}%")
                            
                            # Determine day name
                            day_name = "tomorrow" if i == 1 else f"day {i + 1}"
                            
                            result += f" {day_name.capitalize()}: {min_temp} to {max_temp} degrees, {condition}"
                            
                            # Add precipitation info
                            if snow_chance > 30:
                                result += f" with {snow_chance}% chance of snow"
                            elif rain_chance > 30:
                                result += f" with {rain_chance}% chance of rain"
                            
                            result += "."
                    
                    print(f"✅ [WEATHER SUCCESS] Final result: {result}")
                    logger.info(f"✅ [WEATHER SUCCESS] Weather data retrieved successfully for {city}")
                    logger.info(f"✅ [WEATHER FINAL] {result}")
                    print("=" * 80)
                    return result
                    
                elif response.status == 400:
                    error_msg = f"I couldn't find weather information for '{city}', sir. Please check the city name."
                    print(f"❌ [WEATHER ERROR 400] {error_msg}")
                    logger.error(f"❌ [WEATHER ERROR 400] {error_msg}")
                    print("=" * 80)
                    return error_msg
                else:
                    error_msg = "I'm having trouble accessing the weather service right now, sir."
                    print(f"❌ [WEATHER ERROR {response.status}] {error_msg}")
                    logger.error(f"❌ [WEATHER ERROR {response.status}] {error_msg}")
                    print("=" * 80)
                    return error_msg
                    
    except Exception as e:
        error_msg = f"I encountered an issue while getting weather for {city}, sir. Please try again."
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