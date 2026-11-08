"""Сборка конфигурации sing-box 1.14 для выбранного сервера."""

import copy

RULES_DIR = "/usr/share/astramars-vpn/rules"
MIXED_PORT = 2080      # локальный HTTP/SOCKS-прокси (его находит astramars-proxy)
API_PORT = 9090        # Clash API: скорость и трафик


def build_config(outbound: dict, *, mode: str = "tun", bypass_ru: bool = True,
                 api_secret: str = "", rules_dir: str = RULES_DIR) -> dict:
    proxy = copy.deepcopy(outbound)
    proxy["tag"] = "proxy"

    inbounds = [{
        "type": "mixed",
        "tag": "mixed-in",
        "listen": "127.0.0.1",
        "listen_port": MIXED_PORT,
    }]
    if mode == "tun":
        inbounds.insert(0, {
            "type": "tun",
            "tag": "tun-in",
            "interface_name": "astramars0",
            "address": ["172.19.0.1/30", "fdfe:dcba:9877::1/126"],
            "mtu": 9000,
            "auto_route": True,
            "strict_route": True,
            "stack": "mixed",
        })

    dns_rules = []
    route_rules = [
        {"action": "sniff"},
        {"protocol": "dns", "action": "hijack-dns"},
        {"ip_is_private": True, "outbound": "direct"},
    ]
    rule_sets = []

    if bypass_ru:
        ru_domains = {"domain_suffix": ["ru", "su", "xn--p1ai"]}
        rule_sets = [
            {"type": "local", "tag": "geosite-ru", "format": "binary", "path": f"{rules_dir}/geosite-category-ru.srs"},
            {"type": "local", "tag": "geoip-ru", "format": "binary", "path": f"{rules_dir}/geoip-ru.srs"},
        ]
        dns_rules += [
            dict(ru_domains, action="route", server="dns-direct"),
            {"rule_set": "geosite-ru", "action": "route", "server": "dns-direct"},
        ]
        route_rules += [
            dict(ru_domains, outbound="direct"),
            {"rule_set": ["geosite-ru", "geoip-ru"], "outbound": "direct"},
        ]

    config = {
        "log": {"level": "info", "timestamp": True},
        "dns": {
            "servers": [
                {"type": "https", "tag": "dns-remote", "server": "1.1.1.1", "detour": "proxy"},
                {"type": "udp", "tag": "dns-direct", "server": "77.88.8.8"},
            ],
            "rules": dns_rules,
            "final": "dns-remote",
            "strategy": "ipv4_only",
        },
        "inbounds": inbounds,
        "outbounds": [proxy, {"type": "direct", "tag": "direct"}],
        "route": {
            "rules": route_rules,
            "rule_set": rule_sets,
            "final": "proxy",
            "auto_detect_interface": True,
            "default_domain_resolver": "dns-direct",
        },
        "experimental": {
            "cache_file": {"enabled": True, "path": "cache.db"},
            "clash_api": {"external_controller": f"127.0.0.1:{API_PORT}", "secret": api_secret},
        },
    }
    if not dns_rules:
        del config["dns"]["rules"]
    if not rule_sets:
        del config["route"]["rule_set"]
    return config
