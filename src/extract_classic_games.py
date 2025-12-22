import os
import sys
import json
import logging
import requests
import re
import time
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict, field
import hashlib

# Определение корневой директории проекта
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
SRC_DIR = os.path.join(BASE_DIR, 'src')

# Добавляем src в sys.path для импорта модулей
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

# Создание директорий, если они не существуют
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

# Настройка логирования
LOG_FILE = os.path.join(LOGS_DIR, 'extract_games.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def load_configuration():
    try:
        # Пытаемся импортировать конфигурацию
        import config

        # Проверяем обязательные поля
        required_fields = ['TELEGRAM_CONFIG', 'PARSER_CONFIG']
        for field in required_fields:
            if not hasattr(config, field):
                raise AttributeError(f"В config.py отсутствует обязательный параметр: {field}")

        # Проверяем токен Telegram
        telegram_config = config.TELEGRAM_CONFIG
        if 'token' not in telegram_config or not telegram_config['token']:
            raise ValueError("Токен Telegram не указан в config.py")

        if 'chat_id' not in telegram_config or not telegram_config['chat_id']:
            raise ValueError("Chat ID не указан в config.py")

        # Проверяем базовый URL парсера
        parser_config = config.PARSER_CONFIG
        if 'base_url' not in parser_config or not parser_config['base_url']:
            raise ValueError("Базовый URL не указан в config.py")

        logger.info("✓ Конфигурация успешно загружена из config.py")

        # Маскируем токен для безопасного логирования
        token = telegram_config['token']
        masked_token = f"{token[:10]}...{token[-5:]}" if len(token) > 15 else "***"
        logger.info(f"  Telegram токен: {masked_token}")
        logger.info(f"  Chat ID: {telegram_config['chat_id']}")
        logger.info(f"  Базовый URL: {parser_config['base_url']}")

        return telegram_config, parser_config

    except ImportError:
        logger.error("❌ ФАЙЛ config.py НЕ НАЙДЕН!")
        print_error_and_exit()
    except AttributeError as e:
        logger.error(f"❌ ОШИБКА В СТРУКТУРЕ config.py: {e}")
        print_error_and_exit()
    except ValueError as e:
        logger.error(f"❌ ОШИБКА В ДАННЫХ config.py: {e}")
        print_error_and_exit()
    except Exception as e:
        logger.error(f"❌ НЕОЖИДАННАЯ ОШИБКА ПРИ ЗАГРУЗКЕ КОНФИГУРАЦИИ: {e}")
        print_error_and_exit()


def print_error_and_exit():
    """Вывод инструкции по исправлению ошибки и завершение программы"""
    print("\n" + "=" * 60)
    print("❌ ОШИБКА КОНФИГУРАЦИИ!")
    print("=" * 60)
    print("📋 Для решения проблемы выполните следующие шаги:")
    print()
    print("1. Если файла config.py нет:")
    print("   а) Скопируйте шаблон:")
    print("      cp src/config.example.py src/config.py")
    print("   б) Или создайте вручную в папке src/ файл config.py")
    print()
    print("2. Отредактируйте файл config.py:")
    print("   а) Получите токен бота у @BotFather в Telegram")
    print("   б) Замените ВАШ_ТОКЕН_БОТА_ЗДЕСЬ на ваш токен")
    print("   в) Получите Chat ID:")
    print("      python src/get_chat_id.py")
    print("   г) Замените ВАШ_CHAT_ID_ЗДЕСЬ на ваш Chat ID")
    print()
    print("3. Пример содержимого config.py:")
    print("   TELEGRAM_CONFIG = {")
    print("       'token': '1234567890:ABCdefGHIjklMNOpqrSTUvwx',")
    print("       'chat_id': '987654321'")
    print("   }")
    print("   PARSER_CONFIG = {")
    print("       'base_url': 'https://klg.quizplease.ru/schedule'")
    print("   }")
    print()
    print("4. Убедитесь, что config.py находится в папке src/")
    print("5. Запустите скрипт снова")
    print("=" * 60)
    sys.exit(1)


# Загружаем конфигурацию (программа завершится, если что-то не так)
TELEGRAM_CONFIG, PARSER_CONFIG = load_configuration()


@dataclass
class Game:
    """Класс для хранения информации об игре"""
    id: str
    title: str
    game_number: str
    date: str
    time: str
    place: str
    address: str
    price: str
    status: str
    button_text: str
    availability_type: str  # 'active', 'reserve', 'unknown'
    registration_url: str
    extracted_at: str
    is_available: bool = False
    game_hash: str = field(default="")  # Хэш для отслеживания изменений

    def __post_init__(self):
        """Вычисляем хэш игры после инициализации"""
        if not self.game_hash:
            self.game_hash = self.calculate_hash()

    def calculate_hash(self) -> str:
        """Вычисление хэша игры для отслеживания изменений"""
        data_string = f"{self.title}{self.game_number}{self.date}{self.time}{self.place}{self.status}{self.availability_type}"
        return hashlib.md5(data_string.encode('utf-8')).hexdigest()

    def to_dict(self) -> Dict:
        """Преобразование в словарь"""
        return asdict(self)

    def to_telegram_message(self) -> str:
        # Эмодзи в зависимости от типа доступности
        if self.availability_type == 'reserve':
            emoji = "⚠️"
            availability_text = "ЗАПИСЬ В РЕЗЕРВ"
        elif self.availability_type == 'active':
            emoji = "✅"
            availability_text = "СВОБОДНЫЕ МЕСТА"
        else:
            emoji = "❓"
            availability_text = "СТАТУС НЕИЗВЕСТЕН"

        # Очистка цены от лишних символов
        price_display = self._clean_price(self.price) if self.price else 'Не указана'

        # Определение статуса для отображения
        status_display = self.status if self.status else self.button_text

        message = (
            f"{emoji} *{availability_text}*\n"
            f"🎯 *{self.title} {self.game_number}*\n"
            f"📅 *Дата:* {self.date}\n"
            f"🕒 *Время:* {self.time if self.time else 'Не указано'}\n"
            f"📍 *Место:* {self.place if self.place else 'Не указано'}\n"
            f"🏠 *Адрес:* {self.address if self.address else 'Не указан'}\n"
            f"💰 *Цена:* {price_display}\n"
            f"📊 *Статус:* {status_display}\n"
            f"🕐 *Обновлено:* {self.extracted_at}"
        )

        # Добавляем ссылку, если есть
        if self.registration_url and self.registration_url != "#":
            message += f"\n\n👉 [Ссылка для регистрации]({self.registration_url})"

        return message

    def _clean_price(self, price: str) -> str:
        """Очистка строки цены от лишних символов"""
        if not price:
            return ""
        # Убираем лишние пробелы и переносы строк
        price = re.sub(r'\s+', ' ', price.strip())
        # Убираем повторяющиеся пробелы
        price = re.sub(r'\s{2,}', ' ', price)
        # Заменяем переносы на пробелы
        price = price.replace('\n', ' ').replace('\r', ' ').replace('/', ' / ')
        # Убираем лишние пробелы вокруг слэша
        price = re.sub(r'\s*/\s*', ' / ', price)
        return price


class QuizPleaseParser:
    """Парсер сайта quizplease.ru - ТОЛЬКО классические игры"""

    def __init__(self, base_url: str = None):
        self.base_url = base_url or PARSER_CONFIG['base_url']
        self.session = requests.Session()
        self._setup_session()

    def _setup_session(self) -> None:
        """Настройка HTTP-сессии"""
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })

    def _determine_availability_type(self, button_text: str, status_text: str) -> Tuple[str, bool]:
        """
        Определение типа доступности игры
        """
        button_lower = button_text.lower() if button_text else ""
        status_lower = status_text.lower() if status_text else ""

        # Определение по тексту кнопки
        if 'резерв' in button_lower:
            return 'reserve', False
        elif 'записаться' in button_lower:
            return 'active', True
        elif 'нет мест' in button_lower:
            return 'reserve', False

        # Дополнительная проверка по статусу
        if 'нет мест' in status_lower and 'резерв' in status_lower:
            return 'reserve', False
        elif 'осталось мало мест' in status_lower:
            return 'active', True
        elif 'свободные места' in status_lower:
            return 'active', True
        elif 'записаться' in status_lower:
            return 'active', True

        return 'unknown', False

    def _extract_game_number(self, block) -> str:
        """Извлечение номера игры из блока"""
        try:
            # Поиск номера игры (например, #499, #502)
            game_number_elem = block.find('span', class_='game-number')
            if game_number_elem:
                return game_number_elem.text.strip()

            # Альтернативный поиск: ищем текст с символом #
            game_text = block.get_text()
            if '#' in game_text:
                lines = game_text.split('\n')
                for line in lines:
                    if '#' in line and any(char.isdigit() for char in line):
                        # Извлекаем номер после #
                        parts = line.split('#')
                        if len(parts) > 1:
                            number_part = parts[1].strip()
                            # Берем только цифры
                            number = ''.join(
                                filter(str.isdigit, number_part.split()[0] if number_part.split() else number_part))
                            if number:
                                return f"#{number}"

            return ""
        except Exception as e:
            logger.debug(f"Не удалось извлечь номер игры: {str(e)}")
            return ""

    def _extract_registration_url(self, block) -> str:
        """Извлечение URL для регистрации"""
        try:
            # Поиск всех ссылок с классом 'button'
            buttons = block.find_all('a', class_='button')
            for button in buttons:
                if button.has_attr('href'):
                    href = button['href']
                    if href and href != "#":
                        # Преобразование относительного URL в абсолютный
                        if href.startswith('/'):
                            return f"https://klg.quizplease.ru{href}"
                        return href
            return "#"
        except Exception as e:
            logger.debug(f"Не удалось извлечь URL регистрации: {str(e)}")
            return "#"

    def _extract_time(self, block) -> str:
        """Извлечение времени игры"""
        try:
            # Поиск времени в разных местах
            time_elements = block.find_all('div', class_=lambda x: x and ('time' in x.lower() or 'clock' in x.lower()))

            for elem in time_elements:
                if ':' in elem.text:
                    # Ищем формат HH:MM
                    time_match = re.search(r'(\d{1,2}:\d{2})', elem.text)
                    if time_match:
                        return time_match.group(1)

            # Альтернативный поиск: ищем текст с "в XX:XX"
            block_text = block.get_text()
            time_match = re.search(r'в\s+(\d{1,2}:\d{2})', block_text, re.IGNORECASE)
            if time_match:
                return time_match.group(1)

            # Ищем в schedule-info блоках
            info_blocks = block.find_all('div', class_='schedule-info')
            for info in info_blocks:
                text = info.get_text()
                if ':' in text and any(c.isdigit() for c in text.split(':')[0]):
                    # Извлекаем время
                    lines = text.split('\n')
                    for line in lines:
                        if ':' in line and line.split(':')[0].strip().isdigit():
                            return line.strip()

            return ""
        except Exception as e:
            logger.debug(f"Не удалось извлечь время: {str(e)}")
            return ""

    def _extract_place_and_address(self, block) -> Tuple[str, str]:
        """Извлечение места и адреса игры"""
        place = ""
        address = ""

        try:
            # Ищем информацию о месте в блоке
            info_blocks = block.find_all('div', class_='schedule-info')

            for info in info_blocks:
                text = info.get_text(strip=True)
                if not text:
                    continue

                # Пропускаем время и цену
                if re.search(r'\d{1,2}:\d{2}', text) or re.search(r'\d+\s*₽', text):
                    continue

                # Пропускаем даты
                if any(month in text.lower() for month in ['янв', 'фев', 'мар', 'апр', 'май', 'июн',
                                                           'июл', 'авг', 'сен', 'окт', 'ноя', 'дек']):
                    continue

                # Проверяем на адресные признаки
                if any(word in text.lower() for word in
                       ['ул.', 'улица', 'проспект', 'пр.', 'дом', 'д.', 'г.', 'город']):
                    if not address and len(text) < 150:  # Адрес обычно не слишком длинный
                        address = text
                else:
                    # Предполагаем, что это название места
                    if not place and len(text) < 100:  # Не слишком длинный текст
                        place = text

            return place, address

        except Exception as e:
            logger.debug(f"Не удалось извлечь место и адрес: {str(e)}")
            return "", ""

    def _extract_price(self, block) -> str:
        """Извлечение цены игры"""
        try:
            # Поиск цены в разных местах
            price_elements = block.find_all(['div', 'span'], class_=lambda x: x and (
                    'price' in x.lower() or 'руб' in x.lower() or '₽' in x.lower()))

            for elem in price_elements:
                text = elem.text.strip()
                if '₽' in text or 'руб' in text.lower():
                    return text

            # Поиск цены по тексту
            block_text = block.get_text()
            price_match = re.search(r'(\d+\s*₽\s*/\s*с\s*человека)', block_text)
            if price_match:
                return price_match.group(1)

            return ""
        except Exception as e:
            logger.debug(f"Не удалось извлечь цену: {str(e)}")
            return ""

    def _extract_status(self, block) -> str:
        """Извлечение статуса игры"""
        try:
            # Поиск статуса в разных местах
            status_elements = block.find_all(['div', 'span'], class_=lambda x: x and (
                    'status' in x.lower() or 'мест' in x.lower() or 'запис' in x.lower()))

            for elem in status_elements:
                text = elem.text.strip()
                if text:
                    return text

            # Поиск по тексту в блоке
            block_text = block.get_text()
            status_keywords = ['нет мест', 'осталось мало мест', 'свободные места', 'записаться', 'резерв']
            for keyword in status_keywords:
                if keyword in block_text.lower():
                    # Ищем строку с ключевым словом
                    lines = block_text.split('\n')
                    for line in lines:
                        if keyword in line.lower():
                            return line.strip()

            return ""
        except Exception as e:
            logger.debug(f"Не удалось извлечь статус: {str(e)}")
            return ""

    def _extract_button_text(self, block) -> str:
        """Извлечение текста кнопки"""
        try:
            button_elem = block.find(['a', 'button'],
                                     class_=lambda x: x and ('button' in x.lower() or 'btn' in x.lower()))
            if button_elem:
                return button_elem.text.strip()
            return ""
        except Exception as e:
            logger.debug(f"Не удалось извлечь текст кнопки: {str(e)}")
            return ""

    def _is_classic_or_regular_game(self, block) -> bool:
        """
        Проверка, является ли игра классической ИЛИ обычной игрой "Квиз, плиз! KLG"
        """
        try:
            # Проверяем заголовок
            title_elem = block.find(['div', 'h2', 'h3'],
                                    class_=lambda x: x and ('h2-game-card' in x or 'game-title' in x or 'title' in x))
            if not title_elem:
                return False

            title = title_elem.text.strip() if hasattr(title_elem, 'text') else str(title_elem).strip()

            # Заголовок должен быть именно "Квиз, плиз! KLG"
            if title == "Квиз, плиз! KLG":
                return True

            # Дополнительная проверка: ищем описание классической игры
            block_text = block.get_text()
            classic_keywords = [
                'классическая игра',
                'вопросы на всевозможные темы',
                'любое знание',
                'классическая'
            ]

            # Если в тексте есть слова о классической игре
            for keyword in classic_keywords:
                if keyword in block_text.lower():
                    return True

            return False

        except Exception as e:
            logger.debug(f"Ошибка при проверке игры: {str(e)}")
            return False

    def parse_games(self) -> List[Game]:
        """Парсинг только классических игр с сайта"""
        try:
            logger.info(f"Начинаем парсинг страницы: {self.base_url}")

            response = self.session.get(self.base_url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Ищем все блоки с играми
            game_blocks = []

            # Несколько возможных селекторов для блоков игр
            selectors = [
                'div.schedule-column',
                'div[class*="schedule"][class*="column"]',
                'div.game-card',
                'div.schedule-game'
            ]

            for selector in selectors:
                game_blocks = soup.select(selector)
                if game_blocks:
                    break

            logger.info(f"Найдено {len(game_blocks)} блоков с играми")

            games = []
            classic_count = 0

            for block in game_blocks:
                try:
                    # Проверяем, является ли игра классической ИЛИ обычной игрой "Квиз, плиз! KLG"
                    if not self._is_classic_or_regular_game(block):
                        continue

                    game = self._parse_game_block(block)
                    if game:
                        games.append(game)
                        classic_count += 1

                except Exception as e:
                    logger.error(f"Ошибка при обработке блока: {str(e)}", exc_info=False)
                    continue

            logger.info(f"Успешно обработано {classic_count} классических/обычных игр 'Квиз, плиз! KLG'")
            return games

        except requests.RequestException as e:
            logger.error(f"Ошибка сети при запросе: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Неожиданная ошибка при парсинге: {str(e)}", exc_info=True)
            return []

    def _parse_game_block(self, block) -> Optional[Game]:
        """Парсинг одного блока с игрой"""
        try:
            # Извлечение даты
            date_text = ""
            date_elements = block.find_all(['div', 'span'],
                                           class_=lambda x: x and ('date' in x.lower() or 'day' in x.lower()))
            for elem in date_elements:
                text = elem.text.strip()
                if text and any(month in text.lower() for month in ['янв', 'фев', 'мар', 'апр', 'май', 'июн',
                                                                    'июл', 'авг', 'сен', 'окт', 'ноя', 'дек']):
                    date_text = text
                    break

            if not date_text:
                # Ищем в тексте блока
                block_text = block.get_text()
                date_match = re.search(r'(\d{1,2}\s+[а-яА-Я]+\s*,\s*[а-яА-Я]+)', block_text)
                if date_match:
                    date_text = date_match.group(1)

            # Извлечение времени
            time_text = self._extract_time(block)

            # Извлечение места и адреса
            place_text, address_text = self._extract_place_and_address(block)

            # Извлечение цены
            price_text = self._extract_price(block)

            # Извлечение статуса
            status_text = self._extract_status(block)

            # Извлечение текста кнопки
            button_text = self._extract_button_text(block)

            # Извлечение дополнительной информации
            game_number = self._extract_game_number(block)
            registration_url = self._extract_registration_url(block)

            # Определение типа доступности
            availability_type, is_available = self._determine_availability_type(button_text, status_text)

            # Генерация ID
            game_id = ""
            if game_number:
                game_id = f"game_{game_number.replace('#', '')}"
            else:
                # Создаем ID на основе даты и времени
                id_date = date_text.replace(' ', '_').replace(',', '')
                id_time = time_text.replace(':', '') if time_text else '0000'
                game_id = f"game_{id_date}_{id_time}"

            # Создание объекта игры
            game = Game(
                id=game_id,
                title="Квиз, плиз! KLG",  # Фиксируем название
                game_number=game_number,
                date=date_text,
                time=time_text if time_text else "",
                place=place_text if place_text else "Не указано",
                address=address_text if address_text else "Не указан",
                price=price_text,
                status=status_text,
                button_text=button_text,
                availability_type=availability_type,
                registration_url=registration_url,
                extracted_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                is_available=is_available
            )

            return game

        except Exception as e:
            logger.debug(f"Ошибка в _parse_game_block: {str(e)}")
            return None


class GameStorage:
    """Класс для работы с хранением игр"""

    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or DATA_DIR
        self.history_file = os.path.join(self.output_dir, 'games_history.json')

    def save_games(self, games: List[Game], filename: str = "classic_games.json") -> str:
        """
        Сохранение списка игр в JSON файл
        """
        try:
            output_path = os.path.join(self.output_dir, filename)

            # Преобразование в список словарей
            games_data = [game.to_dict() for game in games]

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(games_data, f, ensure_ascii=False, indent=2)

            # Сохраняем в историю
            self._save_to_history(games)

            logger.info(f"Сохранено {len(games)} игр в {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Ошибка при сохранении игр: {str(e)}")
            return ""

    def _save_to_history(self, games: List[Game]) -> None:
        """Сохранение игр в историю для отслеживания изменений"""
        try:
            history = []
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)

            # Добавляем текущие игры с timestamp
            timestamp = datetime.now().isoformat()
            for game in games:
                game_data = game.to_dict()
                game_data['timestamp'] = timestamp
                game_data['parsed_at'] = game.extracted_at
                history.append(game_data)

            # Ограничиваем размер истории (последние 1000 записей)
            if len(history) > 1000:
                history = history[-1000:]

            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.debug(f"Не удалось сохранить историю: {str(e)}")

    def load_games(self, filename: str = "classic_games.json") -> List[Game]:
        """
        Загрузка игр из JSON файла
        """
        try:
            filepath = os.path.join(self.output_dir, filename)
            if not os.path.exists(filepath):
                logger.info(f"Файл {filepath} не найден, возвращаем пустой список")
                return []

            with open(filepath, 'r', encoding='utf-8') as f:
                games_data = json.load(f)

            games = []
            for game_data in games_data:
                try:
                    game = Game(**game_data)
                    games.append(game)
                except Exception as e:
                    logger.warning(f"Ошибка при создании игры из данных: {str(e)}")
                    continue

            logger.info(f"Загружено {len(games)} игр из {filepath}")
            return games

        except Exception as e:
            logger.error(f"Ошибка при загрузке игр: {str(e)}")
            return []

    def find_new_games(self, current_games: List[Game], previous_games: List[Game]) -> List[Game]:
        """
        Поиск новых игр по сравнению с предыдущей версией
        """
        if not previous_games:
            return current_games

        previous_hashes = {game.game_hash for game in previous_games}
        new_games = [game for game in current_games if game.game_hash not in previous_hashes]

        if new_games:
            logger.info(f"Найдено {len(new_games)} новых игр")
        else:
            logger.info("Новых игр не найдено")

        return new_games

    def find_changed_games(self, current_games: List[Game], previous_games: List[Game]) -> List[Game]:
        """
        Поиск игр с изменившимся статусом
        """
        if not previous_games:
            return []

        previous_dict = {game.game_number: game for game in previous_games}
        changed_games = []

        for current_game in current_games:
            previous_game = previous_dict.get(current_game.game_number)
            if previous_game and previous_game.availability_type != current_game.availability_type:
                changed_games.append(current_game)

        if changed_games:
            logger.info(f"Найдено {len(changed_games)} игр с измененным статусом")
        else:
            logger.info("Игр с измененным статусом не найдено")

        return changed_games


