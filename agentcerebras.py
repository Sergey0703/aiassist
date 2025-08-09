import asyncio
import logging
import os
import base64
import time
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
from livekit.plugins import openai, silero, google, assemblyai
from livekit.agents.llm import ChatContext, ChatMessage, ImageContent
from livekit.agents.utils.images import encode, EncodeOptions, ResizeOptions
from livekit import rtc

# Импортируем все инструменты: погода, поиск и email
from toolscerebras import get_weather, search_web, send_email, test_cerebras

# -------------------- Setup --------------------
load_dotenv()

# Настройка логирования как в оригинале
logger = logging.getLogger("cerebras-assistant")
logger.setLevel(logging.INFO)

formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

file_handler = logging.FileHandler("cerebras_agent.log", encoding='utf-8')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Получаем API ключи
openai_api_key = os.getenv("OPENAI_API_KEY")
google_api_key = os.getenv("GOOGLE_API_KEY")
enable_video = os.getenv("ENABLE_VIDEO", "true").lower() == "true"

if not openai_api_key:
    logger.error("OPENAI_API_KEY not found in environment variables")
    raise ValueError("OPENAI_API_KEY is required")

if enable_video and not google_api_key:
    logger.error("GOOGLE_API_KEY not found but video is enabled")
    raise ValueError("GOOGLE_API_KEY is required when ENABLE_VIDEO=true")

logger.info(f"🎬 [CONFIG] Video processing: {'ENABLED' if enable_video else 'DISABLED'}")

# -------------------- Video Helper Functions (как в оригинале) --------------------
def encode_frame_to_base64(frame: rtc.VideoFrame) -> str:
    """Кодирует видео кадр в base64 JPEG для Gemini"""
    try:
        image_bytes = encode(
            frame,
            EncodeOptions(
                format="JPEG",
                quality=70,
                resize_options=ResizeOptions(
                    width=512,
                    height=512,
                    strategy="scale_aspect_fit"
                )
            )
        )
        
        base64_str = base64.b64encode(image_bytes).decode('utf-8')
        return f"data:image/jpeg;base64,{base64_str}"
        
    except Exception as e:
        logger.error(f"❌ [VIDEO ENCODE] Error encoding frame: {e}")
        return None

