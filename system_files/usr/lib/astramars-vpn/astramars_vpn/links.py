"""Разбор ссылок на серверы (vless://, vmess://, trojan://, ss://, hy2://, tuic://, anytls://, socks://)
и подписок в исходящие соединения (outbound) sing-box."""

import base64
import binascii
import hashlib
import json
import re
import urllib.parse as up

SCHEMES = ("vless", "vmess", "trojan", "ss", "hysteria2", "hy2", "tuic", "anytls", "socks", "socks5")

PROTOCOL_LABELS = {
    "vless": "VLESS",
    "vmess": "VMess",
    "trojan": "Trojan",
    "shadowsocks": "SS",
    "hysteria2": "Hy2",
    "tuic": "TUIC",
    "anytls": "AnyTLS",
    "socks": "SOCKS",
}

# Протоколы поверх UDP (QUIC): TCP-пинг для них не показателен
UDP_PROTOCOLS = {"hysteria2", "tuic"}


class LinkError(ValueError):
    """Ссылку не удалось разобрать или она не поддерживается."""


# --- вспомогательные функции ---------------------------------------------------

def b64decode(text: str) -> str:
    s = re.sub(r"\s+", "", text).replace("-", "+").replace("_", "/")
    s += "=" * (-len(s) % 4)
    try:
        return base64.b64decode(s, validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError) as e:
        raise LinkError("не удалось расшифровать base64") from e


def _query(query: str) -> dict:
    return {k: v[-1] for k, v in up.parse_qs(query, keep_blank_values=True).items()}


def _truthy(value) -> bool:
    return str(value or "").strip().lower() in ("1", "true", "yes", "on")


def _split_netloc(netloc: str):
    """'user:pass@host:port' -> (user, password, host, port_text)."""
    userinfo, _, hostport = netloc.rpartition("@")
    user, password = None, None
    if userinfo:
        user, sep, pw = userinfo.partition(":")
        user = up.unquote(user)
        password = up.unquote(pw) if sep else None
    if hostport.startswith("["):
        end = hostport.find("]")
        if end < 0:
            raise LinkError("неверный IPv6-адрес")
        host = hostport[1:end]
        port = hostport[end + 2:] if hostport[end + 1:end + 2] == ":" else ""
    else:
        host, _, port = hostport.rpartition(":")
        if not host:
            host, port = hostport, ""
    host = up.unquote(host).strip()
    if not host:
        raise LinkError("не указан адрес сервера")
    return user, password, host, port


def _port(port_text: str) -> int:
    if not port_text.isdigit() or not 0 < int(port_text) < 65536:
        raise LinkError(f"неверный порт: {port_text or 'не указан'}")
    return int(port_text)


def _name(fragment: str, fallback: str) -> str:
    name = up.unquote(fragment or "").strip()
    return name or fallback


def _tls(params: dict, default_sni: str, reality: bool = False) -> dict:
    tls = {"enabled": True}
    sni = params.get("sni") or params.get("peer") or params.get("servername") or default_sni
    if sni:
        tls["server_name"] = sni
    if _truthy(params.get("allowInsecure") or params.get("insecure") or params.get("allow_insecure")):
        tls["insecure"] = True
    alpn = params.get("alpn")
    if alpn:
        tls["alpn"] = [a.strip() for a in up.unquote(alpn).split(",") if a.strip()]
    fp = params.get("fp") or params.get("fingerprint")
    if fp and fp.lower() != "none":
        tls["utls"] = {"enabled": True, "fingerprint": fp.lower()}
    if reality:
        pbk = params.get("pbk") or params.get("publicKey")
        if not pbk:
            raise LinkError("для Reality нужен публичный ключ (pbk)")
        tls["reality"] = {"enabled": True, "public_key": pbk, "short_id": params.get("sid", "")}
        # Reality в sing-box работает только с uTLS
        tls.setdefault("utls", {"enabled": True, "fingerprint": "chrome"})
        tls.pop("insecure", None)
    return tls


def _transport(params: dict, net: str):
    net = (net or "tcp").strip().lower()
    host = up.unquote(params.get("host", ""))
    path = up.unquote(params.get("path", ""))

    if net in ("tcp", "raw", "none", ""):
        return None
    if net == "ws":
        t = {"type": "ws", "path": path or "/"}
        m = re.search(r"[?&]ed=(\d+)", t["path"])
        if m:
            t["path"] = re.sub(r"[?&]ed=\d+", "", t["path"]) or "/"
            t["max_early_data"] = int(m.group(1))
            t["early_data_header_name"] = "Sec-WebSocket-Protocol"
        if host:
            t["headers"] = {"Host": host}
        return t
    if net == "grpc":
        return {"type": "grpc", "service_name": up.unquote(params.get("serviceName") or params.get("service_name") or path)}
    if net in ("http", "h2"):
        t = {"type": "http"}
        if host:
            t["host"] = [h.strip() for h in host.split(",") if h.strip()]
        if path:
            t["path"] = path
        return t
    if net == "httpupgrade":
        t = {"type": "httpupgrade", "path": path or "/"}
        if host:
            t["host"] = host
        return t
    if net == "quic":
        return {"type": "quic"}
    if net in ("xhttp", "splithttp"):
        raise LinkError("транспорт XHTTP поддерживается только ядром Xray, в sing-box его нет")
    raise LinkError(f"неизвестный транспорт: {net}")


