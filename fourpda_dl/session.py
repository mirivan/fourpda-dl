import logging
import random
import re
import ssl
import sys
from typing import Optional

import httpx
from httpx import Timeout

from .exceptions import FourPDASessionException, CloudflareException, AuthenticationError


def validate_authentication(config, session):
    """
    Проверяет актуальность авторизации пользователя на форуме.
    
    Выполняет запрос к странице авторизации и проверяет наличие идентификатора
    пользователя в ответе. При неактуальной авторизации очищает конфигурацию.
    
    Args:
        config: Объект конфигурации с данными авторизации
        session: Сессия для выполнения HTTP-запросов
    
    Returns:
        bool: True если авторизация актуальна, False в противном случае
    
    Notes:
        - При актуальной авторизации проверяет имя пользователя из конфига и на форуме, если они разные - синхронизуем
        - При неактуальной авторизации полностью очищает конфигурацию
    """
    if not config.is_authenticated():
        raise AuthenticationError("Требуется авторизация.")

    logging.info("Проверяю актуальность авторизации...")

    username = config.username
    member_id = config.get_cookie("member_id")

    cookies = {k: v for k, v in config.cookies.items() if not k.startswith("__")}

    request = session.get(
        f"{session.base_url}/forum/index.php?showuser={member_id}",
        cookies=cookies,
        follow_redirects=True
    )

    html = request.text

    edit_profile = "showuser=8576755&action=edit"
    chpass = "act=auth&action=chpass"

    if request.status_code == 200\
            and edit_profile in html\
            and chpass in html:
        logging.info("Авторизация актуальна.")

        forum_username = re.search(r"<title>(.*) - 4PDA</title>", html, re.DOTALL)

        if forum_username and username != forum_username:
            forum_username = forum_username.group(1)
            logging.debug("Имя пользователя в конфиге и на форуме отличается, синхронизируем имя пользователя с форума...")
            config.username = forum_username
            config.save()

        return True

    logging.error("Авторизация не актуальна.")
    config.clear()
    logging.info("Конфиг очищен.")

    logging.info(f"Используйте: python {sys.argv[0]} login username password")
    return False


