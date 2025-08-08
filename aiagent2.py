import asyncio
import logging
import os
from dotenv import load_dotenv

from livekit import agents
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    WorkerOptions,
    cli,
)
from livekit.plugins import google, silero, deepgram, elevenlabs
from prompts import AGENT_INSTRUCTION, SESSION_INSTRUCTION
from aitools import get_weather, search_web, send_email

# -------------------- Setup --------------------
load_dotenv()

# Настройка логирования с UTF-8
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("aiassist.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Получаем API ключи
google_api_key = os.getenv("GOOGLE_API_KEY")
assemblyai_api_key = os.getenv("ASSEMBLYAI_API_KEY")

if not google_api_key:
    logger.error("GOOGLE_API_KEY not found in environment variables")
    raise ValueError("GOOGLE_API_KEY is required")

if not assemblyai_api_key:
    logger.error("ASSEMBLYAI_API_KEY not found in environment variables")
    raise ValueError("ASSEMBLYAI_API_KEY is required")


# -------------------- AIAssist Agent Class --------------------
class AIAssist(Agent):
    """Персональный голосовой помощник в стиле дворецкого из Iron Man"""
    
    def __init__(self):
        super().__init__(
            instructions=AGENT_INSTRUCTION,
            # ✅ TOOLS В AGENT - ПРАВИЛЬНАЯ АРХИТЕКТУРА!
            tools=[get_weather, search_web, send_email],
        )
        logger.info("AIAssist agent initialized with tools: weather, search, email")


# -------------------- Entrypoint --------------------
async def entrypoint(ctx: JobContext):
    """Главная точка входа для AIAssist агента"""
    
    logger.info("Starting AIAssist entrypoint")
    
    # Подключаемся к комнате
    await ctx.connect()
    logger.info(f"Connected to room: {ctx.room.name}")
    
    # Создаем агента С ИНСТРУМЕНТАМИ
    agent = AIAssist()
    
    # Создаем сессию с Voice Pipeline - ПОЛНОЦЕННЫЙ ГОЛОСОВОЙ АГЕНТ
    session = AgentSession(
        # VAD для детекции речи
        vad=silero.VAD.load(),
        
        # ✅ ПОЛНОЦЕННЫЙ VOICE PIPELINE!
        stt=deepgram.STT(model="nova-2"),   # Deepgram STT - отличное качество
        llm=google.LLM(                     # Google LLM с function calling
            model="gemini-2.0-flash",
            temperature=0.7,
        ),
        tts=elevenlabs.TTS(),               # ElevenLabs TTS - лучшее качество голоса!
    )
    
    logger.info("AIAssist session created with Voice Pipeline (STT + LLM + TTS) + Tools")
    
    # ПРАВИЛЬНЫЕ события для LiveKit Agents v1.0+
    @session.on("user_input_transcribed")
    def on_user_transcribed(event):
        transcript = getattr(event, 'transcript', 'No transcript')
        is_final = getattr(event, 'is_final', False)
        logger.info(f"[USER TRANSCRIBED] {transcript} (final: {is_final})")
        print(f"\n🎤 [USER] {transcript} {'✓' if is_final else '...'}")
        if is_final:
            print("-" * 80)
    
    @session.on("conversation_item_added")
    def on_conversation_item(event):
        item = getattr(event, 'item', None)
        if item:
            role = getattr(item, 'role', 'unknown')
            text_content = getattr(item, 'text_content', str(item))
            interrupted = getattr(item, 'interrupted', False)
            
            logger.info(f"[CONVERSATION] {role}: {text_content} (interrupted: {interrupted})")
            
            if role == "user":
                print(f"👤 [USER FINAL] {text_content}")
            elif role == "assistant":
                print(f"🤖 [AIASSIST] {text_content}")
            print("-" * 80)
    
    @session.on("speech_created")
    def on_speech_created(event):
        logger.info("[AIASSIST] Speech created - starting to speak")
        print("🔊 [AIASSIST] Starting to speak...")
    
    @session.on("agent_state_changed")
    def on_agent_state(event):
        old_state = getattr(event, 'old_state', 'unknown')
        new_state = getattr(event, 'new_state', 'unknown')
        logger.info(f"[AGENT STATE] {old_state} -> {new_state}")
        print(f"⚡ [STATE] {old_state} -> {new_state}")
    
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
    
    # Отладочные события - важные события для понимания что происходит
    @session.on("*")
    def on_debug_events(event_name, event):
        # Логируем только важные события для отладки (НЕ tool events - они выше)
        important_events = [
            "user_input", "transcript", "speech", "conversation", 
            "turn", "started", "stopped", "committed"
        ]
        tool_keywords = ['function', 'tool', 'call', 'execute']
        
        # Показываем важные события, но НЕ tool events (они уже обработаны выше)
        if (any(keyword in event_name.lower() for keyword in important_events) and 
            not any(tool_keyword in event_name.lower() for tool_keyword in tool_keywords)):
            logger.debug(f"[DEBUG EVENT] {event_name}: {type(event).__name__}")
            print(f"🔍 [DEBUG] {event_name}: {type(event).__name__}")
    
    # Запускаем сессию
    await session.start(
        agent=agent,
        room=ctx.room,
    )
    
    logger.info("AIAssist session started successfully")
    
    # Начальное приветствие
    try:
        await session.generate_reply(instructions=SESSION_INSTRUCTION)
        logger.info("Initial AIAssist greeting generated")
    except Exception as e:
        logger.warning(f"Could not generate initial greeting: {e}")
        print(f"\n[AIASSIST]: Hi my name is AIAssist, your personal assistant, how may I help you?")
    
    print("\n" + "="*80)
    print("🤖 [AIASSIST] Ready! Your sarcastic digital butler is at your service.")
    print("📋 [INFO] Using FULL Voice Pipeline (STT + LLM + TTS) with Function Calling")
    print("🎤 [SPEECH] Deepgram STT for speech recognition") 
    print("🧠 [LLM] Google Gemini for intelligence")
    print("🔊 [VOICE] ElevenLabs TTS for natural speech synthesis")
    print("🛠️ [TOOLS] Available: Weather, Web Search, Email")
    print("🔍 [MONITORING] Function calls will be logged in detail")
    print("📝 [LOGGING] All activity logged to aiassist.log and console")
    print("")
    print("🎯 [TEST COMMANDS]:")
    print("   • 'What's the weather in London?'")
    print("   • 'Search for latest AI news'") 
    print("   • 'Send email to test@example.com with subject Hello'")
    print("")
    print("🎮 [CONTROLS] Speak into your microphone, press Ctrl+C to quit")
    print("="*80 + "\n")
    print("🎙️ [READY] Start speaking now...")
    print("🔧 [WATCH] Looking for function call events...")
    
    # Бесконечный цикл для поддержания работы агента
    try:
        while True:
            await asyncio.sleep(0.1)
    except KeyboardInterrupt:
        logger.info("AIAssist shutting down...")
        print("\n👋 [AIASSIST] Goodbye, sir!")


# -------------------- Main --------------------
if __name__ == "__main__":
    # Запускаем AIAssist
    logger.info("Starting AIAssist LiveKit agent application")
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint
        )
    )