def _server(link: str, name: str, outbound: dict) -> dict:
    return {
        "id": hashlib.sha1(link.encode("utf-8")).hexdigest()[:12],
        "name": name,
        "protocol": outbound["type"],
        "host": outbound["server"],
        "port": outbound.get("server_port", 0),
        "link": link,
        "outbound": outbound,
    }


# --- протоколы -------------------------------------------------------------------

def _vless(link, u):
    user, _, host, port = _split_netloc(u.netloc)
    p = _query(u.query)
    if not user:
        raise LinkError("не указан UUID")
    ob = {"type": "vless", "server": host, "server_port": _port(port), "uuid": user}
    if p.get("flow"):
        ob["flow"] = p["flow"]
    security = (p.get("security") or "none").lower()
    if security in ("tls", "xtls"):
        ob["tls"] = _tls(p, host)
    elif security == "reality":
        ob["tls"] = _tls(p, host, reality=True)
    transport = _transport(p, p.get("type"))
    if transport:
        ob["transport"] = transport
    ob["packet_encoding"] = "xudp"
    return _server(link, _name(u.fragment, host), ob)


def _vmess(link, u):
    body = link[len("vmess://"):].split("#", 1)[0]
    try:
        d = json.loads(b64decode(body))
    except (LinkError, json.JSONDecodeError):
        # Новый формат vmess://uuid@host:port?... — устроен как VLESS
        server = _vless(link, u)
        ob = server["outbound"]
        ob["type"] = "vmess"
        ob.pop("flow", None)
        ob["security"] = "auto"
        server["protocol"] = "vmess"
        return server
    host = str(d.get("add", "")).strip()
    if not host:
        raise LinkError("не указан адрес сервера")
    ob = {
        "type": "vmess",
        "server": host,
        "server_port": _port(str(d.get("port", ""))),
        "uuid": str(d.get("id", "")),
        "security": d.get("scy") or "auto",
        "alter_id": int(d.get("aid") or 0),
    }
    net = str(d.get("net") or "tcp")
    params = {
        "host": str(d.get("host") or ""),
        "path": str(d.get("path") or ""),
        "serviceName": str(d.get("path") or "") if net == "grpc" else "",
        "sni": str(d.get("sni") or ""),
        "alpn": str(d.get("alpn") or ""),
        "fp": str(d.get("fp") or ""),
        "allowInsecure": d.get("allowInsecure") or d.get("skip-cert-verify") or "",
    }
    if str(d.get("tls") or "").lower() == "tls":
        ob["tls"] = _tls(params, params["host"] or host)
    transport = _transport(params, net)
    if transport:
        ob["transport"] = transport
    ob["packet_encoding"] = "xudp"
    return _server(link, str(d.get("ps") or "").strip() or host, ob)


def _trojan(link, u):
    user, _, host, port = _split_netloc(u.netloc)
    p = _query(u.query)
    if not user:
        raise LinkError("не указан пароль")
    ob = {"type": "trojan", "server": host, "server_port": _port(port), "password": user}
    security = (p.get("security") or "tls").lower()
    if security != "none":
        ob["tls"] = _tls(p, host, reality=(security == "reality"))
    transport = _transport(p, p.get("type"))
    if transport:
        ob["transport"] = transport
    return _server(link, _name(u.fragment, host), ob)


def _shadowsocks(link, u):
    body = link[len("ss://"):].split("#", 1)[0]
    if "@" in body:
        userinfo, _, rest = body.rpartition("@")
        userinfo = up.unquote(userinfo)
        if ":" not in userinfo:
            userinfo = b64decode(userinfo)
        hostpart, _, query = rest.partition("?")
        hostpart = hostpart.rstrip("/")
    else:
        decoded = b64decode(body.split("?", 1)[0].rstrip("/"))
        userinfo, _, hostpart = decoded.rpartition("@")
        query = body.partition("?")[2]
    method, sep, password = userinfo.partition(":")
    if not sep or not method:
        raise LinkError("не указан метод шифрования или пароль")
    _, _, host, port = _split_netloc(hostpart)
    ob = {"type": "shadowsocks", "server": host, "server_port": _port(port), "method": method, "password": password}
    plugin = _query(query).get("plugin")
    if plugin:
        name, _, opts = up.unquote(plugin).partition(";")
        if name in ("obfs-local", "simple-obfs"):
            name = "obfs-local"
        elif name != "v2ray-plugin":
            raise LinkError(f"плагин Shadowsocks «{name}» не поддерживается")
        ob["plugin"] = name
        ob["plugin_opts"] = opts
    return _server(link, _name(u.fragment, host), ob)


