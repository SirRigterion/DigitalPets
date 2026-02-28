from fastapi import APIRouter, Depends
import httpx

from src.core.config_app import settings
from src.core.config_log import logger
from src.auth import get_current_user
from src.db.models import User
from src.utils.decorators import active_user_required
from src.weather.schemas import WeatherResponse, LocationRequest
from src.core.exceptions import ValidationError

weather_router = APIRouter()

# Fallback погода по умолчанию
DEFAULT_WEATHER = WeatherResponse(
    temp=15.0,
    description="Нет данных",
)

WEATHER_MAIN_TRANSLATIONS = {
    "Clear": "Ясно",
    "Clouds": "Облачно",
    "Rain": "Дождь",
    "Drizzle": "Ливень",
    "Thunderstorm": "Гроза",
    "Snow": "Снег",
    "Mist": "Дымка",
    "Smoke": "Дымка",
    "Haze": "Мгла",
    "Dust": "Пыль",
    "Fog": "Туман",
    "Sand": "Сухо",
    "Ash": "Пепел",
    "Squall": "Шквал",
    "Tornado": "Торнадо"
}

async def _fetch_weather(latitude: float, longitude: float) -> WeatherResponse:
    """Получить погоду по координатам из OpenWeather API. При ошибке возвращает fallback."""
    
    if not settings.OPENWEATHER_API_KEY:
        return DEFAULT_WEATHER
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={
                    "lat": latitude,
                    "lon": longitude,
                    "appid": settings.OPENWEATHER_API_KEY,
                    "units": "metric",
                    "lang": "ru",
                },
                timeout=10.0
            )
            
            if response.status_code == 401:
                logger.error(f"OpenWeather API: 401 Unauthorized. Проверьте API ключ в переменной окружения OPENWEATHER_API_KEY")
                return DEFAULT_WEATHER
            
            if response.status_code == 429:
                logger.warning(f"OpenWeather API: 429 Rate Limited. Используем fallback.")
                return DEFAULT_WEATHER
            
            response.raise_for_status()
            data = response.json()
            weather_description_ru = WEATHER_MAIN_TRANSLATIONS.get(
                data["weather"][0]["main"], 
                data["weather"][0]["description"]
            )
            return WeatherResponse(
                temp=float(round(data["main"]["temp"])),
                description=weather_description_ru
            )
    except httpx.HTTPStatusError as e:
        logger.error(f"OpenWeather API HTTP ошибка ({e.response.status_code}): {str(e)[:100]}")
        return DEFAULT_WEATHER
    except httpx.TimeoutException:
        logger.warning("OpenWeather API: Timeout. Используем fallback.")
        return DEFAULT_WEATHER
    except httpx.RequestError as e:
        logger.error(f"OpenWeather API: Ошибка подключения: {str(e)[:100]}")
        return DEFAULT_WEATHER
    except Exception as e:
        logger.error(f"OpenWeather API: Неожиданная ошибка: {str(e)[:100]}")
        return DEFAULT_WEATHER


@weather_router.post("/", response_model=WeatherResponse)
async def get_weather_post(location: LocationRequest):
    """Получить погоду по передаваемым координатам (POST запрос)."""
    
    return await _fetch_weather(location.latitude, location.longitude)


@weather_router.get("/me", response_model=WeatherResponse)
@active_user_required
async def get_weather_me(current_user: User = Depends(get_current_user)):
    """Получить погоду по локации текущего пользователя (защищённый)."""
    
    lat = getattr(current_user, "location_lat", None)
    lon = getattr(current_user, "location_lon", None)
    if lat is None or lon is None:
        raise ValidationError("Ваша локация не указана. Пожалуйста, обновите её в профиле.")
    return await _fetch_weather(lat, lon)
