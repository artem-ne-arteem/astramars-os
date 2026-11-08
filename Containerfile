# AstraMars OS — атомарный дистрибутив на базе Fedora Kinoite (KDE Plasma)
#
# Основа: ublue-os/kinoite-main — это официальная Fedora Kinoite
# плюс мультимедиа-кодеки и полезные мелочи для дома.

ARG BASE_IMAGE=ghcr.io/ublue-os/kinoite-main
# Версия Fedora. При выходе новой — поменять число здесь.
ARG FEDORA_VERSION=45

# Отдельный слой со скриптами сборки (в итоговый образ не попадает)
FROM scratch AS ctx
COPY build_files /

FROM ${BASE_IMAGE}:${FEDORA_VERSION}
# standard — основной образ; nvidia — с драйвером NVIDIA (BASE_IMAGE=ghcr.io/ublue-os/kinoite-nvidia)
ARG VARIANT=standard

# Файлы системы: темы, обои, логотипы, настройки KDE по умолчанию
COPY system_files /

RUN --mount=type=bind,from=ctx,source=/,target=/ctx \
    --mount=type=cache,dst=/var/cache \
    --mount=type=tmpfs,dst=/tmp \
    bash /ctx/build.sh && \
    ostree container commit

# Проверка, что образ корректен для bootc
RUN bootc container lint
