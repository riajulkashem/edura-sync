# interfaces/gui_pyside6/screens/dashboard_screen.py
"""Dashboard (home) screen — at-a-glance system health."""
from __future__ import annotations

import logging
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QTableWidget,
    QTableWidgetItem, QHeaderView, QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QTimer

from interfaces.gui_pyside6.theme import tokens, SPACE_LG, SPACE_MD, SPACE_SM, SPACE_XL, RADIUS_LG
from interfaces.gui_pyside6.widgets import StatCard, StatusBadge, Spinner


class _CalloutBanner(QFrame):
    """Dismissable info banner shown when pending records exist."""
    action_clicked = Signal()

    def __init__(self, message: str, action_label: str = "", parent=None):
        super().__init__(parent)
        t = tokens()
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {t['warning_bg']};
                border: 1px solid {t['warning']};
                border-radius: {RADIUS_LG}px;
                padding: 4px;
            }}
        """)
        row = QHBoxLayout(self)
        row.setContentsMargins(SPACE_MD, SPACE_SM, SPACE_MD, SPACE_SM)
        lbl = QLabel(message)
        lbl.setStyleSheet(f"color: {t['warning']}; font-weight: 600; background: transparent; border: none;")
        row.addWidget(lbl, stretch=1)
        if action_label:
            btn = QPushButton(action_label)
            btn.setProperty("variant", "ghost")
            btn.setStyleSheet(f"color: {t['warning']}; font-weight: 700; background: transparent; border: none;")
            btn.clicked.connect(self.action_clicked)
            row.addWidget(btn)


class _SectionHeader(QLabel):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        t = tokens()
        self.setStyleSheet(
            f"font-size: 13px; font-weight: 700; color: {t['text_primary']};"
            f" padding-bottom: 2px; border-bottom: 2px solid {t['border']}; background: transparent;"
        )


class DashboardScreen(QWidget):
    """
    Home screen with:
    - 4 stat cards (total devices, online, total users, pending uploads)
    - Last-sync timestamps
    - Device status table
    - Quick action buttons (wired to WorkerManager via signals)
    """

    # Signals emitted when user clicks action buttons
    sig_check_devices     = Signal()  # Ping all machines
    sig_pull_from_devices = Signal()  # Device → Local DB (attendance)
    sig_post_to_cloud     = Signal()  # Local DB → Cloud (attendance)
    sig_sync_attendance   = Signal()  # Pull from devices + Post to cloud
    sig_sync_users        = Signal()  # Cloud → Local DB → Devices (user profiles)

    def __init__(self, device_repo, user_repo, attendance_repo, settings_repo, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self._device_repo     = device_repo
        self._user_repo       = user_repo
        self._attendance_repo = attendance_repo
        self._settings_repo   = settings_repo

        self._action_buttons: list[QPushButton] = []
        self._callout: _CalloutBanner | None = None

        self._setup_ui()

        # Auto-refresh every 30 s (only DB reads — no network)
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self.refresh)
        self._refresh_timer.start(30_000)

    # ── UI construction ──────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(SPACE_XL, SPACE_XL, SPACE_XL, 0)
        outer.setSpacing(SPACE_LG)

        # Scrollable content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        self._layout = QVBoxLayout(content)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(SPACE_XL)
        scroll.setWidget(content)
        outer.addWidget(scroll, stretch=1)

        # ── Page title
        t = tokens()
        title = QLabel("Dashboard")
        title.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {t['text_primary']}; background: transparent;")
        self._layout.addWidget(title)

        # ── Callout placeholder
        self._callout_container = QVBoxLayout()
        self._callout_container.setContentsMargins(0, 0, 0, 0)
        self._layout.addLayout(self._callout_container)

        # ── Stat cards
        self._stat_devices  = StatCard("0", "Total Devices",   tone="neutral")
        self._stat_online   = StatCard("0", "Online",          tone="success")
        self._stat_users    = StatCard("0", "Total Users",     tone="neutral")
        self._stat_pending  = StatCard("0", "Pending Upload",  tone="neutral")

        cards_row = QHBoxLayout()
        cards_row.setSpacing(SPACE_MD)
        for card in [self._stat_devices, self._stat_online, self._stat_users, self._stat_pending]:
            card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            cards_row.addWidget(card)
        self._layout.addLayout(cards_row)

        # ── Quick actions — two logical groups ────────────────────────────────
        self._layout.addWidget(_SectionHeader("Quick Actions"))

        actions_outer = QHBoxLayout()
        actions_outer.setSpacing(SPACE_LG)

        # ── Left group: Attendance flow ────────────────────────────────────
        attend_group = self._mk_action_group(
            "Attendance",
            t["accent_muted"],
            [
                (
                    "⬇  Pull from Devices",
                    "Fetch attendance logs from ZKTeco devices → save to local database",
                    self.sig_pull_from_devices,
                    "primary",
                ),
                (
                    "⬆  Post to Cloud",
                    "Upload pending attendance records from local database → cloud API",
                    self.sig_post_to_cloud,
                    "primary",
                ),
                (
                    "⬇⬆  Sync Attendance",
                    "Pull from devices and immediately upload to cloud in one step",
                    self.sig_sync_attendance,
                    "primary",
                ),
            ],
        )
        actions_outer.addWidget(attend_group)

        # ── Right group: Device & user management ──────────────────────────
        device_group = self._mk_action_group(
            "Devices & Users",
            t["success_bg"],
            [
                (
                    "↻  Sync Users & Devices",
                    "Download user profiles and device list from cloud → save locally → push to ZKTeco devices",
                    self.sig_sync_users,
                    "primary",
                ),
                (
                    "●  Check Device Status",
                    "Test connectivity to all configured ZKTeco machines",
                    self.sig_check_devices,
                    "secondary",
                ),
            ],
        )
        actions_outer.addWidget(device_group)

        self._layout.addLayout(actions_outer)

        # ── Device status table
        self._layout.addWidget(_SectionHeader("Devices"))
        self._device_table = QTableWidget()
        self._device_table.setColumnCount(5)
        self._device_table.setHorizontalHeaderLabels(["IP Address", "Model", "Status", "Users", "Last Updated"])
        self._device_table.horizontalHeader().setStretchLastSection(True)
        self._device_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._device_table.verticalHeader().setVisible(False)
        self._device_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._device_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._device_table.setAlternatingRowColors(True)
        self._device_table.setMinimumHeight(160)
        self._layout.addWidget(self._device_table)

        self._layout.addStretch()

        # ── Last-activity footer bar (outside scroll, always visible) ─────────
        self._footer = self._build_activity_footer()
        outer.addWidget(self._footer)

        self.refresh()

    def _mk_action_group(
        self,
        title: str,
        bg: str,
        actions: list[tuple[str, str, object, str]],
    ) -> QFrame:
        """
        Build a titled group card containing action buttons.
        actions: list of (label, tooltip, signal, variant)
        """
        t = tokens()
        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background-color: {bg}; border: 1px solid {t['border']};"
            f" border-radius: 8px; }}"
        )
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        lv = QVBoxLayout(card)
        lv.setContentsMargins(SPACE_MD, SPACE_MD, SPACE_MD, SPACE_MD)
        lv.setSpacing(SPACE_SM)

        group_lbl = QLabel(title)
        group_lbl.setStyleSheet(
            f"font-size: 11px; font-weight: 700; letter-spacing: 0.5px;"
            f" color: {t['text_secondary']}; background: transparent;"
            f" text-transform: uppercase;"
        )
        lv.addWidget(group_lbl)

        for label, tooltip, sig, variant in actions:
            btn = QPushButton(label)
            btn.setProperty("variant", variant)
            btn.setToolTip(tooltip)
            btn.setMinimumHeight(34)
            btn.clicked.connect(sig)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            self._action_buttons.append(btn)
            lv.addWidget(btn)

        return card

    def _build_activity_footer(self) -> QFrame:
        """Build the sticky single-row footer showing last-activity timestamps."""
        t = tokens()
        bar = QFrame()
        bar.setFixedHeight(36)
        bar.setStyleSheet(
            f"QFrame {{ background-color: {t['bg_subtle']};"
            f" border-top: 1px solid {t['border']}; border-radius: 0; }}"
        )
        row = QHBoxLayout(bar)
        row.setContentsMargins(SPACE_LG, 0, SPACE_LG, 0)
        row.setSpacing(0)

        self._footer_pull_lbl  = QLabel()
        self._footer_post_lbl  = QLabel()
        lbl_style = (
            f"color: {t['text_secondary']}; font-size: 11px; background: transparent;"
        )
        self._footer_pull_lbl.setStyleSheet(lbl_style)
        self._footer_post_lbl.setStyleSheet(lbl_style)

        dot = QLabel("  ·  ")
        dot.setStyleSheet(f"color: {t['text_disabled']}; font-size: 11px; background: transparent;")

        row.addWidget(self._footer_pull_lbl)
        row.addWidget(dot)
        row.addWidget(self._footer_post_lbl)
        row.addStretch()

        self._refresh_activity_footer()
        return bar

    def _refresh_activity_footer(self) -> None:
        """Update the footer labels from the current settings row."""
        settings = self._settings_repo.get_settings()

        def _fmt(ts):
            if isinstance(ts, datetime):
                return ts.strftime("%b %d, %Y  %H:%M")
            return "Never"

        pull_ts = getattr(settings, "last_sync", None) if settings else None
        post_ts = getattr(settings, "last_post", None) if settings else None

        self._footer_pull_lbl.setText(f"Last device pull:  {_fmt(pull_ts)}")
        self._footer_post_lbl.setText(f"Last cloud upload:  {_fmt(post_ts)}")

    # ── Public API ────────────────────────────────────────────────────────────

    def refresh(self) -> None:
        """Refresh all stats from the database (no network calls)."""
        try:
            self._refresh_stats()
            self._refresh_device_table()
            self._refresh_activity_footer()
            self._refresh_callout()
        except Exception as e:
            self.logger.error(f"Dashboard refresh error: {e}")

    def set_busy(self, busy: bool, message: str = "") -> None:
        """Disable/enable action buttons and show a status indicator."""
        for btn in self._action_buttons:
            btn.setEnabled(not busy)
            if busy:
                btn.setProperty("variant", "secondary")
            else:
                btn.setProperty("variant", "primary")
            # Force style refresh
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    # ── Private helpers ───────────────────────────────────────────────────────

    def _refresh_stats(self) -> None:
        device_stats = self._device_repo.get_device_stats()
        user_stats   = self._user_repo.get_user_stats()
        pending      = self._attendance_repo.get_pending_count()
        total        = self._attendance_repo.count()

        self._stat_devices.set_value(str(device_stats.get("total", 0)))
        online = device_stats.get("online", 0)
        self._stat_online.set_value(str(online))
        self._stat_online.set_tone("success" if online > 0 else "danger")
        self._stat_users.set_value(str(user_stats.get("total", 0)))
        self._stat_pending.set_value(str(pending))
        self._stat_pending.set_tone("warning" if pending > 0 else "neutral")

    def _refresh_device_table(self) -> None:
        devices = self._device_repo.get_all()
        self._device_table.setRowCount(len(devices))
        t = tokens()
        for row, dev in enumerate(devices):
            self._device_table.setItem(row, 0, QTableWidgetItem(dev.ip_address))
            self._device_table.setItem(row, 1, QTableWidgetItem(dev.device_model))

            badge_widget = QWidget()
            badge_layout = QHBoxLayout(badge_widget)
            badge_layout.setContentsMargins(4, 2, 4, 2)
            tone = "success" if dev.status == "Online" else "danger"
            badge_layout.addWidget(StatusBadge(dev.status, tone))
            badge_layout.addStretch()
            self._device_table.setCellWidget(row, 2, badge_widget)

            user_count = self._user_repo.count_by_device(dev)
            self._device_table.setItem(row, 3, QTableWidgetItem(str(user_count)))
            updated = dev.updated_at.strftime("%b %d  %H:%M") if hasattr(dev.updated_at, "strftime") else str(dev.updated_at)
            self._device_table.setItem(row, 4, QTableWidgetItem(updated))
        self._device_table.resizeRowsToContents()

    def _refresh_callout(self) -> None:
        # Clear old callout
        while self._callout_container.count():
            item = self._callout_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        pending = self._attendance_repo.get_pending_count()
        if pending > 0:
            banner = _CalloutBanner(
                f"{pending} attendance records waiting to upload to cloud.",
                "Post to Cloud"
            )
            banner.action_clicked.connect(self.sig_post_to_cloud)
            self._callout_container.addWidget(banner)

    def cleanup(self) -> None:
        self._refresh_timer.stop()
