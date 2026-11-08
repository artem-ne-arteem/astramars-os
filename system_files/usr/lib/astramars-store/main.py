"""AstraMars Store — точка входа."""

import os
import signal
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtCore import Q_ARG, QMetaObject, QTimer, QUrl  # noqa: E402
from PySide6.QtGui import QGuiApplication, QIcon  # noqa: E402
from PySide6.QtNetwork import QLocalServer, QLocalSocket  # noqa: E402
from PySide6.QtQml import QQmlApplicationEngine  # noqa: E402
from PySide6.QtQuickControls2 import QQuickStyle  # noqa: E402

from astramars_store.backend import Backend  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SOCKET_NAME = f"astramars-store-{os.environ.get('USER') or os.environ.get('USERNAME') or 'user'}"


def accent():
    """Акцентный цвет, выбранный в Настройках AstraMars."""
    import json
    path = os.path.join(os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config"), "astramars", "theme.json")
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f).get("accent", "#ff3b30")
    except (OSError, ValueError):
        return "#ff3b30"


def main():
    check_only = "--check" in sys.argv
    screenshot = sys.argv[sys.argv.index("--screenshot") + 1] if "--screenshot" in sys.argv else None
    arg = sys.argv[sys.argv.index("--search") + 1] if "--search" in sys.argv[:-1] else ""

    QQuickStyle.setStyle("Basic")
    app = QGuiApplication(sys.argv)
    app.setApplicationName("astramars-store")
    app.setApplicationDisplayName("AstraMars Store")
    app.setDesktopFileName("astramars-store")
    app.setWindowIcon(QIcon.fromTheme("astramars-store"))
    font = app.font()
    font.setFamily("Inter")
    app.setFont(font)
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Один экземпляр: повторный запуск поднимает уже открытое окно
    probe = QLocalSocket()
    probe.connectToServer(SOCKET_NAME)
    if not check_only and probe.waitForConnected(300):
        probe.write(("search:" + (arg or "")).encode() if arg else b"show")
        probe.waitForBytesWritten(300)
        return 0
    QLocalServer.removeServer(SOCKET_NAME)
    server = QLocalServer()
    server.listen(SOCKET_NAME)

    backend = Backend()
    engine = QQmlApplicationEngine()
    warnings = []

    def on_warnings(ws):
        for w in ws:
            warnings.append(w.toString())
            print("QML:", w.toString(), file=sys.stderr)
    engine.warnings.connect(on_warnings)
    engine.rootContext().setContextProperty("backend", backend)
    engine.rootContext().setContextProperty("astraAccent", accent())
    engine.load(QUrl.fromLocalFile(os.path.join(HERE, "qml", "Main.qml")))
    if not engine.rootObjects():
        return 1
    window = engine.rootObjects()[0]

    def show_window():
        window.show()
        window.raise_()
        window.requestActivate()

    def on_connection():
        sock = server.nextPendingConnection()
        sock.waitForReadyRead(300)
        data = bytes(sock.readAll()).decode(errors="replace")
        show_window()
        if data.startswith("search:"):
            QMetaObject.invokeMethod(window, "setSearch", Q_ARG("QVariant", data.split(":", 1)[1]))
    server.newConnection.connect(on_connection)

    backend.start()
    if check_only:
        window.show()
        QTimer.singleShot(2500, app.quit)
        app.exec()
        print("QML OK" if not warnings else f"QML: предупреждений {len(warnings)}")
        backend.shutdown()
        del window, engine
        return 1 if warnings else 0

    show_window()
    if arg:
        data = "search:" + arg
        QTimer.singleShot(400, lambda: QMetaObject.invokeMethod(window, "setSearch", Q_ARG("QVariant", data.split(":", 1)[1])))
    if screenshot:
        def grab():
            window.grabWindow().save(screenshot)
            app.quit()
        QTimer.singleShot(int(os.environ.get("ASTRAMARS_STORE_SHOT_DELAY", "3000")), grab)
        if os.environ.get("ASTRAMARS_STORE_SHOT_INSTALL"):
            delay = int(os.environ.get("ASTRAMARS_STORE_SHOT_DELAY", "3000"))
            QTimer.singleShot(max(300, delay - 650), lambda: backend.install(os.environ["ASTRAMARS_STORE_SHOT_INSTALL"]))
        if os.environ.get("ASTRAMARS_STORE_SHOT_CATEGORY"):
            QTimer.singleShot(200, lambda: backend.setCategory(os.environ["ASTRAMARS_STORE_SHOT_CATEGORY"]))
        if os.environ.get("ASTRAMARS_STORE_SHOT_ACTION"):
            delay = int(os.environ.get("ASTRAMARS_STORE_SHOT_DELAY", "3000"))
            QTimer.singleShot(max(300, delay - 1200), getattr(backend, os.environ["ASTRAMARS_STORE_SHOT_ACTION"]))
        if os.environ.get("ASTRAMARS_STORE_SHOT_QUERY"):
            QTimer.singleShot(300, lambda: backend.setQuery(os.environ["ASTRAMARS_STORE_SHOT_QUERY"]))

    code = app.exec()
    backend.shutdown()
    del window, engine
    return code


if __name__ == "__main__":
    sys.exit(main())
