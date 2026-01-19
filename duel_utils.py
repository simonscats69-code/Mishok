# duel_utils.py
import logging
from typing import Dict, Any, Optional, Tuple
from telegram import User
from datetime import datetime

logger = logging.getLogger(__name__)

def validate_duel_invite(invite: Dict[str, Any], user: User) -> Tuple[bool, str]:
    """
    Проверяет, может ли пользователь принять/отклонить приглашение на дуэль
    
    Args:
        invite: Данные приглашения
        user: Пользователь Telegram
        
    Returns:
        Tuple[bool, str]: (можно ли принять/отклонить, сообщение об ошибке)
    """
    try:
        # Проверка времени
        expires_at = datetime.fromisoformat(invite["expires_at"])
        if datetime.now() > expires_at:
            return False, "Приглашение просрочено"
        
        # Проверка пользователя
        return is_user_target(invite, user)
        
    except Exception as e:
        logger.error(f"Ошибка проверки приглашения: {e}")
        return False, "Ошибка проверки приглашения"

def is_user_target(invite: Dict[str, Any], user: User) -> Tuple[bool, str]:
    """
    Проверяет, является ли пользователь целевым для приглашения
    
    Args:
        invite: Данные приглашения
        user: Пользователь Telegram
        
    Returns:
        Tuple[bool, str]: (является ли целевым, сообщение об ошибке)
    """
    try:
        target_name = invite["target_name"].lower().replace("@", "").strip()
        
        if not target_name:
            return False, "Некорректное имя цели"
        
        # Получаем чистые имена пользователя
        username = (user.username or "").lower().replace("@", "").strip()
        first_name = user.first_name.lower().strip()
        last_name = (user.last_name or "").lower().strip()
        
        # Список всех вариантов имени пользователя
        user_names = [username, first_name]
        if last_name:
            user_names.append(last_name)
            user_names.append(f"{first_name} {last_name}")
        
        # Проверки в порядке приоритета
        
        # 1. Прямое совпадение
        for name in user_names:
            if name and target_name == name:
                return True, ""
        
        # 2. Если target_name начинается с @ (упоминание)
        if invite["target_name"].startswith("@"):
            target_without_at = target_name[1:] if target_name.startswith("@") else target_name
            for name in user_names:
                if name and target_without_at == name:
                    return True, ""
        
        # 3. Частичное совпадение (менее надежно, но на крайний случай)
        for name in user_names:
            if name and (target_name in name or name in target_name):
                return True, ""
        
        return False, "Это приглашение не для вас"
        
    except Exception as e:
        logger.error(f"Ошибка проверки целевого пользователя: {e}")
        return False, "Ошибка проверки"

def format_duel_time_remaining(ends_at_iso: str) -> str:
    """
    Форматирует оставшееся время дуэли
    
    Args:
        ends_at_iso: Время окончания дуэли в формате ISO
        
    Returns:
        str: Отформатированное время
    """
    try:
        ends_at = datetime.fromisoformat(ends_at_iso)
        now = datetime.now()
        
        if now >= ends_at:
            return "00:00"
        
        remaining = ends_at - now
        minutes = remaining.seconds // 60
        seconds = remaining.seconds % 60
        
        return f"{minutes:02d}:{seconds:02d}"
    except Exception as e:
        logger.error(f"Ошибка форматирования времени дуэли: {e}")
        return "??:??"

def get_duel_status(duel: Dict[str, Any]) -> str:
    """
    Получает статус дуэли
    
    Args:
        duel: Данные дуэли
        
    Returns:
        str: Статус дуэли
    """
    try:
        if "finished_at" in duel:
            if duel.get("winner_id"):
                return "finished_win"
            elif duel.get("ended_by") == "surrender":
                return "finished_surrender"
            else:
                return "finished_draw"
        
        ends_at = datetime.fromisoformat(duel["ends_at"])
        if datetime.now() >= ends_at:
            return "expired"
        
        return "active"
    except Exception as e:
        logger.error(f"Ошибка получения статуса дуэли: {e}")
        return "unknown"

