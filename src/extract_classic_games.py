import os
import json
import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/extract_games.log'),
        logging.StreamHandler()
    ]
)

def extract_classic_games():
    """Извлекает информацию о классических играх с точным названием 'Квиз, плиз! KLG' с сайта и сохраняет в файл"""
    try:
        BASE_URL = "https://klg.quizplease.ru/schedule?QpGameSearch%5Bformat%5D=0"
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

        logging.info(f"Отправляем запрос на {BASE_URL}")
        response = session.get(BASE_URL, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        game_blocks = soup.find_all('div', class_='schedule-column')
        
        classic_games = []
        
        logging.info(f"Найдено {len(game_blocks)} блоков с играми")
        
        for block in game_blocks:
            try:
                title_elem = block.find('div', class_='h2-game-card')
                if not title_elem or title_elem.text.strip() != "Квиз, плиз! KLG":
                    continue
                
                date_block = block.find('div', class_='block-date-with-language-game')
                if not date_block:
                    continue
                
                date_text = date_block.text.strip()
                time_text = ""
                place_text = ""
                address_text = ""
                price_text = ""
                status_text = ""
                
                # Извлечение времени
                info_blocks = block.find_all('div', class_='schedule-info')
                for info in info_blocks:
                    img = info.find('img')
                    if img and 'time-halfwhite.svg' in img.get('src', ''):
                        time_text = info.find('div', class_='techtext').text.strip()
                    elif img and 'pin-halfwhite.svg' in img.get('src', ''):
                        place_elem = info.find('div', class_='schedule-block-info-bar')
                        address_elem = info.find('div', class_='techtext-halfwhite')
                        if place_elem:
                            place_text = place_elem.text.strip()
                        if address_elem:
                            address_text = address_elem.text.strip().replace('Где это?', '').strip()
                    elif 'new-price' in info.get('class', []):
                        price_elem = info.find('span', class_='price')
                        if price_elem:
                            price_text = price_elem.text.strip()

                # Извлечение статуса
                status_elem = block.find('div', class_='game-status')
                if status_elem:
                    status_text = status_elem.text.strip()

                # Извлечение кнопок
                buttons = block.find_all('a', class_='button')
                button_text = buttons[0].text.strip() if buttons else "Нет кнопки"
                
                game_info = {
                    'id': block.get('id', ''),
                    'title': title_elem.text.strip(),
                    'date': date_text,
                    'time': time_text,
                    'place': place_text,
                    'address': address_text,
                    'price': price_text,
                    'status': status_text,
                    'button': button_text,
                    'extracted_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                classic_games.append(game_info)
                logging.info(f"Добавлена игра: {game_info['title']} ({game_info['date']})")
                
            except Exception as e:
                logging.warning(f"Ошибка при обработке блока игры: {str(e)}")
                continue
        
        # Сохранение в файл
        os.makedirs('data', exist_ok=True)
        output_file = 'data/classic_games.json'
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(classic_games, f, ensure_ascii=False, indent=2)
        
        logging.info(f"Сохранено {len(classic_games)} классических игр в {output_file}")
        return classic_games
        
    except Exception as e:
        logging.error(f"Ошибка при извлечении игр: {str(e)}", exc_info=True)
        return []

if __name__ == "__main__":
    extract_classic_games()
