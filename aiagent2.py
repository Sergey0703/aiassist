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
from livekit.plugins import openai

# -------------------- Setup --------------------
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Получаем OpenAI API ключ
openai_api_key = os.getenv("OPENAI_API_KEY")

if not openai_api_key:
    logger.error("OPENAI_API_KEY not found in environment variables")
    raise ValueError("OPENAI_API_KEY is required")


# -------------------- Simple Agent --------------------
class SimpleAgent(Agent):
    """Простой агент для тестирования OpenAI"""
    
    def __init__(self):
        super().__init__(
            instructions="You are a helpful assistant. Respond briefly and clearly.",
        )
        logger.info("Simple agent initialized")


# -------------------- Entrypoint --------------------
async def entrypoint(ctx: JobContext):
    """Простая точка входа"""
    
    logger.info("Starting simple agent")
    
    # Подключаемся к комнате
    await ctx.connect()
    logger.info(f"Connected to room: {ctx.room.name}")
    
    # Создаем простого агента БЕЗ инструментов
    agent = SimpleAgent()
    
    # Простая сессия с OpenAI LLM + TTS (чтобы не было ошибок)
    session = AgentSession(
        llm=openai.LLM(model="gpt-4o-mini", temperature=0.7),
        tts=openai.TTS(),  # Добавляем TTS чтобы не было ошибок
    )
    
    logger.info("Session created with OpenAI LLM")
    
    # События для отладки
    @session.on("conversation_item_added")
    def on_conversation_item(event):
        item = getattr(event, 'item', None)
        if item:
            role = getattr(item, 'role', 'unknown')
            text_content = getattr(item, 'text_content', str(item))
            
            if role == "user":
                print(f"👤 [USER] {text_content}")
            elif role == "assistant":
                print(f"🤖 [ASSISTANT] {text_content}")
            print("-" * 40)
    
    # Запускаем сессию
    await session.start(agent=agent, room=ctx.room)
    
    logger.info("Session started successfully")
    
    # Приветствие
    try:
        await session.generate_reply(instructions="Say hello and introduce yourself briefly.")
        logger.info("Initial greeting generated")
    except Exception as e:
        logger.warning(f"Could not generate greeting: {e}")
    
    print("\n" + "="*60)
    print("🤖 [SIMPLE AGENT] Ready for testing!")
    print("📋 [INFO] OpenAI GPT-4o-mini - NO TOOLS")
    print("💬 [MODE] Text mode - press [Ctrl+B] if needed")
    print("")
    print("🎯 [TEST]: Ask simple questions like:")
    print("   • 'What is 2+2?'")
    print("   • 'Tell me a joke'")
    print("   • 'What is Python?'")
    print("")
    print("⌨️ [CONTROLS] Type messages, press Ctrl+C to quit")
    print("="*60 + "\n")
    
    # Бесконечный цикл
    try:
        while True:
            await asyncio.sleep(0.1)
    except KeyboardInterrupt:
        logger.info("Simple agent shutting down...")
        print("\n👋 [BYE] Simple agent stopped!")


# -------------------- Main --------------------
if __name__ == "__main__":
    logger.info("Starting simple OpenAI agent test")
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint
        )
    )