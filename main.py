import time
import logging
from datetime import datetime
from src.parser import QuizParser
from src.notifier import send_notification

def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/main.log'),
            logging.StreamHandler()
        ]
    )
    
    parser = QuizParser()
    last_check = None
    
    logging.info("Запуск парсера квизов")
    
    try:
        while True:
            current_time = datetime.now().strftime("%H:%M:%S")
            logging.info(f"Проверка доступных игр ({current_time})")
            
            games = parser.check_available_games()
            if games:
                logging.info(f"Найдено {len(games)} подходящих игр")
                
                for game in games:
                    logging.info(f"Попытка регистрации на игру: {game['date']} {game['time']} ({game['status']})")
                    success, result = parser.register_to_game(game)
                    
                    notification_text = (
                        f"Успешная регистрация на игру!\n"
                        f"Дата: {game['date']}\n"
                        f"Время: {game['time']}\n"
                        f"Статус: {game['status']}\n\n"
                        f"{result}"
                    ) if success else (
                        f"Ошибка регистрации на игру\n"
                        f"Дата: {game['date']}\n"
                        f"Время: {game['time']}\n"
                        f"Статус: {game['status']}\n\n"
                        f"Ошибка: {result}"
                    )
                    
                    send_notification(
                        title="Квиз, плиз! Регистрация",
                        message=notification_text,
                        is_success=success
                    )
                    
                    if success:
                        logging.info("Успешная регистрация, завершение работы")
                        return
            
            # Пауза между проверками (5 минут)
            time.sleep(300)
            
    except KeyboardInterrupt:
        logging.info("Работа парсера остановлена пользователем")
    except Exception as e:
        logging.error(f"Критическая ошибка: {str(e)}", exc_info=True)
        send_notification(
            title="Квиз, плиз! Ошибка",
            message=f"Парсер остановлен с ошибкой:\n{str(e)}",
            is_success=False
        )

if __name__ == "__main__":
    main()
