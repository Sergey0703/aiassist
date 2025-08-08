import asyncio
import logging
import os
import base64
from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    WorkerOptions,
    cli,
    AutoSubscribe,
    get_job_context,
)
from livekit.plugins import openai, silero
from livekit.agents.llm import ChatContext, ChatMessage
from livekit.agents.utils.images import encode, EncodeOptions, ResizeOptions
from livekit import rtc

# Импортируем все три инструмента: погода, поиск и email
from aitools import get_weather, search_web, send_email

# -------------------- Setup --------------------
load_dotenv()

# Правильная настройка логирования как в примерах LiveKit
logger = logging.getLogger("openai-assistant")
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
file_handler = logging.FileHandler("agent.log", encoding='utf-8')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Получаем OpenAI API ключ
openai_api_key = os.getenv("OPENAI_API_KEY")

if not openai_api_key:
    logger.error("OPENAI_API_KEY not found in environment variables")
    raise ValueError("OPENAI_API_KEY is required")

# -------------------- Video Helper Functions --------------------
def encode_frame_to_base64(frame: rtc.VideoFrame) -> str:
    """Кодирует видео кадр в base64 JPEG с оптимальным сжатием"""
    try:
        # Используем LiveKit's encode с оптимальными настройками для GPT-4o-mini
        image_bytes = encode(
            frame,
            EncodeOptions(
                format="JPEG",
                quality=80,  # Баланс качества и размера
                resize_options=ResizeOptions(
                    width=1024,
                    height=1024,
                    strategy="scale_aspect_fit"  # Сохраняем пропорции
                )
            )
        )
        
        # Возвращаем data URL
        base64_str = base64.b64encode(image_bytes).decode('utf-8')
        return f"data:image/jpeg;base64,{base64_str}"
        
    except Exception as e:
        logger.error(f"❌ [VIDEO ENCODE] Error encoding frame: {e}")
        return None

