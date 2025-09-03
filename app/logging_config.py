# app/logging_config.py
import logging
import sys
from pathlib import Path

def setup_logging():
    """Настройка логирования для бота"""
    
    # Создаем директорию для логов
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Настройка форматирования
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Настройка корневого логгера
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Очищаем существующие хэндлеры
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Консольный хэндлер
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Файловый хэндлер для всех логов
    file_handler = logging.FileHandler(log_dir / "bot.log", encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # Отдельный файл для задач (reminders, expiry)
    tasks_handler = logging.FileHandler(log_dir / "tasks.log", encoding='utf-8')
    tasks_handler.setLevel(logging.INFO)
    tasks_handler.setFormatter(formatter)
    
    # Логгеры для задач
    tasks_logger = logging.getLogger('app.tasks')
    tasks_logger.addHandler(tasks_handler)
    tasks_logger.setLevel(logging.INFO)
    
    # Логгеры для worker'а
    worker_logger = logging.getLogger('app.tasks.worker')
    worker_logger.addHandler(tasks_handler)
    worker_logger.setLevel(logging.INFO)
    
    # Логгеры для expiry
    expiry_logger = logging.getLogger('app.tasks.expiry')
    expiry_logger.addHandler(tasks_handler)
    expiry_logger.setLevel(logging.INFO)
    
    # Логгеры для reminders
    reminders_logger = logging.getLogger('app.tasks.reminders')
    reminders_logger.addHandler(tasks_handler)
    reminders_logger.setLevel(logging.INFO)
    
    # Логгеры для winback
    winback_logger = logging.getLogger('app.tasks.winback')
    winback_logger.addHandler(tasks_handler)
    winback_logger.setLevel(logging.INFO)
    
    logging.info("Логирование настроено. Логи сохраняются в папку logs/")
