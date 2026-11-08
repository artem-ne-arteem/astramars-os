#!/usr/bin/bash
# Заставка загрузки AstraMars (Plymouth): логотип, надпись точками и кольцо из точек
# вместо логотипа Fedora. Тема живёт внутри initramfs, поэтому после смены темы
# initramfs пересобирается (так же делает Universal Blue).
set -ouex pipefail

THEME=astramars
DIR=/usr/share/plymouth/themes/$THEME

plymouth-set-default-theme || true
ls /usr/share/plymouth/themes

# Картинки для окна ввода пароля диска и т.п. — из стандартной темы spinner
mkdir -p "$DIR"
cp -a /usr/share/plymouth/themes/spinner/. "$DIR/"
rm -f "$DIR"/spinner.plymouth "$DIR"/throbber-*.png "$DIR"/animation-*.png "$DIR"/watermark.png
# Наши: логотип с надписью, кольцо из точек, описание темы
cp -a /usr/share/astramars/plymouth/. "$DIR/"
ls "$DIR"

plymouth-set-default-theme "$THEME"
cat /etc/plymouth/plymouthd.conf

# Пересборка initramfs для ядра образа
KVER="$(ls /usr/lib/modules | sort -V | tail -1)"
INITRAMFS="/usr/lib/modules/$KVER/initramfs.img"
/usr/bin/dracut --no-hostonly --kver "$KVER" --reproducible --zstd -v --add ostree -f "$INITRAMFS"
chmod 0600 "$INITRAMFS"

# Проверка: тема и модуль ostree действительно внутри
lsinitrd "$INITRAMFS" > /tmp/initramfs.list
grep -E "plymouth/themes/$THEME/(astramars.plymouth|watermark.png|throbber-0001.png)" /tmp/initramfs.list
grep -q "themes/$THEME/astramars.plymouth" /tmp/initramfs.list
grep -q "Theme=$THEME" /tmp/initramfs.list || lsinitrd -f etc/plymouth/plymouthd.conf "$INITRAMFS" | grep -q "Theme=$THEME"
grep -q "ostree-prepare-root" /tmp/initramfs.list
rm -f /tmp/initramfs.list
echo "Заставка $THEME встроена в initramfs ядра $KVER"
