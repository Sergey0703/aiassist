import asyncio
import logging
import os
from dotenv import load_dotenv
from livekit import agents
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    RoomInputOptions,
    WorkerOptions,
    cli,
)
from livekit.plugins import (
    noise_cancellation,
    google,
)

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
logger = logging.getLogger("gemini-agent")

# -------------------- GOOGLE API SETUP --------------------
google_api_key = os.getenv("GOOGLE_API_KEY")
if not google_api_key:
    logger.error("GOOGLE_API_KEY not found in environment variables")
    print("❌ [SETUP] GOOGLE_API_KEY is required for Google Realtime Model")
    print("💡 [SETUP] Add GOOGLE_API_KEY=your_key to .env file")
    raise ValueError("GOOGLE_API_KEY is required")

logger.info("✅ [SETUP] Google API key found")
print("✅ [SETUP] Google API key configured")

# -------------------- AGENT INSTRUCTIONS --------------------
AGENT_INSTRUCTION = """
You are a helpful voice assistant powered by Google Gemini Realtime Model.
You can help users with various tasks using these tools:

🌤️ Weather Information: Use get_weather_n8n to get current weather for any city
📊 Trade Analysis: Use get_trade_results_n8n to analyze sales data and product performance  
🔍 Web Search: Use search_web to find information on the internet
📧 Email Sending: Use send_email to send emails through SMTP

When users ask for information:
- Use the appropriate tool for their request
- Provide clear, concise responses based on the tool results
- Be helpful and efficient in your responses
- You can see and analyze video/images when users share their screen or camera

Keep responses conversational and natural for voice interaction.
"""

SESSION_INSTRUCTION = """
Greet the user warmly and let them know you're ready to help. 
Briefly mention you can assist with weather, trade analysis, web search, and sending emails.
Also mention that you can see and analyze anything they show you via video.
"""

# -------------------- GEMINI AGENT CLASS --------------------
class GeminiAgent(Agent):
    """Голосовой и мультимодальный агент на базе Google Realtime Model"""
    
    def __init__(self) -> None:
        super().__init__(
            instructions=AGENT_INSTRUCTION,
            
            # 🔑 LLM В AGENT - НОВАЯ АРХИТЕКТУРА!
            llm=google.beta.realtime.RealtimeModel(
                model="gemini-live-2.5-flash-preview",  # Последняя Gemini модель
                voice="Aoede",                 # Красивый женский голос
                temperature=0.7,
                api_key=google_api_key,
                # БЕЗ tools - они определены ниже!
            ),
            
            # ✅ ВСЕ ИНСТРУМЕНТЫ В AGENT
            tools=[
                get_weather_n8n,        # N8N погода
                get_trade_results_n8n,  # N8N торговая аналитика  
                search_web,             # Tavily поиск
                send_email,             # SMTP email
            ],
        )
        logger.info("✅ [AGENT] GeminiAgent initialized with Google Realtime Model + 4 tools")

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
            interrupted = getattr(item, 'interrupted', False)
            
            logger.info(f"[CONVERSATION] {role}: {content} (interrupted: {interrupted})")
            
            if role == "user":
                print(f"👤 [USER FINAL] {content}")
            elif role == "assistant":
                print(f"🤖 [GEMINI] {content}")
            print("-" * 80)
    
    # ================================
    # СОБЫТИЯ ДЛЯ МОНИТОРИНГА FUNCTION CALLING
    # ================================
    
    @session.on("function_call_started")
    def on_function_call_started(event):
        function_name = getattr(event, 'function_name', 'unknown')
        arguments = getattr(event, 'arguments', {})
        logger.info(f"🚀 [FUNCTION CALL STARTED] {function_name} with args: {arguments}")
        print(f"🚀 [FUNCTION CALL STARTED] {function_name} with args: {arguments}")
    
    @session.on("function_call_completed")
    def on_function_call_completed(event):
        function_name = getattr(event, 'function_name', 'unknown')
        result = getattr(event, 'result', 'no result')
        logger.info(f"✅ [FUNCTION CALL COMPLETED] {function_name} returned: {result}")
        print(f"✅ [FUNCTION CALL COMPLETED] {function_name} returned: {result}")
    
    @session.on("function_tools_executed")
    def on_function_tools_executed(event):
        logger.info("🔧 [TOOLS EXECUTED] Function tools have been executed!")
        print("🔧 [TOOLS EXECUTED] Function tools have been executed!")
        
        # Получаем результаты инструментов если есть
        if hasattr(event, 'results') and event.results:
            for i, result in enumerate(event.results):
                logger.info(f"🔧 [TOOL RESULT {i+1}] {result}")
                print(f"🔧 [TOOL RESULT {i+1}] {result}")
        
        # Проверяем все атрибуты события для отладки
        for attr in dir(event):
            if not attr.startswith('_'):
                value = getattr(event, attr, None)
                if value and not callable(value):
                    logger.info(f"🔧 [TOOL EVENT.{attr}] {value}")
                    print(f"🔧 [TOOL EVENT.{attr}] {value}")
    
    @session.on("speech_created")
    def on_speech_created(event):
        logger.info("[GEMINI] Speech created - starting to speak")
        print("🔊 [GEMINI] Starting to speak...")
    
    @session.on("agent_state_changed")
    def on_agent_state(event):
        old_state = getattr(event, 'old_state', 'unknown')
        new_state = getattr(event, 'new_state', 'unknown')
        logger.info(f"[AGENT STATE] {old_state} -> {new_state}")
        print(f"⚡ [STATE] {old_state} -> {new_state}")
    
    # Отлавливаем ВСЕ события связанные с инструментами для отладки
    @session.on("*")
    def on_all_events(event_name, event):
        # Ищем события связанные с функциями/инструментами
        tool_keywords = ['function', 'tool', 'call', 'execute']
        if any(keyword in event_name.lower() for keyword in tool_keywords):
            logger.info(f"🔍 [TOOL EVENT] {event_name}: {type(event).__name__}")
            print(f"🔍 [TOOL EVENT] {event_name}: {type(event).__name__}")
            
            # Выводим содержимое события для отладки
            for attr in dir(event):
                if not attr.startswith('_') and not callable(getattr(event, attr, None)):
                    value = getattr(event, attr, None)
                    if value is not None:
                        logger.info(f"🔍 [TOOL EVENT.{attr}] {value}")
                        print(f"🔍 [TOOL EVENT.{attr}] {value}")
    
    # Ошибки
    @session.on("error")
    def on_error(event):
        error = getattr(event, 'error', str(event))
        recoverable = getattr(error, 'recoverable', False) if hasattr(error, 'recoverable') else True
        logger.error(f"[ERROR] {error} (recoverable: {recoverable})")
        print(f"❌ [ERROR] {error} (recoverable: {recoverable})")
    
    logger.info("✅ [EVENTS] All event handlers configured")

