from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    RunContext,
    WorkerOptions,
    cli,
    function_tool,
)
from livekit.plugins import groq, silero
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")

# Копируем ваши инструменты напрямую в код (без внешних импортов)
@function_tool
async def lookup_weather(
    context: RunContext,
    location: str,
):
    """Used to look up weather information."""
    return {"weather": "sunny", "temperature": 70}

@function_tool
async def search_web(
    context: RunContext,
    query: str,
):
    """Search the web for information."""
    return {"results": f"Search results for: {query}"}

@function_tool
async def send_email(
    context: RunContext,
    to: str,
    subject: str,
    body: str = "",
):
    """Send an email."""
    return {"status": "Email sent", "to": to, "subject": subject}

async def entrypoint(ctx: JobContext):
    await ctx.connect()

    agent = Agent(
        instructions="""
            You are AIAssist, a sarcastic and witty digital butler inspired by JARVIS from Iron Man.
            You are professional but with a dry sense of humor and occasional sarcasm.
            Keep responses concise but engaging. Address the user as "sir" or "boss" occasionally.
            You are helpful, intelligent, and slightly condescending in a charming way.
            
            Start every conversation by greeting the user.
            Use the tools when specifically requested:
            - lookup_weather: Only when user asks for weather information
            - search_web: Only when user asks to search for something
            - send_email: Only when user asks to send an email
            Never assume a location or provide data without a request.
            """,
        tools=[lookup_weather, search_web, send_email],
    )
    
    session = AgentSession(
        vad=silero.VAD.load(),
        # ТОЧНО такие же параметры как в вашей рабочей версии
        stt=groq.STT(),  
        llm=groq.LLM(model="llama-3.3-70b-versatile"),
        tts=groq.TTS(model="playai-tts"), 
    )

    await session.start(agent=agent, room=ctx.room)
    await session.generate_reply(instructions="Greet the user as AIAssist, their sarcastic digital butler. Be witty and ask how you can help them today.")

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))