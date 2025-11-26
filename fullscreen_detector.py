"""
Detects when fullscreen applications are active to hide the overlay.
"""
import win32gui
import win32con
import win32api
from typing import Callable, Optional
import config


class FullscreenDetector:
    """Monitors for fullscreen applications and notifies callbacks."""
    
    def __init__(self, on_fullscreen_change: Optional[Callable[[bool], None]] = None):
        self.on_fullscreen_change = on_fullscreen_change
        self._is_fullscreen = False
        self._last_foreground = None
    
    def check_fullscreen(self) -> bool:
        """
        Check if the current foreground window is fullscreen.
        Returns True if fullscreen, False otherwise.
        """
        try:
            hwnd = win32gui.GetForegroundWindow()
            if hwnd == 0:
                return False
            
            # Check if window is maximized
            placement = win32gui.GetWindowPlacement(hwnd)
            if placement[1] == win32con.SW_SHOWMAXIMIZED:
                # Check if it covers the entire screen
                window_rect = win32gui.GetWindowRect(hwnd)
                screen_width = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
                screen_height = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
                
                # Check if window covers entire screen (with small tolerance)
                tolerance = 10
                covers_screen = (
                    abs(window_rect[0]) <= tolerance and
                    abs(window_rect[1]) <= tolerance and
                    abs(window_rect[2] - screen_width) <= tolerance and
                    abs(window_rect[3] - screen_height) <= tolerance
                )
                
                # Also check if window has no title bar (common in fullscreen apps)
                style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
                has_title_bar = bool(style & win32con.WS_CAPTION)
                
                is_fullscreen = covers_screen or not has_title_bar
                
                # Notify if state changed
                if is_fullscreen != self._is_fullscreen:
                    self._is_fullscreen = is_fullscreen
                    if self.on_fullscreen_change:
                        self.on_fullscreen_change(is_fullscreen)
                
                return is_fullscreen
            else:
                if self._is_fullscreen:
                    self._is_fullscreen = False
                    if self.on_fullscreen_change:
                        self.on_fullscreen_change(False)
                return False
                
        except Exception as e:
            print(f"Error checking fullscreen: {e}")
            return False
    
    def is_fullscreen(self) -> bool:
        """Get current fullscreen state."""
        return self._is_fullscreen

