import argparse
import logging

from .auth import login, logout
from .config import DEFAULT_CONFIG_FILE, Config
from .downloader import get_direct_link
from .logger import setup_logger
from .session import FourPDASession, validate_authentication


def main():
    # TODO: русифицировать
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--log",
        type=str,
        default="",
        help='Флаги логгера: d=debug, t=время, c=цвет (пример: "dtc")'
    )

    subparsers = parser.add_subparsers(dest="cmd", required=True)

    p_login = subparsers.add_parser("login", help="Авторизация")
    p_login.add_argument("username")
    p_login.add_argument("password")

    p_u = subparsers.add_parser("u", help="Получить прямую ссылку")
    p_u.add_argument("url")

    subparsers.add_parser("verify", help="Проверить актуальность авторизации")

    subparsers.add_parser("logout", help="Выход")

    args = parser.parse_args()

    setup_logger(args.log)

    logging.debug("Журналирование инициализировано с параметрами: %s", args.log)

    config = Config()

    logging.debug("Загружен конфиг файл: %s", DEFAULT_CONFIG_FILE)

    session = FourPDASession(config)

    if args.cmd == "login":
        login(session, config, args.username, args.password, False)
    elif args.cmd == "logout":
        logout(config)
    elif args.cmd == "u":
        print(get_direct_link(session, config, args.url))
    elif args.cmd == "verify":
        validate_authentication(config, session)