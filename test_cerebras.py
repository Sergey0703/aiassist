import os
import requests
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Проверяем ключ
cerebras_key = os.getenv('CEREBRAS_API_KEY')
print(f"Cerebras API Key: {cerebras_key[:10]}..." if cerebras_key else "Ключ не найден!")

# Проверяем доступные модели
if cerebras_key:
    headers = {"Authorization": f"Bearer {cerebras_key}"}
    try:
        response = requests.get("https://api.cerebras.ai/v1/models", headers=headers)
        print(f"Status Code: {response.status_code}")
        print("Доступные модели:")
        print(response.json())
    except Exception as e:
        print(f"Ошибка: {e}")
else:
    print("Сначала добавьте CEREBRAS_API_KEY в .env файл")