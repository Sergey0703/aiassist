import asyncio
import logging
import os
from dotenv import load_dotenv

from livekit import agents
from livekit.agents import (
    JobContext,
    WorkerOptions,
    cli,
    AutoSubscribe,
)
from livekit.plugins import google
# Из найденных примеров - правильный импорт для OpenAI, но для Google используется другая архитектура
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


# -------------------- Entrypoint --------------------
async def entrypoint(ctx: JobContext):
    """Главная точка входа для AIAssist агента - используем рабочую архитектуру"""
    
    logger.info("Starting AIAssist entrypoint")
    
    # Подключаемся к комнате
    await ctx.connect()
    logger.info(f"Connected to room: {ctx.room.name}")
    
    # Создаем агента - как в вашем рабочем коде
    from livekit.agents import Agent, AgentSession
    
    agent = Agent(
        instructions=AGENT_INSTRUCTION,
    )
    
    logger.info("AIAssist agent initialized")
    
    # Создаем сессию с Google Realtime Model - как в вашем коде
    session = AgentSession(
        vad=google.VAD.load() if hasattr(google, 'VAD') else None,
        llm=google.beta.realtime.RealtimeModel(
            model="gemini-2.0-flash-exp",
            voice="Aoede",
            temperature=0.7,
            instructions=AGENT_INSTRUCTION,
            api_key=google_api_key,
        ),
    )
    
    logger.info("AIAssist session created with Google Realtime Model")
    
    # Правильные события для реальной работы
    @session.on("user_input_transcribed") 
    def on_user_transcribed(event):
        transcript = getattr(event, 'transcript', 'No transcript')
        is_final = getattr(event, 'is_final', False)
        logger.info(f"[USER TRANSCRIBED] {transcript} (final: {is_final})")
        print(f"\n🎤 [USER] {transcript} {'✓' if is_final else '...'}")
    
    @session.on("conversation_item_added")
    def on_conversation_item(event):
        item = getattr(event, 'item', None) 
        if item and hasattr(item, 'role'):
            role = item.role
            text = getattr(item, 'text_content', str(item))
            logger.info(f"[CONVERSATION] {role}: {text}")
            
            if role == "user":
                print(f"👤 [USER FINAL] {text}")
                print("-" * 80)
            elif role == "assistant":
                print(f"🤖 [AIASSIST] {text}")
                print("-" * 80)
    
    @session.on("agent_state_changed")
    def on_agent_state_changed(event):
        old_state = getattr(event, 'old_state', 'unknown')
        new_state = getattr(event, 'new_state', 'unknown') 
        logger.info(f"[AGENT STATE] {old_state} -> {new_state}")
        print(f"⚡ [STATE] {old_state} -> {new_state}")
    
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
    
    logger.info("AIAssist is ready and listening")
    print("\n" + "="*80)
    print("🤖 [AIASSIST] Ready! Your sarcastic digital butler is at your service.")
    print("📋 [INFO] Using Google Realtime Model with AgentSession")
    print("🔧 [TOOLS] Available: Weather, Web Search, Email")
    print("🎯 [MONITORING] Looking for transcription events...")
    print("🎮 [CONTROLS] Speak into microphone, Ctrl+C to quit")
    print("="*80 + "\n")
    
    # Бесконечный цикл для поддержания работы агента  
    try:
        while True:
            await asyncio.sleep(0.1)
    except KeyboardInterrupt:
        logger.info("AIAssist shutting down...")
        print("\n👋 [AIASSIST] Goodbye, sir!")


# -------------------- Main --------------------
if __name__ == "__main__":
    # Запускаем AIAssist с правильной архитектурой
    logger.info("Starting AIAssist LiveKit MultimodalAgent application")
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint
        )
    )