# interfaces/gui_pyside6/screens/attendance_screen.py
"""Attendance screen — browse, filter and export attendance records."""
from __future__ import annotations

import csv
import logging
import os

from datetime import date, timedelta
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QComboBox, QDateEdit, QLineEdit,
    QMessageBox, QFileDialog, QProgressBar, QFrame
)
from PySide6.QtCore import Qt, QDate

from interfaces.gui_pyside6.theme import tokens, SPACE_LG, SPACE_MD, SPACE_SM, SPACE_XL
from interfaces.gui_pyside6.widgets import StatusBadge
from interfaces.database.repository import AttendanceRepository, UserRepository, DeviceRepository


class AttendanceScreen(QWidget):
    """Filterable, paginated view of attendance records with CSV export."""

    PAGE_SIZE = 100

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.attendance_repo = AttendanceRepository()
        self.user_repo       = UserRepository()
        self.device_repo     = DeviceRepository()

        self._current_page = 0
        self._total_records = 0
        self._all_records: list = []

        self._setup_ui()
        self._load_records()

    # ── Timestamp helper ──────────────────────────────────────────────────────

    @staticmethod
    def _parse_ts(value):
        """
        Return a datetime from *value*, or None if it cannot be parsed.

        Peewee's DateTimeField normally returns a datetime, but when the row
        was written by an external library (e.g. ZKTeco) the column may contain
        a raw SQLite string.  This helper handles both cases transparently.
        """
        if value is None:
            return None
        if hasattr(value, "strftime"):
            return value  # already a datetime / date
        from datetime import datetime as _dt
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"):
            try:
                return _dt.strptime(str(value), fmt)
            except ValueError:
                pass
        return None

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _make_date_edit(self) -> QDateEdit:
        """
        Create a QDateEdit with a calendar popup that renders correctly.

        Qt's QCalendarWidget inherits the application-level stylesheet, which
        causes the global QTableView / QHeaderView / QSpinBox / QProgressBar
        rules to bleed in and collapse rows or add unwanted gaps. The fix is to
        call calendarWidget() right after enabling the popup so Qt creates the
        internal widget, then apply a fully self-contained stylesheet to THAT
        instance — instance-level sheets override the app-level sheet for the
        entire widget subtree.
        """
        t = tokens()
        de = QDateEdit()
        de.setCalendarPopup(True)
        de.setMinimumWidth(110)
        de.setDisplayFormat("dd/MM/yy")

        cal = de.calendarWidget()
        if cal is None:
            return de

        cal.setGridVisible(False)
        # 340 px wide fits 7 columns without truncating "Sun/Mon/…"
        cal.setMinimumSize(340, 280)

        accent    = t["accent"]
        surface   = t["bg_surface"]
        subtle    = t["bg_subtle"]
        border    = t["border"]
        primary   = t["text_primary"]
        secondary = t["text_secondary"]
        disabled  = t["text_disabled"]

        # ── Fully self-contained stylesheet ─────────────────────────────────
        # Every selector is written as "QCalendarWidget <child>" so it does
        # NOT inherit from the app-level sheet.  Rules that must fully reset a
        # property (e.g. border, border-radius, margin, padding) are explicit.
        cal.setStyleSheet(f"""

/* Container — opaque so no bleed-through from widgets behind */
QCalendarWidget {{
    background-color: {surface};
    border: 1px solid {border};
    border-radius: 8px;
}}

/* ── Navigation bar ───────────────────────────────────────── */
QCalendarWidget QWidget#qt_calendar_navigationbar {{
    background-color: {accent};
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    min-height: 38px;
    max-height: 38px;
    margin: 0;
    padding: 0 6px;
}}

QCalendarWidget QToolButton {{
    color: #ffffff;
    background-color: transparent;
    border: none;
    border-radius: 4px;
    font-size: 13px;
    font-weight: 600;
    padding: 4px 10px;
    margin: 0;
    min-height: 28px;
    max-height: 28px;
    min-width: 0;
}}
QCalendarWidget QToolButton:hover  {{ background-color: rgba(255,255,255,0.20); }}
QCalendarWidget QToolButton:pressed {{ background-color: rgba(255,255,255,0.30); }}
QCalendarWidget QToolButton::menu-indicator {{ image: none; width: 0; }}

QCalendarWidget QSpinBox {{
    color: #ffffff;
    background-color: transparent;
    border: none;
    font-size: 13px;
    font-weight: 600;
    padding: 0 4px;
    margin: 0;
    min-height: 28px;
    max-height: 28px;
    selection-background-color: rgba(255,255,255,0.30);
    selection-color: #ffffff;
}}
QCalendarWidget QSpinBox::up-button,
QCalendarWidget QSpinBox::down-button {{
    width: 0; height: 0; border: none;
}}

/* ── Day grid (QCalendarView is a QTableView subclass) ─────── */
QCalendarWidget QTableView {{
    background-color: {surface};
    alternate-background-color: {surface};
    gridline-color: transparent;
    border: none;
    border-radius: 0;
    margin: 0;
    padding: 0;
    outline: none;
    selection-background-color: {accent};
    selection-color: #ffffff;
    font-size: 12px;
}}
QCalendarWidget QTableView::item {{
    padding: 0;
    margin: 0;
    border: none;
    border-radius: 0;
    min-height: 0;
    max-height: none;
    color: {primary};
}}
QCalendarWidget QTableView::item:selected {{
    background-color: {accent};
    color: #ffffff;
}}
QCalendarWidget QTableView::item:hover {{
    background-color: {subtle};
}}

/* Day-name header row */
QCalendarWidget QTableView QHeaderView {{
    background-color: {subtle};
    border: none;
    margin: 0;
    padding: 0;
}}
QCalendarWidget QTableView QHeaderView::section {{
    background-color: {subtle};
    color: {secondary};
    font-size: 11px;
    font-weight: 600;
    border: none;
    border-bottom: 1px solid {border};
    padding: 3px 0;
    margin: 0;
    min-height: 22px;
    max-height: 22px;
}}

/* Scrollbars inside calendar */
QCalendarWidget QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 0;
    max-height: none;
}}
QCalendarWidget QScrollBar::handle:vertical {{
    background: {border};
    border-radius: 3px;
    min-height: 20px;
    max-height: none;
}}
QCalendarWidget QScrollBar:horizontal {{
    background: transparent;
    height: 6px;
    margin: 0;
    max-width: none;
}}
QCalendarWidget QScrollBar::handle:horizontal {{
    background: {border};
    border-radius: 3px;
    min-width: 20px;
    max-width: none;
}}
QCalendarWidget QScrollBar::add-line:vertical,
QCalendarWidget QScrollBar::sub-line:vertical  {{ height: 0; border: none; }}
QCalendarWidget QScrollBar::add-line:horizontal,
QCalendarWidget QScrollBar::sub-line:horizontal {{ width: 0; border: none; }}

""")
        return de

    # ── UI ────────────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        t = tokens()
        root = QVBoxLayout(self)
        root.setContentsMargins(SPACE_XL, SPACE_XL, SPACE_XL, SPACE_XL)
        root.setSpacing(SPACE_MD)

        # Title row
        hdr = QHBoxLayout()
        title = QLabel("Attendance")
        title.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {t['text_primary']}; background: transparent;")
        hdr.addWidget(title, stretch=1)
        export_btn = QPushButton("Export CSV")
        export_btn.setProperty("variant", "primary")
        export_btn.clicked.connect(self._export_csv)
        hdr.addWidget(export_btn)
        root.addLayout(hdr)

        # Filters
        filter_box = QFrame()
        filter_box.setStyleSheet(
            f"background-color: {t['bg_surface']}; border: 1px solid {t['border']};"
            f" border-radius: 8px; padding: 4px;"
        )
        fl = QHBoxLayout(filter_box)
        fl.setSpacing(SPACE_SM)

        # Search (narrow — fixed width)
        self._search = QLineEdit()
        self._search.setPlaceholderText("Search name / user ID…")
        self._search.setFixedWidth(180)
        self._search.textChanged.connect(self._apply_filters)
        fl.addWidget(self._search)

        # Status filter (slightly wider)
        self._status_combo = QComboBox()
        self._status_combo.addItems(["All Status", "Pending", "Posted"])
        self._status_combo.setMinimumWidth(120)
        self._status_combo.currentIndexChanged.connect(self._apply_filters)
        fl.addWidget(self._status_combo)

        # Date range — labels + pickers take remaining stretch
        from_lbl = QLabel("From")
        fl.addWidget(from_lbl)
        self._from_date = self._make_date_edit()
        self._from_date.setDate(QDate.currentDate().addDays(-30))
        self._from_date.dateChanged.connect(self._apply_filters)
        fl.addWidget(self._from_date)

        to_lbl = QLabel("To")
        fl.addWidget(to_lbl)
        self._to_date = self._make_date_edit()
        self._to_date.setDate(QDate.currentDate())
        self._to_date.dateChanged.connect(self._apply_filters)
        fl.addWidget(self._to_date)

        reset_btn = QPushButton("Reset")
        reset_btn.setMinimumWidth(70)
        reset_btn.clicked.connect(self._reset_filters)
        fl.addWidget(reset_btn)

        root.addWidget(filter_box)

        # Stats row
        self._count_label = QLabel("")
        self._count_label.setStyleSheet(f"color: {t['text_secondary']}; font-size: 11px; background: transparent;")
        self._pending_badge = StatusBadge("0 pending", "warning")
        stats_row = QHBoxLayout()
        stats_row.addWidget(self._count_label, stretch=1)
        stats_row.addWidget(self._pending_badge)
        root.addLayout(stats_row)

        # Table
        self._table = QTableWidget()
        self._table.setColumnCount(7)
        self._table.setHorizontalHeaderLabels(["User ID", "Name", "Device", "Timestamp", "Method", "Punch", "Status"])
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        root.addWidget(self._table, stretch=1)

        # Pagination
        pg_row = QHBoxLayout()
        self._prev_btn = QPushButton("← Prev")
        self._next_btn = QPushButton("Next →")
        self._page_label = QLabel("")
        self._page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._prev_btn.clicked.connect(self._prev_page)
        self._next_btn.clicked.connect(self._next_page)
        pg_row.addWidget(self._prev_btn)
        pg_row.addWidget(self._page_label, stretch=1)
        pg_row.addWidget(self._next_btn)
        root.addLayout(pg_row)

    # ── Data ──────────────────────────────────────────────────────────────────

    def _load_records(self) -> None:
        try:
            raw = self.attendance_repo.get_all_with_user()
        except Exception as e:
            self.logger.error(f"Attendance load error: {e}")
            raw = []
        self._all_records = raw
        self._apply_filters()

    def _apply_filters(self) -> None:
        search    = self._search.text().lower().strip()
        status    = self._status_combo.currentIndex()  # 0=All, 1=Pending, 2=Posted
        from_d    = self._from_date.date().toPython()
        to_d      = self._to_date.date().toPython()

        filtered = []
        for rec in self._all_records:
            # Status filter
            if status == 1 and rec.posted:
                continue
            if status == 2 and not rec.posted:
                continue

            # Date filter
            ts = self._parse_ts(rec.timestamp)
            if ts:
                rec_date = ts.date()
                if not (from_d <= rec_date <= to_d):
                    continue

            # Search
            if search:
                user_id  = str(getattr(rec, "user_id",  "")).lower()
                try:
                    name = rec.user.name.lower()
                except Exception:
                    name = ""
                if search not in user_id and search not in name:
                    continue

            filtered.append(rec)

        self._filtered = filtered
        self._current_page = 0
        self._refresh_table()
        self._update_stats(filtered)

    def _refresh_table(self) -> None:
        start = self._current_page * self.PAGE_SIZE
        page  = self._filtered[start:start + self.PAGE_SIZE]
        from interfaces.database.models import Attendance as AttModel

        self._table.setRowCount(len(page))
        for row, rec in enumerate(page):
            try:
                name = rec.user.name
                user_id = rec.user.user_id
            except Exception:
                name = "Unknown"
                user_id = str(getattr(rec, "user_id", ""))

            try:
                device_ip = rec.device.ip_address
            except Exception:
                device_ip = "Unknown"

            ts = self._parse_ts(rec.timestamp)
            ts_str = ts.strftime("%b %d, %Y  %I:%M %p") if ts else "Unknown"
            status_code = getattr(rec, "status", 0)
            punch_code  = getattr(rec, "punch",  0)

            self._table.setItem(row, 0, QTableWidgetItem(str(user_id)))
            self._table.setItem(row, 1, QTableWidgetItem(name))
            self._table.setItem(row, 2, QTableWidgetItem(device_ip))
            self._table.setItem(row, 3, QTableWidgetItem(ts_str))
            self._table.setItem(row, 4, QTableWidgetItem(AttModel.STATUS_MAP.get(status_code, str(status_code))))
            self._table.setItem(row, 5, QTableWidgetItem(AttModel.PUNCH_MAP.get(punch_code, str(punch_code))))

            # Status badge in col 6
            status_text = "Posted" if rec.posted else "Pending"
            tone = "success" if rec.posted else "warning"
            badge_w = QWidget()
            badge_l = QHBoxLayout(badge_w)
            badge_l.setContentsMargins(4, 2, 4, 2)
            badge_l.addWidget(StatusBadge(status_text, tone))
            badge_l.addStretch()
            self._table.setCellWidget(row, 6, badge_w)

        self._table.resizeRowsToContents()
        total_pages = max(1, -(-len(self._filtered) // self.PAGE_SIZE))
        self._page_label.setText(f"Page {self._current_page + 1} of {total_pages}  ({len(self._filtered)} records)")
        self._prev_btn.setEnabled(self._current_page > 0)
        self._next_btn.setEnabled((self._current_page + 1) * self.PAGE_SIZE < len(self._filtered))

    def _update_stats(self, records: list) -> None:
        pending = sum(1 for r in records if not r.posted)
        self._count_label.setText(f"{len(records)} records shown")
        self._pending_badge.update_badge(f"{pending} pending", "warning" if pending else "neutral")

    def _prev_page(self) -> None:
        if self._current_page > 0:
            self._current_page -= 1
            self._refresh_table()

    def _next_page(self) -> None:
        if (self._current_page + 1) * self.PAGE_SIZE < len(self._filtered):
            self._current_page += 1
            self._refresh_table()

    def _reset_filters(self) -> None:
        self._search.clear()
        self._status_combo.setCurrentIndex(0)
        self._from_date.setDate(QDate.currentDate().addDays(-30))
        self._to_date.setDate(QDate.currentDate())

    def refresh(self) -> None:
        self._load_records()

    # ── Export ────────────────────────────────────────────────────────────────

    def _export_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Attendance", f"attendance_{date.today()}.csv", "CSV Files (*.csv)"
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["User ID", "Name", "Device", "Timestamp", "Method", "Punch", "Status"])
                from interfaces.database.models import Attendance as AttModel
                for rec in self._filtered:
                    try:
                        name    = rec.user.name
                        user_id = rec.user.user_id
                    except Exception:
                        name    = "Unknown"
                        user_id = str(getattr(rec, "user_id", ""))
                    try:
                        device_ip = rec.device.ip_address
                    except Exception:
                        device_ip = "Unknown"
                    ts = rec.timestamp.strftime("%Y-%m-%d %H:%M:%S") if rec.timestamp else ""
                    status_code = getattr(rec, "status", 0)
                    punch_code  = getattr(rec, "punch",  0)
                    posted_str  = "Posted" if rec.posted else "Pending"
                    writer.writerow([
                        user_id, name, device_ip, ts,
                        AttModel.STATUS_MAP.get(status_code, str(status_code)),
                        AttModel.PUNCH_MAP.get(punch_code, str(punch_code)),
                        posted_str
                    ])
            QMessageBox.information(self, "Export Complete", f"Saved to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", str(e))
