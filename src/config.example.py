TELEGRAM_CONFIG = {
    'token': "ВАШ_ТОКЕН_БОТА_ЗДЕСЬ",  # Пример: "8121544932:AAEBUzCUbQYgRzERRSaz37l7eO6P83pJEhM"
    'chat_id': "ВАШ_CHAT_ID_ЗДЕСЬ"    # Получите через get_chat_id.py
}

# Настройки парсера
PARSER_CONFIG = {
    'base_url': "https://klg.quizplease.ru/schedule",  # URL для парсинга
    'timeout': 30,  # Таймаут HTTP запросов в секундах
    'user_agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# Настройки уведомлений
NOTIFICATION_CONFIG = {
    'send_telegram': True,  # Отправлять уведомления в Telegram
    'send_full_details': True,  # Отправлять полную информацию по каждой игре
    'only_new_games': False,  # Отправлять только уведомления о новых играх
    'check_interval': 1800  # Интервал проверки в секундах (1800 = 30 минут)
}

# Настройки логирования
LOGGING_CONFIG = {
    'level': 'INFO',  # Уровень логирования: DEBUG, INFO, WARNING, ERROR
    'log_to_file': True,  # Логировать в файл
    'log_to_console': True  # Логировать в консоль
}

# Настройки фильтрации игр
FILTER_CONFIG = {
    'only_classic_games': True,  # Парсить только классические игры
    'only_available': False,  # Показывать только доступные игры
    'exclude_reserve': False,  # Исключить игры в резерве
    'future_days': 90  # Количество дней вперед для парсинга
}

# Прокси настройки (опционально)
PROXY_CONFIG = {
    'enabled': False,
    'http': "http://user:pass@proxy:port",
    'https': "https://user:pass@proxy:port"
}