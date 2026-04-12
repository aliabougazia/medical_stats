"""
MedStat Pro – Advanced Medical Research Statistical Analysis
Entry point: sets matplotlib backend before any other import.
"""
import sys
import os
import traceback

os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")

import matplotlib
matplotlib.use("QtAgg")

from PyQt6.QtWidgets import QApplication, QSplashScreen
from PyQt6.QtGui import QFont, QPixmap, QColor, QPainter, QLinearGradient
from PyQt6.QtCore import Qt, QTimer


def _make_splash() -> QSplashScreen:
    pix = QPixmap(480, 260)
    pix.fill(QColor("#0f172a"))
    painter = QPainter(pix)
    grad = QLinearGradient(0, 0, 480, 0)
    grad.setColorAt(0, QColor("#0ea5e9"))
    grad.setColorAt(1, QColor("#8b5cf6"))
    painter.setPen(QColor(0, 0, 0, 0))
    painter.setBrush(grad)
    painter.drawRect(0, 220, 480, 8)
    f = QFont("Segoe UI", 22, QFont.Weight.Bold)
    painter.setFont(f)
    painter.setPen(QColor("#f1f5f9"))
    painter.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, "MedStat Pro")
    f2 = QFont("Segoe UI", 10)
    painter.setFont(f2)
    painter.setPen(QColor("#94a3b8"))
    painter.drawText(0, 180, 480, 30, Qt.AlignmentFlag.AlignCenter,
                     "Advanced Medical Research Statistical Analysis")
    painter.end()
    return QSplashScreen(pix)


def _global_excepthook(exc_type, exc_value, exc_tb):
    """Show a QMessageBox for any uncaught exception instead of crashing."""
    msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    brief = str(exc_value) if str(exc_value) else exc_type.__name__
    try:
        from PyQt6.QtWidgets import QMessageBox
        box = QMessageBox()
        box.setWindowTitle("Unexpected Error")
        box.setIcon(QMessageBox.Icon.Critical)
        box.setText(f"An unexpected error occurred:\n\n{brief}")
        box.setDetailedText(msg)
        box.setStandardButtons(QMessageBox.StandardButton.Ok)
        box.exec()
    except Exception:
        print(msg, file=sys.stderr)


def main():
    sys.excepthook = _global_excepthook
    app = QApplication(sys.argv)
    app.setApplicationName("MedStat Pro")
    app.setApplicationVersion("1.0.0")
    app.setFont(QFont("Segoe UI", 10))

    splash = _make_splash()
    splash.show()
    app.processEvents()

    from app.main_window import MainWindow
    window = MainWindow()

    QTimer.singleShot(1200, lambda: (splash.close(), window.show()))
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
