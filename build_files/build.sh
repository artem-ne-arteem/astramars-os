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
    jetbrains-mono-fonts-all

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

### 5. Уборка ##################################################################
dnf5 clean all