# -------------------- MAIN ENTRYPOINT --------------------
async def entrypoint(ctx: JobContext):
    """Главная точка входа - Agent-LLM архитектура с видео поддержкой"""
    
    logger.info("🚀 [GEMINI] Starting Agent-LLM architecture with video support")
    print("🚀 [GEMINI] Starting...")
    
    # ================================
    # ПУСТАЯ SESSION - LLM В AGENT!
    # ================================
    session = AgentSession(
        # ПУСТАЯ СЕССИЯ! Все в Agent
    )
    
    logger.info("✅ [SESSION] Created empty session (LLM in Agent)")
    
    # Настраиваем события
    setup_session_events(session)
    
    # Запускаем сессию с Agent + видео поддержкой
    await session.start(
        room=ctx.room,
        agent=GeminiAgent(),  # LLM внутри Agent!
        
        # 🎥 ПОДДЕРЖКА ВИДЕО + АУДИО
        room_input_options=RoomInputOptions(
            video_enabled=True,  # ← ВИДЕО ПОДДЕРЖКА!
            noise_cancellation=noise_cancellation.BVC(),  # Шумоподавление
        ),
    )
    
    # Подключаемся к комнате
    await ctx.connect()
    
    logger.info("✅ [GEMINI] Session started with video support")
    
    # Начальное приветствие
    try:
        await session.generate_reply(instructions=SESSION_INSTRUCTION)
        logger.info("✅ [GREETING] Initial greeting generated")
    except Exception as e:
        logger.warning(f"⚠️ [GREETING] Could not generate greeting: {e}")
        print("🤖 [GEMINI] Hello! I'm your multimodal voice assistant. How can I help you today?")
    
    # Информация о запуске
    print("\n" + "="*90)
    print("🤖 [GEMINI AGENT] Multimodal voice assistant ready!")
    print("📋 [ARCHITECTURE] Agent-LLM (LLM inside Agent, not Session)")
    print("🎥 [MULTIMODAL] Voice + Video + Text support")
    print("🔊 [VOICE] Google Realtime Model with Aoede voice")
    print("🛠️ [TOOLS] Weather (N8N) | Trade Analysis (N8N) | Web Search | Email")
    print("🎚️ [AUDIO] Enhanced noise cancellation (BVC)")
    print("")
    print("🎯 [TEST COMMANDS]:")
    print("   • 'What's the weather in Dublin?'")
    print("   • 'Show me trade results for last 30 days'")
    print("   • 'Search for latest AI news'")
    print("   • 'Send email to test@example.com saying hello'")
    print("   • 📹 Show your screen/camera for visual analysis!")
    print("")
    print("📊 [ADVANTAGES vs Session-LLM]:")
    print("   ✅ Video support (show screen, documents, objects)")
    print("   ✅ Multimodal conversations")
    print("   ✅ Modern Agent-centric architecture")  
    print("   ✅ Single Google API key")
    print("   ✅ Enhanced noise cancellation")
    print("")
    print("🎮 [CONTROLS] Speak into microphone | Show screen/camera | Press Q to quit")
    print("="*90 + "\n")
    
    logger.info("🎙️ [READY] Multimodal agent ready for voice and video input")
    print("🎙️ [READY] Start speaking or show me something...")

# -------------------- MAIN --------------------
if __name__ == "__main__":
    # Запускаем Agent-LLM архитектуру
    logger.info("🚀 [MAIN] Starting Gemini Agent-LLM multimodal architecture")
    print("🚀 [MAIN] Initializing Agent-LLM multimodal system...")
    
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint
        )
    )