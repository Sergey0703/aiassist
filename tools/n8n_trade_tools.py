"""
N8N Trade Results Tool - Инструмент анализа торговых результатов

Этот инструмент подключается к n8n workflow TradeResults для анализа:
- ТОП-3 самых продаваемых продуктов
- 3 наименее продаваемых продукта
- Данные за последние N дней из Airtable
"""

import asyncio
import logging
import aiohttp
import json
from typing import Optional, Dict, Any
from livekit.agents import function_tool, RunContext

# -------------------- Logging Setup --------------------
logger = logging.getLogger("trade-results-tool")

# -------------------- N8N Trade Results Configuration --------------------
N8N_TRADE_RESULTS_URL = "https://auto2025system.duckdns.org/webhook/76f40ffb-2d6a-4f67-85f9-8f9b20ae6a7e"

# -------------------- Trade Results Tool --------------------
@function_tool()
async def get_trade_results_n8n(
    context: RunContext,
    days_ago: int = 30,
    analysis_type: str = "both"
) -> str:
    """
    Get trade results analysis through n8n workflow from Airtable data
    
    Args:
        days_ago: Number of days to analyze (default 30, max 365)
        analysis_type: Type of analysis ("top", "worst", "both")
    
    Returns:
        str: Trade analysis results or error message
    """
    logger.info(f"📊 [TRADE RESULTS] Getting trade analysis for last {days_ago} days (type: {analysis_type})")
    print(f"📊 [TRADE RESULTS] Analyzing sales data for last {days_ago} days...")
    
    try:
        # Валидация параметров
        days_ago = max(1, min(days_ago, 365))  # От 1 до 365 дней
        analysis_type = analysis_type.lower()
        if analysis_type not in ["top", "worst", "both"]:
            analysis_type = "both"
        
        # Подготавливаем данные для n8n workflow
        payload = {
            "daysAgo": days_ago,
            "analysisType": analysis_type,
            "user_id": "livekit_user",
            "timestamp": asyncio.get_event_loop().time(),
            "source": "voice_agent"
        }
        
        logger.info(f"🌐 [N8N TRADE REQUEST] Sending to {N8N_TRADE_RESULTS_URL}")
        logger.info(f"🌐 [N8N TRADE PAYLOAD] {payload}")
        
        # Делаем HTTP запрос к n8n workflow
        async with aiohttp.ClientSession() as session:
            async with session.post(
                N8N_TRADE_RESULTS_URL,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "LiveKit-N8N-TradeAgent/1.0"
                },
                timeout=aiohttp.ClientTimeout(total=20)
            ) as response:
                
                logger.info(f"📡 [N8N TRADE RESPONSE] Status: {response.status}")
                
                if response.status == 200:
                    result = await response.json()
                    
                    logger.info(f"📊 [N8N TRADE DATA] Response length: {len(str(result))}")
                    logger.info(f"📊 [N8N TRADE KEYS] Response keys: {list(result.keys()) if isinstance(result, dict) else 'List response'}")
                    
                    # Обрабатываем результат анализа
                    analysis_result = _format_trade_analysis(result, days_ago, analysis_type)
                    
                    print(f"✅ [N8N TRADE SUCCESS] Analysis completed for {days_ago} days")
                    logger.info(f"✅ [N8N TRADE SUCCESS] Trade analysis retrieved successfully")
                    
                    return analysis_result
                        
                else:
                    error_text = await response.text()
                    error_msg = f"Trade analysis service returned status {response.status}. Please try again."
                    logger.error(f"❌ [N8N TRADE HTTP ERROR] Status {response.status}: {error_text[:200]}")
                    print(f"❌ [N8N TRADE HTTP ERROR] Status {response.status}")
                    return error_msg
                    
    except asyncio.TimeoutError:
        error_msg = "Trade analysis request timed out. The service might be busy, please try again."
        logger.error(f"⏰ [N8N TRADE TIMEOUT] Trade analysis timed out for {days_ago} days")
        print(f"⏰ [N8N TRADE TIMEOUT] Request timed out")
        return error_msg
        
    except aiohttp.ClientError as e:
        error_msg = f"Failed to connect to trade analysis service. Please check your connection and try again."
        logger.error(f"🌐 [N8N TRADE CONNECTION ERROR] {str(e)}")
        print(f"🌐 [N8N TRADE CONNECTION ERROR] {str(e)}")
        return error_msg
        
    except json.JSONDecodeError as e:
        error_msg = f"Trade analysis service returned invalid data. Please try again."
        logger.error(f"📄 [N8N TRADE JSON ERROR] {str(e)}")
        print(f"📄 [N8N TRADE JSON ERROR] Invalid response format")
        return error_msg
        
    except Exception as e:
        error_msg = f"An unexpected error occurred while getting trade analysis for {days_ago} days. Please try again."
        logger.error(f"💥 [N8N TRADE EXCEPTION] Trade error for '{days_ago}' days: {e}")
        logger.exception("Full n8n trade exception traceback:")
        print(f"💥 [N8N TRADE EXCEPTION] {str(e)}")
        return error_msg

