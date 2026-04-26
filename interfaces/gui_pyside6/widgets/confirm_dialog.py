# interfaces/gui_pyside6/widgets/confirm_dialog.py
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QFrame
)
from PySide6.QtCore import Qt
from interfaces.gui_pyside6.theme import tokens, SPACE_SM, SPACE_MD, SPACE_LG, RADIUS_LG


class ConfirmDialog(QDialog):
    """
    A themed two-step confirmation dialog for destructive actions.

    Usage:
        dlg = ConfirmDialog(
            parent=self,
            title="Reset Device",
            message="This will erase all users and logs from the device.",
            confirm_label="Reset",
            require_key=True,          # Show password-style verification input
            key_hint="Enter Sync ID to authorise",
            expected_key="my-sync-id", # If set, Confirm is only enabled when input matches
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            do_it()
    """

    def __init__(
        self,
        parent=None,
        title: str = "Confirm",
        message: str = "Are you sure?",
        confirm_label: str = "Confirm",
        danger: bool = True,
        require_key: bool = False,
        key_hint: str = "Enter authorisation key",
        expected_key: str = "",
    ):
        super().__init__(parent)
        self._expected_key = expected_key
        self._require_key = require_key
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(400)
        self.setMaximumWidth(480)

        t = tokens()
        self.setStyleSheet(f"background-color: {t['bg_surface']}; border-radius: {RADIUS_LG}px;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACE_LG, SPACE_LG, SPACE_LG, SPACE_LG)
        layout.setSpacing(SPACE_MD)

        # Icon + title row
        icon_char = "!" if danger else "?"
        icon_label = QLabel(icon_char)
        icon_label.setStyleSheet(
            f"font-size: 28px; font-weight: 700; "
            f"color: {t['danger'] if danger else t['accent']}; background: transparent;"
        )
        title_label = QLabel(title)
        title_label.setStyleSheet(
            f"font-size: 15px; font-weight: 700; color: {t['text_primary']}; background: transparent;"
        )
        header_row = QHBoxLayout()
        header_row.addWidget(icon_label)
        header_row.addWidget(title_label, stretch=1)
        layout.addLayout(header_row)

        # Message
        msg_label = QLabel(message)
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet(f"color: {t['text_secondary']}; font-size: 12px; background: transparent;")
        layout.addWidget(msg_label)

        # Optional key input
        self._key_input: QLineEdit | None = None
        self._confirm_btn: QPushButton | None = None

        if require_key:
            sep = QFrame()
            sep.setFrameShape(QFrame.Shape.HLine)
            sep.setStyleSheet(f"background: {t['border']}; border: none; max-height: 1px;")
            layout.addWidget(sep)

            key_label = QLabel(key_hint)
            key_label.setStyleSheet(f"color: {t['text_secondary']}; font-size: 11px; background: transparent;")
            layout.addWidget(key_label)

            self._key_input = QLineEdit()
            self._key_input.setEchoMode(QLineEdit.EchoMode.Password)
            self._key_input.setPlaceholderText("••••••••")
            self._key_input.textChanged.connect(self._on_key_changed)
            layout.addWidget(self._key_input)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(SPACE_SM)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setProperty("variant", "secondary")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        self._confirm_btn = QPushButton(confirm_label)
        self._confirm_btn.setProperty("variant", "danger" if danger else "primary")
        self._confirm_btn.clicked.connect(self.accept)
        if require_key and expected_key:
            self._confirm_btn.setEnabled(False)
        btn_row.addWidget(self._confirm_btn)

        layout.addLayout(btn_row)

    def _on_key_changed(self, text: str) -> None:
        if self._confirm_btn and self._expected_key:
            self._confirm_btn.setEnabled(text == self._expected_key)

    def entered_key(self) -> str:
        return self._key_input.text() if self._key_input else ""
