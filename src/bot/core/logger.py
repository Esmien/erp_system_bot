import logging
import sys

from loguru import logger

from bot.core.config import settings


class InterceptHandler(logging.Handler):
    """
    Класс для перехвата логов из стандартной библиотеки logging и перенаправления их в loguru.
    """

    def emit(self, record):
        # Получаем соответствующий уровень loguru
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Находим фрейм, откуда было вызвано сообщение, чтобы loguru правильно показал строку кода
        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup_logger():
    """
    Настраивает loguru: вывод в консоль и в файл с ротацией.
    """
    # Удаляем стандартный обработчик
    logger.remove()

    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    # Чтобы uvicorn не двоил логи в консоли, подменяем его логгеры
    for logger_name in ("uvicorn.asgi", "uvicorn.access", "uvicorn", "aiogram"):
        logging_logger = logging.getLogger(logger_name)
        logging_logger.handlers = [InterceptHandler()]
        logging_logger.propagate = False

    # Настройка вывода в консоль
    logger.add(
        sys.stdout,
        level=settings.logger.LOG_LEVEL,
        colorize=True,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>",
    )

    # Вывод в файл с ротацией
    # rotation="10 MB" - создаст новый файл, когда старый весит 10МБ
    # compression="zip" - старые логи будут сжиматься
    # retention="10 days" - храним логи за последние 10 дней
    logger.add(
        "logs/app.log",
        rotation="10 MB",
        retention="10 days",
        compression="zip",
        level=settings.logger.LOG_LEVEL,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        serialize=settings.logger.LOG_SERIALIZE,
    )

    logger.info("Логгер успешно инициализирован.")
