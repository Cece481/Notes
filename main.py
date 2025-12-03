"""
Main application entry point for Notes Overlay.
"""
import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QSystemTrayIcon, QMenu
from PyQt6.QtCore import (
    Qt,
    QTimer,
    QPropertyAnimation,
    QEasingCurve,
    QParallelAnimationGroup,
    QRect,
    QSettings,
)
from PyQt6.QtGui import QScreen, QKeySequence, QShortcut, QCursor, QIcon, QPixmap, QPainter, QColor

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
        self._button_side = "right"  # "left" or "right"
        self._current_screen = None  # Track which screen the button is on
        self._drag_start_global_y = None
        self._drag_start_button_y = None
        # Settings for persisting button side preference
        self._settings = QSettings("NotesOverlay", config.APP_NAME)
        self._notes_manager = NotesManager()
        self._fullscreen_detector = FullscreenDetector(self._on_fullscreen_change)
        
        self._setup_window()
        self._setup_widgets()
        self._setup_animations()
        self._setup_timers()
        self._setup_system_tray()
        self._load_button_side()
        self._detect_current_screen()  # Detect which screen button is on
        self._position_widgets()
        self._load_notes()
        # Setup shortcuts AFTER everything else is initialized
        self._setup_shortcuts()
        # Monitor screen changes
        self._setup_screen_monitoring()
    
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
    
    def _setup_system_tray(self):
        """Setup system tray icon with context menu."""
        # Load icon from app.ico file in the same folder as main.py
        import os
        
        # Get the directory where main.py is located
        current_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(current_dir, "app.ico")
        
        # Try to load the icon file, fall back to generated icon if file not found
        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
            print(f"Loaded icon from: {icon_path}")
        else:
            print(f"Warning: app.ico not found at {icon_path}, using generated icon")
            icon = self._create_tray_icon()
        
        # Create system tray icon
        self.tray_icon = QSystemTrayIcon(icon, self)
        
        # Create context menu
        tray_menu = QMenu()
        
        # Add Show/Hide action
        self.show_hide_action = tray_menu.addAction("Show/Hide Overlay")
        self.show_hide_action.triggered.connect(self._toggle_manual_visibility)
        
        # Add separator
        tray_menu.addSeparator()
        
        # Add Exit action
        exit_action = tray_menu.addAction("Exit")
        exit_action.triggered.connect(self._exit_application)
        
        # Set the menu to the tray icon
        self.tray_icon.setContextMenu(tray_menu)
        
        # Optional: Add double-click functionality
        self.tray_icon.activated.connect(self._on_tray_activated)
        
        # Show the tray icon
        self.tray_icon.show()
        
        # Show a message when the app starts (optional)
        self.tray_icon.showMessage(
            "Notes Overlay",
            "Application is running in the system tray.\nPress Ctrl+Alt+N to toggle visibility.",
            QSystemTrayIcon.MessageIcon.Information,
            2000
        )
    
    def _create_tray_icon(self):
        """Create a simple tray icon programmatically."""
        # Create a 64x64 pixmap with a simple icon design
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw a simple notepad icon
        # Background
        painter.setBrush(QColor(70, 130, 180))
        painter.setPen(QColor(50, 100, 150))
        painter.drawRoundedRect(12, 8, 40, 48, 4, 4)
        
        # Lines to represent text
        painter.setPen(QColor(255, 255, 255))
        painter.drawLine(18, 20, 46, 20)
        painter.drawLine(18, 28, 46, 28)
        painter.drawLine(18, 36, 40, 36)
        painter.drawLine(18, 44, 46, 44)
        
        painter.end()
        
        return QIcon(pixmap)
    
    def _on_tray_activated(self, reason):
        """Handle system tray icon activation (clicks)."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            # Double-click to toggle visibility
            self._toggle_manual_visibility()
    
    def _exit_application(self):
        """Exit the application completely."""
        # Save notes before exiting
        content = self.notes_window.get_content()
        self._notes_manager.save_notes(content)
        
        # Hide tray icon
        self.tray_icon.hide()
        
        # Quit the application
        QApplication.quit()
    
    def _setup_animations(self):
        """Setup expansion/collapse animations."""
        # Button position animation
        self._button_animation = QPropertyAnimation(self.button, b"geometry")
        self._button_animation.setDuration(config.ANIMATION_DURATION)
        self._button_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Snap animation for the overlay window (button container)
        self._snap_animation = QPropertyAnimation(self, b"pos")
        self._snap_animation.setDuration(config.ANIMATION_DURATION)
        self._snap_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._snap_animation.finished.connect(self._position_notes_window)
        
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
        # Use QApplication as parent to make shortcut truly global
        self._visibility_shortcut = QShortcut(QKeySequence("Ctrl+Alt+N"), QApplication.instance())
        self._visibility_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self._visibility_shortcut.activated.connect(self._toggle_manual_visibility)
        
        # Also register on notes window as backup
        self._visibility_shortcut_notes = QShortcut(QKeySequence("Ctrl+Alt+N"), self.notes_window)
        self._visibility_shortcut_notes.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self._visibility_shortcut_notes.activated.connect(self._toggle_manual_visibility)
    
    def _setup_screen_monitoring(self):
        """Setup monitoring for screen configuration changes."""
        # Connect to screen added/removed signals
        app = QApplication.instance()
        app.screenAdded.connect(self._on_screen_configuration_changed)
        app.screenRemoved.connect(self._on_screen_configuration_changed)
        
        # Monitor primary screen changes
        app.primaryScreenChanged.connect(self._on_screen_configuration_changed)
    
    def _detect_current_screen(self):
        """Detect which screen the button is currently on."""
        button_center = self.geometry().center()
        
        for screen in QApplication.screens():
            if screen.geometry().contains(button_center):
                self._current_screen = screen
                return
        
        # Fallback to primary screen if not found
        self._current_screen = QApplication.primaryScreen()
    
    def _get_current_screen(self):
        """Get the screen that the button is currently on."""
        if self._current_screen is None:
            self._detect_current_screen()
        return self._current_screen
    
    def _on_screen_configuration_changed(self, screen=None):
        """Handle screen configuration changes (added/removed/changed)."""
        # Re-detect current screen
        self._detect_current_screen()
        
        # Reposition widgets to ensure they're still on a valid screen
        self._position_widgets()
        
        # If expanded, reposition notes window as well
        if self._is_expanded:
            self._position_notes_window()
    
    def _position_widgets(self):
        """Position widgets on screen."""
        screen = self._get_current_screen()
        screen_geometry = screen.geometry()
        
        # Clamp button position to current screen bounds
        max_y = screen_geometry.height() - config.BUTTON_HEIGHT
        self._button_y = max(0, min(max_y, self._button_y))
        
        self._apply_button_position()
        self._position_notes_window()

    def _load_button_side(self):
        """Load persisted button side (left/right)."""
        side = self._settings.value("button_side", "right")
        if side in ("left", "right"):
            self._button_side = side
        else:
            self._button_side = "right"

    def _save_button_side(self):
        """Persist current button side."""
        self._settings.setValue("button_side", self._button_side)
    
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
        
        screen = self._get_current_screen()
        screen_geometry = screen.geometry()
        screen_width = screen_geometry.width()

        # Calculate button X based on side (do NOT move the button vertically)
        if self._button_side == "right":
            button_x = screen_geometry.x() + screen_width - config.BUTTON_WIDTH
        else:
            button_x = screen_geometry.x()

        # Target geometry for notes window that keeps it on-screen
        notes_target_geom = self._compute_notes_target_geometry()
        
        # Show notes window
        self.notes_window.setWindowOpacity(0.0)
        self.notes_window.show()
        
        # Animate button - direction depends on which side it's on
        button_start = QRect(0, 0, config.BUTTON_WIDTH, config.BUTTON_HEIGHT)
        if self._button_side == "right":
            # Right side: shift RIGHT (positive X)
            button_end = QRect(5, 0, config.BUTTON_WIDTH, config.BUTTON_HEIGHT)
        else:
            # Left side: shift LEFT (negative X)
            button_end = QRect(-5, 0, config.BUTTON_WIDTH, config.BUTTON_HEIGHT)
        
        # Animate notes window (fade in and slide from appropriate side)
        # Notes window is positioned on screen coordinates
        notes_start = QRect(
            button_x, notes_target_geom.y(),
            config.NOTES_WINDOW_WIDTH,
            config.NOTES_WINDOW_HEIGHT
        )
        notes_end = notes_target_geom
        
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
        
        screen = self._get_current_screen()
        screen_geometry = screen.geometry()
        screen_width = screen_geometry.width()

        # Calculate positions based on which side the button is on
        if self._button_side == "right":
            button_x = screen_geometry.x() + screen_width - config.BUTTON_WIDTH
            notes_end_x = button_x
        else:
            button_x = screen_geometry.x()
            notes_end_x = button_x - config.NOTES_WINDOW_WIDTH

        button_y = self._button_y
        
        # Animate button back
        button_start = self.button.geometry()
        button_end = QRect(0, 0, config.BUTTON_WIDTH, config.BUTTON_HEIGHT)
        
        notes_start = self.notes_window.geometry()
        notes_end = QRect(
            notes_end_x, button_y,
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
        screen = self._get_current_screen()
        screen_geometry = screen.geometry()
        
        if self._button_side == "right":
            button_x = screen_geometry.x() + screen_geometry.width() - config.BUTTON_WIDTH
        else:
            button_x = screen_geometry.x()
        
        self.move(button_x, screen_geometry.y() + self._button_y)
        self.button.move(0, 0)

    def _compute_notes_target_geometry(self):
        """
        Compute a notes window geometry that keeps it fully on-screen and
        positioned next to the button.
        Default: open below the button; if there isn't enough space below,
        open above instead.
        """
        screen = self._get_current_screen()
        screen_geometry = screen.geometry()
        screen_width = screen_geometry.width()
        screen_height = screen_geometry.height()

        # Button position and size (relative to current screen)
        if self._button_side == "right":
            button_x = screen_geometry.x() + screen_width - config.BUTTON_WIDTH
        else:
            button_x = screen_geometry.x()
        button_y = screen_geometry.y() + self._button_y
        button_top = button_y
        button_bottom = button_y + config.BUTTON_HEIGHT

        # Available vertical space (relative to current screen)
        space_above = self._button_y
        space_below = screen_height - (self._button_y + config.BUTTON_HEIGHT)

        # Decide whether to show notes above or below the button
        if space_below < config.NOTES_WINDOW_HEIGHT:
            # Not enough space below; show entirely above the button
            notes_y = max(screen_geometry.y(), button_top - (config.NOTES_WINDOW_HEIGHT - config.BUTTON_HEIGHT))
        else:
            # Default: place top of notes at the bottom of the button, clamped to screen
            notes_y = min(button_bottom - config.BUTTON_HEIGHT, 
                         screen_geometry.y() + screen_height - config.NOTES_WINDOW_HEIGHT)

        # Horizontal positioning based on button side
        if self._button_side == "right":
            preferred_x = button_x - config.NOTES_WINDOW_WIDTH
        else:
            preferred_x = button_x + config.BUTTON_WIDTH

        # Clamp horizontally so window stays fully on current screen
        notes_x = max(screen_geometry.x(), 
                     min(screen_geometry.x() + screen_width - config.NOTES_WINDOW_WIDTH, preferred_x))

        return QRect(
            notes_x,
            notes_y,
            config.NOTES_WINDOW_WIDTH,
            config.NOTES_WINDOW_HEIGHT,
        )

    def _position_notes_window(self):
        """Align notes window with the button, keeping it fully on-screen."""
        target_geom = self._compute_notes_target_geometry()
        self.notes_window.setGeometry(target_geom)
    
    def _clamp_button_position(self, desired_y: int) -> int:
        """Keep button within the vertical bounds of the current screen."""
        screen = self._get_current_screen()
        screen_geometry = screen.availableGeometry()
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
        
        # Get cursor position to detect which screen we're on
        cursor_pos = QCursor.pos()
        
        # Detect which screen the cursor is currently on
        for screen in QApplication.screens():
            if screen.geometry().contains(cursor_pos):
                self._current_screen = screen
                break
        
        screen_geometry = self._get_current_screen().geometry()
        screen_width = screen_geometry.width()
        screen_height = screen_geometry.height()
        
        # Vertical movement (adjusted for screen position)
        delta = int(global_y - self._drag_start_global_y)
        new_y = self._clamp_button_position(self._drag_start_button_y + delta)
        self._button_y = new_y

        # Horizontal movement follows the cursor during drag
        # Center button on cursor X while keeping it on current screen
        tentative_x = int(cursor_pos.x() - config.BUTTON_WIDTH / 2)
        tentative_x = max(screen_geometry.x(), 
                         min(screen_geometry.x() + screen_width - config.BUTTON_WIDTH, tentative_x))
        
        self.move(tentative_x, screen_geometry.y() + self._button_y)
        self.button.move(0, 0)
        self._position_notes_window()
    
    def _on_button_drag_ended(self):
        """Reset drag tracking when the drag finishes."""
        self._drag_start_global_y = None
        self._drag_start_button_y = None

        # Decide which side to snap to based on final horizontal position on current screen
        screen = self._get_current_screen()
        screen_geometry = screen.geometry()
        screen_center_x = screen_geometry.x() + (screen_geometry.width() / 2)
        button_center_x = self.x() + (config.BUTTON_WIDTH / 2)

        if button_center_x < screen_center_x:
            self._button_side = "left"
        else:
            self._button_side = "right"

        self._save_button_side()
        self._snap_button_to_current_side()

    def _snap_button_to_current_side(self):
        """Animate button snapping to the nearest screen edge while keeping Y."""
        screen = self._get_current_screen()
        screen_geometry = screen.geometry()
        
        if self._button_side == "right":
            target_x = screen_geometry.x() + screen_geometry.width() - config.BUTTON_WIDTH
        else:
            target_x = screen_geometry.x()

        start_pos = self.pos()
        end_pos = start_pos
        end_pos.setX(int(target_x))

        self._snap_animation.stop()
        self._snap_animation.setStartValue(start_pos)
        self._snap_animation.setEndValue(end_pos)
        self._snap_animation.start()
    
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
        # Instead of closing, just hide to system tray
        if self.tray_icon.isVisible():
            event.ignore()
            self.hide()
            self.notes_window.hide()
            self.tray_icon.showMessage(
                "Notes Overlay",
                "Application minimized to tray. Right-click the tray icon to exit.",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )
        else:
            # If tray icon is not visible, allow close
            content = self.notes_window.get_content()
            self._notes_manager.save_notes(content)
            event.accept()
    
    def _toggle_manual_visibility(self):
        """Hide or show the overlay via keyboard shortcut."""
        print("DEBUG: Ctrl+Alt+N shortcut triggered!")  # Debug line
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
    
    # Prevent application from quitting when main window is closed
    app.setQuitOnLastWindowClosed(False)
    
    # High DPI scaling is enabled by default in PyQt6
    # No need to set AA_EnableHighDpiScaling or AA_UseHighDpiPixmaps
    
    window = OverlayMainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()