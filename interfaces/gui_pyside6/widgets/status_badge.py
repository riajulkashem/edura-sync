# interfaces/gui_pyside6/widgets/status_badge.py
from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt
from interfaces.gui_pyside6.theme import tokens, RADIUS_SM


class StatusBadge(QLabel):
    """
    Small pill label with semantic colour.
    tone: 'success' | 'warning' | 'danger' | 'info' | 'neutral'
    """

    SYMBOLS = {
        "success": "●",
        "warning": "◐",
        "danger":  "○",
        "info":    "↻",
        "neutral": "–",
    }

    def __init__(self, text: str = "", tone: str = "neutral", parent=None):
        super().__init__(parent)
        self._tone = tone
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.update_badge(text, tone)

    def update_badge(self, text: str, tone: str) -> None:
        self._tone = tone
        symbol = self.SYMBOLS.get(tone, "")
        self.setText(f"{symbol} {text}" if symbol else text)
        self._apply_style()

    def _apply_style(self) -> None:
        t = tokens()
        bg, fg = {
            "success": (t["success_bg"], t["success"]),
            "warning": (t["warning_bg"], t["warning"]),
            "danger":  (t["danger_bg"],  t["danger"]),
            "info":    (t["accent_muted"], t["accent"]),
            "neutral": (t["bg_subtle"],  t["text_secondary"]),
        }.get(self._tone, (t["bg_subtle"], t["text_secondary"]))

        self.setStyleSheet(f"""
            QLabel {{
                background-color: {bg};
                color: {fg};
                border-radius: {RADIUS_SM}px;
                padding: 2px 8px;
                font-size: 11px;
                font-weight: 600;
            }}
        """)
