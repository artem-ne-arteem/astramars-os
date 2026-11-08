"""Аккаунт Ygolek VPN: вход через Telegram-бота и получение подписки с сайта ygolek-vpn.online.

Протокол (site/lib/app-auth.ts в репозитории Ygolek):
  POST /api/app/login/start {device}        → {code, secret, botUrl, expiresIn}
  POST /api/app/login/poll  {code, secret}  → {status: pending|ok|denied|expired|invalid, token?}
  GET  /api/app/me   (Authorization: Bearer) → {username, subscription, key, deviceLimit, renewUrl}
  POST /api/app/logout (Authorization: Bearer)
"""

import json
import os
import socket
import urllib.error
import urllib.request

from . import __version__, singbox

API_BASE = os.environ.get("YGOLEK_API", "https://ygolek-vpn.online").rstrip("/")
LOGIN_TIMEOUT = 10 * 60


class AccountError(Exception):
    pass


class Unauthorized(AccountError):
    pass


def _open(req, timeout):
    """Запрос напрямую, а если сайт недоступен — через локальный прокси VPN, если он запущен."""
    try:
        return urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError:
        raise
    except (urllib.error.URLError, OSError):
        try:
            with socket.create_connection(("127.0.0.1", singbox.MIXED_PORT), timeout=0.3):
                pass
        except OSError:
            raise
        proxy = f"http://127.0.0.1:{singbox.MIXED_PORT}"
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
        return opener.open(req, timeout=timeout)


def api(method: str, path: str, body=None, token: str = "", timeout: float = 15):
    headers = {"Accept": "application/json", "User-Agent": f"YgolekVPN/{__version__} (Linux; AstraMars OS)"}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(API_BASE + path, data=data, headers=headers, method=method)
    try:
        with _open(req, timeout) as r:
            return json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise Unauthorized("вход больше не действует") from e
        try:
            return json.loads(e.read().decode() or "{}")
        except ValueError:
            raise AccountError(f"сайт ответил ошибкой {e.code}") from e
    except (urllib.error.URLError, OSError) as e:
        raise AccountError("нет связи с сайтом Ygolek") from e
    except ValueError as e:
        raise AccountError("сайт вернул непонятный ответ") from e


def device_name() -> str:
    host = socket.gethostname() or "Linux"
    return f"{host} · AstraMars OS"[:64]


def start_login() -> dict:
    data = api("POST", "/api/app/login/start", {"device": device_name()})
    if not data.get("code") or not data.get("secret") or not data.get("botUrl"):
        raise AccountError("сайт не выдал ссылку для входа")
    return data


def poll_login(code: str, secret: str) -> dict:
    return api("POST", "/api/app/login/poll", {"code": code, "secret": secret})


def me(token: str) -> dict:
    return api("GET", "/api/app/me", token=token)


def logout(token: str) -> None:
    try:
        api("POST", "/api/app/logout", token=token, timeout=8)
    except AccountError:
        pass


def make_qr(url: str, path: str) -> bool:
    """SVG с QR-кодом ссылки на бота. False, если модуля qrcode нет."""
    try:
        import qrcode
        import qrcode.image.svg
    except ImportError:
        return False
    img = qrcode.make(url, image_factory=qrcode.image.svg.SvgPathFillImage, box_size=12, border=2)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path)
    return True
