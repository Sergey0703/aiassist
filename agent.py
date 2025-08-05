import os
import logging
from dotenv import load_dotenv

from livekit import agents
from livekit.agents.voice import Agent as VoiceAgent, AgentSession
from livekit.agents import (
    JobContext,
    WorkerOptions,
    cli,
)
from livekit.plugins import google, silero
from prompts import AGENT_INSTRUCTION, SESSION_INSTRUCTION
from tools import get_weather, search_web, send_email

# -------------------- Setup --------------------
load_dotenv()

# Настройка логирования с UTF-8
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("assistant.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Установка Google API ключа если он есть в .env
google_api_key = os.getenv("GOOGLE_API_KEY")
if google_api_key:
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = google_api_key


# -------------------- Entrypoint --------------------
async def entrypoint(ctx: JobContext):
    """Главная точка входа для LiveKit агента"""
    
    logger.info("Starting agent entrypoint")
    
    # Подключаемся к комнате
    await ctx.connect()
    logger.info(f"Connected to room: {ctx.room.name}")
    
    # Создаем голосового агента только с Google Realtime Model
    # RealtimeModel уже включает в себя STT и TTS функциональность
    # Добавляем инструкцию о том, что нужно озвучивать результаты функций
    enhanced_instructions = AGENT_INSTRUCTION + """
    
    IMPORTANT: When you call a function/tool:
    1. Wait for the function result
    2. Always speak the result out loud to the user
    3. Format weather results in a natural way, for example: "The weather in London is partly cloudy with a temperature of 21 degrees Celsius"
    4. Never just say "Roger" or short acknowledgments - always provide the full information
    """
    
    agent = VoiceAgent(
        instructions=enhanced_instructions,
        llm=google.beta.realtime.RealtimeModel(
            instructions=enhanced_instructions,
            voice="Aoede",  # Голос для озвучки
            temperature=0.8,
            api_key=google_api_key,  # Передаем API ключ если есть
        ),
        tools=[
            get_weather,
            search_web,
            send_email
        ],
        vad=silero.VAD.load(),  # Voice Activity Detection
        # Не добавляем отдельный TTS - RealtimeModel сам озвучивает
    )
    
    logger.info("Voice agent created with Google Realtime Model")
    
    # Создаем сессию
    session = AgentSession()
    
    # Подписываемся на события с правильными атрибутами
    @session.on("user_input_transcribed")
    def on_user_input(event):
        try:
            # Используем transcript вместо text
            if hasattr(event, 'transcript'):
                logger.info(f"[USER] Input: {event.transcript}")
                print(f"\n[USER]: {event.transcript}")
        except Exception as e:
            logger.error(f"Error in on_user_input: {e}")
    
    @session.on("agent_state_changed")
    def on_state_changed(event):
        try:
            logger.info(f"[STATE] Changed from {event.old_state} to {event.new_state}")
            if str(event.new_state).lower() == "speaking":
                print("[AGENT]: Speaking...")
            elif str(event.new_state).lower() == "listening":
                print("[AGENT]: Listening...")
            elif str(event.new_state).lower() == "thinking":
                print("[AGENT]: Thinking...")
        except Exception as e:
            logger.error(f"Error in on_state_changed: {e}")
    
    @session.on("conversation_item_added") 
    def on_item_added(event):
        try:
            if hasattr(event.item, 'content'):
                content_str = str(event.item.content)[:100]
                logger.info(f"[CONVERSATION] Added: {content_str}")
                
                # Проверяем роль и выводим ответ агента
                if hasattr(event.item, 'role'):
                    if event.item.role == "assistant":
                        print(f"[AGENT]: {event.item.content}")
                    elif event.item.role == "user":
                        print(f"[USER]: {event.item.content}")
        except Exception as e:
            logger.error(f"Error in on_item_added: {e}")
    
    @session.on("function_tools_executed")
    def on_tools_executed(event):
        try:
            logger.info(f"[TOOLS] Executed: {event}")
            print(f"[TOOLS] Function executed successfully")
            # Форсируем генерацию ответа после выполнения функции
            if hasattr(event, 'results') and event.results:
                for result in event.results:
                    print(f"[FUNCTION RESULT]: {result}")
        except Exception as e:
            logger.error(f"Error in on_tools_executed: {e}")
    
    # Запускаем сессию с агентом
    await session.start(
        agent=agent,
        room=ctx.room,
    )
    
    logger.info("Agent session started successfully")
    
    # Начальное приветствие через generate_reply вместо say
    try:
        # Используем generate_reply для начала разговора
        await session.generate_reply(instructions=SESSION_INSTRUCTION)
        logger.info("Initial conversation started")
    except Exception as e:
        logger.warning(f"Could not start initial conversation: {e}")
        print(f"\n[AGENT]: {SESSION_INSTRUCTION}")
    
    logger.info("Agent is ready and listening")
    print("\n" + "="*50)
    print("[AGENT] Ready! You can start talking or type your message.")
    print("[INFO] Available commands:")
    print("  - Ask about weather: 'What's the weather in London?'")
    print("  - Search the web: 'Search for latest AI news'") 
    print("  - Send email: 'Send an email to...'")
    print("[CONTROLS] Press Ctrl+B to toggle Text/Audio mode, Q to quit")
    print("="*50 + "\n")


# -------------------- Main --------------------
if __name__ == "__main__":
    # Запускаем приложение
    logger.info("Starting LiveKit agent application")
    agents.cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint
        )
    )