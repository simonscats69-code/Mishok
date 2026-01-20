#!/usr/bin/env python3
import json
import os
import shutil
from datetime import datetime
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

print("🛠️ ИСПРАВЛЕНИЕ ДАННЫХ ДЛЯ ВЕРСИИ 3.0")
print("=" * 60)

from config import DATA_FILE, BACKUP_PATH

def fix_data_structure():
    if not os.path.exists(DATA_FILE):
        print(f"❌ Файл не найден: {DATA_FILE}")
        print("Создаю новый файл с оптимизированной структурой...")
        
        new_data = {
            "version": "3.0",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
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
            "records": [],
            "votes": {}  # Новая секция голосований
        }
        
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(new_data, f, separators=(',', ':'))
        
        print(f"✅ Создан новый файл: {DATA_FILE}")
        return True
    
    print("📦 Создание резервной копии...")
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(BACKUP_PATH, f"fix_backup_{timestamp}.json")
        
        os.makedirs(BACKUP_PATH, exist_ok=True)
        
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            original_data = json.load(f)
        
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(original_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Резервная копия создана: {backup_file}")
    except Exception as e:
        print(f"❌ Ошибка создания резервной копии: {e}")
        return False
    
    print("\n🔍 Анализ текущей структуры...")
    
    version = original_data.get("version", "1.0")
    print(f"   Версия: {version}")
    
    has_damage_history = False
    has_chat_stats = False
    
    for user_id, user_data in original_data.get("users", {}).items():
        if "damage_history" in user_data:
            has_damage_history = True
        if "chat_stats" in user_data:
            has_chat_stats = True
        if has_damage_history and has_chat_stats:
            break
    
    print(f"   damage_history: {'⚠️ ЕСТЬ' if has_damage_history else '✅ НЕТ'}")
    print(f"   chat_stats: {'⚠️ ЕСТЬ' if has_chat_stats else '✅ НЕТ'}")
    
    print("\n🔄 Оптимизация структуры...")
    
    fixed_data = {
        "version": "3.0",
        "created_at": original_data.get("created_at", datetime.now().isoformat()),
        "updated_at": datetime.now().isoformat(),
        "users": {},
        "chats": original_data.get("chats", {}),
        "global_stats": original_data.get("global_stats", {
            "total_shleps": 0,
            "last_shlep": None,
            "max_damage": 0,
            "max_damage_user": None,
            "max_damage_date": None,
            "total_users": 0
        }),
        "timestamps": {},
        "records": [],
        "votes": original_data.get("votes", {})  # Сохраняем голосования если есть
    }
    
    print("   Оптимизирую пользователей...")
    for user_id, user_data in original_data.get("users", {}).items():
        fixed_data["users"][user_id] = {
            "username": user_data.get("username", f"User_{user_id}"),
            "total_shleps": user_data.get("total_shleps", user_data.get("count", 0)),
            "max_damage": user_data.get("max_damage", 0),
            "last_shlep": user_data.get("last_shlep"),
            "bonus_damage": user_data.get("bonus_damage", 0)
        }
    
    print("   Оптимизирую timestamps...")
    if "timestamps" in original_data:
        for key, value in original_data["timestamps"].items():
            if isinstance(value, dict) and "count" in value:
                fixed_data["timestamps"][key] = value["count"]
            else:
                fixed_data["timestamps"][key] = value
    
    print("   Ограничиваю records до 5...")
    if "records" in original_data:
        fixed_data["records"] = original_data["records"][-5:] if len(original_data["records"]) > 5 else original_data["records"]
    
    print("   Обновляю счётчик пользователей...")
    fixed_data["global_stats"]["total_users"] = len(fixed_data["users"])
    
    print("\n💾 Сохранение оптимизированного файла...")
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(fixed_data, f, separators=(',', ':'))
        
        original_size = os.path.getsize(backup_file)
        new_size = os.path.getsize(DATA_FILE)
        reduction = ((original_size - new_size) / original_size) * 100 if original_size > 0 else 0
        
        print(f"✅ Файл сохранен: {DATA_FILE}")
        
        print(f"\n📊 РЕЗУЛЬТАТЫ ОПТИМИЗАЦИИ:")
        print(f"   📏 Исходный размер: {original_size:,} байт".replace(",", " "))
        print(f"   📏 Новый размер: {new_size:,} байт".replace(",", " "))
        print(f"   📉 Сокращение: {reduction:.1f}%")
        print(f"   👥 Пользователей: {len(fixed_data['users'])}")
        print(f"   👊 Шлёпков: {fixed_data['global_stats']['total_shleps']}")
        print(f"   🗳️ Голосований: {len(fixed_data['votes'])}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка сохранения: {e}")
        return False

def verify_fixed_data():
    print("\n🧪 ПРОВЕРКА ОПТИМИЗИРОВАННЫХ ДАННЫХ")
    print("=" * 60)
    
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        version = data.get("version", "1.0")
        print(f"✅ Версия данных: {version}")
        
        required_keys = ["users", "chats", "global_stats", "timestamps", "records", "votes"]
        all_keys_present = all(key in data for key in required_keys)
        
        if all_keys_present:
            print("✅ Все обязательные ключи присутствуют")
        else:
            missing = [k for k in required_keys if k not in data]
            print(f"❌ Отсутствуют ключи: {missing}")
            return False
        
        print("🔍 Проверка структуры пользователей...")
        errors = 0
        for user_id, user_data in data["users"].items():
            required_user_keys = ["username", "total_shleps", "max_damage", "last_shlep", "bonus_damage"]
            missing_keys = [k for k in required_user_keys if k not in user_data]
            if missing_keys:
                print(f"   ⚠️ {user_id}: отсутствуют {missing_keys}")
                errors += 1
        
        if errors == 0:
            print("✅ Структура пользователей корректна")
        
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
    print("🛠️  СКРИПТ ОПТИМИЗАЦИИ ДАННЫХ v3.0")
    print("=" * 60)
    
    if fix_data_structure():
        if verify_fixed_data():
            print("\n🎉 ОПТИМИЗАЦИЯ ЗАВЕРШЕНА УСПЕШНО!")
            print("Бот готов к работе с оптимизированными данными")
        else:
            print("\n⚠️ Оптимизация завершена, но есть проблемы с проверкой")
    else:
        print("\n❌ ОПТИМИЗАЦИЯ НЕ УДАЛАСЬ!")
    
    print("\n" + "=" * 60)
