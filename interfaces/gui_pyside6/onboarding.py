# interfaces/gui_pyside6/onboarding.py
"""
First-run onboarding wizard.

Shown when no Settings row exists in the DB.  Collects the two mandatory
fields (Cloud API URL + Sync ID) and saves them before the main window appears.
"""
from __future__ import annotations

import logging

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QFormLayout,
    QFrame, QStackedWidget, QWidget
)
from PySide6.QtCore import Qt

from core.constants import APP_NAME, DEFAULT_SETTING
from interfaces.gui_pyside6.theme import tokens, SPACE_LG, SPACE_MD, SPACE_SM, RADIUS_LG


class OnboardingWizard(QDialog):
    """
    Three-step wizard:
      Step 0 — Welcome
      Step 1 — API Configuration
      Step 2 — Done
    """

    def __init__(self, settings_repo, parent=None):
        super().__init__(parent)
        self.logger        = logging.getLogger(__name__)
        self.settings_repo = settings_repo

        self.setWindowTitle(f"Welcome to {APP_NAME}")
        self.setModal(True)
        self.setMinimumSize(520, 380)
        self.setMaximumSize(560, 440)

        t = tokens()
        self.setStyleSheet(f"background-color: {t['bg_surface']};")

        self._current_step = 0
        self._setup_ui()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        t = tokens()
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Step indicator strip
        self._indicator = _StepIndicator(["Welcome", "Configure", "Done"])
        root.addWidget(self._indicator)

        # Page stack
        self._stack = QStackedWidget()
        root.addWidget(self._stack, stretch=1)

        self._stack.addWidget(self._build_welcome())
        self._stack.addWidget(self._build_configure())
        self._stack.addWidget(self._build_done())

        # Navigation row
        nav = QHBoxLayout()
        nav.setContentsMargins(SPACE_LG, SPACE_MD, SPACE_LG, SPACE_LG)
        nav.setSpacing(SPACE_SM)

        self._back_btn = QPushButton("← Back")
        self._back_btn.clicked.connect(self._prev_step)
        self._back_btn.setVisible(False)

        self._next_btn = QPushButton("Get Started →")
        self._next_btn.setProperty("variant", "primary")
        self._next_btn.clicked.connect(self._next_step)

        nav.addWidget(self._back_btn)
        nav.addStretch()
        nav.addWidget(self._next_btn)
        root.addLayout(nav)

    def _build_welcome(self) -> QWidget:
        t = tokens()
        w = QWidget()
        lv = QVBoxLayout(w)
        lv.setContentsMargins(SPACE_LG * 2, SPACE_LG, SPACE_LG * 2, SPACE_LG)
        lv.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lv.setSpacing(SPACE_MD)

        title = QLabel(APP_NAME)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"font-size: 30px; font-weight: 800; color: {t['accent']}; background: transparent;")
        lv.addWidget(title)

        sub = QLabel("Biometric attendance sync for ZKTeco devices")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet(f"font-size: 13px; color: {t['text_secondary']}; background: transparent;")
        lv.addWidget(sub)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background: {t['border']}; border: none; max-height: 1px; margin: 8px 40px;")
        lv.addWidget(sep)

        body = QLabel(
            "This quick setup will connect the app to your cloud account.\n"
            "You only need to do this once."
        )
        body.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body.setWordWrap(True)
        body.setStyleSheet(f"font-size: 12px; color: {t['text_secondary']}; background: transparent;")
        lv.addWidget(body)
        lv.addStretch()
        return w

    def _build_configure(self) -> QWidget:
        t = tokens()
        w = QWidget()
        lv = QVBoxLayout(w)
        lv.setContentsMargins(SPACE_LG * 2, SPACE_LG, SPACE_LG * 2, SPACE_LG)
        lv.setSpacing(SPACE_MD)

        header = QLabel("Cloud API Configuration")
        header.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {t['text_primary']}; background: transparent;")
        lv.addWidget(header)

        hint = QLabel("These credentials connect EduraSync to your school's cloud account.")
        hint.setWordWrap(True)
        hint.setStyleSheet(f"font-size: 11px; color: {t['text_secondary']}; background: transparent;")
        lv.addWidget(hint)

        form = QFormLayout()
        form.setSpacing(SPACE_MD)

        self._url_input = QLineEdit()
        self._url_input.setPlaceholderText("https://api.yourschool.com")
        self._url_input.setText(DEFAULT_SETTING.get("cloud_api_url", ""))
        form.addRow("API URL:", self._url_input)

        self._sync_id_input = QLineEdit()
        self._sync_id_input.setPlaceholderText("Your organisation sync token")
        self._sync_id_input.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Sync ID:", self._sync_id_input)

        lv.addLayout(form)

        self._config_error = QLabel("")
        self._config_error.setStyleSheet(f"color: {t['danger']}; font-size: 11px; background: transparent;")
        lv.addWidget(self._config_error)
        lv.addStretch()
        return w

    def _build_done(self) -> QWidget:
        t = tokens()
        w = QWidget()
        lv = QVBoxLayout(w)
        lv.setContentsMargins(SPACE_LG * 2, SPACE_LG, SPACE_LG * 2, SPACE_LG)
        lv.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lv.setSpacing(SPACE_MD)

        tick = QLabel("✓")
        tick.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tick.setStyleSheet(f"font-size: 48px; color: {t['success']}; background: transparent;")
        lv.addWidget(tick)

        title = QLabel("You're all set!")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {t['text_primary']}; background: transparent;")
        lv.addWidget(title)

        body = QLabel(
            "Settings saved. You can update them at any time from the Settings screen."
        )
        body.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body.setWordWrap(True)
        body.setStyleSheet(f"font-size: 12px; color: {t['text_secondary']}; background: transparent;")
        lv.addWidget(body)
        lv.addStretch()
        return w

    # ── Navigation ────────────────────────────────────────────────────────────

    def _next_step(self) -> None:
        if self._current_step == 1:
            if not self._validate_and_save():
                return
        self._current_step += 1
        self._update_step()

    def _prev_step(self) -> None:
        self._current_step = max(0, self._current_step - 1)
        self._update_step()

    def _update_step(self) -> None:
        self._stack.setCurrentIndex(self._current_step)
        self._indicator.set_step(self._current_step)
        self._back_btn.setVisible(self._current_step > 0)

        if self._current_step == 0:
            self._next_btn.setText("Get Started →")
        elif self._current_step == 1:
            self._next_btn.setText("Save & Continue →")
        else:
            self._next_btn.setText("Open Dashboard")
            self._next_btn.clicked.disconnect()
            self._next_btn.clicked.connect(self.accept)

    def _validate_and_save(self) -> bool:
        url     = self._url_input.text().strip()
        sync_id = self._sync_id_input.text().strip()

        if not url:
            self._config_error.setText("API URL is required.")
            return False
        if not sync_id:
            self._config_error.setText("Sync ID is required.")
            return False

        self._config_error.setText("")
        try:
            self.settings_repo.save_settings(
                cloud_api_url=url,
                sync_id=sync_id,
            )
            self.logger.info("Onboarding: settings saved")
            return True
        except Exception as e:
            self._config_error.setText(f"Failed to save: {e}")
            self.logger.error(f"Onboarding save error: {e}")
            return False


