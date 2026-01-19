[file name]: duel_system.py
[file content begin]
"""
Простая и надежная система дуэлей
"""
import json
import os
import random
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

DUELS_FILE = "data/duels.json"

@dataclass
class DuelInvite:
    """Приглашение на дуэль"""
    id: str
    challenger_id: int
    challenger_name: str
    target_id: int
    target_name: str
    chat_id: int
    created_at: str
    expires_at: str
    status: str = "pending"  # pending, accepted, declined, expired
    
    def is_expired(self) -> bool:
        return datetime.now() > datetime.fromisoformat(self.expires_at)
    
    def is_for_user(self, user_id: int, username: str) -> bool:
        """Проверяет, предназначено ли приглашение пользователю"""
        # Проверяем по ID
        if self.target_id == user_id:
            return True
        
        # Проверяем по имени (если target_id еще не установлен)
        if self.target_id == 0:
            target_lower = self.target_name.lower().replace("@", "").strip()
            user_lower = username.lower().strip()
            user_username_lower = (username or "").lower().strip()
            
            return (target_lower in user_lower or 
                   user_lower in target_lower or
                   target_lower == user_lower or
                   target_lower == user_username_lower)
        
        return False

@dataclass
class ActiveDuel:
    """Активная дуэль"""
    id: str
    challenger_id: int
    challenger_name: str
    challenger_damage: int = 0
    challenger_shleps: int = 0
    target_id: int
    target_name: str
    target_damage: int = 0
    target_shleps: int = 0
    chat_id: int
    message_id: Optional[int] = None
    started_at: str = None
    ends_at: str = None
    winner_id: Optional[int] = None
    winner_name: Optional[str] = None
    reward: int = 0
    history: List[Dict] = None
    
    def __post_init__(self):
        if self.started_at is None:
            self.started_at = datetime.now().isoformat()
        if self.ends_at is None:
            self.ends_at = (datetime.now() + timedelta(minutes=5)).isoformat()
        if self.history is None:
            self.history = []
        if self.reward == 0:
            self.reward = random.randint(15, 40)
    
    def is_finished(self) -> bool:
        return (self.winner_id is not None or 
                datetime.now() > datetime.fromisoformat(self.ends_at))
    
    def add_damage(self, user_id: int, damage: int, username: str):
        """Добавляет урон от пользователя"""
        action = {
            "user_id": user_id,
            "username": username,
            "damage": damage,
            "timestamp": datetime.now().isoformat()
        }
        
        if user_id == self.challenger_id:
            self.challenger_damage += damage
            self.challenger_shleps += 1
            action["side"] = "challenger"
        elif user_id == self.target_id:
            self.target_damage += damage
            self.target_shleps += 1
            action["side"] = "target"
        else:
            return False
        
        self.history.append(action)
        if len(self.history) > 20:
            self.history = self.history[-20:]
        
        return True
    
    def finish(self):
        """Завершает дуэль и определяет победителя"""
        if self.challenger_damage > self.target_damage:
            self.winner_id = self.challenger_id
            self.winner_name = self.challenger_name
        elif self.target_damage > self.challenger_damage:
            self.winner_id = self.target_id
            self.winner_name = self.target_name
        else:
            # Ничья
            self.winner_id = None
            self.winner_name = None

