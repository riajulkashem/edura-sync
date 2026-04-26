# interfaces/gui_pyside6/widgets/spinner.py
from PySide6.QtWidgets import QLabel
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QTransform, QPixmap, QPainter, QColor
from interfaces.gui_pyside6.theme import tokens


class Spinner(QLabel):
    """
    A lightweight rotating spinner rendered from a unicode arrow character.
    Uses QTimer + QTransform — no external assets needed.
    """
    _FRAMES = ["◐", "◓", "○", "◑", "◒", "●"]  # Unicode cycle frames

    def __init__(self, size: int = 14, parent=None):
        super().__init__(parent)
        self._size = size
        self._frame = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t = tokens()
        self.setStyleSheet(f"color: {t['accent']}; font-size: {size}px; background: transparent;")
        self.setText(self._FRAMES[0])
        self.hide()

    def start(self) -> None:
        self.show()
        self._timer.start(100)

    def stop(self) -> None:
        self._timer.stop()
        self.hide()

    def _tick(self) -> None:
        self._frame = (self._frame + 1) % len(self._FRAMES)
        self.setText(self._FRAMES[self._frame])
