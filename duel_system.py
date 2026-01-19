"""
ПОЛНАЯ СИСТЕМА ДУЭЛЕЙ В ОДНОМ ФАЙЛЕ
Все функции через _ в названиях
"""
import json
import os
import random
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Callable
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

logger = logging.getLogger(__name__)

DUELS_FILE = "data/duels.json"

class SimpleDuelSystem:
    """Простая система дуэлей - все в одном классе"""
    
    def __init__(self):
        self.duels_file = DUELS_FILE
        self._ensure_files()
        self.duel_duration = 60  # 1 минута дуэль
        self.invite_duration = 300  # 5 минут на принятие
    
    # ========== СИСТЕМНЫЕ ФУНКЦИИ ==========
    
    def _ensure_files(self):
        """Создает файлы если их нет"""
        os.makedirs(os.path.dirname(self.duels_file), exist_ok=True)
        if not os.path.exists(self.duels_file):
            self._save_data({"invites": {}, "active": {}, "history": []})
    
    def _load_data(self) -> Dict:
        """Загружает данные"""
        try:
            with open(self.duels_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {"invites": {}, "active": {}, "history": []}
    
    def _save_data(self, data: Dict):
        """Сохраняет данные"""
        try:
            with open(self.duels_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            return True
        except Exception as e:
            logger.error(f"Ошибка сохранения дуэлей: {e}")
            return False
    
    def _generate_id(self) -> str:
        """Генерирует ID дуэли"""
        return f"duel_{int(datetime.now().timestamp())}_{random.randint(1000, 9999)}"
    
    def _is_user_in_duel(self, user_id: int) -> bool:
        """Проверяет, участвует ли пользователь в дуэли"""
        return self.get_user_active_duel(user_id) is not None
    
    def _format_time(self, seconds: int) -> str:
        """Форматирует время"""
        return f"{seconds // 60:02d}:{seconds % 60:02d}"
    
    # ========== ОСНОВНЫЕ ФУНКЦИИ ДЛЯ КОМАНД ==========
    
    def duel_create(self, challenger_id: int, challenger_name: str, 
                   target_name: str, chat_id: int) -> Tuple[bool, str, Dict]:
        """
        /duel @username - вызвать на дуэль
        """
        try:
            # Проверяем активную дуэль
            if self._is_user_in_duel(challenger_id):
                return False, "Вы уже участвуете в дуэли!", {}
            
            duel_id = self._generate_id()
            
            duel_data = {
                "id": duel_id,
                "challenger_id": challenger_id,
                "challenger_name": challenger_name,
                "target_name": target_name.lower().replace("@", "").strip(),
                "target_id": 0,  # Будет установлен
                "chat_id": chat_id,
                "message_id": 0,
                "created_at": datetime.now().isoformat(),
                "expires_at": (datetime.now() + timedelta(seconds=self.invite_duration)).isoformat(),
                "status": "pending",
                "started_at": None,
                "ends_at": None,
                "challenger_damage": 0,
                "challenger_shleps": 0,
                "target_damage": 0,
                "target_shleps": 0,
                "reward": random.randint(15, 25),
                "winner": None,
                "winner_name": None,
                "history": []
            }
            
            data = self._load_data()
            data["invites"][duel_id] = duel_data
            self._save_data(data)
            
            logger.info(f"Создана дуэль {duel_id}")
            return True, duel_id, duel_data
            
        except Exception as e:
            logger.error(f"Ошибка создания дуэли: {e}")
            return False, f"Ошибка: {e}", {}
    
    def duel_accept(self, user_id: int, username: str) -> Tuple[bool, str, Dict]:
        """
        /duel accept - принять дуэль
        Принимает первую доступную дуэль
        """
        try:
            # Проверяем активную дуэль
            if self._is_user_in_duel(user_id):
                return False, "Вы уже участвуете в дуэли!", {}
            
            # Ищем приглашения для пользователя
            invites = self._get_user_invites(user_id, username)
            
            if not invites:
                return False, "У вас нет приглашений на дуэль!", {}
            
            # Берем первое приглашение
            duel = invites[0]
            duel_id = duel["id"]
            
            # Проверяем время
            if datetime.now() > datetime.fromisoformat(duel["expires_at"]):
                self._move_to_history(duel_id, "expired")
                return False, "Время на принятие вышло!", {}
            
            # Обновляем дуэль
            duel["target_id"] = user_id
            duel["status"] = "active"
            duel["started_at"] = datetime.now().isoformat()
            duel["ends_at"] = (datetime.now() + timedelta(seconds=self.duel_duration)).isoformat()
            
            # Сохраняем
            data = self._load_data()
            data["active"][duel_id] = duel
            del data["invites"][duel_id]
            self._save_data(data)
            
            logger.info(f"Дуэль принята: {duel_id}")
            return True, f"Дуэль с {duel['challenger_name']} началась! У вас 1 минута!", duel
            
        except Exception as e:
            logger.error(f"Ошибка принятия дуэли: {e}")
            return False, f"Ошибка: {e}", {}
    
    def duel_accept_id(self, duel_id: str, user_id: int, username: str) -> Tuple[bool, str, Dict]:
        """
        /duel accept_id ID - принять дуэль по ID
        """
        try:
            # Проверяем активную дуэль
            if self._is_user_in_duel(user_id):
                return False, "Вы уже участвуете в дуэли!", {}
            
            data = self._load_data()
            
            if duel_id not in data["invites"]:
                return False, "Дуэль не найдена!", {}
            
            duel = data["invites"][duel_id]
            
            # Проверяем время
            if datetime.now() > datetime.fromisoformat(duel["expires_at"]):
                self._move_to_history(duel_id, "expired")
                return False, "Время на принятие вышло!", {}
            
            # Проверяем, для этого ли пользователя
            target_name = duel["target_name"].lower()
            username_lower = username.lower()
            
            if not (target_name in username_lower or username_lower in target_name):
                return False, "Это приглашение не для вас!", {}
            
            # Обновляем дуэль
            duel["target_id"] = user_id
            duel["status"] = "active"
            duel["started_at"] = datetime.now().isoformat()
            duel["ends_at"] = (datetime.now() + timedelta(seconds=self.duel_duration)).isoformat()
            
            # Сохраняем
            data["active"][duel_id] = duel
            del data["invites"][duel_id]
            self._save_data(data)
            
            return True, f"Дуэль с {duel['challenger_name']} началась! У вас 1 минута!", duel
            
        except Exception as e:
            logger.error(f"Ошибка принятия дуэли по ID: {e}")
            return False, f"Ошибка: {e}", {}
    
    def duel_list(self, chat_id: int = None) -> Tuple[bool, str]:
        """
        /duel list - список дуэлей
        """
        try:
            data = self._load_data()
            
            text = "⚔️ АКТИВНЫЕ ДУЭЛИ:\n\n"
            
            # Активные дуэли
            active_count = 0
            for duel in data["active"].values():
                if chat_id and duel.get("chat_id") != chat_id:
                    continue
                
                ends_at = datetime.fromisoformat(duel["ends_at"])
                remaining = max(0, (ends_at - datetime.now()).seconds)
                
                text += f"• {duel['challenger_name']} vs {duel['target_name']}\n"
                text += f"  ⏱️ {self._format_time(remaining)} | 🎯 +{duel['reward']}\n"
                text += f"  📊 {duel['challenger_damage']}-{duel['target_damage']}\n\n"
                active_count += 1
            
            if active_count == 0:
                text += "Нет активных дуэлей\n\n"
            
            # Приглашения
            text += "📨 ПРИГЛАШЕНИЯ:\n\n"
            invite_count = 0
            for duel in data["invites"].values():
                if chat_id and duel.get("chat_id") != chat_id:
                    continue
                
                expires_at = datetime.fromisoformat(duel["expires_at"])
                remaining = max(0, (expires_at - datetime.now()).seconds)
                
                text += f"• {duel['challenger_name']} → {duel['target_name']}\n"
                text += f"  ⏱️ {self._format_time(remaining)} | 🆔 {duel['id'][:8]}...\n\n"
                invite_count += 1
            
            if invite_count == 0:
                text += "Нет приглашений\n"
            
            return True, text
            
        except Exception as e:
            logger.error(f"Ошибка списка дуэлей: {e}")
            return False, f"Ошибка: {e}"
    
    def duel_cancel(self, user_id: int) -> Tuple[bool, str]:
        """
        /duel cancel - отменить дуэль
        """
        try:
            data = self._load_data()
            cancelled = 0
            
            # Отменяем приглашения пользователя
            to_remove = []
            for duel_id, duel in data["invites"].items():
                if duel["challenger_id"] == user_id:
                    duel["status"] = "cancelled"
                    data["history"].append(duel)
                    to_remove.append(duel_id)
                    cancelled += 1
            
            for duel_id in to_remove:
                del data["invites"][duel_id]
            
            self._save_data(data)
            
            if cancelled > 0:
                return True, f"✅ Отменено {cancelled} приглашений"
            else:
                return False, "❌ У вас нет активных приглашений"
            
        except Exception as e:
            logger.error(f"Ошибка отмены дуэли: {e}")
            return False, f"Ошибка: {e}"
    
    def duel_stats(self, user_id: int) -> Tuple[bool, str]:
        """
        /duel stats - статистика дуэлей
        """
        try:
            data = self._load_data()
            
            wins = 0
            losses = 0
            draws = 0
            total_damage = 0
            total_reward = 0
            
            for duel in data["history"]:
                if duel.get("challenger_id") == user_id or duel.get("target_id") == user_id:
                    if duel.get("winner") == "challenger":
                        if duel["challenger_id"] == user_id:
                            wins += 1
                            total_reward += duel.get("reward", 0)
                        else:
                            losses += 1
                    elif duel.get("winner") == "target":
                        if duel["target_id"] == user_id:
                            wins += 1
                            total_reward += duel.get("reward", 0)
                        else:
                            losses += 1
                    elif duel.get("winner") == "draw":
                        draws += 1
                    
                    if duel["challenger_id"] == user_id:
                        total_damage += duel.get("challenger_damage", 0)
                    else:
                        total_damage += duel.get("target_damage", 0)
            
            total = wins + losses + draws
            win_rate = (wins / total * 100) if total > 0 else 0
            
            text = (
                f"⚔️ ВАША СТАТИСТИКА ДУЭЛЕЙ:\n\n"
                f"🏆 Побед: {wins}\n"
                f"💀 Поражений: {losses}\n"
                f"🤝 Ничьих: {draws}\n\n"
                f"📊 Процент побед: {win_rate:.1f}%\n"
                f"🔥 Всего урона: {total_damage}\n"
                f"🎯 Бонусный урон: +{total_reward}\n\n"
                f"Всего дуэлей: {total}"
            )
            
            return True, text
            
        except Exception as e:
            logger.error(f"Ошибка статистики дуэлей: {e}")
            return False, f"Ошибка: {e}"
    
    # ========== ФУНКЦИИ ДЛЯ КОЛЛБЭКОВ ==========
    
    def duel_callback_accept(self, duel_id: str, user_id: int, username: str) -> Tuple[bool, str, Dict]:
        """Callback: Принять дуэль (кнопка)"""
        return self.duel_accept_id(duel_id, user_id, username)
    
    def duel_callback_decline(self, duel_id: str, user_id: int, username: str) -> Tuple[bool, str]:
        """Callback: Отклонить дуэль (кнопка)"""
        try:
            data = self._load_data()
            
            if duel_id not in data["invites"]:
                return False, "Дуэль не найдена"
            
            duel = data["invites"][duel_id]
            
            # Проверяем, для этого ли пользователя
            target_name = duel["target_name"].lower()
            username_lower = username.lower()
            
            if not (target_name in username_lower or username_lower in target_name):
                return False, "Это приглашение не для вас"
            
            # Перемещаем в историю
            duel["status"] = "declined"
            duel["declined_by"] = username
            data["history"].append(duel)
            del data["invites"][duel_id]
            
            self._save_data(data)
            
            return True, "✅ Дуэль отклонена"
            
        except Exception as e:
            logger.error(f"Ошибка отклонения дуэли: {e}")
            return False, f"Ошибка: {e}"
    
    def duel_callback_attack(self, duel_id: str, user_id: int, damage: int, username: str) -> Tuple[bool, str, Dict]:
        """Callback: Атаковать в дуэли (кнопка)"""
        try:
            data = self._load_data()
            
            if duel_id not in data["active"]:
                return False, "Дуэль не найдена", {}
            
            duel = data["active"][duel_id]
            
            # Проверяем участника
            if user_id not in [duel["challenger_id"], duel["target_id"]]:
                return False, "Вы не участник этой дуэли", {}
            
            # Проверяем время
            if datetime.now() > datetime.fromisoformat(duel["ends_at"]):
                return self._finish_duel(duel_id)
            
            # Добавляем урон
            action = {
                "user_id": user_id,
                "username": username,
                "damage": damage,
                "timestamp": datetime.now().isoformat()
            }
            
            if user_id == duel["challenger_id"]:
                duel["challenger_damage"] += damage
                duel["challenger_shleps"] += 1
                action["side"] = "challenger"
            else:
                duel["target_damage"] += damage
                duel["target_shleps"] += 1
                action["side"] = "target"
            
            duel["history"].append(action)
            
            # Сохраняем
            data["active"][duel_id] = duel
            self._save_data(data)
            
            # Проверяем время
            if datetime.now() > datetime.fromisoformat(duel["ends_at"]):
                return self._finish_duel(duel_id)
            
            return True, f"👊 {username} нанес {damage} урона!", duel
            
        except Exception as e:
            logger.error(f"Ошибка атаки в дуэли: {e}")
            return False, f"Ошибка: {e}", {}
    
    def duel_callback_surrender(self, duel_id: str, user_id: int, username: str) -> Tuple[bool, str, Dict]:
        """Callback: Сдаться в дуэли (кнопка)"""
        try:
            data = self._load_data()
            
            if duel_id not in data["active"]:
                return False, "Дуэль не найдена", {}
            
            duel = data["active"][duel_id]
            
            # Проверяем участника
            if user_id not in [duel["challenger_id"], duel["target_id"]]:
                return False, "Вы не участник этой дуэли", {}
            
            # Определяем победителя (противник)
            if user_id == duel["challenger_id"]:
                duel["winner"] = "target"
                duel["winner_name"] = duel["target_name"]
                duel["surrenderer"] = duel["challenger_name"]
            else:
                duel["winner"] = "challenger"
                duel["winner_name"] = duel["challenger_name"]
                duel["surrenderer"] = duel["target_name"]
            
            duel["status"] = "surrendered"
            duel["finished_at"] = datetime.now().isoformat()
            
            # Перемещаем в историю
            data["history"].append(duel)
            del data["active"][duel_id]
            
            self._save_data(data)
            
            return True, f"🏳️ {username} сдался! Победитель: {duel['winner_name']}", duel
            
        except Exception as e:
            logger.error(f"Ошибка сдачи в дуэли: {e}")
            return False, f"Ошибка: {e}", {}
    
    def duel_callback_stats(self, duel_id: str) -> Tuple[bool, str]:
        """Callback: Статистика дуэли (кнопка)"""
        try:
            duel = self.get_duel(duel_id)
            
            if not duel:
                return False, "Дуэль не найдена"
            
            text = (
                f"📊 СТАТИСТИКА ДУЭЛИ:\n\n"
                f"👤 {duel['challenger_name']}:\n"
                f"• Урон: {duel['challenger_damage']}\n"
                f"• Шлёпков: {duel['challenger_shleps']}\n"
                f"• Средний: {duel['challenger_damage'] // max(duel['challenger_shleps'], 1)}\n\n"
                f"👤 {duel['target_name']}:\n"
                f"• Урон: {duel['target_damage']}\n"
                f"• Шлёпков: {duel['target_shleps']}\n"
                f"• Средний: {duel['target_damage'] // max(duel['target_shleps'], 1)}\n\n"
                f"🎯 Награда: +{duel.get('reward', 0)} урона"
            )
            
            return True, text
            
        except Exception as e:
            logger.error(f"Ошибка статистики дуэли: {e}")
            return False, f"Ошибка: {e}"
    
    # ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
    
    def _get_user_invites(self, user_id: int, username: str) -> List[Dict]:
        """Получает приглашения для пользователя"""
        data = self._load_data()
        invites = []
        
        username_lower = username.lower()
        
        for duel in data["invites"].values():
            target_name = duel["target_name"].lower()
            
            if (target_name in username_lower or 
                username_lower in target_name or 
                target_name == username_lower):
                
                if datetime.now() < datetime.fromisoformat(duel["expires_at"]):
                    invites.append(duel)
        
        return invites
    
    def _move_to_history(self, duel_id: str, status: str):
        """Перемещает дуэль в историю"""
        try:
            data = self._load_data()
            
            if duel_id in data["invites"]:
                duel = data["invites"][duel_id]
                duel["status"] = status
                data["history"].append(duel)
                del data["invites"][duel_id]
                self._save_data(data)
            elif duel_id in data["active"]:
                duel = data["active"][duel_id]
                duel["status"] = status
                data["history"].append(duel)
                del data["active"][duel_id]
                self._save_data(data)
                
        except Exception as e:
            logger.error(f"Ошибка перемещения в историю: {e}")
    
    def _finish_duel(self, duel_id: str) -> Tuple[bool, str, Dict]:
        """Завершает дуэль"""
        try:
            data = self._load_data()
            
            if duel_id not in data["active"]:
                return False, "Дуэль не найдена", {}
            
            duel = data["active"][duel_id]
            
            # Определяем победителя
            if duel["challenger_damage"] > duel["target_damage"]:
                duel["winner"] = "challenger"
                duel["winner_name"] = duel["challenger_name"]
            elif duel["target_damage"] > duel["challenger_damage"]:
                duel["winner"] = "target"
                duel["winner_name"] = duel["target_name"]
            else:
                duel["winner"] = "draw"
                duel["winner_name"] = "Ничья"
            
            duel["status"] = "finished"
            duel["finished_at"] = datetime.now().isoformat()
            
            # Перемещаем в историю
            data["history"].append(duel)
            del data["active"][duel_id]
            
            self._save_data(data)
            
            logger.info(f"Дуэль завершена: {duel_id}")
            return True, "Дуэль завершена!", duel
            
        except Exception as e:
            logger.error(f"Ошибка завершения дуэли: {e}")
            return False, f"Ошибка: {e}", {}
    
    # ========== ПОЛУЧЕНИЕ ДАННЫХ ==========
    
    def get_duel(self, duel_id: str) -> Optional[Dict]:
        """Получает дуэль по ID"""
        data = self._load_data()
        
        if duel_id in data["active"]:
            return data["active"][duel_id]
        elif duel_id in data["invites"]:
            return data["invites"][duel_id]
        
        # Ищем в истории
        for duel in data["history"]:
            if duel.get("id") == duel_id:
                return duel
        
        return None
    
    def get_user_active_duel(self, user_id: int) -> Optional[Dict]:
        """Получает активную дуэль пользователя"""
        data = self._load_data()
        
        for duel in data["active"].values():
            if duel["challenger_id"] == user_id or duel["target_id"] == user_id:
                return duel
        
        return None
    
    def get_all_invites(self) -> List[Dict]:
        """Получает все приглашения"""
        data = self._load_data()
        return list(data["invites"].values())
    
    def get_all_active(self) -> List[Dict]:
        """Получает все активные дуэли"""
        data = self._load_data()
        return list(data["active"].values())
    
    def cleanup(self):
        """Очищает просроченные дуэли"""
        try:
            data = self._load_data()
            cleaned = 0
            
            now = datetime.now()
            
            # Приглашения
            expired_invites = []
            for duel_id, duel in data["invites"].items():
                if now > datetime.fromisoformat(duel["expires_at"]):
                    duel["status"] = "expired"
                    data["history"].append(duel)
                    expired_invites.append(duel_id)
                    cleaned += 1
            
            for duel_id in expired_invites:
                del data["invites"][duel_id]
            
            # Активные дуэли
            expired_duels = []
            for duel_id, duel in data["active"].items():
                if now > datetime.fromisoformat(duel["ends_at"]):
                    self._finish_duel(duel_id)
                    expired_duels.append(duel_id)
                    cleaned += 1
            
            for duel_id in expired_duels:
                if duel_id in data["active"]:
                    del data["active"][duel_id]
            
            if cleaned > 0:
                self._save_data(data)
                logger.info(f"Очищено {cleaned} просроченных дуэлей")
            
            return cleaned
            
        except Exception as e:
            logger.error(f"Ошибка очистки дуэлей: {e}")
            return 0

# ========== КЛАВИАТУРЫ ==========

def get_duel_invite_keyboard(duel_id: str):
    """Клавиатура для приглашения на дуэль"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ ПРИНЯТЬ", callback_data=f"duel_accept_{duel_id}"),
            InlineKeyboardButton("❌ ОТКЛОНИТЬ", callback_data=f"duel_decline_{duel_id}")
        ]
    ])

def get_duel_active_keyboard(duel_id: str):
    """Клавиатура для активной дуэли"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👊 АТАКОВАТЬ", callback_data=f"duel_attack_{duel_id}"),
            InlineKeyboardButton("📊 СТАТИСТИКА", callback_data=f"duel_stats_{duel_id}")
        ],
        [
            InlineKeyboardButton("🏳️ СДАТЬСЯ", callback_data=f"duel_surrender_{duel_id}"),
            InlineKeyboardButton("🔄 ОБНОВИТЬ", callback_data=f"duel_refresh_{duel_id}")
        ]
    ])

