import re
from typing import Dict, Any

from src.core.config_log import logger


class ContentFilter:
    """Фильтр контента автоматическая модерация"""
    
    BANNED_WORDS = {
    # --- Спам и реклама ---
    "спам", "ИИ", "боты", "бот"
    
    # --- Мошенничество и финансы ---
    "скам", "развод", "кидалово", "фишинг", "дроп", "кардинг",
    "обналичка", "обнал", "блокчейн", "биткоин", "usdt", "transfer",
    "wmz", "webmoney", "qiwi", "cvv", "cvc", "пин-код"
    
    # --- Кибербезопасность и взлом ---
    "взлом", "хак", "хакер", "кракер", "эксплойт", "шифровальщик", "стилер",
    "логгер", "кейлоггер", "троян", "вирус", "малварь", "брут", "перебор",
    "чекер", "валидатор", "бд", "слив", "дампы", "логи", "аккаунты",
    "админка", "бэкдор", "руткит",
    
    # --- Недопустимый контент ---
    "порно", "эротика", "18+", "секс", "интим",
    "казино", "ставка", "бет", "покер", "слоты", "тотализатор",
    "наркотики", "меф", "соль", "гашиш",
    
    # --- Агрессия и угрозы ---
    "угроза", "убийство", "террор", "взрыв", "оружие", "пистолет", "автомат",
    "оскорбление", "мат", "пидор", "шлюха", "сука", "блять", "ебать",
    
    # --- Технические триггеры (часто в спаме) ---
    "bit.ly", "t.me", "telegra.ph", "консультация", "менеджер",
    "звоните", "пишите", "срочно", "вакансия"
}
    
    PATTERNS = {
        "links": r'https?://[^\s]+',
        "credit_cards": r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
        "emails": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        "phones": r'(\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}',
    }

    async def validate_content(self, text: str) -> Dict[str, Any]:
        """Проверяет сообщение и возвращает результат модерации."""
        violations = []
        lowered_text = text.lower()

        for word in self.BANNED_WORDS:
            if word in lowered_text:
                violations.append(f"Запрещённое слово: '{word}'")

        for pattern_name, pattern in self.PATTERNS.items():
            if re.search(pattern, text):
                pattern_descriptions = {
                    "links": "Ссылки запрещены в сообщениях",
                    "credit_cards": "Обнаружены данные кредитной карты",
                }
                violations.append(pattern_descriptions.get(pattern_name, f"Обнаружено: {pattern_name}"))

        is_allowed = len(violations) == 0
        
        if not is_allowed:
            logger.warning(f"Сообщение не прошло модерацию. Нарушения: {violations}")

        return {
            "is_allowed": is_allowed,
            "violations": violations,
            "status": "sent" if is_allowed else "moderated"
        }

    async def add_banned_word(self, word: str) -> None:
        """Добавить слово в чёрный список."""
        self.BANNED_WORDS.add(word.lower())

    async def remove_banned_word(self, word: str) -> None:
        """Удалить слово из чёрного списка."""
        self.BANNED_WORDS.discard(word.lower())
