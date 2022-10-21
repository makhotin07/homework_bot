import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exceptions import (CannotSendMessageToTelegram, CannotSendRequestToServer,
                        EndpointNotAvailable, IsNotDict,
                        NotDocumentedStatusHomework,
                        NotSendInTelegram, ServerNotSentKey,
                        ServerNotSentListHomeworks)

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
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)


def send_message(bot: telegram.Bot, message: str) -> None:
    """Отправляет сообщение в телеграм."""
    logging.info(f'Начали отправку сообщение {message}')
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except telegram.TelegramError as telegram_error:
        raise CannotSendMessageToTelegram(
            f'Сообщение в Telegram не отправлено: {telegram_error}')
    else:
        logging.info(
            f'Сообщение в Telegram отправлено: {message}')


def get_api_answer(current_timestamp: int) -> dict:
    """Запрос к Яндексу, получает ответ от апи."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}

    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)

    except Exception as e:
        raise CannotSendRequestToServer(
            f'Не удалось отправить запрос {ENDPOINT}. Ошибка {e}')
    else:
        if response.status_code != HTTPStatus.OK:
            raise EndpointNotAvailable(
                f'Эндпоинт недоступен {ENDPOINT}. '
                f'Статус код: {response.status_code}'
                f'Причина ответа: {response.reason}'
                f'Текст ответа: {response.text}'
                f'Заголовки: {HEADERS}'
                f'Параметры: {params}')

        return response.json()


def check_response(response: dict) -> list:
    """Проверяет корректность ответа API Яндекс практикума."""
    if not isinstance(response, dict):
        raise IsNotDict(
            'Response не словарь.'
        )

    current_date = response.get('current_date')
    if current_date is None:
        raise ServerNotSentKey('current_date is None')

    list_of_homeworks = response.get('homeworks')

    if list_of_homeworks is None:
        raise ServerNotSentKey(
            'В ответе сервера отсутствует ключ homeworks'
        )

    if not isinstance(list_of_homeworks, list):
        raise ServerNotSentListHomeworks(
            'Содержимое ключа homeworks не является списком')

    return list_of_homeworks


def parse_status(homework: dict) -> str:
    """Проверяет статус домашнего задания."""
    if not isinstance(homework, dict):
        raise IsNotDict(
            'Response не словарь.'
        )

    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_STATUSES:
        raise NotDocumentedStatusHomework(
            'недокументированный статус домашней работы: '
            f'{homework_status}'
        )
    return ('Изменился статус проверки работы '
            f'"{homework_name}". {HOMEWORK_STATUSES[homework_status]}')


def check_tokens() -> bool:
    """Проверяет наличие токена и чат ID телеграмма."""
    tuple_of_tokens = (PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
    return all(tuple_of_tokens)


def main() -> None:
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical('Отсутствует одна или более переменных окружения')
        sys.exit(
            'Отсутствует одна или более переменных окружения.'
            'Программа будет остановлена')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    last_message = ''
    last_error = ''
    while True:
        try:
            response = get_api_answer(current_timestamp)
            list_of_homeworks = check_response(response)

            if not list_of_homeworks:
                message = 'Список homeworks пустой'
            else:
                message = parse_status(list_of_homeworks[0])
            if message != last_message:
                send_message(bot, message)
                last_message = message
            else:
                logging.info(
                    'Сообщение не изменилось'
                    ' и не было отправлено в телеграм.')
            current_timestamp = response.get('current_date')
        except NotSendInTelegram as error:
            logging.error(error, exc_info=error)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if error != last_error:
                send_message(bot, message)
                last_error = error
            logging.error(error, exc_info=error)
        finally:
            logging.info('Цикл закончен')
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
