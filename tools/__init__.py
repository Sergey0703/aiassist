"""
N8N Tools Package - Модульная система инструментов для LiveKit агента

Этот пакет содержит все инструменты для голосового агента, организованные по категориям:
- n8n_tools: Инструменты интеграции с n8n workflows
- n8n_trade_tools: Торговая аналитика через n8n
- n8n_calendar_tools: Работа с календарем через n8n
- web_tools: Веб-поиск и работа с интернет-ресурсами  
- email_tools: Отправка email и уведомлений
- file_tools: Работа с файлами и документами (в будущем)
- ai_tools: AI-инструменты и обработка текста (в будущем)
"""

import logging
import asyncio
from typing import List, Dict, Any

# Настройка логирования для всех инструментов
logger = logging.getLogger("tools")

# -------------------- Импорты инструментов --------------------
# N8N инструменты
from .n8n_tools import (
    get_weather_n8n,
    test_n8n_connection,
    send_notification_n8n  # пока заглушка
)

# N8N торговые инструменты
from .n8n_trade_tools import (
    get_trade_results_n8n,
    test_trade_results_connection
)

# N8N календарные инструменты
from .n8n_calendar_tools import (
    get_calendar_data_n8n,
    test_calendar_connection
)

# Веб инструменты  
from .web_tools import (
    search_web,
    validate_web_tools
)

# Email инструменты
from .email_tools import (
    send_email,
    validate_email_tools
)

# -------------------- Главный список активных инструментов --------------------
AVAILABLE_TOOLS = [
    # N8N интеграции
    get_weather_n8n,        # Погода через n8n workflow
    get_trade_results_n8n,  # Торговая аналитика через n8n
    get_calendar_data_n8n,  # Календарные данные через n8n
    
    # Веб сервисы
    search_web,             # Поиск через Tavily AI
    
    # Коммуникации  
    send_email,             # Отправка email через SMTP
    
    # send_notification_n8n, # Пока заглушка - раскомментировать когда готов
]

# -------------------- Инструменты в разработке --------------------
DEVELOPMENT_TOOLS = [
    send_notification_n8n,  # N8N уведомления - в разработке
]

# -------------------- Категории инструментов --------------------
TOOL_CATEGORIES = {
    "weather": [get_weather_n8n],
    "analytics": [get_trade_results_n8n],
    "calendar": [get_calendar_data_n8n],
    "communication": [send_email, send_notification_n8n], 
    "information": [search_web],
    "n8n_integrated": [get_weather_n8n, get_trade_results_n8n, get_calendar_data_n8n, send_notification_n8n],
    "web_services": [search_web, send_email],
    "productivity": [get_calendar_data_n8n, send_email],
}

# -------------------- Информация о пакете --------------------
def get_package_info() -> Dict[str, Any]:
    """
    Получить информацию о пакете инструментов
    
    Returns:
        Dict: Информация о всех доступных инструментах
    """
    return {
        "package": "N8N Tools",
        "version": "1.2.0",  # Обновили версию для календаря
        "active_tools": len(AVAILABLE_TOOLS),
        "development_tools": len(DEVELOPMENT_TOOLS),
        "categories": list(TOOL_CATEGORIES.keys()),
        "tools_by_category": {
            category: [tool.__name__ for tool in tools] 
            for category, tools in TOOL_CATEGORIES.items()
        },
        "new_features": [
            "Calendar integration via n8n",
            "Enhanced productivity tools",
            "Multi-calendar support"
        ]
    }

