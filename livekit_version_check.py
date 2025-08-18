#!/usr/bin/env python3
"""
LiveKit Version Check Script
Проверяет установленные версии всех LiveKit пакетов и их совместимость
"""

import sys
import subprocess
import pkg_resources
from typing import Dict, List, Optional

def get_installed_version(package_name: str) -> Optional[str]:
    """Получить версию установленного пакета"""
    try:
        return pkg_resources.get_distribution(package_name).version
    except pkg_resources.DistributionNotFound:
        return None

def run_pip_list() -> Dict[str, str]:
    """Получить список всех установленных пакетов через pip"""
    try:
        result = subprocess.run([sys.executable, "-m", "pip", "list"], 
                              capture_output=True, text=True, check=True)
        packages = {}
        for line in result.stdout.split('\n')[2:]:  # Пропускаем заголовки
            if line.strip():
                parts = line.split()
                if len(parts) >= 2:
                    packages[parts[0]] = parts[1]
        return packages
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running pip list: {e}")
        return {}

def check_livekit_versions():
    """Проверить все версии LiveKit пакетов"""
    
    print("🔍 [VERSION CHECK] Checking LiveKit package versions...")
    print("=" * 70)
    
    # Основные LiveKit пакеты
    livekit_packages = [
        "livekit",
        "livekit-agents", 
        "livekit-plugins-google",
        "livekit-plugins-silero",
        "livekit-rtc",
        "livekit-api",
    ]
    
    installed_packages = run_pip_list()
    
    print("📦 [LIVEKIT PACKAGES]")
    for package in livekit_packages:
        version = get_installed_version(package)
        pip_version = installed_packages.get(package, "Not found")
        
        if version:
            print(f"   ✅ {package:<25} {version}")
        else:
            print(f"   ❌ {package:<25} NOT INSTALLED")
    
    print("\n🔗 [GOOGLE/GEMINI RELATED]")
    google_packages = [
        "google-genai",
        "google-cloud-aiplatform", 
        "google-auth",
        "google-api-core",
    ]
    
    for package in google_packages:
        version = get_installed_version(package)
        if version:
            print(f"   ✅ {package:<25} {version}")
        else:
            print(f"   ❌ {package:<25} NOT INSTALLED")
    
    print("\n🐍 [PYTHON ENVIRONMENT]")
    print(f"   Python version: {sys.version}")
    print(f"   Python executable: {sys.executable}")
    
    # Дополнительные важные пакеты
    print("\n🛠️ [OTHER DEPENDENCIES]")
    other_packages = [
        "aiohttp",
        "websockets", 
        "numpy",
        "packaging",
    ]
    
    for package in other_packages:
        version = get_installed_version(package)
        if version:
            print(f"   ✅ {package:<25} {version}")
        else:
            print(f"   ⚠️ {package:<25} NOT INSTALLED")
    
    print("=" * 70)
    
    # Проверяем совместимость
    check_compatibility()

def check_compatibility():
    """Проверить совместимость версий для Gemini Live API"""
    
    print("\n🎯 [COMPATIBILITY CHECK for Gemini Live API]")
    
    agents_version = get_installed_version("livekit-agents")
    google_plugin_version = get_installed_version("livekit-plugins-google")
    rtc_version = get_installed_version("livekit-rtc")
    
    # Рекомендуемые минимальные версии для Gemini Live API
    recommended_versions = {
        "livekit-agents": "1.2.0",
        "livekit-plugins-google": "1.2.0", 
        "livekit-rtc": "1.0.10",
    }
    
    print("\n📋 [MINIMUM REQUIRED VERSIONS for Gemini Live API]:")
    
    # Устанавливаем packaging если его нет
    try:
        from packaging import version
    except ImportError:
        print("   ⚠️ Installing packaging for version comparison...")
        subprocess.run([sys.executable, "-m", "pip", "install", "packaging"], check=True)
        from packaging import version
    
    for package, min_version in recommended_versions.items():
        current = get_installed_version(package)
        if current:
            try:
                if version.parse(current) >= version.parse(min_version):
                    print(f"   ✅ {package:<25} {current} (>= {min_version}) ✓")
                else:
                    print(f"   ⚠️ {package:<25} {current} (< {min_version}) ⚠️ UPGRADE NEEDED")
            except Exception as e:
                print(f"   ❓ {package:<25} {current} (can't check version)")
        else:
            print(f"   ❌ {package:<25} NOT INSTALLED")
    
    print("\n💡 [RECOMMENDATIONS]:")
    
    if not agents_version:
        print("   🔸 Install livekit-agents: pip install livekit-agents")
    else:
        try:
            if version.parse(agents_version) < version.parse("1.2.0"):
                print("   🔸 Upgrade livekit-agents: pip install --upgrade livekit-agents")
        except:
            pass
    
    if not google_plugin_version:
        print("   🔸 Install Google plugin: pip install livekit-plugins-google")
    else:
        try:
            if version.parse(google_plugin_version) < version.parse("1.2.0"):
                print("   🔸 Upgrade Google plugin: pip install --upgrade livekit-plugins-google")
        except:
            pass
    
    if not rtc_version:
        print("   🔸 Install livekit-rtc: pip install livekit-rtc")
    else:
        try:
            if version.parse(rtc_version) < version.parse("1.0.10"):
                print("   🔸 Upgrade livekit-rtc: pip install --upgrade livekit-rtc")
        except:
            pass
    
    # Проверяем Google GenAI SDK
    genai_version = get_installed_version("google-genai")
    if not genai_version:
        print("   🔸 Install Google GenAI SDK: pip install google-genai")
    
    print("\n🚀 [QUICK UPGRADE COMMAND]:")
    print("   pip install --upgrade livekit-agents livekit-plugins-google livekit-rtc google-genai")

def test_imports():
    """Тестировать импорты"""
    print("\n🧪 [IMPORT TEST] Testing critical imports...")
    
    tests = [
        ("livekit.agents", "import livekit.agents"),
        ("livekit.plugins.google", "import livekit.plugins.google"),
        ("RealtimeModel", "from livekit.plugins.google.beta.realtime import RealtimeModel"),
        ("google.genai", "from google import genai"),
    ]
    
    for test_name, import_code in tests:
        try:
            exec(import_code)
            print(f"   ✅ {test_name:<20} SUCCESS")
        except ImportError as e:
            print(f"   ❌ {test_name:<20} FAILED: {e}")
        except Exception as e:
            print(f"   ⚠️ {test_name:<20} ERROR: {e}")

def main():
    """Главная функция"""
    try:
        check_livekit_versions()
        test_imports()
        
        print("\n" + "=" * 70)
        print("✅ [DONE] Version check complete!")
        print("💡 [TIP] Run this script after any updates to verify compatibility")
        
    except KeyboardInterrupt:
        print("\n🛑 [INTERRUPTED] Check interrupted by user")
    except Exception as e:
        print(f"\n💥 [ERROR] Unexpected error: {e}")

if __name__ == "__main__":
    main()