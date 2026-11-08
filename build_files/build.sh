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
    python3-pyyaml \
    python3-qrcode \
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

### 4б. Экран входа и блокировки ###################################################
bash "$CTX/login-theme.sh"

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

chmod +x /usr/bin/astramars-vpn /usr/bin/ygolek-vpn
python3 -c "import PySide6.QtQuick, PySide6.QtQuickControls2, qrcode, yaml; print('PySide6', PySide6.__version__)"

# Самотест: все протоколы разбираются, а каждая конфигурация проходит проверку sing-box
python3 "$CTX/vpn_selftest.py" /usr/lib/astramars-vpn /usr/libexec/astramars-vpn/sing-box

# Интерфейс загружается на Qt из Fedora без ошибок QML
ASTRAMARS_VPN_DEV=1 ASTRAMARS_VPN_HOME=/tmp/vpn-check QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software \
    /usr/bin/ygolek-vpn --check
rm -rf /tmp/vpn-check

### 5б. AstraMars Store (магазин приложений) ###################################
chmod +x /usr/bin/astramars-store /usr/libexec/astramars-update
bootc --version
mkdir -p /tmp/store-check
curl -fsSL --retry 3 -o /tmp/store-check/appstream.xml.gz     https://dl.flathub.org/repo/appstream/x86_64/appstream.xml.gz
python3 "$CTX/store_selftest.py" /usr/lib/astramars-store /tmp/store-check
ASTRAMARS_STORE_DEV=1 ASTRAMARS_STORE_APPSTREAM=/tmp/store-check QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software     /usr/bin/astramars-store --check
rm -rf /tmp/store-check

### 5в. Быстрые действия ###########################################################
chmod +x /usr/bin/astramars-actions
python3 "$CTX/actions_selftest.py" /usr/lib/astramars-actions
ASTRAMARS_ACTIONS_DEV=1 ASTRAMARS_ACTIONS_HOME=/tmp/actions-check QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software     /usr/bin/astramars-actions --check
rm -rf /tmp/actions-check

### 6. Заставка загрузки (последним: пересобирает initramfs) #################
bash "$CTX/plymouth.sh"

### 7. Уборка ##################################################################
dnf5 clean all
