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
from livekit.plugins import google, silero
from prompts import AGENT_INSTRUCTION, SESSION_INSTRUCTION

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

# Получаем Google API ключ
google_api_key = os.getenv("GOOGLE_API_KEY")
if not google_api_key:
    logger.error("GOOGLE_API_KEY not found in environment variables")
    raise ValueError("GOOGLE_API_KEY is required")


# -------------------- AIAssist Agent Class --------------------
class AIAssist(Agent):
    """Персональный голосовой помощник в стиле дворецкого из Iron Man"""
    
    def __init__(self):
        super().__init__(
            instructions=AGENT_INSTRUCTION,
        )
        logger.info("AIAssist agent initialized")


# -------------------- Entrypoint --------------------
async def entrypoint(ctx: JobContext):
    """Главная точка входа для AIAssist агента"""
    
    logger.info("Starting AIAssist entrypoint")
    
    # Подключаемся к комнате
    await ctx.connect()
    logger.info(f"Connected to room: {ctx.room.name}")
    
    # Создаем агента
    agent = AIAssist()
    
    # Создаем сессию с Google Realtime Model
    session = AgentSession(
        # VAD для детекции речи
        vad=silero.VAD.load(),
        
        # Используем Google Realtime Model (аналог OpenAI Realtime API)
        # Включает в себе STT + LLM + TTS в одном
        llm=google.beta.realtime.RealtimeModel(
            model="gemini-2.0-flash-exp",  # Gemini Flash 2.5
            voice="Aoede",  # Голос для озвучки
            temperature=0.7,
            instructions=AGENT_INSTRUCTION,
            api_key=google_api_key,
        ),
    )
    
    logger.info("AIAssist session created with Google Realtime Model")
    
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
    
    # Ошибки
    @session.on("error")
    def on_error(event):
        error = getattr(event, 'error', str(event))
        recoverable = getattr(error, 'recoverable', False) if hasattr(error, 'recoverable') else True
        logger.error(f"[ERROR] {error} (recoverable: {recoverable})")
        print(f"❌ [ERROR] {error} (recoverable: {recoverable})")
    
    # Отладочные события - все события для понимания что происходит
    @session.on("*")
    def on_all_events(event_name, event):
        # Логируем только важные события для отладки
        important_events = [
            "user_input", "transcript", "speech", "conversation", 
            "turn", "started", "stopped", "committed"
        ]
        if any(keyword in event_name.lower() for keyword in important_events):
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
    print("📋 [INFO] All speech will be logged in console and aiassist.log file")
    print("🎯 [DEBUGGING] If you don't see transcriptions:")
    print("   1. Check microphone permissions")
    print("   2. Speak clearly and loudly")
    print("   3. Look for any error messages above")
    print("   4. Events will show as they happen")
    print("🎮 [CONTROLS] Speak into your microphone, press Ctrl+C to quit")
    print("="*80 + "\n")
    print("🎙️ [READY] Start speaking now...")
    
    # Бесконечный цикл для поддержания работы агента
    try:
        while True:
            await asyncio.sleep(0.1)  # Более частая проверка
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