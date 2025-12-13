"""
Main application entry point for Notes Overlay.
"""
import sys
import os
import ctypes
from ctypes import wintypes
from PyQt6.QtWidgets import QApplication, QMainWindow, QSystemTrayIcon, QMenu
from PyQt6.QtCore import (
    Qt,
    QTimer,
    QPropertyAnimation,
    QEasingCurve,
    QParallelAnimationGroup,
    QSequentialAnimationGroup,
    QRect,
    QSettings,
    QPoint,
    QSize,
    QAbstractNativeEventFilter,
)
from PyQt6.QtGui import QScreen, QKeySequence, QShortcut, QCursor, QIcon, QPixmap, QPainter, QColor, QAction

import config
from overlay_button import OverlayButton
from notes_window import NotesWindow
from notes_manager import NotesManager
from fullscreen_detector import FullscreenDetector
from theme_manager import ThemeManager
from settings_window import SettingsWindow

# Windows API constants for global hotkey
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_NOREPEAT = 0x4000  # Prevent repeated firing when key is held
VK_N = 0x4E  # Virtual key code for 'N'
WM_HOTKEY = 0x0312
HOTKEY_ID = 1  # Unique ID for our hotkey


class GlobalHotkeyFilter(QAbstractNativeEventFilter):
    """Native event filter to catch global hotkey messages from Windows."""
    
    def __init__(self, callback):
        super().__init__()
        self.callback = callback
    
    def nativeEventFilter(self, eventType, message):
        """Filter native Windows messages for WM_HOTKEY."""
        try:
            if eventType == b"windows_generic_MSG":
                # Parse the MSG structure
                msg = ctypes.wintypes.MSG.from_address(int(message))
                if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
                    # Our hotkey was pressed!
                    if self.callback:
                        self.callback()
                    return True, 0  # Message handled
        except Exception as e:
            print(f"Error in native event filter: {e}")
        return False, 0  # Let Qt handle other messages


