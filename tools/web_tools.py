"""
Web Tools Module - Инструменты для работы с веб-ресурсами

Этот модуль содержит все инструменты для работы с интернетом:
- search_web: Поиск в интернете через Tavily AI API
- validate_web_tools: Проверка доступности веб-сервисов
"""

import asyncio
import logging
import aiohttp
import os
from typing import Dict, Any, Optional
from livekit.agents import function_tool, RunContext

# -------------------- Logging Setup --------------------
logger = logging.getLogger("web-tools")

# -------------------- Web Services Configuration --------------------
TAVILY_API_URL = "https://api.tavily.com/search"
USER_AGENT = "LiveKit-Web-Agent/1.0"

# Настройки поиска по умолчанию
DEFAULT_SEARCH_CONFIG = {
    "search_depth": "basic",      # basic или advanced
    "include_answer": True,       # Получать AI-сгенерированный ответ
    "include_images": False,      # Не нужны изображения для голоса
    "include_raw_content": False, # Не нужен полный контент
    "max_results": 3,             # Лимит результатов для голосового ответа
    "include_domains": [],        # Без ограничений по доменам
    "exclude_domains": []         # Без исключений доменов
}

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
    
    Returns:
        str: Search results or error message
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
        # Подготавливаем payload для Tavily API
        payload = {
            "api_key": tavily_api_key,
            "query": query.strip(),
            **DEFAULT_SEARCH_CONFIG
        }
        
        headers = {
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT
        }
        
        print(f"🌐 [SEARCH API] Calling URL: {TAVILY_API_URL}")
        print(f"🌐 [SEARCH QUERY] '{query}' with config: {DEFAULT_SEARCH_CONFIG}")
        logger.info(f"🌐 [SEARCH API] URL: {TAVILY_API_URL}, query: '{query}'")
        
        async with aiohttp.ClientSession() as session:
            print("🔄 [SEARCH HTTP] Making HTTP request...")
            logger.info("🔄 [SEARCH HTTP] Making HTTP request...")
            
            async with session.post(
                TAVILY_API_URL, 
                json=payload, 
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=20)
            ) as response:
                
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
                    error_text = await response.text()
                    error_msg = "I'm having trouble with the search service right now, sir."
                    print(f"❌ [SEARCH ERROR {response.status}] {error_msg}")
                    logger.error(f"❌ [SEARCH ERROR {response.status}] Response: {error_text[:200]}")
                    print("=" * 80)
                    return error_msg
                    
    except asyncio.TimeoutError:
        error_msg = f"Search request timed out. Please try again with a simpler query."
        print(f"⏰ [SEARCH TIMEOUT] {error_msg}")
        logger.error(f"⏰ [SEARCH TIMEOUT] Search timed out for '{query}'")
        print("=" * 80)
        return error_msg
        
    except aiohttp.ClientError as e:
        error_msg = f"Failed to connect to search service. Please check your connection and try again."
        print(f"🌐 [SEARCH CONNECTION ERROR] {str(e)}")
        logger.error(f"🌐 [SEARCH CONNECTION ERROR] {str(e)}")
        print("=" * 80)
        return error_msg
        
    except Exception as e:
        error_msg = f"I encountered an issue while searching for '{query}', sir. Please try again."
        print(f"💥 [SEARCH EXCEPTION] {str(e)}")
        logger.error(f"💥 [SEARCH EXCEPTION] Web search error for '{query}': {e}")
        logger.exception("Full search exception traceback:")
        print("=" * 80)
        return error_msg

