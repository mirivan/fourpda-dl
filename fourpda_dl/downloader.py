import logging
import re
import urllib.parse

from typing import Tuple

from .exceptions import AuthenticationError, DirectLinkNotFound


def parse_url(base_url: str, raw_url: str) -> Tuple[int, str]:
    """
    Разбирает ссылку и возвращает post_id и имя файла.

    Args:
        base_url (str): Базовый домен
        raw_url (str): DL-ссылка

    Returns:
        Tuple[int, str]: post_id (int), file_name (str, URL encoded)
    """
    url = raw_url.strip()
    pattern = base_url.replace('.', r"\.") + r"/forum/dl/post/(\d+)/(.*?)(?:\?.*)?$"
    match = re.search(pattern, url)

    if not match:
        return None, None

    post_id = int(match.group(1))
    file_name = urllib.parse.quote(match.group(2)).replace('%20', '+')

    return post_id, file_name

def get_direct_link(session, config, url):
    """
    Получает прямую ссылку для скачивания файла с форума 4PDA.

    Выполняет двухэтапный процесс получения прямой ссылки:
    1. Прямой запрос к URL с проверкой Location header
    2. Если прямой ссылки нет, парсит HTML для получения attachment ссылки
       и выполняет дополнительный запрос

    Args:
        session: Сессия httpx для выполнения HTTP-запросов
        config: Объект конфигурации с авторизационными данными
        url (str): URL страницы загрузки файла

    Returns:
        str: Прямая ссылка для скачивания файла

    Raises:
        ValueError: Если ссылка для скачивания файла не валидная
        ValueError: Если не удалось найти ссылку на attachment в HTML
        DirectLinkNotFound: Если сервер не вернул прямую ссылку после всех попыток

    Notes:
        - Очищает cookies от служебных параметров (начинающихся с __)
        - Добавляет необходимые cookies modtids и modpids
        - Обрабатывает 404 ошибку как отсутствие доступа к файлу
    """
    post_id, file_name = parse_url(session.base_url, url)

    if not all([post_id, file_name]):
        raise ValueError(
            "Неправильная ссылка для загрузки файла. Ожидается формат: "
            f"{session.base_url}/forum/dl/post/<ID>/<filename>"
        )

    url = f"{session.base_url}/forum/dl/post/{post_id}/{file_name}"

    logging.info("Открываю страницу загрузки...")

    cookies = {k: v for k, v in config.cookies.items() if not k.startswith("__")}
    cookies.update({"modtids": "", "modpids": ""})

    request = session.get(url, cookies=cookies)

    if request.status_code == 404:
        return logging.error("Файл не найден или у вас нет к нему доступа.")

    headers = dict(request.headers)
    headers_keys_lower = [key.lower() for key in headers]
    if "location" in headers_keys_lower:
        location = headers.get("location")
        if location and "4pda.ws" in location:
            logging.info("Финальная ссылка получена.")
            return location

    logging.debug("Сервер не дал ссылку на файл сразу, пробуем загрузку attachment...")

    match = re.search(
        r'<a[^>]*href="(https://4pda\.to/forum/index\.php\?act=attach[^"]*)"[^>]*>Скачать',
        request.text
    )

    if not match:
        raise ValueError("Не удалось получить ссылку на attachment.")

    logging.info("Запрашиваю attachment...")

    request = session.get(match.group(1), cookies=cookies, follow_redirects=False)

    headers = dict(request.headers)
    headers_keys_lower = [key.lower() for key in headers]
    if "location" in headers_keys_lower:
        location = headers.get("location")
        if location and "4pda.ws" in location:
            logging.info("Финальная ссылка получена.")
            return location

    raise DirectLinkNotFound("Сервер не дал ссылку на файл, попробуйте снова.")