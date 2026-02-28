import traceback
import uuid
from typing import Any, Dict, Optional, List, Union
from contextvars import ContextVar
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import ValidationError as PydanticValidationError

from src.core.config_log import logger


request_id_ctx: ContextVar[str] = ContextVar("request_id", default=None)

class DigitalPetsException(Exception):
    """Базовый класс для всех пользовательских исключений."""
    def __init__(
        self, 
        message: str, 
        status_code: int = 500, 
        details: Optional[Union[Dict[str, Any], List[Any]]] = None,
        headers: Optional[Dict[str, str]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or []
        self.headers = headers
        super().__init__(self.message)


class ValidationError(DigitalPetsException):
    """Исключение для ошибок валидации данных."""
    
    def __init__(self, message: str, details: Optional[Dict] = None, field: Optional[str] = None):
        final_details = None
        if details is None:
            final_details = {"field": field} if field else None
        else:
            if isinstance(details, dict):
                final_details = details.copy()
                if field:
                    final_details.setdefault("field", field)
            else:
                final_details = details

        super().__init__(message=message, status_code=400, details=final_details)

class AuthenticationError(DigitalPetsException):
    """Исключение для ошибок аутентификации."""
    def __init__(self, message: str = "Необходима авторизация"):
        super().__init__(message=message, status_code=401, headers={"WWW-Authenticate": "Bearer"})

class AuthorizationError(DigitalPetsException):
    """Исключение для ошибок авторизации."""
    def __init__(self, message: str = "Доступ запрещен"):
        super().__init__(message=message, status_code=403)

class NotFoundError(DigitalPetsException):
    """Исключение для ошибок, связанных с отсутствием ресурса."""
    def __init__(self, resource: str = "Ресурс", details: Optional[Dict] = None):
        super().__init__(message=f"{resource} не найден", status_code=404, details=details)

class ConflictError(DigitalPetsException):
    """Исключение для ошибок конфликта ресурсов."""
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(message=message, status_code=409, details=details)

class InternalServerError(DigitalPetsException):
    """Исключение для внутренних ошибок сервера."""
    def __init__(self, message: str = "Внутренняя ошибка сервера"):
        super().__init__(message=message, status_code=500)


def create_error_response(
    status_code: int,
    message: str,
    details: Any = None,
) -> JSONResponse:
    """Создает стандартизированный JSON ответ."""
    
    req_id = request_id_ctx.get()
    
    error_content = {
        "code": status_code,
        "message": message,
        "request_id": req_id
    }
    if details:
        error_content["details"] = details
        
    return JSONResponse(
        status_code=status_code,
        content={"error": error_content}
    )

def translate_pydantic_error(error_type: str, original_msg: str, ctx: dict = None) -> str:
    """
    Переводит системные ошибки Pydantic на русский язык.
    """
    
    if "value_error" in error_type and any(c in original_msg for c in "а-яА-Я"):
        return original_msg

    if error_type == "enum":
        import re
        matches = re.findall(r"'([^']+)'", original_msg)
        if matches:
            unique_values = list(dict.fromkeys(matches))
            values_str = ", ".join(unique_values)
            return f"Допустимые значения: {values_str}"
        return "Выберите значение из списка разрешенных"

    translations = {
        "json_invalid": "Некорректный формат JSON",
        "missing": "Поле обязательно для заполнения",
        "email_type": "Некорректный адрес электронной почты",
        "value_error.email": "Некорректный адрес электронной почты",
        "string_too_short": f"Минимальная длина — {ctx.get('min_length')} симв." if ctx else "Слишком короткое значение",
        "string_too_long": f"Максимальная длина — {ctx.get('max_length')} симв." if ctx else "Слишком длинное значение",
        "too_short": "Слишком короткое значение",
        "type_error.enum": "Выберите значение из списка разрешенных",
        "int_parsing": "Должно быть целым числом",
    }
    
    if "email" in original_msg.lower():
        return "Некорректный адрес электронной почты"

    return translations.get(error_type, original_msg)


async def digitalpets_exception_handler(request: Request, exc: DigitalPetsException) -> JSONResponse:
    """Обработчик для всех исключений, наследующихся от DigitalPetsException."""
    
    logger.warning(f"API Error: {exc.message} | Path: {request.url.path}")
    return create_error_response(exc.status_code, exc.message, exc.details)

async def validation_exception_handler(request: Request, exc: Union[RequestValidationError, PydanticValidationError]) -> JSONResponse:
    """Обработчик для ошибок валидации данных от Pydantic."""
    
    formatted_errors = []
    for error in exc.errors():
        field_path = ".".join(str(x) for x in error.get("loc", []))
        err_type = error.get("type")
        ctx = error.get("ctx")
        
        raw_msg = error.get("msg", "")
        clean_msg = raw_msg.replace("Value error, ", "").replace("Assertion failed, ", "")
        
        final_msg = translate_pydantic_error(err_type, clean_msg, ctx)
        
        formatted_errors.append({
            "field": field_path,
            "message": final_msg,
            "type": err_type
        })

    logger.info(f"Validation Error: {formatted_errors} | Path: {request.url.path}")
    return create_error_response(422, "Ошибка валидации данных", formatted_errors)


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Обработчик для стандартных HTTP исключений от Starlette."""
    
    messages = {404: "Ресурс не найден", 405: "Метод не разрешен"}
    msg = messages.get(exc.status_code, str(exc.detail))
    return create_error_response(exc.status_code, msg)

async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Обработчик для всех непредвиденных исключений."""
    
    logger.error(f"Unhandled Exception: {type(exc).__name__}: {str(exc)} | Traceback: {traceback.format_exc()}")
    return create_error_response(500, "Произошла внутренняя ошибка сервера")


async def request_id_middleware(request: Request, call_next):
    """Middleware для генерации уникального идентификатора запроса и его передачи в контекст."""
    
    req_id = str(uuid.uuid4())
    request_id_ctx.set(req_id)
    response = await call_next(request)
    response.headers["X-Request-ID"] = req_id
    return response

def setup_exception_handlers(app: FastAPI):
    """Функция для настройки всех обработчиков исключений и middleware в FastAPI приложении."""
    
    app.middleware("http")(request_id_middleware)
    app.add_exception_handler(DigitalPetsException,digitalpets_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(PydanticValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)