def get_duel_finished_keyboard(duel_id: str):
    """Клавиатура для завершенной дуэли"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📋 ИТОГИ", callback_data=f"duel_result_{duel_id}"),
            InlineKeyboardButton("❌ ЗАКРЫТЬ", callback_data=f"duel_close_{duel_id}")
        ]
    ])

# ========== ОБРАБОТЧИК КОМАНД ==========

async def handle_duel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /duel
    Форматы:
    /duel @username - вызвать на дуэль
    /duel accept - принять дуэль
    /duel list - список дуэлей
    /duel cancel - отменить дуэль
    /duel stats - статистика
    """
    from bot import get_message_from_update
    
    msg = get_message_from_update(update)
    if not msg:
        return
    
    user = update.effective_user
    chat = update.effective_chat
    
    # Только в группах
    if chat.type == "private":
        await msg.reply_text("⚔️ Дуэли работают только в группах!")
        return
    
    system = SimpleDuelSystem()
    
    # Без аргументов - помощь
    if not context.args:
        text = (
            "⚔️ КОМАНДЫ ДУЭЛЕЙ:\n\n"
            "/duel @username - вызвать на дуэль\n"
            "/duel accept - принять вызов\n"
            "/duel list - список дуэлей\n"
            "/duel cancel - отменить свои вызовы\n"
            "/duel stats - ваша статистика\n\n"
            "📋 Правила:\n"
            "• Дуэль длится 1 минуту\n"
            "• 5 минут на принятие вызова\n"
            "• Победитель получает +15-25 урона\n"
            "• Шлёпайте кнопкой в сообщении дуэли"
        )
        await msg.reply_text(text)
        return
    
    # Получаем команду
    command = context.args[0].lower()
    
    # /duel @username - вызов
    if command.startswith("@"):
        target_name = command[1:] if command.startswith("@") else command
        
        success, result, duel_data = system.duel_create(
            challenger_id=user.id,
            challenger_name=user.first_name,
            target_name=target_name,
            chat_id=chat.id
        )
        
        if success:
            text = (
                f"⚔️ ВЫЗОВ НА ДУЭЛЬ!\n\n"
                f"👤 {user.first_name} вызывает @{target_name}!\n\n"
                f"📋 Правила:\n"
                f"• 5 минут на принятие\n"
                f"• Дуэль 1 минута\n"
                f"• Победитель: +{duel_data['reward']} урона\n\n"
                f"🆔 ID: `{result}`\n"
                f"⏱️ Время на принятие: 5:00"
            )
            
            await msg.reply_text(
                text,
                reply_markup=get_duel_invite_keyboard(result),
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await msg.reply_text(f"❌ {result}")
    
    # /duel accept - принять
    elif command == "accept":
        success, result, duel_data = system.duel_accept(user.id, user.first_name)
        
        if success:
            text = (
                f"⚔️ ДУЭЛЬ НАЧАЛАСЬ!\n\n"
                f"👤 {duel_data['challenger_name']} vs 👤 {duel_data['target_name']}\n\n"
                f"⏱️ Длительность: 1:00\n"
                f"🎯 Награда: +{duel_data['reward']} урона\n\n"
                f"Используйте кнопку ниже для атаки!"
            )
            
            await msg.reply_text(
                text,
                reply_markup=get_duel_active_keyboard(duel_data['id'])
            )
        else:
            await msg.reply_text(f"❌ {result}")
    
    # /duel accept_id ID - принять по ID
    elif command == "accept_id" and len(context.args) > 1:
        duel_id = context.args[1]
        success, result, duel_data = system.duel_accept_id(duel_id, user.id, user.first_name)
        
        if success:
            text = (
                f"⚔️ ДУЭЛЬ НАЧАЛАСЬ!\n\n"
                f"👤 {duel_data['challenger_name']} vs 👤 {duel_data['target_name']}\n\n"
                f"⏱️ Длительность: 1:00\n"
                f"🎯 Награда: +{duel_data['reward']} урона\n\n"
                f"Используйте кнопку ниже для атаки!"
            )
            
            await msg.reply_text(
                text,
                reply_markup=get_duel_active_keyboard(duel_data['id'])
            )
        else:
            await msg.reply_text(f"❌ {result}")
    
    # /duel list - список
    elif command == "list":
        success, result = system.duel_list(chat.id)
        
        if success:
            await msg.reply_text(result)
        else:
            await msg.reply_text(f"❌ {result}")
    
    # /duel cancel - отменить
    elif command == "cancel":
        success, result = system.duel_cancel(user.id)
        
        await msg.reply_text(result)
    
    # /duel stats - статистика
    elif command == "stats":
        success, result = system.duel_stats(user.id)
        
        if success:
            await msg.reply_text(result)
        else:
            await msg.reply_text(f"❌ {result}")
    
    # Неизвестная команда
    else:
        await msg.reply_text(
            "❌ Неизвестная команда дуэли.\n"
            "Используйте:\n"
            "/duel @username - вызвать\n"
            "/duel accept - принять\n"
            "/duel list - список\n"
            "/duel cancel - отменить\n"
            "/duel stats - статистика"
        )

# ========== ОБРАБОТЧИК КОЛЛБЭКОВ ==========

async def handle_duel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    """
    Обработчик callback для дуэлей
    Форматы:
    duel_accept_ID - принять дуэль
    duel_decline_ID - отклонить дуэль
    duel_attack_ID - атаковать в дуэли
    duel_surrender_ID - сдаться
    duel_stats_ID - статистика дуэли
    duel_refresh_ID - обновить сообщение
    duel_result_ID - итоги дуэли
    duel_close_ID - закрыть сообщение
    """
    query = update.callback_query
    user = update.effective_user
    
    if not query:
        return
    
    await query.answer()
    
    # Разбираем callback data
    # Формат: duel_ACTION_ID
    parts = data.split("_")
    
    if len(parts) < 3:
        await query.answer("❌ Ошибка формата", show_alert=True)
        return
    
    action = parts[1]
    duel_id = "_".join(parts[2:])  # На случай если в ID есть _
    
    logger.info(f"Дуэль callback: {action} для {duel_id} от {user.first_name}")
    
    system = SimpleDuelSystem()
    
    # Принять дуэль
    if action == "accept":
        success, result, duel_data = system.duel_callback_accept(duel_id, user.id, user.first_name)
        
        if success:
            text = (
                f"⚔️ ДУЭЛЬ НАЧАЛАСЬ!\n\n"
                f"👤 {duel_data['challenger_name']} vs 👤 {duel_data['target_name']}\n\n"
                f"⏱️ Длительность: 1:00\n"
                f"🎯 Награда: +{duel_data['reward']} урона\n\n"
                f"Используйте кнопку ниже для атаки!"
            )
            
            await query.message.edit_text(
                text,
                reply_markup=get_duel_active_keyboard(duel_id)
            )
            await query.answer("✅ Вы приняли вызов!", show_alert=True)
        else:
            await query.answer(f"❌ {result}", show_alert=True)
    
    # Отклонить дуэль
    elif action == "decline":
        success, result = system.duel_callback_decline(duel_id, user.id, user.first_name)
        
        if success:
            await query.message.edit_text(
                f"❌ ДУЭЛЬ ОТКЛОНЕНА\n\n"
                f"{user.first_name} отклонил вызов."
            )
            await query.answer(result, show_alert=False)
        else:
            await query.answer(f"❌ {result}", show_alert=True)
    
    # Атаковать в дуэли
    elif action == "attack":
        # Получаем урон пользователя
        from bot import calc_level
        from database import get_user_stats
        
        _, user_shleps, _ = get_user_stats(user.id)
        lvl = calc_level(user_shleps)
        damage = random.randint(lvl['min'], lvl['max'])
        
        success, result, duel_data = system.duel_callback_attack(duel_id, user.id, damage, user.first_name)
        
        if success:
            # Обновляем сообщение
            await update_duel_message(duel_data, query.message)
            await query.answer(f"👊 Вы нанесли {damage} урона!", show_alert=False)
        else:
            await query.answer(f"❌ {result}", show_alert=True)
    
    # Сдаться
    elif action == "surrender":
        success, result, duel_data = system.duel_callback_surrender(duel_id, user.id, user.first_name)
        
        if success:
            text = (
                f"🏳️ ДУЭЛЬ ЗАВЕРШЕНА СДАЧЕЙ\n\n"
                f"{result}\n\n"
                f"Итоговый счёт:\n"
                f"👤 {duel_data['challenger_name']}: {duel_data['challenger_damage']} урона\n"
                f"👤 {duel_data['target_name']}: {duel_data['target_damage']} урона\n\n"
                f"🎯 Награда: +{duel_data['reward']} урона"
            )
            
            await query.message.edit_text(
                text,
                reply_markup=get_duel_finished_keyboard(duel_id)
            )
            await query.answer("Вы сдались", show_alert=True)
        else:
            await query.answer(f"❌ {result}", show_alert=True)
    
    # Статистика дуэли
    elif action == "stats":
        success, result = system.duel_callback_stats(duel_id)
        
        if success:
            await query.answer(result, show_alert=True)
        else:
            await query.answer(f"❌ {result}", show_alert=True)
    
    # Обновить сообщение
    elif action == "refresh":
        duel = system.get_duel(duel_id)
        if duel:
            await update_duel_message(duel, query.message)
            await query.answer("🔄 Сообщение обновлено", show_alert=False)
        else:
            await query.answer("❌ Дуэль не найдена", show_alert=True)
    
    # Закрыть сообщение
    elif action == "close":
        await query.message.delete()
        await query.answer("✅ Сообщение закрыто", show_alert=False)
    
    # Неизвестное действие
    else:
        await query.answer("⚙️ Функция в разработке", show_alert=True)

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

async def update_duel_message(duel_data: Dict, message):
    """Обновляет сообщение дуэли"""
    try:
        ends_at = datetime.fromisoformat(duel_data["ends_at"])
        now = datetime.now()
        
        if now >= ends_at or duel_data.get("status") in ["finished", "surrendered"]:
            # Дуэль завершена
            if duel_data.get("winner_name") and duel_data["winner_name"] != "Ничья":
                winner_text = f"🏆 ПОБЕДИТЕЛЬ: {duel_data['winner_name']}!\n\n"
            else:
                winner_text = "🤝 НИЧЬЯ!\n\n"
            
            text = (
                f"⚔️ ДУЭЛЬ ЗАВЕРШЕНА\n\n"
                f"{winner_text}"
                f"Итоговый счёт:\n"
                f"👤 {duel_data['challenger_name']}: {duel_data['challenger_damage']} урона\n"
                f"👤 {duel_data['target_name']}: {duel_data['target_damage']} урона\n\n"
                f"🎯 Награда: +{duel_data['reward']} урона"
            )
            
            await message.edit_text(
                text,
                reply_markup=get_duel_finished_keyboard(duel_data['id'])
            )
            return
        
        # Дуэль активна
        remaining = max(0, (ends_at - now).seconds)
        minutes = remaining // 60
        seconds = remaining % 60
        
        if duel_data['challenger_damage'] > duel_data['target_damage']:
            leader = f"👑 Лидирует: {duel_data['challenger_name']}"
        elif duel_data['target_damage'] > duel_data['challenger_damage']:
            leader = f"👑 Лидирует: {duel_data['target_name']}"
        else:
            leader = "⚖️ Ничья!"
        
        text = (
            f"⚔️ ДУЭЛЬ В РЕАЛЬНОМ ВРЕМЕНИ\n\n"
            f"{leader}\n\n"
            f"👤 {duel_data['challenger_name']}:\n"
            f"• Урон: {duel_data['challenger_damage']}\n"
            f"• Шлёпков: {duel_data['challenger_shleps']}\n\n"
            f"👤 {duel_data['target_name']}:\n"
            f"• Урон: {duel_data['target_damage']}\n"
            f"• Шлёпков: {duel_data['target_shleps']}\n\n"
            f"⏱️ Осталось: {minutes:02d}:{seconds:02d}\n"
            f"🎯 Награда: +{duel_data['reward']} урона"
        )
        
        await message.edit_text(
            text,
            reply_markup=get_duel_active_keyboard(duel_data['id'])
        )
        
    except Exception as e:
        logger.error(f"Ошибка обновления сообщения дуэли: {e}")

# ========== ГЛОБАЛЬНЫЙ ЭКЗЕМПЛЯР ==========

duel_system = SimpleDuelSystem()

# ========== ИНИЦИАЛИЗАЦИЯ ==========

def init_duel_system():
    """Инициализирует систему дуэлей"""
    system = SimpleDuelSystem()
    cleaned = system.cleanup()
    if cleaned > 0:
        logger.info(f"✅ Очищено {cleaned} просроченных дуэлей")
    return system

# Автоматическая инициализация при импорте
init_duel_system()
