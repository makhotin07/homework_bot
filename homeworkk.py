import logging
import os
import sys
import time
from http import HTTPStatus
import requests
import telegram
from dotenv import load_dotenv
import exception

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s - %(funcName)s - [%(levelname)s] - %(message)s'
)
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger.addHandler(handler)

PRACTICUM_TOKEN = os.getenv('y0_AgAAAABJVJRMAAYckQAAAADPQk31jiSRnbf3S4Kn8Dkhvm8n46Cbru4')
TELEGRAM_TOKEN = os.getenv('5737703870:AAFfo_2qbmjchLB-Z3ZOBfcTNO_WZXcGqu8')
TELEGRAM_CHAT_ID = os.getenv('308335172')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message) -> None:
    """
    Отправляет сообщение в Телеграмм.
    В случае неудачи, вызывает ошибку. Логирует события.
    """
    failed_message = 'Не удалось отправить сообщение'
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(f'Бот отправил сообщение {message}')
    except telegram.error.TelegramError:
        logger.error(failed_message)
        raise telegram.error.TelegramError(failed_message)


def get_api_answer(current_timestamp: int) -> dict:
    """
    Делает запрос к API Практикум.
    Возвращает ответ API преобразованный в тип данных Python.
    Принимает в качестве параметра временную метку.
    """
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}

    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        logger.info(f'Отправлен запрос к API Практикума. '
                    f'Код ответа API: {response.status_code}')
        if response.status_code != HTTPStatus.OK:
            raise response.raise_for_status()

    except requests.exceptions.RequestException as error:
        message = f'Эндпойнт недоступен: {error}'
        logger.error(message)
        raise requests.exceptions.RequestException(message)
    return response.json()


def check_response(response: dict) -> list:
    """
    Проверка корректности ответа API.
    В качестве параметра получает ответ
    API приведенный к типам данных Python (dict). Функция возвращает список
    домашних работ по ключу 'homeworks'.
    """
    if isinstance(response, dict):
        try:
            homework = response['homeworks']
        except KeyError as error:
            message = f'В ответе не обнаружен ключ {error}'
            logger.error(message)
            raise exception.KeyNotFound(message)
        if not isinstance(homework, list):
            raise TypeError('Ответ не содержит список домашних работ')
        message = 'Получены сведения о последней домашней работе'
        logger.info(message) if len(homework) else None
        return homework
    else:
        raise TypeError('В ответе API не обнаружен словарь')

def parse_status(homework: dict) -> str:
    """
    Извлекает из информации о домашней работе статус работы.
    Возвращает строку для отправки сообщения в Телеграмм.
    """
    try:
        homework_name = homework['homework_name']
        homework_status = homework['status']
    except KeyError as error:
        message = f'Ключ {error} не найден в информации о домашней работе'
        logger.error(message)
        raise KeyError(message)

    try:
        verdict = HOMEWORK_STATUSES[homework_status]
        logger.info('Сообщение подготовлено для отправки')
    except KeyError as error:
        message = f'Неизвестный статус домашней работы: {error}'
        logger.error(message)
        raise exception.UnknownStatus(message)

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens() -> bool:
    """
    Проверяет доступность переменных окружения.
    Проверка токенов Практикума и
    Bot API, id чата получателя. Возвращает булево значение.
    """
    checker = all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))
    return checker


if __name__ == '__main__':
    try:
        pass
    except KeyboardInterrupt:
        sys.exit()