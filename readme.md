# 🤖 Gemini Voice Assistant with N8N Integration

Multimodal voice assistant powered by Google Gemini Realtime Model with N8N workflow integration for weather, trade analysis, calendar management, web search, and email functionality.

## 📋 Prerequisites

- **Python 3.8+** (Recommended: Python 3.11)
- **Windows 10/11**
- **Google API Key** (for Gemini Realtime Model)
- **N8N Instance** (running on auto2025system.duckdns.org)
- **Optional**: Tavily API Key (for web search)
- **Optional**: Email credentials (Gmail, Outlook, etc.)

## 🚀 Quick Start Guide

### Step 1: Clone the Repository
```bash
git clone <your-repository-url>
cd gemini-voice-assistant

###Step 2: Create Virtual Environment (Windows)

Method 1: Using Python venv (Recommended)

# Create virtual environment
python -m venv gemini_env

# Activate virtual environment
gemini_env\Scripts\activate

# You should see (gemini_env) in your command prompt

Method 2: Using Python with specific version
cmd# If you have multiple Python versions
py -3.11 -m venv gemini_env

# Activate
gemini_env\Scripts\activate

###Step 3: Install Dependencies
cmd# Make sure virtual environment is activated
pip install --upgrade pip

# Install requirements
pip install -r requirements.txt

# If requirements.txt doesn't exist, install manually:
pip install livekit-agents livekit-plugins-google livekit-plugins-noise-cancellation
pip install aiohttp python-dotenv

Step 4: Environment Configuration
Create .env file in the project root:
env# Google API Configuration (REQUIRED)
GOOGLE_API_KEY=your_google_api_key_here

# Web Search (Optional)
TAVILY_API_KEY=your_tavily_api_key_here

# Email Configuration (Optional)
EMAIL_PROVIDER=gmail
GMAIL_USER=your.email@gmail.com
GMAIL_APP_PASSWORD=your_app_password

# OR for demo mode
EMAIL_DEMO_MODE=true

# N8N Configuration (Already configured)
N8N_BASE_URL=https://auto2025system.duckdns.org

🎮 Running the Application
Method 1: Development Mode (Recommended for testing)
cmd# Activate virtual environment first
venv\Scripts\activate

python agentn8n_gemini_video.py console
# Run in development mode with auto-reload
python agentn8n_gemini_video.py dev

🛠️ Development Commands
Test Individual Tools
cmd# Test all tools
python tools/__init__.py

# Quick validation
python tools/__init__.py --quick

# Test specific modules
python tools/n8n_tools.py
python tools/n8n_trade_tools.py
python tools/n8n_calendar_tools.py
python tools/web_tools.py
python tools/email_tools.py



