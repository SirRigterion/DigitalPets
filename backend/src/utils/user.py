
from fastapi import UploadFile

from src.core.exceptions import ValidationError


async def _validate_file_upload(file: UploadFile, max_size_mb: int = 5) -> None:
    """Валидирует загружаемый файл."""
    if not file.content_type:
        raise ValidationError("Не удалось определить тип файла", field="photo")
    
    # Проверяем тип файла
    allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    if file.content_type not in allowed_types:
        raise ValidationError(
            f"Неподдерживаемый тип файла. Разрешены: {', '.join(allowed_types)}", 
            field="photo"
        )
    
    # Проверяем размер файла (если доступен)
    if hasattr(file, 'size') and file.size:
        max_size_bytes = max_size_mb * 1024 * 1024
        if file.size > max_size_bytes:
            raise ValidationError(
                f"Размер файла превышает {max_size_mb}MB", 
                field="photo"
            )

