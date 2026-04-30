# interfaces/gui_pyside6/screens/about_screen.py
"""
About screen — company info, contact support, and interactive user manual.
© Softzenix IT. All rights reserved.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QPushButton, QSizePolicy, QTabWidget,
    QScrollArea, QApplication,
)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QPixmap, QCursor

from core.constants import APP_NAME, APP_VERSION
from interfaces.gui_pyside6.theme import (
    tokens, SPACE_LG, SPACE_MD, SPACE_SM, SPACE_XL, RADIUS_MD,
)


def _logo_path() -> str | None:
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parents[3]
    p = base / "assets" / "logo.png"
    return str(p) if p.exists() else None


# ── Reusable helpers ──────────────────────────────────────────────────────────

class _CopyButton(QPushButton):
    """Small inline button that copies text to clipboard."""
    def __init__(self, value: str, parent=None):
        super().__init__("Copy", parent)
        self._value = value
        self.setFixedWidth(50)
        self.setFixedHeight(22)
        self.setProperty("variant", "ghost")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.clicked.connect(self._copy)
        t = tokens()
        self.setStyleSheet(
            f"font-size: 10px; color: {t['accent']}; border: none; "
            f"background: transparent; padding: 0 4px;"
        )

    def _copy(self) -> None:
        QApplication.clipboard().setText(self._value)
        self.setText("✓")
        from PySide6.QtCore import QTimer
        QTimer.singleShot(1500, lambda: self.setText("Copy"))


def _contact_row(label: str, value: str, link: str | None = None) -> QHBoxLayout:
    """Build a label + value + optional copy/open-link row."""
    t = tokens()
    row = QHBoxLayout()
    row.setSpacing(SPACE_SM)

    lbl = QLabel(label)
    lbl.setFixedWidth(80)
    lbl.setStyleSheet(f"color: {t['text_secondary']}; font-size: 12px; background: transparent;")
    row.addWidget(lbl)

    val = QLabel(value)
    val.setStyleSheet(f"color: {t['text_primary']}; font-size: 12px; font-weight: 600; background: transparent;")
    val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    row.addWidget(val, stretch=1)

    if link:
        open_btn = QPushButton("Open")
        open_btn.setFixedWidth(50)
        open_btn.setFixedHeight(22)
        open_btn.setProperty("variant", "ghost")
        open_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        _url = link
        open_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(_url)))
        t2 = tokens()
        open_btn.setStyleSheet(
            f"font-size: 10px; color: {t2['accent']}; border: none; background: transparent; padding: 0 4px;"
        )
        row.addWidget(open_btn)

    copy_btn = _CopyButton(value)
    row.addWidget(copy_btn)
    return row


class _Accordion(QWidget):
    """
    Collapsible accordion section.
    Header is a clickable button; body is shown/hidden on click.
    """
    def __init__(self, title: str, body_widget: QWidget, parent=None):
        super().__init__(parent)
        t = tokens()
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header button
        self._btn = QPushButton(f"▶  {title}")
        self._btn.setCheckable(True)
        self._btn.setChecked(False)
        self._btn.setFlat(True)
        self._btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {t['bg_subtle']};
                color: {t['text_primary']};
                border: 1px solid {t['border']};
                border-radius: {RADIUS_MD}px;
                text-align: left;
                padding: 8px 14px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:checked {{
                background-color: {t['accent_muted']};
                color: {t['accent']};
                border-color: {t['accent']};
                border-bottom-left-radius: 0px;
                border-bottom-right-radius: 0px;
            }}
            QPushButton:hover:!checked {{
                background-color: {t['bg_subtle']};
                border-color: {t['text_disabled']};
            }}
        """)
        self._btn.toggled.connect(self._toggle)
        root.addWidget(self._btn)

        # Body container
        self._body_container = QFrame()
        self._body_container.setVisible(False)
        self._body_container.setStyleSheet(
            f"background-color: {t['bg_surface']}; "
            f"border: 1px solid {t['accent']}; "
            f"border-top: none; "
            f"border-bottom-left-radius: {RADIUS_MD}px; "
            f"border-bottom-right-radius: {RADIUS_MD}px;"
        )
        body_layout = QVBoxLayout(self._body_container)
        body_layout.setContentsMargins(SPACE_MD, SPACE_MD, SPACE_MD, SPACE_MD)
        body_layout.addWidget(body_widget)
        root.addWidget(self._body_container)

    def _toggle(self, checked: bool) -> None:
        icon = "▼" if checked else "▶"
        text = self._btn.text()[2:]  # strip old icon + space
        self._btn.setText(f"{icon}  {text}")
        self._body_container.setVisible(checked)


