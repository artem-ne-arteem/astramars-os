"""Быстрые действия AstraMars — точка входа."""

import os
import signal
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtCore import Q_ARG, QMetaObject, QTimer, QUrl  # noqa: E402
from PySide6.QtGui import QGuiApplication, QIcon  # noqa: E402
from PySide6.QtNetwork import QLocalServer, QLocalSocket  # noqa: E402
from PySide6.QtQml import QQmlApplicationEngine  # noqa: E402
from PySide6.QtQuickControls2 import QQuickStyle  # noqa: E402

from astramars_actions.backend import Backend  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SOCKET_NAME = f"astramars-actions-{os.environ.get('USER') or os.environ.get('USERNAME') or 'user'}"


def main():
    check_only = "--check" in sys.argv
    screenshot = sys.argv[sys.argv.index("--screenshot") + 1] if "--screenshot" in sys.argv else None

    QQuickStyle.setStyle("Basic")
    app = QGuiApplication(sys.argv)
    app.setApplicationName("astramars-actions")
    app.setApplicationDisplayName("Быстрые действия")
    app.setDesktopFileName("astramars-actions")
    app.setWindowIcon(QIcon.fromTheme("astramars-actions"))
    font = app.font()
    font.setFamily("Inter")
    app.setFont(font)
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    probe = QLocalSocket()
    probe.connectToServer(SOCKET_NAME)
    if not check_only and probe.waitForConnected(300):
        probe.write(b"show")
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
    engine.load(QUrl.fromLocalFile(os.path.join(HERE, "qml", "Main.qml")))
    if not engine.rootObjects():
        return 1
    window = engine.rootObjects()[0]

    def show_window():
        window.show()
        window.raise_()
        window.requestActivate()
    server.newConnection.connect(lambda: (server.nextPendingConnection(), show_window()))

    if check_only:
        # Проверка при сборке: окно, все плитки, запуск действия и редактор — без предупреждений QML
        window.show()
        QTimer.singleShot(300, lambda: backend.run("space"))
        QTimer.singleShot(600, lambda: QMetaObject.invokeMethod(window, "openPanel", Q_ARG("QVariant", "editor")))
        QTimer.singleShot(2500, app.quit)
        app.exec()
        print("QML OK" if not warnings else f"QML: предупреждений {len(warnings)}")
        backend.shutdown()
        del window, engine
        return 1 if warnings else 0

    show_window()
    if screenshot:
        for item in filter(None, os.environ.get("ASTRAMARS_ACTIONS_SHOT_RUN", "").split(",")):
            QTimer.singleShot(400, lambda i=item: backend.run(i))
        if os.environ.get("ASTRAMARS_ACTIONS_SHOT_PANEL"):
            QTimer.singleShot(500, lambda: QMetaObject.invokeMethod(
                window, "openPanel", Q_ARG("QVariant", os.environ["ASTRAMARS_ACTIONS_SHOT_PANEL"])))

        def grab():
            window.grabWindow().save(screenshot)
            app.quit()
        QTimer.singleShot(int(os.environ.get("ASTRAMARS_ACTIONS_SHOT_DELAY", "2500")), grab)

    code = app.exec()
    backend.shutdown()
    del window, engine
    return code


if __name__ == "__main__":
    sys.exit(main())
