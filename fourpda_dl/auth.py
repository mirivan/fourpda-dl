import logging
import os
import re
import sys

from .utils import confirmation_request

CAPTCHA_FILENAME = "captcha.gif"

def login(session, config, username: str, password: str, pass_authenticated: bool = True):
    """
    Выполняет авторизацию на форуме 4PDA.
    
    Процесс авторизации включает:
    - Получение данных капчи (время, сигнатура, URL)
    - Загрузку и сохранение изображения капчи
    - Ввод решения капчи пользователем
    - Отправку данных авторизации на сервер
    - Сохранение полученных cookies в конфигурацию
    
    Args:
        session: Сессия httpx для выполнения HTTP-запросов
        config: Объект конфигурации для сохранения авторизационных данных
        username (str): Логин пользователя
        password (str): Пароль пользователя
        pass_authenticated (bool, optional): Пропускать проверку существующей авторизации. 
                                           По умолчанию True.
    
    Returns:
        bool: True если авторизация успешна, False в противном случае
    
    Raises:
        ValueError: При неожиданном коде ответа сервера
        KeyError: При невозможности получить данные капчи
    
    Notes:
        - При существующей авторизации запрашивает подтверждение переавторизации
        - Сохраняет cookies (member_id, pass_hash, cf_clearance)в конфиг
        - Временный файл капчи автоматически удаляется после использования
    """

    if config.is_authenticated() and not pass_authenticated:
        logging.info("В конфиге уже есть авторизованный аккаунт.")
        logging.info(f"Для проверки авторизации используйте: python {sys.argv[0]} verify")
        relogin = confirmation_request("Желаете продолжить авторизацию?", False)
        if not relogin:
            return False

    logging.info("Запуск авторизации...")

    request = session.get(
        f"{session.base_url}/forum/index.php?act=auth",
        follow_redirects=True
    )

    if request.status_code != 200:
        raise ValueError(f"Неожиданный код-ответ сервера: {request.status_code}")

    html = request.text

    def extract(pattern):
        m = re.search(pattern, html)
        return m.group(1) if m else None

    captcha_time = extract(r'name="captcha-time"[^>]*value="([^"]*)"')
    captcha_sig  = extract(r'name="captcha-sig"[^>]*value="([^"]*)"')
    captcha_url  = extract(r'<img[^>]*src="([^"]*)"[^>]*data-captcha="renew-login"')

    if not all([captcha_time, captcha_sig, captcha_url]):
        raise KeyError("Не удалось получить данные капчи, попробуйте авторизоваться снова.")

    logging.debug(f"Получили captcha_time: {captcha_time}")
    logging.debug(f"Получили captcha_sig: {captcha_sig}")
    logging.debug(f"Получили URL капчи: {captcha_url}")
    logging.debug(f"Загружаем капчу в файл: {CAPTCHA_FILENAME}")

    captcha = session.get(captcha_url)
    with open(CAPTCHA_FILENAME, "wb") as f:
        f.write(captcha.content)

    logging.info(f"Капча сохранена в файл: {CAPTCHA_FILENAME}")
    captcha = input("Введите решение капчи: ")

    data = {
        "return": session.base_url + '/',
        "login": username,
        "password": password,
        "remember": "1",
        "captcha": captcha,
        "captcha-time": captcha_time,
        "captcha-sig": captcha_sig,
    }

    request = session.post(
        f"{session.base_url}/forum/index.php?act=auth",
        data=data, follow_redirects=False
    )

    os.remove(CAPTCHA_FILENAME)
    logging.debug(f"Файл {CAPTCHA_FILENAME} был удален")

    if "member_id" in request.cookies and "pass_hash" in request.cookies:
        logging.info(f"Авторизован как: {username}")
        session_cookies = dict(request.cookies)
        cf_clearance = session_cookies.get("cf_clearance")
        if cf_clearance:
            logging.info("Был получен cf_clearance токен от форума!")
            session_cookies["cf_clearance"] = cf_clearance
        for k, v in session_cookies.items():
            config.set_cookie(k, v)
        config.username = username
        config.save()
        return True
    else:
        html = request.text
        # TODO: при выводе ошибки снова ждать от пользователя данные (username, password, captcha), потому что в html
        #  появляются новые данные капчи, что даёт возможность попробовать отправить данные авторизации снова.
        #  Трудность заключается в том, что это нужно только для сli.
        error_block = re.search(
            r'<div class="error-content">.*?<ul class="errors-list">(.*?)</ul>', html, re.DOTALL)
        if error_block:
            errors = re.findall(r'<li>([^<]+)</li>', error_block.group(1))
            logging.error(errors[0])
        else:
            logging.error("Ошибка авторизации.")
        config.clear()
        return False


def logout(config):
    """
    Выполняет выход из профиля 4PDA путем очистки конфигурации.
    
    Удаляет все авторизационные данные (cookies, логин) из конфигурационного файла,
    тем самым завершая текущую сессию пользователя.
    
    Args:
        config: Объект конфигурации, содержащий авторизационные данные
    
    Notes:
        - Очищает все cookies и сбрасывает имя пользователя
        - Сохраняет изменения в конфигурационном файле
        - После выполнения функции требуется повторная авторизация для доступа к защищенным ресурсам
    """
    logging.info("Выходим из профиля 4PDA...")
    config.clear()
