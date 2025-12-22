"""
Модуль для отправки уведомлений в Telegram
"""

import logging
import requests
import time
from datetime import datetime
from typing import List, Optional

logger = logging.getLogger(__name__)


class TelegramBot:

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.is_available = self._test_connection()

    def _test_connection(self) -> bool:
        """Проверка подключения к боту."""
        try:
            response = requests.get(f"{self.base_url}/getMe", timeout=10)
            if response.status_code == 200:
                bot_data = response.json()['result']
                bot_name = bot_data.get('username', 'Unknown')
                logger.info(f"✓ Бот @{bot_name} успешно подключен")
                return True
            else:
                logger.error(f"Ошибка подключения к боту: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Ошибка при проверке подключения бота: {str(e)}")
            return False

    def send_game_notification(self, game) -> bool:
        try:
            message = game.to_telegram_message()

            # Отправка сообщения с поддержкой Markdown
            response = requests.post(
                f"{self.base_url}/sendMessage",
                json={
                    'chat_id': self.chat_id,
                    'text': message,
                    'parse_mode': 'Markdown',
                    'disable_web_page_preview': False
                },
                timeout=10
            )

            if response.status_code == 200:
                logger.info(f"✓ Уведомление об игре {game.game_number} отправлено в Telegram")
                return True
            else:
                logger.error(f"Ошибка отправки в Telegram: {response.text}")
                return False

        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления: {str(e)}")
            return False

    def send_message(self, text: str, parse_mode: str = 'Markdown') -> bool:
        if not self.is_available:
            logger.warning("Бот недоступен, пропускаем отправку сообщения")
            return False

        try:
            payload = {
                'chat_id': self.chat_id,
                'text': text,
                'parse_mode': parse_mode,
                'disable_web_page_preview': False,
                'disable_notification': False
            }

            response = requests.post(
                f"{self.base_url}/sendMessage",
                json=payload,
                timeout=10
            )

            if response.status_code == 200:
                return True
            else:
                error_data = response.json()
                logger.error(f"Ошибка отправки в Telegram: {error_data.get('description', 'Unknown error')}")
                return False

        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения: {str(e)}")
            return False

    def send_summary(self, games: List) -> bool:
        if not games:
            logger.info("Нет игр для отправки сводки")
            return True

        # Статистика
        total_games = len(games)
        active_games = [g for g in games if g.availability_type == 'active']
        reserve_games = [g for g in games if g.availability_type == 'reserve']
        unknown_games = [g for g in games if g.availability_type == 'unknown']

        # Формируем сообщение
        summary_lines = [
            f"📊 *СВОДКА ПО ИГРАМ КВИЗ, ПЛИЗ! KLG*",
            f"🕐 *Обновлено:* {games[0].extracted_at}",
            "",
            f"📋 *Всего игр:* {total_games}",
            f"✅ *Доступно для записи:* {len(active_games)}",
            f"⚠️  *Запись в резерв:* {len(reserve_games)}",
        ]

        if unknown_games:
            summary_lines.append(f"❓ *Неизвестный статус:* {len(unknown_games)}")

        # Добавляем ближайшие игры в резерве
        if reserve_games:
            summary_lines.extend(["", "*Ближайшие игры:*"])
            for i, game in enumerate(reserve_games[:3], 1):
                info = f"{i}. {game.date} {game.time} - {game.game_number}"
                if game.place and game.place != 'Не указано':
                    info += f" ({game.place})"
                summary_lines.append(info)

        # Добавляем доступные игры
        if active_games:
            summary_lines.extend(["", "*Доступные для записи:*"])
            for i, game in enumerate(active_games[:3], 1):
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

    def send_games_summary(self, games: List, availability_type: str = None) -> bool:
        logger.warning("Метод send_games_summary устарел. Используйте send_summary.")
        return self.send_summary(games)

    def send_detailed_games(self, games: List, availability_type: str = None) -> None:
        if availability_type:
            games_to_send = [g for g in games if g.availability_type == availability_type]
        else:
            games_to_send = games

        logger.info(f"Начинаем отправку {len(games_to_send)} игр в Telegram...")

        successful = 0
        for game in games_to_send:
            if self.send_game_notification(game):
                successful += 1
            # Небольшая пауза между сообщениями, чтобы не превысить лимиты API
            time.sleep(0.5)

        logger.info(f"✓ Отправлено {successful} из {len(games_to_send)} игр")

    def send_test_message(self) -> bool:
        """Отправка тестового сообщения для проверки работы"""
        test_message = (
            "🤖 *Тестовое сообщение от QuizPlease Parser*\n"
            f"🕐 Время отправки: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            "✅ Бот успешно подключен и готов к работе!\n"
            "📊 Ожидайте уведомлений о новых играх."
        )

        logger.info("Отправка тестового сообщения...")
        return self.send_message(test_message)


# Алиас для совместимости со старым кодом
TelegramNotifier = TelegramBot