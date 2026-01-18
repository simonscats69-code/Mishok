import os
from dotenv import load_dotenv

load_dotenv()

required_vars = ['BOT_TOKEN']
optional_vars = ['DATABASE_URL', 'ADMIN_ID', 'WEBHOOK_MODE', 'DOMAIN', 'PORT']

print("🔍 Проверка переменных окружения:")
print("=" * 40)

# Проверяем обязательные
for var in required_vars:
    value = os.getenv(var)
    if value:
        print(f"✅ {var}: {'*' * min(len(value), 10)}...")
    else:
        print(f"❌ {var}: НЕ НАЙДЕН!")

print("\nОпциональные переменные:")
for var in optional_vars:
    value = os.getenv(var)
    if value:
        print(f"✅ {var}: {value[:30]}...")
    else:
        print(f"⚠️  {var}: не установлен")

print("\nНастройки кэша:")
cache_vars = ['CACHE_ENABLED', 'CACHE_TTL_SECONDS', 'MAX_CACHE_SIZE']
for var in cache_vars:
    print(f"{var}: {os.getenv(var, 'по умолчанию')}")

print("\nНастройки чатов:")
chat_vars = ['CHAT_VOTE_DURATION', 'CHAT_DUEL_DURATION', 'CHAT_ROLE_DURATION']
for var in chat_vars:
    print(f"{var}: {os.getenv(var, 'по умолчанию')}")