def get_icon_path():
    """
    Get the correct absolute path to app.ico.
    Works both during development and after installation as frozen executable.
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled .exe (PyInstaller)
        # sys.executable gives the full path to the .exe file
        # Example: C:\Program Files\NotesOverlay\NotesOverlay.exe
        application_path = os.path.dirname(sys.executable)
    else:
        # Running as a Python script during development
        application_path = os.path.dirname(os.path.abspath(__file__))
    
    # Build the full path to app.ico
    icon_path = os.path.join(application_path, 'app.ico')
    
    return icon_path


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
        self._is_dragging = False
        self._target_notes_geometry = None  # Target position for smooth following
        self._last_window_side = None  # Track if window was above or below button
        self._reposition_cooldown = False  # Prevent animation spam
        # Settings for persisting button side preference
        self._settings = QSettings("NotesOverlay", config.APP_NAME)
        self._notes_manager = NotesManager()
        self._fullscreen_detector = FullscreenDetector(self._on_fullscreen_change)
        
        # Initialize ThemeManager singleton
        self._theme_manager = ThemeManager.get_instance()
        
        self._setup_window()
        self._setup_widgets()
        self._setup_animations()
        self._setup_timers()
        self._setup_system_tray()
        
        # Create settings window (initially hidden)
        self.settings_window = SettingsWindow()
        self.settings_window.hide()
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
        self.button.rightClicked.connect(self._show_button_context_menu)
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
        # Get the correct icon path (works both in development and after installation)
        icon_path = get_icon_path()
        
        # Try to load the icon file, fall back to generated icon if file not found
        if icon_path and os.path.exists(icon_path):
            icon = QIcon(icon_path)
            print(f"Loaded icon from: {icon_path}")
        else:
            # Log detailed debug info when icon is not found
            print(f"Warning: app.ico not found at {icon_path}")
            print(f"  Executable: {sys.executable}")
            print(f"  Frozen: {getattr(sys, 'frozen', False)}")
            print(f"  Current dir: {os.getcwd()}")
            icon = self._create_tray_icon()
        
        # Create system tray icon
        self.tray_icon = QSystemTrayIcon(icon, self)
        
        # Create context menu
        tray_menu = QMenu()
        
        # Add Show/Hide action
        self.show_hide_action = tray_menu.addAction("Show/Hide Overlay")
        self.show_hide_action.triggered.connect(self._toggle_manual_visibility)
        
        # Add Settings action
        settings_action = tray_menu.addAction("Settings")
        settings_action.triggered.connect(self._show_settings)
        
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
        
        # Unregister global hotkey
        self._unregister_hotkey()
        
        # Hide tray icon
        self.tray_icon.hide()
        
        # Quit the application
        QApplication.quit()
    
    def _unregister_hotkey(self):
        """Unregister the global hotkey."""
        if hasattr(self, '_hotkey_registered') and self._hotkey_registered:
            try:
                ctypes.windll.user32.UnregisterHotKey(None, HOTKEY_ID)
                print("Global hotkey unregistered")
            except Exception as e:
                print(f"Error unregistering hotkey: {e}")
        
        # Remove native event filter
        if hasattr(self, '_hotkey_filter') and self._hotkey_filter:
            try:
                QApplication.instance().removeNativeEventFilter(self._hotkey_filter)
            except Exception as e:
                print(f"Error removing event filter: {e}")
    
    def _setup_animations(self):
        """Setup expansion/collapse animations with Windows 11 style bounce effects."""
        # Animation durations
        self._expand_duration = 400  # Slightly longer for smooth entrance
        self._collapse_duration = 300  # Faster exit
        
        # Button position animation
        self._button_animation = QPropertyAnimation(self.button, b"geometry")
        self._button_animation.setDuration(self._expand_duration)
        self._button_animation.setEasingCurve(QEasingCurve.Type.OutBack)  # Bounce effect

        # Snap animation for the overlay window (button container)
        self._snap_animation = QPropertyAnimation(self, b"pos")
        self._snap_animation.setDuration(config.ANIMATION_DURATION)
        self._snap_animation.setEasingCurve(QEasingCurve.Type.OutBack)  # Bounce snap
        # Note: Window animation is now handled in _snap_button_to_current_side via _animate_window_snap_sync
        
        # Notes window opacity animation
        self._notes_opacity_animation = QPropertyAnimation(self.notes_window, b"windowOpacity")
        self._notes_opacity_animation.setDuration(self._expand_duration)
        self._notes_opacity_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Notes window geometry animation with bounce
        self._notes_geometry_animation = QPropertyAnimation(self.notes_window, b"geometry")
        self._notes_geometry_animation.setDuration(self._expand_duration)
        self._notes_geometry_animation.setEasingCurve(QEasingCurve.Type.OutBack)  # Bounce effect
        
        # Parallel animation group for expansion
        self._animation_group = QParallelAnimationGroup()
        self._animation_group.addAnimation(self._button_animation)
        self._animation_group.addAnimation(self._notes_opacity_animation)
        self._animation_group.addAnimation(self._notes_geometry_animation)
        
        # Collapse animation group (faster, ease-in)
        self._collapse_animation_group = QParallelAnimationGroup()
        
        # Smooth window following animation during drag
        self._follow_animation = QPropertyAnimation(self.notes_window, b"geometry")
        self._follow_animation.setDuration(350)
        self._follow_animation.setEasingCurve(QEasingCurve.Type.OutBack)  # Bounce for repositioning
        
        # Timer for smooth following with slight trail effect (~60fps)
        self._follow_timer = QTimer(self)
        self._follow_timer.setInterval(16)  # ~60fps
        self._follow_timer.timeout.connect(self._update_window_follow)
    
    def _setup_timers(self):
        """Setup periodic timers."""
        # Fullscreen detection timer
        self._fullscreen_timer = QTimer(self)
        self._fullscreen_timer.timeout.connect(self._check_fullscreen)
        self._fullscreen_timer.start(config.FULLSCREEN_CHECK_INTERVAL)
    
    def _setup_shortcuts(self):
        """Setup global keyboard shortcut (Ctrl+Alt+N) using Windows API."""
        # Register global hotkey using Windows API - works even when app doesn't have focus
        self._hotkey_registered = False
        self._hotkey_filter = None
        
        try:
            # Register the global hotkey: Ctrl + Alt + N
            # MOD_NOREPEAT prevents the hotkey from firing repeatedly when held down
            result = ctypes.windll.user32.RegisterHotKey(
                None,  # No specific window - system-wide
                HOTKEY_ID,
                MOD_CONTROL | MOD_ALT | MOD_NOREPEAT,
                VK_N
            )
            
            if result:
                self._hotkey_registered = True
                print("Global hotkey Ctrl+Alt+N registered successfully")
                
                # Install native event filter to catch the hotkey
                self._hotkey_filter = GlobalHotkeyFilter(self._toggle_manual_visibility)
                QApplication.instance().installNativeEventFilter(self._hotkey_filter)
            else:
                error_code = ctypes.windll.kernel32.GetLastError()
                print(f"Failed to register global hotkey. Error code: {error_code}")
                print("Hotkey might be in use by another application.")
                # Fall back to Qt shortcut (only works when app has focus)
                self._setup_fallback_shortcuts()
                
        except Exception as e:
            print(f"Error setting up global hotkey: {e}")
            self._setup_fallback_shortcuts()
    
    def _setup_fallback_shortcuts(self):
        """Setup fallback Qt shortcuts if global hotkey registration fails."""
        print("Using fallback Qt shortcuts (only work when app has focus)")
        self._visibility_shortcut = QShortcut(QKeySequence("Ctrl+Alt+N"), self)
        self._visibility_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self._visibility_shortcut.activated.connect(self._toggle_manual_visibility)
        
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
        
        # If expanded, reposition notes window as well with animation
        if self._is_expanded:
            self._position_notes_window(animate=True)
    
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
        """Expand the notes window with Windows 11 style bounce animation."""
        if self._is_expanded:
            return
        
        self._is_expanded = True
        
        screen = self._get_current_screen()
        screen_geometry = screen.geometry()
        screen_width = screen_geometry.width()

        # Calculate button X based on side
        if self._button_side == "right":
            button_x = screen_geometry.x() + screen_width - config.BUTTON_WIDTH
        else:
            button_x = screen_geometry.x()

        # Target geometry for notes window
        notes_target_geom = self._compute_notes_target_geometry()
        
        # Calculate start position (from button position, scaled down)
        button_center_y = screen_geometry.y() + self._button_y + config.BUTTON_HEIGHT // 2
        
        # Start geometry: small, at button position
        start_width = int(config.NOTES_WINDOW_WIDTH * 0.3)
        start_height = int(config.NOTES_WINDOW_HEIGHT * 0.3)
        
        if self._button_side == "right":
            start_x = button_x - start_width
        else:
            start_x = button_x + config.BUTTON_WIDTH
        
        start_y = button_center_y - start_height // 2
        
        notes_start = QRect(start_x, start_y, start_width, start_height)
        notes_end = notes_target_geom
        
        # Show notes window with initial state
        self.notes_window.setWindowOpacity(0.0)
        self.notes_window.setGeometry(notes_start)
        self.notes_window.show()
        
        # Button animation - slight shift with bounce
        button_start = QRect(0, 0, config.BUTTON_WIDTH, config.BUTTON_HEIGHT)
        if self._button_side == "right":
            button_end = QRect(8, 0, config.BUTTON_WIDTH, config.BUTTON_HEIGHT)
        else:
            button_end = QRect(-8, 0, config.BUTTON_WIDTH, config.BUTTON_HEIGHT)
        
        # Set expansion animation durations and curves
        self._button_animation.setDuration(self._expand_duration)
        self._button_animation.setEasingCurve(QEasingCurve.Type.OutBack)
        
        self._notes_opacity_animation.setDuration(self._expand_duration)
        self._notes_opacity_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self._notes_geometry_animation.setDuration(self._expand_duration)
        self._notes_geometry_animation.setEasingCurve(QEasingCurve.Type.OutBack)
        
        # Setup animation values
        self._button_animation.setStartValue(button_start)
        self._button_animation.setEndValue(button_end)
        
        self._notes_opacity_animation.setStartValue(0.0)
        self._notes_opacity_animation.setEndValue(1.0)
        
        self._notes_geometry_animation.setStartValue(notes_start)
        self._notes_geometry_animation.setEndValue(notes_end)
        
        # Start animations
        self._animation_group.start()
    
    def _collapse(self):
        """Collapse the notes window with smooth shrink animation back to button."""
        if not self._is_expanded:
            return
        
        self._is_expanded = False
        
        screen = self._get_current_screen()
        screen_geometry = screen.geometry()
        screen_width = screen_geometry.width()

        # Calculate button position
        if self._button_side == "right":
            button_x = screen_geometry.x() + screen_width - config.BUTTON_WIDTH
        else:
            button_x = screen_geometry.x()

        button_center_y = screen_geometry.y() + self._button_y + config.BUTTON_HEIGHT // 2
        
        # End geometry: small, at button position (reverse of expand)
        end_width = int(config.NOTES_WINDOW_WIDTH * 0.3)
        end_height = int(config.NOTES_WINDOW_HEIGHT * 0.3)
        
        if self._button_side == "right":
            end_x = button_x - end_width
        else:
            end_x = button_x + config.BUTTON_WIDTH
        
        end_y = button_center_y - end_height // 2
        
        # Animate button back
        button_start = self.button.geometry()
        button_end = QRect(0, 0, config.BUTTON_WIDTH, config.BUTTON_HEIGHT)
        
        notes_start = self.notes_window.geometry()
        notes_end = QRect(end_x, end_y, end_width, end_height)
        
        # Set collapse animation durations and curves (faster, ease-in)
        self._button_animation.setDuration(self._collapse_duration)
        self._button_animation.setEasingCurve(QEasingCurve.Type.InCubic)
        
        self._notes_opacity_animation.setDuration(self._collapse_duration)
        self._notes_opacity_animation.setEasingCurve(QEasingCurve.Type.InCubic)
        
        self._notes_geometry_animation.setDuration(self._collapse_duration)
        self._notes_geometry_animation.setEasingCurve(QEasingCurve.Type.InCubic)
        
        # Setup animation values
        self._button_animation.setStartValue(button_start)
        self._button_animation.setEndValue(button_end)
        
        self._notes_opacity_animation.setStartValue(1.0)
        self._notes_opacity_animation.setEndValue(0.0)
        
        self._notes_geometry_animation.setStartValue(notes_start)
        self._notes_geometry_animation.setEndValue(notes_end)
        
        # Disconnect any previous connections to avoid multiple calls
        try:
            self._notes_opacity_animation.finished.disconnect()
        except:
            pass
        
        # Hide notes window after animation completes
        def hide_notes():
            if not self._is_expanded:
                self.notes_window.hide()
        
        self._notes_opacity_animation.finished.connect(hide_notes)
        
        # Start animations
        self._animation_group.start()
    
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

    def _position_notes_window(self, animate: bool = False):
        """Align notes window with the button, keeping it fully on-screen."""
        target_geom = self._compute_notes_target_geometry()
        
        if animate and self.notes_window.isVisible():
            # Animate to new position
            current = self.notes_window.geometry()
            if abs(current.x() - target_geom.x()) > 5 or abs(current.y() - target_geom.y()) > 5:
                self._follow_animation.stop()
                self._follow_animation.setStartValue(current)
                self._follow_animation.setEndValue(target_geom)
                self._follow_animation.setDuration(350)
                self._follow_animation.setEasingCurve(QEasingCurve.Type.OutBack)
                self._follow_animation.start()
                return
        
        self.notes_window.setGeometry(target_geom)
    
    def _clamp_button_position(self, desired_y: int) -> int:
        """Keep button within the vertical bounds of the current screen."""
        screen = self._get_current_screen()
        screen_geometry = screen.availableGeometry()
        max_y = screen_geometry.height() - config.BUTTON_HEIGHT
        return max(0, min(max_y, desired_y))
    
    def _on_button_drag_started(self, global_y: float):
        """Store initial positions at the start of a drag."""
        # Cancel any ongoing snap animation (allow interrupt)
        self._snap_animation.stop()
        self._follow_animation.stop()
        
        self._drag_start_global_y = global_y
        self._drag_start_button_y = self._button_y
        self._is_dragging = True
        
        # Store current window side (above or below button)
        if self._is_expanded:
            current_geom = self.notes_window.geometry()
            button_y = self.y()
            self._last_window_side = "above" if current_geom.y() < button_y else "below"
            
            # Start smooth following timer
            self._target_notes_geometry = current_geom
            self._follow_timer.start()
    
    def _on_button_drag_moved(self, global_y: float):
        """Update button and notes positions while dragging with smooth window following."""
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
        tentative_x = int(cursor_pos.x() - config.BUTTON_WIDTH / 2)
        tentative_x = max(screen_geometry.x(), 
                         min(screen_geometry.x() + screen_width - config.BUTTON_WIDTH, tentative_x))
        
        # Move button immediately
        self.move(tentative_x, screen_geometry.y() + self._button_y)
        self.button.move(0, 0)
        
        # Update target geometry for smooth following (if expanded)
        if self._is_expanded:
            new_target = self._compute_notes_target_geometry()
            
            # Check if we need to reposition (window side change)
            button_screen_y = self._button_y
            new_window_side = "above" if new_target.y() < (screen_geometry.y() + button_screen_y) else "below"
            
            # If side changed and not in cooldown, trigger smooth reposition animation
            if self._last_window_side and new_window_side != self._last_window_side and not self._reposition_cooldown:
                self._trigger_reposition_animation(new_target)
                self._last_window_side = new_window_side
            else:
                # Normal following - update target for smooth interpolation
                self._target_notes_geometry = new_target
                if not self._last_window_side:
                    self._last_window_side = new_window_side
        else:
            # If not expanded, just update position directly
            self._position_notes_window()
    
    def _on_button_drag_ended(self):
        """Reset drag tracking when the drag finishes."""
        self._drag_start_global_y = None
        self._drag_start_button_y = None
        self._is_dragging = False
        self._last_window_side = None
        
        # Stop follow timer
        self._follow_timer.stop()

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
        # Note: Notes window animation is now handled inside _snap_button_to_current_side

    def _snap_button_to_current_side(self):
        """Animate button snapping to the nearest screen edge with bounce effect."""
        screen = self._get_current_screen()
        screen_geometry = screen.geometry()
        
        # Calculate target position (edge of screen)
        if self._button_side == "right":
            target_x = screen_geometry.x() + screen_geometry.width() - config.BUTTON_WIDTH
        else:
            target_x = screen_geometry.x()

        # Get the ACTUAL current position (force update to avoid stale values)
        start_pos = self.pos()
        current_y = start_pos.y()
        end_pos = QPoint(int(target_x), current_y)
        
        # Calculate distance for adaptive animation duration
        distance = abs(start_pos.x() - target_x)
        
        # If already at target, no animation needed
        if distance < 2:
            self.move(end_pos)
            if self._is_expanded:
                self._position_notes_window()
            return
        
        # Distance-based duration with bounce effect
        if distance < 50:
            duration = 250  # Very close - quick snap with bounce
            easing = QEasingCurve.Type.OutBack
        elif distance < 150:
            duration = 300  # Close - medium snap
            easing = QEasingCurve.Type.OutBack
        elif distance < 300:
            duration = 350  # Medium distance
            easing = QEasingCurve.Type.OutBack
        else:
            duration = 400  # Far distance - full animation with pronounced bounce
            easing = QEasingCurve.Type.OutBack

        # Stop any running animation first
        self._snap_animation.stop()
        
        # CRITICAL: Ensure widget is at start position to prevent visual jump
        # QPropertyAnimation doesn't apply startValue immediately on start()
        self.move(start_pos)
        
        # Configure snap animation with bounce effect
        self._snap_animation.setDuration(duration)
        self._snap_animation.setEasingCurve(easing)
        self._snap_animation.setStartValue(start_pos)
        self._snap_animation.setEndValue(end_pos)
        
        # Disconnect any previous finished connections
        try:
            self._snap_animation.finished.disconnect()
        except:
            pass
        
        # Connect finished handler to ensure final position is correct
        def on_snap_finished():
            # Ensure button is exactly at target position
            self.move(end_pos)
            # Ensure notes window is in correct position after snap completes
            if self._is_expanded and not self._follow_animation.state() == QPropertyAnimation.State.Running:
                self._position_notes_window()
        
        self._snap_animation.finished.connect(on_snap_finished)
        
        # Start animation
        self._snap_animation.start()
        
        # Also animate notes window in sync if expanded
        if self._is_expanded and self.notes_window.isVisible():
            self._animate_window_snap_sync(duration, easing)
    
    def _update_window_follow(self):
        """Timer callback for smooth window following during drag (lerp interpolation)."""
        if not self._is_dragging or not self._is_expanded or self._target_notes_geometry is None:
            return
        
        # Skip if reposition animation is running
        if self._follow_animation.state() == QPropertyAnimation.State.Running:
            return
        
        # Get current geometry
        current = self.notes_window.geometry()
        target = self._target_notes_geometry
        
        # Calculate distance for adaptive smoothing
        dist_x = abs(target.x() - current.x())
        dist_y = abs(target.y() - current.y())
        total_dist = (dist_x ** 2 + dist_y ** 2) ** 0.5
        
        # Adaptive smoothing: faster when far, slower when close (for precise landing)
        if total_dist > 100:
            smoothing = 0.35  # Faster catch-up
        elif total_dist > 30:
            smoothing = 0.25  # Normal following
        else:
            smoothing = 0.4   # Quick settle when close
        
        # Linear interpolation (lerp) for smooth trailing effect
        new_x = int(current.x() + (target.x() - current.x()) * smoothing)
        new_y = int(current.y() + (target.y() - current.y()) * smoothing)
        new_width = int(current.width() + (target.width() - current.width()) * smoothing)
        new_height = int(current.height() + (target.height() - current.height()) * smoothing)
        
        # Apply new position
        self.notes_window.setGeometry(new_x, new_y, new_width, new_height)
    
    def _trigger_reposition_animation(self, target_geometry: QRect):
        """Trigger smooth animation when window needs to flip from above to below or vice versa."""
        # Set cooldown to prevent animation spam
        self._reposition_cooldown = True
        
        # Stop the follow timer temporarily during animation
        self._follow_timer.stop()
        
        # Setup and start the reposition animation
        self._follow_animation.stop()
        self._follow_animation.setStartValue(self.notes_window.geometry())
        self._follow_animation.setEndValue(target_geometry)
        self._follow_animation.setDuration(350)
        self._follow_animation.setEasingCurve(QEasingCurve.Type.OutBack)  # Bounce effect
        
        # Disconnect any previous connections
        try:
            self._follow_animation.finished.disconnect()
        except:
            pass
        
        # Resume following after animation and reset cooldown
        def on_reposition_finished():
            self._reposition_cooldown = False
            self._target_notes_geometry = target_geometry
            if self._is_dragging:
                self._follow_timer.start()
        
        self._follow_animation.finished.connect(on_reposition_finished)
        self._follow_animation.start()
    
    def _animate_notes_to_final_position(self):
        """Animate notes window to its final position after drag ends."""
        target = self._compute_notes_target_geometry()
        current = self.notes_window.geometry()
        
        # Only animate if there's a meaningful difference
        if abs(current.x() - target.x()) > 5 or abs(current.y() - target.y()) > 5:
            self._follow_animation.stop()
            self._follow_animation.setStartValue(current)
            self._follow_animation.setEndValue(target)
            self._follow_animation.setDuration(350)
            self._follow_animation.setEasingCurve(QEasingCurve.Type.OutBack)
            self._follow_animation.start()
        else:
            # Just set directly if close enough
            self.notes_window.setGeometry(target)
    
    def _animate_window_snap_sync(self, duration: int, easing: QEasingCurve.Type = QEasingCurve.Type.OutBack):
        """Animate notes window in sync with button snap animation."""
        # Calculate the final target position after snap completes
        target = self._compute_notes_target_geometry()
        current = self.notes_window.geometry()
        
        # If already close to target, just set directly
        dist = abs(current.x() - target.x()) + abs(current.y() - target.y())
        if dist < 5:
            self.notes_window.setGeometry(target)
            return
        
        # Stop any running animation
        self._follow_animation.stop()
        
        # Ensure window is at current position to prevent visual jump
        self.notes_window.setGeometry(current)
        
        # Setup synchronized animation with matching easing
        self._follow_animation.setStartValue(current)
        self._follow_animation.setEndValue(target)
        self._follow_animation.setDuration(duration)
        self._follow_animation.setEasingCurve(easing)  # Match button animation
        self._follow_animation.start()
    
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
    
    def _show_settings(self):
        """Show the settings window."""
        self.settings_window.show()
        self.settings_window.raise_()
        self.settings_window.activateWindow()
    
    def _show_button_context_menu(self):
        """Show context menu when right-clicking the NOTES button (same as tray menu)."""
        # Create context menu with same items as system tray
        menu = QMenu()
        
        # Style the menu for Windows 11 look
        theme = self._theme_manager.get_theme()
        bg_color = theme["window_bg"]
        text_color = theme["text_primary"]
        accent = theme["accent_color"]
        border_color = theme["border_color"]
        
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {bg_color};
                color: {text_color};
                border: 1px solid {border_color};
                border-radius: 8px;
                padding: 5px;
            }}
            QMenu::item {{
                padding: 8px 25px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background-color: {accent};
                color: white;
            }}
            QMenu::separator {{
                height: 1px;
                background: {border_color};
                margin: 5px 10px;
            }}
        """)
        
        # Add Show/Hide action
        show_hide_action = menu.addAction("Show/Hide Overlay")
        show_hide_action.triggered.connect(self._toggle_manual_visibility)
        
        # Add Settings action
        settings_action = menu.addAction("Settings")
        settings_action.triggered.connect(self._show_settings)
        
        # Add separator
        menu.addSeparator()
        
        # Add Exit action
        exit_action = menu.addAction("Exit")
        exit_action.triggered.connect(self._exit_application)
        
        # Show menu at cursor position
        menu.exec(QCursor.pos())


def main():
    """Application entry point."""
    # Single instance check using Windows mutex
    mutex_name = f"Global\\{config.APP_NAME}_SingleInstance"
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
    last_error = ctypes.windll.kernel32.GetLastError()
    
    # ERROR_ALREADY_EXISTS means another instance is already running
    if last_error == 183:  # ERROR_ALREADY_EXISTS
        print("Another instance of the application is already running.")
        ctypes.windll.kernel32.CloseHandle(mutex)
        sys.exit(0)
    
    try:
        app = QApplication(sys.argv)
        app.setApplicationName(config.APP_NAME)
        
        # Prevent application from quitting when main window is closed
        app.setQuitOnLastWindowClosed(False)
        
        # High DPI scaling is enabled by default in PyQt6
        # No need to set AA_EnableHighDpiScaling or AA_UseHighDpiPixmaps
        
        window = OverlayMainWindow()
        window.show()
        
        sys.exit(app.exec())
    finally:
        # Release mutex when application exits
        if mutex:
            ctypes.windll.kernel32.CloseHandle(mutex)


if __name__ == "__main__":
    main()