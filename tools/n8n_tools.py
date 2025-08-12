"""
N8N Tools Module - Инструменты интеграции с n8n workflows

Этот модуль содержит все инструменты для работы с n8n автоматизацией:
- get_weather_n8n: Получение погоды через n8n workflow
- send_notification_n8n: Отправка уведомлений (в разработке)
- test_n8n_connection: Тестирование подключения к n8n
"""

import asyncio
import logging
import aiohttp
import json
from typing import Optional, Dict, Any
from livekit.agents import function_tool, RunContext

# -------------------- Logging Setup --------------------
logger = logging.getLogger("n8n-tools")

# -------------------- N8N Configuration --------------------
N8N_BASE_URL = "https://auto2025system.duckdns.org"
N8N_WEATHER_URL = f"{N8N_BASE_URL}/webhook/smart-weather"

# Будущие endpoints для других n8n workflows
N8N_ENDPOINTS = {
    "weather": f"{N8N_BASE_URL}/webhook/smart-weather",
    "notifications": f"{N8N_BASE_URL}/webhook/smart-notifications",  # будущий
    "analytics": f"{N8N_BASE_URL}/webhook/smart-analytics",          # будущий
    "email": f"{N8N_BASE_URL}/webhook/smart-email",                  # будущий
}

# -------------------- N8N Weather Tool --------------------
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
            "timestamp": asyncio.get_event_loop().time(),
            "source": "voice_agent"
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

# -------------------- N8N Notification Tool (Future) --------------------
@function_tool()
async def send_notification_n8n(
    context: RunContext,
    message: str,
    channel: str = "general",
    priority: str = "normal",
    notification_type: str = "info"
) -> str:
    """
    Send notification through n8n workflow (placeholder for future implementation)
    
    Args:
        message: Notification message
        channel: Channel to send to (e.g., "general", "alerts", "team")
        priority: Priority level ("low", "normal", "high", "urgent")
        notification_type: Type of notification ("info", "warning", "error", "success")
    
    Returns:
        str: Success or error message
    """
    logger.info(f"📢 [N8N NOTIFICATION] Would send: '{message}' to {channel} (priority: {priority}, type: {notification_type})")
    
    # Пока что возвращаем заглушку - в будущем здесь будет реальная реализация
    placeholder_msg = (
        f"Notification tool is not yet implemented. "
        f"Would send '{message}' to {channel} channel with {priority} priority as {notification_type} notification."
    )
    
    print(f"⚠️ [N8N PLACEHOLDER] {placeholder_msg}")
    return placeholder_msg

# -------------------- N8N Connection Testing --------------------
async def test_n8n_connection() -> bool:
    """
    Test if n8n weather workflow is accessible
    
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
            "test": True,
            "source": "validation"
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

# -------------------- N8N Workflow Management --------------------
async def get_n8n_workflow_status() -> Dict[str, Any]:
    """
    Get status of all n8n workflows
    
    Returns:
        dict: Status information for all configured workflows
    """
    status = {
        "timestamp": asyncio.get_event_loop().time(),
        "base_url": N8N_BASE_URL,
        "workflows": {}
    }
    
    logger.info("🔍 [N8N STATUS] Checking workflow statuses...")
    
    # Проверяем каждый настроенный endpoint
    for workflow_name, endpoint_url in N8N_ENDPOINTS.items():
        try:
            if workflow_name == "weather":
                # Для погоды используем специальный тест
                is_working = await test_n8n_connection()
                status["workflows"][workflow_name] = {
                    "url": endpoint_url,
                    "status": "active" if is_working else "failed",
                    "implemented": True
                }
            else:
                # Для остальных - пока что заглушки
                status["workflows"][workflow_name] = {
                    "url": endpoint_url,
                    "status": "not_implemented",
                    "implemented": False
                }
                
        except Exception as e:
            logger.error(f"❌ [N8N STATUS] Error checking {workflow_name}: {e}")
            status["workflows"][workflow_name] = {
                "url": endpoint_url,
                "status": "error",
                "error": str(e),
                "implemented": False
            }
    
    logger.info(f"📊 [N8N STATUS] Status check complete: {len(status['workflows'])} workflows")
    return status

# -------------------- N8N Tools Information --------------------
def get_n8n_tools_info() -> Dict[str, Any]:
    """
    Get information about available n8n tools
    
    Returns:
        dict: Information about all n8n tools
    """
    return {
        "module": "n8n_tools",
        "version": "1.0.0",
        "base_url": N8N_BASE_URL,
        "tools": {
            "get_weather_n8n": {
                "description": "Get weather information via n8n workflow",
                "endpoint": N8N_WEATHER_URL,
                "status": "active",
                "parameters": ["city", "units"]
            },
            "send_notification_n8n": {
                "description": "Send notifications via n8n (placeholder)",
                "endpoint": N8N_ENDPOINTS.get("notifications"),
                "status": "placeholder", 
                "parameters": ["message", "channel", "priority", "notification_type"]
            }
        },
        "endpoints": N8N_ENDPOINTS
    }

# -------------------- Module Exports --------------------
__all__ = [
    # Основные инструменты
    'get_weather_n8n',
    'send_notification_n8n',
    
    # Тестирование и управление
    'test_n8n_connection',
    'get_n8n_workflow_status',
    'get_n8n_tools_info',
    
    # Конфигурация
    'N8N_BASE_URL',
    'N8N_WEATHER_URL',
    'N8N_ENDPOINTS',
]

# -------------------- Module Testing --------------------
if __name__ == "__main__":
    print("🛠️ [N8N TOOLS] Module Information:")
    info = get_n8n_tools_info()
    print(f"   📦 Module: {info['module']} v{info['version']}")
    print(f"   🌐 Base URL: {info['base_url']}")
    print(f"   🔧 Tools: {len(info['tools'])}")
    
    for tool_name, tool_info in info['tools'].items():
        print(f"      • {tool_name}: {tool_info['status']}")
    
    # Тестируем подключение
    async def test_module():
        print("\n🧪 [TESTING] Testing n8n connections...")
        
        # Тест основного подключения
        weather_status = await test_n8n_connection()
        print(f"   🌤️ Weather service: {'✅ Working' if weather_status else '❌ Failed'}")
        
        # Полный статус всех workflow
        print("\n📊 [STATUS] Full workflow status:")
        full_status = await get_n8n_workflow_status()
        for workflow, details in full_status['workflows'].items():
            status_emoji = "✅" if details['status'] == "active" else "⚠️" if details['status'] == "not_implemented" else "❌"
            print(f"   {status_emoji} {workflow}: {details['status']}")
    
    asyncio.run(test_module())