"""Ygolek VPN — точка входа."""

import os
import signal
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtCore import Q_ARG, QMetaObject, QTimer, QUrl  # noqa: E402
from PySide6.QtGui import QAction, QIcon  # noqa: E402
from PySide6.QtNetwork import QLocalServer, QLocalSocket  # noqa: E402
from PySide6.QtQml import QQmlApplicationEngine  # noqa: E402
from PySide6.QtQuickControls2 import QQuickStyle  # noqa: E402
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon  # noqa: E402

from astramars_vpn.backend import Backend  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SOCKET_NAME = f"ygolek-vpn-{os.environ.get('USER') or os.environ.get('USERNAME') or 'user'}"


def app_icon() -> QIcon:
    icon = QIcon.fromTheme("ygolek-vpn")
    if icon.isNull():
        icon = QIcon(os.path.join(HERE, "qml", "assets", "icon.svg"))
    return icon


def main():
    minimized = "--minimized" in sys.argv
    check_only = "--check" in sys.argv
    screenshot = None
    if "--screenshot" in sys.argv:
        screenshot = sys.argv[sys.argv.index("--screenshot") + 1]

    QQuickStyle.setStyle("Basic")
    app = QApplication(sys.argv)
    app.setApplicationName("ygolek-vpn")
    app.setApplicationDisplayName("Ygolek VPN")
    app.setDesktopFileName("ygolek-vpn")
    app.setWindowIcon(app_icon())
    app.setQuitOnLastWindowClosed(False)
    font = app.font()
    font.setFamily("Inter")
    app.setFont(font)
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Один экземпляр: повторный запуск просто показывает окно
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
    qml_warnings = []

    def on_warnings(ws):
        for w in ws:
            qml_warnings.append(w.toString())
            print("QML:", w.toString(), file=sys.stderr)
    engine.warnings.connect(on_warnings)
    engine.rootContext().setContextProperty("backend", backend)
    engine.load(QUrl.fromLocalFile(os.path.join(HERE, "qml", "Main.qml")))
    if not engine.rootObjects():
        return 1
    window = engine.rootObjects()[0]

    if check_only:
        # Проверка при сборке образа: интерфейс загружается без единого предупреждения
        for name in ("add", "settings"):
            QMetaObject.invokeMethod(window, "openPanel", Q_ARG("QVariant", name))
        QTimer.singleShot(1500, app.quit)
        app.exec()
        print("QML OK" if not qml_warnings else f"QML: предупреждений {len(qml_warnings)}")
        del window
        del engine
        return 1 if qml_warnings else 0

    def show_window():
        window.show()
        window.raise_()
        window.requestActivate()

    server.newConnection.connect(lambda: (server.nextPendingConnection(), show_window()))
    backend.showWindowRequested.connect(show_window)

    # Значок в трее
    tray = None
    if QSystemTrayIcon.isSystemTrayAvailable():
        tray = QSystemTrayIcon(app_icon())
        menu = QMenu()
        act_show = QAction("Открыть Ygolek VPN", menu, triggered=show_window)
        act_toggle = QAction("Подключить", menu, triggered=backend.toggleConnection)
        act_quit = QAction("Выйти", menu, triggered=app.quit)
        menu.addAction(act_show)
        menu.addAction(act_toggle)
        menu.addSeparator()
        menu.addAction(act_quit)
        tray.setContextMenu(menu)

        def update_tray():
            on = backend.status == "on"
            act_toggle.setText("Отключить" if backend.status in ("on", "connecting") else "Подключить")
            name = backend.current.get("name", "")
            tray.setToolTip(f"Ygolek VPN — {'подключено: ' + name if on else 'отключено'}")
        backend.statusChanged.connect(update_tray)
        backend.selectedChanged.connect(update_tray)
        update_tray()
        tray.activated.connect(lambda reason: show_window() if reason == QSystemTrayIcon.Trigger else None)
        tray.show()
    window.setProperty("hideOnClose", tray is not None)

    if screenshot:
        window.show()
        panel = os.environ.get("ASTRAMARS_VPN_SHOT_PANEL")
        if panel:
            QTimer.singleShot(800, lambda: QMetaObject.invokeMethod(window, "openPanel", Q_ARG("QVariant", panel)))

        def grab():
            window.grabWindow().save(screenshot)
            app.quit()
        QTimer.singleShot(int(os.environ.get("ASTRAMARS_VPN_SHOT_DELAY", "2500")), grab)
    elif not minimized:
        window.show()

    backend.start()
    app.aboutToQuit.connect(backend.shutdown)
    code = app.exec()
    # Сначала интерфейс, потом логика: иначе QML успевает обратиться к удалённому backend
    del window
    del engine
    return code


if __name__ == "__main__":
    sys.exit(main())
