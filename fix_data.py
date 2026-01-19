#!/usr/bin/env python3
# fix_data.py - Исправление структуры файла данных

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Добавляем путь к текущей директории
sys.path.append(str(Path(__file__).parent))

def fix_mishok_data():
    """Исправляет файл данных мишока"""
    
    DATA_FILE = "/data/mishok_data.json"
    BACKUP_FILE = "/data/mishok_data_backup_before_fix.json"
    
    print("🔧 ИСПРАВЛЕНИЕ ФАЙЛА ДАННЫХ МИШОКА")
    print("=" * 60)
    
    # 1. Проверяем существование файла
    if not os.path.exists(DATA_FILE):
        print(f"❌ Файл не найден: {DATA_FILE}")
        print("Создаю новый файл с правильной структурой...")
        
        new_data = {
            "users": {},
            "chats": {},
            "global_stats": {
                "total_shleps": 0,
                "last_shlep": None,
                "max_damage": 0,
                "max_damage_user": None,
                "max_damage_date": None,
                "total_users": 0
            },
            "timestamps": {},
            "records": []
        }
        
        # Создаем директорию
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(new_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Создан новый файл: {DATA_FILE}")
        return True
    
    # 2. Создаем резервную копию
    print("📦 Создание резервной копии...")
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            original_data = json.load(f)
        
        with open(BACKUP_FILE, 'w', encoding='utf-8') as f:
            json.dump(original_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Резервная копия создана: {BACKUP_FILE}")
    except Exception as e:
        print(f"❌ Ошибка создания резервной копии: {e}")
        return False
    
    # 3. Анализируем структуру
    print("\n🔍 Анализ текущей структуры...")
    
    has_user_stats = "user_stats" in original_data
    has_users = "users" in original_data
    has_global_stats = "global_stats" in original_data
    has_chat_stats = "chat_stats" in original_data
    
    print(f"   user_stats: {'✅' if has_user_stats else '❌'}")
    print(f"   users: {'✅' if has_users else '❌'}")
    print(f"   global_stats: {'✅' if has_global_stats else '❌'}")
    print(f"   chat_stats: {'✅' if has_chat_stats else '❌'}")
    
    # 4. Создаем исправленную структуру
    print("\n🔄 Создание исправленной структуры...")
    
    fixed_data = {
        "users": {},
        "chats": {},
        "global_stats": {
            "total_shleps": 0,
            "last_shlep": None,
            "max_damage": 0,
            "max_damage_user": None,
            "max_damage_date": None,
            "total_users": 0
        },
        "timestamps": {},
        "records": []
    }
    
    # 5. Конвертируем user_stats -> users
    if has_user_stats:
        print("   Конвертируем user_stats -> users...")
        for user_id_str, user_info in original_data["user_stats"].items():
            # Определяем количество шлёпков
            count = user_info.get("count", 0)
            total_shleps = user_info.get("total_shleps", count)
            
            fixed_data["users"][user_id_str] = {
                "username": user_info.get("username", f"User_{user_id_str}"),
                "total_shleps": total_shleps,
                "max_damage": 0,  # Будет вычислено позже
                "last_shlep": user_info.get("last_shlep"),
                "damage_history": [],
                "chat_stats": {}
            }
        print(f"   ✅ Конвертировано {len(fixed_data['users'])} пользователей")
    elif has_users:
        # Уже в правильном формате, копируем
        print("   Копируем существующих users...")
        for user_id_str, user_info in original_data["users"].items():
            fixed_data["users"][user_id_str] = user_info
        print(f"   ✅ Скопировано {len(fixed_data['users'])} пользователей")
    
    # 6. Конвертируем global_stats
    if has_global_stats:
        print("   Обновляем global_stats...")
        fixed_data["global_stats"] = {
            "total_shleps": original_data["global_stats"].get("total_shleps", 0),
            "last_shlep": original_data["global_stats"].get("last_shlep"),
            "max_damage": original_data["global_stats"].get("max_damage", 0),
            "max_damage_user": original_data["global_stats"].get("max_damage_user"),
            "max_damage_date": original_data["global_stats"].get("max_damage_date"),
            "total_users": len(fixed_data["users"])
        }
        print("   ✅ global_stats обновлены")
    
    # 7. Конвертируем chat_stats
    if has_chat_stats:
        print("   Конвертируем chat_stats...")
        for chat_id_str, chat_info in original_data["chat_stats"].items():
            fixed_data["chats"][chat_id_str] = {
                "total_shleps": chat_info.get("total_shleps", 0),
                "users": {},
                "max_damage": chat_info.get("max_damage", 0),
                "max_damage_user": chat_info.get("max_damage_user"),
                "max_damage_date": chat_info.get("max_damage_date")
            }
            
            # Обрабатываем пользователей в чате
            if "users" in chat_info:
                # Убираем дубликаты
                seen_users = {}
                for uid, user_data in chat_info["users"].items():
                    if uid not in seen_users:
                        count = user_data.get("count", 0)
                        total_shleps = user_data.get("total_shleps", count)
                        
                        seen_users[uid] = {
                            "username": user_data.get("username", f"User_{uid}"),
                            "total_shleps": total_shleps,
                            "max_damage": user_data.get("max_damage", 0)
                        }
                    else:
                        # Суммируем для дубликатов
                        count = user_data.get("count", 0)
                        total_shleps = user_data.get("total_shleps", count)
                        seen_users[uid]["total_shleps"] += total_shleps
                
                fixed_data["chats"][chat_id_str]["users"] = seen_users
        
        print(f"   ✅ Конвертировано {len(fixed_data['chats'])} чатов")
    
    # 8. Вычисляем max_damage для пользователей
    print("   Вычисляем максимальный урон...")
    for chat_id, chat_data in fixed_data["chats"].items():
        for user_id, user_data in chat_data["users"].items():
            if user_id in fixed_data["users"]:
                user_max_damage = fixed_data["users"][user_id].get("max_damage", 0)
                chat_user_max_damage = user_data.get("max_damage", 0)
                
                if chat_user_max_damage > user_max_damage:
                    fixed_data["users"][user_id]["max_damage"] = chat_user_max_damage
    
    # 9. Сохраняем исправленный файл
    print("\n💾 Сохранение исправленного файла...")
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(fixed_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Файл сохранен: {DATA_FILE}")
        
        # 10. Выводим статистику
        print("\n📊 СТАТИСТИКА ПОСЛЕ ИСПРАВЛЕНИЯ:")
        print(f"   👥 Пользователей: {len(fixed_data['users'])}")
        print(f"   💬 Чатов: {len(fixed_data['chats'])}")
        print(f"   👊 Всего шлёпков: {fixed_data['global_stats']['total_shleps']}")
        
        # Проверяем дубликаты
        print("\n🔍 Проверка целостности:")
        errors_found = False
        
        for chat_id, chat_data in fixed_data["chats"].items():
            user_ids = list(chat_data.get("users", {}).keys())
            if len(user_ids) != len(set(user_ids)):
                print(f"   ⚠️ Чат {chat_id}: обнаружены дубликаты")
                errors_found = True
        
        if not errors_found:
            print("   ✅ Дубликатов не обнаружено")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка сохранения: {e}")
        return False

def verify_fixed_data():
    """Проверяет исправленный файл"""
    DATA_FILE = "/data/mishok_data.json"
    
    print("\n🧪 ПРОВЕРКА ИСПРАВЛЕННОГО ФАЙЛА")
    print("=" * 60)
    
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Проверяем обязательные ключи
        required_keys = ["users", "chats", "global_stats", "timestamps", "records"]
        all_keys_present = all(key in data for key in required_keys)
        
        if all_keys_present:
            print("✅ Все обязательные ключи присутствуют")
        else:
            missing = [k for k in required_keys if k not in data]
            print(f"❌ Отсутствуют ключи: {missing}")
            return False
        
        # Проверяем структуру пользователей
        user_errors = []
        for user_id, user_data in data["users"].items():
            required_user_keys = ["username", "total_shleps", "max_damage", "last_shlep", "damage_history", "chat_stats"]
            missing_keys = [k for k in required_user_keys if k not in user_data]
            if missing_keys:
                user_errors.append(f"{user_id}: {missing_keys}")
        
        if user_errors:
            print(f"⚠️ Ошибки в пользователях: {len(user_errors)}")
            for error in user_errors[:3]:  # Показываем первые 3 ошибки
                print(f"   {error}")
        else:
            print("✅ Структура пользователей корректна")
        
        # Тестируем импорт database
        print("\n🔗 Тестирование импорта database.py...")
        try:
            from database import load_data, get_stats
            
            test_data = load_data()
            print(f"✅ database.load_data() работает")
            
            total, last, maxd, maxu, maxdt = get_stats()
            print(f"✅ database.get_stats() работает")
            print(f"   Всего шлёпков: {total}")
            
            return True
            
        except ImportError as e:
            print(f"❌ Ошибка импорта database.py: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка проверки: {e}")
        return False

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🛠️  СКРИПТ ИСПРАВЛЕНИЯ ДАННЫХ МИШОКА")
    print("=" * 60)
    
    # Запускаем исправление
    if fix_mishok_data():
        # Проверяем результат
        if verify_fixed_data():
            print("\n🎉 ИСПРАВЛЕНИЕ ЗАВЕРШЕНО УСПЕШНО!")
            print("Бот должен работать корректно с файлом /data/mishok_data.json")
        else:
            print("\n⚠️ Исправление завершено, но есть проблемы с проверкой")
    else:
        print("\n❌ ИСПРАВЛЕНИЕ НЕ УДАЛОСЬ!")
    
    print("\n" + "=" * 60)
