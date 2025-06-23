from src.parser import QuizParser
from config import settings
import logging
import time

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/test_parser.log'),
            logging.StreamHandler()
        ]
    )

def test_parse_and_reserve():
    setup_logging()
    parser = QuizParser()
    
    logging.info("Начинаем тестовый парсинг...")
    games = parser.check_available_games()
    
    if not games:
        logging.info("Не найдено доступных игр")
        return
    
    logging.info(f"Найдено игр: {len(games)}")
    for game in games:
        logging.info(f"Игра: {game['title']} | Дата: {game['date']} | Время: {game['time']}")
    
    target_dates = ["10 июня, Вторник", "15 июня, Воскресенье"]
    found_games = [g for g in games if any(date in g['date'] for date in target_dates)]
    
    if found_games:
        for game in found_games:
            logging.info(f"\nПытаемся записаться на игру: {game['title']} {game['date']}")
            success, result = parser.register_to_game(game['link'])
            logging.info(f"Результат: {result}")
            
            status = f"Тест | {game['date']} | {game['title']} | {result}"
            parser.save_status(status)
            logging.info(f"Результат сохранен в {settings.LOG_FILE}")
            
            # Пауза между попытками записи
            time.sleep(5)
    else:
        logging.info("\nНет подходящих игр на 10 или 15 июня")

if __name__ == "__main__":
    test_parse_and_reserve()
