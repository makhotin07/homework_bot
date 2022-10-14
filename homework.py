import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exceptions import CannotSendMessageToTelegram, CannotSendRequestToServer, \
    EndpointNotAvailable, ResponseIsNotDictOrList, ServerNotSentKeyDate, \
    ServerNotSentKeyHomeworks, ServerNotSentListHomeworks, \
    NotDocumentedStatusHomework, ServerSentEmptyListHomeworks, \
    ToSendInTelegram, HomeworkIsNotDictOrList

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

    logging.info(f'Начали отправку сообщение {message}')
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except telegram.TelegramError as telegram_error:
        raise CannotSendMessageToTelegram(
            f'Сообщение в Telegram не отправлено: {telegram_error}')
    else:
        logging.info(
            f'Сообщение в Telegram отправлено: {message}')


def get_api_answer(current_timestamp):
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


def check_response(response):
    """Проверяет корректность ответа API Яндекс практикума."""

    if not isinstance(response, dict):
        if isinstance(response, list):
            response = response[0]
        else:
            raise ResponseIsNotDictOrList(
                'Response не словарь и не список.'
            )

    if response.get('current_date') is None:
        raise ServerNotSentKeyDate('current_date is None')

    current_date = response.get('current_date')
    list_of_homeworks = response.get('homeworks')

    if response['homeworks'] is None:
        raise ServerNotSentKeyHomeworks(
            'В ответе сервера отсутствует ключ homeworks'
        )

    if not isinstance(list_of_homeworks, list):
        raise ServerNotSentListHomeworks(
            'Содержимое ключа homeworks не является списком')

    return list_of_homeworks, current_date


def parse_status(homework):
    """Проверяет статус домашнего задания."""

    if not isinstance(homework, dict):
        if isinstance(homework, list):
            homework = homework[0]
        else:
            raise HomeworkIsNotDictOrList(
                'Response не словарь и не список.'
            )

    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_STATUSES:
        raise NotDocumentedStatusHomework(
            f'недокументированный статус домашней работы: '
            f'{homework_status}'
        )
    return ('Изменился статус проверки работы '
            f'"{homework_name}". {HOMEWORK_STATUSES[homework_status]}')


def check_tokens():
    """Проверяет наличие токена и чат ID телеграмма."""

    list_of_tokens = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    return all(list_of_tokens)


def main():
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
            list_of_homeworks, current_timestamp = check_response(response)

            if not list_of_homeworks:
                raise ServerSentEmptyListHomeworks(
                    'Список homeworks пустой')

            message = parse_status(list_of_homeworks[0])
            if message != last_message:
                send_message(bot, message)
            current_timestamp = current_timestamp

        except ToSendInTelegram as error:
            message = f'Сбой в работе программы: {error}'
            if error != last_error:
                send_message(bot, message)
                last_error = error
            logging.error(error, exc_info=True)
        except Exception as error:
            logging.error(error, exc_info=True)
        else:
            logging.info('Успешно произвели операцию')
        finally:
            logging.info('Цикл закончен')
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