# -------------------- Agent Class with Video --------------------
class OpenAIAssistant(Agent):
    """Голосовой помощник с OpenAI, тремя инструментами и ручной обработкой видео"""
    
    def __init__(self):
        super().__init__(
            instructions=(
                "You are a helpful voice assistant with access to weather information, web search, email sending, and live video from the user's camera. "
                "ALWAYS respond in English only, regardless of what language the user speaks. "
                "You understand all languages but respond ONLY in English. "
                "Do NOT mention the language issue - just answer naturally in English. "
                "When users ask about weather, use the get_weather tool and provide the exact information returned. "
                "When users ask for information you don't know, use the search_web tool to find current information. "
                "When users ask to send email, use the send_email tool with the information they provide. "
                "When users ask about what you see or show you something, describe what you can see in the video. "
                "You have access to live video from the user's camera and can see what they are showing you. "
                "Be specific and detailed when describing what you see - count objects, read text, describe colors and positions. "
                "Do NOT make up information - only use data from your tools or what you actually see in the video. "
                "Be clear, concise, and direct. Do NOT add phrases like 'If you have any other questions' or 'Let me know if you need more help' - just give the information requested."
            ),
            # Все три инструмента
            tools=[get_weather, search_web, send_email],
        )
        
        # Видео обработка
        self._latest_frame = None
        self._video_stream = None
        self._frame_count = 0
        self._last_frame_time = 0
        self._video_tasks = []  # Для отслеживания async задач
        
        logger.info("✅ OpenAI Assistant agent initialized with weather, search, email tools and manual video processing")

    async def on_enter(self):
        """Вызывается когда агент входит в комнату"""
        logger.info("🚀 [AGENT] Agent entered room, setting up video processing...")
        
        # Настраиваем обработку видео
        await self._setup_video_processing()
        
        # Также следим за новыми видео треками
        room = get_job_context().room
        
        @room.on("track_subscribed")
        def on_track_subscribed(track: rtc.Track, publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant):
            if track.kind == rtc.TrackKind.KIND_VIDEO:
                logger.info(f"📹 [VIDEO] New video track subscribed from {participant.identity}")
                asyncio.create_task(self._setup_video_stream(track))

    async def _setup_video_processing(self):
        """Настройка обработки видео из существующих треков"""
        try:
            room = get_job_context().room
            
            # Ищем существующие видео треки
            for participant in room.remote_participants.values():
                logger.info(f"👤 [PARTICIPANT] Checking {participant.identity} for video tracks")
                
                for publication in participant.track_publications.values():
                    track = publication.track
                    if track and track.kind == rtc.TrackKind.KIND_VIDEO:
                        logger.info(f"📹 [VIDEO] Found existing video track from {participant.identity}")
                        await self._setup_video_stream(track)
                        return  # Используем только первый найденный видео трек
            
            logger.info("📹 [VIDEO] No existing video tracks found, waiting for new ones...")
            
        except Exception as e:
            logger.error(f"❌ [VIDEO SETUP] Error setting up video processing: {e}")

    async def _setup_video_stream(self, track: rtc.Track):
        """Настройка потока для конкретного видео трека"""
        try:
            # Закрываем предыдущий поток если есть
            if self._video_stream:
                logger.info("📹 [VIDEO] Closing previous video stream")
                self._video_stream.close()
            
            # Создаем новый поток
            self._video_stream = rtc.VideoStream(track)
            logger.info("📹 [VIDEO] Created new video stream")
            
            # Запускаем обработку кадров
            task = asyncio.create_task(self._process_video_frames())
            self._video_tasks.append(task)
            task.add_done_callback(lambda t: self._video_tasks.remove(t) if t in self._video_tasks else None)
            
            logger.info("✅ [VIDEO] Video stream processing started")
            
        except Exception as e:
            logger.error(f"❌ [VIDEO STREAM] Error setting up video stream: {e}")

    async def _process_video_frames(self):
        """Обрабатывает входящие видео кадры с пропуском для экономии tokens"""
        try:
            logger.info("🎬 [VIDEO FRAMES] Starting frame processing loop with frame skipping")
            
            async for event in self._video_stream:
                try:
                    frame = event.frame
                    self._frame_count += 1
                    
                    # ЭКОНОМИЯ TOKENS: Обрабатываем только каждый 10-й кадр
                    if self._frame_count % 10 != 0:
                        continue
                    
                    # Логируем каждый 30-й обработанный кадр чтобы не спамить
                    if self._frame_count % 30 == 0:
                        logger.info(f"📸 [VIDEO FRAME] Processed {self._frame_count} frames, latest: {frame.width}x{frame.height}")
                    
                    # Кодируем кадр в base64
                    encoded_frame = encode_frame_to_base64(frame)
                    
                    if encoded_frame:
                        # Сохраняем последний кадр для использования в чате
                        self._latest_frame = encoded_frame
                        
                        # Обновляем время последнего кадра
                        import time
                        self._last_frame_time = time.time()
                        
                        # Логируем успешную обработку
                        if self._frame_count % 30 == 0:
                            logger.info(f"✅ [VIDEO FRAME] Successfully encoded frame {self._frame_count} (skipping 9/10 frames)")
                    else:
                        logger.warning(f"⚠️ [VIDEO FRAME] Failed to encode frame {self._frame_count}")
                        
                except Exception as e:
                    logger.error(f"❌ [VIDEO FRAME] Error processing frame {self._frame_count}: {e}")
                    
        except Exception as e:
            logger.error(f"❌ [VIDEO FRAMES] Video frame processing loop ended: {e}")
        
        logger.info("🛑 [VIDEO FRAMES] Frame processing loop ended")

    async def on_user_turn_completed(self, turn_ctx: ChatContext, new_message: ChatMessage) -> None:
        """Вызывается когда пользователь закончил говорить - добавляем видео к его сообщению"""
        try:
            # Проверяем есть ли свежий видео кадр
            if self._latest_frame:
                import time
                frame_age = time.time() - self._last_frame_time
                
                # Используем кадр только если он свежий (не старше 10 секунд)
                if frame_age < 10:
                    # Импортируем ImageContent
                    from livekit.agents.llm import ImageContent
                    
                    # Добавляем видео кадр к сообщению пользователя
                    if hasattr(new_message, 'content') and isinstance(new_message.content, list):
                        new_message.content.append(ImageContent(image=self._latest_frame))
                        logger.info(f"📹 [TURN COMPLETED] Added video frame to user message (frame age: {frame_age:.1f}s)")
                    else:
                        logger.warning("⚠️ [TURN COMPLETED] Could not add video - message content format unexpected")
                else:
                    logger.warning(f"⚠️ [TURN COMPLETED] Video frame too old ({frame_age:.1f}s), skipping")
            else:
                logger.info("📹 [TURN COMPLETED] No video frame available to add to message")
                
        except Exception as e:
            logger.error(f"❌ [TURN COMPLETED] Error adding video to message: {e}")

    def __del__(self):
        """Очистка ресурсов при удалении агента"""
        if self._video_stream:
            try:
                self._video_stream.close()
            except:
                pass

