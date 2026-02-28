import logging
import sys
from pathlib import Path


LOG_NAME = "user_api"
LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "app.log"


LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger(LOG_NAME)
logger.setLevel(logging.DEBUG)
logger.propagate = False

if not logger.handlers:
    # Форматтер
    log_format = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(module)s:%(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Консоль: Только INFO и выше
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.INFO) 
    stream_handler.setFormatter(log_format)

    # Файл: Пишем DEBUG
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(log_format)

    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)

if __name__ == "__main__":
    logger.info("Логгер настроен. Можно использовать logger в проекте.")
    logger.debug("Debug-сообщение (увидите только в консоли).")
    logger.info("Info-сообщение (пишется и в файл, и в консоль).")
    logger.warning("Warning-сообщение.")
    logger.error("Error-сообщение.")
    logger.critical("Critical-сообщение.")
