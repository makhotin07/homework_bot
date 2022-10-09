import logging
import os
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.DEBUG,
    filename=os.path.join(os.path.dirname(__file__), 'main.log'),
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s'
)


def send_message(bot, message):
    """Отправляет сообщение в телеграм."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.info(
            f'Сообщение в Telegram отправлено: {message}')
    except telegram.TelegramError as telegram_error:
        logging.error(
            f'Сообщение в Telegram не отправлено: {telegram_error}')


def get_api_answer(current_timestamp):
    """запрос к Яндексу, получает ответ от апи."""

    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    r = requests.get(ENDPOINT, headers=HEADERS, params=params)

    if r.status_code != HTTPStatus.OK:
        logging.error(
            f'Эндпоинт недоступен {ENDPOINT}. Статус код: {r.status_code}')
        raise Exception(
            f'Эндпоинт недоступен {ENDPOINT}. Ошибка: {e}')

    else:
        return r.json()


def check_response(response):
    """Проверяет корректность ответа API Яндекс практикума."""
    list_of_homeworks = response['homeworks']

    if list_of_homeworks is None:
        logging.error(
            f'В ответе сервера отсутствует ключ homeworks'
        )
        raise Exception

    if not isinstance(list_of_homeworks, list):
        logging.error('Содержимое ключа homeworks не является списком')
        raise Exception('Некорректный ответ')

    return list_of_homeworks


def parse_status(homework):
    """Проверяет статус домашнего задания."""
    document_status = {'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
                       'reviewing': 'Работа взята на проверку ревьюером.',
                       'rejected': 'Работа проверена: у ревьюера есть замечания.'}
    try:
        homework_name = homework.get('homework_name')
        homework_status = homework.get('status')

        if homework_status not in document_status:
            logging.error(
                f'недокументированный статус домашней работы: {homework_status}'
            )
    except Exception as e:
        logging.error(
            f'Возникла ошибка при парсинге ответа: {e}'
        )
    else:
        return f'Изменился статус проверки работы "{homework_name}". {document_status[homework_status]}'


def check_tokens():
    """Проверяет наличие токена и чат ID телеграмма."""
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        return True
    else:
        return False


def main():
    """Основная логика работы бота."""
    if check_tokens():

        bot = telegram.Bot(token=TELEGRAM_TOKEN)
        current_timestamp = int(time.time())

        while True:
            try:
                response = get_api_answer(current_timestamp)
                list_of_homeworks = check_response(response)
                message = parse_status(list_of_homeworks[0])
                send_message(bot, message)
                current_timestamp = int(time.time())
                time.sleep(RETRY_TIME)
            except Exception as error:
                message = f'Сбой в работе программы: {error}'
                logging.error(error, exc_info=True)
                time.sleep(RETRY_TIME)
            else:
                logging.info('Успешно произвели операцию')

    else:
        logging.critical('Отсутствует одна или более переменных окружения')


if __name__ == '__main__':
    main()
