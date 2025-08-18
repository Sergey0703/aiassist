"""
N8N Calendar Tools Module - Инструменты для работы с календарными данными

Этот модуль содержит все инструменты для работы с календарем через n8n:
- get_calendar_data_n8n: Получение событий календаря через n8n workflow
- test_calendar_connection: Тестирование подключения к n8n календарю
"""

import asyncio
import logging
import aiohttp
import json
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from livekit.agents import function_tool, RunContext

# -------------------- Logging Setup --------------------
logger = logging.getLogger("calendar-tools")

# -------------------- N8N Calendar Configuration --------------------
N8N_BASE_URL = "https://auto2025system.duckdns.org"
N8N_CALENDAR_URL = f"{N8N_BASE_URL}/webhook/smart-calendar"

# Возможные временные диапазоны для календаря
CALENDAR_TIME_RANGES = {
    "today": 0,
    "tomorrow": 1,
    "this_week": 7,
    "next_week": 14,
    "this_month": 30
}

# -------------------- N8N Calendar Tool --------------------
@function_tool()
async def get_calendar_data_n8n(
    context: RunContext,
    time_range: str = "today",
    calendar_type: str = "all",
    max_events: int = 10
) -> str:
    """
    Get calendar events through n8n workflow
    
    Args:
        time_range: Time range to fetch ("today", "tomorrow", "this_week", "next_week", "this_month")
        calendar_type: Type of calendar events ("all", "meetings", "personal", "work")
        max_events: Maximum number of events to return (1-20)
    
    Returns:
        str: Calendar events information or error message
    """
    logger.info(f"📅 [N8N CALENDAR] Getting calendar data for '{time_range}' (type: {calendar_type}, max: {max_events})")
    print(f"📅 [N8N CALENDAR] Fetching calendar events for {time_range}...")
    
    try:
        # Валидация параметров
        time_range = time_range.lower()
        if time_range not in CALENDAR_TIME_RANGES:
            time_range = "today"
        
        calendar_type = calendar_type.lower()
        if calendar_type not in ["all", "meetings", "personal", "work"]:
            calendar_type = "all"
            
        max_events = max(1, min(max_events, 20))  # От 1 до 20 событий
        
        # Подготавливаем данные для n8n workflow
        payload = {
            "action": "calendar",
            "timeRange": time_range,
            "calendarType": calendar_type,
            "maxEvents": max_events,
            "user_id": "livekit_user",
            "timestamp": asyncio.get_event_loop().time(),
            "source": "voice_agent"
        }
        
        logger.info(f"🌐 [N8N CALENDAR REQUEST] Sending to {N8N_CALENDAR_URL}")
        logger.info(f"🌐 [N8N CALENDAR PAYLOAD] {payload}")
        
        # Делаем HTTP запрос к n8n workflow
        async with aiohttp.ClientSession() as session:
            async with session.post(
                N8N_CALENDAR_URL,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "LiveKit-N8N-CalendarAgent/1.0"
                },
                timeout=aiohttp.ClientTimeout(total=20)
            ) as response:
                
                logger.info(f"📡 [N8N CALENDAR RESPONSE] Status: {response.status}")
                
                if response.status == 200:
                    result = await response.json()
                    
                    logger.info(f"📊 [N8N CALENDAR DATA] Success: {result.get('success', False)}")
                    logger.info(f"📊 [N8N CALENDAR MESSAGE] Response type: {type(result)}")
                    
                    if result.get('success', False):
                        # Получаем события из ответа
                        events = result.get('events', [])
                        calendar_summary = result.get('message', '')
                        
                        # Форматируем результат для голосового ответа
                        formatted_result = _format_calendar_response(events, time_range, calendar_type, calendar_summary)
                        
                        print(f"✅ [N8N CALENDAR SUCCESS] Found {len(events)} events for {time_range}")
                        logger.info(f"✅ [N8N CALENDAR SUCCESS] Calendar data retrieved for {time_range}")
                        
                        return formatted_result
                    else:
                        error_message = result.get('message', 'Failed to get calendar information.')
                        logger.error(f"❌ [N8N CALENDAR ERROR] {error_message}")
                        print(f"❌ [N8N CALENDAR ERROR] {error_message}")
                        return f"Calendar service error: {error_message}"
                        
                else:
                    error_text = await response.text()
                    error_msg = f"Calendar service returned status {response.status}. Please try again."
                    logger.error(f"❌ [N8N CALENDAR HTTP ERROR] Status {response.status}: {error_text[:200]}")
                    print(f"❌ [N8N CALENDAR HTTP ERROR] Status {response.status}")
                    return error_msg
                    
    except asyncio.TimeoutError:
        error_msg = "Calendar request timed out. The service might be busy, please try again."
        logger.error(f"⏰ [N8N CALENDAR TIMEOUT] Calendar request timed out for {time_range}")
        print(f"⏰ [N8N CALENDAR TIMEOUT] Request timed out")
        return error_msg
        
    except aiohttp.ClientError as e:
        error_msg = f"Failed to connect to calendar service. Please check your connection and try again."
        logger.error(f"🌐 [N8N CALENDAR CONNECTION ERROR] {str(e)}")
        print(f"🌐 [N8N CALENDAR CONNECTION ERROR] {str(e)}")
        return error_msg
        
    except json.JSONDecodeError as e:
        error_msg = f"Calendar service returned invalid data. Please try again."
        logger.error(f"📄 [N8N CALENDAR JSON ERROR] {str(e)}")
        print(f"📄 [N8N CALENDAR JSON ERROR] Invalid response format")
        return error_msg
        
    except Exception as e:
        error_msg = f"An unexpected error occurred while getting calendar information for {time_range}. Please try again."
        logger.error(f"💥 [N8N CALENDAR EXCEPTION] Calendar error for '{time_range}': {e}")
        logger.exception("Full n8n calendar exception traceback:")
        print(f"💥 [N8N CALENDAR EXCEPTION] {str(e)}")
        return error_msg

