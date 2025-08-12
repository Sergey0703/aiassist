import asyncio
import logging
import os
from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    RunContext,
    WorkerOptions,
    cli,
)
from livekit.plugins import openai, silero

# Импортируем инструменты из модульной системы
from tools import AVAILABLE_TOOLS, validate_all_tools, get_package_info

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

# Получаем OpenAI API ключ из переменных окружения
openai_api_key = os.getenv("OPENAI_API_KEY")

if not openai_api_key:
    logger.error("OPENAI_API_KEY not found in environment variables")
    raise ValueError("OPENAI_API_KEY is required")

# -------------------- Agent Class --------------------
class N8NAssistant(Agent):
    """Голосовой помощник с модульной системой инструментов: n8n + веб + email"""
    
    def __init__(self):
        # Получаем информацию о доступных инструментах
        tools_info = get_package_info()
        tools_count = tools_info['active_tools']
        categories = ', '.join(tools_info['categories'])
        
        super().__init__(
            instructions=(
                "You are a helpful voice assistant with access to weather information, web search, and email sending. "
                "ALWAYS respond in English only, regardless of what language the user speaks. "
                "You understand all languages but respond ONLY in English. "
                "Do NOT mention the language issue - just answer naturally in English. "
                "\n"
                "Available tools:\n"
                "- Weather: Use get_weather_n8n for current weather and forecasts through n8n workflow\n"
                "- Web Search: Use search_web to find current information on the internet\n"
                "- Email: Use send_email to send messages via SMTP\n"
                "\n"
                "Guidelines:\n"
                "- When users ask about weather, use get_weather_n8n and provide the exact information returned\n"
                "- When users ask for information you don't know, use search_web to find current information\n"
                "- When users ask to send email, use send_email with the information they provide\n"
                "- Do NOT make up information - only use data from your tools\n"
                "- Be clear, concise, and direct\n"
                "- Do NOT add phrases like 'If you have any other questions' or 'Let me know if you need more help'\n"
                "- Just give the information requested professionally and helpfully"
            ),
            # Используем все доступные инструменты из модульной системы
            tools=AVAILABLE_TOOLS,
        )
        
        logger.info(f"✅ [AGENT INIT] N8N Assistant initialized with {tools_count} tools")
        logger.info(f"📂 [AGENT INIT] Tool categories: {categories}")

# -------------------- Event Handlers --------------------
def setup_session_events(session: AgentSession):
    """Настройка всех обработчиков событий сессии"""
    
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
        """Когда выполнены функции-инструменты"""
        logger.info("🛠️ [TOOLS EXECUTED] Function tools completed")
        print("🛠️ [TOOLS] Function executed - processing result...")
        
        # Пытаемся получить результаты инструментов разными способами
        if hasattr(event, 'function_calls') and event.function_calls:
            for i, call in enumerate(event.function_calls):
                function_name = getattr(call, 'function_name', 'unknown')
                result = getattr(call, 'result', 'no result')
                logger.info(f"🛠️ [TOOL RESULT {i+1}] {function_name}: {str(result)[:200]}...")
                print(f"🛠️ [TOOL {i+1}] {function_name}: {str(result)[:100]}...")
        
        # Дополнительная отладка для понимания структуры события
        if hasattr(event, 'results') and event.results:
            logger.info(f"🛠️ [TOOL RESULTS] Found {len(event.results)} results")
            print(f"🛠️ [RESULTS] Found {len(event.results)} tool results")
            
        # Показываем важные атрибуты события
        for attr in ['tools', 'calls', 'results', 'output']:
            if hasattr(event, attr):
                value = getattr(event, attr, None)
                if value:
                    logger.info(f"🛠️ [ATTR] {attr}: {str(value)[:100]}...")
                    print(f"🛠️ [ATTR] {attr}: {str(value)[:50]}...")
        
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

# -------------------- Session Creation --------------------
def create_agent_session():
    """Создание оптимальной сессии агента с OpenAI компонентами"""
    session = AgentSession(
        # VAD для детекции речи
        vad=silero.VAD.load(),
        
        # OpenAI STT (Whisper) - ПРИНУДИТЕЛЬНО ТОЛЬКО АНГЛИЙСКИЙ!
        stt=openai.STT(
            language="en",  # ПРИНУДИТЕЛЬНО английский - никакой автоопределения!
        ),
        
        # OpenAI LLM - GPT-4o-mini для экономии
        llm=openai.LLM(
            model="gpt-4o-mini",
            temperature=0.7,
        ),
                
        # OpenAI TTS для озвучки
        tts=openai.TTS(
            voice="alloy",
            speed=1.0,
        ),
    )
    
    logger.info("✅ [SESSION] Created: Whisper STT (EN) + GPT-4o-mini + TTS + Modular Tools")
    return session