def _hysteria2(link, u):
    user, password, host, port = _split_netloc(u.netloc)
    p = _query(u.query)
    auth = user or ""
    if password is not None:
        auth += ":" + password
    ob = {"type": "hysteria2", "server": host, "password": auth}
    ports = p.get("mport") or (port if port and not port.isdigit() else "")
    if ports:
        ob["server_ports"] = [r.strip().replace("-", ":") for r in ports.split(",") if r.strip()]
        if port.isdigit():
            ob["server_port"] = int(port)
    else:
        ob["server_port"] = _port(port or "443")
    obfs = p.get("obfs")
    if obfs and obfs.lower() != "none":
        ob["obfs"] = {"type": obfs, "password": p.get("obfs-password", "")}
    tls = _tls(p, host)
    tls.setdefault("alpn", ["h3"])
    ob["tls"] = tls
    return _server(link, _name(u.fragment, host), ob)


def _tuic(link, u):
    user, password, host, port = _split_netloc(u.netloc)
    p = _query(u.query)
    if not user:
        raise LinkError("не указан UUID")
    ob = {
        "type": "tuic",
        "server": host,
        "server_port": _port(port),
        "uuid": user,
        "password": password or p.get("password", ""),
        "congestion_control": p.get("congestion_control") or p.get("congestion-control") or "bbr",
        "udp_relay_mode": p.get("udp_relay_mode") or p.get("udp-relay-mode") or "native",
    }
    tls = _tls(p, host)
    tls.setdefault("alpn", ["h3"])
    ob["tls"] = tls
    return _server(link, _name(u.fragment, host), ob)


def _anytls(link, u):
    user, _, host, port = _split_netloc(u.netloc)
    p = _query(u.query)
    ob = {"type": "anytls", "server": host, "server_port": _port(port), "password": user or "", "tls": _tls(p, host)}
    return _server(link, _name(u.fragment, host), ob)


def _socks(link, u):
    user, password, host, port = _split_netloc(u.netloc)
    if user and password is None:
        # v2rayN: socks://base64(user:pass)@host:port
        try:
            user, _, password = b64decode(user).partition(":")
        except LinkError:
            pass
    ob = {"type": "socks", "server": host, "server_port": _port(port), "version": "5"}
    if user:
        ob["username"] = user
        ob["password"] = password or ""
    return _server(link, _name(u.fragment, host), ob)


_PARSERS = {
    "vless": _vless,
    "vmess": _vmess,
    "trojan": _trojan,
    "ss": _shadowsocks,
    "hysteria2": _hysteria2,
    "hy2": _hysteria2,
    "tuic": _tuic,
    "anytls": _anytls,
    "socks": _socks,
    "socks5": _socks,
}


# --- публичный интерфейс ---------------------------------------------------------

def parse_link(link: str) -> dict:
    link = link.strip()
    scheme = link.split("://", 1)[0].lower() if "://" in link else ""
    parser = _PARSERS.get(scheme)
    if not parser:
        raise LinkError(f"неизвестный протокол: {scheme or link[:20]}")
    try:
        return parser(link, up.urlsplit(link))
    except LinkError:
        raise
    except (ValueError, KeyError, TypeError) as e:
        raise LinkError(f"ошибка в ссылке: {e}") from e


def parse_many(text: str):
    """Разбирает текст со ссылками (по одной на строку). Возвращает (серверы, ошибки)."""
    servers, errors, seen = [], [], set()
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "://" not in line:
            continue
        try:
            server = parse_link(line)
        except LinkError as e:
            name = up.unquote(line.rpartition("#")[2]) if "#" in line else line[:40]
            errors.append(f"{name}: {e}")
            continue
        if server["id"] not in seen:
            seen.add(server["id"])
            servers.append(server)
    return servers, errors


def looks_like_links(text: str) -> bool:
    return any(line.strip().lower().startswith(tuple(s + "://" for s in SCHEMES)) for line in text.splitlines())


def parse_subscription(body: str):
    """Тело подписки: список ссылок открытым текстом или в base64."""
    text = body.strip()
    if not looks_like_links(text):
        if text.startswith(("{", "proxies:", "port:", "mixed-port:", "mode:")) or "\nproxies:" in text:
            raise LinkError("подписка в формате Clash/sing-box пока не поддерживается — нужен список ссылок")
        if text.startswith("happ://"):
            raise LinkError("зашифрованные подписки Happ открываются только в самом Happ")
        text = b64decode(text)
    servers, errors = parse_many(text)
    if not servers and not errors:
        raise LinkError("в подписке нет серверов")
    return servers, errors


def parse_userinfo(header: str) -> dict:
    """Заголовок subscription-userinfo: upload=..; download=..; total=..; expire=.."""
    info = {}
    for part in (header or "").split(";"):
        key, _, value = part.strip().partition("=")
        if key in ("upload", "download", "total", "expire") and value.strip().isdigit():
            info[key] = int(value.strip())
    return info


def parse_title(header: str) -> str:
    header = (header or "").strip()
    if header.startswith("base64:"):
        try:
            return b64decode(header[7:]).strip()
        except LinkError:
            return ""
    return header
