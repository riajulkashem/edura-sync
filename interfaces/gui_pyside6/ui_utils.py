# interfaces/gui_pyside6/ui_utils.py
"""
Utility functions for creating consistent PySide6 UI components.
"""

import logging
from pathlib import Path
from weakref import WeakSet

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QPushButton, QLineEdit, QTextEdit, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QScrollArea,
    QFrame, QSizePolicy, QMessageBox
)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QPixmap, QDesktopServices, QIcon

from core.constants import UI_CONFIG
from core.config import Config

logger = logging.getLogger(__name__)

# Keep track of temporary widgets for proper cleanup
_temporary_widgets = WeakSet()


def create_main_window(title: str, size=(800, 600)) -> QWidget:
    """
    Create a main window with standard configuration.

    Args:
        title: Window title
        size: Tuple of (width, height)

    Returns:
        QWidget: Configured main window
    """
    window = QWidget()
    window.setWindowTitle(title)
    window.resize(*size)
    
    # Set window icon
    config = Config()
    if config.ICON_PATH and config.ICON_PATH.exists():
        window.setWindowIcon(QPixmap(str(config.ICON_PATH)))
    
    _temporary_widgets.add(window)
    return window


def create_layout(orientation="vertical", parent=None) -> QVBoxLayout | QHBoxLayout:
    """
    Create a layout with standard configuration.

    Args:
        orientation: "vertical" or "horizontal"
        parent: Parent widget

    Returns:
        QVBoxLayout or QHBoxLayout: Configured layout
    """
    if orientation == "horizontal":
        layout = QHBoxLayout(parent)
    else:
        layout = QVBoxLayout(parent)
    _temporary_widgets.add(layout)
    return layout


def create_form_layout(parent=None) -> QFormLayout:
    """
    Create a form layout with standard configuration.

    Args:
        parent: Parent widget

    Returns:
        QFormLayout: Configured form layout
    """
    layout = QFormLayout(parent)
    _temporary_widgets.add(layout)
    return layout


def create_button(text: str, callback=None, parent=None) -> QPushButton:
    """
    Create a button with standard configuration.

    Args:
        text: Button text
        callback: Function to call when clicked
        parent: Parent widget

    Returns:
        QPushButton: Configured button
    """
    button = QPushButton(text, parent)
    if callback:
        button.clicked.connect(callback)
    _temporary_widgets.add(button)
    return button


def create_label(text: str, parent=None) -> QLabel:
    """
    Create a label with standard configuration.

    Args:
        text: Label text
        parent: Parent widget

    Returns:
        QLabel: Configured label
    """
    label = QLabel(text, parent)
    _temporary_widgets.add(label)
    return label


def create_line_edit(parent=None) -> QLineEdit:
    """
    Create a line edit with standard configuration.

    Args:
        parent: Parent widget

    Returns:
        QLineEdit: Configured line edit
    """
    line_edit = QLineEdit(parent)
    _temporary_widgets.add(line_edit)
    return line_edit


def create_text_edit(parent=None) -> QTextEdit:
    """
    Create a text edit with standard configuration.

    Args:
        parent: Parent widget

    Returns:
        QTextEdit: Configured text edit
    """
    text_edit = QTextEdit(parent)
    _temporary_widgets.add(text_edit)
    return text_edit


def create_combo_box(parent=None) -> QComboBox:
    """
    Create a combo box with standard configuration.

    Args:
        parent: Parent widget

    Returns:
        QComboBox: Configured combo box
    """
    combo_box = QComboBox(parent)
    _temporary_widgets.add(combo_box)
    return combo_box


def create_table(columns: list, parent=None) -> QTableWidget:
    """
    Create a table widget with standard configuration.

    Args:
        columns: List of column names
        parent: Parent widget

    Returns:
        QTableWidget: Configured table widget
    """
    table = QTableWidget(0, len(columns), parent)
    table.setHorizontalHeaderLabels(columns)
    
    # Configure header
    header = table.horizontalHeader()
    header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    
    _temporary_widgets.add(table)
    _temporary_widgets.add(header)
    return table


def create_scroll_area(parent=None) -> QScrollArea:
    """
    Create a scroll area with standard configuration.

    Args:
        parent: Parent widget

    Returns:
        QScrollArea: Configured scroll area
    """
    scroll_area = QScrollArea(parent)
    scroll_area.setWidgetResizable(True)
    _temporary_widgets.add(scroll_area)
    return scroll_area


def create_frame(parent=None) -> QFrame:
    """
    Create a frame with standard configuration.

    Args:
        parent: Parent widget

    Returns:
        QFrame: Configured frame
    """
    frame = QFrame(parent)
    _temporary_widgets.add(frame)
    return frame


def set_window_icon(window, icon_path: Path) -> bool:
    """
    Set icon for a window.

    Args:
        window: Window to set icon for
        icon_path: Path to icon file

    Returns:
        bool: True if icon set successfully, False otherwise
    """
    try:
        if icon_path and icon_path.exists():
            window.setWindowIcon(QPixmap(str(icon_path)))
            logger.debug(f"Icon set for {window.windowTitle()}")
            return True
        else:
            logger.warning(f"Icon file not found: {icon_path}")
            return False
    except Exception as e:
        logger.error(f"Icon set failed: {e}")
        return False


def show_message_box(parent, title: str, message: str, msg_type="info"):
    """
    Show a message box to the user.

    Args:
        parent: Parent widget
        title: Message box title
        message: Message text
        msg_type: Type of message ("info", "warning", "error", "question")
    """
    # Create message box with custom icon
    msg_box = QMessageBox(parent)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    
    # Set custom application icon
    config = Config()
    if config.ICON_PATH and config.ICON_PATH.exists():
        msg_box.setWindowIcon(QIcon(QPixmap(str(config.ICON_PATH))))
    
    # Set icon based on message type
    if msg_type == "warning":
        msg_box.setIcon(QMessageBox.Warning)
    elif msg_type == "error":
        msg_box.setIcon(QMessageBox.Critical)
    elif msg_type == "question":
        msg_box.setIcon(QMessageBox.Question)
    else:
        msg_box.setIcon(QMessageBox.Information)
    
    return msg_box.exec()


def open_url(url: str):
    """
    Open a URL in the default browser.

    Args:
        url: URL to open
    """
    QDesktopServices.openUrl(QUrl(url))


def get_form_values(form_fields):
    """Get values from all form fields (dict of name: widget)."""
    values = {}
    for name, field in form_fields.items():
        if isinstance(field, QLineEdit):
            values[name] = field.text().strip()
        elif isinstance(field, QComboBox):
            values[name] = field.currentText()
        elif hasattr(field, 'text'):
            values[name] = field.text().strip()
        else:
            values[name] = str(field)
    return values


def validate_required_fields(form_fields, required_fields, parent=None):
    """Validate required form fields."""
    values = get_form_values(form_fields)
    missing_fields = [field for field in required_fields if not values.get(field)]
    if missing_fields:
        field_names = ", ".join(missing_fields)
        if parent:
            show_message_box(
                parent, 
                "Error", 
                f"Please fill required fields: {field_names}", 
                "error"
            )
        return False
    return True


def cleanup_temporary_widgets():
    """
    Clean up temporary widgets.
    This method should be called periodically or during application shutdown.
    """
    count = len(_temporary_widgets)
    # Objects in WeakSet are automatically removed when they are deleted
    # This is just for logging purposes
    logger.info(f"Cleaned up {count} temporary widgets")