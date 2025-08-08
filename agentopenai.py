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
from livekit.plugins import openai, silero

# Импортируем все три инструмента: погода, поиск и email
from aitools import get_weather, search_web, send_email

# -------------------- Setup --------------------
load_dotenv()

# Правильная настройка логирования как в примерах LiveKit
logger = logging.getLogger("openai-assistant")
logger.setLevel(logging.INFO)  # Возвращаем INFO вместо DEBUG

# Настройка форматтера для красивого вывода
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Консольный обработчик
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Файловый обработчик
file_handler = logging.FileHandler("agent.log", encoding='utf-8')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Получаем OpenAI API ключ
openai_api_key = os.getenv("OPENAI_API_KEY")

if not openai_api_key:
    logger.error("OPENAI_API_KEY not found in environment variables")
    raise ValueError("OPENAI_API_KEY is required")

# -------------------- Agent Class --------------------
class OpenAIAssistant(Agent):
    """Голосовой помощник с OpenAI и тремя инструментами: погода, поиск, email"""
    
    def __init__(self):
        super().__init__(
            instructions=(
                "You are a helpful voice assistant with access to weather information, web search, and email sending. "
                "ALWAYS respond in English only, regardless of what language the user speaks. "
                "You understand all languages but respond ONLY in English. "
                "Do NOT mention the language issue - just answer naturally in English. "
                "When users ask about weather, use the get_weather tool and provide the exact information returned. "
                "When users ask for information you don't know, use the search_web tool to find current information. "
                "When users ask to send email, use the send_email tool with the information they provide. "
                "Do NOT make up information - only use data from your tools. "
                "Be clear, concise, and direct. Do NOT add phrases like 'If you have any other questions' or 'Let me know if you need more help' - just give the information requested."
            ),
            # Добавляем все три инструмента
            tools=[get_weather, search_web, send_email],
        )
        logger.info("OpenAI Assistant agent initialized with weather, search, and email tools")

# -------------------- Entrypoint --------------------
async def entrypoint(ctx: JobContext):
    """Главная точка входа для OpenAI агента"""
    
    logger.info("🚀 Starting OpenAI Assistant entrypoint")
    
    # Подключаемся к комнате
    await ctx.connect()
    logger.info(f"✅ Connected to room: {ctx.room.name}")
    
    # Создаем агента
    agent = OpenAIAssistant()
    
    # ОПТИМАЛЬНАЯ сессия: все через OpenAI, дешево и надежно
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
    
    logger.info("✅ Session created: Whisper STT (EN) + GPT-4o-mini + TTS + Weather + Search + Email")
    
    # ==========================================
    # ПРАВИЛЬНЫЕ события как в примерах LiveKit
    # ==========================================
    
    # ==========================================
    # ПРАВИЛЬНЫЕ СОБЫТИЯ из официальной документации LiveKit
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
    
    # Ошибки
    @session.on("error")
    def on_error(event):
        error = getattr(event, 'error', str(event))
        logger.error(f"❌ [ERROR] {error}")
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
            instructions="Say hello and introduce yourself as a helpful voice assistant."
        )
        logger.info("✅ Initial greeting generated")
    except Exception as e:
        logger.warning(f"⚠️ Could not generate initial greeting: {e}")
        print("🤖 [ASSISTANT] Hello! I'm your voice assistant. How can I help you?")
    
    # Информационное сообщение
    print("\n" + "="*80)
    print("🤖 [OPENAI ASSISTANT] Ready for conversation!")
    print("📋 [INFO] OpenAI Whisper STT (ENGLISH ONLY) + GPT-4o-mini + TTS + Tools")
    print("🔍 [VAD] Silero VAD for speech detection")
    print("💰 [COST] ~$0.02 per minute (very affordable!)")
    print("🌍 [STT] Treats ALL speech as English (no language detection)")
    print("🛠️ [TOOLS] Weather information and web search available")
    print("📝 [LOGGING] All activity logged to agent.log and console")
    print("")
    print("🎯 [TEST COMMANDS] (ALL speech treated as English):")
    print("   • 'What's the weather in London?' → weather tool") 
    print("   • 'Search for latest AI news' → search tool")
    print("   • Any speech → STT treats as English words")
    print("   • Russian/other languages → transcribed as English sounds")
    print("")
    print("🎮 [CONTROLS] Speak into your microphone, press Ctrl+C to quit")
    print("="*80 + "\n")
    print("🎙️ [LISTENING] Start speaking now...")
    
    # Бесконечный цикл для поддержания работы агента
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("👋 [SHUTDOWN] OpenAI Assistant shutting down...")
        print("\n👋 [ASSISTANT] Goodbye!")

# -------------------- Main --------------------
if __name__ == "__main__":
    logger.info("🚀 Starting OpenAI Assistant LiveKit agent application")
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint
        )
    )