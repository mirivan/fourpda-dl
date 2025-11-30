import logging
import sys
from datetime import datetime


class LoggingFormatter(logging.Formatter):
    """
    Кастомный форматтер для логирования с поддержкой цветов и иконок.
    
    Обеспечивает цветное форматирование логов с временными метками и иконками
    для различных уровней логирования.
    
    Attributes:
        COLORS (dict): Соответствие уровней логирования ANSI-цветам
        ICONS (dict): Соответствие уровней логирования иконкам
        RESET (str): ANSI-код сброса форматирования
        show_time (bool): Флаг отображения времени в логах. По умолчанию True
        use_color (bool): Флаг использования цветного форматирования. По умолчанию True
    """

    COLORS = {
        logging.ERROR: "\033[91m",   # красный
        logging.WARNING: "\033[93m", # желтый
        logging.INFO: "\033[96m",    # голубой
        logging.DEBUG: "\033[0;37m", # светло-серый
    }

    ICONS = {
        logging.ERROR: "✘ ",
        logging.WARNING: "! ",
        logging.INFO: "¡ ",
        logging.DEBUG: "🐞",
    }

    RESET = "\033[0m"

    def __init__(self, show_time=True, use_color=True):
        super().__init__("%(message)s")
        self.show_time = show_time
        self.use_color = use_color

    def format(self, record):
        icon = self.ICONS.get(record.levelno, "")
        module = record.module

        # время
        if self.show_time:
            time_str = datetime.now().strftime("%I:%M %p %d.%m.%Y")
            prefix = f"[ {time_str} ] {icon} [ {module} ] ➜"
        else:
            prefix = f"{icon} [ {module} ] ➜"

        msg = super().format(record)

        if self.use_color:
            color = self.COLORS.get(record.levelno, "")
            return f"{color}{prefix}  {msg}{self.RESET}"

        return f"{prefix}  {msg}"


def setup_logger(log_options: str):
    """
    Настраивает систему логирования с указанными опциями.
    
    Параметры настройки задаются строкой символов:
    - 'd' - включить уровень отладки (DEBUG)
    - 't' - показывать время в логах
    - 'c' - использовать цветное форматирование
    
    Args:
        log_options (str): Строка с опциями логирования (например 'dtc')
    
    Notes:
        - По умолчанию используется уровень INFO если не указан 'd'
        - Создает StreamHandler с кастомным форматтером
        - Принудительно перезаписывает существующие настройки логирования
    """

    debug_enabled = "d" in log_options
    show_time = "t" in log_options
    use_color = "c" in log_options

    level = logging.DEBUG if debug_enabled else logging.INFO

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(LoggingFormatter(
        show_time=show_time,
        use_color=use_color
    ))

    logging.basicConfig(
        level=level,
        handlers=[handler],
        force=True,
    )

    logging.debug("Ведение журнала отладки включено.")
