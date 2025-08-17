import asyncio
import logging
import os
from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    WorkerOptions,
    cli,
)
from livekit.plugins import google, silero

# Импортируем ваши инструменты
from tools.n8n_tools import get_weather_n8n
from tools.n8n_trade_tools import get_trade_results_n8n
from tools.web_tools import search_web
from tools.email_tools import send_email

# -------------------- Setup --------------------
load_dotenv(dotenv_path=".env")

# Настройка логирования с UTF-8
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("aiassist_gemini.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("gemini-realtime")

# -------------------- GOOGLE REALTIME MODEL SETUP --------------------
# 🎯 НОВАЯ АРХИТЕКТУРА: Google Realtime Model = STT + LLM + TTS в одном!
# Только один API ключ вместо сложных credentials

google_api_key = os.getenv("GOOGLE_API_KEY")
if not google_api_key:
    logger.error("GOOGLE_API_KEY not found in environment variables")
    print("❌ [SETUP] GOOGLE_API_KEY is required for Google Realtime Model")
    print("💡 [SETUP] Add GOOGLE_API_KEY=your_key to .env file")
    raise ValueError("GOOGLE_API_KEY is required")

logger.info("✅ [SETUP] Google API key found")
print("✅ [SETUP] Google API key configured")

# -------------------- GEMINI AGENT CLASS --------------------
class GeminiAgent(Agent):
    """Голосовой агент на базе Google Realtime Model с N8N инструментами"""
    
    def __init__(self):
        super().__init__(
            instructions="""
            You are a helpful voice assistant powered by Google Gemini Realtime Model.
            You can help with:
            - Weather information using get_weather_n8n tool
            - Trade analysis using get_trade_results_n8n tool  
            - Web search using search_web tool
            - Sending emails using send_email tool
            
            When users ask for information, use the appropriate tools and provide clear, concise responses.
            Be helpful and efficient in your responses.
            """,
            # ✅ ВСЕ ИНСТРУМЕНТЫ В AGENT - ПРАВИЛЬНАЯ АРХИТЕКТУРА!
            tools=[get_weather_n8n, get_trade_results_n8n, search_web, send_email],
        )
        logger.info("✅ [AGENT] GeminiAgent initialized with 4 tools: weather, trade, search, email")

# -------------------- EVENT HANDLERS --------------------
def setup_session_events(session: AgentSession):
    """Настройка событий для мониторинга работы агента и инструментов"""
    
    @session.on("user_input_transcribed")
    def on_user_transcribed(event):
        transcript = getattr(event, 'transcript', 'No transcript')
        is_final = getattr(event, 'is_final', False)
        if is_final:
            logger.info(f"👤 [USER] {transcript}")
            print(f"👤 [USER] {transcript}")
    
    @session.on("conversation_item_added")
    def on_conversation_item(event):
        item = getattr(event, 'item', None)
        if item:
            role = getattr(item, 'role', 'unknown')
            content = getattr(item, 'text_content', '') or str(getattr(item, 'content', ''))
            
            if role == "assistant":
                logger.info(f"🤖 [GEMINI] {content}")
                print(f"🤖 [GEMINI] {content}")
    
    # ================================
    # СОБЫТИЯ ДЛЯ МОНИТОРИНГА FUNCTION CALLING
    # ================================
    
    @session.on("function_call_started")
    def on_function_call_started(event):
        function_name = getattr(event, 'function_name', 'unknown')
        arguments = getattr(event, 'arguments', {})
        logger.info(f"🚀 [FUNCTION STARTED] {function_name} with args: {arguments}")
        print(f"🚀 [FUNCTION STARTED] {function_name}")
    
    @session.on("function_call_completed")
    def on_function_call_completed(event):
        function_name = getattr(event, 'function_name', 'unknown')
        result = getattr(event, 'result', 'no result')
        logger.info(f"✅ [FUNCTION COMPLETED] {function_name} returned: {str(result)[:200]}...")
        print(f"✅ [FUNCTION COMPLETED] {function_name}")
    
    @session.on("function_tools_executed")
    def on_function_tools_executed(event):
        logger.info("🛠️ [TOOLS EXECUTED] Function tools completed")
        print("🛠️ [TOOLS] Function executed")
        
        # Проверяем результаты если есть
        if hasattr(event, 'function_call_outputs') and event.function_call_outputs:
            logger.info(f"✅ [OUTPUTS] Found {len(event.function_call_outputs)} outputs")
            
            for i, output in enumerate(event.function_call_outputs):
                function_name = getattr(output, 'name', 'unknown')
                result_output = getattr(output, 'output', 'no output')
                
                logger.info(f"✅ [OUTPUT {i+1}] {function_name}: {str(result_output)[:200]}...")
                print(f"✅ [RESULT] {function_name}: {str(result_output)[:100]}...")
        else:
            logger.warning("❌ [OUTPUTS] No function_call_outputs found")
    
    @session.on("speech_created")
    def on_speech_created(event):
        logger.info("🔊 [SPEECH] Gemini started speaking")
        print("🔊 [SPEECH] Speaking...")
    
    @session.on("agent_state_changed")
    def on_agent_state(event):
        old_state = getattr(event, 'old_state', 'unknown')
        new_state = getattr(event, 'new_state', 'unknown')
        logger.info(f"⚡ [STATE] {old_state} -> {new_state}")
        print(f"⚡ [STATE] {old_state} -> {new_state}")
    
    @session.on("error")
    def on_error(event):
        error = getattr(event, 'error', str(event))
        logger.error(f"❌ [ERROR] {error}")
        print(f"❌ [ERROR] {error}")
    
    logger.info("✅ [EVENTS] All event handlers configured")

# -------------------- MAIN ENTRYPOINT --------------------
async def entrypoint(ctx: JobContext):
    """Главная точка входа - Google Realtime Model архитектура"""
    
    logger.info("🚀 [GEMINI REALTIME] Starting with Google Realtime Model")
    print("🚀 [GEMINI REALTIME] Starting...")
    
    # Подключаемся к комнате
    await ctx.connect()
    logger.info(f"✅ [LIVEKIT] Connected to room: {ctx.room.name}")
    
    # Создаем агента с инструментами
    agent = GeminiAgent()
    
    # ================================
    # GOOGLE REALTIME MODEL = STT + LLM + TTS В ОДНОМ!
    # ================================
    session = AgentSession(
        # VAD для детекции речи
        vad=silero.VAD.load(),
        
        # Google Realtime Model - ВСЁ В ОДНОМ компоненте!
        llm=google.beta.realtime.RealtimeModel(
            model="gemini-2.0-flash-exp",  # Последняя модель Gemini
            voice="Aoede",  # Встроенный голос - красивый женский голос
            temperature=0.7,
            api_key=google_api_key,
            # БЕЗ tools параметра - они в Agent!
        ),
        # БЕЗ отдельных stt= и tts= - всё в Realtime Model!
    )
    
    logger.info("✅ [SESSION] Created with Google Realtime Model (STT+LLM+TTS)")
    print("✅ [SESSION] Google Realtime Model ready")
    
    # Настраиваем события
    setup_session_events(session)
    
    # Запускаем сессию
    await session.start(
        agent=agent,
        room=ctx.room,
    )
    
    logger.info("✅ [GEMINI] Session started successfully")
    
    # Начальное приветствие
    try:
        await session.generate_reply(
            instructions="Greet the user and briefly mention you can help with weather, trade analysis, web search, and emails."
        )
        logger.info("✅ [GREETING] Initial greeting generated")
    except Exception as e:
        logger.warning(f"⚠️ [GREETING] Could not generate greeting: {e}")
        print("🤖 [GEMINI] Hello! I'm your voice assistant. How can I help you today?")
    
    # Информация о запуске
    print("\n" + "="*80)
    print("🤖 [GEMINI REALTIME] Voice assistant ready!")
    print("📋 [ARCHITECTURE] Google Realtime Model (STT+LLM+TTS in one)")
    print("🛠️ [TOOLS] Weather (N8N) | Trade Analysis (N8N) | Web Search | Email")
    print("🔑 [AUTH] Simple Google API key (no complex credentials)")
    print("🎙️ [VOICE] Aoede voice with real-time speech")
    print("")
    print("🎯 [TEST COMMANDS]:")
    print("   • 'What's the weather in Dublin?'")
    print("   • 'Show me trade results for last 30 days'")
    print("   • 'Search for latest AI news'")
    print("   • 'Send email to test@example.com saying hello'")
    print("")
    print("📊 [COMPARISON vs old architecture]:")
    print("   ✅ No separate STT/LLM/TTS components")
    print("   ✅ No Google Cloud credentials complexity")
    print("   ✅ Single API key instead of multiple auth")
    print("   ✅ Built-in voice synthesis")
    print("   ✅ Less HTTP sessions = less aiohttp issues")
    print("")
    print("🎮 [CONTROLS] Speak into microphone | Press Q to quit")
    print("="*80 + "\n")
    
    # Бесконечный цикл для поддержания работы агента
    try:
        logger.info("🎙️ [READY] Waiting for user input...")
        print("🎙️ [READY] Start speaking now...")
        
        while True:
            await asyncio.sleep(0.1)
            
    except KeyboardInterrupt:
        logger.info("👋 [SHUTDOWN] Gemini agent shutting down...")
        print("\n👋 [GEMINI] Goodbye!")

# -------------------- MAIN --------------------
if __name__ == "__main__":
    # Запускаем Gemini Realtime агента
    logger.info("🚀 [MAIN] Starting Gemini Realtime Model agent")
    print("🚀 [MAIN] Initializing Gemini Realtime Model...")
    
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint
        )
    )