class DuelManager:
    """Менеджер дуэлей"""
    
    def __init__(self):
        self.duels_file = DUELS_FILE
        self._ensure_files()
    
    def _ensure_files(self):
        """Создает необходимые файлы"""
        os.makedirs(os.path.dirname(self.duels_file), exist_ok=True)
        if not os.path.exists(self.duels_file):
            self._save_data({
                "invites": {},
                "active": {},
                "history": []
            })
    
    def _load_data(self) -> Dict:
        """Загружает данные дуэлей"""
        try:
            with open(self.duels_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"invites": {}, "active": {}, "history": []}
    
    def _save_data(self, data: Dict):
        """Сохраняет данные дуэлей"""
        try:
            # Конвертируем dataclasses в dict
            def convert(obj):
                if isinstance(obj, (DuelInvite, ActiveDuel)):
                    return asdict(obj)
                elif isinstance(obj, list):
                    return [convert(item) for item in obj]
                elif isinstance(obj, dict):
                    return {key: convert(value) for key, value in obj.items()}
                return obj
            
            converted_data = convert(data)
            
            with open(self.duels_file, 'w', encoding='utf-8') as f:
                json.dump(converted_data, f, indent=2, ensure_ascii=False, default=str)
            return True
        except Exception as e:
            logger.error(f"Ошибка сохранения дуэлей: {e}")
            return False
    
    # ========== УПРАВЛЕНИЕ ПРИГЛАШЕНИЯМИ ==========
    
    def create_invite(self, challenger_id: int, challenger_name: str,
                     target_name: str, chat_id: int) -> Optional[DuelInvite]:
        """Создает новое приглашение на дуэль"""
        try:
            # Генерируем ID
            timestamp = int(datetime.now().timestamp())
            random_suffix = random.randint(1000, 9999)
            duel_id = f"inv_{challenger_id}_{timestamp}_{random_suffix}"
            
            invite = DuelInvite(
                id=duel_id,
                challenger_id=challenger_id,
                challenger_name=challenger_name,
                target_id=0,  # Будет установлен при принятии
                target_name=target_name,
                chat_id=chat_id,
                created_at=datetime.now().isoformat(),
                expires_at=(datetime.now() + timedelta(minutes=5)).isoformat()
            )
            
            data = self._load_data()
            data["invites"][duel_id] = asdict(invite)
            self._save_data(data)
            
            logger.info(f"Создано приглашение: {duel_id} от {challenger_name} для {target_name}")
            return invite
        except Exception as e:
            logger.error(f"Ошибка создания приглашения: {e}")
            return None
    
    def get_invite(self, invite_id: str) -> Optional[DuelInvite]:
        """Получает приглашение по ID"""
        data = self._load_data()
        invite_data = data["invites"].get(invite_id)
        if invite_data:
            return DuelInvite(**invite_data)
        return None
    
    def get_user_invites(self, user_id: int, username: str) -> List[DuelInvite]:
        """Получает все приглашения для пользователя"""
        data = self._load_data()
        invites = []
        
        for invite_data in data["invites"].values():
            invite = DuelInvite(**invite_data)
            if invite.is_for_user(user_id, username) and not invite.is_expired():
                invites.append(invite)
        
        return invites
    
    def accept_invite(self, invite_id: str, user_id: int, username: str) -> Optional[ActiveDuel]:
        """Принимает приглашение на дуэль"""
        try:
            data = self._load_data()
            
            if invite_id not in data["invites"]:
                return None
            
            invite_data = data["invites"][invite_id]
            invite = DuelInvite(**invite_data)
            
            # Проверяем, предназначено ли пользователю
            if not invite.is_for_user(user_id, username):
                return None
            
            # Проверяем срок действия
            if invite.is_expired():
                # Перемещаем в историю как просроченное
                invite.status = "expired"
                data["history"].append(asdict(invite))
                del data["invites"][invite_id]
                self._save_data(data)
                return None
            
            # Создаем активную дуэль
            duel_id = invite_id.replace("inv_", "duel_")
            duel = ActiveDuel(
                id=duel_id,
                challenger_id=invite.challenger_id,
                challenger_name=invite.challenger_name,
                target_id=user_id,
                target_name=username,
                chat_id=invite.chat_id
            )
            
            # Обновляем данные
            invite.status = "accepted"
            invite.target_id = user_id
            invite.target_name = username
            
            data["active"][duel_id] = asdict(duel)
            data["history"].append(asdict(invite))
            del data["invites"][invite_id]
            
            self._save_data(data)
            
            logger.info(f"Дуэль начата: {duel_id} между {duel.challenger_name} и {duel.target_name}")
            return duel
        except Exception as e:
            logger.error(f"Ошибка принятия приглашения: {e}")
            return None
    
    def decline_invite(self, invite_id: str, user_id: int, username: str) -> bool:
        """Отклоняет приглашение на дуэль"""
        try:
            data = self._load_data()
            
            if invite_id not in data["invites"]:
                return False
            
            invite_data = data["invites"][invite_id]
            invite = DuelInvite(**invite_data)
            
            if not invite.is_for_user(user_id, username):
                return False
            
            invite.status = "declined"
            data["history"].append(asdict(invite))
            del data["invites"][invite_id]
            
            self._save_data(data)
            return True
        except Exception as e:
            logger.error(f"Ошибка отклонения приглашения: {e}")
            return False
    
    # ========== УПРАВЛЕНИЕ АКТИВНЫМИ ДУЭЛЯМИ ==========
    
    def get_active_duel(self, duel_id: str) -> Optional[ActiveDuel]:
        """Получает активную дуэль по ID"""
        data = self._load_data()
        duel_data = data["active"].get(duel_id)
        if duel_data:
            return ActiveDuel(**duel_data)
        return None
    
    def get_user_active_duel(self, user_id: int) -> Optional[ActiveDuel]:
        """Получает активную дуэль пользователя"""
        data = self._load_data()
        
        for duel_data in data["active"].values():
            duel = ActiveDuel(**duel_data)
            if duel.challenger_id == user_id or duel.target_id == user_id:
                return duel
        
        return None
    
    def add_damage_to_duel(self, duel_id: str, user_id: int, damage: int, username: str) -> Optional[Dict]:
        """Добавляет урон в дуэль"""
        try:
            data = self._load_data()
            
            if duel_id not in data["active"]:
                return None
            
            duel_data = data["active"][duel_id]
            duel = ActiveDuel(**duel_data)
            
            # Проверяем, является ли пользователь участником
            if user_id not in [duel.challenger_id, duel.target_id]:
                return None
            
            # Проверяем, не завершена ли дуэль
            if duel.is_finished():
                return None
            
            # Добавляем урон
            if duel.add_damage(user_id, damage, username):
                # Проверяем, не истекло ли время
                if datetime.now() > datetime.fromisoformat(duel.ends_at):
                    duel.finish()
                    result = {
                        "winner_id": duel.winner_id,
                        "winner_name": duel.winner_name,
                        "is_finished": True
                    }
                    
                    # Перемещаем в историю
                    data["history"].append(asdict(duel))
                    del data["active"][duel_id]
                else:
                    result = {
                        "is_finished": False,
                        "duel": duel
                    }
                    data["active"][duel_id] = asdict(duel)
                
                self._save_data(data)
                return result
            
            return None
        except Exception as e:
            logger.error(f"Ошибка добавления урона в дуэль: {e}")
            return None
    
    def surrender_duel(self, duel_id: str, user_id: int) -> Optional[Dict]:
        """Сдача в дуэли"""
        try:
            data = self._load_data()
            
            if duel_id not in data["active"]:
                return None
            
            duel_data = data["active"][duel_id]
            duel = ActiveDuel(**duel_data)
            
            # Определяем победителя (противник сдавшегося)
            if user_id == duel.challenger_id:
                winner_id = duel.target_id
                winner_name = duel.target_name
                surrenderer_name = duel.challenger_name
            else:
                winner_id = duel.challenger_id
                winner_name = duel.challenger_name
                surrenderer_name = duel.target_name
            
            duel.winner_id = winner_id
            duel.winner_name = winner_name
            
            result = {
                "winner_id": winner_id,
                "winner_name": winner_name,
                "surrenderer_name": surrenderer_name,
                "reward": duel.reward // 2  # Половина награды за сдачу
            }
            
            # Перемещаем в историю
            data["history"].append(asdict(duel))
            del data["active"][duel_id]
            
            self._save_data(data)
            return result
        except Exception as e:
            logger.error(f"Ошибка при сдаче в дуэли: {e}")
            return None
    
    # ========== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ==========
    
    def cleanup_expired(self):
        """Очищает просроченные приглашения и дуэли"""
        try:
            data = self._load_data()
            cleaned = 0
            
            # Очистка просроченных приглашений
            expired_invites = []
            for invite_id, invite_data in data["invites"].items():
                invite = DuelInvite(**invite_data)
                if invite.is_expired():
                    invite.status = "expired"
                    data["history"].append(asdict(invite))
                    expired_invites.append(invite_id)
                    cleaned += 1
            
            for invite_id in expired_invites:
                del data["invites"][invite_id]
            
            # Очистка завершенных дуэлей
            expired_duels = []
            for duel_id, duel_data in data["active"].items():
                duel = ActiveDuel(**duel_data)
                if duel.is_finished():
                    data["history"].append(asdict(duel))
                    expired_duels.append(duel_id)
                    cleaned += 1
            
            for duel_id in expired_duels:
                del data["active"][duel_id]
            
            if cleaned > 0:
                self._save_data(data)
                logger.info(f"Очищено {cleaned} просроченных записей")
            
            return cleaned
        except Exception as e:
            logger.error(f"Ошибка очистки дуэлей: {e}")
            return 0
    
    def get_all_invites(self) -> List[DuelInvite]:
        """Получает все приглашения"""
        data = self._load_data()
        return [DuelInvite(**invite) for invite in data["invites"].values()]
    
    def get_all_active_duels(self) -> List[ActiveDuel]:
        """Получает все активные дуэли"""
        data = self._load_data()
        return [ActiveDuel(**duel) for duel in data["active"].values()]

# Глобальный экземпляр менеджера
duel_manager = DuelManager()
[file content end]