# -------------------- Calendar Response Formatting --------------------
def _format_calendar_response(events: list, time_range: str, calendar_type: str, summary: str = "") -> str:
    """
    Format calendar events for voice response
    
    Args:
        events: List of calendar events from n8n
        time_range: Time range requested
        calendar_type: Type of calendar events
        summary: Optional summary message from n8n
    
    Returns:
        str: Formatted calendar response for voice output
    """
    try:
        logger.info(f"📝 [CALENDAR FORMAT] Formatting {len(events)} events for {time_range}")
        
        # Если нет событий
        if not events or len(events) == 0:
            empty_msg = f"You have no {calendar_type} events scheduled for {time_range}."
            if summary:
                empty_msg = f"{summary} {empty_msg}"
            logger.info(f"📝 [CALENDAR FORMAT] No events found")
            return empty_msg
        
        # Начинаем формировать ответ
        response_parts = []
        
        # Добавляем summary если есть
        if summary:
            response_parts.append(summary)
        
        # Основная информация о количестве событий
        event_count = len(events)
        if event_count == 1:
            response_parts.append(f"You have 1 event scheduled for {time_range}:")
        else:
            response_parts.append(f"You have {event_count} events scheduled for {time_range}:")
        
        # Обрабатываем каждое событие
        for i, event in enumerate(events[:10], 1):  # Лимит 10 событий для голоса
            try:
                title = event.get("title", "Untitled Event")
                start_time = event.get("startTime", "")
                end_time = event.get("endTime", "")
                location = event.get("location", "")
                attendees = event.get("attendees", [])
                
                logger.info(f"📝 [CALENDAR EVENT {i}] {title} at {start_time}")
                
                # Форматируем время
                time_info = ""
                if start_time:
                    # Пытаемся распарсить и отформатировать время
                    time_info = _format_event_time(start_time, end_time)
                
                # Собираем информацию о событии
                event_parts = [f"{i}. {title}"]
                
                if time_info:
                    event_parts.append(f"at {time_info}")
                
                if location:
                    event_parts.append(f"in {location}")
                
                if attendees and len(attendees) > 0:
                    attendee_count = len(attendees)
                    if attendee_count == 1:
                        event_parts.append("with 1 attendee")
                    else:
                        event_parts.append(f"with {attendee_count} attendees")
                
                response_parts.append(" ".join(event_parts))
                
            except Exception as e:
                logger.error(f"❌ [CALENDAR FORMAT ERROR] Error formatting event {i}: {e}")
                response_parts.append(f"{i}. Event (details unavailable)")
        
        # Если событий больше 10, добавляем информацию об этом
        if len(events) > 10:
            additional_count = len(events) - 10
            response_parts.append(f"Plus {additional_count} more events.")
        
        final_response = " ".join(response_parts)
        
        logger.info(f"📝 [CALENDAR FORMAT] Successfully formatted {len(events)} events")
        logger.info(f"📝 [CALENDAR FORMAT] Final response length: {len(final_response)}")
        
        return final_response
        
    except Exception as e:
        logger.error(f"💥 [CALENDAR FORMAT ERROR] Error formatting calendar response: {e}")
        logger.exception("Full calendar formatting exception traceback:")
        
        # Возвращаем базовую информацию в случае ошибки форматирования
        fallback_msg = f"Calendar information retrieved for {time_range} but formatting failed. "
        if events:
            fallback_msg += f"Found {len(events)} events."
        else:
            fallback_msg += "No events found."
        
        return fallback_msg

