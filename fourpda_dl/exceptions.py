class CloudflareException(Exception):
    """Исключение, когда Cloudflare блокирует из-за истёкшего/отсутствующего cf_clearance"""
    pass

class FourPDASessionException(Exception):
    """Исключение, когда с сессией происходит что-то не так"""
    pass

class AuthenticationError(Exception):
    """Исключение для ошибок аутентификации"""
    pass

class DirectLinkNotFound(Exception):
    """Не удалось найти прямую ссылку для скачивания."""
    pass