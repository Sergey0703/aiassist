#!/usr/bin/env python3
"""
Environment Comparison Scripts
Для точного сравнения двух виртуальных окружений
"""

import sys
import subprocess
import json
import os
from pathlib import Path

# ==================== СКРИПТ 1: ЭКСПОРТ РАБОЧЕГО ОКРУЖЕНИЯ ====================
def export_working_environment():
    """
    ЗАПУСТИТЕ ЭТОТ СКРИПТ В РАБОЧЕМ ОКРУЖЕНИИ
    Создает подробный отчет об установленных пакетах
    """
    print("🔍 [WORKING ENV EXPORT] Exporting working environment details...")
    
    # 1. Получаем список всех пакетов
    try:
        result = subprocess.run([sys.executable, "-m", "pip", "list", "--format=json"], 
                              capture_output=True, text=True, check=True)
        packages_json = json.loads(result.stdout)
        
        # 2. Получаем pip freeze (точные версии)
        freeze_result = subprocess.run([sys.executable, "-m", "pip", "freeze"], 
                                     capture_output=True, text=True, check=True)
        
        # 3. Собираем информацию об окружении
        env_info = {
            "python_version": sys.version,
            "python_executable": sys.executable,
            "virtual_env": os.environ.get('VIRTUAL_ENV', 'Not detected'),
            "site_packages": [p for p in sys.path if 'site-packages' in p],
            "packages_json": packages_json,
            "pip_freeze": freeze_result.stdout.split('\n'),
            "livekit_packages": [pkg for pkg in packages_json if 'livekit' in pkg['name'].lower()],
            "google_packages": [pkg for pkg in packages_json if 'google' in pkg['name'].lower()],
            "audio_packages": [pkg for pkg in packages_json if any(keyword in pkg['name'].lower() 
                              for keyword in ['audio', 'noise', 'sound', 'speech', 'voice'])],
        }
        
        # 4. Сохраняем в файл
        with open("working_environment.json", "w", encoding='utf-8') as f:
            json.dump(env_info, f, indent=2, ensure_ascii=False)
        
        # 5. Создаем простой requirements.txt
        with open("working_requirements.txt", "w", encoding='utf-8') as f:
            f.write(freeze_result.stdout)
        
        print("✅ [EXPORT SUCCESS] Files created:")
        print("   📄 working_environment.json - подробная информация")
        print("   📄 working_requirements.txt - список пакетов для pip install")
        
        # 6. Показываем ключевые пакеты
        print("\n🔧 [KEY PACKAGES in working environment]:")
        for pkg in env_info['livekit_packages']:
            print(f"   ✅ {pkg['name']:<35} {pkg['version']}")
        
        print("\n🤖 [GOOGLE PACKAGES in working environment]:")
        for pkg in env_info['google_packages']:
            print(f"   ✅ {pkg['name']:<35} {pkg['version']}")
        
        return True
        
    except Exception as e:
        print(f"❌ [EXPORT ERROR] {e}")
        return False

# ==================== СКРИПТ 2: СРАВНЕНИЕ ОКРУЖЕНИЙ ====================
def compare_environments():
    """
    ЗАПУСТИТЕ ЭТОТ СКРИПТ В ТЕКУЩЕМ ОКРУЖЕНИИ
    Сравнивает с экспортированным рабочим окружением
    """
    print("🔍 [ENVIRONMENT COMPARISON] Comparing environments...")
    
    # 1. Проверяем наличие файла от рабочего окружения
    if not Path("working_environment.json").exists():
        print("❌ [ERROR] working_environment.json not found!")
        print("💡 [SOLUTION] Run export_working_environment() in your working environment first")
        return False
    
    # 2. Загружаем данные рабочего окружения
    try:
        with open("working_environment.json", "r", encoding='utf-8') as f:
            working_env = json.load(f)
    except Exception as e:
        print(f"❌ [ERROR] Failed to load working environment: {e}")
        return False
    
    # 3. Получаем данные текущего окружения
    try:
        result = subprocess.run([sys.executable, "-m", "pip", "list", "--format=json"], 
                              capture_output=True, text=True, check=True)
        current_packages = json.loads(result.stdout)
        current_dict = {pkg['name'].lower(): pkg['version'] for pkg in current_packages}
        
    except Exception as e:
        print(f"❌ [ERROR] Failed to get current environment: {e}")
        return False
    
    # 4. Сравниваем пакеты
    working_dict = {pkg['name'].lower(): pkg['version'] for pkg in working_env['packages_json']}
    
    missing_packages = []
    version_differences = []
    
    for pkg_name, version in working_dict.items():
        if pkg_name not in current_dict:
            missing_packages.append((pkg_name, version))
        elif current_dict[pkg_name] != version:
            version_differences.append((pkg_name, current_dict[pkg_name], version))
    
    # 5. Показываем результаты
    print(f"\n📊 [COMPARISON RESULTS]:")
    print(f"   Working environment: {len(working_dict)} packages")
    print(f"   Current environment: {len(current_dict)} packages")
    print(f"   Missing packages: {len(missing_packages)}")
    print(f"   Version differences: {len(version_differences)}")
    
    if missing_packages:
        print(f"\n❌ [MISSING PACKAGES] ({len(missing_packages)} packages):")
        for name, version in missing_packages:
            print(f"   📦 {name}=={version}")
        
        # Создаем команду для установки
        missing_list = [f"{name}=={version}" for name, version in missing_packages]
        install_command = f"pip install {' '.join(missing_list)}"
        
        print(f"\n🚀 [INSTALL COMMAND]:")
        print(f"pip install \\")
        for i, pkg in enumerate(missing_list):
            if i == len(missing_list) - 1:
                print(f"  {pkg}")
            else:
                print(f"  {pkg} \\")
        
        # Сохраняем команду в файл
        with open("install_missing.bat", "w") as f:
            f.write(install_command)
        
        print(f"\n💾 [SAVED] Install command saved to: install_missing.bat")
    
    if version_differences:
        print(f"\n⚠️ [VERSION DIFFERENCES] ({len(version_differences)} packages):")
        for name, current_ver, working_ver in version_differences:
            print(f"   📦 {name:<30} current: {current_ver:<10} working: {working_ver}")
    
    if not missing_packages and not version_differences:
        print(f"\n✅ [PERFECT MATCH] Environments are identical!")
    
    return True

