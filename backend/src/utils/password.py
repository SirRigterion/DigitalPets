import bcrypt
import hashlib
import hmac

from src.core.config_app import settings


class PasswordManager:
    """Сервис для хеширования и проверки паролей с использованием pepper и bcrypt."""
    
    def __init__(self):
        self.pepper = settings.PASSWORD_PEPPER

    def _prepare_password(self, password: str) -> bytes:
        """Готовит пароль: подмешивает pepper и хеширует через SHA-256."""
        
        keyed_hash = hmac.new(
            self.pepper.encode('utf-8'),
            password.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return keyed_hash.encode('utf-8')

    def hash_password(self, password: str) -> str:
        """Хеширует пароль для сохранения в БД."""
        
        prepared = self._prepare_password(password)
        hashed = bcrypt.hashpw(prepared, bcrypt.gensalt())
        return hashed.decode('utf-8')

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Проверяет пароль на соответствие хешу."""
        
        prepared = self._prepare_password(plain_password)
        return bcrypt.checkpw(prepared, hashed_password.encode('utf-8'))
    
pwd_manager = PasswordManager()