# -------------------- Event Time Formatting --------------------
def _format_event_time(start_time: str, end_time: str = "") -> str:
    """
    Format event time for voice output
    
    Args:
        start_time: Event start time string
        end_time: Event end time string (optional)
    
    Returns:
        str: Formatted time string for voice
    """
    try:
        # Пытаемся различные форматы времени
        time_formats = [
            "%Y-%m-%dT%H:%M:%S",      # ISO format
            "%Y-%m-%d %H:%M:%S",      # Standard format
            "%H:%M",                  # Time only
            "%H:%M:%S",              # Time with seconds
            "%Y-%m-%d",              # Date only
        ]
        
        parsed_start = None
        for fmt in time_formats:
            try:
                parsed_start = datetime.strptime(start_time, fmt)
                break
            except ValueError:
                continue
        
        if not parsed_start:
            # Если не удалось распарсить, возвращаем как есть
            return start_time
        
        # Форматируем для голоса
        if parsed_start.date() == datetime.now().date():
            # Сегодня - показываем только время
            time_str = parsed_start.strftime("%H:%M")
        else:
            # Другой день - показываем дату и время
            time_str = parsed_start.strftime("%B %d at %H:%M")
        
        # Добавляем время окончания если есть
        if end_time:
            try:
                parsed_end = None
                for fmt in time_formats:
                    try:
                        parsed_end = datetime.strptime(end_time, fmt)
                        break
                    except ValueError:
                        continue
                
                if parsed_end:
                    end_time_str = parsed_end.strftime("%H:%M")
                    time_str += f" to {end_time_str}"
            except:
                pass
        
        return time_str
        
    except Exception as e:
        logger.error(f"❌ [TIME FORMAT ERROR] Error formatting time {start_time}: {e}")
        return start_time

