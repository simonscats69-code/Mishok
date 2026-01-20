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

from texts import DATA_TOOLS_TEXTS, STATUS_TEXTS
from config import DATA_FILE, BACKUP_PATH

OLD_DATA_PATHS = [
    "mishok_data.json",
    "data/mishok_data.json",
    "root/mishok_data.json",
    "bothost/mishok_data.json",
    "app/mishok_data.json"
]

print(DATA_TOOLS_TEXTS['title'])
print(DATA_TOOLS_TEXTS['divider'])

# ==================== ОБЩИЕ УТИЛИТЫ ====================

def create_backup(description: str = "") -> tuple:
    """Создать резервную копию данных"""
    try:
        if not os.path.exists(DATA_FILE):
            return False, DATA_TOOLS_TEXTS['file_not_found'].format(file=DATA_FILE)
        
        os.makedirs(BACKUP_PATH, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        desc_part = f"_{description}" if description else ""
        backup_file = os.path.join(BACKUP_PATH, f"backup{desc_part}_{timestamp}.json")
        
        shutil.copy2(DATA_FILE, backup_file)
        
        size = os.path.getsize(backup_file)
        print(DATA_TOOLS_TEXTS['backup_created'].format(file=backup_file, size=size))
        
        return True, backup_file
    except Exception as e:
        print(DATA_TOOLS_TEXTS['backup_error'].format(error=e))
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
                print(DATA_TOOLS_TEXTS['check_data'].format(
                    file=DATA_FILE,
                    users=users_count,
                    shleps=total_shleps,
                    votes=votes_count,
                    version=version
                ))
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
                
                print(DATA_TOOLS_TEXTS['migrated_file'].format(old=old_path, new=new_path))
                print(DATA_TOOLS_TEXTS['file_backup'].format(backup=backup_name))
                return True
            except Exception as e:
                print(f"⚠️ Ошибка переноса {old_path}: {e}")
    return False

def migrate_all():
    """Выполнить полную миграцию данных"""
    print("\n" + DATA_TOOLS_TEXTS['migrate_title'])
    
    if not check_current_data():
        migrated = migrate_file(OLD_DATA_PATHS, DATA_FILE, "данные")
        if not migrated:
            print(DATA_TOOLS_TEXTS['no_old_data'])
    
    print("\n" + DATA_TOOLS_TEXTS['backup_dir'])
    os.makedirs(BACKUP_PATH, exist_ok=True)
    print(DATA_TOOLS_TEXTS['backup_dir_created'].format(path=BACKUP_PATH))
    print("\n" + DATA_TOOLS_TEXTS['migration_complete'])
    
    return True

# ==================== ИСПРАВЛЕНИЕ ДАННЫХ ====================

def fix_data_structure():
    """Исправить и оптимизировать структуру данных"""
    if not os.path.exists(DATA_FILE):
        print(DATA_TOOLS_TEXTS['file_not_found'].format(file=DATA_FILE))
        print(DATA_TOOLS_TEXTS['create_new'])
        
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
        
        print(DATA_TOOLS_TEXTS['created_new'].format(file=DATA_FILE))
        return True
    
    print(DATA_TOOLS_TEXTS['backup_creating'])
    success, backup_path = create_backup("before_fix")
    
    if not success:
        print(DATA_TOOLS_TEXTS['backup_error'].format(error=backup_path))
        return False
    
    print(DATA_TOOLS_TEXTS['analysis'])
    
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            original_data = json.load(f)
    except Exception as e:
        print(f"❌ Ошибка чтения данных: {e}")
        return False
    
    version = original_data.get("version", "1.0")
    print(DATA_TOOLS_TEXTS['version'].format(version=version))
    
    has_damage_history = False
    has_chat_stats = False
    
    for user_id, user_data in original_data.get("users", {}).items():
        if "damage_history" in user_data:
            has_damage_history = True
        if "chat_stats" in user_data:
            has_chat_stats = True
        if has_damage_history and has_chat_stats:
            break
    
    damage_status = STATUS_TEXTS['warning_yes'] if has_damage_history else STATUS_TEXTS['no']
    chat_status = STATUS_TEXTS['warning_yes'] if has_chat_stats else STATUS_TEXTS['no']
    
    print(f"   damage_history: {damage_status}")
    print(f"   chat_stats: {chat_status}")
    
    print(DATA_TOOLS_TEXTS['optimization'])
    
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
    
    print(DATA_TOOLS_TEXTS['optimizing_users'])
    for user_id, user_data in original_data.get("users", {}).items():
        fixed_data["users"][user_id] = {
            "username": user_data.get("username", f"User_{user_id}"),
            "total_shleps": user_data.get("total_shleps", user_data.get("count", 0)),
            "max_damage": user_data.get("max_damage", 0),
            "last_shlep": user_data.get("last_shlep"),
            "bonus_damage": user_data.get("bonus_damage", 0)
        }
    
    print(DATA_TOOLS_TEXTS['optimizing_timestamps'])
    if "timestamps" in original_data:
        for key, value in original_data["timestamps"].items():
            if isinstance(value, dict) and "count" in value:
                fixed_data["timestamps"][key] = value["count"]
            else:
                fixed_data["timestamps"][key] = value
    
    print(DATA_TOOLS_TEXTS['limiting_records'])
    if "records" in original_data:
        fixed_data["records"] = original_data["records"][-5:] if len(original_data["records"]) > 5 else original_data["records"]
    
    print(DATA_TOOLS_TEXTS['updating_counter'])
    fixed_data["global_stats"]["total_users"] = len(fixed_data["users"])
    
    print(DATA_TOOLS_TEXTS['saving'])
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(fixed_data, f, separators=(',', ':'))
        
        original_size = os.path.getsize(backup_path)
        new_size = os.path.getsize(DATA_FILE)
        reduction = ((original_size - new_size) / original_size) * 100 if original_size > 0 else 0
        
        print(DATA_TOOLS_TEXTS['saved'].format(file=DATA_FILE))
        
        print(DATA_TOOLS_TEXTS['optimization_results'])
        print(DATA_TOOLS_TEXTS['original_size'].format(size=original_size))
        print(DATA_TOOLS_TEXTS['new_size'].format(size=new_size))
        print(DATA_TOOLS_TEXTS['reduction'].format(percent=reduction))
        print(DATA_TOOLS_TEXTS['users_count'].format(count=len(fixed_data['users'])))
        print(DATA_TOOLS_TEXTS['shleps_count'].format(count=fixed_data['global_stats']['total_shleps']))
        print(DATA_TOOLS_TEXTS['votes_count'].format(count=len(fixed_data['votes'])))
        
        return True
        
    except Exception as e:
        print(DATA_TOOLS_TEXTS['save_error'].format(error=e))
        return False

def verify_fixed_data():
    """Проверить исправленные данные"""
    print("\n" + DATA_TOOLS_TEXTS['verify_title'])
    print(DATA_TOOLS_TEXTS['divider'])
    
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        version = data.get("version", "1.0")
        print(DATA_TOOLS_TEXTS['data_version'].format(version=version))
        
        required_keys = ["users", "chats", "global_stats", "timestamps", "records", "votes"]
        all_keys_present = all(key in data for key in required_keys)
        
        if all_keys_present:
            print(DATA_TOOLS_TEXTS['keys_ok'])
        else:
            missing = [k for k in required_keys if k not in data]
            print(DATA_TOOLS_TEXTS['keys_missing'].format(keys=missing))
            return False
        
        print(DATA_TOOLS_TEXTS['checking_users'])
        errors = 0
        for user_id, user_data in data["users"].items():
            required_user_keys = ["username", "total_shleps", "max_damage", "last_shlep", "bonus_damage"]
            missing_keys = [k for k in required_user_keys if k not in user_data]
            if missing_keys:
                print(DATA_TOOLS_TEXTS['user_error'].format(id=user_id, keys=missing_keys))
                errors += 1
        
        if errors == 0:
            print(DATA_TOOLS_TEXTS['users_ok'])
        
        print(DATA_TOOLS_TEXTS['testing_import'])
        try:
            from database import load_data, get_stats
            
            test_data = load_data()
            print(DATA_TOOLS_TEXTS['load_ok'])
            
            total, last, maxd, maxu, maxdt = get_stats()
            print(DATA_TOOLS_TEXTS['stats_ok'])
            print(DATA_TOOLS_TEXTS['total_shleps'].format(count=total))
            
            return True
            
        except ImportError as e:
            print(DATA_TOOLS_TEXTS['import_error'].format(error=e))
            return False
            
    except Exception as e:
        print(DATA_TOOLS_TEXTS['verify_error'].format(error=e))
        return False

def fix_and_verify():
    """Выполнить исправление и проверку данных"""
    print("\n" + DATA_TOOLS_TEXTS['fix_title'])
    if fix_data_structure():
        if verify_fixed_data():
            print(DATA_TOOLS_TEXTS['success'])
            return True
        else:
            print(DATA_TOOLS_TEXTS['warning'])
            return False
    else:
        print(DATA_TOOLS_TEXTS['error'])
        return False

# ==================== КОМАНДНАЯ СТРОКА ====================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Инструменты для работы с данными бота Мишок Лысый",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=DATA_TOOLS_TEXTS['examples']
    )
    
    parser.add_argument("--migrate", action="store_true", help="Мигрировать данные в защищенную директорию")
    parser.add_argument("--fix", action="store_true", help="Исправить структуру данных")
    parser.add_argument("--check", action="store_true", help="Проверить текущие данные")
    parser.add_argument("--backup", action="store_true", help="Создать резервную копию")
    
    args = parser.parse_args()
    
    print("\n" + DATA_TOOLS_TEXTS['script_title'])
    print(DATA_TOOLS_TEXTS['divider'])
    
    if args.migrate:
        migrate_all()
    
    elif args.fix:
        fix_and_verify()
    
    elif args.check:
        print("\n" + DATA_TOOLS_TEXTS['check_title'])
        if check_current_data():
            print(DATA_TOOLS_TEXTS['data_ok'])
        else:
            print(DATA_TOOLS_TEXTS['data_problems'])
    
    elif args.backup:
        print("\n" + DATA_TOOLS_TEXTS['backup_title'])
        success, path = create_backup("manual")
        if success:
            print(DATA_TOOLS_TEXTS['backup_success'].format(path=path))
        else:
            print(DATA_TOOLS_TEXTS['backup_failed'].format(error=path))
    
    else:
        print(DATA_TOOLS_TEXTS['usage'])
    
    print("\n" + DATA_TOOLS_TEXTS['divider'])
