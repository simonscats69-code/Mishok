#!/usr/bin/env python3
import json
import os
import shutil
from datetime import datetime
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

print("🔄 МИГРАЦИЯ ДАННЫХ В ЗАЩИЩЕННУЮ ДИРЕКТОРИЮ")
print("=" * 60)

from config import DATA_FILE, VOTES_FILE, BACKUP_PATH

OLD_DATA_PATHS = [
    "mishok_data.json",
    "data/mishok_data.json",
    "/root/mishok_data.json",
    "/bothost/mishok_data.json",
    "/app/mishok_data.json"
]

OLD_VOTES_PATHS = [
    "data/votes.json",
    "votes.json",
    "/data/votes.json"
]

def migrate_file(old_paths, new_path):
    for old_path in old_paths:
        if os.path.exists(old_path) and old_path != new_path:
            try:
                os.makedirs(os.path.dirname(new_path), exist_ok=True)
                shutil.copy2(old_path, new_path)
                backup_name = f"{old_path}.migration_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
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
                print(f"📊 Текущие данные в {DATA_FILE}:")
                print(f"   👥 Пользователей: {users_count}")
                print(f"   👊 Шлёпков: {total_shleps}")
                return True
        except Exception as e:
            print(f"❌ Ошибка чтения текущих данных: {e}")
    return False

print("\n🔍 Поиск старых данных...")

if not check_current_data():
    migrated = migrate_file(OLD_DATA_PATHS, DATA_FILE)
    if not migrated:
        print("📭 Старые данные не найдены, будет создан новый файл")

if os.path.exists(VOTES_FILE):
    print(f"✅ Файл голосований уже на месте: {VOTES_FILE}")
else:
    migrate_file(OLD_VOTES_PATHS, VOTES_FILE)

print("\n🎉 Миграция завершена!")
print(f"📁 Данные теперь защищены в: {os.path.dirname(DATA_FILE)}")
print("=" * 60)