# -------------------- ИСПРАВЛЕННАЯ функция форматирования --------------------
def _format_trade_analysis(data: Any, days_ago: int, analysis_type: str) -> str:
    """
    Format trade analysis results for voice response - краткий summary с топ-3 и худшие-3
    
    Args:
        data: Raw response from n8n workflow (массив объектов)
        days_ago: Number of days analyzed
        analysis_type: Type of analysis requested
    
    Returns:
        str: Formatted analysis for voice output
    """
    try:
        logger.info(f"📝 [TRADE FORMAT] Formatting trade analysis data")
        logger.info(f"📝 [TRADE FORMAT] Data type: {type(data)}, length: {len(data) if isinstance(data, list) else 'not list'}")
        
        # Проверяем что получили список
        if not isinstance(data, list) or len(data) == 0:
            logger.warning(f"⚠️ [TRADE FORMAT] Expected list but got: {type(data)}")
            return f"Trade analysis for the last {days_ago} days returned no data. There might be no sales in this period."
        
        top_data = None
        worst_data = None
        
        # Извлекаем данные по типам из массива
        logger.info(f"📝 [TRADE FORMAT] Processing {len(data)} items from response")
        for i, item in enumerate(data):
            logger.info(f"📝 [TRADE FORMAT] Item {i}: {type(item)} - {item}")
            
            if isinstance(item, dict):
                # Извлекаем данные из обертки "json" (n8n упаковывает данные в json ключ)
                json_data = item.get("json", {})
                item_type = json_data.get("type", "unknown")
                item_products = json_data.get("products", [])
                
                logger.info(f"📝 [TRADE FORMAT] Found {item_type} with {len(item_products)} products")
                
                if item_type == "TOP":
                    top_data = item_products
                elif item_type == "WORST":
                    worst_data = item_products
        
        # Логируем что извлекли
        logger.info(f"📝 [TRADE FORMAT] Extracted TOP: {len(top_data) if top_data else 0} products")
        logger.info(f"📝 [TRADE FORMAT] Extracted WORST: {len(worst_data) if worst_data else 0} products")
        
        # Если нет данных после извлечения
        if not top_data and not worst_data:
            logger.warning("⚠️ [TRADE FORMAT] No TOP or WORST data found after parsing")
            return f"No sales data found for the last {days_ago} days."
        
        # Если есть данные, но они пустые
        if (top_data is not None and len(top_data) == 0) and (worst_data is not None and len(worst_data) == 0):
            logger.warning("⚠️ [TRADE FORMAT] TOP and WORST arrays are empty")
            return f"No sales data found for the last {days_ago} days."
        
        # ==================== КРАТКИЙ SUMMARY ДЛЯ ГОЛОСА ====================
        summary_parts = []
        
        # Определяем лидера и аутсайдера для краткого summary
        leader_info = ""
        worst_info = ""
        
        if top_data and len(top_data) > 0:
            leader = top_data[0]
            leader_name = leader.get("productName", "Unknown")
            leader_sales = leader.get("totalSold", 0)
            leader_info = f"Top seller: {leader_name} with {leader_sales:.1f} units"
            logger.info(f"📈 [TRADE FORMAT] Leader: {leader_name} - {leader_sales}")
        
        if worst_data and len(worst_data) > 0:
            worst = worst_data[0]
            worst_name = worst.get("productName", "Unknown")
            worst_sales = worst.get("totalSold", 0)
            worst_info = f"Worst performer: {worst_name} with {worst_sales:.1f} units"
            logger.info(f"📉 [TRADE FORMAT] Worst: {worst_name} - {worst_sales}")
        
        # Общая статистика для summary
        all_products = []
        if top_data:
            all_products.extend(top_data)
        if worst_data:
            all_products.extend(worst_data)
            
        unique_products = {}
        for product in all_products:
            name = product.get("productName", "Unknown")
            sales = product.get("totalSold", 0)
            if name not in unique_products:
                unique_products[name] = sales
            else:
                unique_products[name] = max(unique_products[name], sales)
        
        total_products_count = len(unique_products)
        total_sales_volume = sum(unique_products.values())
        
        logger.info(f"📊 [TRADE FORMAT] Statistics: {total_products_count} products, {total_sales_volume} total sales")
        
        # Собираем краткий summary
        summary_parts = [f"Sales analysis for last {days_ago} days:"]
        if leader_info:
            summary_parts.append(leader_info)
        if worst_info:
            summary_parts.append(worst_info)
        summary_parts.append(f"Analysis covers {total_products_count} products with total {total_sales_volume:.1f} units sold")
        
        summary = " ".join(summary_parts) + "."
        
        # ==================== ДЕТАЛЬНОЕ ОЗВУЧИВАНИЕ ТОП-3 И ХУДШИХ-3 ====================
        voice_details = []
        
        # Озвучиваем TOP-3 продукта
        if analysis_type in ["top", "both"] and top_data and len(top_data) > 0:
            voice_details.append("Top 3 selling products:")
            for i, product in enumerate(top_data[:3], 1):  # Только первые 3
                name = product.get("productName", "Unknown")
                total = product.get("totalSold", 0)
                voice_details.append(f"{i}. {name}: {total:.1f} units")
                logger.info(f"📈 [TRADE FORMAT] TOP {i}: {name} - {total}")
        
        # Озвучиваем ХУДШИЕ-3 продукта
        if analysis_type in ["worst", "both"] and worst_data and len(worst_data) > 0:
            voice_details.append("3 worst selling products:")
            for i, product in enumerate(worst_data[:3], 1):  # Только первые 3
                name = product.get("productName", "Unknown")
                total = product.get("totalSold", 0)
                voice_details.append(f"{i}. {name}: {total:.1f} units")
                logger.info(f"📉 [TRADE FORMAT] WORST {i}: {name} - {total}")
        
        # ==================== ФИНАЛЬНЫЙ РЕЗУЛЬТАТ ДЛЯ ГОЛОСА ====================
        if voice_details:
            final_result = summary + " " + " ".join(voice_details)
        else:
            final_result = summary
        
        logger.info(f"📝 [TRADE FORMAT] Final voice result: {final_result[:150]}...")
        logger.info(f"✅ [TRADE FORMAT] Successfully formatted trade analysis")
        
        return final_result
        
    except Exception as e:
        logger.error(f"💥 [TRADE FORMAT ERROR] Error formatting trade data: {e}")
        logger.exception("Full formatting exception traceback:")
        
        # Возвращаем отладочную информацию в случае ошибки
        debug_info = f"Trade analysis completed for {days_ago} days, but formatting failed. "
        debug_info += f"Data type: {type(data)}, "
        if isinstance(data, list):
            debug_info += f"Length: {len(data)}, "
            if len(data) > 0:
                debug_info += f"First item type: {type(data[0])}"
        
        return debug_info

