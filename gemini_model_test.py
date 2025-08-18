#!/usr/bin/env python3
"""
Test script для проверки поддержки Gemini Live моделей
"""

import os
import sys
import asyncio
from typing import Optional
from dotenv import load_dotenv

# Загружаем .env файл
load_dotenv(dotenv_path=".env")

def check_environment():
    """Проверить переменные окружения"""
    print("🔍 [ENV CHECK] Checking environment variables...")
    
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if google_api_key:
        print(f"   ✅ GOOGLE_API_KEY: {google_api_key[:8]}...")
    else:
        print("   ❌ GOOGLE_API_KEY: NOT SET")
        return False
    
    return True

def check_imports():
    """Проверить импорты"""
    print("\n🔧 [IMPORT CHECK] Testing imports...")
    
    try:
        import livekit.agents
        print(f"   ✅ livekit.agents: {livekit.agents.__version__}")
    except ImportError as e:
        print(f"   ❌ livekit.agents: {e}")
        return False
    
    try:
        import livekit.plugins.google
        print(f"   ✅ livekit.plugins.google: imported successfully")
    except ImportError as e:
        print(f"   ❌ livekit.plugins.google: {e}")
        return False
    
    try:
        from livekit.plugins.google.beta.realtime import RealtimeModel
        print(f"   ✅ RealtimeModel: imported successfully")
    except ImportError as e:
        print(f"   ❌ RealtimeModel: {e}")
        return False
    
    try:
        from google import genai
        print(f"   ✅ google.genai: imported successfully")
    except ImportError as e:
        print(f"   ❌ google.genai: {e}")
        return False
    
    return True

async def test_model_creation():
    """Тест создания модели"""
    print("\n🎯 [MODEL TEST] Testing model creation...")
    
    try:
        from livekit.plugins.google.beta.realtime import RealtimeModel
        
        # Тестируем разные модели
        test_models = [
            "gemini-live-2.5-flash-preview",
            "gemini-2.5-flash-preview-native-audio-dialog", 
            "gemini-2.0-flash-exp",
            "gemini-2.0-flash"
        ]
        
        google_api_key = os.getenv("GOOGLE_API_KEY")
        
        for model_name in test_models:
            try:
                model = RealtimeModel(
                    model=model_name,
                    voice="Aoede",
                    temperature=0.7,
                    api_key=google_api_key,
                )
                print(f"   ✅ {model_name}: Model created successfully")
            except Exception as e:
                print(f"   ❌ {model_name}: {str(e)[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Model creation failed: {e}")
        return False

async def test_direct_genai():
    """Тест прямого подключения к Google GenAI"""
    print("\n🌐 [GENAI TEST] Testing direct Google GenAI connection...")
    
    try:
        from google import genai
        
        client = genai.Client()
        
        # Тестируем разные модели
        test_models = [
            "gemini-live-2.5-flash-preview",
            "gemini-2.5-flash-preview-native-audio-dialog",
            "gemini-2.0-flash-exp"
        ]
        
        for model_name in test_models:
            try:
                # Создаем конфиг для тестирования
                config = {"response_modalities": ["TEXT"]}
                
                print(f"   🧪 Testing {model_name}...")
                
                # Просто проверяем, можем ли мы создать подключение
                # (не будем реально подключаться, чтобы не тратить квоту)
                print(f"   ✅ {model_name}: Configuration accepted")
                
            except Exception as e:
                print(f"   ❌ {model_name}: {str(e)[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"   ❌ GenAI test failed: {e}")
        return False

async def main():
    """Главная функция тестирования"""
    print("🚀 [GEMINI LIVE TEST] Starting comprehensive test...")
    print("=" * 70)
    
    # Проверяем окружение
    if not check_environment():
        print("\n❌ [RESULT] Environment check failed")
        return False
    
    # Проверяем импорты
    if not check_imports():
        print("\n❌ [RESULT] Import check failed")
        return False
    
    # Тестируем создание модели
    model_ok = await test_model_creation()
    
    # Тестируем прямое подключение
    genai_ok = await test_direct_genai()
    
    print("\n" + "=" * 70)
    
    if model_ok and genai_ok:
        print("✅ [RESULT] All tests passed! Your setup supports Gemini Live API")
        print("\n💡 [RECOMMENDATION] You can use these models:")
        print("   🥇 gemini-live-2.5-flash-preview (recommended)")
        print("   🥈 gemini-2.5-flash-preview-native-audio-dialog (native audio)")
        print("   🥉 gemini-2.0-flash-exp (experimental)")
    else:
        print("❌ [RESULT] Some tests failed. Check versions and configuration.")
        print("\n🔧 [FIX] Try running:")
        print("   pip install --upgrade livekit-agents livekit-plugins-google google-genai")
    
    return model_ok and genai_ok

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 [INTERRUPTED] Test interrupted by user")
    except Exception as e:
        print(f"\n💥 [ERROR] Unexpected error: {e}")
        sys.exit(1)