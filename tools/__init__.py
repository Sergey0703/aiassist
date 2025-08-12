"""
N8N Tools Package - Модульная система инструментов для LiveKit агента

Этот пакет содержит все инструменты для голосового агента, организованные по категориям:
- n8n_tools: Инструменты интеграции с n8n workflows
- n8n_trade_tools: Торговая аналитика через n8n
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
    "communication": [send_email, send_notification_n8n], 
    "information": [search_web],
    "n8n_integrated": [get_weather_n8n, get_trade_results_n8n, send_notification_n8n],
    "web_services": [search_web, send_email],
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
        "version": "1.1.0",
        "active_tools": len(AVAILABLE_TOOLS),
        "development_tools": len(DEVELOPMENT_TOOLS),
        "categories": list(TOOL_CATEGORIES.keys()),
        "tools_by_category": {
            category: [tool.__name__ for tool in tools] 
            for category, tools in TOOL_CATEGORIES.items()
        }
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
        
        for category, tools in package_info['tools_by_category'].items():
            logger.info(f"   📁 {category}: {', '.join(tools)}")
        
        print("🛠️ [TOOLS] N8N Tools package initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ [INIT] Failed to initialize tools package: {e}")
        print(f"❌ [TOOLS] Initialization failed: {e}")
        return False

# -------------------- Экспорт основных элементов --------------------
__all__ = [
    # Основные списки
    'AVAILABLE_TOOLS',
    'DEVELOPMENT_TOOLS', 
    'TOOL_CATEGORIES',
    
    # Функции управления
    'get_package_info',
    'validate_all_tools',
    'initialize_tools',
    
    # Отдельные инструменты (для прямого импорта)
    'get_weather_n8n',
    'get_trade_results_n8n',
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
    
    # Показываем инструменты по категориям
    for category, tools in info['tools_by_category'].items():
        print(f"      📁 {category}: {', '.join(tools)}")
    
    # Запускаем валидацию
    async def run_validation():
        print("\n🧪 [TESTING] Running full tool validation...")
        results = await validate_all_tools()
        print(f"📊 [RESULTS] Validation complete:")
        print(f"   ✅ Working: {results['summary']['working_tools']}")
        print(f"   ❌ Failed: {results['summary']['failed_tools']}")
        
        # Детали по модулям
        if results.get('n8n_tools'):
            weather_status = results['n8n_tools'].get('weather_service', False)
            print(f"   🌤️ N8N Weather: {'✅ Working' if weather_status else '❌ Failed'}")
            
        if results.get('n8n_trade_tools'):
            trade_status = results['n8n_trade_tools'].get('trade_analysis', False)
            print(f"   📊 N8N Trade: {'✅ Working' if trade_status else '❌ Failed'}")
            
        if results.get('web_tools'):
            web_status = results['web_tools'].get('search_web', False)
            print(f"   🔍 Web Search: {'✅ Working' if web_status else '❌ Failed'}")
            
        if results.get('email_tools'):
            email_status = results['email_tools'].get('send_email', False)
            print(f"   📧 Email Send: {'✅ Working' if email_status else '❌ Failed'}")
    
    asyncio.run(run_validation())
else:
    # При импорте - просто инициализируем
    initialize_tools()