# -------------------- Trade Results Testing --------------------
async def test_trade_results_connection() -> bool:
    """
    Test if n8n trade results workflow is accessible
    
    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        logger.info(f"🧪 [N8N TRADE TEST] Testing connection to {N8N_TRADE_RESULTS_URL}")
        
        test_payload = {
            "daysAgo": 7,  # Тест за последние 7 дней
            "analysisType": "both",
            "user_id": "test_user",
            "test": True,
            "source": "validation"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                N8N_TRADE_RESULTS_URL,
                json=test_payload,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "LiveKit-N8N-TradeAgent/1.0-Test"
                },
                timeout=aiohttp.ClientTimeout(total=15)
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    # Проверяем структуру ответа
                    if isinstance(result, list) and len(result) > 0:
                        logger.info("✅ [N8N TRADE TEST] Connection successful")
                        print("✅ [N8N TRADE TEST] Trade analysis service is working")
                        return True
                    else:
                        logger.warning(f"⚠️ [N8N TRADE TEST] Service responded but returned unexpected format")
                        print("⚠️ [N8N TRADE TEST] Service responded but returned unexpected data")
                        return False
                else:
                    logger.error(f"❌ [N8N TRADE TEST] HTTP error {response.status}")
                    print(f"❌ [N8N TRADE TEST] HTTP error {response.status}")
                    return False
                    
    except asyncio.TimeoutError:
        logger.error("⏰ [N8N TRADE TEST] Connection test timed out")
        print("⏰ [N8N TRADE TEST] Connection timed out")
        return False
        
    except aiohttp.ClientError as e:
        logger.error(f"🌐 [N8N TRADE TEST] Connection error: {e}")
        print(f"🌐 [N8N TRADE TEST] Connection failed: {e}")
        return False
        
    except Exception as e:
        logger.error(f"💥 [N8N TRADE TEST] Connection test failed: {e}")
        print(f"💥 [N8N TRADE TEST] Connection failed: {e}")
        return False

# -------------------- Trade Results Information --------------------
def get_trade_results_info() -> Dict[str, Any]:
    """
    Get information about trade results tool
    
    Returns:
        dict: Information about trade results tool
    """
    return {
        "tool": "get_trade_results_n8n",
        "description": "Get sales analysis from Airtable via n8n workflow",
        "endpoint": N8N_TRADE_RESULTS_URL,
        "workflow_name": "TradeResults",
        "parameters": {
            "days_ago": {
                "type": "int",
                "default": 30,
                "range": "1-365",
                "description": "Number of days to analyze"
            },
            "analysis_type": {
                "type": "str", 
                "default": "both",
                "options": ["top", "worst", "both"],
                "description": "Type of analysis to perform"
            }
        },
        "returns": {
            "summary": "Brief overview with leader and worst performer",
            "top_3": "Top 3 selling products with units sold",
            "worst_3": "3 worst selling products with units sold", 
            "statistics": "Total products and sales volume"
        },
        "data_source": "Airtable StockMovements table",
        "status": "active"
    }

# -------------------- Module Testing --------------------
if __name__ == "__main__":
    print("📊 [TRADE RESULTS TOOL] Trade Analysis Tool Information:")
    info = get_trade_results_info()
    print(f"   🛠️ Tool: {info['tool']}")
    print(f"   📝 Description: {info['description']}")
    print(f"   🌐 Endpoint: {info['endpoint']}")
    print(f"   📋 Workflow: {info['workflow_name']}")
    print(f"   📊 Data Source: {info['data_source']}")
    
    # Тестируем подключение
    async def test_module():
        print("\n🧪 [TESTING] Testing trade results connection...")
        
        # Тест подключения
        trade_status = await test_trade_results_connection()
        print(f"   📊 Trade Analysis: {'✅ Working' if trade_status else '❌ Failed'}")
        
        # Если подключение работает - можно сделать тестовый запрос
        if trade_status:
            print("\n📈 [TEST ANALYSIS] Running test analysis...")
            # Раскомментировать для реального теста:
            # test_result = await get_trade_results_n8n(None, 7, "both")
            # print(f"   📄 Result: {test_result[:200]}...")
    
    asyncio.run(test_module())