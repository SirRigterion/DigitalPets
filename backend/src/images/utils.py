import mimetypes
from pathlib import Path
from typing import Set, Dict
import uuid
import aiofiles
from fastapi import Response, UploadFile


from src.core.config_log import logger
from src.core.config_app import settings
from src.core.exceptions import ValidationError
from src.cache.redis_service import redis_service

ALLOWED_EXTENSIONS: Set[str] = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
ALLOWED_MIME_TYPES: Set[str] = {
    "image/jpeg", 
    "image/jpg", 
    "image/png", 
    "image/gif", 
    "image/webp"
}
MAX_FILE_SIZE: int = 5 * 1024 * 1024
IMAGE_CACHE_TTL = settings.IMAGE_CACHE_TTL
IMAGE_CACHE_MAX_BYTES = settings.IMAGE_CACHE_MAX_BYTES

FILE_SIGNATURES: Dict[str, bytes] = {
    "jpeg": b"\xff\xd8\xff",
    "png": b"\x89PNG\r\n\x1a\n",
    "gif": b"GIF8",
    "webp": b"RIFF"
}


def validate_extension(file_name: str) -> str:
    """Проверяет расширение файла на безопасность."""
    
    if not file_name or not file_name.strip():
        logger.warning("Пустое имя файла")
        raise ValidationError("Имя файла пустое", field="file_name")
    
    path_obj = Path(file_name)
    ext = path_obj.suffix.lower()
    
    if ext not in ALLOWED_EXTENSIONS:
        logger.warning(f"Формат {ext} не разрешен")
        raise ValidationError(f"Формат {ext} не разрешен", field="file_name")
    return ext

def validate_file_content(content: bytes) -> str:
    """Проверяет содержимое файла по магическим байтам."""
    
    if len(content) < 12:
        logger.warning("Файл поврежден или слишком мал")
        raise ValidationError("Файл поврежден или слишком мал", field="content")
    
    for file_type, signature in FILE_SIGNATURES.items():
        if content.startswith(signature):
            if file_type == "webp" and b"WEBP" not in content[8:12]:
                continue
            return file_type
            
    logger.warning("Тип файла не соответствует расширению (MIME-spoofing)")
    raise ValidationError("Тип файла не соответствует расширению (MIME-spoofing)", field="content")

def validate_mime_type(content_type: str) -> None:
    """Проверяет MIME тип файла."""
    
    if not content_type or content_type.lower() not in ALLOWED_MIME_TYPES:
        logger.warning("Недопустимый MIME-тип")
        raise ValidationError("Недопустимый MIME-тип", field="content_type")

def safe_resolve_path(base: Path, target: Path) -> Path:
    """Защита от Path Traversal атак."""
    
    try:
        base_resolved = base.resolve()
        target_resolved = target.resolve()
        if not str(target_resolved).startswith(str(base_resolved)):
            logger.warning("Попытка выхода за пределы директории")
            raise ValidationError("Попытка выхода за пределы директории", field="target_path")
        return target_resolved
    except Exception:
        logger.warning("Ошибка формирования пути")
        raise ValidationError("Ошибка формирования пути", field="target_path")

async def save_uploaded_file(
    file: UploadFile,
    entity_id: int,
    directory: str | Path,
    entity_type: str = "user"
) -> str:
    """Сохраняет файл с полной проверкой безопасности."""
    
    directory = Path(directory)
    ext = validate_extension(file.filename)
    validate_mime_type(file.content_type)

    try:
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            logger.warning("Файл превышает 5МБ")
            raise ValidationError("Файл превышает 5МБ", field="content")
    finally:
        await file.seek(0)

    validate_file_content(content)

    unique_name = f"{entity_type}-{entity_id}-{uuid.uuid4().hex}{ext}"
    safe_path = safe_resolve_path(directory, directory / unique_name)

    try:
        directory.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(safe_path, "wb") as out_f:
            await out_f.write(content)
    except Exception as e:
        logger.error(f"Ошибка при записи на диск: {e}")
        raise ValidationError("Ошибка при записи на диск", field="content")

    return unique_name

async def _serve_file(base_dir: Path, file_name: str) -> Response:
    """Отдает файл из кэша или с диска."""
    
    cache_key = f"img:{file_name}"
    
    cached_data = await redis_service.get_bytes(cache_key)
    if cached_data:
        mime, _ = mimetypes.guess_type(file_name)
        return Response(content=cached_data, media_type=mime or "image/jpeg")

    try:
        target_path = safe_resolve_path(base_dir, base_dir / file_name)
    except Exception as e:
        logger.error(f"Ошибка безопасности пути: {e}")
        raise ValidationError("Некорректный путь к файлу", field="file_name")

    if not target_path.exists():
        logger.warning(f"Файл не найден по пути: {target_path}")
        raise ValidationError("Файл не найден", field="file_name")

    try:
        async with aiofiles.open(target_path, "rb") as f:
            data = await f.read()
        
        if len(data) <= IMAGE_CACHE_MAX_BYTES:
            await redis_service.set_bytes(cache_key, data, IMAGE_CACHE_TTL)
            
        mime, _ = mimetypes.guess_type(str(target_path))
        return Response(content=data, media_type=mime or "image/jpeg")
    except Exception as e:
        logger.error(f"Ошибка чтения файла {file_name}: {e}")
        raise ValidationError("Ошибка при чтении файла", field="file_name")