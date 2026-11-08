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

CLASH_YAML = f"""
mixed-port: 7890
proxies:
  - name: "Clash Reality"
    type: vless
    server: r.example.com
    port: 443
    uuid: {UUID}
    network: tcp
    tls: true
    flow: xtls-rprx-vision
    servername: www.microsoft.com
    client-fingerprint: chrome
    reality-opts:
      public-key: {PBK}
      short-id: 6ba85179e30d4fc2
  - name: "Clash VMess WS"
    type: vmess
    server: vm.example.com
    port: 443
    uuid: {UUID}
    alterId: 0
    cipher: auto
    tls: true
    network: ws
    ws-opts:
      path: /ray
      headers:
        Host: cdn.example.com
  - name: "Clash Trojan gRPC"
    type: trojan
    server: t.example.com
    port: 443
    password: pw
    network: grpc
    grpc-opts:
      grpc-service-name: svc
  - name: "Clash SS obfs"
    type: ss
    server: ss.example.com
    port: 8388
    cipher: aes-256-gcm
    password: secret
    plugin: obfs
    plugin-opts:
      mode: tls
      host: bing.com
  - name: "Clash Hy2"
    type: hysteria2
    server: hy.example.com
    port: 443
    ports: 20000-30000
    password: pw
    obfs: salamander
    obfs-password: cats
  - name: "Clash TUIC"
    type: tuic
    server: tu.example.com
    port: 443
    uuid: {UUID}
    password: pw
    congestion-controller: bbr
  - name: "Clash WireGuard"
    type: wireguard
    server: wg.example.com
    port: 51820
proxy-groups: []
"""

SINGBOX_JSON = json.dumps({"outbounds": [
    {"type": "selector", "tag": "proxy", "outbounds": ["NL"]},
    {"type": "vless", "tag": "NL", "server": "nl.example.com", "server_port": 443, "uuid": UUID,
     "tls": {"enabled": True, "server_name": "nl.example.com"}},
    {"type": "hysteria2", "tag": "FI", "server": "fi.example.com", "server_port": 443, "password": "pw",
     "tls": {"enabled": True, "server_name": "fi.example.com"}},
    {"type": "direct", "tag": "direct"},
]})

DEEP_LINKS = {
    "https://sub.example.com/abc": "https://sub.example.com/abc",
    "happ://add/https://sub.example.com/abc": "https://sub.example.com/abc",
    "sing-box://import-remote-profile?url=https%3A%2F%2Fsub.example.com%2Fabc#My": "https://sub.example.com/abc",
    "v2rayng://install-sub?url=https%3A%2F%2Fsub.example.com%2Fabc&name=x": "https://sub.example.com/abc",
    "hiddify://import/https://sub.example.com/abc#name": "https://sub.example.com/abc",
    f"vless://{UUID}@h.example.com:443?host=https://x#n": None,
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

    # Подписка Clash/Mihomo
    clash, clash_errors = links.parse_subscription(CLASH_YAML)
    if len(clash) == 6 and len(clash_errors) == 1 and "wireguard" in clash_errors[0]:
        print(f"ok   subscription clash: {len(clash)} серверов, пропущен WireGuard")
        for s in clash:
            servers["clash " + s["name"]] = s
    else:
        print(f"FAIL subscription clash: {len(clash)} серверов, ошибки {clash_errors}")
        failed += 1

    # Подписка sing-box JSON (служебные selector/direct пропускаются)
    sbj, _ = links.parse_subscription(SINGBOX_JSON)
    sbj_b64, _ = links.parse_subscription(base64.b64encode(SINGBOX_JSON.encode()).decode())
    if [s["name"] for s in sbj] == ["NL", "FI"] and len(sbj_b64) == 2:
        print("ok   subscription sing-box json (+ base64)")
        for s in sbj:
            servers["json " + s["name"]] = s
    else:
        print(f"FAIL subscription json: {[s['name'] for s in sbj]}")
        failed += 1

    # Веб-страница вместо подписки
    try:
        links.parse_subscription("<!DOCTYPE html><html><body>Подписка</body></html>")
        print("FAIL html: ожидалась ошибка")
        failed += 1
    except links.LinkError as e:
        print(f"ok   reject html: {e}")

    # Ссылки-приглашения приложений
    for line, expected in DEEP_LINKS.items():
        got = links.extract_subscription_url(line)
        if got == expected:
            print(f"ok   deep link {line[:45]}")
        else:
            print(f"FAIL deep link {line}: {got!r} != {expected!r}")
            failed += 1

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