def calculate_duel_progress(duel: Dict[str, Any]) -> Tuple[int, int, int, int]:
    """
    Рассчитывает прогресс дуэли
    
    Args:
        duel: Данные дуэли
        
    Returns:
        Tuple[int, int, int, int]: (процент вызователя, процент цели, 
                                    урон вызователя, урон цели)
    """
    try:
        challenger_damage = duel.get("challenger_damage", 0)
        target_damage = duel.get("target_damage", 0)
        total_damage = challenger_damage + target_damage
        
        if total_damage > 0:
            challenger_percent = int((challenger_damage / total_damage) * 100)
            target_percent = 100 - challenger_percent
        else:
            challenger_percent = 50
            target_percent = 50
        
        return challenger_percent, target_percent, challenger_damage, target_damage
    except Exception as e:
        logger.error(f"Ошибка расчета прогресса дуэли: {e}")
        return 50, 50, 0, 0

def format_duel_id(user_id: int, target_name: str) -> str:
    """
    Форматирует ID дуэли
    
    Args:
        user_id: ID пользователя
        target_name: Имя цели
        
    Returns:
        str: ID дуэли
    """
    from datetime import datetime
    import random
    import hashlib
    
    try:
        timestamp = int(datetime.now().timestamp())
        random_suffix = random.randint(1000, 9999)
        
        # Создаем хэш для уникальности
        hash_input = f"{user_id}_{target_name}_{timestamp}_{random_suffix}"
        hash_obj = hashlib.md5(hash_input.encode())
        hash_hex = hash_obj.hexdigest()[:8]
        
        return f"duel_{user_id}_{timestamp}_{hash_hex}"
    except Exception as e:
        logger.error(f"Ошибка форматирования ID дуэли: {e}")
        return f"duel_{user_id}_{int(datetime.now().timestamp())}"

def can_user_accept_duel(invite: Dict[str, Any], user: User) -> Tuple[bool, str]:
    """
    Проверяет, может ли пользователь принять дуэль
    
    Args:
        invite: Данные приглашения
        user: Пользователь Telegram
        
    Returns:
        Tuple[bool, str]: (может ли принять, сообщение об ошибке)
    """
    try:
        # Проверяем, является ли пользователь целевым
        is_target, error_msg = is_user_target(invite, user)
        if not is_target:
            return False, error_msg
        
        # Проверяем время
        expires_at = datetime.fromisoformat(invite["expires_at"])
        if datetime.now() > expires_at:
            return False, "Приглашение просрочено"
        
        # Проверяем, не участвует ли пользователь уже в другой дуэли
        from database import get_user_active_duel
        active_duel = get_user_active_duel(user.id)
        if active_duel:
            opponent = active_duel["target_name"] if user.id == active_duel["challenger_id"] else active_duel["challenger_name"]
            return False, f"Вы уже участвуете в дуэли с {opponent}"
        
        return True, ""
        
    except Exception as e:
        logger.error(f"Ошибка проверки возможности принять дуэль: {e}")
        return False, "Ошибка проверки"

def get_duel_reward_message(duel: Dict[str, Any]) -> str:
    """
    Получает сообщение о награде за дуэль
    
    Args:
        duel: Данные дуэли
        
    Returns:
        str: Сообщение о награде
    """
    try:
        if "winner_name" not in duel or not duel["winner_name"]:
            return "Ничья! Награда не присуждается."
        
        reward = duel.get("reward", 0)
        winner_name = duel["winner_name"]
        
        if duel.get("ended_by") == "surrender":
            return f"🏆 {winner_name} получает +{reward//2} к урону (сдача противника)"
        else:
            return f"🏆 {winner_name} получает +{reward} к урону!"
    except Exception as e:
        logger.error(f"Ошибка получения сообщения о награде: {e}")
        return "Награда: +0 к урону"

def create_duel_history_entry(action: str, user_id: int, user_name: str, 
                             damage: int = 0, duel_id: str = "") -> Dict[str, Any]:
    """
    Создает запись в истории дуэли
    
    Args:
        action: Действие ("shlep", "accept", "decline", "surrender", "finish")
        user_id: ID пользователя
        user_name: Имя пользователя
        damage: Урон (для действия "shlep")
        duel_id: ID дуэли
        
    Returns:
        Dict[str, Any]: Запись истории
    """
    return {
        "action": action,
        "user_id": user_id,
        "user_name": user_name,
        "damage": damage,
        "duel_id": duel_id,
        "timestamp": datetime.now().isoformat()
    }