# ==================== СКРИПТ 3: ФОКУС НА LIVEKIT ====================
def focus_on_livekit():
    """Сравнение только LiveKit пакетов"""
    print("🔧 [LIVEKIT FOCUS] Comparing LiveKit packages specifically...")
    
    if not Path("working_environment.json").exists():
        print("❌ [ERROR] working_environment.json not found!")
        return False
    
    with open("working_environment.json", "r", encoding='utf-8') as f:
        working_env = json.load(f)
    
    # Текущие LiveKit пакеты
    result = subprocess.run([sys.executable, "-m", "pip", "list", "--format=json"], 
                          capture_output=True, text=True, check=True)
    current_packages = json.loads(result.stdout)
    current_livekit = [pkg for pkg in current_packages if 'livekit' in pkg['name'].lower()]
    
    # Рабочие LiveKit пакеты
    working_livekit = working_env['livekit_packages']
    
    print("\n🔧 [WORKING ENVIRONMENT - LIVEKIT]:")
    for pkg in working_livekit:
        print(f"   ✅ {pkg['name']:<35} {pkg['version']}")
    
    print("\n🔧 [CURRENT ENVIRONMENT - LIVEKIT]:")
    for pkg in current_livekit:
        print(f"   ✅ {pkg['name']:<35} {pkg['version']}")
    
    # Найти недостающие LiveKit пакеты
    working_names = {pkg['name'].lower() for pkg in working_livekit}
    current_names = {pkg['name'].lower() for pkg in current_livekit}
    
    missing_livekit = working_names - current_names
    
    if missing_livekit:
        print(f"\n❌ [MISSING LIVEKIT PACKAGES]:")
        for pkg_name in missing_livekit:
            # Найти версию
            for pkg in working_livekit:
                if pkg['name'].lower() == pkg_name:
                    print(f"   📦 pip install {pkg['name']}=={pkg['version']}")
                    break
    else:
        print(f"\n✅ [ALL LIVEKIT PACKAGES PRESENT]")

# ==================== MAIN FUNCTIONS ====================
def main():
    """Главная функция с меню"""
    print("🔍 [ENVIRONMENT COMPARISON TOOL]")
    print("=" * 60)
    print("1. Export working environment (run in WORKING env)")
    print("2. Compare environments (run in CURRENT env)")  
    print("3. Focus on LiveKit packages")
    print("4. Quick export (working env)")
    print("=" * 60)
    
    if len(sys.argv) > 1:
        choice = sys.argv[1]
    else:
        choice = input("Enter choice (1-4): ").strip()
    
    if choice == "1":
        export_working_environment()
    elif choice == "2":
        compare_environments()
    elif choice == "3":
        focus_on_livekit()
    elif choice == "4":
        # Быстрый экспорт
        result = subprocess.run([sys.executable, "-m", "pip", "freeze"], 
                              capture_output=True, text=True, check=True)
        with open("working_requirements.txt", "w") as f:
            f.write(result.stdout)
        print("✅ [QUICK EXPORT] Saved to working_requirements.txt")
    else:
        print("❌ Invalid choice")

if __name__ == "__main__":
    main()

# ==================== ИНСТРУКЦИЯ ПО ИСПОЛЬЗОВАНИЮ ====================
"""
🎯 [USAGE INSTRUCTIONS]:

ШАГИ:
1. В РАБОЧЕМ окружении:
   python environment_comparison.py 1
   
2. Скопируйте файлы working_environment.json и working_requirements.txt
   в текущее окружение

3. В ТЕКУЩЕМ окружении:
   python environment_comparison.py 2
   
4. Выполните предложенную команду установки

АЛЬТЕРНАТИВНО (быстро):
1. В рабочем окружении: pip freeze > working.txt
2. В текущем окружении: pip install -r working.txt
"""