# -------------------- Agent Class (упрощенная версия) --------------------
class CerebrasHybridAssistant(Agent):
    """Простой гибридный помощник: OpenAI для основной работы + опциональное видео через Gemini"""
    
    def __init__(self):
        super().__init__(
            instructions=(
                "You are a helpful voice assistant. "
                "ALWAYS respond in English only. "
                "Be EXTREMELY concise - use MAXIMUM 1-2 short sentences. NEVER more than 20 words total. "
                "When users ask about weather, use get_weather tool. "
                "When users ask for web info, use search_web tool. "
                "When users ask to send email, use send_email tool. "
                f"{'You have access to live video analysis. ' if enable_video else ''}"
                "When video information is available, incorporate it naturally into responses. "
                "Be specific when describing what you see. "
                "Do NOT add phrases like 'How can I help' - just answer directly and stop."
            ),
            tools=[] #tools=[get_weather, search_web, send_email, test_cerebras],
        )
        
        # Видео обработка (опционально)
        self._latest_frame = None
        self._video_stream = None
        self._frame_count = 0
        self._last_frame_time = 0
        self._video_tasks = []
        self._gemini_llm = None
        self._latest_video_description = None
        
        logger.info(f"✅ Cerebras Assistant initialized (Video: {'ON' if enable_video else 'OFF'})")

    async def on_enter(self):
        """Вызывается когда агент входит в комнату"""
        logger.info("🚀 [AGENT] Agent entered room")
        
        if enable_video:
            logger.info("📹 [VIDEO] Setting up video processing...")
            try:
                self._gemini_llm = google.LLM(
                    model="gemini-1.5-flash",
                    temperature=0.1,
                )
                logger.info("✅ [GEMINI] LLM created for video analysis")
            except Exception as e:
                logger.error(f"❌ [GEMINI] Failed to create LLM: {e}")
                return
            
            await self._setup_video_processing()
            
            room = get_job_context().room
            
            @room.on("track_subscribed")
            def on_track_subscribed(track: rtc.Track, publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant):
                if track.kind == rtc.TrackKind.KIND_VIDEO:
                    logger.info(f"📹 [VIDEO] New video track from {participant.identity}")
                    asyncio.create_task(self._setup_video_stream(track))
        else:
            logger.info("📹 [VIDEO] Video processing disabled")

    async def _setup_video_processing(self):
        """Настройка обработки видео"""
        if not enable_video:
            return
            
        try:
            room = get_job_context().room
            
            for participant in room.remote_participants.values():
                logger.info(f"👤 [PARTICIPANT] Checking {participant.identity} for video tracks")
                
                for publication in participant.track_publications.values():
                    track = publication.track
                    if track and track.kind == rtc.TrackKind.KIND_VIDEO:
                        logger.info(f"📹 [VIDEO] Found existing video track from {participant.identity}")
                        await self._setup_video_stream(track)
                        return
            
            logger.info("📹 [VIDEO] No existing video tracks found, waiting for new ones...")
            
        except Exception as e:
            logger.error(f"❌ [VIDEO SETUP] Error: {e}")

    async def _setup_video_stream(self, track: rtc.Track):
        """Настройка потока для видео"""
        if not enable_video:
            return
            
        try:
            if self._video_stream:
                logger.info("📹 [VIDEO] Closing previous video stream")
                self._video_stream.close()
            
            self._video_stream = rtc.VideoStream(track)
            logger.info("📹 [VIDEO] Created new video stream")
            
            task = asyncio.create_task(self._process_video_frames())
            self._video_tasks.append(task)
            task.add_done_callback(lambda t: self._video_tasks.remove(t) if t in self._video_tasks else None)
            
            logger.info("✅ [VIDEO] Video stream processing started")
            
        except Exception as e:
            logger.error(f"❌ [VIDEO STREAM] Error: {e}")

    async def _process_video_frames(self):
        """Обрабатывает видео кадры через Gemini"""
        if not enable_video:
            return
            
        try:
            logger.info("🎬 [VIDEO] Starting Gemini video analysis loop")
            
            async for event in self._video_stream:
                try:
                    frame = event.frame
                    self._frame_count += 1
                    
                    # Обрабатываем каждый 60-й кадр
                    if self._frame_count % 60 != 0:
                        continue
                    
                    if self._frame_count % 60 == 0:
                        logger.info(f"📸 [VIDEO] Processing frame {self._frame_count}")
                    
                    encoded_frame = encode_frame_to_base64(frame)
                    
                    if encoded_frame:
                        self._latest_frame = encoded_frame
                        asyncio.create_task(self._analyze_frame_with_gemini(encoded_frame))
                        self._last_frame_time = time.time()
                        logger.info(f"✅ [VIDEO] Sent frame {self._frame_count} to Gemini")
                        
                except Exception as e:
                    logger.error(f"❌ [VIDEO] Error processing frame {self._frame_count}: {e}")
                    
        except Exception as e:
            logger.error(f"❌ [VIDEO] Video loop ended: {e}")
        
        logger.info("🛑 [VIDEO] Gemini video analysis loop ended")

    async def _analyze_frame_with_gemini(self, encoded_frame: str):
        """Анализирует видео кадр через Gemini"""
        if not enable_video or not self._gemini_llm:
            return
            
        try:
            video_context = ChatContext()
            image_content = ImageContent(image=encoded_frame)
            
            video_context.append(
                role="user",
                text="Analyze this image briefly. Describe what you see in 10 words or less. Focus on people, objects, actions.",
                images=[image_content]
            )
            
            logger.info("🧠 [GEMINI] Sending frame for analysis...")
            
            chat_stream = self._gemini_llm.chat(chat_ctx=video_context)
            
            response_text = ""
            async for chunk in chat_stream:
                if chunk.text:
                    response_text += chunk.text
            
            if response_text:
                self._latest_video_description = response_text.strip()
                logger.info(f"✅ [GEMINI] Video analysis: '{self._latest_video_description}'")
            else:
                logger.warning("⚠️ [GEMINI] No response from Gemini")
                
        except Exception as e:
            logger.error(f"❌ [GEMINI] Error in video analysis: {e}")
            self._latest_video_description = None

    async def on_user_turn_completed(self, turn_ctx: ChatContext, new_message: ChatMessage) -> None:
        """Добавляем описание видео к контексту"""
        if not enable_video:
            return
            
        try:
            if self._latest_video_description:
                frame_age = time.time() - self._last_frame_time
                
                if frame_age < 10:
                    if hasattr(new_message, 'content') and isinstance(new_message.content, list):
                        video_context = f"[Video context: {self._latest_video_description}]"
                        new_message.content.append(video_context)
                        logger.info(f"📹 [HYBRID] Added video context: '{self._latest_video_description}'")
                    else:
                        logger.warning("⚠️ [HYBRID] Could not add video description")
                else:
                    logger.warning(f"⚠️ [HYBRID] Video description too old ({frame_age:.1f}s)")
            else:
                logger.info("📹 [HYBRID] No video description available")
                
        except Exception as e:
            logger.error(f"❌ [HYBRID] Error adding video description: {e}")

