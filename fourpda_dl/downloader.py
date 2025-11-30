import logging
import re

from .exceptions import AuthenticationError, DirectLinkNotFound


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
        ValueError: Если не удалось найти ссылку на attachment в HTML
        DirectLinkNotFound: Если сервер не вернул прямую ссылку после всех попыток

    Notes:
        - Очищает cookies от служебных параметров (начинающихся с __)
        - Добавляет необходимые cookies modtids и modpids
        - Обрабатывает 404 ошибку как отсутствие доступа к файлу
    """
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