def _manual_body(steps: list[str]) -> QWidget:
    """Build a body widget containing numbered step labels."""
    t = tokens()
    w = QWidget()
    lv = QVBoxLayout(w)
    lv.setContentsMargins(0, 0, 0, 0)
    lv.setSpacing(SPACE_SM)
    for i, step in enumerate(steps, 1):
        row = QHBoxLayout()
        num = QLabel(f"{i}.")
        num.setFixedWidth(20)
        num.setAlignment(Qt.AlignmentFlag.AlignTop)
        num.setStyleSheet(
            f"color: {t['accent']}; font-weight: 700; font-size: 12px; background: transparent;"
        )
        txt = QLabel(step)
        txt.setWordWrap(True)
        txt.setStyleSheet(f"color: {t['text_primary']}; font-size: 12px; background: transparent;")
        txt.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        row.addWidget(num)
        row.addWidget(txt, stretch=1)
        lv.addLayout(row)
    return w


# ── Main screen ───────────────────────────────────────────────────────────────

class AboutScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        t = tokens()
        root = QVBoxLayout(self)
        root.setContentsMargins(SPACE_XL, SPACE_XL, SPACE_XL, SPACE_XL)
        root.setSpacing(SPACE_LG)

        # ── Top branding strip ────────────────────────────────────────────────
        top_row = QHBoxLayout()
        top_row.setSpacing(SPACE_LG)
        top_row.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        # Vertical divider
        vline = QFrame()
        vline.setFrameShape(QFrame.Shape.VLine)
        vline.setStyleSheet(f"background: {t['border']}; border: none; max-width: 1px;")
        vline.setFixedHeight(50)
        top_row.addWidget(vline)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        app_lbl = QLabel(APP_NAME)
        app_lbl.setStyleSheet(
            f"font-size: 18px; font-weight: 800; color: {t['text_primary']}; background: transparent;"
        )
        ver_lbl = QLabel(f"Version {APP_VERSION}  ·  Biometric attendance sync for ZKTeco devices")
        ver_lbl.setStyleSheet(
            f"font-size: 11px; color: {t['text_secondary']}; background: transparent;"
        )
        title_col.addWidget(app_lbl)
        title_col.addWidget(ver_lbl)
        top_row.addLayout(title_col)
        top_row.addStretch()

        root.addLayout(top_row)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background: {t['border']}; border: none; max-height: 1px;")
        root.addWidget(sep)

        # ── Tab widget ────────────────────────────────────────────────────────
        tabs = QTabWidget()
        tabs.addTab(self._build_about_tab(),   "About")
        tabs.addTab(self._build_contact_tab(), "Contact & Support")
        tabs.addTab(self._build_manual_tab(),  "User Manual")
        root.addWidget(tabs, stretch=1)

        # ── Copyright footer ──────────────────────────────────────────────────
        from datetime import date as _date
        footer = QLabel(
            f"© {_date.today().year} Softzenix IT  ·  All rights reserved  ·  "
            f"<a href='https://softzenixbd.com' style='color:{t['accent']};'>softzenixbd.com</a>"
        )
        footer.setOpenExternalLinks(True)
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet(
            f"color: {t['text_disabled']}; font-size: 10px; background: transparent;"
        )
        root.addWidget(footer)

    # ── Tab: About ────────────────────────────────────────────────────────────

    def _build_about_tab(self) -> QWidget:
        t = tokens()
        w = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        inner = QWidget()
        lv = QVBoxLayout(inner)
        lv.setContentsMargins(SPACE_LG, SPACE_LG, SPACE_LG, SPACE_LG)
        lv.setSpacing(SPACE_LG)

        # Section title
        co_title = QLabel("About Softzenix IT")
        co_title.setStyleSheet(
            f"font-size: 15px; font-weight: 700; color: {t['text_primary']}; background: transparent;"
        )
        lv.addWidget(co_title)

        co_desc = QLabel(
            f"{APP_NAME} is a proprietary attendance management solution developed by "
            "<b>Softzenix IT</b>. It bridges ZKTeco biometric devices with cloud-based school "
            "management systems, enabling real-time attendance synchronisation for students, "
            "teachers, and staff."
        )
        co_desc.setWordWrap(True)
        co_desc.setStyleSheet(
            f"font-size: 13px; color: {t['text_secondary']}; background: transparent; line-height: 150%;"
        )
        lv.addWidget(co_desc)

        web_btn = QPushButton("  Visit softzenixbd.com")
        web_btn.setProperty("variant", "primary")
        web_btn.setMaximumWidth(200)
        web_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://softzenixbd.com")))
        lv.addWidget(web_btn)

        lv.addStretch()

        scroll.setWidget(inner)
        ol = QVBoxLayout(w)
        ol.setContentsMargins(0, 0, 0, 0)
        ol.addWidget(scroll)
        return w

    # ── Tab: Contact & Support ────────────────────────────────────────────────

    def _build_contact_tab(self) -> QWidget:
        t = tokens()
        w = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        inner = QWidget()
        lv = QVBoxLayout(inner)
        lv.setContentsMargins(SPACE_LG, SPACE_LG, SPACE_LG, SPACE_LG)
        lv.setSpacing(SPACE_LG)

        # ── Support contacts ──────────────────────────────────────────────────
        contact_card = QFrame()
        contact_card.setStyleSheet("background: transparent; border: none;")
        cl = QVBoxLayout(contact_card)
        cl.setContentsMargins(SPACE_LG, SPACE_LG, SPACE_LG, SPACE_LG)
        cl.setSpacing(SPACE_MD)

        ct_title = QLabel("Support Contacts")
        ct_title.setStyleSheet(
            f"font-size: 14px; font-weight: 700; color: {t['text_primary']}; background: transparent;"
        )
        cl.addWidget(ct_title)

        ct_info = QLabel(
            "For technical support or feature requests, reach out to our team during "
            "business hours (Sat–Thu, 10:00 AM – 6:00 PM BST)."
        )
        ct_info.setWordWrap(True)
        ct_info.setStyleSheet(f"font-size: 11px; color: {t['text_secondary']}; background: transparent;")
        cl.addWidget(ct_info)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background: {t['border']}; border: none; max-height: 1px;")
        cl.addWidget(sep)

        # Contacts
        contacts = [
            ("Email",   "csedurabd@gmail.com",   "mailto:csedurabd@gmail.com"),
            ("Website", "softzenixbd.com",        "https://softzenixbd.com"),
        ]
        for label, value, link in contacts:
            cl.addLayout(_contact_row(label, value, link))

        # Developers
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet(f"background: {t['border']}; border: none; max-height: 1px;")
        cl.addWidget(sep2)

        dev_lbl = QLabel("Development Team")
        dev_lbl.setStyleSheet(
            f"font-size: 12px; font-weight: 700; color: {t['text_secondary']}; background: transparent;"
        )
        cl.addWidget(dev_lbl)

        devs = [
            ("Rupan Chakraborty", "+880 1912-884839"),
            ("Riajul Kasem",      "+880 1777-824258"),
        ]
        for name, phone in devs:
            dev_row = QHBoxLayout()
            dev_row.setSpacing(SPACE_SM)
            name_lbl = QLabel(name)
            name_lbl.setFixedWidth(160)
            name_lbl.setStyleSheet(
                f"color: {t['text_primary']}; font-size: 12px; font-weight: 600; background: transparent;"
            )
            phone_lbl = QLabel(phone)
            phone_lbl.setStyleSheet(
                f"color: {t['text_secondary']}; font-size: 12px; background: transparent;"
            )
            phone_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            copy_btn = _CopyButton(phone.replace("-", "").replace(" ", ""))
            dev_row.addWidget(name_lbl)
            dev_row.addWidget(phone_lbl, stretch=1)
            dev_row.addWidget(copy_btn)
            cl.addLayout(dev_row)

        lv.addWidget(contact_card)

        # ── Office address ────────────────────────────────────────────────────
        addr_card = QFrame()
        addr_card.setStyleSheet("background: transparent; border: none;")
        al = QVBoxLayout(addr_card)
        al.setContentsMargins(SPACE_LG, SPACE_LG, SPACE_LG, SPACE_LG)
        al.setSpacing(SPACE_SM)

        addr_title = QLabel("Office Address")
        addr_title.setStyleSheet(
            f"font-size: 14px; font-weight: 700; color: {t['text_primary']}; background: transparent;"
        )
        al.addWidget(addr_title)

        addr_text = QLabel(
            "Satish Chandra Sarani,\n"
            "House No. 29, Korer Para,\n"
            "Pathantula, Sylhet."
        )
        addr_text.setStyleSheet(
            f"font-size: 12px; color: {t['text_primary']}; line-height: 160%; background: transparent;"
        )
        addr_text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        al.addWidget(addr_text)

        copy_addr_btn = _CopyButton("Satish Chandra Sarani, House No. 29, Korer Para, Pathantula, Sylhet.")
        copy_addr_btn.setFixedWidth(60)
        addr_copy_row = QHBoxLayout()
        addr_copy_row.addStretch()
        addr_copy_row.addWidget(copy_addr_btn)
        al.addLayout(addr_copy_row)

        lv.addWidget(addr_card)
        lv.addStretch()

        scroll.setWidget(inner)
        ol = QVBoxLayout(w)
        ol.setContentsMargins(0, 0, 0, 0)
        ol.addWidget(scroll)
        return w

    # ── Tab: User Manual ──────────────────────────────────────────────────────

    def _build_manual_tab(self) -> QWidget:
        w = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        inner = QWidget()
        lv = QVBoxLayout(inner)
        lv.setContentsMargins(SPACE_LG, SPACE_LG, SPACE_LG, SPACE_LG)
        lv.setSpacing(SPACE_SM)

        t = tokens()
        intro = QLabel(
            "Click any section heading below to expand it and read the instructions."
        )
        intro.setStyleSheet(
            f"font-size: 11px; color: {t['text_secondary']}; background: transparent;"
        )
        lv.addWidget(intro)

        sections = [
            ("Getting Started", [
                "Launch EduraSync from the Start Menu or desktop shortcut.",
                "On first run, the Setup Wizard appears automatically — enter your Cloud API URL and Sync ID, then click 'Save & Continue'.",
                "The main Dashboard opens after setup is complete.",
                "Add your biometric machines under the Devices page before syncing.",
            ]),
            ("Adding a Biometric Machine", [
                "Go to the Devices page from the left sidebar.",
                "Click '+ Add Machine' in the top-right corner.",
                "Enter the device's IP Address, Port (default 4370), and Model name.",
                "Click Save. The machine appears in the list.",
                "Select the machine and click 'Connect' to verify the connection.",
            ]),
            ("Fetching Attendance Logs", [
                "On the Dashboard, click 'Fetch Device Logs'.",
                "EduraSync connects to each online device and downloads all attendance records.",
                "Progress is shown in the status bar at the bottom of the window.",
                "Fetched records appear in the Attendance page.",
            ]),
            ("Uploading to Cloud", [
                "After fetching logs, click 'Upload Attendance' on the Dashboard.",
                "All pending (not yet posted) records are sent to the cloud API.",
                "Successfully posted records are marked and excluded from future uploads.",
                "Use 'Full Sync' to fetch and upload in a single step.",
            ]),
            ("Syncing User Profiles", [
                "Click 'Sync User Profiles' on the Dashboard.",
                "EduraSync downloads the latest student, teacher, and staff profiles from the cloud.",
                "Updated profiles are saved locally and pushed to all connected devices.",
                "Users assigned to a device appear under Devices → Users tab.",
            ]),
            ("Automatic Daily Sync", [
                "Go to Settings and enable the 'Enable daily automatic sync' checkbox.",
                "Set a Daily Sync Time (e.g. 11:00 PM) when the sync should run automatically.",
                "Click 'Save Settings'. EduraSync will perform a full sync every day at that time.",
                "To disable, uncheck the option and save again.",
            ]),
            ("Managing Attendance Records", [
                "Open the Attendance page from the sidebar.",
                "Use the search box to filter by user name or ID.",
                "Filter by status (Pending / Posted) or date range using the controls in the filter bar.",
                "Click 'Export CSV' to download the current filtered records as a spreadsheet.",
            ]),
            ("Resetting a Device", [
                "Go to Settings → Advanced Maintenance.",
                "Select the machine you want to reset from the dropdown.",
                "Click 'Reset Machine'.",
                "In the confirmation dialog, type your Sync ID to authorise the reset.",
                "Click Reset. All users and attendance logs on the physical device will be erased.",
            ]),
            ("Troubleshooting", [
                "Device shows Offline: Check the IP address and port, and ensure the device is powered on and on the same network.",
                "Upload fails: Verify the Cloud API URL and Sync ID in Settings → Test Connection.",
                "No users synced: Confirm the cloud account has user profiles assigned to this device.",
                "Application does not start: Check the log file at %APPDATA%\\EduraSync\\logs\\edurasync.log for errors.",
                "For further help, contact the support team via the Contact & Support tab.",
            ]),
        ]

        for title, steps in sections:
            body = _manual_body(steps)
            acc = _Accordion(title, body)
            lv.addWidget(acc)

        lv.addStretch()
        scroll.setWidget(inner)
        ol = QVBoxLayout(w)
        ol.setContentsMargins(0, 0, 0, 0)
        ol.addWidget(scroll)
        return w
