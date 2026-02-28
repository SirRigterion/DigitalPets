from pathlib import Path
from fastapi import APIRouter, Depends, Request, HTTPException
import re

from src.auth import get_current_user
from src.db.models import User
from src.core.config_app import settings
from src.core.config_log import logger
from src.images.utils import _serve_file
from src.utils.decorators import active_user_required, cache, rate_limit, security_headers_check

router = APIRouter()

def validate_file_path(file_path: str, allowed_extensions: set[str]) -> bool:
    """Комплексная проверка безопасности пути и расширения."""
    if not file_path or len(file_path) > 255:
        return False

    if '..' in file_path or file_path.startswith(('/', '\\')):
        return False

    dangerous_patterns = r'[<>:"|?*]'
    if re.search(dangerous_patterns, file_path):
        return False

    ext = Path(file_path).suffix.lower()
    if ext not in allowed_extensions:
        return False

    return True

@router.get("/{file:path}", response_model=dict, status_code=200)
@security_headers_check
@rate_limit(limit=20, period=60)
@active_user_required
@cache(ttl=3600)
async def get_image(
    file: str,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Приватные изображения."""
    
    allowed_ext = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    
    if not validate_file_path(file, allowed_ext):
        logger.warning(f"Security: Invalid private path attempt: {file} by UID {current_user.user_id}")
        raise HTTPException(status_code=400, detail="Неверный путь к файлу")
    
    # если нужно ограничить доступ только к файлам, принадлежащим пользователю, можно раскомментировать следующий код
    # if not file.startswith(f"user-{current_user.user_id}-"):
    #     logger.warning(f"Access Denied: User {current_user.user_id} tried to access {file}")
    #     raise HTTPException(status_code=403, detail="Доступ запрещен")
    
    return await _serve_file(Path(settings.AVATAR_DIR), file)