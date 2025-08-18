#!/usr/bin/env python3
"""
Установка всех недостающих пакетов из рабочего окружения
"""

import subprocess
import sys

# Список всех недостающих пакетов
missing_packages = [
    "backoff==2.2.1",
    "beautifulsoup4==4.13.4", 
    "cerebras_cloud_sdk==1.46.0",
    "comtypes==1.4.11",
    "dataclasses-json==0.6.7",
    "distro==1.9.0",
    "duckduckgo_search==8.1.1",
    "greenlet==3.2.3",
    "groq==0.31.0",
    "h2==4.2.0",
    "hpack==4.1.0",
    "httpx-sse==0.4.1",
    "hyperframe==6.1.0",
    "jiter==0.10.0",
    "jsonpatch==1.33",
    "jsonpointer==3.0.0",
    "langchain==0.3.27",
    "langchain-community==0.3.27",
    "langchain-core==0.3.72",
    "langchain-text-splitters==0.3.9",
    "langsmith==0.4.11",
    "livekit-plugins-assemblyai==1.2.4",
    "livekit-plugins-deepgram==1.2.3",
    "livekit-plugins-elevenlabs==1.2.3",
    "livekit-plugins-groq==1.2.4",
    "livekit-plugins-openai==1.2.4",
    "lxml==6.0.0",
    "marshmallow==3.26.1",
    "mem0ai==0.1.115",
    "mypy_extensions==1.1.0",
    "openai==1.99.9",
    "orjson==3.11.1",
    "pillow==11.3.0",
    "portalocker==3.2.0",
    "posthog==6.3.3",
    "primp==0.15.0",
    "pydantic-settings==2.10.1",
    "pypiwin32==223",
    "python-dateutil==2.9.0.post0",
    "pyttsx3==2.99",
    "pytz==2025.2",
    "pywin32==311",
    "pyyaml==6.0.2",
    "qdrant-client==1.15.1",
    "requests-toolbelt==1.0.0",
    "setuptools==80.9.0",
    "six==1.17.0",
    "soupsieve==2.7",
    "sqlalchemy==2.0.42",
    "tqdm==4.67.1",
    "typing-inspect==0.9.0",
    "wheel==0.45.1",
    "zstandard==0.23.0"
]

def install_packages():
    """Установка всех пакетов"""
    print("🚀 [FULL INSTALL] Installing ALL missing packages...")
    print(f"📦 [TOTAL] {len(missing_packages)} packages will be installed")
    print("⏱️ [TIME] This may take 5-10 minutes")
    print("=" * 60)
    
    success_count = 0
    failed_packages = []
    
    for i, package in enumerate(missing_packages, 1):
        print(f"\n📦 [{i}/{len(missing_packages)}] Installing {package}...")
        
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", package],
                capture_output=True,
                text=True,
                check=True
            )
            print(f"   ✅ SUCCESS: {package}")
            success_count += 1
            
        except subprocess.CalledProcessError as e:
            print(f"   ❌ FAILED: {package}")
            print(f"      Error: {e.stderr.strip()}")
            failed_packages.append(package)
            
        except Exception as e:
            print(f"   ⚠️ ERROR: {package} - {e}")
            failed_packages.append(package)
    
    # Итоги
    print("\n" + "=" * 60)
    print("📊 [INSTALLATION SUMMARY]:")
    print(f"   ✅ Successful: {success_count}/{len(missing_packages)}")
    print(f"   ❌ Failed: {len(failed_packages)}/{len(missing_packages)}")
    
    if failed_packages:
        print(f"\n❌ [FAILED PACKAGES]:")
        for pkg in failed_packages:
            print(f"   📦 {pkg}")
        
        print(f"\n🔄 [RETRY COMMAND]:")
        retry_cmd = f"pip install {' '.join(failed_packages)}"
        print(f"   {retry_cmd}")
    
    if success_count == len(missing_packages):
        print(f"\n🎉 [PERFECT!] All packages installed successfully!")
    elif success_count > len(missing_packages) * 0.8:  # 80% успешности
        print(f"\n✅ [GOOD!] Most packages installed successfully!")
    else:
        print(f"\n⚠️ [ISSUES] Many packages failed to install")
    
    print(f"\n🧪 [NEXT STEPS]:")
    print(f"   1. Test import: python -c \"from livekit.plugins import noise_cancellation\"")
    print(f"   2. Run agent: python agentn8n_gemini_video.py dev")
    print(f"   3. Check video recognition quality")

def main():
    """Главная функция"""
    try:
        install_packages()
    except KeyboardInterrupt:
        print(f"\n🛑 [INTERRUPTED] Installation cancelled by user")
    except Exception as e:
        print(f"\n💥 [ERROR] Unexpected error: {e}")

if __name__ == "__main__":
    main()