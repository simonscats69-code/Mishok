#!/usr/bin/env python3
"""
Скрипт для проверки настроек BHost
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

def check_environment():
    """Проверка переменных окружения"""
    print("🔍 ПРОВЕРКА НАСТРОЕК ДЛЯ BHOST")
    print("=" * 50)
    
    # Обязательные переменные
    required = [
        ('BOT_TOKEN', 'Токен бота от @BotFather'),
        ('WEBHOOK_MODE', 'Режим работы (true/false)'),
        ('PORT', 'Порт приложения')
    ]
    
    all_ok = True
    
    for var, description in required:
        value = os.getenv(var)
        if value:
            if var == 'BOT_TOKEN':
                print(f"✅ {var}: {'*' * min(len(value), 10)}... ({description})")
            else:
                print(f"✅ {var}: {value} ({description})")
        else:
            print(f"❌ {var}: НЕ НАЙДЕН! ({description})")
            all_ok = False
    
    print("\n📊 ДОПОЛНИТЕЛЬНЫЕ НАСТРОЙКИ:")
    
    optional = [
        ('DATABASE_URL', 'Строка подключения к БД'),
        ('ADMIN_ID', 'ID администратора'),
        ('DOMAIN', 'Домен BHost'),
        ('CACHE_ENABLED', 'Включен ли кэш'),
        ('CHAT_NOTIFICATIONS_ENABLED', 'Уведомления в чатах')
    ]
    
    for var, description in optional:
        value = os.getenv(var)
        if value:
            print(f"   ✅ {var}: {value}")
        else:
            print(f"   ⚠️  {var}: не установлен ({description})")
    
    print("\n" + "=" * 50)
    
    if not all_ok:
        print("🚨 ОШИБКА: Не все обязательные переменные установлены!")
        print("\n📝 ЧТО ДЕЛАТЬ:")
        print("1. Проверьте файл .env в корне проекта")
        print("2. Убедитесь что BOT_TOKEN указан правильно")
        print("3. WEBHOOK_MODE должен быть 'true' для BHost")
        print("4. PORT должен быть '8443' для BHost")
        sys.exit(1)
    
    # Проверка значений
    if os.getenv('WEBHOOK_MODE', '').lower() != 'true':
        print("⚠️  ВНИМАНИЕ: WEBHOOK_MODE должен быть 'true' для BHost!")
    
    if os.getenv('PORT') != '8443':
        print("⚠️  ВНИМАНИЕ: Рекомендуемый порт для BHost - 8443")
    
    print("✅ Все проверки пройдены успешно!")
    print("\n🚀 ДЛЯ ДЕПЛОЯ НА BHOST:")
    print("1. git add .")
    print("2. git commit -m 'Deploy to BHost'")
    print("3. git push origin main")
    print("\n⚙️  ПОСЛЕ ДЕПЛОЯ:")
    print("1. Получите домен в панели BHost")
    print("2. Добавьте его в переменные как DOMAIN")
    print("3. Перезапустите приложение")

def check_files():
    """Проверка необходимых файлов"""
    print("\n📁 ПРОВЕРКА ФАЙЛОВ:")
    
    required_files = [
        ('Procfile', 'Файл для запуска на BHost'),
        ('requirements.txt', 'Зависимости Python'),
        ('runtime.txt', 'Версия Python'),
        ('.env', 'Переменные окружения')
    ]
    
    for filename, description in required_files:
        if os.path.exists(filename):
            print(f"✅ {filename}: найден ({description})")
        else:
            print(f"❌ {filename}: НЕ НАЙДЕН! ({description})")

if __name__ == "__main__":
    check_files()
    print("\n")
    check_environment()