# -------------------- Entrypoint --------------------
async def entrypoint(ctx: JobContext):
    """Главная точка входа для OpenAI агента с видео"""
    
    logger.info("🚀 Starting OpenAI Assistant entrypoint with video support")
    
    # Подключаемся к комнате с автоподпиской на ВСЕ треки (аудио + видео)
    await ctx.connect(auto_subscribe=AutoSubscribe.SUBSCRIBE_ALL)
    logger.info(f"✅ Connected to room: {ctx.room.name} with full auto-subscribe")
    
    # Создаем агента с видео поддержкой
    agent = OpenAIAssistant()
    
    # ОПТИМАЛЬНАЯ сессия с поддержкой видео через ручную обработку
    session = AgentSession(
        # VAD для детекции речи
        vad=silero.VAD.load(),
        
        # OpenAI STT (Whisper) - ПРИНУДИТЕЛЬНО ТОЛЬКО АНГЛИЙСКИЙ!
        stt=openai.STT(
            language="en",  # ПРИНУДИТЕЛЬНО английский - никакой автоопределения!
        ),
        
        # OpenAI LLM - GPT-4 с поддержкой vision (больше лимитов)
        llm=openai.LLM(
            model="gpt-4o",  # Переключаемся на GPT-4o с большими лимитами
            temperature=0.7,
        ),
        
        # OpenAI TTS для озвучки
        tts=openai.TTS(
            voice="alloy",
            speed=1.0,
        ),
        
        # НЕТ автоматического video_sampler - мы делаем это вручную!
    )
    
    logger.info("✅ Session created: Whisper STT (EN) + GPT-4o (vision + higher limits) + TTS + Manual Video Processing + 3 Tools")
    
    # ==========================================
    # ПРАВИЛЬНЫЕ события как в примерах LiveKit
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
        
    # СОБЫТИЯ ДЛЯ ОТЛАДКИ ВИДЕО
    @session.on("participant_connected")
    def on_participant_connected(event):
        """Когда участник подключился"""
        participant = getattr(event, 'participant', None)
        if participant:
            logger.info(f"🔗 [PARTICIPANT] Connected: {participant.identity}")
            print(f"🔗 [PARTICIPANT] {participant.identity} connected")
    
    @session.on("track_subscribed") 
    def on_track_subscribed(event):
        """Когда подписались на трек (аудио/видео)"""
        track = getattr(event, 'track', None)
        participant = getattr(event, 'participant', None)
        if track and participant:
            track_kind = "video" if hasattr(track, 'kind') and str(track.kind) == "KIND_VIDEO" else "audio"
            logger.info(f"📹 [TRACK] Subscribed to {track_kind} from {participant.identity}")
            print(f"📹 [TRACK] Subscribed to {track_kind} from {participant.identity}")
        
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
    
    logger.info("✅ Session started successfully with manual video processing")
    
    # Начальное приветствие
    try:
        await session.generate_reply(
            instructions="Say hello and introduce yourself as a helpful voice assistant that can see through the camera."
        )
        logger.info("✅ Initial greeting generated")
    except Exception as e:
        logger.warning(f"⚠️ Could not generate initial greeting: {e}")
        print("🤖 [ASSISTANT] Hello! I'm your voice assistant with video vision. How can I help you?")
    
    # Информационное сообщение
    print("\n" + "="*80)
    print("🤖 [OPENAI ASSISTANT] Ready for conversation with video vision!")
    print("📋 [INFO] OpenAI Whisper STT (EN) + GPT-4o (vision + higher limits) + TTS + Manual Video + 3 Tools")
    print("🔍 [VAD] Silero VAD for speech detection")
    print("💰 [COST] ~$0.15 per minute (higher but with much better limits)")
    print("⚡ [LIMITS] GPT-4o has 5x higher rate limits than gpt-4o-mini")
    print("🌍 [STT] Treats ALL speech as English (no language detection)")
    print("📹 [VIDEO] Manual video processing - can see what you show (10:1 frame skipping for efficiency)")
    print("🛠️ [TOOLS] Weather, Web Search, and Email sending available")
    print("📝 [LOGGING] All activity logged to agent.log and console")
    print("")
    print("🎯 [TEST COMMANDS] (ALL speech treated as English):")
    print("   • 'What's the weather in London?' → weather tool") 
    print("   • 'Search for latest AI news' → search tool")
    print("   • 'Send email to john@example.com about meeting' → email tool")
    print("   • 'What do you see?' → describes video from camera")
    print("   • 'How many fingers am I showing?' → counts fingers in video")
    print("   • 'Can you read this text?' → reads text from paper/screen")
    print("")
    print("🎮 [CONTROLS] Speak into your microphone, press Ctrl+C to quit")
    print("="*80 + "\n")
    print("🎙️ [LISTENING] Start speaking now...")
    print("📹 [VIDEO] Make sure camera is enabled in LiveKit Playground")
    print("📹 [VIDEO] Manual video processing will start automatically")
    
    # Отладочная информация о состоянии комнаты
    try:
        room_participants = len(ctx.room.remote_participants)
        logger.info(f"🏠 [ROOM] {room_participants} remote participants")
        print(f"🏠 [ROOM] {room_participants} remote participants")
        
        # Проверяем наличие видео треков
        for participant in ctx.room.remote_participants.values():
            video_tracks = [pub for pub in participant.track_publications.values() 
                          if hasattr(pub.track, 'kind') and str(pub.track.kind) == "KIND_VIDEO"]
            logger.info(f"📹 [PARTICIPANT] {participant.identity} has {len(video_tracks)} video tracks")
            print(f"📹 [PARTICIPANT] {participant.identity} has {len(video_tracks)} video tracks")
            
    except Exception as e:
        logger.debug(f"⚠️ [DEBUG] Room info error: {e}")
    
    # Бесконечный цикл для поддержания работы агента
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("👋 [SHUTDOWN] OpenAI Assistant shutting down...")
        print("\n👋 [ASSISTANT] Goodbye!")

# -------------------- Main --------------------
if __name__ == "__main__":
    logger.info("🚀 Starting OpenAI Assistant LiveKit agent application with manual video processing")
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint
        )
    )