# -------------------- Tools Validation --------------------
async def startup_tools_validation():
    """Проверка работоспособности всех инструментов при запуске"""
    print("🧪 [STARTUP] Validating all tools...")
    logger.info("🧪 [STARTUP] Starting comprehensive tool validation...")
    
    try:
        validation_results = await validate_all_tools()
        
        # Выводим результаты валидации
        total_tools = validation_results['summary']['total_tools']
        working_tools = validation_results['summary']['working_tools']
        failed_tools = validation_results['summary']['failed_tools']
        
        print(f"📊 [VALIDATION] Results: {working_tools}/{total_tools} tools working")
        logger.info(f"📊 [VALIDATION] Complete: {working_tools} working, {failed_tools} failed")
        
        # Детали по категориям
        if validation_results.get('n8n_tools'):
            n8n_status = validation_results['n8n_tools'].get('weather_service', False)
            status_emoji = "✅" if n8n_status else "❌"
            print(f"   {status_emoji} N8N Weather: {'Working' if n8n_status else 'Failed'}")
            
        if validation_results.get('web_tools'):
            web_status = validation_results['web_tools'].get('search_web', False)
            status_emoji = "✅" if web_status else "❌" 
            print(f"   {status_emoji} Web Search: {'Working' if web_status else 'Failed'}")
            
        if validation_results.get('email_tools'):
            email_status = validation_results['email_tools'].get('send_email', False)
            status_emoji = "✅" if email_status else "❌"
            print(f"   {status_emoji} Email Send: {'Working' if email_status else 'Failed'}")
        
        # Предупреждения если что-то не работает
        if failed_tools > 0:
            print(f"⚠️ [WARNING] {failed_tools} tools have configuration issues but agent will continue")
            logger.warning(f"⚠️ [WARNING] {failed_tools} tools failed validation")
        else:
            print("✅ [VALIDATION] All tools are working properly!")
            logger.info("✅ [VALIDATION] All tools validated successfully")
            
        return validation_results
        
    except Exception as e:
        print(f"❌ [VALIDATION ERROR] Tool validation failed: {e}")
        logger.error(f"❌ [VALIDATION ERROR] {e}")
        return None

# -------------------- Info Display --------------------
def display_startup_info(validation_results=None):
    """Отображение информации о запуске агента"""
    tools_info = get_package_info()
    
    print("\n" + "="*80)
    print("🤖 [N8N ASSISTANT] Ready for conversation!")
    print(f"📦 [TOOLS] {tools_info['package']} v{tools_info['version']}")
    print("📋 [STACK] OpenAI Whisper STT (ENGLISH ONLY) + GPT-4o-mini + TTS")
    print("🔍 [VAD] Silero VAD for speech detection")
    print("💰 [COST] ~$0.02 per minute (very affordable!)")
    print("🌍 [STT] Treats ALL speech as English (no language detection)")
    print("")
    print("🛠️ [TOOLS] Available instruments:")
    for category, tool_names in tools_info['tools_by_category'].items():
        print(f"   📂 {category}: {', '.join(tool_names)}")
    print("")
    print("📝 [LOGGING] All activity logged to agent_n8n.log and console")
    print("")
    print("🎯 [TEST COMMANDS] (ALL speech treated as English):")
    print("   • 'What's the weather in London?' → n8n weather tool") 
    print("   • 'Weather in Paris in Fahrenheit?' → n8n weather with units")
    print("   • 'Search for latest AI news' → Tavily web search")
    print("   • 'Send email to test@example.com about meeting' → SMTP email")
    print("")
    
    # Показываем статус инструментов если доступен
    if validation_results:
        working = validation_results['summary']['working_tools']
        total = validation_results['summary']['total_tools']
        print(f"⚡ [STATUS] {working}/{total} tools operational")
    
    print("🎮 [CONTROLS] Speak into your microphone, press Ctrl+C to quit")
    print("="*80 + "\n")
    print("🎙️ [LISTENING] Start speaking now...")

# -------------------- Entrypoint --------------------
async def entrypoint(ctx: JobContext):
    """Главная точка входа для N8N агента с модульной системой инструментов"""
    
    logger.info("🚀 [ENTRYPOINT] Starting N8N Assistant with modular tools")
    
    # Валидируем все инструменты при запуске
    validation_results = await startup_tools_validation()
    
    # Подключаемся к комнате LiveKit
    await ctx.connect()
    logger.info(f"✅ [LIVEKIT] Connected to room: {ctx.room.name}")
    
    # Создаем агента с модульными инструментами
    agent = N8NAssistant()
    
    # Создаем сессию с OpenAI компонентами
    session = create_agent_session()
    
    # Настраиваем все обработчики событий
    setup_session_events(session)
    
    # Запускаем сессию агента
    await session.start(
        agent=agent,
        room=ctx.room,
    )
    
    logger.info("✅ [SESSION] Started successfully")
    
    # Начальное приветствие
    try:
        await session.generate_reply(
            instructions="Say hello and introduce yourself as a helpful voice assistant with weather, search, and email capabilities."
        )
        logger.info("✅ [GREETING] Initial greeting generated")
    except Exception as e:
        logger.warning(f"⚠️ [GREETING] Could not generate initial greeting: {e}")
        print("🤖 [ASSISTANT] Hello! I'm your voice assistant with weather, search, and email capabilities!")
    
    # Отображаем информацию о запуске
    display_startup_info(validation_results)
    
    # Бесконечный цикл для поддержания работы агента
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("👋 [SHUTDOWN] N8N Assistant shutting down...")
        print("\n👋 [ASSISTANT] Goodbye!")

# -------------------- Main --------------------
if __name__ == "__main__":
    logger.info("🚀 [MAIN] Starting N8N Assistant LiveKit agent application")
    
    # Показываем информацию о модульной системе при запуске
    try:
        tools_info = get_package_info()
        logger.info(f"📦 [TOOLS] Loading {tools_info['package']} v{tools_info['version']}")
        logger.info(f"🔧 [TOOLS] {tools_info['active_tools']} active tools in {len(tools_info['categories'])} categories")
    except Exception as e:
        logger.error(f"❌ [TOOLS] Failed to load tools info: {e}")
    
    # Запускаем LiveKit агент
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint
        )
    )