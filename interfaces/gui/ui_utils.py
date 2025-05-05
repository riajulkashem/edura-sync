# interfaces/gui/ui_utils.py
"""
Utility functions for creating consistent UI components.
"""

import tkinter as tk
from tkinter import ttk
import logging
from typing import Dict, Any, Callable
from PIL import Image, ImageTk

from core.constants import UI_CONFIG

logger = logging.getLogger(__name__)


def create_window(parent: tk.Tk, title: str, size: str = None) -> tk.Toplevel:
    """
    Create a consistent toplevel window.

    Args:
        parent: Parent window
        title: Window title
        size: Window size, default from UI_CONFIG

    Returns:
        tk.Toplevel: Configured window
    """
    window = tk.Toplevel(parent)
    window.title(title)
    window.geometry(size or UI_CONFIG["DASHBOARD_SIZE"])
    window.resizable(False, False)
    return window


def setup_styles() -> ttk.Style:
    """
    Set up consistent styles for the application.

    Returns:
        ttk.Style: Configured style object
    """
    style = ttk.Style()
    style.configure("TLabel", padding=5, font=UI_CONFIG["DEFAULT_FONT"])
    style.configure("Header.TLabel", font=UI_CONFIG["HEADER_FONT"])
    style.configure("Good.TLabel", foreground="green")
    style.configure("Warning.TLabel", foreground="orange")
    style.configure("Error.TLabel", foreground="red")
    style.configure("Info.TLabel", foreground="blue")
    style.configure("Credits.TLabel", font=UI_CONFIG["DEFAULT_FONT"], padding=5)
    style.configure("CreditsLink.TLabel", font=UI_CONFIG["DEFAULT_FONT"], foreground="blue", padding=5)
    return style


def create_notebook(parent: tk.Widget) -> ttk.Notebook:
    """
    Create a notebook for tabbed interface.

    Args:
        parent: Parent widget

    Returns:
        ttk.Notebook: Configured notebook
    """
    notebook = ttk.Notebook(parent)
    notebook.pack(fill="both", expand=True, padx=10, pady=10)
    return notebook


def create_tab(notebook: ttk.Notebook, title: str) -> ttk.Frame:
    """
    Create a tab in the notebook.

    Args:
        notebook: Notebook widget
        title: Tab title

    Returns:
        ttk.Frame: Tab frame
    """
    frame = ttk.Frame(notebook, padding=10)
    notebook.add(frame, text=title)
    return frame


def load_icon(window: tk.Toplevel, icon_path) -> None:
    """
    Load and set the application icon for the window.

    Args:
        window: Window to set icon for
        icon_path: Path to icon file
    """
    try:
        if icon_path and icon_path.exists():
            img = Image.open(icon_path)
            photo = ImageTk.PhotoImage(img)
            window.iconphoto(True, photo)
            window._icon = photo  # Keep a reference to prevent garbage collection
            logger.info(f"Icon set for {window.title()}")
    except Exception as e:
        logger.error(f"Icon load failed: {e}")


def create_button(parent, text: str, command: Callable, padding: int = 8) -> ttk.Button:
    """
    Create a styled button.

    Args:
        parent: Parent widget
        text: Button text
        command: Button callback
        padding: Button padding

    Returns:
        ttk.Button: Configured button
    """
    return ttk.Button(
        parent,
        text=text,
        command=command,
        padding=padding
    )


def create_labeled_entry(parent, label_text: str, row: int,
                         show: str = None, width: int = 40) -> ttk.Entry:
    """
    Create a labeled entry field.

    Args:
        parent: Parent widget
        label_text: Label text
        row: Grid row
        show: Character to show for masked entries
        width: Entry width

    Returns:
        ttk.Entry: Entry widget
    """
    ttk.Label(parent, text=label_text).grid(
        row=row,
        column=0,
        sticky='w',
        pady=5,
        padx=5
    )

    entry = ttk.Entry(parent, width=width, show=show)
    entry.grid(
        row=row,
        column=1,
        sticky='we',
        pady=5,
        padx=5
    )
    return entry