# -------------------- Web Tools Validation --------------------
async def validate_web_tools() -> Dict[str, Any]:
    """
    Validate web tools and their configuration
    
    Returns:
        dict: Status of web tools and services
    """
    results = {
        "timestamp": asyncio.get_event_loop().time(),
        "search_web": False,
        "tavily_api": {
            "key_configured": False,
            "service_accessible": False
        }
    }
    
    logger.info("🔍 [WEB VALIDATION] Validating web tools...")
    
    # Проверяем наличие Tavily API ключа
    tavily_key = os.getenv("TAVILY_API_KEY")
    results["tavily_api"]["key_configured"] = bool(tavily_key)
    
    if tavily_key:
        # Тестируем доступность Tavily API с простым запросом
        try:
            test_payload = {
                "api_key": tavily_key,
                "query": "test query",
                "search_depth": "basic",
                "max_results": 1,
                "include_answer": False
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    TAVILY_API_URL,
                    json=test_payload,
                    headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    
                    if response.status in [200, 429]:  # 429 = rate limit, но сервис работает
                        results["tavily_api"]["service_accessible"] = True
                        results["search_web"] = True
                        logger.info("✅ [WEB VALIDATION] Tavily API is accessible")
                    else:
                        logger.error(f"❌ [WEB VALIDATION] Tavily API returned status {response.status}")
                        
        except Exception as e:
            logger.error(f"❌ [WEB VALIDATION] Tavily API test failed: {e}")
    else:
        logger.warning("⚠️ [WEB VALIDATION] Tavily API key not configured")
    
    logger.info(f"📊 [WEB VALIDATION] Results: {results}")
    return results

# -------------------- Web Tools Information --------------------
def get_web_tools_info() -> Dict[str, Any]:
    """
    Get information about available web tools
    
    Returns:
        dict: Information about all web tools
    """
    return {
        "module": "web_tools",
        "version": "1.0.0",
        "services": {
            "tavily_search": {
                "name": "Tavily AI Search",
                "url": TAVILY_API_URL,
                "description": "AI-powered web search with smart answers",
                "key_required": True,
                "env_var": "TAVILY_API_KEY"
            }
        },
        "tools": {
            "search_web": {
                "description": "Search the web using Tavily AI",
                "parameters": ["query"],
                "config": DEFAULT_SEARCH_CONFIG,
                "status": "active"
            }
        },
        "configuration": {
            "default_search_config": DEFAULT_SEARCH_CONFIG,
            "user_agent": USER_AGENT
        }
    }

# -------------------- Advanced Web Tools (Future) --------------------
@function_tool()
async def fetch_webpage(
    context: RunContext,
    url: str,
    extract_text: bool = True
) -> str:
    """
    Fetch and extract content from a webpage (placeholder for future implementation)
    
    Args:
        url: URL to fetch
        extract_text: Whether to extract text content only
    
    Returns:
        str: Webpage content or error message
    """
    logger.info(f"🌐 [FETCH WEBPAGE] Would fetch: {url} (extract_text: {extract_text})")
    
    # Пока что заглушка - в будущем здесь будет реальная реализация
    placeholder_msg = f"Webpage fetching tool is not yet implemented. Would fetch content from {url}."
    
    print(f"⚠️ [WEB PLACEHOLDER] {placeholder_msg}")
    return placeholder_msg

# -------------------- Module Exports --------------------
__all__ = [
    # Основные инструменты
    'search_web',
    'fetch_webpage',  # пока заглушка
    
    # Валидация и управление
    'validate_web_tools',
    'get_web_tools_info',
    
    # Конфигурация
    'TAVILY_API_URL',
    'DEFAULT_SEARCH_CONFIG',
    'USER_AGENT',
]

# -------------------- Module Testing --------------------
if __name__ == "__main__":
    print("🛠️ [WEB TOOLS] Module Information:")
    info = get_web_tools_info()
    print(f"   📦 Module: {info['module']} v{info['version']}")
    print(f"   🔧 Tools: {len(info['tools'])}")
    
    for tool_name, tool_info in info['tools'].items():
        print(f"      • {tool_name}: {tool_info['status']}")
    
    print(f"   🌐 Services: {len(info['services'])}")
    for service_name, service_info in info['services'].items():
        print(f"      • {service_name}: {service_info['description']}")
    
    # Тестируем веб-инструменты
    async def test_module():
        print("\n🧪 [TESTING] Testing web tools...")
        
        # Валидация всех инструментов
        validation_results = await validate_web_tools()
        
        print(f"   🔍 Search Web: {'✅ Working' if validation_results['search_web'] else '❌ Failed'}")
        print(f"   🔑 Tavily API Key: {'✅ Found' if validation_results['tavily_api']['key_configured'] else '❌ Missing'}")
        print(f"   🌐 Tavily Service: {'✅ Accessible' if validation_results['tavily_api']['service_accessible'] else '❌ Failed'}")
        
        # Если все настроено - делаем тестовый поиск
        if validation_results['search_web']:
            print("\n🔍 [TEST SEARCH] Running test search...")
            # Тестовый поиск можно раскомментировать для реальной проверки
            # test_result = await search_web(None, "test search")
            # print(f"   📄 Result: {test_result[:100]}...")
        
    asyncio.run(test_module())