# -------------------- Валидация всех инструментов --------------------
async def validate_all_tools() -> Dict[str, Any]:
    """
    Проверить работоспособность всех инструментов
    
    Returns:
        Dict: Статус всех инструментов и их настроек
    """
    results = {
        "timestamp": asyncio.get_event_loop().time(),
        "n8n_tools": {},
        "n8n_trade_tools": {},
        "n8n_calendar_tools": {},  # Новая секция для календаря
        "web_tools": {},
        "email_tools": {},
        "summary": {
            "total_tools": len(AVAILABLE_TOOLS),
            "working_tools": 0,
            "failed_tools": 0
        }
    }
    
    logger.info("🔍 [VALIDATION] Starting tool validation...")
    
    # Валидируем N8N основные инструменты
    try:
        n8n_status = await test_n8n_connection()
        results["n8n_tools"]["weather_service"] = n8n_status
        if n8n_status:
            results["summary"]["working_tools"] += 1
        else:
            results["summary"]["failed_tools"] += 1
    except Exception as e:
        logger.error(f"❌ [VALIDATION] N8N validation failed: {e}")
        results["n8n_tools"]["weather_service"] = False
        results["summary"]["failed_tools"] += 1
    
    # Валидируем N8N торговые инструменты
    try:
        trade_status = await test_trade_results_connection()
        results["n8n_trade_tools"]["trade_analysis"] = trade_status
        if trade_status:
            results["summary"]["working_tools"] += 1
        else:
            results["summary"]["failed_tools"] += 1
    except Exception as e:
        logger.error(f"❌ [VALIDATION] N8N Trade validation failed: {e}")
        results["n8n_trade_tools"]["trade_analysis"] = False
        results["summary"]["failed_tools"] += 1
    
    # Валидируем N8N календарные инструменты
    try:
        calendar_status = await test_calendar_connection()
        results["n8n_calendar_tools"]["calendar_service"] = calendar_status
        if calendar_status:
            results["summary"]["working_tools"] += 1
        else:
            results["summary"]["failed_tools"] += 1
    except Exception as e:
        logger.error(f"❌ [VALIDATION] N8N Calendar validation failed: {e}")
        results["n8n_calendar_tools"]["calendar_service"] = False
        results["summary"]["failed_tools"] += 1
    
    # Валидируем веб инструменты
    try:
        web_status = await validate_web_tools()
        results["web_tools"].update(web_status)
        if web_status.get("search_web", False):
            results["summary"]["working_tools"] += 1
        else:
            results["summary"]["failed_tools"] += 1
    except Exception as e:
        logger.error(f"❌ [VALIDATION] Web tools validation failed: {e}")
        results["web_tools"]["search_web"] = False
        results["summary"]["failed_tools"] += 1
    
    # Валидируем email инструменты
    try:
        email_status = await validate_email_tools()
        results["email_tools"].update(email_status)
        if email_status.get("send_email", False):
            results["summary"]["working_tools"] += 1
        else:
            results["summary"]["failed_tools"] += 1
    except Exception as e:
        logger.error(f"❌ [VALIDATION] Email tools validation failed: {e}")
        results["email_tools"]["send_email"] = False
        results["summary"]["failed_tools"] += 1
    
    # Логируем результаты
    logger.info(f"✅ [VALIDATION] Complete: {results['summary']['working_tools']}/{results['summary']['total_tools']} tools working")
    
    return results

# -------------------- Быстрая проверка инструментов --------------------
async def quick_tools_check() -> Dict[str, bool]:
    """
    Быстрая проверка всех основных инструментов
    
    Returns:
        Dict: Быстрый статус каждого инструмента
    """
    quick_status = {}
    
    logger.info("⚡ [QUICK CHECK] Running quick tools validation...")
    
    # Проверяем каждый инструмент с таймаутом
    checks = [
        ("weather", test_n8n_connection()),
        ("trade_analysis", test_trade_results_connection()),
        ("calendar", test_calendar_connection()),
    ]
    
    for tool_name, check_coro in checks:
        try:
            result = await asyncio.wait_for(check_coro, timeout=5.0)
            quick_status[tool_name] = result
        except asyncio.TimeoutError:
            quick_status[tool_name] = False
            logger.warning(f"⏰ [QUICK CHECK] {tool_name} check timed out")
        except Exception as e:
            quick_status[tool_name] = False
            logger.error(f"❌ [QUICK CHECK] {tool_name} check failed: {e}")
    
    # Проверяем веб и email инструменты (упрощенно)
    try:
        import os
        quick_status["web_search"] = bool(os.getenv("TAVILY_API_KEY"))
        quick_status["email"] = bool(os.getenv("GMAIL_USER")) or bool(os.getenv("EMAIL_DEMO_MODE"))
    except:
        quick_status["web_search"] = False
        quick_status["email"] = False
    
    working_count = sum(1 for status in quick_status.values() if status)
    total_count = len(quick_status)
    
    logger.info(f"⚡ [QUICK CHECK] Complete: {working_count}/{total_count} tools working")
    
    return quick_status

