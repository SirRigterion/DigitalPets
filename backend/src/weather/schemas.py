from pydantic import BaseModel, Field


class WeatherResponse(BaseModel):
    """Модель ответа с погодой. Содержит температуру и описание погоды."""
    
    temp: float
    description: str

class LocationRequest(BaseModel):
    """Модель запроса с координатами. Содержит широту и долготу с валидацией диапазона."""
    
    latitude: float = Field(...,  ge=-90,  le=90,  description="Широта в градусах от -90 до 90" )
    longitude: float = Field(...,  ge=-180,  le=180,  description="Долгота в градусах от -180 до 180" )