# interfaces/gui_pyside6/theme.py
"""
Design system for EduraSync.
All colours, spacing, and typography in one place.
Apply once at startup via apply_theme(QApplication).
"""
from __future__ import annotations

from PySide6.QtGui import QColor, QPalette, QFont
from PySide6.QtWidgets import QApplication


# ── Spacing tokens ────────────────────────────────────────────────────────────
SPACE_XS  = 4
SPACE_SM  = 8
SPACE_MD  = 12
SPACE_LG  = 16
SPACE_XL  = 24
SPACE_2XL = 32

RADIUS_SM = 4
RADIUS_MD = 6
RADIUS_LG = 8

SIDEBAR_WIDTH  = 200
WINDOW_MIN_W   = 960
WINDOW_MIN_H   = 640


# ── Palette definitions ───────────────────────────────────────────────────────
_LIGHT = {
    "bg_base":        "#F8F9FA",
    "bg_surface":     "#FFFFFF",
    "bg_subtle":      "#F1F3F5",
    "border":         "#DEE2E6",
    "text_primary":   "#212529",
    "text_secondary": "#6C757D",
    "text_disabled":  "#ADB5BD",
    "accent":         "#228BE6",
    "accent_hover":   "#1C7ED6",
    "accent_muted":   "#E7F5FF",
    "success":        "#2F9E44",
    "success_bg":     "#EBFBEE",
    "warning":        "#E67700",
    "warning_bg":     "#FFF9DB",
    "danger":         "#C92A2A",
    "danger_bg":      "#FFF5F5",
}

_DARK = {
    "bg_base":        "#1A1B1E",
    "bg_surface":     "#25262B",
    "bg_subtle":      "#2C2E33",
    "border":         "#373A40",
    "text_primary":   "#C1C2C5",
    "text_secondary": "#868E96",
    "text_disabled":  "#5C5F66",
    "accent":         "#4DABF7",
    "accent_hover":   "#74C0FC",
    "accent_muted":   "#1864AB",
    "success":        "#51CF66",
    "success_bg":     "#1B3D2A",
    "warning":        "#FFD43B",
    "warning_bg":     "#3D3010",
    "danger":         "#FF6B6B",
    "danger_bg":      "#3D1010",
}


def _is_dark(app: QApplication) -> bool:
    """Return True when the host OS is in dark mode."""
    try:
        # Qt 6.5+
        hints = app.styleHints()
        scheme = hints.colorScheme()
        from PySide6.QtCore import Qt
        return scheme == Qt.ColorScheme.Dark
    except AttributeError:
        # Fallback: check window background lightness
        c = app.palette().color(QPalette.ColorRole.Window)
        return c.lightness() < 128


def tokens(app: QApplication | None = None) -> dict:
    """Return the active colour token dict for the current OS theme."""
    if app is None:
        app = QApplication.instance()
    return _DARK if (app and _is_dark(app)) else _LIGHT


def _build_palette(t: dict) -> QPalette:
    p = QPalette()
    p.setColor(QPalette.ColorRole.Window,          QColor(t["bg_base"]))
    p.setColor(QPalette.ColorRole.WindowText,      QColor(t["text_primary"]))
    p.setColor(QPalette.ColorRole.Base,            QColor(t["bg_surface"]))
    p.setColor(QPalette.ColorRole.AlternateBase,   QColor(t["bg_subtle"]))
    p.setColor(QPalette.ColorRole.Text,            QColor(t["text_primary"]))
    p.setColor(QPalette.ColorRole.BrightText,      QColor(t["text_primary"]))
    p.setColor(QPalette.ColorRole.ButtonText,      QColor(t["text_primary"]))
    p.setColor(QPalette.ColorRole.Button,          QColor(t["bg_surface"]))
    p.setColor(QPalette.ColorRole.Highlight,       QColor(t["accent"]))
    p.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
    p.setColor(QPalette.ColorRole.PlaceholderText, QColor(t["text_disabled"]))
    p.setColor(QPalette.ColorRole.ToolTipBase,     QColor(t["bg_surface"]))
    p.setColor(QPalette.ColorRole.ToolTipText,     QColor(t["text_primary"]))
    # Disabled group
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(t["text_disabled"]))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text,       QColor(t["text_disabled"]))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(t["text_disabled"]))
    return p


