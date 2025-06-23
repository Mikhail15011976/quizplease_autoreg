import time
import logging
import os
from bs4 import BeautifulSoup
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from datetime import datetime

try:
    from config import settings
    from src.notifier import send_notification
    from src.webdriver import init_webdriver
except ImportError:
    from ..config import settings
    from ..src.notifier import send_notification
    from ..src.webdriver import init_webdriver

# Настройка логирования
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    filename='logs/parser.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)

class QuizParser:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.target_dates = ["10 июня", "15 июня"]

    def check_available_games(self):
        """Проверяет доступные классические игры на сайте"""
        try:
            response = self.session.get(settings.BASE_URL, timeout=30)
            response.raise_for_status()
            
            # Сохраняем HTML для отладки
            os.makedirs('data', exist_ok=True)
            with open('data/last_page.html', 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Ищем все блоки с играми
            game_blocks = soup.find_all('div', class_='schedule-column')
            available_games = []
            
            for block in game_blocks:
                try:
                    # Проверяем, что это классическая игра
                    title = block.find('div', class_='h2-game-card').text.strip()
                    if "Квиз, плиз!" not in title:
                        continue
                    
                    # Извлекаем информацию об игре
                    date_block = block.find('div', class_='block-date-with-language-game')
                    if not date_block:
                        continue
                        
                    date_text = date_block.text.strip()
                    
                    # Проверяем нужные даты
                    if not any(target_date in date_text for target_date in self.target_dates):
                        continue
                    
                    time_text = block.find('div', class_='techtext').text.strip()
                    game_buttons = block.find_all('a', class_='button')
                    
                    if not game_buttons:
                        continue
                        
                    # Определяем основной статус игры
                    main_button = game_buttons[0]
                    status = 'available' if 'button-green' in main_button.get('class', []) else 'reserve'
                    
                    game_info = {
                        'id': block.get('id', ''),
                        'title': title,
                        'date': date_text,
                        'time': time_text,
                        'link': main_button.get('href', ''),
                        'status': status
                    }
                    
                    available_games.append(game_info)
                    
                except Exception as e:
                    logging.warning(f"Ошибка парсинга блока игры: {str(e)}")
                    continue
            
            logging.info(f"Найдено доступных игр: {len(available_games)}")
            return available_games
            
        except Exception as e:
            logging.error(f"Ошибка при проверке игр: {str(e)}", exc_info=True)
            return []

    def register_to_game(self, game_info):
        """Регистрирует команду на указанную игру"""
        driver = None
        try:
            driver = init_webdriver()
            full_url = game_info['link'] if game_info['link'].startswith('http') else f"https://klg.quizplease.ru{game_info['link']}"
            driver.get(full_url)
            
            # Ждем загрузки страницы
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.ID, 'qprecord-teamname'))
            )
            
            # Заполнение формы
            self._fill_registration_form(driver)
            
            # Попытка записи
            result, success = self._try_register(driver, game_info['status'])
            
            # Делаем скриншот для отладки
            os.makedirs('screenshots', exist_ok=True)
            screenshot_name = f"screenshots/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{'success' if success else 'fail'}.png"
            driver.save_screenshot(screenshot_name)
            logging.info(f"Скриншот сохранен: {screenshot_name}")
            
            return success, result
            
        except Exception as e:
            error_msg = f"Ошибка при регистрации: {str(e)}"
            logging.error(error_msg, exc_info=True)
            
            if driver:
                # Делаем скриншот при ошибке
                os.makedirs('screenshots', exist_ok=True)
                screenshot_name = f"screenshots/error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                driver.save_screenshot(screenshot_name)
                logging.info(f"Скриншот ошибки сохранен: {screenshot_name}")
            
            return False, error_msg
        finally:
            if driver:
                driver.quit()

    def _fill_registration_form(self, driver):
        """Заполняет форму регистрации"""
        # Основные поля
        fields = {
            'qprecord-teamname': settings.TEAM_NAME,
            'qprecord-captainname': settings.CAPTAIN_NAME,
            'qprecord-email': settings.EMAIL,
            'qprecord-phone-16': settings.PHONE
        }
        
        for field_id, value in fields.items():
            element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, field_id))
            )
            element.clear()
            element.send_keys(value)
        
        # Выбор количества участников
        select = Select(WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'example'))
        ))
        select.select_by_value(str(settings.TEAM_SIZE))
        
        # Чекбоксы
        first_time_checkbox = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'qprecord-first_time'))
        )
        first_time_checkbox.click()

    def _try_register(self, driver, status):
        """Пытается отправить форму регистрации"""
        try:
            # Нажимаем кнопку "Записаться" или "Записаться в резерв"
            button_text = "Записаться" if status == 'available' else "Записаться в резерв"
            
            # Ищем кнопку по тексту
            register_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, f"//button[contains(text(), '{button_text}')]"))
            )
            register_button.click()
            
            # Ждем сообщения об успехе или ошибке
            WebDriverWait(driver, 15).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, ".alert-success, .alert-danger"))
            )
            
            # Проверяем результат
            result_element = driver.find_element(By.CSS_SELECTOR, ".alert-success, .alert-danger")
            result_text = result_element.text.strip()
            
            if "успешн" in result_text.lower():
                logging.info(f"Успешная регистрация: {result_text}")
                return result_text, True
            else:
                logging.warning(f"Ошибка регистрации: {result_text}")
                return result_text, False
                
        except Exception as e:
            error_msg = f"Ошибка при попытке регистрации: {str(e)}"
            logging.error(error_msg)
            return error_msg, False
