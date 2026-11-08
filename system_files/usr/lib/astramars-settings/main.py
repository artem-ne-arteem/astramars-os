"""Настройки AstraMars — точка входа.

  astramars-settings [--page раздел]   настройки
  astramars-settings --assistant       окно помощника (Meta + A)
  astramars-settings --run-exe ФАЙЛ    запуск программы для Windows
  astramars-settings --check           проверка интерфейса при сборке (все разделы и окна)
"""

import os
import signal
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
VENDOR = os.path.join(HERE, "vendor")
if os.path.isdir(VENDOR):
    sys.path.insert(1, VENDOR)

from PySide6.QtCore import QTimer, QUrl  # noqa: E402
from PySide6.QtGui import QGuiApplication, QIcon  # noqa: E402
from PySide6.QtNetwork import QLocalServer, QLocalSocket  # noqa: E402
from PySide6.QtQml import QQmlApplicationEngine  # noqa: E402
from PySide6.QtQuickControls2 import QQuickStyle  # noqa: E402

from astramars_settings import appearance  # noqa: E402
from astramars_settings.backend import Backend  # noqa: E402
from astramars_settings.util import USER, spawn  # noqa: E402

PAGES = ["home", "appearance", "network", "system", "windows", "games", "phone", "assistant", "laptop", "privacy"]
LOGO = "/usr/share/astramars/branding/about-logo.png"
WALLPAPERS = "/usr/share/wallpapers/AstraMarsDaytime"


def arg(name):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv and sys.argv.index(name) + 1 < len(sys.argv) else None


def resource(path, fallback):
    """В режиме разработки файлы берутся из репозитория (system_files/…)."""
    if os.path.exists(path):
        return path
    return os.path.normpath(os.path.join(HERE, "..", "..", "..", fallback))


def main():
    check = "--check" in sys.argv
    screenshot = arg("--screenshot")
    exe_path = arg("--run-exe")
    mode = "exe" if exe_path else "assistant" if "--assistant" in sys.argv else "settings"
    page = arg("--page") or ""
    if page not in PAGES:
        page = ""

    QQuickStyle.setStyle("Basic")
    app = QGuiApplication(sys.argv)
    app.setApplicationName("astramars-settings" if mode == "settings" else f"astramars-{mode}")
    app.setApplicationDisplayName({"settings": "Настройки AstraMars", "assistant": "Помощник AstraMars",
                                   "exe": "Программа для Windows"}[mode])
    app.setDesktopFileName({"settings": "astramars-settings", "assistant": "astramars-assistant",
                            "exe": "astramars-run-exe"}[mode])
    app.setWindowIcon(QIcon.fromTheme("astramars-settings"))
    font = app.font()
    font.setFamily("Inter")
    app.setFont(font)
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Одно окно настроек и одно окно помощника: повторный запуск показывает уже открытое
    server = None
    if mode != "exe" and not check and not screenshot:
        name = f"astramars-{mode}-{USER}"
        probe = QLocalSocket()
        probe.connectToServer(name)
        if probe.waitForConnected(300):
            probe.write(("show:" + page).encode())
            probe.waitForBytesWritten(300)
            return 0
        QLocalServer.removeServer(name)
        server = QLocalServer()
        server.listen(name)

    backend = Backend()
    engine = QQmlApplicationEngine()
    warnings = []

    def on_warnings(ws):
        for w in ws:
            warnings.append(w.toString())
            print("QML:", w.toString(), file=sys.stderr)
    engine.warnings.connect(on_warnings)

    ctx = engine.rootContext()
    ctx.setContextProperty("backend", backend)
    ctx.setContextProperty("astraAccent", appearance.accent())
    ctx.setContextProperty("initialPage", page)
    ctx.setContextProperty("exePath", exe_path or "")
    ctx.setContextProperty("logoUrl", QUrl.fromLocalFile(
        resource(LOGO, "usr/share/astramars/branding/about-logo.png")).toString())
    ctx.setContextProperty("wallpaperDir", QUrl.fromLocalFile(
        resource(WALLPAPERS, "usr/share/wallpapers/AstraMarsDaytime")).toString())
    backend.changed.connect(lambda what: what == "accent" and ctx.setContextProperty("astraAccent", appearance.accent()))
    if mode == "assistant":
        # Кнопка «открыть раздел» из отдельного окна помощника открывает Настройки
        backend.openPage.connect(lambda p: spawn("astramars-settings", "--page", p))

    qml = {"settings": "Main.qml", "assistant": "AssistantWindow.qml", "exe": "ExeWindow.qml"}[mode]
    engine.load(QUrl.fromLocalFile(os.path.join(HERE, "qml", qml)))
    if not engine.rootObjects():
        return 1
    window = engine.rootObjects()[0]

    def show(p=""):
        if p and mode == "settings":
            window.setProperty("page", p)
        window.show()
        window.raise_()
        window.requestActivate()

    if server:
        def on_connection():
            sock = server.nextPendingConnection()
            sock.waitForReadyRead(300)
            data = bytes(sock.readAll()).decode(errors="replace")
            show(data.split(":", 1)[1] if data.startswith("show:") else "")
        server.newConnection.connect(on_connection)

    if check:
        # Проверка при сборке: каждый раздел загружается без предупреждений QML
        window.show()
        if mode == "settings":
            for i, p in enumerate(PAGES):
                QTimer.singleShot(300 + i * 400, lambda p=p: window.setProperty("page", p))
            QTimer.singleShot(300 + len(PAGES) * 400 + 600, app.quit)
        else:
            QTimer.singleShot(1500, app.quit)
        app.exec()
        print("QML OK" if not warnings else f"QML: предупреждений {len(warnings)}")
        del window, engine
        return 1 if warnings else 0

    show()
    if screenshot:
        def grab():
            window.grabWindow().save(screenshot)
            app.quit()
        QTimer.singleShot(int(os.environ.get("ASTRAMARS_SETTINGS_SHOT_DELAY", "2500")), grab)

    code = app.exec()
    del window, engine
    return code


if __name__ == "__main__":
    sys.exit(main())
