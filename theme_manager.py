"""
Comprehensive theme management system with Windows system theme detection,
theme storage, and live theme application.
"""
import json
import os
from pathlib import Path
from typing import Dict, Optional, Callable, List
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtGui import QColor
import config
from theme_presets import ThemePresets
from theme_presets import ThemePresets

try:
    import winreg
    WINDOWS_REGISTRY_AVAILABLE = True
except ImportError:
    WINDOWS_REGISTRY_AVAILABLE = False


class ThemeManager(QObject):
    """Manages application theme with system detection, persistence, and customization."""
    
    # Signal emitted when theme changes
    theme_changed = pyqtSignal()
    
    # Default theme definitions
    DEFAULT_LIGHT_THEME = {
        "window_bg": "#f5f5f5",
        "window_bg_opacity": 240,
        "text_primary": "#000000",
        "text_secondary": "#666666",
        "border_color": "#c8c8c8",
        "window_border_color": "#c8c8c8",
        "accent_color": "#0078d7",
        "title_bar_color": "#f5f5f5",
        "tab_bg_active": "#f5f5f5",
        "tab_bg_inactive": "#e6e6e6",
        "tab_text_color": "#000000",
        "scrollbar_color": "#b4b4b4",
        "button_bg": "#f0f0f0",
        "button_text": "#000000",
        "button_hover": "#e0e0e0",
        "button_border": "#c8c8c8",
        "window_opacity": 95,
        "blur_enabled": True,
        "blur_intensity": 10,
        "shadow_intensity": 3,
        "border_radius": 12,
        "font_family": "Segoe UI",
        "font_size": 11,
    }
    
    DEFAULT_DARK_THEME = {
        "window_bg": "#202020",
        "window_bg_opacity": 240,
        "text_primary": "#ffffff",
        "text_secondary": "#b3b3b3",
        "border_color": "#646464",
        "window_border_color": "#646464",
        "accent_color": "#0078d7",
        "title_bar_color": "#202020",
        "tab_bg_active": "#202020",
        "tab_bg_inactive": "#323232",
        "tab_text_color": "#ffffff",
        "scrollbar_color": "#646464",
        "button_bg": "#3c3c3c",
        "button_text": "#ffffff",
        "button_hover": "#505050",
        "button_border": "#646464",
        "window_opacity": 95,
        "blur_enabled": True,
        "blur_intensity": 10,
        "shadow_intensity": 3,
        "border_radius": 12,
        "font_family": "Segoe UI",
        "font_size": 11,
    }
    
    _instance: Optional['ThemeManager'] = None
    
    def __init__(self):
        super().__init__()
        if ThemeManager._instance is not None:
            raise RuntimeError("ThemeManager is a singleton. Use get_instance()")
        
        self._follow_system_theme = True
        self._current_theme_mode = "dark"  # "light", "dark", or "custom"
        self._custom_theme: Dict = {}
        self._config_file = config.DATA_DIR / "theme_config.json"
        self._theme_listeners: List[Callable] = []
        
        # Load saved theme or use defaults
        self._load_theme()
        
        # Monitor system theme changes
        self._system_theme_timer = QTimer()
        self._system_theme_timer.timeout.connect(self._check_system_theme_change)
        self._system_theme_timer.start(1000)  # Check every second
        self._last_system_theme = self._detect_windows_theme()
        
        ThemeManager._instance = self
    
    @classmethod
    def get_instance(cls) -> 'ThemeManager':
        """Get the singleton instance of ThemeManager."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def _detect_windows_theme(self) -> str:
        """Detect Windows system theme using Registry."""
        if not WINDOWS_REGISTRY_AVAILABLE:
            # Fallback to QPalette method
            try:
                from PyQt6.QtWidgets import QApplication
                from PyQt6.QtGui import QPalette
                app = QApplication.instance()
                if app:
                    palette = app.palette()
                    window_color = palette.color(QPalette.ColorRole.Window)
                    return "dark" if window_color.lightness() < 128 else "light"
            except:
                pass
            return "light"
        
        try:
            # Check Windows 10/11 theme preference
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
            )
            try:
                value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                winreg.CloseKey(key)
                return "light" if value == 1 else "dark"
            except FileNotFoundError:
                winreg.CloseKey(key)
                # Try alternative registry path
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Themes"
                )
                try:
                    value, _ = winreg.QueryValueEx(key, "CurrentTheme")
                    winreg.CloseKey(key)
                    # Theme names often contain "dark" or "light"
                    theme_name = value.lower()
                    return "dark" if "dark" in theme_name else "light"
                except:
                    if key:
                        winreg.CloseKey(key)
                    return "light"
        except Exception as e:
            print(f"Error detecting Windows theme: {e}")
            return "light"
    
    def _check_system_theme_change(self):
        """Check if system theme has changed and update if following system theme."""
        if not self._follow_system_theme:
            return
        
        current_system_theme = self._detect_windows_theme()
        if current_system_theme != self._last_system_theme:
            self._last_system_theme = current_system_theme
            self._current_theme_mode = current_system_theme
            self._apply_theme()
            self.theme_changed.emit()
    
    def _load_theme(self):
        """Load theme from config file."""
        if not self._config_file.exists():
            # Use system theme as default
            system_theme = self._detect_windows_theme()
            self._current_theme_mode = system_theme
            self._follow_system_theme = True
            return
        
        try:
            with open(self._config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self._follow_system_theme = data.get("follow_system_theme", True)
            self._current_theme_mode = data.get("current_theme", "dark")
            self._custom_theme = data.get("custom_theme", {})
            
            # If following system theme, update to current system theme
            if self._follow_system_theme:
                self._current_theme_mode = self._detect_windows_theme()
            
        except Exception as e:
            print(f"Error loading theme config: {e}")
            # Use defaults
            self._follow_system_theme = True
            self._current_theme_mode = self._detect_windows_theme()
    
    def save_theme(self):
        """Save current theme to config file."""
        try:
            data = {
                "follow_system_theme": self._follow_system_theme,
                "current_theme": self._current_theme_mode,
                "custom_theme": self._custom_theme.copy() if self._custom_theme else {}
            }
            
            with open(self._config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving theme config: {e}")
    
    def get_theme(self) -> Dict:
        """Get current theme dictionary."""
        if self._current_theme_mode == "custom" and self._custom_theme:
            # Merge custom theme with defaults to ensure all keys exist
            base_theme = self.DEFAULT_DARK_THEME.copy()
            base_theme.update(self._custom_theme)
            return base_theme
        elif self._current_theme_mode == "light":
            return self.DEFAULT_LIGHT_THEME.copy()
        else:  # dark
            return self.DEFAULT_DARK_THEME.copy()
    
    def set_theme_property(self, key: str, value):
        """Set a theme property and apply immediately."""
        if self._current_theme_mode != "custom":
            # Switch to custom mode
            self._current_theme_mode = "custom"
            # Initialize custom theme with current theme
            self._custom_theme = self.get_theme().copy()
        
        self._custom_theme[key] = value
        self._apply_theme()
        self.theme_changed.emit()
    
    def set_follow_system_theme(self, follow: bool):
        """Set whether to follow system theme."""
        self._follow_system_theme = follow
        if follow:
            self._current_theme_mode = self._detect_windows_theme()
            self._apply_theme()
            self.theme_changed.emit()
        self.save_theme()
    
    def set_theme_mode(self, mode: str):
        """Set theme mode: 'light', 'dark', or 'custom'."""
        if mode not in ["light", "dark", "custom"]:
            return
        
        self._current_theme_mode = mode
        if mode != "custom":
            self._follow_system_theme = False
        
        self._apply_theme()
        self.theme_changed.emit()
        self.save_theme()
    
    def set_custom_theme(self, theme: Dict):
        """Set a complete custom theme."""
        self._current_theme_mode = "custom"
        self._follow_system_theme = False
        self._custom_theme = theme.copy()
        self._apply_theme()
        self.theme_changed.emit()
        self.save_theme()
    
    def apply_preset(self, preset_id: str):
        """Apply a theme preset by ID."""
        preset = ThemePresets.get_preset_by_id(preset_id)
        if preset:
            # Remove metadata fields (id, name, category, mode)
            theme_data = {k: v for k, v in preset.items() 
                         if k not in ["id", "name", "category", "mode"]}
            self.set_custom_theme(theme_data)
            # Store preset ID for reference
            self._current_preset_id = preset_id
        else:
            print(f"Preset '{preset_id}' not found")
    
    def get_current_preset_id(self) -> Optional[str]:
        """Get the ID of the currently applied preset, if any."""
        return getattr(self, '_current_preset_id', None)
    
    def reset_to_default(self):
        """Reset to default theme based on current mode."""
        if self._current_theme_mode == "light":
            self._custom_theme = {}
        elif self._current_theme_mode == "dark":
            self._custom_theme = {}
        else:
            # Reset custom theme to default dark
            self._custom_theme = {}
            self._current_theme_mode = "dark"
        
        self._apply_theme()
        self.theme_changed.emit()
        self.save_theme()
    
    def export_theme(self, file_path: str) -> bool:
        """Export current theme to a JSON file."""
        try:
            theme = self.get_theme()
            data = {
                "theme_name": "Custom Theme",
                "version": "1.0",
                "theme": theme
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            print(f"Error exporting theme: {e}")
            return False
    
    def import_theme(self, file_path: str) -> bool:
        """Import theme from a JSON file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Support different JSON structures
            if "theme" in data:
                theme = data["theme"]
            elif "custom_theme" in data:
                theme = data["custom_theme"]
            else:
                # Assume the whole file is the theme
                theme = data
            
            # Validate theme has required keys
            default_keys = set(self.DEFAULT_DARK_THEME.keys())
            theme_keys = set(theme.keys())
            
            if not default_keys.issubset(theme_keys):
                # Fill missing keys with defaults
                for key in default_keys:
                    if key not in theme:
                        theme[key] = self.DEFAULT_DARK_THEME[key]
            
            self.set_custom_theme(theme)
            return True
        except Exception as e:
            print(f"Error importing theme: {e}")
            return False
    
    def _apply_theme(self):
        """Apply theme to all registered listeners."""
        for listener in self._theme_listeners:
            try:
                listener()
            except Exception as e:
                print(f"Error applying theme to listener: {e}")
    
    def register_listener(self, callback: Callable):
        """Register a callback to be called when theme changes."""
        if callback not in self._theme_listeners:
            self._theme_listeners.append(callback)
    
    def unregister_listener(self, callback: Callable):
        """Unregister a theme change callback."""
        if callback in self._theme_listeners:
            self._theme_listeners.remove(callback)
    
    # Convenience methods for backward compatibility
    @staticmethod
    def is_dark_mode() -> bool:
        """Check if current theme is dark mode."""
        instance = ThemeManager.get_instance()
        theme = instance.get_theme()
        # Check background color lightness
        bg_color = QColor(theme["window_bg"])
        return bg_color.lightness() < 128
    
    @staticmethod
    def get_bg_color() -> tuple:
        """Get background color as RGBA tuple."""
        instance = ThemeManager.get_instance()
        theme = instance.get_theme()
        color = QColor(theme["window_bg"])
        opacity = theme.get("window_bg_opacity", 240)
        return (color.red(), color.green(), color.blue(), opacity)
    
    @staticmethod
    def get_text_color() -> tuple:
        """Get text color as RGBA tuple."""
        instance = ThemeManager.get_instance()
        theme = instance.get_theme()
        color = QColor(theme["text_primary"])
        return (color.red(), color.green(), color.blue(), 255)
    
    @staticmethod
    def get_border_color(opacity: float = 1.0) -> tuple:
        """Get border color as RGBA tuple."""
        instance = ThemeManager.get_instance()
        theme = instance.get_theme()
        color = QColor(theme["border_color"])
        alpha = int(150 * opacity)
        return (color.red(), color.green(), color.blue(), alpha)
