from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import os

def init_webdriver():
    # Путь к исполняемому файлу Яндекс.Браузера
    yandex_browser_path = None
    
    # Попробуем найти Яндекс.Браузер в стандартных расположениях
    possible_paths = [
        os.path.expanduser('~/AppData/Local/Yandex/YandexBrowser/Application/browser.exe'),  # Windows
        '/Applications/Yandex.app/Contents/MacOS/Yandex',  # MacOS
        '/usr/bin/yandex-browser',  # Linux
        '/usr/bin/yandex-browser-beta',
        '/usr/bin/yandex-browser-stable'
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            yandex_browser_path = path
            break
    
    options = Options()
    
    if yandex_browser_path:
        options.binary_location = yandex_browser_path
    else:
        # Если Яндекс.Браузер не найден, используем обычный Chrome
        options.add_argument("--headless")  # Фоновый режим
    
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    # Отключаем сообщения в консоли
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    
    driver = webdriver.Chrome(
        ChromeDriverManager().install(),
        options=options
    )
    
    return driver
