#!/usr/bin/env python3
"""
Environment Investigation Script
Исследует виртуальное окружение для поиска недостающих пакетов
"""

import sys
import subprocess
import os
from pathlib import Path

def get_all_packages():
    """Получить все установленные пакеты"""
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

def search_noise_cancellation_packages():
    """Поиск пакетов связанных с noise cancellation"""
    print("🔍 [NOISE CANCELLATION SEARCH] Looking for related packages...")
    
    all_packages = get_all_packages()
    
    # Ключевые слова для поиска
    keywords = ['noise', 'cancellation', 'krisp', 'nvidia', 'audio', 'bvc']
    
    found_packages = []
    for package_name, version in all_packages.items():
        package_lower = package_name.lower()
        if any(keyword in package_lower for keyword in keywords):
            found_packages.append((package_name, version))
    
    if found_packages:
        print("📦 [FOUND AUDIO/NOISE PACKAGES]:")
        for name, version in found_packages:
            print(f"   ✅ {name:<30} {version}")
    else:
        print("   ❌ No noise cancellation packages found")
    
    return found_packages

def check_livekit_plugins():
    """Проверить все установленные livekit плагины"""
    print("\n🔧 [LIVEKIT PLUGINS] Checking all LiveKit plugins...")
    
    all_packages = get_all_packages()
    
    livekit_plugins = []
    for package_name, version in all_packages.items():
        if package_name.startswith('livekit-plugins-'):
            livekit_plugins.append((package_name, version))
    
    if livekit_plugins:
        print("📦 [LIVEKIT PLUGINS INSTALLED]:")
        for name, version in livekit_plugins:
            print(f"   ✅ {name:<35} {version}")
    else:
        print("   ❌ No livekit-plugins found")
    
    return livekit_plugins

def test_noise_cancellation_import():
    """Тестировать различные способы импорта noise_cancellation"""
    print("\n🧪 [IMPORT TEST] Testing different import methods...")
    
    import_tests = [
        ("from livekit.plugins import noise_cancellation", "Standard import"),
        ("from livekit.plugins.krisp import VAD", "Krisp plugin"),
        ("from livekit.plugins.nvidia import VAD", "NVIDIA plugin"),
        ("import livekit.plugins.krisp", "Krisp module"),
        ("import livekit.plugins.nvidia", "NVIDIA module"),
    ]
    
    for import_code, description in import_tests:
        try:
            exec(import_code)
            print(f"   ✅ {description:<20} SUCCESS")
        except ImportError as e:
            print(f"   ❌ {description:<20} FAILED: {e}")
        except Exception as e:
            print(f"   ⚠️ {description:<20} ERROR: {e}")

def check_available_plugins():
    """Проверить доступные плагины для установки"""
    print("\n🌐 [AVAILABLE PLUGINS] Checking PyPI for available LiveKit plugins...")
    
    # Известные LiveKit плагины с noise cancellation
    potential_plugins = [
        "livekit-plugins-krisp",
        "livekit-plugins-nvidia", 
        "livekit-plugins-bvc",
        "livekit-plugins-noise-cancellation",
        "livekit-plugins-audio",
    ]
    
    for plugin in potential_plugins:
        try:
            result = subprocess.run([sys.executable, "-m", "pip", "show", plugin], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print(f"   ✅ {plugin:<35} INSTALLED")
            else:
                # Проверяем доступность в PyPI
                result = subprocess.run([sys.executable, "-m", "pip", "index", "versions", plugin], 
                                      capture_output=True, text=True)
                if "No matching distribution found" not in result.stderr:
                    print(f"   🔍 {plugin:<35} AVAILABLE (not installed)")
                else:
                    print(f"   ❌ {plugin:<35} NOT FOUND")
        except Exception as e:
            print(f"   ⚠️ {plugin:<35} ERROR: {e}")

def show_python_environment():
    """Показать информацию о Python окружении"""
    print("\n🐍 [PYTHON ENVIRONMENT]:")
    print(f"   Python version: {sys.version}")
    print(f"   Python executable: {sys.executable}")
    print(f"   Virtual environment: {os.environ.get('VIRTUAL_ENV', 'Not detected')}")
    
    # Проверяем site-packages
    site_packages = [p for p in sys.path if 'site-packages' in p]
    if site_packages:
        print(f"   Site-packages: {site_packages[0]}")

def generate_comparison_script():
    """Генерировать скрипт для сравнения с другим окружением"""
    script_content = '''
# Скрипт для запуска во ВТОРОМ (рабочем) окружении
# Сохраните как compare_env.py и запустите там

import subprocess
import sys

def export_packages():
    """Экспорт всех пакетов рабочего окружения"""
    try:
        result = subprocess.run([sys.executable, "-m", "pip", "freeze"], 
                              capture_output=True, text=True, check=True)
        
        with open("working_env_packages.txt", "w") as f:
            f.write(result.stdout)
        
        print("✅ Packages exported to working_env_packages.txt")
        print("📋 Copy this file to your current environment")
        
        # Показываем livekit пакеты
        livekit_packages = [line for line in result.stdout.split('\\n') 
                           if 'livekit' in line.lower()]
        
        print("\\n🔧 [LIVEKIT PACKAGES in working environment]:")
        for package in livekit_packages:
            print(f"   {package}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    export_packages()
'''
    
    with open("compare_env.py", "w") as f:
        f.write(script_content)
    
    print("\n📄 [COMPARISON SCRIPT] Generated compare_env.py")
    print("   1. Copy this file to your working environment")
    print("   2. Run: python compare_env.py")
    print("   3. Copy working_env_packages.txt back here")

def main():
    """Главная функция исследования"""
    print("🔍 [ENVIRONMENT INVESTIGATION] Starting investigation...")
    print("=" * 80)
    
    show_python_environment()
    livekit_plugins = check_livekit_plugins()
    noise_packages = search_noise_cancellation_packages()
    test_noise_cancellation_import()
    check_available_plugins()
    generate_comparison_script()
    
    print("\n" + "=" * 80)
    print("🎯 [RECOMMENDATIONS]:")
    
    if not any('krisp' in pkg[0].lower() for pkg in livekit_plugins):
        print("   🔸 Try: pip install livekit-plugins-krisp")
    
    if not any('nvidia' in pkg[0].lower() for pkg in livekit_plugins):
        print("   🔸 Try: pip install livekit-plugins-nvidia")
    
    print("\n📋 [NEXT STEPS]:")
    print("   1. Run compare_env.py in your working environment")
    print("   2. Compare packages list")
    print("   3. Install missing packages")
    
    print("\n🔄 [MANUAL COMPARISON]:")
    print("   In working environment run:")
    print("   pip list | findstr livekit")
    print("   pip freeze > working_packages.txt")

if __name__ == "__main__":
    main()