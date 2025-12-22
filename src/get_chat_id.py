"""
Утилита для получения Chat ID из Telegram
"""

import requests
import os
import sys
import importlib.util


def load_token_from_config():
    """Загрузка токена из config.py с правильным импортом"""
    try:
        # Определяем абсолютный путь к config.py
        current_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(current_dir, 'config.py')

        # Проверяем существование файла
        if not os.path.exists(config_path):
            print("❌ Файл config.py не найден в папке src/")
            print(f"   Ожидаемый путь: {config_path}")
            return None

        # Динамический импорт config.py
        spec = importlib.util.spec_from_file_location("config", config_path)
        if spec is None:
            print("❌ Не удалось загрузить spec из config.py")
            return None

        config = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config)

        # Проверяем наличие TELEGRAM_CONFIG
        if not hasattr(config, 'TELEGRAM_CONFIG'):
            print("❌ В config.py не найден TELEGRAM_CONFIG")
            return None

        token = config.TELEGRAM_CONFIG.get('token')

        if not token:
            print("❌ Токен не найден в TELEGRAM_CONFIG")
            return None

        # Проверяем формат токена
        if not isinstance(token, str) or ':' not in token:
            print("❌ Неверный формат токена в config.py")
            print(f"   Токен должен быть строкой вида '123456:ABCdefGHIjklMNOpqrSTUvwx'")
            return None

        print(f"✓ Токен загружен из config.py")
        print(f"   Токен: {token[:10]}...{token[-5:] if len(token) > 15 else ''}")
        return token

    except FileNotFoundError:
        print("❌ Файл config.py не найден")
        return None
    except AttributeError as e:
        print(f"❌ Неверная структура config.py: {e}")
        return None
    except Exception as e:
        print(f"❌ Ошибка при загрузке конфигурации: {e}")
        return None


def check_bot_info(token):
    """Проверка информации о боте и токене"""
    if not token:
        return False

    print("\n" + "=" * 50)
    print("🔍 ПРОВЕРКА ТОКЕНА И БОТА")
    print("=" * 50)

    try:
        url = f"https://api.telegram.org/bot{token}/getMe"
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()
            bot_info = data['result']

            print(f"✅ Токен валидный!")
            print(f"\n🤖 ИНФОРМАЦИЯ О БОТЕ:")
            print("-" * 30)
            print(f"ID: {bot_info.get('id', 'Неизвестно')}")
            print(f"Имя: {bot_info.get('first_name', 'Неизвестно')}")
            print(f"Username: @{bot_info.get('username', 'Неизвестно')}")
            print(f"Может читать групповые сообщения: {'Да' if bot_info.get('can_read_all_group_messages') else 'Нет'}")
            print(f"Поддерживает инлайн-режим: {'Да' if bot_info.get('supports_inline_queries') else 'Нет'}")
            print(f"Является ботом: {'Да' if bot_info.get('is_bot') else 'Нет'}")
            print("-" * 30)
            return True

        elif response.status_code == 401:
            print("❌ Токен недействителен или отозван")
            print("   Проверьте токен в @BotFather")
            return False
        elif response.status_code == 404:
            print("❌ Бот не найден")
            print("   Возможно, бот был удален")
            return False
        else:
            print(f"❌ Ошибка API: {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Описание: {error_data.get('description', 'Неизвестная ошибка')}")
            except:
                print(f"   Ответ сервера: {response.text[:100]}")
            return False

    except requests.exceptions.Timeout:
        print("❌ Таймаут соединения с Telegram API")
        print("   Проверьте интернет-соединение")
        return False
    except requests.exceptions.ConnectionError:
        print("❌ Ошибка соединения")
        print("   Не удалось подключиться к Telegram API")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return False


def get_updates(token, limit=10):
    if not token:
        print("❌ Токен не указан")
        return

    print("\n" + "=" * 50)
    print("📡 ПОЛУЧЕНИЕ ОБНОВЛЕНИЙ ОТ БОТА")
    print("=" * 50)

    try:
        url = f"https://api.telegram.org/bot{token}/getUpdates"
        params = {'limit': limit, 'timeout': 30}

        print(f"Запрашиваем последние {limit} обновлений...")
        print("(Если бот новый, сначала напишите ему сообщение)")

        response = requests.get(url, params=params, timeout=35)

        if response.status_code == 200:
            data = response.json()

            if data.get('ok') and data.get('result'):
                updates = data['result']
                print(f"\n✅ Получено {len(updates)} обновлений")

                # Собираем уникальные чаты
                unique_chats = {}
                for update in updates:
                    if 'message' in update:
                        chat = update['message']['chat']
                        chat_id = chat['id']
                        if chat_id not in unique_chats:
                            unique_chats[chat_id] = {
                                'username': chat.get('username', 'Нет username'),
                                'first_name': chat.get('first_name', ''),
                                'last_name': chat.get('last_name', ''),
                                'type': chat.get('type', 'private')
                            }

                if unique_chats:
                    print("\n" + "=" * 50)
                    print("👤 НАЙДЕННЫЕ CHAT ID:")
                    print("=" * 50)

                    for i, (chat_id, info) in enumerate(unique_chats.items(), 1):
                        print(f"\n{i}. Chat ID: {chat_id}")
                        if info['first_name'] or info['last_name']:
                            name = f"{info['first_name']} {info['last_name']}".strip()
                            print(f"   Имя: {name}")
                        if info['username'] != 'Нет username':
                            print(f"   Username: @{info['username']}")
                        print(f"   Тип чата: {info['type']}")

                    print("\n" + "=" * 50)
                    print("📋 ДЛЯ КОПИРОВАНИЯ:")
                    print("=" * 50)
                    for chat_id in unique_chats.keys():
                        print(f"chat_id: \"{chat_id}\"")

                else:
                    print("\n⚠️  Сообщений от пользователей не найдено")
                    print("\n📝 Что делать:")
                    print("1. Откройте Telegram")
                    print("2. Найдите бота @QuizPleaseKlgBot")
                    print("3. Нажмите /start или напишите любое сообщение")
                    print("4. Подождите 5 секунд")
                    print("5. Запустите этот скрипт снова")

            else:
                print("\n⚠️  В истории бота нет обновлений")
                print("\n📝 Инструкция:")
                print("1. Откройте Telegram")
                print("2. Найдите вашего бота (по username из проверки выше)")
                print("3. Нажмите кнопку 'Start' или напишите /start")
                print("4. Подождите несколько секунд")
                print("5. Запустите скрипт снова")

        else:
            print(f"❌ Ошибка при получении обновлений: {response.status_code}")

    except requests.exceptions.Timeout:
        print("❌ Таймаут при ожидании обновлений")
        print("   Telegram не отправил обновления за 30 секунд")
    except Exception as e:
        print(f"❌ Ошибка: {e}")