# -------------------- Инициализация пакета --------------------
def initialize_tools() -> bool:
    """
    Инициализировать все инструменты и вывести информацию
    
    Returns:
        bool: True если инициализация успешна
    """
    try:
        logger.info("🛠️ [INIT] Initializing N8N Tools package...")
        
        package_info = get_package_info()
        
        logger.info(f"📦 [INIT] Package: {package_info['package']} v{package_info['version']}")
        logger.info(f"🔧 [INIT] Active tools: {package_info['active_tools']}")
        logger.info(f"⚗️ [INIT] Development tools: {package_info['development_tools']}")
        logger.info(f"📂 [INIT] Categories: {', '.join(package_info['categories'])}")
        
        # Показываем новые функции
        if package_info.get('new_features'):
            logger.info(f"✨ [INIT] New features: {', '.join(package_info['new_features'])}")
        
        for category, tools in package_info['tools_by_category'].items():
            logger.info(f"   📁 {category}: {', '.join(tools)}")
        
        print("🛠️ [TOOLS] N8N Tools package initialized successfully")
        print(f"   📦 Version: {package_info['version']}")
        print(f"   🔧 Active tools: {package_info['active_tools']}")
        print(f"   📂 Categories: {len(package_info['categories'])}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ [INIT] Failed to initialize tools package: {e}")
        print(f"❌ [TOOLS] Initialization failed: {e}")
        return False

# -------------------- Получение инструмента по имени --------------------
def get_tool_by_name(tool_name: str):
    """
    Получить инструмент по имени
    
    Args:
        tool_name: Имя инструмента
    
    Returns:
        function: Функция инструмента или None
    """
    tool_mapping = {
        "get_weather_n8n": get_weather_n8n,
        "get_trade_results_n8n": get_trade_results_n8n,
        "get_calendar_data_n8n": get_calendar_data_n8n,
        "search_web": search_web,
        "send_email": send_email,
        "send_notification_n8n": send_notification_n8n,
    }
    
    return tool_mapping.get(tool_name)

# -------------------- Получение инструментов по категории --------------------
def get_tools_by_category(category: str) -> List:
    """
    Получить все инструменты определенной категории
    
    Args:
        category: Название категории
    
    Returns:
        List: Список инструментов в категории
    """
    return TOOL_CATEGORIES.get(category, [])

# -------------------- Статистика использования инструментов --------------------
def get_tools_statistics() -> Dict[str, Any]:
    """
    Получить статистику по инструментам
    
    Returns:
        Dict: Статистика использования инструментов
    """
    return {
        "total_tools": len(AVAILABLE_TOOLS),
        "development_tools": len(DEVELOPMENT_TOOLS),
        "categories_count": len(TOOL_CATEGORIES),
        "n8n_tools": len([tool for tool in AVAILABLE_TOOLS if "n8n" in tool.__name__]),
        "web_tools": len([tool for tool in AVAILABLE_TOOLS if tool in [search_web]]),
        "communication_tools": len([tool for tool in AVAILABLE_TOOLS if tool in [send_email]]),
        "tool_names": [tool.__name__ for tool in AVAILABLE_TOOLS],
        "categories": list(TOOL_CATEGORIES.keys())
    }

