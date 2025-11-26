"""
Manages theme detection and color schemes for light/dark mode.
"""
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette
import config


class ThemeManager:
    """Manages application theme (light/dark mode)."""
    
    @staticmethod
    def is_dark_mode() -> bool:
        """Detect if system is in dark mode."""
        try:
            app = QApplication.instance()
            if app:
                palette = app.palette()
                window_color = palette.color(QPalette.ColorRole.Window)
                # Check if background is dark (lightness < 128)
                return window_color.lightness() < 128
        except:
            pass
        # Default to light mode if detection fails
        return False
    
    @staticmethod
    def get_bg_color() -> tuple:
        """Get background color based on current theme."""
        if ThemeManager.is_dark_mode():
            return config.COLOR_DARK_BG
        return config.COLOR_LIGHT_BG
    
    @staticmethod
    def get_text_color() -> tuple:
        """Get text color based on current theme."""
        if ThemeManager.is_dark_mode():
            return config.COLOR_DARK_TEXT
        return config.COLOR_LIGHT_TEXT
    
    @staticmethod
    def get_border_color(opacity: float = 1.0) -> tuple:
        """Get border color based on current theme."""
        if ThemeManager.is_dark_mode():
            return (100, 100, 100, int(150 * opacity))
        return (220, 220, 220, int(150 * opacity))