class FourPDASession:
    """
    Кастомная сессия HTTP-запросов с эмуляцией мобильного браузера Chrome на Android.
    
    Обеспечивает обход защиты Cloudflare за счет эмуляции реального мобильного устройства,
    включая TLS-настройки, заголовки и параметры соединения.
    
    Attributes:
        config: Объект конфигурации для получения cookies авторизации
        client: HTTPX клиент для выполнения запросов
    """

    def __init__(self, config):
        self.config = config
        self.client: Optional[httpx.Client] = None
        self._create_client()
        self.base_url = "https://4pda.to"

    def _chrome_android_tls_context(self):
        """
        Создает TLS-контекст эмулирующий Chrome на Android.
        
        Returns:
            ssl.SSLContext: Настроенный TLS-контекст с параметрами Chrome 142
        
        Notes:
            - Устанавливает поддержку TLS 1.2-1.3
            - Настраивает шифры соответствующие Chrome Android
            - Включает поддержку ALPN протоколов (h2, http/1.1)
        """
        context = ssl.create_default_context()

        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.maximum_version = ssl.TLSVersion.TLSv1_3

        # https://clienttest.ssllabs.com:8443/ssltest/viewMyClient.html
        context.set_ciphers(
            "TLS_AES_128_GCM_SHA256:"
            "TLS_AES_256_GCM_SHA384:"
            "TLS_CHACHA20_POLY1305_SHA256:"
            "ECDHE-ECDSA-AES128-GCM-SHA256:"
            "ECDHE-RSA-AES128-GCM-SHA256:"
            "ECDHE-ECDSA-AES256-GCM-SHA384:"
            "ECDHE-RSA-AES256-GCM-SHA384:"
            "ECDHE-ECDSA-CHACHA20-POLY1305:"
            "ECDHE-RSA-CHACHA20-POLY1305:"
            "ECDHE-RSA-AES128-SHA:"
            "ECDHE-RSA-AES256-SHA:"
            "AES128-GCM-SHA256:"
            "AES256-GCM-SHA384:"
            "AES128-SHA:"
            "AES256-SHA"
        )

        context.set_alpn_protocols(["h2", "http/1.1"])

        return context

    def _get_headers(self):
        """
        Генерирует заголовки HTTP-запросов эмулирующие Nothing Phone 1.
        
        Returns:
            dict: Словарь с заголовками мобильного Chrome браузера
        
        Notes:
            - Включает Client Hints для эмуляции характеристик устройства
            - Устанавливает параметры viewport, памяти и сетевые характеристики
            - Использует User-Agent Chrome 142
        """
        return {
            "Device-Memory": "8",
            "Sec-CH-Device-Memory": "8",
            "DPR": "2.6187500953674316",
            "Sec-CH-DPR": "2.6187500953674316",
            "Viewport-Width": "980",
            "Sec-CH-Viewport-Width": "980",
            "Sec-CH-Viewport-Height": "1920",
            "RTT": "200",
            "Downlink": "1.55",
            "ECT": "4g",
            "sec-ch-ua": "\"Chromium\";v=\"142\", \"Google Chrome\";v=\"142\", \"Not_A Brand\";v=\"99\"",
            "sec-ch-ua-mobile": "?1",
            "Sec-CH-UA-Full-Version": "\"142.0.7444.171\"",
            "sec-ch-ua-platform": "\"Android\"",
            "Sec-CH-UA-Platform-Version": "\"15.0.0\"",
            "Sec-CH-UA-Model": "\"A063\"",
            "Sec-CH-UA-Full-Version-List": "\"Chromium\";v=\"142.0.7444.171\", \"Google Chrome\";v=\"142.0.7444.171\", \"Not_A Brand\";v=\"99.0.0.0\"",
            "Sec-CH-UA-Form-Factors": "\"Mobile\"",
            "Sec-CH-Prefers-Color-Scheme": "dark",
            "Sec-CH-Prefers-Reduced-Motion": "no-preference",
            "Sec-CH-Prefers-Reduced-Transparency": "no-preference",
            "DNT": "1",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Mobile Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-User": "?1",
            "Sec-Fetch-Dest": "document",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-US,en;q=0.9,ru;q=0.8,ka;q=0.7",
            "Priority": "u=0, i"
        }

    def _maybe_low_entropy_hints(self):
        """
        С вероятностью 70% добавляет низкоэнтропийные Client Hints.
        
        Returns:
            dict: Словарь с дополнительными Client Hints или пустыми значениями
        
        Notes:
            - С вероятностью 70% возвращает архитектуру и разрядность
            - С вероятностью 30% возвращает пустые значения для разнообразия
        """
        if random.random() < 0.7:
            return {
                "Sec-CH-UA-Arch": '"arm64-v8a"',
                "Sec-CH-UA-Bitness": '"64"',
            }
        return {
            "Sec-CH-UA-Arch": ""
        }

    def _create_client(self):
        """
        Создает и настраивает HTTPX клиент с мобильной эмуляцией.
        
        Notes:
            - Использует кастомный TLS-контекст Chrome Android
            - Настраивает таймауты и транспорт
            - Поддерживает HTTP/1.1 и HTTP/2
        """
        logging.debug("Создаем базовую сессию для запросов...")

        ctx = self._chrome_android_tls_context()
        transport = httpx.HTTPTransport(verify=ctx, retries=0)

        self.client = httpx.Client(
            http1=True,
            http2=True,
            timeout=Timeout(20.0),
            transport=transport,
            verify=True
        )

    def _handle_cloudflare_block(self, response: httpx.Response):
        """
        Обрабатывает блокировку запросов со стороны Cloudflare.
        
        Args:
            response (httpx.Response): Ответ сервера для проверки на блокировку
        
        Raises:
            CloudflareException: При обнаружении блокировки Cloudflare
        
        Notes:
            - Проверяет статус 403 и наличие заголовка Cf-Mitigated
            - Предлагает различные решения в зависимости от наличия cf_clearance
        """
        if response.status_code == 403 and response.headers.get("Cf-Mitigated") == "challenge":
            cf_clearance = self.config.get_cookie("cf_clearance")
            if cf_clearance and cf_clearance.strip():
                info = "Cloudflare блокирует вход, надо получить новый cf_clearance или вы можете попробовать убрать его из конфига совсем."
            else:
                info = "Cloudflare блокирует вход, надо получить cf_clearance и указать его в конфиге."

            raise CloudflareException(info)

    def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """
        Выполняет HTTP-запрос.
        
        Args:
            method (str): HTTP-метод (GET, POST, etc.)
            url (str): URL для запроса
            **kwargs: Дополнительные параметры для httpx.Client.request()
        
        Returns:
            httpx.Response: Ответ сервера
        
        Raises:
            HttpxSessionException: Если сессия не создана
            CloudflareException: При блокировке Cloudflare
        
        Notes:
            - Добавляет заголовки эмуляции мобильного устройства
            - Включает низкоэнтропийные Client Hints с вероятностью
            - Обрабатывает cf_clearance из конфигурации
            - Проверяет ответ на блокировку Cloudflare
        """
        if not self.client:
            raise FourPDASessionException("Сессия не создана")

        base_headers = self._get_headers()
        low_entropy_hints = self._maybe_low_entropy_hints()

        headers = {}
        keys = list(base_headers.keys())

        for i, key in enumerate(keys):
            headers[key] = base_headers[key]

            if (key == "Sec-CH-UA-Full-Version" and
                "Sec-CH-UA-Arch" in low_entropy_hints and
                i + 1 < len(keys) and
                keys[i + 1] == "sec-ch-ua-platform"):
                headers["Sec-CH-UA-Arch"] = low_entropy_hints["Sec-CH-UA-Arch"]

            if (key == "Sec-CH-UA-Model" and
                "Sec-CH-UA-Bitness" in low_entropy_hints and
                low_entropy_hints["Sec-CH-UA-Bitness"] and
                headers.get("Sec-CH-UA-Arch") and
                i + 1 < len(keys) and
                keys[i + 1] in ["Sec-CH-UA-WoW64", "Sec-CH-UA-Full-Version-List"]):
                headers["Sec-CH-UA-Bitness"] = low_entropy_hints["Sec-CH-UA-Bitness"]

        kwargs["headers"] = headers

        cf_clearance = self.config.get_cookie("cf_clearance")
        if cf_clearance:
            logging.debug("Используем cf_clearance, указанный в конфиге!")
            cookies = kwargs.get("cookies")
            if cookies:
                cookies["cf_clearance"] = cf_clearance

        response = self.client.request(method, url, **kwargs)
        self._handle_cloudflare_block(response)
        return response

    def get(self, url: str, **kwargs) -> httpx.Response:
        """
        Выполняет GET-запрос.
        
        Args:
            url (str): URL для запроса
            **kwargs: Дополнительные параметры для httpx.Client.request()
        
        Returns:
            httpx.Response: Ответ сервера
        """
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs) -> httpx.Response:
        """
        Выполняет POST-запрос.
        
        Args:
            url (str): URL для запроса
            **kwargs: Дополнительные параметры для httpx.Client.request()
        
        Returns:
            httpx.Response: Ответ сервера
        """
        return self.request("POST", url, **kwargs)

    def close(self):
        """
        Закрывает HTTP-сессию и освобождает ресурсы.
        
        Raises:
            ValueError: Если сессия уже была закрыта
        """
        if not self.client:
            raise ValueError("Сессия уже была закрыта.")
        self.client.close()
        self.client = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return False