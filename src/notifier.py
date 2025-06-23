import logging
import requests
from datetime import datetime

def send_notification(title, message, is_success=False):
    """Отправляет уведомление через Telegram"""
    try:
        # Проверяем, настроен ли Telegram
        from config import settings
        if not hasattr(settings, 'TELEGRAM_BOT_TOKEN') or not hasattr(settings, 'TELEGRAM_CHAT_ID'):
            logging.warning("Telegram не настроен в config.py")
            return False
        
        bot_token = settings.TELEGRAM_BOT_TOKEN
        chat_id = settings.TELEGRAM_CHAT_ID
        
        # Форматируем сообщение
        status = "✅ УСПЕХ" if is_success else "⚠️ ОШИБКА"
        full_message = f"*{status}*: {title}\n\n{message}"
        
        # Отправляем сообщение
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        params = {
            'chat_id': chat_id,
            'text': full_message,
            'parse_mode': 'Markdown'
        }
        
        response = requests.post(url, params=params)
        response.raise_for_status()
        
        logging.info("Уведомление успешно отправлено в Telegram")
        return True
        
    except Exception as e:
        logging.error(f"Ошибка при отправке уведомления: {str(e)}")
        return False