"""Самотест AstraMars VPN: разбор ссылок всех протоколов и проверка конфигураций настоящим sing-box.

При сборке образа:   python3 vpn_selftest.py /usr/lib/astramars-vpn /usr/libexec/astramars-vpn/sing-box
Локально (без ядра): python3 vpn_selftest.py system_files/usr/lib/astramars-vpn
"""

import base64
import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, sys.argv[1])
from astramars_vpn import links, singbox  # noqa: E402

UUID = "b831381d-6324-4d53-ad4f-8cda48b30811"
PBK = "Z84J2IelR9ch3k8VtlVhhs5ycBUlXA7wHBWcBrjqnAw"

VMESS = "vmess://" + base64.b64encode(json.dumps({
    "v": "2", "ps": "VMess WS TLS", "add": "vm.example.com", "port": "443", "id": UUID, "aid": "0",
    "scy": "auto", "net": "ws", "host": "cdn.example.com", "path": "/ray?ed=2048", "tls": "tls", "sni": "cdn.example.com",
}).encode()).decode()

SS_2022 = "ss://" + base64.urlsafe_b64encode(b"2022-blake3-aes-128-gcm:Y2VsZXN0aWFsLWthdHMhIQ==").decode().rstrip("=") + "@ss.example.com:8388#SS%202022"
SS_LEGACY = "ss://" + base64.b64encode(b"chacha20-ietf-poly1305:secret@203.0.113.7:8389").decode() + "#SS%20legacy"

CASES = {
    "vless-reality": f"vless://{UUID}@vless.example.com:443?type=tcp&security=reality&pbk={PBK}&sid=6ba85179e30d4fc2&sni=www.microsoft.com&fp=chrome&flow=xtls-rprx-vision#Reality%20%F0%9F%87%B3%F0%9F%87%B1",
    "vless-ws-tls": f"vless://{UUID}@[2001:db8::1]:8443?type=ws&security=tls&path=%2Fws&host=cdn.example.com&sni=cdn.example.com&alpn=h2%2Chttp%2F1.1#WS",
    "vless-grpc": f"vless://{UUID}@grpc.example.com:443?type=grpc&security=tls&serviceName=grpcsvc#gRPC",
    "vless-httpupgrade": f"vless://{UUID}@hu.example.com:80?type=httpupgrade&path=%2Fup&host=hu.example.com#HU",
    "vmess-json": VMESS,
    "trojan": "trojan://p%40ss@trojan.example.com:443?sni=trojan.example.com&allowInsecure=1#Trojan",
    "ss-2022": SS_2022,
    "ss-legacy": SS_LEGACY,
    "ss-obfs": "ss://YWVzLTI1Ni1nY206c2VjcmV0@obfs.example.com:8388/?plugin=obfs-local%3Bobfs%3Dhttp%3Bobfs-host%3Dexample.com#SS%20obfs",
    "hysteria2": "hysteria2://letmein@hy.example.com:443?sni=hy.example.com&obfs=salamander&obfs-password=cats&insecure=1#Hy2",
    "hy2-ports": "hy2://letmein@hy.example.com:443?mport=20000-30000#Hy2%20ports",
    "tuic": f"tuic://{UUID}:pw@tuic.example.com:443?congestion_control=bbr&alpn=h3&sni=tuic.example.com#TUIC",
    "anytls": "anytls://pw@any.example.com:443?sni=any.example.com#AnyTLS",
    "socks": "socks://dXNlcjpwYXNz@198.51.100.4:1080#SOCKS",
}

EXPECT_FAIL = {
    "xhttp": f"vless://{UUID}@x.example.com:443?type=xhttp&security=tls#XHTTP",
    "unknown": "foo://bar",
}


def main():
    singbox_bin = sys.argv[2] if len(sys.argv) > 2 else None
    failed = 0

    servers = {}
    for name, link in CASES.items():
        try:
            servers[name] = links.parse_link(link)
            s = servers[name]
            print(f"ok   parse {name:18} -> {s['protocol']:12} {s['host']}:{s['port']}  «{s['name']}»")
        except links.LinkError as e:
            print(f"FAIL parse {name}: {e}")
            failed += 1

    for name, link in EXPECT_FAIL.items():
        try:
            links.parse_link(link)
            print(f"FAIL {name}: ожидалась ошибка")
            failed += 1
        except links.LinkError as e:
            print(f"ok   reject {name}: {e}")

    # Подписка в base64 с одной битой строкой
    body = base64.b64encode("\n".join(list(CASES.values())[:3] + [EXPECT_FAIL["xhttp"]]).encode()).decode()
    subs, errors = links.parse_subscription(body)
    if len(subs) == 3 and len(errors) == 1:
        print("ok   subscription base64: 3 сервера, 1 ошибка")
    else:
        print(f"FAIL subscription: {len(subs)} серверов, {errors}")
        failed += 1
    info = links.parse_userinfo("upload=1024; download=2048; total=10737418240; expire=1798675200")
    assert info == {"upload": 1024, "download": 2048, "total": 10737418240, "expire": 1798675200}, info
    assert links.parse_title("base64:" + base64.b64encode("Мой VPN".encode()).decode()) == "Мой VPN"
    print("ok   subscription headers")

    if not singbox_bin:
        print("\n(ядро sing-box не указано — проверка конфигураций пропущена)")
    else:
        with tempfile.TemporaryDirectory() as tmp:
            for name, server in servers.items():
                for mode in ("tun", "proxy"):
                    for bypass in (True, False):
                        cfg = singbox.build_config(server["outbound"], mode=mode, bypass_ru=bypass, api_secret="test")
                        path = os.path.join(tmp, "c.json")
                        with open(path, "w", encoding="utf-8") as f:
                            json.dump(cfg, f)
                        p = subprocess.run([singbox_bin, "check", "-c", path], capture_output=True, text=True)
                        tag = f"{name}/{mode}/{'ru' if bypass else 'all'}"
                        if p.returncode == 0:
                            print(f"ok   sing-box check {tag}")
                        else:
                            print(f"FAIL sing-box check {tag}: {(p.stderr or p.stdout).strip()}")
                            failed += 1

    print(f"\nИтого ошибок: {failed}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
