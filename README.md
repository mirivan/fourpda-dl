# fourpda-dl

Утилита и библиотека для получения прямых ссылок на загрузку файлов с 4PDA.
Поддерживает работу из CLI и использование как Python-модуля.

**TODO**
- Проверка ссылок на валидность
- Поддержка ссылок с пробелами
- Интерактивная загрузка файлов по полученной ссылке

**Особенности**
- Авторизация и сохранение cookie
- Проверка сессии
- Генерация прямых ссылок для скачивания
- Логирование и удобный CLI
- Простая интеграция в скрипты

---

## Установка

```bash
git clone https://github.com/mirivan/fourpda-dl
cd fourpda-dl
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

### Рекомендуется 
- Использование uv вместо pip

---

## Быстрый старт (CLI)

```bash
# Авторизация аккаунта
python main.py login <username> <password>

# Проверить валидность cookie / статуса авторизации
python main.py verify

# Получить прямую ссылку (u = url)
python main.py u "https://4pda.to/forum/dl/post/33872457/Platform-tools%20r36.0.1-linux.zip"

# Выйти из аккаунта
python main.py logout
```

Примеры:

```bash
python main.py login Alice 'VStraneChudes123'
python main.py u "https://4pda.to/forum/dl/post/33872457/Platform-tools%20r36.0.1-linux.zip"
```

---

## Использование как библиотеки

```python
from fourpda_dl.config import Config
from fourpda_dl.session import FourPDASession, validate_authentication
from fourpda_dl.auth import login, logout
from fourpda_dl.downloader import get_direct_link

cfg = Config() # читает/создает конфиг
session = FourPDASession(cfg)

# логин (сохранить cookie)
login(session, cfg, "username", "password")

# получить прямую ссылку
direct_link = get_direct_link(session, cfg, "https://4pda.to/...")
print(direct_link)

# проверить авторизацию
validate_authentication()

# выйти
logout(cfg)
```

---

## Конфигурация

По умолчанию конфигурация хранится в `config.json`.
Возможные пути:
- Windows: `%LOCALAPPDATA%\fourpda-dl\config.json`
- Linux/macOS: `~/.local/share/fourpda-dl/config.json` или `~/.fourpda-dl/config.json` (если есть XDG)

Структура:
- `username` — имя авторизованного пользователя
- `cookies` — тут хранятся HTTP Cookies, необходимые для работы скрипта:
  - `member_id` — id пользователя
  - `pass_hash` — хэш пароля
  - `cf_clearance` — токен для обхода Cloudflare челленджа, добавляется в конфиг вручную при необходимости (в случае если Cloudflare требует пройти челлендж)
  - прочие cookies

---

## Логирование

- По умолчанию — `INFO`.
- Для отладки используйте флаг `--log dtc`
  - d — debug
  - t — время
  - c — цвет

---