# -------------------- Экспорт основных элементов --------------------
__all__ = [
    # Основные списки
    'AVAILABLE_TOOLS',
    'DEVELOPMENT_TOOLS', 
    'TOOL_CATEGORIES',
    
    # Функции управления
    'get_package_info',
    'validate_all_tools',
    'quick_tools_check',
    'initialize_tools',
    'get_tool_by_name',
    'get_tools_by_category',
    'get_tools_statistics',
    
    # Отдельные инструменты (для прямого импорта)
    'get_weather_n8n',
    'get_trade_results_n8n',
    'get_calendar_data_n8n',  # Новый календарный инструмент
    'search_web',
    'send_email',
    'send_notification_n8n',
]

# -------------------- Автоинициализация при импорте --------------------
if __name__ == "__main__":
    # Если запускаем напрямую - показываем информацию и тестируем
    print("🛠️ [N8N TOOLS] Package Information:")
    info = get_package_info()
    print(f"   📦 Package: {info['package']} v{info['version']}")
    print(f"   🔧 Active tools: {info['active_tools']}")
    print(f"   ⚗️ Development tools: {info['development_tools']}")
    print(f"   📂 Categories: {', '.join(info['categories'])}")
    
    # Показываем новые функции
    if info.get('new_features'):
        print(f"   ✨ New features: {', '.join(info['new_features'])}")
    
    # Показываем инструменты по категориям
    for category, tools in info['tools_by_category'].items():
        print(f"      📁 {category}: {', '.join(tools)}")
    
    # Показываем статистику
    print("\n📊 [STATISTICS] Tools Statistics:")
    stats = get_tools_statistics()
    print(f"   🔧 Total tools: {stats['total_tools']}")
    print(f"   🔗 N8N tools: {stats['n8n_tools']}")
    print(f"   🌐 Web tools: {stats['web_tools']}")
    print(f"   📧 Communication tools: {stats['communication_tools']}")
    
    # Запускаем быструю проверку
    async def run_quick_check():
        print("\n⚡ [QUICK CHECK] Running quick tool validation...")
        results = await quick_tools_check()
        print(f"📊 [RESULTS] Quick check complete:")
        
        for tool_name, status in results.items():
            status_emoji = "✅" if status else "❌"
            print(f"   {status_emoji} {tool_name}: {'Working' if status else 'Failed'}")
        
        working_count = sum(1 for status in results.values() if status)
        total_count = len(results)
        print(f"\n📈 [SUMMARY] {working_count}/{total_count} tools are working")
    
    # Запускаем полную валидацию
    async def run_full_validation():
        print("\n🧪 [TESTING] Running full tool validation...")
        results = await validate_all_tools()
        print(f"📊 [RESULTS] Validation complete:")
        print(f"   ✅ Working: {results['summary']['working_tools']}")
        print(f"   ❌ Failed: {results['summary']['failed_tools']}")
        
        # Детали по модулям
        print("\n📋 [DETAILS] Module details:")
        if results.get('n8n_tools'):
            weather_status = results['n8n_tools'].get('weather_service', False)
            print(f"   🌤️ N8N Weather: {'✅ Working' if weather_status else '❌ Failed'}")
            
        if results.get('n8n_trade_tools'):
            trade_status = results['n8n_trade_tools'].get('trade_analysis', False)
            print(f"   📊 N8N Trade: {'✅ Working' if trade_status else '❌ Failed'}")
            
        if results.get('n8n_calendar_tools'):
            calendar_status = results['n8n_calendar_tools'].get('calendar_service', False)
            print(f"   📅 N8N Calendar: {'✅ Working' if calendar_status else '❌ Failed'}")
            
        if results.get('web_tools'):
            web_status = results['web_tools'].get('search_web', False)
            print(f"   🔍 Web Search: {'✅ Working' if web_status else '❌ Failed'}")
            
        if results.get('email_tools'):
            email_status = results['email_tools'].get('send_email', False)
            print(f"   📧 Email Send: {'✅ Working' if email_status else '❌ Failed'}")
    
    # Выбираем тип проверки
    import sys
    if "--quick" in sys.argv:
        asyncio.run(run_quick_check())
    else:
        asyncio.run(run_full_validation())
else:
    # При импорте - просто инициализируем
    initialize_tools()