def manual_token_input():
    """Ручной ввод токена"""
    print("\n" + "=" * 50)
    print("🔑 РУЧНОЙ ВВОД ТОКЕНА")
    print("=" * 50)

    print("\n📝 Как получить токен:")
    print("1. Откройте Telegram")
    print("2. Найдите @BotFather")
    print("3. Отправьте /newbot или выберите существующего бота")
    print("4. Скопируйте токен (формат: 1234567890:ABCdefGHIjklMNOpqrSTUvwx)")

    token = input("\nВведите токен бота: ").strip()

    if not token:
        print("❌ Токен не введен")
        return None

    # Проверка формата токена
    if ':' not in token:
        print("❌ Неверный формат токена")
        print("   Токен должен содержать двоеточие: 123456:ABCdef...")
        return None

    parts = token.split(':')
    if len(parts) != 2 or not parts[0].isdigit():
        print("❌ Неверный формат токена")
        print("   Пример правильного токена: 8121544932:AAEBUzCUbQYgRzERRSaz37l7eO6P83pJEhM")
        return None

    print(f"✓ Токен принят: {parts[0]}:{parts[1][:10]}...")
    return token


def create_config_template():
    """Создание шаблона config.py"""
    print("\n" + "=" * 50)
    print("📄 СОЗДАНИЕ ФАЙЛА CONFIG.PY")
    print("=" * 50)

    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(current_dir, 'config.py')

    if os.path.exists(config_path):
        print(f"❌ Файл уже существует: {config_path}")
        return False

    config_content = '''"""
Конфигурация проекта QuizPlease Autoreg
"""

# Telegram конфигурация
TELEGRAM_CONFIG = {
    'token': "ВАШ_ТОКЕН_БОТА_ЗДЕСЬ",  # Пример: "8121544932:AAEBUzCUbQYgRzERRSaz37l7eO6P83pJEhM"
    'chat_id': "ВАШ_CHAT_ID_ЗДЕСЬ"   # Получите через get_chat_id.py
}

# Настройки парсера
PARSER_CONFIG = {
    'base_url': "https://klg.quizplease.ru/schedule"
}
'''

    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(config_content)

        print(f"✓ Создан файл: {config_path}")
        print("\n📝 Что делать дальше:")
        print("1. Откройте созданный файл в редакторе")
        print("2. Вставьте ваш токен вместо ВАШ_ТОКЕН_БОТА_ЗДЕСЬ")
        print("3. Запустите этот скрипт снова для получения Chat ID")
        print("4. Добавьте Chat ID в конфигурацию")
        return True

    except Exception as e:
        print(f"❌ Ошибка при создании файла: {e}")
        return False


def main():
    """Основная функция"""
    print("=" * 60)
    print("🤖 ПОЛУЧЕНИЕ CHAT ID ИЗ TELEGRAM")
    print("=" * 60)

    # 1. Пробуем загрузить токен из config.py
    token = load_token_from_config()

    # 2. Если токена нет, предлагаем варианты
    if not token:
        print("\n📋 ВАРИАНТЫ ДЕЙСТВИЙ:")
        print("1. Создать config.py с шаблоном")
        print("2. Ввести токен вручную")
        print("3. Выйти")

        choice = input("\nВыберите вариант (1-3): ").strip()

        if choice == '1':
            if create_config_template():
                input("\nНажмите Enter для выхода...")
                return
        elif choice == '2':
            token = manual_token_input()
            if not token:
                input("\nНажмите Enter для выхода...")
                return
        else:
            print("\n👋 Выход из программы")
            input("Нажмите Enter для выхода...")
            return

    # 3. Проверяем токен и получаем информацию о боте
    if token and check_bot_info(token):
        # 4. Получаем обновления для нахождения Chat ID
        get_updates(token)
    else:
        print("\n❌ Не удалось проверить бота")
        print("   Проверьте токен и повторите попытку")

    print("\n" + "=" * 60)
    print("ℹ️  ДОПОЛНИТЕЛЬНАЯ ИНФОРМАЦИЯ:")
    print("=" * 60)
    print("📝 Чтобы использовать Chat ID в проекте:")
    print("1. Откройте src/config.py")
    print("2. Найдите TELEGRAM_CONFIG")
    print("3. Вставьте Chat ID в поле 'chat_id'")
    print("4. Сохраните файл")
    print("5. Запустите python src/extract_classic_games.py")

    input("\nНажмите Enter для выхода...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Программа прервана пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback

        traceback.print_exc()