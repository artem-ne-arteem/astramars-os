# AstraMars OS

Дистрибутив Linux на базе Fedora Kinoite (KDE Plasma 6), названный в честь кошки Астры и кота Марсика.
Тёмная тема, плавные анимации, атомарные обновления с откатом.

## Что внутри

| Путь | Что это |
|---|---|
| `Containerfile` | Описание системы: основа и шаги сборки |
| `build_files/build.sh` | Установка пакетов, тема, службы |
| `build_files/branding.sh` | Название системы (`/usr/lib/os-release`) |
| `system_files/` | Файлы, которые копируются в корень системы |
| `system_files/etc/xdg/kdeglobals` | Тёмная тема, шрифты, акцентный цвет |
| `system_files/etc/xdg/kwinrc` | Эффекты и анимации окон |
| `system_files/usr/share/wallpapers/AstraMars/` | Обои |
| `system_files/usr/share/pixmaps/astramars-logo.svg` | Логотип |
| `system_files/usr/share/astramars/flatpaks.list` | Программы, которые ставятся при первом запуске |
| `.github/workflows/build.yml` | Автосборка образа при каждом изменении |
| `.github/workflows/build-iso.yml` | Сборка установочного ISO (вручную) |

## Как запустить сборку

1. Создайте на GitHub **публичный** репозиторий `astramars-os`
   (для публичных репозиториев сборка и хранение бесплатны).
2. Загрузите туда эту папку (через GitHub Desktop или `git push`).
3. Откройте вкладку **Actions** и дождитесь зелёной галочки у «Сборка образа AstraMars OS» (15–25 минут).
4. Сделайте образ публичным: профиль GitHub → **Packages** → `astramars-os` →
   **Package settings** → **Change visibility** → **Public**.

Образ будет доступен как `ghcr.io/<ваш-логин>/astramars-os:latest` (логин маленькими буквами).

## Как поставить на свой ПК

**Вариант А — через Fedora Kinoite (рекомендуется для первого раза):**
1. Установите обычную Fedora Kinoite второй системой: https://fedoraproject.org/atomic-desktops/kinoite/
2. В терминале выполните:
   ```bash
   sudo bootc switch ghcr.io/<ваш-логин>/astramars-os:latest
   ```
   Если `bootc` ругается, то же самое делает:
   ```bash
   sudo rpm-ostree rebase ostree-unverified-registry:ghcr.io/<ваш-логин>/astramars-os:latest
   ```
3. Перезагрузитесь. Готово — дальше обновления приходят сами.

**Вариант Б — через свой ISO:**
Actions → «Сборка установочного ISO» → **Run workflow**. Когда закончится,
скачайте ISO внизу страницы запуска и запишите на флешку (Fedora Media Writer или Rufus).

## Прокси (Happ и другие)

Если VPN-программа работает только в режиме прокси, AstraMars находит его сама:
раз в 30 секунд проверяет порты `10809 10808 2080 2081 7890 7897 1080 8080 20171 20172 8888`
и, если через прокси открывается интернет, направляет через него обновления системы,
Flatpak, Discover, терминал и рабочий стол KDE. Выключили прокси — всё идёт напрямую.

```bash
astramars-proxy            # состояние
astramars-proxy on 12345   # всегда использовать прокси на порту 12345
astramars-proxy auto       # снова автоматически
astramars-proxy off        # не использовать прокси
```

Браузер и программы рабочего стола подхватывают прокси после выхода и входа в систему.

## Откат

Если новая версия сломалась — при загрузке выберите в меню предыдущий пункт.
Или: `sudo bootc rollback` и перезагрузка.

## Перед публикацией для других людей

Fedora разрешает ремиксы, но запрещает выдавать их за официальную Fedora.
Перед публичным распространением нужно заменить логотипы Fedora (`fedora-logos`)
на свои — это следующий шаг проекта.
