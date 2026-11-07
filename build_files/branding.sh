#!/usr/bin/bash
# Меняет название системы на AstraMars OS.
# ID оставляем «fedora»: на него опираются dnf, bootc-image-builder и другие инструменты.
set -ouex pipefail

OS_RELEASE=/usr/lib/os-release
VERSION_ID="$(. "$OS_RELEASE" && echo "$VERSION_ID")"

set_kv() {
    local key="$1" value="$2"
    if grep -q "^${key}=" "$OS_RELEASE"; then
        sed -i "s|^${key}=.*|${key}=\"${value}\"|" "$OS_RELEASE"
    else
        echo "${key}=\"${value}\"" >> "$OS_RELEASE"
    fi
}

set_kv NAME             "AstraMars OS"
set_kv PRETTY_NAME      "AstraMars OS ${VERSION_ID}"
set_kv VARIANT          "Astra & Mars"
set_kv VARIANT_ID       "astramars"
set_kv LOGO             "astramars-logo"
set_kv DEFAULT_HOSTNAME "astramars"
set_kv ANSI_COLOR       "38;2;255;122;69"
set_kv ID_LIKE          "fedora"
