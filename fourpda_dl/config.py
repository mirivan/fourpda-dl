import json
import os
import sys

from pathlib import Path
from typing import Dict


def is_windows() -> bool:
    return os.name == "nt" or sys.platform.startswith("win")

def get_default_config_dir() -> Path:
    """
    Возвращает путь к конфиг-директории 4pda-dl
    с корректной поддержкой Windows, Linux, macOS.
    """
    if is_windows():
        if os.getenv("LOCALAPPDATA"):
            base = Path(os.getenv("LOCALAPPDATA")) / "fourpda-dl"
        elif os.getenv("USERPROFILE"):
            base = Path(os.getenv("USERPROFILE")) / "Local Settings" / "fourpda-dl"
        else:
            base = Path.home() / "fourpda-dl"
    else:
        base = Path.home() / ".fourpda-dl"

        if not base.is_dir():
            if "XDG_DATA_HOME" in os.environ:
                base = Path(os.environ["XDG_DATA_HOME"]) / "fourpda-dl"
            else:
                base = Path.home() / ".local" / "share" / "fourpda-dl"

    return base

DEFAULT_CONFIG_DIR = get_default_config_dir()
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.json"

def load_config() -> dict:
    """
    Загружает конфигурацию из JSON-файла.
    
    Returns:
        dict: Словарь с данными конфигурации или пустой словарь, если файл не существует
    """
    if DEFAULT_CONFIG_FILE.exists():
        with open(DEFAULT_CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


class Config:
    """
    Класс для управления конфигурацией авторизации на форуме 4PDA.
    
    Обеспечивает работу с данными пользователя и cookies, сохраняемыми в JSON-файл.
    Поддерживает основные операции для управления сессией авторизации.
    
    Attributes:
        _data (dict): Внутреннее хранилище данных конфигурации, содержащее:
            - username (str): Имя пользователя
            - cookies (dict): Словарь с cookies сессии
    
    File:
        config.json: Файл для сохранения и загрузки конфигурации
    """
    def __init__(self):
        data = load_config()

        self._data = {
            "username": data.get("username", ""),
            "cookies": dict(data.get("cookies", {}))
        }

    @property
    def username(self) -> str:
        """
        Возвращает имя пользователя из конфигурации.
        
        Returns:
            str: Имя пользователя или пустая строка если не установлено
        """
        return self._data.get("username", "")

    @username.setter
    def username(self, value: str):
        """
        Устанавливает имя пользователя в конфигурации.
        
        Args:
            value (str): Новое имя пользователя
        """
        self._data["username"] = value

    @property
    def cookies(self) -> Dict[str, str]:
        """
        Возвращает копию словаря cookies из конфигурации.
        
        Returns:
            Dict[str, str]: Копия словаря cookies
        """
        return dict(self._data.get("cookies", {}))

    def get_cookie(self, key: str, default="") -> str:
        """
        Получает значение cookie по указанному ключу.
        
        Args:
            key (str): Ключ cookie
            default (str, optional): Значение по умолчанию если ключ не найден
            
        Returns:
            str: Значение cookie или значение по умолчанию
        """
        return self._data["cookies"].get(key, default)

    def set_cookie(self, key: str, value: str):
        """
        Устанавливает значение cookie по указанному ключу.
        
        Args:
            key (str): Ключ cookie
            value (str): Значение cookie
        """
        self._data["cookies"][key] = value

    def update_from_session(self, session_cookies: Dict[str, str]):
        """
        Обновляет cookies из переданной сессии, сохраняя cf_clearance если он был.
        
        Args:
            session_cookies (Dict[str, str]): Cookies из сессии requests
        """
        cf = self.get_cookie("cf_clearance")

        merged = dict(session_cookies)
        if cf:
            merged["cf_clearance"] = cf

        self._data["cookies"] = merged

    def is_authenticated(self) -> bool:
        """
        Проверяет наличие авторизации в конфигурации.
        
        Returns:
            bool: True если присутствуют username, pass_hash и member_id
        """
        return bool(
            self.username and 
            self.get_cookie("pass_hash") and 
            self.get_cookie("member_id")
        )

    def clear(self):
        """
        Очищает конфигурацию, сохраняя только cf_clearance если он присутствует.
        """
        cf = self.get_cookie("cf_clearance")
        self._data = {"cookies": {"cf_clearance": cf}} if cf else {}
        self.save()

    def save(self):
        """
        Сохраняет конфигурацию в JSON-файл.
        """
        if DEFAULT_CONFIG_DIR.exists():
            with open(DEFAULT_CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=4, ensure_ascii=False)
        else:
            p = Path(DEFAULT_CONFIG_DIR)
            p.mkdir(parents=True, exist_ok=True)
            self.save()

    def to_dict(self):
        """
        Возвращает данные конфигурации в виде словаря.
        
        Returns:
            dict: Копия данных конфигурации в виде словаря
        """
        return json.loads(json.dumps(self._data))