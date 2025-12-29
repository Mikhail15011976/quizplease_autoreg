"""
Модуль для отправки уведомлений в Telegram
"""

import logging
import asyncio
from datetime import datetime
from typing import List

logger = logging.getLogger(__name__)

try:
    from telegram import Bot
    from telegram.error import TelegramError
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    logger.warning("Библиотека python-telegram-bot не установлена. Установите: pip install python-telegram-bot")


class TelegramBot:
    """Класс для работы с Telegram Bot API"""

    def __init__(self, bot_token: str, chat_id: str):
        if not TELEGRAM_AVAILABLE:
            logger.error("Библиотека python-telegram-bot не установлена")
            self.is_available = False
            return
            
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.bot = Bot(token=bot_token)
        self.is_available = self._test_connection()

    def _test_connection(self) -> bool:
        """Проверка подключения к боту."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def check():
                return await self.bot.get_me()
            
            bot_info = loop.run_until_complete(check())
            loop.close()
            
            logger.info(f"✓ Бот @{bot_info.username} успешно подключен")
            return True
        except Exception as e:
            logger.error(f"Ошибка подключения к боту: {str(e)}")
            return False

    def send_message(self, text: str, parse_mode: str = 'Markdown') -> bool:
        """Отправка сообщения в Telegram"""
        if not self.is_available:
            logger.warning("Бот недоступен, пропускаем отправку сообщения")
            return False

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def send():
                await self.bot.send_message(
                    chat_id=self.chat_id,
                    text=text,
                    parse_mode=parse_mode,
                    disable_web_page_preview=False
                )
            
            loop.run_until_complete(send())
            loop.close()
            
            logger.info("✓ Сообщение отправлено в Telegram")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения: {str(e)}")
            return False

    def send_game_notification(self, game) -> bool:
        """Отправка уведомления об игре"""
        try:
            message = game.to_telegram_message()
            return self.send_message(message)
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления: {str(e)}")
            return False

    def send_summary(self, games: List) -> bool:
        """Отправка сводки по играм"""
        if not games:
            logger.info("Нет игр для отправки сводки")
            return True

        total_games = len(games)
        active_games = [g for g in games if g.availability_type == 'active']
        reserve_games = [g for g in games if g.availability_type == 'reserve']

        summary_lines = [
            f"📊 *СВОДКА ПО ИГРАМ КВИЗ, ПЛИЗ! KLG*",
            f"🕐 *Обновлено:* {games[0].extracted_at}",
            "",
            f"📋 *Всего игр:* {total_games}",
            f"✅ *Доступно для записи:* {len(active_games)}",
            f"⚠️  *Запись в резерв:* {len(reserve_games)}",
        ]

        if reserve_games:
            summary_lines.extend(["", "*Ближайшие игры:*"])
            for i, game in enumerate(reserve_games[:3], 1):
                info = f"{i}. {game.date} {game.time} - {game.game_number}"
                if game.place and game.place != 'Не указано':
                    info += f" ({game.place})"
                summary_lines.append(info)

        summary_lines.extend([
            "",
            f"[📅 Открыть полное расписание](https://klg.quizplease.ru/schedule)"
        ])

        summary = "\n".join(summary_lines)
        return self.send_message(summary)

    def send_test_message(self) -> bool:
        """Отправка тестового сообщения"""
        test_message = (
            "🤖 *Тестовое сообщение от QuizPlease Parser*\n"
            f"🕐 Время отправки: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            "✅ Бот успешно подключен и готов к работе!\n"
            "📊 Ожидайте уведомлений о новых играх."
        )
        
        logger.info("Отправка тестового сообщения...")
        return self.send_message(test_message)


# Алиас для совместимости
TelegramNotifier = TelegramBot