class QuizPleaseMonitor:
    """Основной класс мониторинга игр"""

    def __init__(self, telegram_token: str = None, telegram_chat_id: str = None):
        self.parser = QuizPleaseParser()
        self.storage = GameStorage()
        self.telegram = None

        # Инициализация Telegram бота
        if telegram_token and telegram_chat_id:
            try:
                from src.telegram_notifier import TelegramBot
                self.telegram = TelegramBot(telegram_token, telegram_chat_id)
                if not self.telegram.is_available:
                    logger.warning("Telegram бот недоступен, уведомления отключены")
                    self.telegram = None
                else:
                    # Отправляем тестовое сообщение при инициализации
                    self.telegram.send_test_message()
            except ImportError:
                logger.warning("Модуль telegram_notifier не найден. Установите зависимости.")
                self.telegram = None
            except Exception as e:
                logger.error(f"Ошибка инициализации Telegram бота: {str(e)}")
                self.telegram = None

    def run(self, send_notifications: bool = True) -> List[Game]:
        """
        Запуск полного цикла мониторинга
        """
        try:
            logger.info("=" * 60)
            logger.info("Запуск мониторинга игр 'Квиз, плиз! KLG'")
            logger.info("=" * 60)

            # Загружаем предыдущие игры
            previous_games = self.storage.load_games()

            # Парсим текущие игры
            current_games = self.parser.parse_games()

            if not current_games:
                logger.warning("Не удалось найти игры")
                if self.telegram and send_notifications:
                    self.telegram.send_message("❌ Не удалось получить расписание игр.")
                return []

            # Сохраняем текущие игры
            self.storage.save_games(current_games)

            # Анализируем изменения
            new_games = self.storage.find_new_games(current_games, previous_games)
            changed_games = self.storage.find_changed_games(current_games, previous_games)

            # Отправляем уведомления в Telegram
            if self.telegram and send_notifications:
                self._send_telegram_notifications(current_games, new_games, changed_games)

            # Выводим статистику
            self._print_statistics(current_games, new_games, changed_games)

            return current_games

        except KeyboardInterrupt:
            logger.info("\nМониторинг прерван пользователем")
            return []
        except Exception as e:
            logger.error(f"Критическая ошибка в мониторинге: {str(e)}", exc_info=True)
            return []

    def _send_telegram_notifications(self, current_games: List[Game],
                                     new_games: List[Game],
                                     changed_games: List[Game]) -> None:
        """Отправка уведомлений в Telegram - ПОЛНЫЙ ВЫВОД КАЖДОЙ ИГРЫ"""
        try:
            # 1. Отправляем сводку
            self.telegram.send_summary(current_games)

            # 2. Отправляем ПОЛНЫЙ РАСКЛАД по КАЖДОЙ найденной игре
            if current_games:
                # Заголовок для полного расклада
                if len(current_games) == 1:
                    self.telegram.send_message(f"🎲 *ПОЛНЫЙ РАСКЛАД ПО ИГРЕ:*")
                else:
                    self.telegram.send_message(f"🎲 *ПОЛНЫЙ РАСКЛАД ПО ВСЕМ {len(current_games)} ИГРАМ:*")

                # Отправляем каждую игру полным сообщением
                for i, game in enumerate(current_games, 1):
                    logger.info(f"Отправка игры {i}/{len(current_games)}: {game.game_number}")
                    self.telegram.send_game_notification(game)
                    # Пауза между сообщениями, чтобы не превысить лимиты Telegram API
                    time.sleep(0.5)

            # 3. Отправляем уведомления о новых играх (если есть)
            if new_games:
                if len(new_games) == 1:
                    self.telegram.send_message(f"🎉 *НОВАЯ ИГРА!*")
                else:
                    self.telegram.send_message(f"🎉 *НОВЫЕ ИГРЫ!* ({len(new_games)})")

                # Новые игры уже отправлены в полном раскладе
                for game in new_games:
                    self.telegram.send_game_notification(game)
                    time.sleep(0.3)

            # 4. Отправляем уведомления об изменении статуса (если есть)
            if changed_games:
                if len(changed_games) == 1:
                    self.telegram.send_message(f"🔄 *ИЗМЕНИЛСЯ СТАТУС ИГРЫ!*")
                else:
                    self.telegram.send_message(f"🔄 *ИЗМЕНИЛСЯ СТАТУС ИГР!* ({len(changed_games)})")

                # Игры с измененным статусом уже отправлены в полном раскладе
                for game in changed_games:
                    self.telegram.send_game_notification(game)
                    time.sleep(0.3)

        except Exception as e:
            logger.error(f"Ошибка при отправке уведомлений: {str(e)}")

    def _print_statistics(self, current_games: List[Game],
                          new_games: List[Game],
                          changed_games: List[Game]) -> None:
        """Вывод статистики в консоль и лог"""
        # Фильтрация по типам доступности
        active_games = [g for g in current_games if g.availability_type == 'active']
        reserve_games = [g for g in current_games if g.availability_type == 'reserve']
        unknown_games = [g for g in current_games if g.availability_type == 'unknown']

        # Вывод в лог
        logger.info("\n" + "=" * 50)
        logger.info("СТАТИСТИКА МОНИТОРИНГА:")
        logger.info("=" * 50)
        logger.info(f"Всего игр: {len(current_games)}")
        logger.info(f"✅ Доступные для записи: {len(active_games)}")
        logger.info(f"⚠️  Запись в резерв: {len(reserve_games)}")
        logger.info(f"❓ Неизвестный статус: {len(unknown_games)}")
        logger.info(f"🎉 Новые игры: {len(new_games)}")
        logger.info(f"🔄 Игры с измененным статусом: {len(changed_games)}")

        # Вывод в консоль
        print(f"\n🎯 Найдено {len(current_games)} игр 'Квиз, плиз! KLG'")
        print(f"   ✅ Доступных для записи: {len(active_games)}")
        print(f"   ⚠️  Для записи в резерв: {len(reserve_games)}")

        if new_games:
            print(f"   🎉 Новые игры: {len(new_games)}")
        if changed_games:
            print(f"   🔄 Изменения статуса: {len(changed_games)}")

        # Вывод информации о доступных играх
        if active_games:
            print(f"\n✅ Доступные для записи игры:")
            for i, game in enumerate(active_games[:5], 1):
                print(f"   {i}. {game.date} {game.time} - {game.game_number}")
                if game.place and game.place != 'Не указано':
                    print(f"      Место: {game.place}")

        # Вывод информации о ближайших играх в резерве
        if reserve_games:
            print(f"\n⚠️  Игры для записи в резерв (ближайшие):")
            for i, game in enumerate(reserve_games[:5], 1):
                print(f"   {i}. {game.date} {game.time} - {game.game_number}")
                if game.place and game.place != 'Не указано':
                    print(f"      Место: {game.place}")

        print(f"\n📁 Данные сохранены в: {os.path.join(DATA_DIR, 'classic_games.json')}")
        print(f"📝 Логи сохранены в: {LOG_FILE}")

        logger.info("=" * 50)
        logger.info("Мониторинг завершён успешно!")
        logger.info("=" * 50)


def main():
    """Основная функция запуска мониторинга"""
    try:
        # Используем конфигурацию, загруженную в начале
        monitor = QuizPleaseMonitor(
            telegram_token=TELEGRAM_CONFIG['token'],
            telegram_chat_id=TELEGRAM_CONFIG['chat_id']
        )

        # Запускаем мониторинг
        games = monitor.run(send_notifications=True)

        # Краткая информация о завершении
        if games:
            print(f"\n{'=' * 50}")
            print("✨ Мониторинг завершён успешно!")
            print("✅ Полный расклад по играм отправлен в Telegram")
            print("Следующий запуск: python src/extract_classic_games.py")
            print(f"{'=' * 50}")
            return 0
        else:
            print(f"\n{'=' * 50}")
            print("❌ Мониторинг завершён с ошибками")
            print("Проверьте логи для подробной информации")
            print(f"{'=' * 50}")
            return 1

    except KeyboardInterrupt:
        print(f"\n\n{'=' * 50}")
        print("⏹️  Мониторинг прерван пользователем")
        print(f"{'=' * 50}")
        return 130
    except Exception as e:
        print(f"\n{'=' * 50}")
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        print(f"{'=' * 50}")
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)