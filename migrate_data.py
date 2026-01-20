#!/usr/bin/env python3
import json
import os
import shutil
from datetime import datetime
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

print("🔄 ПЕРЕНОС ДАННЫХ В ЗАЩИЩЕННУЮ ДИРЕКТОРИЮ")
print("=" * 60)

from config import DATA_FILE, BACKUP_PATH

OLD_DATA_PATHS = [
    "mishok_data.json",
    "data/mishok_data.json",
    "root/mishok_data.json",
    "bothost/mishok_data.json",
    "app/mishok_data.json"
]

def migrate_file(old_paths, new_path, file_type="данные"):
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

def check_current_data():
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

print("\n🔍 Поиск старых данных...")

if not check_current_data():
    migrated = migrate_file(OLD_DATA_PATHS, DATA_FILE, "данные")
    if not migrated:
        print("📭 Старые данные не найдены, будет создан новый файл")

print("\n🧹 Создание директории для бэкапов...")
os.makedirs(BACKUP_PATH, exist_ok=True)
print(f"✅ Директория бэкапов: {BACKUP_PATH}")

print("\n🎉 Перенос данных завершён!")
print(f"📁 Данные теперь защищены в: {os.path.dirname(DATA_FILE)}")
print("ℹ️  Голосования теперь хранятся в основном файле данных")
print("=" * 60)