class _StepIndicator(QWidget):
    """Horizontal step progress indicator."""

    def __init__(self, labels: list[str], parent=None):
        super().__init__(parent)
        self._labels  = labels
        self._current = 0
        self.setFixedHeight(44)
        self._setup()

    def _setup(self) -> None:
        t = tokens()
        self.setStyleSheet(
            f"background-color: {t['bg_subtle']}; border-bottom: 1px solid {t['border']};"
        )
        row = QHBoxLayout(self)
        row.setContentsMargins(24, 0, 24, 0)
        self._step_labels: list[QLabel] = []
        for i, label in enumerate(self._labels):
            lbl = QLabel(f"{i + 1}. {label}")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            row.addWidget(lbl, stretch=1)
            self._step_labels.append(lbl)
        self._apply_colours()

    def set_step(self, step: int) -> None:
        self._current = step
        self._apply_colours()

    def _apply_colours(self) -> None:
        t = tokens()
        for i, lbl in enumerate(self._step_labels):
            if i < self._current:
                lbl.setStyleSheet(f"color: {t['success']}; font-weight: 600; font-size: 12px; background: transparent;")
            elif i == self._current:
                lbl.setStyleSheet(f"color: {t['accent']}; font-weight: 700; font-size: 12px; background: transparent;")
            else:
                lbl.setStyleSheet(f"color: {t['text_disabled']}; font-size: 12px; background: transparent;")
