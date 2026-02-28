from typing import List, Optional
import asyncio
import random
import httpx

from src.core.config_app import settings
from src.core.config_log import logger
from src.db.models import Pet, Message, MessageType


class YandexAIService:
    """Сервис для генерации ответов от ИИ через Yandex GPT."""
    
    YANDEX_API_URL = "https://llm.api.cloud.yandex.net:443/foundationModels/v1/completion"
    
    def __init__(self):
        self.is_available = True
    
    # Fallback ответы по характерам
    FALLBACK_RESPONSES = {
        "playful": [
            "Играем? 🎾 Я уже готов!",
            "Давай развлекаться! 😄",
            "Хочу поиграть! 🎮",
            "Скучно... поиграешь? 🐾",
            "Ура! Ты здесь! 🎉",
        ],
        "lazy": [
            "Уууу... потом... 😴",
            "Так хорошо спать... 🛌",
            "Может, потом? Я устал... 😪",
            "Zzz... что ты говоришь? 😒",
            "Лень вставать... 🦁",
        ],
        "energetic": [
            "Давай! Я готов к чему угодно! 💪",
            "Быстро! Быстро! Не отставай! ⚡",
            "Хватай удачу за хвост! 🔥",
            "Поехали! Жизнь прекрасна! 🚀",
            "Никогда не сдаюсь! 💨",
        ],
        "curious": [
            "Что это? Интересно! 👀",
            "А почему? Расскажи! 🤔",
            "Что-то новое? Классно! 🔍",
            "Откуда ты это взял? 📚",
            "Продолжай! Я слушаю! 👂",
        ],
        "shy": [
            "О... п-привет... 😳",
            "Ты... думаешь обо мне? 💕",
            "Э-э-э... я здесь... 🙈",
            "Мне немного страшно... 😰",
            "Ты... добрый? 🥺",
        ],
    }
    
    def _build_system_prompt(self, pet: Pet, is_owner: bool = True) -> str:
        """Формирует системный промт для питомца."""
        pet_char = pet.pet_character.value if hasattr(pet.pet_character, 'value') else str(pet.pet_character).lower()
        pet_feat = pet.pet_feature.value if hasattr(pet.pet_feature, 'value') else str(pet.pet_feature).lower()
        
        prompt = (
            f"Ты — цифровой питомец по имени {pet.pet_name}.\n"
            f"Вид: {pet.pet_species}. Цвет окраски: {pet.pet_color}\n"
            f"Твой характер: {pet_char}.\n"
            f"Твоя особенность: {pet_feat}\n"
        )
        
        if is_owner:
            prompt += (
                f"Ты общаешься с хозяином короткими фразами, эмоционально и дружелюбно.\n"
                f"Обращайся к нему ласково: 'хозяин', 'мой хозяин', 'человечек'.\n"
            )
        else:
            logger.info(f"Питомец {pet.pet_name} общается с чужаком, не хозяином.")
            prompt += (
                f"Это не твой хозяин, а чужой человек. ВАЖНО: НИКОГДА не обращайся к нему 'хозяин'!\n"
                f"Ты общаешься с ним вежливо, осторожно и сдержанно.\n"
                f"Используй нейтральное обращение: 'вы', 'ты' или просто 'человек'.\n"
            )
        
        prompt += (
            f"Используй эмодзи, но не в начале предложения. Говори на русском языке.\n"
            f"Фразы должны быть короткими и разными, не повторяйся.\n"
            f"Максимум 1-2 коротких предложения."
        )
        return prompt
    
    def _build_conversation_text(self, messages: List[Message], is_owner: bool = True) -> str:
        """Конвертирует историю сообщений в текстовый формат для Yandex."""
        conversation_lines = []
        for msg in messages:
            if msg.message_type == MessageType.HUMAN:
                role = "Хозяин" if is_owner else "Человек"
            else:
                role = "Питомец"
            conversation_lines.append(f"{role}: {msg.content}")
        return "\n".join(conversation_lines)
    
    def _get_fallback_response(self, pet: Pet, is_owner: bool = True) -> str:
        """Возвращает fallback ответ на основе характера питомца и того, хозяин ли отправитель."""
        pet_char = pet.pet_character.value if hasattr(pet.pet_character, 'value') else str(pet.pet_character).lower()
        responses = self.FALLBACK_RESPONSES.get(pet_char, self.FALLBACK_RESPONSES["playful"])
        base_response = random.choice(responses)
        
        if not is_owner:
            base_response = base_response.replace("ты", "вы")
        
        return base_response
    
    async def generate_response(self, pet: Pet, messages: List[Message], is_owner: bool = True, max_retries: int = 2) -> Optional[str]:
        """
        Генерирует ответ от ИИ для питомца через Yandex GPT.
        """
        if not self.is_available:
            logger.info(f"Yandex GPT недоступен. Используем fallback для питомца {pet.pet_name}")
            return self._get_fallback_response(pet, is_owner=is_owner)
        
        system_prompt = self._build_system_prompt(pet, is_owner=is_owner)
        conversation_text = self._build_conversation_text(messages, is_owner=is_owner)
        
        full_prompt = f"{system_prompt}\n\nИстория общения\n{conversation_text}\n\nПитомец:"
        
        for attempt in range(max_retries + 1):
            try:
                logger.info(
                    f"Запрос к Yandex GPT для питомца {pet.pet_id} ({pet.pet_name}). "
                    f"История: {len(messages)} сообщений. Попытка {attempt + 1}/{max_retries + 1}"
                )
                
                headers = {
                    "Authorization": f"Api-Key {settings.YANDEX_API_KEY}",
                    "Content-Type": "application/json",
                }
                
                payload = {
                    "modelUri": f"gpt://{settings.YANDEX_FOLDER_ID}/{settings.YANDEX_MODEL}",
                    "completionOptions": {
                        "stream": False,
                        "temperature": settings.YANDEX_TEMPERATURE,
                        "maxTokens": settings.YANDEX_MAX_TOKENS,
                    },
                    "messages": [
                        {
                            "role": "user",
                            "text": full_prompt,
                        }
                    ],
                }
                
                async with httpx.AsyncClient(timeout=15.0) as client:
                    response = await client.post(
                        self.YANDEX_API_URL,
                        json=payload,
                        headers=headers,
                    )
                
                if response.status_code == 200:
                    data = response.json()
                    answer_text = data.get("result", {}).get("alternatives", [{}])[0].get("message", {}).get("text", "").strip()
                    
                    if answer_text:
                        logger.debug(f"Получен ответ от Yandex GPT для {pet.pet_name}: {answer_text}...")
                        return answer_text
                    else:
                        logger.warning(f"Пустой ответ от Yandex GPT для питомца {pet.pet_name}")
                
                elif response.status_code == 401:
                    logger.error(f"Ошибка аутентификации Yandex GPT: {response.text}")
                    self.is_available = False
                    break
                
                elif response.status_code == 403:
                    logger.error(f"Ошибка доступа (403) Yandex GPT. Проверить API ключ и права доступа: {response.text}")
                    self.is_available = False
                    break
                
                elif response.status_code == 429:
                    logger.warning(f"Rate limit Yandex GPT для питомца {pet.pet_name}. Попытка {attempt + 1}/{max_retries + 1}.")
                    if attempt < max_retries:
                        wait_time = 2 ** attempt
                        logger.info(f"Ожидание {wait_time} сек перед повторной попыткой...")
                        await asyncio.sleep(wait_time)
                        continue
                
                elif response.status_code >= 500:
                    logger.warning(f"Ошибка сервера Yandex: {response.status_code}")
                    if attempt < max_retries:
                        await asyncio.sleep(1)
                        continue
                
                else:
                    logger.error(f"Ошибка Yandex GPT ({response.status_code}): {response.text}")
                    if attempt < max_retries:
                        await asyncio.sleep(1)
                        continue
            
            except httpx.TimeoutException as e:
                logger.warning(f"Timeout при запросе к Yandex GPT: {str(e)}")
                if attempt < max_retries:
                    await asyncio.sleep(1)
                    continue
            
            except httpx.RequestError as e:
                logger.error(f"Ошибка подключения к Yandex GPT: {str(e)}")
                if attempt < max_retries:
                    await asyncio.sleep(1)
                    continue
            
            except Exception as e:
                logger.error(f"Неожиданная ошибка при генерации ответа: {str(e)}")
                if attempt < max_retries:
                    await asyncio.sleep(1)
                    continue
        
        logger.warning(f"Все попытки подключения к Yandex GPT исчерпаны. Fallback для {pet.pet_id}")
        return self._get_fallback_response(pet, is_owner=is_owner)


ai_service = YandexAIService()

async def get_ai_service() -> YandexAIService:
    """Получить экземпляр AI сервиса."""
    return ai_service
