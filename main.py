"""
Main application entry point for Notes Overlay.
"""
import sys
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QRect
from PyQt6.QtGui import QScreen, QKeySequence, QShortcut

import config
from overlay_button import OverlayButton
from notes_window import NotesWindow
from notes_manager import NotesManager
from fullscreen_detector import FullscreenDetector
from theme_manager import ThemeManager


class OverlayMainWindow(QMainWindow):
    """Main overlay window that manages button and notes window."""
    
    def __init__(self):
        super().__init__()
        self._is_expanded = False
        self._is_hidden = False
        self._button_y = config.BUTTON_TOP_MARGIN
        self._drag_start_global_y = None
        self._drag_start_button_y = None
        self._notes_manager = NotesManager()
        self._fullscreen_detector = FullscreenDetector(self._on_fullscreen_change)
        
        self._setup_window()
        self._setup_widgets()
        self._setup_animations()
        self._setup_timers()
        self._setup_shortcuts()
        self._position_widgets()
        self._load_notes()
    
    def _setup_window(self):
        """Configure the main window properties."""
        # Make window frameless and always on top
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        
        # Enable transparency
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Make window click-through when collapsed (except button area)
        # We'll handle this dynamically
        
        # Set initial size to cover button area
        self.setFixedSize(config.BUTTON_WIDTH, config.BUTTON_HEIGHT)
    
    def _setup_widgets(self):
        """Create and setup UI widgets."""
        # Create overlay button
        self.button = OverlayButton(self)
        self.button.clicked.connect(self._toggle_expansion)
        self.button.dragStarted.connect(self._on_button_drag_started)
        self.button.dragMoved.connect(self._on_button_drag_moved)
        self.button.dragEnded.connect(self._on_button_drag_ended)
        
        # Create notes window as separate top-level window (initially hidden)
        self.notes_window = NotesWindow()
        self.notes_window.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.notes_window.content_changed.connect(self._on_notes_changed)
        self.notes_window.hide()
    
    def _setup_animations(self):
        """Setup expansion/collapse animations."""
        # Button position animation
        self._button_animation = QPropertyAnimation(self.button, b"geometry")
        self._button_animation.setDuration(config.ANIMATION_DURATION)
        self._button_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Notes window opacity animation
        self._notes_opacity_animation = QPropertyAnimation(self.notes_window, b"windowOpacity")
        self._notes_opacity_animation.setDuration(config.ANIMATION_DURATION)
        self._notes_opacity_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Notes window geometry animation
        self._notes_geometry_animation = QPropertyAnimation(self.notes_window, b"geometry")
        self._notes_geometry_animation.setDuration(config.ANIMATION_DURATION)
        self._notes_geometry_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Parallel animation group
        self._animation_group = QParallelAnimationGroup()
        self._animation_group.addAnimation(self._button_animation)
        self._animation_group.addAnimation(self._notes_opacity_animation)
        self._animation_group.addAnimation(self._notes_geometry_animation)
    
    def _setup_timers(self):
        """Setup periodic timers."""
        # Fullscreen detection timer
        self._fullscreen_timer = QTimer(self)
        self._fullscreen_timer.timeout.connect(self._check_fullscreen)
        self._fullscreen_timer.start(config.FULLSCREEN_CHECK_INTERVAL)
    
    def _setup_shortcuts(self):
        """Setup keyboard shortcuts."""
        self._visibility_shortcut = QShortcut(QKeySequence("Ctrl+Alt+N"), self)
        self._visibility_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self._visibility_shortcut.activated.connect(self._toggle_manual_visibility)
    
    def _position_widgets(self):
        """Position widgets on screen."""
        self._button_y = self._clamp_button_position(self._button_y)
        self._apply_button_position()
        self._position_notes_window()
    
    def _toggle_expansion(self):
        """Toggle between collapsed and expanded states."""
        if self._is_hidden:
            return
        if self._is_expanded:
            self._collapse()
        else:
            self._expand()
    
    def _expand(self):
        """Expand the notes window."""
        if self._is_expanded:
            return
        
        self._is_expanded = True
        
        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()
        
        # Calculate positions
        button_x = screen_geometry.width() - config.BUTTON_WIDTH
        button_y = self._button_y
        notes_x = button_x - config.NOTES_WINDOW_WIDTH
        notes_y = button_y
        
        # Show notes window
        self.notes_window.setWindowOpacity(0.0)
        self.notes_window.show()
        
        # Animate button (slight left movement)
        button_start = QRect(0, 0, config.BUTTON_WIDTH, config.BUTTON_HEIGHT)
        button_end = QRect(-5, 0, config.BUTTON_WIDTH, config.BUTTON_HEIGHT)
        
        # Animate notes window (fade in and slide from right)
        # Notes window is positioned on screen coordinates
        notes_start = QRect(
            button_x, notes_y,
            config.NOTES_WINDOW_WIDTH,
            config.NOTES_WINDOW_HEIGHT
        )
        notes_end = QRect(
            notes_x, notes_y,
            config.NOTES_WINDOW_WIDTH,
            config.NOTES_WINDOW_HEIGHT
        )
        
        # Main window stays the same size (only button window)
        # Don't animate main window for now - it stays button-sized
        
        # Setup animations
        self._button_animation.setStartValue(button_start)
        self._button_animation.setEndValue(button_end)
        
        self._notes_opacity_animation.setStartValue(0.0)
        self._notes_opacity_animation.setEndValue(1.0)
        
        self._notes_geometry_animation.setStartValue(notes_start)
        self._notes_geometry_animation.setEndValue(notes_end)
        
        # Remove window animation from group since we're not using it
        # Start animations
        self._animation_group.start()
    
    def _collapse(self):
        """Collapse the notes window."""
        if not self._is_expanded:
            return
        
        self._is_expanded = False
        
        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()
        
        # Calculate positions
        button_x = screen_geometry.width() - config.BUTTON_WIDTH
        button_y = self._button_y
        
        # Animate button back
        button_start = self.button.geometry()
        button_end = QRect(0, 0, config.BUTTON_WIDTH, config.BUTTON_HEIGHT)
        
        # Animate notes window (fade out and slide to right)
        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()
        button_x = screen_geometry.width() - config.BUTTON_WIDTH
        button_y = self._button_y
        
        notes_start = self.notes_window.geometry()
        notes_end = QRect(
            button_x, button_y,
            config.NOTES_WINDOW_WIDTH,
            config.NOTES_WINDOW_HEIGHT
        )
        
        # Setup animations
        self._button_animation.setStartValue(button_start)
        self._button_animation.setEndValue(button_end)
        
        self._notes_opacity_animation.setStartValue(1.0)
        self._notes_opacity_animation.setEndValue(0.0)
        
        self._notes_geometry_animation.setStartValue(notes_start)
        self._notes_geometry_animation.setEndValue(notes_end)
        
        # Start animations
        self._animation_group.start()
        
        # Hide notes window after animation completes
        def hide_notes():
            if not self._is_expanded:
                self.notes_window.hide()
        
        self._notes_opacity_animation.finished.connect(hide_notes)
    
    def _apply_button_position(self):
        """Move the overlay button window to the current Y coordinate."""
        screen_geometry = QApplication.primaryScreen().geometry()
        button_x = screen_geometry.width() - config.BUTTON_WIDTH
        self.move(button_x, self._button_y)
        self.button.move(0, 0)
    
    def _position_notes_window(self):
        """Align notes window with the button."""
        screen_geometry = QApplication.primaryScreen().geometry()
        button_x = screen_geometry.width() - config.BUTTON_WIDTH
        notes_x = button_x - config.NOTES_WINDOW_WIDTH
        self.notes_window.setGeometry(
            notes_x,
            self._button_y,
            config.NOTES_WINDOW_WIDTH,
            config.NOTES_WINDOW_HEIGHT
        )
    
    def _clamp_button_position(self, desired_y: int) -> int:
        """Keep button within the vertical bounds of the screen."""
        screen_geometry = QApplication.primaryScreen().geometry()
        max_y = screen_geometry.height() - config.BUTTON_HEIGHT
        return max(0, min(max_y, desired_y))
    
    def _on_button_drag_started(self, global_y: float):
        """Store initial positions at the start of a drag."""
        self._drag_start_global_y = global_y
        self._drag_start_button_y = self._button_y
    
    def _on_button_drag_moved(self, global_y: float):
        """Update button and notes positions while dragging."""
        if self._drag_start_global_y is None or self._drag_start_button_y is None:
            return
        delta = int(global_y - self._drag_start_global_y)
        new_y = self._clamp_button_position(self._drag_start_button_y + delta)
        if new_y == self._button_y:
            return
        self._button_y = new_y
        self._apply_button_position()
        self._position_notes_window()
    
    def _on_button_drag_ended(self):
        """Reset drag tracking when the drag finishes."""
        self._drag_start_global_y = None
        self._drag_start_button_y = None
    
    def _on_notes_changed(self, content: str):
        """Handle notes content change."""
        self._notes_manager.save_notes(content)
    
    def _load_notes(self):
        """Load saved notes."""
        content = self._notes_manager.get_notes()
        if content:
            self.notes_window.set_content(content)
    
    def _check_fullscreen(self):
        """Check for fullscreen applications."""
        self._fullscreen_detector.check_fullscreen()
    
    def _on_fullscreen_change(self, is_fullscreen: bool):
        """Handle fullscreen state change."""
        if is_fullscreen:
            # Hide overlay when fullscreen app is active
            if self.isVisible():
                self.hide()
        else:
            # Show overlay when exiting fullscreen
            if not self.isVisible() and not self._is_hidden:
                self.show()
                # Reposition in case screen resolution changed
                self._position_widgets()
    
    def resizeEvent(self, event):
        """Handle window resize."""
        super().resizeEvent(event)
        # Reposition widgets if needed
    
    def closeEvent(self, event):
        """Handle window close event."""
        # Save notes before closing
        content = self.notes_window.get_content()
        self._notes_manager.save_notes(content)
        event.accept()
    
    def _toggle_manual_visibility(self):
        """Hide or show the overlay via keyboard shortcut."""
        if self._is_hidden:
            self._is_hidden = False
            self.button.show()
            self.setWindowOpacity(1.0)
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
            if not self.isVisible():
                self.show()
            self._position_widgets()
        else:
            self._is_hidden = True
            if self._is_expanded:
                self._collapse()
            self.notes_window.hide()
            self.button.hide()
            self.setWindowOpacity(0.0)
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)


def main():
    """Application entry point."""
    app = QApplication(sys.argv)
    app.setApplicationName(config.APP_NAME)
    
    # High DPI scaling is enabled by default in PyQt6
    # No need to set AA_EnableHighDpiScaling or AA_UseHighDpiPixmaps
    
    window = OverlayMainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

