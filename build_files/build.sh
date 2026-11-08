#!/usr/bin/bash
# Основной скрипт сборки AstraMars OS. Выполняется внутри образа.
set -ouex pipefail

CTX="$(dirname "$(readlink -f "$0")")"

### 1. Пакеты #################################################################
# Системные утилиты и шрифты. Обычные программы (браузер, офис и т.д.)
# ставятся как Flatpak при первом запуске — см. system_files/usr/share/astramars/flatpaks.list
dnf5 install -y \
    fastfetch \
    btop \
    rsms-inter-fonts \
    jetbrains-mono-fonts-all \
    python3-pyside6 \
    qt6-qtsvg

### 2. Брендинг ##############################################################
bash "$CTX/branding.sh"

### 3. Оформление KDE ##########################################################
# Своя «глобальная тема» на основе Breeze Dark: берём её целиком
# и подменяем настройки по умолчанию и описание.
LNF_SRC=/usr/share/plasma/look-and-feel/org.kde.breezedark.desktop
LNF_DST=/usr/share/plasma/look-and-feel/org.astramars.desktop
rm -rf "$LNF_DST"
cp -a "$LNF_SRC" "$LNF_DST"
cp /usr/share/astramars/lnf/metadata.json "$LNF_DST/metadata.json"
cp /usr/share/astramars/lnf/defaults      "$LNF_DST/contents/defaults"

### 4. Службы ##################################################################
chmod +x /usr/libexec/astramars-flatpak-setup
systemctl enable astramars-flatpak-setup.service

# Автонастройка прокси (Happ и т.п.)
chmod +x /usr/bin/astramars-proxy
chmod 0440 /etc/sudoers.d/astramars-proxy
visudo -cf /etc/sudoers.d/astramars-proxy
systemctl enable astramars-proxy.timer

### 5. AstraMars VPN ##########################################################
SINGBOX_VERSION=1.14.4
SB_DIR="/tmp/sing-box-${SINGBOX_VERSION}-linux-amd64"
curl -fsSL --retry 3 \
    "https://github.com/SagerNet/sing-box/releases/download/v${SINGBOX_VERSION}/sing-box-${SINGBOX_VERSION}-linux-amd64.tar.gz" \
    | tar -xz -C /tmp
install -Dm755 "$SB_DIR/sing-box" /usr/libexec/astramars-vpn/sing-box
rm -rf "$SB_DIR"
/usr/libexec/astramars-vpn/sing-box version

# Наборы правил «российские сайты напрямую» встроены в образ и обновляются с каждой сборкой
RULES=/usr/share/astramars-vpn/rules
mkdir -p "$RULES"
curl -fsSL --retry 3 -o "$RULES/geoip-ru.srs" \
    https://raw.githubusercontent.com/SagerNet/sing-geoip/rule-set/geoip-ru.srs
curl -fsSL --retry 3 -o "$RULES/geosite-category-ru.srs" \
    https://raw.githubusercontent.com/SagerNet/sing-geosite/rule-set/geosite-category-ru.srs

chmod +x /usr/bin/astramars-vpn
python3 -c "import PySide6.QtQuick, PySide6.QtQuickControls2; print('PySide6', PySide6.__version__)"

# Самотест: все протоколы разбираются, а каждая конфигурация проходит проверку sing-box
python3 "$CTX/vpn_selftest.py" /usr/lib/astramars-vpn /usr/libexec/astramars-vpn/sing-box

# Интерфейс загружается на Qt из Fedora без ошибок QML
ASTRAMARS_VPN_DEV=1 ASTRAMARS_VPN_HOME=/tmp/vpn-check QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software \
    python3 /usr/lib/astramars-vpn/main.py --check
rm -rf /tmp/vpn-check

### 6. Уборка ##################################################################
dnf5 clean all