# -------------------- Entrypoint (упрощенный) --------------------
async def entrypoint(ctx: JobContext):
    """Главная точка входа"""
    
    logger.info("🚀 Starting Cerebras Assistant entrypoint")
    
    await ctx.connect(auto_subscribe=AutoSubscribe.SUBSCRIBE_ALL)
    logger.info(f"✅ Connected to room: {ctx.room.name}")
    
    agent = CerebrasHybridAssistant()
    
    # ОБЫЧНАЯ сессия как в оригинале, но позже заменим LLM на Cerebras
    session = AgentSession(
        vad=silero.VAD.load(),
        
        stt=openai.STT(language="en",),
        #stt=assemblyai.STT(),
        
        # Пока оставляем OpenAI LLM (позже заменим на Cerebras)
        #llm=openai.LLM(
        #    model="gpt-4o-mini",
        #    temperature=0.2,
        #),
       llm=openai.LLM(
            model="llama-3.1-8b",
            temperature=0.2,
            base_url="https://api.cerebras.ai/v1",  # Cerebras endpoint
            api_key=os.getenv("CEREBRAS_API_KEY"),
            #tool_choice="auto",
        ),
        
        tts=openai.TTS(
            voice="alloy",
            speed=1.2,
            model="tts-1-hd",
        ),
    )
    
    video_status = "Gemini (video analysis)" if enable_video else "DISABLED"
    logger.info(f"✅ Session created: Whisper STT + OpenAI LLM + {video_status} + TTS + 3 Tools")
    
    # События LiveKit (как в оригинале)
    @session.on("user_input_transcribed")
    def on_user_input_transcribed(event):
        transcript = getattr(event, 'transcript', 'No transcript')
        is_final = getattr(event, 'is_final', False)
        if is_final:
            logger.info(f"👤 [USER FINAL] {transcript}")
            print(f"\n👤 [USER] {transcript}")
    
    @session.on("conversation_item_added")
    def on_conversation_item_added(event):
        item = getattr(event, 'item', None)
        if item:
            role = getattr(item, 'role', 'unknown')
            content = getattr(item, 'text_content', '') or str(getattr(item, 'content', ''))
            
            if role == "user":
                logger.info(f"💬 [CHAT USER] {content}")
                print(f"💬 [CHAT USER] {content}")
            elif role == "assistant":
                logger.info(f"💬 [CHAT ASSISTANT] {content}")
                print(f"💬 [CHAT ASSISTANT] {content}")
                print("-" * 60)
    
    @session.on("speech_created")
    def on_speech_created(event):
        logger.info("🔊 [SPEECH CREATED] Agent is about to speak")
        print("🔊 [ASSISTANT] Creating speech...")
    
    @session.on("agent_state_changed")
    def on_agent_state_changed(event):
        old_state = getattr(event, 'old_state', 'unknown')
        new_state = getattr(event, 'new_state', 'unknown')
        logger.info(f"🔄 [AGENT STATE] {old_state} -> {new_state}")
        print(f"🔄 [AGENT] {old_state} -> {new_state}")
    
    @session.on("function_tools_executed")
    def on_function_tools_executed(event):
        logger.info("🛠️ [TOOLS EXECUTED] Function tools completed")
        print("🛠️ [TOOLS] Function executed - processing result...")
        
    @session.on("error")
    def on_error(event):
        error = getattr(event, 'error', str(event))
        logger.error(f"❌ [ERROR] {error}")
        print(f"❌ [ERROR] {error}")
    
    # Запускаем сессию
    await session.start(
        agent=agent,
        room=ctx.room,
    )
    
    logger.info("✅ Session started successfully")
    
    # Начальное приветствие
    try:
        greeting = f"Say hello briefly as a voice assistant{'with video vision' if enable_video else ''}."
        await session.generate_reply(instructions=greeting)
        logger.info("✅ Initial greeting generated")
    except Exception as e:
        logger.warning(f"⚠️ Could not generate initial greeting: {e}")
        greeting_text = f"Hello! I'm your voice assistant{' with video vision' if enable_video else ''}."
        print(f"🤖 [ASSISTANT] {greeting_text}")
    
    # Информационное сообщение
    print("\n" + "="*80)
    print("🤖 [ASSISTANT] Simplified version working!")
    print(f"📋 [INFO] OpenAI STT + OpenAI LLM (temp) + {video_status} + OpenAI TTS")
    print("🔍 [VAD] Silero VAD for speech detection")
    print("🌍 [STT] English only")
    if enable_video:
        print("📹 [VIDEO] Gemini video analysis enabled")
    else:
        print("📹 [VIDEO] DISABLED")
    print("🛠️ [TOOLS] Weather, Web Search, and Email available")
    print("")
    print("🎯 [TEST COMMANDS]:")
    print("   • 'What's the weather in London?'")
    print("   • 'Search for latest AI news'")
    print("   • 'Send email to test@example.com'")
    if enable_video:
        print("   • 'What do you see?'")
    print("")
    print("🎮 [CONTROLS] Speak into microphone, Ctrl+C to quit")
    print("="*80 + "\n")
    print("🎙️ [LISTENING] Start speaking now...")
    
    # Бесконечный цикл
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("👋 [SHUTDOWN] Assistant shutting down...")
        print("\n👋 [ASSISTANT] Goodbye!")

# -------------------- Main --------------------
if __name__ == "__main__":
    logger.info("🚀 Starting Cerebras Assistant application")
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint
        )
    )