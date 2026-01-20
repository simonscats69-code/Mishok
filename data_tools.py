#!/usr/bin/env python3
"""
Инструменты для работы с данными бота Мишок Лысый
Объединяет функционал fix_data.py и migrate_data.py
"""

import json
import os
import shutil
import sys
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

print("🛠️ ИНСТРУМЕНТЫ ДЛЯ РАБОТЫ С ДАННЫМИ")
print("=" * 60)

from config import DATA_FILE, BACKUP_PATH

# Пути к старым данным для миграции
OLD_DATA_PATHS = [
    "mishok_data.json",
    "data/mishok_data.json",
    "root/mishok_data.json",
    "bothost/mishok_data.json",
    "app/mishok_data.json"
]

# ==================== ОБЩИЕ УТИЛИТЫ ====================

def create_backup(description: str = "") -> tuple:
    """Создать резервную копию данных"""
    try:
        if not os.path.exists(DATA_FILE):
            return False, "Файл данных не существует"
        
        os.makedirs(BACKUP_PATH, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        desc_part = f"_{description}" if description else ""
        backup_file = os.path.join(BACKUP_PATH, f"backup{desc_part}_{timestamp}.json")
        
        shutil.copy2(DATA_FILE, backup_file)
        
        size = os.path.getsize(backup_file)
        print(f"✅ Создан бэкап: {backup_file} ({size} байт)")
        
        return True, backup_file
    except Exception as e:
        print(f"❌ Ошибка создания бэкапа: {e}")
        return False, str(e)

def check_current_data():
    """Проверить текущее состояние данных"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                total_shleps = data.get('global_stats', {}).get('total_shleps', 0)
                users_count = len(data.get('users', {}))
                votes_count = len(data.get('votes', {}))
                version = data.get('version', '1.0')
                print(f"📊 Текущие данные в {DATA_FILE}:")
                print(f"   👥 Пользователей: {users_count}")
                print(f"   👊 Шлёпков: {total_shleps}")
                print(f"   🗳️ Голосований: {votes_count}")
                print(f"   📋 Версия: {version}")
                return True
        except Exception as e:
            print(f"❌ Ошибка чтения текущих данных: {e}")
    return False

# ==================== МИГРАЦИЯ ДАННЫХ ====================

def migrate_file(old_paths, new_path, file_type="данные"):
    """Перенести файл из старого расположения в новое"""
    for old_path in old_paths:
        if os.path.exists(old_path) and old_path != new_path:
            try:
                os.makedirs(os.path.dirname(new_path), exist_ok=True)
                
                if file_type == "данные":
                    with open(old_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Оптимизируем старую структуру
                    if "users" in data:
                        for user_data in data.get("users", {}).values():
                            user_data.pop("damage_history", None)
                            user_data.pop("chat_stats", None)
                        data["version"] = "3.0"
                    
                    # Добавляем секцию голосований если её нет
                    if "votes" not in data:
                        data["votes"] = {}
                    
                    with open(new_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, separators=(',', ':'))
                else:
                    shutil.copy2(old_path, new_path)
                
                backup_name = f"{old_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                shutil.copy2(old_path, backup_name)
                
                print(f"✅ Перенесено: {old_path} → {new_path}")
                print(f"   💾 Бэкап: {backup_name}")
                return True
            except Exception as e:
                print(f"⚠️ Ошибка переноса {old_path}: {e}")
    return False

def migrate_all():
    """Выполнить полную миграцию данных"""
    print("\n🔄 ПЕРЕНОС ДАННЫХ В ЗАЩИЩЕННУЮ ДИРЕКТОРИЮ")
    
    if not check_current_data():
        migrated = migrate_file(OLD_DATA_PATHS, DATA_FILE, "данные")
        if not migrated:
            print("📭 Старые данные не найдены, будет создан новый файл")
    
    print("\n🧹 Создание директории для бэкапов...")
    os.makedirs(BACKUP_PATH, exist_ok=True)
    print(f"✅ Директория бэкапов: {BACKUP_PATH}")
    print("\n🎉 Перенос данных завершён!")
    
    return True

# ==================== ИСПРАВЛЕНИЕ ДАННЫХ ====================

def fix_data_structure():
    """Исправить и оптимизировать структуру данных"""
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
            "votes": {}
        }
        
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(new_data, f, separators=(',', ':'))
        
        print(f"✅ Создан новый файл: {DATA_FILE}")
        return True
    
    print("📦 Создание резервной копии...")
    success, backup_path = create_backup("before_fix")
    
    if not success:
        print(f"❌ Ошибка создания резервной копии: {backup_path}")
        return False
    
    print("\n🔍 Анализ текущей структуры...")
    
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            original_data = json.load(f)
    except Exception as e:
        print(f"❌ Ошибка чтения данных: {e}")
        return False
    
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
        "votes": original_data.get("votes", {})
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
        
        original_size = os.path.getsize(backup_path)
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
    """Проверить исправленные данные"""
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

def fix_and_verify():
    """Выполнить исправление и проверку данных"""
    print("\n🛠️ ИСПРАВЛЕНИЕ ДАННЫХ ДЛЯ ВЕРСИИ 3.0")
    if fix_data_structure():
        if verify_fixed_data():
            print("\n🎉 ОПТИМИЗАЦИЯ ЗАВЕРШЕНА УСПЕШНО!")
            print("Бот готов к работе с оптимизированными данными")
            return True
        else:
            print("\n⚠️ Оптимизация завершена, но есть проблемы с проверкой")
            return False
    else:
        print("\n❌ ОПТИМИЗАЦИЯ НЕ УДАЛАСЬ!")
        return False

# ==================== КОМАНДНАЯ СТРОКА ====================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Инструменты для работы с данными бота Мишок Лысый",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python data_tools.py --migrate    # Перенести данные
  python data_tools.py --fix        # Исправить структуру
  python data_tools.py --check      # Проверить данные
  python data_tools.py --backup     # Создать бэкап
        """
    )
    
    parser.add_argument("--migrate", action="store_true", help="Мигрировать данные в защищенную директорию")
    parser.add_argument("--fix", action="store_true", help="Исправить структуру данных")
    parser.add_argument("--check", action="store_true", help="Проверить текущие данные")
    parser.add_argument("--backup", action="store_true", help="Создать резервную копию")
    
    args = parser.parse_args()
    
    print("\n" + "=" * 60)
    print("🛠️  ИНСТРУМЕНТЫ ДЛЯ РАБОТЫ С ДАННЫМИ v3.0")
    print("=" * 60)
    
    if args.migrate:
        migrate_all()
    
    elif args.fix:
        fix_and_verify()
    
    elif args.check:
        print("\n🔍 ПРОВЕРКА ТЕКУЩИХ ДАННЫХ")
        if check_current_data():
            print("\n✅ Данные в порядке!")
        else:
            print("\n❌ Проблемы с данными!")
    
    elif args.backup:
        print("\n💾 СОЗДАНИЕ РЕЗЕРВНОЙ КОПИИ")
        success, path = create_backup("manual")
        if success:
            print(f"\n✅ Бэкап создан: {path}")
        else:
            print(f"\n❌ Ошибка: {path}")
    
    else:
        print("ℹ️  Используйте один из параметров:")
        print("  --migrate  для переноса данных")
        print("  --fix      для исправления структуры")
        print("  --check    для проверки данных")
        print("  --backup   для создания бэкапа")
        print("\nИли используйте 'python data_tools.py --help' для справки")
    
    print("\n" + "=" * 60)
