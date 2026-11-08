"""Сеть и VPN: проверка доступа к сайтам, DNS для всей системы, состояние Ygolek VPN и прокси."""

import concurrent.futures as cf
import os
import random
import time
import urllib.error
import urllib.request

from .util import DEV, USER, helper, read, sh, spawn

DNS_PRESETS = [
    {"id": "auto", "name": "Как у провайдера", "hint": "DNS от роутера или провайдера"},
    {"id": "cloudflare", "name": "Cloudflare", "hint": "1.1.1.1 · быстрый, шифрование"},
    {"id": "google", "name": "Google", "hint": "8.8.8.8 · шифрование"},
    {"id": "quad9", "name": "Quad9", "hint": "9.9.9.9 · блокирует вредоносные сайты"},
    {"id": "adguard", "name": "AdGuard", "hint": "94.140.14.14 · без рекламы и трекеров"},
    {"id": "yandex", "name": "Яндекс", "hint": "77.88.8.8 · быстрый в России"},
]
DNS_SIGNS = {"cloudflare": "1.1.1.1", "google": "8.8.8.8", "quad9": "9.9.9.9",
             "adguard": "94.140.14.14", "yandex": "77.88.8.8"}
NM_DNS = "/etc/NetworkManager/conf.d/50-astramars-dns.conf"

SITES = [
    {"id": "youtube", "name": "YouTube", "group": "world", "url": "https://www.youtube.com/generate_204"},
    {"id": "discord", "name": "Discord", "group": "world", "url": "https://discord.com/api/v10/gateway"},
    {"id": "telegram", "name": "Telegram", "group": "world", "url": "https://web.telegram.org/"},
    {"id": "instagram", "name": "Instagram", "group": "world", "url": "https://www.instagram.com/"},
    {"id": "chatgpt", "name": "ChatGPT", "group": "world", "url": "https://chatgpt.com/"},
    {"id": "github", "name": "GitHub", "group": "world", "url": "https://github.com/"},
    {"id": "flathub", "name": "Flathub", "group": "world", "url": "https://dl.flathub.org/repo/summary.idx"},
    {"id": "gosuslugi", "name": "Госуслуги", "group": "ru", "url": "https://www.gosuslugi.ru/"},
    {"id": "sber", "name": "Сбербанк", "group": "ru", "url": "https://online.sberbank.ru/"},
    {"id": "yandex", "name": "Яндекс", "group": "ru", "url": "https://ya.ru/"},
    {"id": "vk", "name": "VK", "group": "ru", "url": "https://vk.com/"},
    {"id": "ozon", "name": "Ozon", "group": "ru", "url": "https://www.ozon.ru/"},
]


def dns_current():
    if DEV:
        return "cloudflare"
    text = read(NM_DNS)
    for preset, sign in DNS_SIGNS.items():
        if sign in text:
            return preset
    return "auto"


def set_dns(preset):
    if preset not in [p["id"] for p in DNS_PRESETS]:
        return False, "неизвестный DNS"
    return helper("dns", preset, timeout=60)


def _probe(site):
    """Открывается ли сайт: любой ответ сервера (даже 403) значит, что связь есть."""
    if DEV:
        time.sleep(random.uniform(0.1, 0.8))
        bad = site["id"] in ("instagram", "chatgpt")
        return {**site, "ok": not bad, "ms": 0 if bad else random.randint(30, 220),
                "note": "не открывается" if bad else ""}
    req = urllib.request.Request(site["url"], method="GET", headers={"User-Agent": "Mozilla/5.0 AstraMars"})
    start = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            r.read(256)
        ok, note = True, ""
    except urllib.error.HTTPError as e:
        ok, note = e.code < 500 or e.code in (502, 503), f"ответ {e.code}"
        if e.code == 451:
            ok, note = False, "заблокирован"
    except Exception as e:  # noqa: BLE001 — любая ошибка сети значит «не открывается»
        text = str(getattr(e, "reason", e)).lower()
        ok = False
        note = "нет ответа" if "timed out" in text or "timeout" in text else \
            "имя не найдено" if "name" in text or "resolve" in text else "соединение сброшено" \
            if "reset" in text or "eof" in text else "не открывается"
    return {**site, "ok": ok, "ms": int((time.monotonic() - start) * 1000) if ok else 0, "note": note}


def check_sites(on_result):
    with cf.ThreadPoolExecutor(max_workers=6) as pool:
        for fut in cf.as_completed([pool.submit(_probe, s) for s in SITES]):
            on_result(fut.result())


def vpn_state():
    if DEV:
        return {"vpn": True, "proxy": "", "installed": True}
    code, out = sh(["systemctl", "is-active", f"astramars-vpn@{USER}.service"])
    proxy = ""
    if os.path.exists("/usr/bin/astramars-proxy"):
        c2, o2 = sh(["/usr/bin/astramars-proxy"], timeout=10)
        proxy = o2.splitlines()[0] if c2 == 0 and o2 else ""
    return {"vpn": out.strip() == "active", "proxy": proxy, "installed": os.path.exists("/usr/bin/ygolek-vpn")}


def open_vpn():
    spawn("ygolek-vpn")


def open_network_settings():
    spawn("systemsettings", "kcm_networkmanagement")