# -------------------- Calendar Connection Testing --------------------
async def test_calendar_connection() -> bool:
    """
    Test if n8n calendar workflow is accessible
    
    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        logger.info(f"🧪 [N8N CALENDAR TEST] Testing connection to {N8N_CALENDAR_URL}")
        
        test_payload = {
            "action": "calendar",
            "timeRange": "today",
            "calendarType": "all",
            "maxEvents": 1,
            "user_id": "test_user",
            "test": True,
            "source": "validation"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                N8N_CALENDAR_URL,
                json=test_payload,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "LiveKit-N8N-CalendarAgent/1.0-Test"
                },
                timeout=aiohttp.ClientTimeout(total=15)
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    if result.get('success', False):
                        logger.info("✅ [N8N CALENDAR TEST] Connection successful")
                        print("✅ [N8N CALENDAR TEST] Calendar service is working")
                        return True
                    else:
                        logger.warning(f"⚠️ [N8N CALENDAR TEST] Service responded but failed: {result.get('message', 'Unknown error')}")
                        print("⚠️ [N8N CALENDAR TEST] Service responded but returned an error")
                        return False
                else:
                    logger.error(f"❌ [N8N CALENDAR TEST] HTTP error {response.status}")
                    print(f"❌ [N8N CALENDAR TEST] HTTP error {response.status}")
                    return False
                    
    except asyncio.TimeoutError:
        logger.error("⏰ [N8N CALENDAR TEST] Connection test timed out")
        print("⏰ [N8N CALENDAR TEST] Connection timed out")
        return False
        
    except aiohttp.ClientError as e:
        logger.error(f"🌐 [N8N CALENDAR TEST] Connection error: {e}")
        print(f"🌐 [N8N CALENDAR TEST] Connection failed: {e}")
        return False
        
    except Exception as e:
        logger.error(f"💥 [N8N CALENDAR TEST] Connection test failed: {e}")
        print(f"💥 [N8N CALENDAR TEST] Connection failed: {e}")
        return False

# -------------------- Calendar Status Information --------------------
async def get_calendar_status() -> Dict[str, Any]:
    """
    Get status of calendar service
    
    Returns:
        dict: Status information for calendar service
    """
    status = {
        "timestamp": asyncio.get_event_loop().time(),
        "service_url": N8N_CALENDAR_URL,
        "service_name": "N8N Calendar Service",
        "available_ranges": list(CALENDAR_TIME_RANGES.keys()),
        "calendar_types": ["all", "meetings", "personal", "work"],
        "max_events_limit": 20,
        "status": "unknown"
    }
    
    logger.info("🔍 [N8N CALENDAR STATUS] Checking calendar service status...")
    
    try:
        is_working = await test_calendar_connection()
        status["status"] = "active" if is_working else "failed"
        status["last_test"] = datetime.now().isoformat()
        
    except Exception as e:
        logger.error(f"❌ [N8N CALENDAR STATUS] Error checking status: {e}")
        status["status"] = "error"
        status["error"] = str(e)
    
    logger.info(f"📊 [N8N CALENDAR STATUS] Status: {status['status']}")
    return status

# -------------------- Calendar Tools Information --------------------
def get_calendar_tools_info() -> Dict[str, Any]:
    """
    Get information about available calendar tools
    
    Returns:
        dict: Information about all calendar tools
    """
    return {
        "module": "n8n_calendar_tools",
        "version": "1.0.0",
        "service_url": N8N_CALENDAR_URL,
        "tools": {
            "get_calendar_data_n8n": {
                "description": "Get calendar events via n8n workflow",
                "endpoint": N8N_CALENDAR_URL,
                "status": "active",
                "parameters": {
                    "time_range": {
                        "type": "str",
                        "default": "today",
                        "options": list(CALENDAR_TIME_RANGES.keys()),
                        "description": "Time range to fetch events"
                    },
                    "calendar_type": {
                        "type": "str",
                        "default": "all",
                        "options": ["all", "meetings", "personal", "work"],
                        "description": "Type of calendar events to fetch"
                    },
                    "max_events": {
                        "type": "int",
                        "default": 10,
                        "range": "1-20",
                        "description": "Maximum number of events to return"
                    }
                }
            }
        },
        "features": [
            "Multiple time ranges support",
            "Calendar type filtering",
            "Event details formatting",
            "Voice-optimized responses",
            "Attendee information",
            "Location details",
            "Time formatting"
        ],
        "time_ranges": CALENDAR_TIME_RANGES,
        "supported_calendars": ["Google Calendar", "Outlook", "Apple Calendar", "Custom calendars"]
    }

# -------------------- Module Exports --------------------
__all__ = [
    # Основной инструмент
    'get_calendar_data_n8n',
    
    # Тестирование и управление
    'test_calendar_connection',
    'get_calendar_status',
    'get_calendar_tools_info',
    
    # Конфигурация
    'N8N_CALENDAR_URL',
    'CALENDAR_TIME_RANGES',
]

# -------------------- Module Testing --------------------
if __name__ == "__main__":
    print("📅 [CALENDAR TOOLS] Module Information:")
    info = get_calendar_tools_info()
    print(f"   📦 Module: {info['module']} v{info['version']}")
    print(f"   🌐 Service URL: {info['service_url']}")
    print(f"   🔧 Tools: {len(info['tools'])}")
    
    for tool_name, tool_info in info['tools'].items():
        print(f"      • {tool_name}: {tool_info['status']}")
    
    print(f"   📊 Time Ranges: {', '.join(info['time_ranges'].keys())}")
    print(f"   📋 Calendar Types: all, meetings, personal, work")
    print(f"   ✨ Features: {len(info['features'])}")
    
    # Тестируем календарный сервис
    async def test_module():
        print("\n🧪 [TESTING] Testing calendar service...")
        
        # Тест подключения
        calendar_status = await test_calendar_connection()
        print(f"   📅 Calendar Service: {'✅ Working' if calendar_status else '❌ Failed'}")
        
        # Полный статус сервиса
        print("\n📊 [STATUS] Calendar service status:")
        full_status = await get_calendar_status()
        print(f"   📅 Status: {full_status['status']}")
        print(f"   🌐 URL: {full_status['service_url']}")
        print(f"   📊 Available Ranges: {', '.join(full_status['available_ranges'])}")
        print(f"   📋 Calendar Types: {', '.join(full_status['calendar_types'])}")
        
        # Если сервис работает - можно сделать тестовый запрос
        if calendar_status:
            print("\n📅 [TEST QUERY] Calendar service is ready for queries!")
            print("   💬 Try: 'What's on my calendar today?'")
            print("   💬 Try: 'Show me this week's meetings'")
            print("   💬 Try: 'What's my schedule for tomorrow?'")
    
    asyncio.run(test_module())