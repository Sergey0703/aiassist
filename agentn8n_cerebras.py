import asyncio
import logging
import os
import aiohttp
import json
from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    RunContext,
    WorkerOptions,
    cli,
    function_tool,
)
from livekit.plugins import openai, silero

# Импортируем старые инструменты поиска и email
from aitools import search_web, send_email

# -------------------- Setup --------------------
load_dotenv()

# Правильная настройка логирования как в примерах LiveKit
logger = logging.getLogger("n8n-assistant")
logger.setLevel(logging.INFO)

# Настройка форматтера для красивого вывода
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Консольный обработчик
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Файловый обработчик
file_handler = logging.FileHandler("agent_n8n.log", encoding='utf-8')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Получаем API ключи
openai_api_key = os.getenv("OPENAI_API_KEY")
cerebras_api_key = os.getenv("CEREBRAS_API_KEY")

if not openai_api_key:
    logger.error("OPENAI_API_KEY not found in environment variables")
    raise ValueError("OPENAI_API_KEY is required")

if not cerebras_api_key:
    logger.error("CEREBRAS_API_KEY not found in environment variables")
    raise ValueError("CEREBRAS_API_KEY is required")

# -------------------- n8n Integration --------------------
N8N_WEATHER_URL = "https://auto2025system.duckdns.org/webhook/smart-weather"

