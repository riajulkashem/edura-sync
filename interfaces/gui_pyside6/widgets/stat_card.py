# interfaces/gui_pyside6/widgets/stat_card.py
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from interfaces.gui_pyside6.theme import tokens, RADIUS_MD, SPACE_MD


class StatCard(QFrame):
    """
    A compact stat card showing a large number and a label.
    tone: 'neutral' | 'success' | 'warning' | 'danger'
    """

    def __init__(self, value: str = "0", label: str = "", tone: str = "neutral", parent=None):
        super().__init__(parent)
        self._tone = tone
        self.setObjectName("StatCard")
        self.setMinimumWidth(120)
        self.setMinimumHeight(72)
        self.setFrameShape(QFrame.Shape.StyledPanel)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACE_MD, SPACE_MD, SPACE_MD, SPACE_MD)
        layout.setSpacing(2)

        self._value_label = QLabel(value)
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self._text_label = QLabel(label)
        self._text_label.setAlignment(Qt.AlignmentFlag.AlignLeft)

        layout.addWidget(self._value_label)
        layout.addWidget(self._text_label)
        layout.addStretch()

        self._apply_style()

    def set_value(self, value: str) -> None:
        self._value_label.setText(value)

    def set_tone(self, tone: str) -> None:
        self._tone = tone
        self._apply_style()

    def _apply_style(self) -> None:
        t = tokens()
        stripe_color = {
            "success": t["success"],
            "warning": t["warning"],
            "danger":  t["danger"],
        }.get(self._tone, t["accent"])

        self.setStyleSheet(f"""
            QFrame#StatCard {{
                background-color: {t['bg_surface']};
                border: 1px solid {t['border']};
                border-left: 3px solid {stripe_color};
                border-radius: {RADIUS_MD}px;
            }}
        """)
        self._value_label.setStyleSheet(
            f"font-size: 26px; font-weight: 700; color: {t['text_primary']}; background: transparent;"
        )
        self._text_label.setStyleSheet(
            f"font-size: 11px; color: {t['text_secondary']}; background: transparent;"
        )
