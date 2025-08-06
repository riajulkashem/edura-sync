# interfaces/gui/ui_utils.py
"""
Utility functions for creating consistent UI components.
"""

import logging
import tkinter as tk
from tkinter import ttk
from pathlib import Path
from PIL import Image, ImageTk

from core.constants import UI_CONFIG


logger = logging.getLogger(__name__)


def create_window(parent, title: str, size: str) -> tk.Toplevel:
    """
    Create a new window with standard configuration.

    Args:
        parent: Parent window
        title: Window title
        size: Window size (e.g., "600x400")

    Returns:
        tk.Toplevel: Configured window
    """
    window = tk.Toplevel(parent)
    window.title(title)
    window.geometry(size)
    window.resizable(True, True)

    # Center window on screen
    window.update_idletasks()
    x = (window.winfo_screenwidth() // 2) - (window.winfo_width() // 2)
    y = (window.winfo_screenheight() // 2) - (window.winfo_height() // 2)
    window.geometry(f"+{x}+{y}")

    return window


def setup_styles():
    """Configure ttk styles for consistent appearance."""
    style = ttk.Style()

    # Configure common styles
    style.configure("Header.TLabel", font=UI_CONFIG["HEADER_FONT"])
    style.configure("Info.TLabel", font=UI_CONFIG["DEFAULT_FONT"])
    style.configure("Small.TLabel", font=UI_CONFIG["SMALL_FONT"])


def create_notebook(parent) -> ttk.Notebook:
    """
    Create a notebook widget with standard configuration.

    Args:
        parent: Parent widget

    Returns:
        ttk.Notebook: Configured notebook widget
    """
    notebook = ttk.Notebook(parent)
    notebook.pack(
        fill="both",
        expand=True,
        padx=UI_CONFIG["DEFAULT_PADDING"],
        pady=UI_CONFIG["DEFAULT_PADDING"],
    )
    return notebook


def create_tab(notebook, title: str) -> ttk.Frame:
    """
    Create a new tab in a notebook.

    Args:
        notebook: Notebook widget
        title: Tab title

    Returns:
        ttk.Frame: Frame for tab content
    """
    frame = ttk.Frame(notebook)
    notebook.add(frame, text=title)
    return frame


def load_icon(window, icon_path: Path) -> bool:
    """
    Load and set icon for a window.

    Args:
        window: Window to set icon for
        icon_path: Path to icon file

    Returns:
        bool: True if icon loaded successfully, False otherwise
    """
    try:
        if icon_path and icon_path.exists():
            # Load and set icon
            icon = Image.open(icon_path)
            photo = ImageTk.PhotoImage(icon)
            window.iconphoto(False, photo)
            logger.debug(f"Icon set for {window.title()}")
            return True
        else:
            logger.warning(f"Icon file not found: {icon_path}")
            return False
    except Exception as e:
        logger.error(f"Icon load failed: {e}")
        return False


def create_button(parent, text: str, command, **kwargs) -> ttk.Button:
    """
    Create a button with standard configuration.

    Args:
        parent: Parent widget
        text: Button text
        command: Command to execute
        **kwargs: Additional button options

    Returns:
        ttk.Button: Configured button
    """
    return ttk.Button(parent, text=text, command=command, **kwargs)


def create_entry(parent, **kwargs) -> ttk.Entry:
    """
    Create an entry widget with standard configuration.

    Args:
        parent: Parent widget
        **kwargs: Additional entry options

    Returns:
        ttk.Entry: Configured entry widget
    """
    return ttk.Entry(parent, **kwargs)


def create_label(parent, text: str, **kwargs) -> ttk.Label:
    """
    Create a label widget with standard configuration.

    Args:
        parent: Parent widget
        text: Label text
        **kwargs: Additional label options

    Returns:
        ttk.Label: Configured label widget
    """
    return ttk.Label(parent, text=text, **kwargs)


def create_frame(parent, **kwargs) -> ttk.Frame:
    """
    Create a frame widget with standard configuration.

    Args:
        parent: Parent widget
        **kwargs: Additional frame options

    Returns:
        ttk.Frame: Configured frame widget
    """
    return ttk.Frame(parent, **kwargs)


def create_treeview(parent, columns: list, **kwargs) -> ttk.Treeview:
    """
    Create a treeview widget with standard configuration.

    Args:
        parent: Parent widget
        columns: List of column names
        **kwargs: Additional treeview options

    Returns:
        ttk.Treeview: Configured treeview widget
    """
    tree = ttk.Treeview(parent, columns=columns, show="headings", **kwargs)

    # Configure columns
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=100)

    return tree


def create_scrollbar(parent, orient: str = "vertical", **kwargs) -> ttk.Scrollbar:
    """
    Create a scrollbar widget with standard configuration.

    Args:
        parent: Parent widget
        orient: Scrollbar orientation ("vertical" or "horizontal")
        **kwargs: Additional scrollbar options

    Returns:
        ttk.Scrollbar: Configured scrollbar widget
    """
    return ttk.Scrollbar(parent, orient=orient, **kwargs)


def create_text(parent, **kwargs) -> tk.Text:
    """
    Create a text widget with standard configuration.

    Args:
        parent: Parent widget
        **kwargs: Additional text widget options

    Returns:
        tk.Text: Configured text widget
    """
    return tk.Text(parent, **kwargs)


def get_form_values(form_fields):
    """Get values from all form fields (dict of name: widget)."""
    return {name: field.get().strip() for name, field in form_fields.items()}


def validate_required_fields(form_fields, required_fields, notify=None, update_status=None):
    """Validate required form fields. Optionally notify and update status on missing fields."""
    values = get_form_values(form_fields)
    missing_fields = [field for field in required_fields if not values.get(field)]
    if missing_fields:
        field_names = ", ".join(missing_fields)
        if notify:
            notify("Error", f"Please fill required fields: {field_names}", "error")
        if update_status:
            update_status(f"Please fill required fields: {field_names}", "error")
        return False
    return True


def show_error_dialog(title, message, notification_service=None):
    """Show error dialog to user, fallback to notification if provided."""
    from tkinter import messagebox
    try:
        messagebox.showerror(title, message)
    except Exception as e:
        logger.error(f"Failed to show error dialog: {e}")
        if notification_service:
            notification_service.notify("Error", f"{title}: {message}", "error")


def show_info_dialog(title, message, notification_service=None):
    """Show info dialog to user, fallback to notification if provided."""
    from tkinter import messagebox
    try:
        messagebox.showinfo(title, message)
    except Exception as e:
        logger.error(f"Failed to show info dialog: {e}")
        if notification_service:
            notification_service.notify("Info", f"{title}: {message}", "info")


def show_confirm_dialog(title, message, notification_service=None):
    """Show confirmation dialog to user, fallback to notification if provided."""
    from tkinter import messagebox
    try:
        return messagebox.askyesno(title, message)
    except Exception as e:
        logger.error(f"Failed to show confirm dialog: {e}")
        if notification_service:
            notification_service.notify("Info", f"{title}: {message}", "info")
        return False