@function_tool()
async def get_weather_n8n(
    context: RunContext,
    city: str,
    units: str = "celsius"
) -> str:
    """
    Get weather information through n8n workflow.
    Use this tool when user asks about weather in any city.
    
    Args:
        city: City name (e.g., "London", "Paris", "Tokyo")
        units: Temperature units ("celsius" or "fahrenheit")
    
    Returns:
        Weather information as a formatted string
    """
    logger.info(f"🌤️ [N8N WEATHER] Getting weather for '{city}' in {units}")
    print(f"🌤️ [N8N WEATHER] Requesting weather for {city}...")
    
    try:
        # Подготавливаем данные для n8n в формате который ожидает workflow
        payload = {
            "action": "weather",
            "city": city,
            "units": units,
            "date": "today",
            "user_id": "livekit_user"
        }
        
        logger.info(f"🌐 [N8N REQUEST] Sending to {N8N_WEATHER_URL}")
        logger.info(f"🌐 [N8N PAYLOAD] {payload}")
        
        # Делаем HTTP запрос к n8n workflow
        async with aiohttp.ClientSession() as session:
            async with session.post(
                N8N_WEATHER_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
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
                        return error_message
                        
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
        
    except Exception as e:
        error_msg = f"An unexpected error occurred while getting weather information for {city}. Please try again."
        logger.error(f"💥 [N8N EXCEPTION] Weather error for '{city}': {e}")
        logger.exception("Full n8n weather exception traceback:")
        print(f"💥 [N8N EXCEPTION] {str(e)}")
        return error_msg

# -------------------- Test n8n Connection --------------------
async def test_n8n_connection():
    """Test if n8n workflow is accessible"""
    try:
        logger.info(f"🧪 [N8N TEST] Testing connection to {N8N_WEATHER_URL}")
        
        test_payload = {
            "action": "weather",
            "city": "London",
            "units": "celsius",
            "user_id": "test_user"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                N8N_WEATHER_URL,
                json=test_payload,
                headers={"Content-Type": "application/json"},
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
                    
    except Exception as e:
        logger.error(f"💥 [N8N TEST] Connection test failed: {e}")
        print(f"💥 [N8N TEST] Connection failed: {e}")
        return False

# -------------------- Agent Class --------------------
class N8NAssistant(Agent):
    """Голосовой помощник с n8n интеграцией для погоды + OpenAI инструменты для поиска и email"""
    
    def __init__(self):
        super().__init__(
            instructions=(
                "You are a helpful voice assistant with access to weather information, web search, and email sending. "
                "ALWAYS respond in English only, regardless of what language the user speaks. "
                "You understand all languages but respond ONLY in English. "
                "Do NOT mention the language issue - just answer naturally in English. "
                
                "For function calling tasks, only use the functions you have been provided with. "
                "When you summarize, make sure you've considered ALL previous instructions. "
                "When users ask about weather, use the get_weather_n8n tool ONCE and provide the exact information returned. "
                "When users ask for information you don't know, use the search_web tool ONCE to find current information. "
                "When users ask to send email, use the send_email tool ONCE with the information they provide. "
                "Do NOT make up information - only use data from your tools. "
                "Be clear, concise, and direct. "
                
                "IMPORTANT: After calling any function and getting a result, provide the information to the user immediately. "
                "Do NOT call the same function multiple times for the same request. "
                "One function call per user request is sufficient."
            ),
            # Комбинируем n8n погоду с OpenAI инструментами
            tools=[get_weather_n8n, search_web, send_email],
        )
        logger.info("N8N Assistant agent initialized with n8n weather, search, and email tools")

# -------------------- Entrypoint --------------------
async def entrypoint(ctx: JobContext):
    """Главная точка входа для N8N агента"""
    
    logger.info("🚀 Starting N8N Assistant entrypoint")
    
    # Тестируем подключение к n8n перед запуском
    print("🧪 [STARTUP] Testing n8n weather service...")
    n8n_working = await test_n8n_connection()
    
    if not n8n_working:
        print("⚠️ [WARNING] n8n weather service is not responding, but continuing anyway...")
        logger.warning("⚠️ [WARNING] n8n weather service test failed, but continuing...")
    
    # Подключаемся к комнате
    await ctx.connect()
    logger.info(f"✅ Connected to room: {ctx.room.name}")
    
    # Создаем агента
    agent = N8NAssistant()
    
    # ИСПРАВЛЕННАЯ сессия с правильными параметрами для function calling
    session = AgentSession(
        # VAD для детекции речи
        vad=silero.VAD.load(),
        
        # OpenAI STT (Whisper) - ПРИНУДИТЕЛЬНО ТОЛЬКО АНГЛИЙСКИЙ!
        stt=openai.STT(
            language="en",  # ПРИНУДИТЕЛЬНО английский - никакой автоопределения!
        ),
        
        # МИНИМАЛЬНЫЕ настройки: только поддерживаемые LiveKit параметры
        llm=openai.LLM(
            base_url="https://api.cerebras.ai/v1",
            api_key=cerebras_api_key,
            model="llama-3.3-70b",  # Доступная 70B модель из вашего списка
            temperature=0.5,  # Как в AutoGen примере
        ),
                
        # OpenAI TTS для озвучки
        tts=openai.TTS(
            voice="alloy",
            speed=1.0,
        ),
        
        # КРИТИЧЕСКИЕ настройки из AutoGen для предотвращения повторных вызовов
        max_tool_steps=1,  # Ограничиваем только одним шагом функций
        
        # Дополнительные настройки для стабильности
        allow_interruptions=True,
        min_endpointing_delay=0.5,  # Немного больше задержки для стабильности
        max_endpointing_delay=6.0,
    )
    
    logger.info("✅ Session created: Whisper STT (EN) + Cerebras Llama-3.3-70B (AutoGen settings) + TTS + N8N Weather + Search + Email")
    
    # ==========================================
    # ИСПРАВЛЕННЫЕ события с правильной обработкой результатов
    # ==========================================
    
    @session.on("user_input_transcribed")
    def on_user_input_transcribed(event):
        """Когда речь пользователя распознана STT"""
        transcript = getattr(event, 'transcript', 'No transcript')
        is_final = getattr(event, 'is_final', False)
        if is_final:
            logger.info(f"👤 [USER FINAL] {transcript}")
            print(f"\n👤 [USER] {transcript}")
        else:
            logger.debug(f"👤 [USER PARTIAL] {transcript}")
    
    @session.on("conversation_item_added")
    def on_conversation_item_added(event):
        """Когда элемент добавлен в историю чата (пользователь ИЛИ агент)"""
        item = getattr(event, 'item', None)
        if item:
            role = getattr(item, 'role', 'unknown')
            content = getattr(item, 'text_content', '') or str(getattr(item, 'content', ''))
            interrupted = getattr(item, 'interrupted', False)
            
            if role == "user":
                logger.info(f"💬 [CHAT USER] {content}")
                print(f"💬 [CHAT USER] {content}")
            elif role == "assistant":
                logger.info(f"💬 [CHAT ASSISTANT] {content}")
                print(f"💬 [CHAT ASSISTANT] {content}")
                print("-" * 60)
            
            if interrupted:
                logger.info(f"⚠️ [INTERRUPTED] {role} was interrupted")
    
    @session.on("speech_created")
    def on_speech_created(event):
        """Когда агент создал новую речь"""
        logger.info("🔊 [SPEECH CREATED] Agent is about to speak")
        print("🔊 [ASSISTANT] Creating speech...")
    
    @session.on("agent_state_changed")
    def on_agent_state_changed(event):
        """Когда состояние агента изменилось"""
        old_state = getattr(event, 'old_state', 'unknown')
        new_state = getattr(event, 'new_state', 'unknown')
        logger.info(f"🔄 [AGENT STATE] {old_state} -> {new_state}")
        print(f"🔄 [AGENT] {old_state} -> {new_state}")
    
    @session.on("user_state_changed")  
    def on_user_state_changed(event):
        """Когда состояние пользователя изменилось"""
        old_state = getattr(event, 'old_state', 'unknown')
        new_state = getattr(event, 'new_state', 'unknown')
        logger.debug(f"👤 [USER STATE] {old_state} -> {new_state}")
        
    @session.on("function_tools_executed")
    def on_function_tools_executed(event):
        """ИСПРАВЛЕННАЯ обработка выполнения функций"""
        logger.info("🛠️ [TOOLS EXECUTED] Function tools completed")
        print("🛠️ [TOOLS] Function executed - processing result...")
        
        # ПРАВИЛЬНЫЙ способ извлечения результатов через zipped()
        try:
            if hasattr(event, 'zipped') and callable(event.zipped):
                for call, result in event.zipped():
                    if hasattr(call, 'function_info') and hasattr(call.function_info, 'name'):
                        function_name = call.function_info.name
                    else:
                        function_name = getattr(call, 'function_name', 'unknown')
                    
                    result_str = str(result)[:200] if result else 'No result'
                    logger.info(f"🛠️ [TOOL SUCCESS] {function_name}: {result_str}...")
                    print(f"🛠️ [TOOL SUCCESS] {function_name}: {result_str[:100]}...")
            else:
                # Fallback для случаев когда zipped() недоступен
                logger.info("🛠️ [TOOL RESULT] Using fallback extraction method")
                print("🛠️ [TOOL RESULT] Function completed (fallback method)")
                
        except Exception as e:
            logger.error(f"❌ [TOOL EXTRACTION ERROR] {e}")
            print(f"❌ [TOOL EXTRACTION ERROR] {e}")
        
    @session.on("metrics_collected")
    def on_metrics_collected(event):
        """Когда собраны метрики производительности"""
        # Отключаем вывод метрик - слишком много спама
        pass
    
    @session.on("close")
    def on_session_close(event):
        """Когда сессия закрывается"""
        logger.info("❌ [SESSION CLOSED] Agent session ended")
        print("❌ [SESSION] Closed")
        
    @session.on("error")
    def on_error(event):
        """Когда происходит ошибка"""
        error = getattr(event, 'error', str(event))
        recoverable = getattr(error, 'recoverable', True) if hasattr(error, 'recoverable') else True
        logger.error(f"❌ [ERROR] {error} (recoverable: {recoverable})")
        print(f"❌ [ERROR] {error}")
    
    # ==========================================
    # Запускаем сессию
    # ==========================================
    
    await session.start(
        agent=agent,
        room=ctx.room,
    )
    
    logger.info("✅ Session started successfully")
    
    # Начальное приветствие
    try:
        await session.generate_reply(
            instructions="Say hello and introduce yourself briefly as a helpful voice assistant with weather information."
        )
        logger.info("✅ Initial greeting generated")
    except Exception as e:
        logger.warning(f"⚠️ Could not generate initial greeting: {e}")
        print("🤖 [ASSISTANT] Hello! I'm your voice assistant with weather, search, and email capabilities!")
    
    # Информационное сообщение
    print("\n" + "="*80)
    print("🤖 [N8N ASSISTANT] Ready for conversation!")
    print("📋 [INFO] OpenAI Whisper STT + Cerebras Llama-3.3-70B (AutoGen) + OpenAI TTS + N8N Weather")
    print("🔍 [VAD] Silero VAD for speech detection")
    print("⚡ [SPEED] Cerebras ~450 tokens/sec + AutoGen settings")
    print("🌍 [STT] Treats ALL speech as English (no language detection)")
    print("🌤️ [WEATHER] Weather via n8n workflow (auto2025system.duckdns.org)")
    print("🛠️ [TOOLS] N8N Weather + OpenAI Search + OpenAI Email")
    print("🔧 [FIX] Минимальные настройки: temp=0.5 + max_tool_steps=1")
    print("📝 [LOGGING] All activity logged to agent_n8n.log and console")
    print("")
    print("🎯 [TEST COMMANDS] (ALL speech treated as English):")
    print("   • 'What's the weather in Cork?' → n8n weather tool") 
    print("   • 'Weather in Paris in Fahrenheit?' → n8n weather with units")
    print("   • 'Search for latest AI news' → OpenAI search tool")
    print("   • 'Send email to test@example.com' → OpenAI email tool")
    print("")
    print("🎮 [CONTROLS] Speak into your microphone, press Ctrl+C to quit")
    print("="*80 + "\n")
    print("🎙️ [LISTENING] Start speaking now...")
    
    # Бесконечный цикл для поддержания работы агента
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("👋 [SHUTDOWN] N8N Assistant shutting down...")
        print("\n👋 [ASSISTANT] Goodbye!")

# -------------------- Main --------------------
if __name__ == "__main__":
    logger.info("🚀 Starting N8N Assistant LiveKit agent application")
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint
        )
    )