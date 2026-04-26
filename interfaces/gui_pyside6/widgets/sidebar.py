# interfaces/gui_pyside6/widgets/sidebar.py
import sys
from pathlib import Path
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFrame
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QIcon
from interfaces.gui_pyside6.theme import tokens, SIDEBAR_WIDTH, SPACE_SM, SPACE_MD, SPACE_LG


def _logo_path() -> str | None:
    """Return absolute path to assets/logo.png, works for source and frozen builds."""
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parents[3]  # project root
    p = base / "assets" / "logo.png"
    return str(p) if p.exists() else None


class _NavItem(QPushButton):
    def __init__(self, icon: str, label: str, parent=None):
        super().__init__(parent)
        self._icon_text = icon
        self._label = label
        self.setCheckable(True)
        self.setFlat(True)
        self.setFixedHeight(36)
        self.setText(f"  {icon}  {label}")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_style(False)

    def setChecked(self, checked: bool) -> None:
        super().setChecked(checked)
        self._apply_style(checked)

    def _apply_style(self, active: bool) -> None:
        t = tokens()
        if active:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {t['accent_muted']};
                    color: {t['accent']};
                    border: none;
                    border-left: 3px solid {t['accent']};
                    border-radius: 0px;
                    text-align: left;
                    padding-left: {SPACE_MD}px;
                    font-size: 12px;
                    font-weight: 600;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {t['text_secondary']};
                    border: none;
                    border-left: 3px solid transparent;
                    border-radius: 0px;
                    text-align: left;
                    padding-left: {SPACE_MD}px;
                    font-size: 12px;
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    background-color: {t['bg_subtle']};
                    color: {t['text_primary']};
                }}
            """)


class SidebarWidget(QWidget):
    """Vertical navigation sidebar. Emits page_changed(index) on nav item click."""

    page_changed = Signal(int)

    NAV_ITEMS = [
        ("  Dashboard",   0),
        ("  Devices",     1),
        ("  Attendance",  2),
        ("  Settings",    3),
    ]
    BOTTOM_ITEMS = [
        ("  About",       4),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(SIDEBAR_WIDTH)
        self.setObjectName("Sidebar")
        self._buttons: list[_NavItem] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        t = tokens()
        self.setStyleSheet(f"""
            QWidget#Sidebar {{
                background-color: {t['bg_surface']};
                border-right: 1px solid {t['border']};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Logo area
        header = QWidget()
        header.setFixedHeight(64)
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(SPACE_LG, SPACE_SM, SPACE_LG, SPACE_SM)
        header_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        logo_file = _logo_path()
        if logo_file:
            logo_lbl = QLabel()
            pix = QPixmap(logo_file)
            logo_lbl.setPixmap(
                pix.scaled(
                    SIDEBAR_WIDTH - SPACE_LG * 2, 44,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            logo_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            logo_lbl.setStyleSheet("background: transparent;")
            header_layout.addWidget(logo_lbl)
        else:
            # Fallback text if logo file is missing
            app_name = QLabel("EduraSync")
            app_name.setStyleSheet(
                f"font-size: 15px; font-weight: 700; color: {t['text_primary']}; background: transparent;"
            )
            header_layout.addWidget(app_name)

        layout.addWidget(header)

        # Top separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background-color: {t['border']}; border: none; max-height: 1px;")
        layout.addWidget(sep)

        layout.addSpacing(SPACE_SM)

        # Nav items
        for label, index in self.NAV_ITEMS:
            btn = _NavItem("", label.strip(), self)
            btn.setText(label)
            btn.clicked.connect(lambda _, i=index: self._on_click(i))
            self._buttons.append(btn)
            layout.addWidget(btn)

        layout.addStretch()

        # Bottom separator
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet(f"background-color: {t['border']}; border: none; max-height: 1px;")
        layout.addWidget(sep2)

        for label, index in self.BOTTOM_ITEMS:
            btn = _NavItem("", label.strip(), self)
            btn.setText(label)
            btn.clicked.connect(lambda _, i=index: self._on_click(i))
            self._buttons.append(btn)
            layout.addWidget(btn)

        layout.addSpacing(SPACE_SM)

        # Default: Dashboard selected
        self.set_active(0)

    def _on_click(self, index: int) -> None:
        self.set_active(index)
        self.page_changed.emit(index)

    def set_active(self, index: int) -> None:
        for btn in self._buttons:
            # Each button tracks its own index via closure — match by page_changed order
            pass
        # Re-implement: find button by iterating nav+bottom items
        all_items = self.NAV_ITEMS + self.BOTTOM_ITEMS
        for i, (btn, (_, idx)) in enumerate(zip(self._buttons, all_items)):
            btn.setChecked(idx == index)