def _build_stylesheet(t: dict) -> str:
    return f"""
/* ── Base ── */
QMainWindow, QDialog, QWidget {{
    background-color: {t['bg_base']};
    color: {t['text_primary']};
    font-size: 12px;
}}

/* ── Inputs ── */
QLineEdit, QSpinBox, QTimeEdit, QComboBox {{
    background-color: {t['bg_surface']};
    color: {t['text_primary']};
    border: 1px solid {t['border']};
    border-radius: {RADIUS_MD}px;
    padding: 4px 8px;
    min-height: 28px;
    selection-background-color: {t['accent_muted']};
}}
QLineEdit:focus, QSpinBox:focus, QTimeEdit:focus, QComboBox:focus {{
    border: 2px solid {t['accent']};
}}
QLineEdit:disabled, QSpinBox:disabled, QTimeEdit:disabled, QComboBox:disabled {{
    background-color: {t['bg_subtle']};
    color: {t['text_disabled']};
    border-color: {t['border']};
}}
QComboBox::drop-down {{
    border: none;
    padding-right: 8px;
}}
QComboBox QAbstractItemView {{
    background-color: {t['bg_surface']};
    border: 1px solid {t['border']};
    selection-background-color: {t['accent_muted']};
    selection-color: {t['accent']};
}}

/* ── Buttons ── */
QPushButton {{
    background-color: {t['bg_surface']};
    color: {t['text_primary']};
    border: 1px solid {t['border']};
    border-radius: {RADIUS_MD}px;
    padding: 5px 14px;
    min-height: 28px;
    font-size: 12px;
    font-weight: 500;
}}
QPushButton:hover  {{ background-color: {t['bg_subtle']}; border-color: {t['text_disabled']}; }}
QPushButton:pressed {{ background-color: {t['bg_subtle']}; }}
QPushButton:disabled {{ background-color: {t['bg_subtle']}; color: {t['text_disabled']}; border-color: {t['border']}; }}

QPushButton[variant="primary"] {{
    background-color: {t['accent']};
    color: #FFFFFF;
    border: none;
}}
QPushButton[variant="primary"]:hover   {{ background-color: {t['accent_hover']}; }}
QPushButton[variant="primary"]:pressed {{ background-color: {t['accent_hover']}; }}
QPushButton[variant="primary"]:disabled {{ background-color: {t['text_disabled']}; color: #FFFFFF; }}

QPushButton[variant="danger"] {{
    background-color: {t['bg_surface']};
    color: {t['danger']};
    border: 1px solid {t['danger']};
}}
QPushButton[variant="danger"]:hover {{ background-color: {t['danger_bg']}; }}

QPushButton[variant="ghost"] {{
    background-color: transparent;
    color: {t['accent']};
    border: none;
    padding: 4px 8px;
}}
QPushButton[variant="ghost"]:hover {{ background-color: {t['accent_muted']}; }}

/* ── Tables ── */
QTableWidget, QTableView {{
    background-color: {t['bg_surface']};
    alternate-background-color: {t['bg_subtle']};
    gridline-color: {t['border']};
    border: 1px solid {t['border']};
    border-radius: {RADIUS_LG}px;
    selection-background-color: {t['accent_muted']};
    selection-color: {t['text_primary']};
}}
QTableWidget::item, QTableView::item {{
    padding: 6px 8px;
    border: none;
}}
QHeaderView::section {{
    background-color: {t['bg_subtle']};
    color: {t['text_secondary']};
    border: none;
    border-bottom: 1px solid {t['border']};
    padding: 6px 8px;
    font-weight: 600;
    font-size: 11px;
}}
QTableWidget::item:selected, QTableView::item:selected {{
    background-color: {t['accent_muted']};
    color: {t['text_primary']};
}}

/* ── Scroll bars ── */
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {t['border']};
    border-radius: 4px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{ background: {t['text_disabled']}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: transparent;
    height: 8px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: {t['border']};
    border-radius: 4px;
    min-width: 24px;
}}
QScrollBar::handle:horizontal:hover {{ background: {t['text_disabled']}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* ── GroupBox ── */
QGroupBox {{
    border: 1px solid {t['border']};
    border-radius: {RADIUS_LG}px;
    margin-top: 14px;
    padding: {SPACE_MD}px;
    font-weight: 600;
    font-size: 12px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    color: {t['text_secondary']};
}}

/* ── Tab widget ── */
QTabWidget::pane {{
    border: 1px solid {t['border']};
    border-radius: {RADIUS_LG}px;
    background-color: {t['bg_surface']};
}}
QTabBar::tab {{
    background: transparent;
    color: {t['text_secondary']};
    padding: 8px 16px;
    font-weight: 600;
    font-size: 12px;
    border-bottom: 2px solid transparent;
}}
QTabBar::tab:selected {{
    color: {t['accent']};
    border-bottom: 2px solid {t['accent']};
}}
QTabBar::tab:hover:!selected {{ color: {t['text_primary']}; }}

/* ── Splitter ── */
QSplitter::handle {{
    background-color: {t['border']};
    width: 1px;
    height: 1px;
}}

/* ── Status bar ── */
QStatusBar {{
    background-color: {t['bg_base']};
    border-top: 1px solid {t['border']};
    color: {t['text_secondary']};
    font-size: 11px;
}}

/* ── ToolTip ── */
QToolTip {{
    background-color: {t['bg_surface']};
    color: {t['text_primary']};
    border: 1px solid {t['border']};
    border-radius: {RADIUS_SM}px;
    padding: 4px 8px;
    font-size: 11px;
}}

/* ── Progress bar ── */
QProgressBar {{
    background-color: {t['bg_subtle']};
    border: 1px solid {t['border']};
    border-radius: {RADIUS_SM}px;
    text-align: center;
    font-size: 10px;
    color: {t['text_secondary']};
    max-height: 6px;
}}
QProgressBar::chunk {{
    background-color: {t['accent']};
    border-radius: {RADIUS_SM}px;
}}

/* ── CheckBox ── */
QCheckBox {{
    color: {t['text_primary']};
    spacing: 8px;
    font-size: 12px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {t['border']};
    border-radius: 4px;
    background: {t['bg_surface']};
}}
QCheckBox::indicator:checked {{
    background-color: {t['accent']};
    border-color: {t['accent']};
}}
QCheckBox::indicator:hover {{ border-color: {t['accent']}; }}

/* ── Menu ── */
QMenu {{
    background-color: {t['bg_surface']};
    border: 1px solid {t['border']};
    border-radius: {RADIUS_MD}px;
    padding: 4px;
}}
QMenu::item {{
    padding: 6px 20px;
    border-radius: {RADIUS_SM}px;
    color: {t['text_primary']};
}}
QMenu::item:selected {{ background-color: {t['accent_muted']}; color: {t['accent']}; }}
QMenu::separator {{ height: 1px; background: {t['border']}; margin: 4px 8px; }}

/* ── MessageBox ── */
QMessageBox {{ background-color: {t['bg_surface']}; }}
QMessageBox QLabel {{ color: {t['text_primary']}; }}

/* ── QCalendarWidget ─────────────────────────────────────────────────────────
   Only a minimal reset here. Each QDateEdit instance receives a full
   standalone stylesheet via calendarWidget().setStyleSheet() in code,
   which completely overrides the app-level sheet for its widget tree.
   This block just ensures no global rule makes the calendar invisible. */
QCalendarWidget QProgressBar {{
    max-height: none;
    min-height: 4px;
}}
"""


def apply_theme(app: QApplication) -> None:
    """Apply palette + stylesheet to the application. Call once after QApplication creation."""
    t = tokens(app)
    app.setPalette(_build_palette(t))
    app.setStyleSheet(_build_stylesheet(t))

    # System UI font
    font = QFont()
    import sys
    if sys.platform.startswith("win"):
        font.setFamily("Segoe UI")
    elif sys.platform == "darwin":
        font.setFamily("-apple-system")
    else:
        font.setFamily("Ubuntu")
    font.setPointSize(9)
    app.setFont(font)
