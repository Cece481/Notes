"""
Pomodoro window with 25-minute timer and circular design.
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QStyle, QMenu, QInputDialog, QStackedWidget, QListWidget, QListWidgetItem, QSplitter, QFrame, QDialog, QLineEdit, QDialogButtonBox, QMessageBox
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QRectF, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QPoint, QSize, QUrl
from PyQt6.QtGui import QFont, QPainter, QPainterPath, QColor, QBrush, QPen, QIcon, QPixmap, QMouseEvent, QFontMetrics, QKeySequence, QShortcut
from PyQt6.QtMultimedia import QSoundEffect, QAudioOutput
from PyQt6.QtWidgets import QStyle
import config
from theme_manager import ThemeManager
import math
from datetime import datetime


class MinimalistMenuButton(QWidget):
    """Minimalist hamburger menu button with three horizontal lines."""
    
    clicked = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(24, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._is_hovered = False
        self._theme_manager = ThemeManager.get_instance()
        self._theme_manager.theme_changed.connect(self.update)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
    
    def enterEvent(self, event):
        """Handle mouse enter."""
        self._is_hovered = True
        self.update()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Handle mouse leave."""
        self._is_hovered = False
        self.update()
        super().leaveEvent(event)
    
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)
    
    def paintEvent(self, event):
        """Draw three horizontal lines."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        theme = self._theme_manager.get_theme()
        text_color = QColor(theme.get("text_primary", "#000000"))
        
        # Adjust opacity on hover
        if self._is_hovered:
            text_color.setAlpha(200)
        else:
            text_color.setAlpha(150)
        
        painter.setPen(QPen(text_color, 1.5))
        
        width = self.width()
        height = self.height()
        
        # Draw three horizontal lines
        line_spacing = 4
        line_length = 14
        start_x = (width - line_length) / 2
        start_y = (height - (2 * line_spacing)) / 2
        
        # Top line
        painter.drawLine(
            int(start_x), 
            int(start_y),
            int(start_x + line_length),
            int(start_y)
        )
        
        # Middle line
        painter.drawLine(
            int(start_x),
            int(start_y + line_spacing),
            int(start_x + line_length),
            int(start_y + line_spacing)
        )
        
        # Bottom line
        painter.drawLine(
            int(start_x),
            int(start_y + 2 * line_spacing),
            int(start_x + line_length),
            int(start_y + 2 * line_spacing)
        )


class CircularTimerWidget(QWidget):
    """Custom widget that displays a circular timer with progress."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(200, 200)  # Smaller circle
        self._remaining_seconds = 0
        self._total_seconds = 25 * 60  # 25 minutes
        self._progress = 1.0  # 1.0 = full, 0.0 = empty
        self._theme_manager = ThemeManager.get_instance()
        self._theme_manager.theme_changed.connect(self.update)
        
    def set_remaining_seconds(self, seconds):
        """Set the remaining time in seconds."""
        self._remaining_seconds = seconds
        self._progress = max(0.0, min(1.0, seconds / self._total_seconds))
        self.update()
    
    def set_total_seconds(self, total_seconds):
        """Set the total time duration."""
        self._total_seconds = total_seconds
        self._progress = max(0.0, min(1.0, self._remaining_seconds / self._total_seconds))
        self.update()
    
    def paintEvent(self, event):
        """Draw the circular timer."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        theme = self._theme_manager.get_theme()
        accent_color = QColor(theme.get("accent_color", "#0078d7"))
        border_color = QColor(theme.get("border_color", "#c8c8c8"))
        bg_color = QColor(theme.get("window_bg", "#f5f5f5"))
        text_color = QColor(theme.get("text_primary", "#000000"))
        
        # Get widget dimensions
        width = self.width()
        height = self.height()
        center_x = width / 2
        center_y = height / 2
        radius = min(width, height) / 2 - 10
        
        # Draw outer circle (border only, no fill)
        pen = QPen(border_color, 3)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(int(center_x - radius), int(center_y - radius), 
                          int(radius * 2), int(radius * 2))
        
        # Draw progress arc (showing elapsed time)
        if self._total_seconds > 0:
            elapsed_seconds = self._total_seconds - self._remaining_seconds
            progress = elapsed_seconds / self._total_seconds
            
            if progress > 0:
                # Draw progress arc using accent color
                progress_pen = QPen(accent_color, 4)
                progress_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                painter.setPen(progress_pen)
                
                # Calculate arc rectangle
                arc_rect = QRectF(
                    center_x - radius,
                    center_y - radius,
                    radius * 2,
                    radius * 2
                )
                
                # Draw arc starting from top (-90 degrees) going clockwise
                # Qt uses 1/16th of a degree, so 360 degrees = 360 * 16
                start_angle = -90 * 16  # Start from top
                span_angle = int(progress * 360 * 16)  # Progress in degrees
                
                painter.drawArc(arc_rect, start_angle, span_angle)
        
        # Draw time text in center
        minutes = self._remaining_seconds // 60
        seconds = self._remaining_seconds % 60
        time_text = f"{minutes:02d}:{seconds:02d}"
        
        font = QFont("Segoe UI", 24, QFont.Weight.Bold)  # Reduced from 36 to 24
        painter.setFont(font)
        painter.setPen(text_color)
        
        # Center the text
        font_metrics = painter.fontMetrics()
        text_rect = font_metrics.boundingRect(time_text)
        text_x = center_x - text_rect.width() / 2
        text_y = center_y + text_rect.height() / 4
        painter.drawText(int(text_x), int(text_y), time_text)


class PomodoroWindow(QWidget):
    """Pomodoro timer window with 25-minute countdown."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._theme_manager = ThemeManager.get_instance()
        self._theme_manager.theme_changed.connect(self._apply_theme)
        
        # Initialize Windows notification
        self._init_windows_notification()
        
        # Set window size to match notes window
        self.setFixedSize(config.NOTES_WINDOW_WIDTH, config.NOTES_WINDOW_HEIGHT)
        
        # Timer state
        self._default_timer_seconds = 25 * 60  # Default 25 minutes
        self._remaining_seconds = self._default_timer_seconds
        self._is_running = False
        self._is_paused = False
        
        # Break timer state
        self._is_break_mode = False
        self._break_seconds = 0
        
        # Task management
        self._selected_task = None
        self._default_tasks = [
            "Work on Project",
            "Study Session",
            "Reading",
            "Exercise",
            "Break"
        ]
        self._custom_tasks = []  # Store custom tasks
        self._task_statistics = {}  # {task_name: {"sessions": [], "total_time": 0}}
        # Each session: {"start": datetime, "pauses": [(pause_time, resume_time)], "end": datetime, "duration": seconds}
        
        # Current session tracking
        self._current_session = None  # {"task": name, "start": datetime, "pauses": []}
        
        # View management
        self._current_view = "Focus"  # Focus, Tasks, Statistics
        
        # Menu state tracking
        self._main_menu = None
        self._main_menu_open = False
        self._task_menu = None
        self._task_menu_open = False
        
        # Timer for countdown
        self._countdown_timer = QTimer()
        self._countdown_timer.timeout.connect(self._update_timer)
        self._countdown_timer.setInterval(1000)  # Update every second
        
        self._setup_ui()
        self._setup_shortcuts()
        self._apply_theme()
    
    def _setup_ui(self):
        """Setup the UI components."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Top bar with hamburger menu
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(10, 10, 10, 10)
        
        # Hamburger menu button (top left) - minimalist style
        self.menu_button = MinimalistMenuButton(self)
        self.menu_button.clicked.connect(self._show_main_menu)
        top_bar.addWidget(self.menu_button, alignment=Qt.AlignmentFlag.AlignLeft)
        top_bar.addStretch()
        
        main_layout.addLayout(top_bar)
        
        # Stacked widget for different views
        self.stacked_widget = QStackedWidget()
        
        # Focus view (main timer view)
        self.focus_view = self._create_focus_view()
        self.stacked_widget.addWidget(self.focus_view)
        
        # Tasks view
        self.tasks_view = self._create_tasks_view()
        self.stacked_widget.addWidget(self.tasks_view)
        
        # Statistics view
        self.statistics_view = self._create_statistics_view()
        self.stacked_widget.addWidget(self.statistics_view)
        
        # Set Focus as default view
        self.stacked_widget.setCurrentWidget(self.focus_view)
        
        main_layout.addWidget(self.stacked_widget)
    
    def _create_focus_view(self):
        """Create the Focus view with timer."""
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Add stretch at top
        layout.addStretch()
        
        # Task selection button (middle-top, above circle)
        self.task_button = QPushButton("Please select a task...")
        self.task_button.setMinimumHeight(35)
        self.task_button.setMinimumWidth(200)
        self.task_button.clicked.connect(self._show_task_menu)
        layout.addWidget(self.task_button, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Spacing between task button and timer
        layout.addSpacing(30)
        
        # Circular timer widget (centered)
        self.timer_widget = CircularTimerWidget(self)
        self.timer_widget.set_remaining_seconds(self._remaining_seconds)
        self.timer_widget.set_total_seconds(self._default_timer_seconds)
        # Enable context menu for right-click
        self.timer_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.timer_widget.customContextMenuRequested.connect(self._show_time_settings_dialog)
        layout.addWidget(self.timer_widget, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Add stretch at bottom to center content vertically
        layout.addStretch()
        
        # Button container for smooth transitions
        self.button_container = QWidget()
        button_container_layout = QHBoxLayout(self.button_container)
        button_container_layout.setContentsMargins(0, 0, 0, 0)
        button_container_layout.setSpacing(10)
        
        # Start/Pause button (centered)
        self.start_pause_btn = QPushButton("Start to Focus")
        self.start_pause_btn.setMinimumHeight(40)
        self.start_pause_btn.setMinimumWidth(150)
        self.start_pause_btn.clicked.connect(self._on_start_pause_clicked)
        button_container_layout.addWidget(self.start_pause_btn)
        
        # Continue button (hidden initially)
        self.continue_btn = QPushButton("Continue")
        self.continue_btn.setMinimumHeight(40)
        self.continue_btn.setMinimumWidth(150)
        self.continue_btn.clicked.connect(self._on_continue_clicked)
        self.continue_btn.hide()
        button_container_layout.addWidget(self.continue_btn)
        
        # Stop button (hidden initially)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setMinimumHeight(40)
        self.stop_btn.setMinimumWidth(150)
        self.stop_btn.clicked.connect(self._on_stop_clicked)
        self.stop_btn.hide()
        button_container_layout.addWidget(self.stop_btn)
        
        layout.addWidget(self.button_container, alignment=Qt.AlignmentFlag.AlignCenter)
        
        return view
    
    def _create_tasks_view(self):
        """Create the Tasks view with task list and statistics."""
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(10, 5, 10, 10)
        layout.setSpacing(5)
        
        # Splitter for left (tasks) and right (statistics) - takes remaining space
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side: Task list
        tasks_widget = QWidget()
        tasks_layout = QVBoxLayout(tasks_widget)
        tasks_layout.setContentsMargins(5, 5, 5, 5)
        tasks_layout.setSpacing(5)
        
        tasks_label = QLabel("Tasks")
        tasks_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        tasks_label.setFixedHeight(25)
        tasks_layout.addWidget(tasks_label)
        
        self.tasks_list = QListWidget()
        self.tasks_list.itemClicked.connect(self._on_task_selected_in_list)
        self.tasks_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tasks_list.customContextMenuRequested.connect(self._show_task_context_menu)
        tasks_layout.addWidget(self.tasks_list)
        
        splitter.addWidget(tasks_widget)
        
        # Right side: Statistics
        stats_widget = QWidget()
        stats_layout = QVBoxLayout(stats_widget)
        stats_layout.setContentsMargins(5, 5, 5, 5)
        stats_layout.setSpacing(5)
        
        stats_label = QLabel("History")
        stats_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        stats_label.setFixedHeight(25)
        stats_layout.addWidget(stats_label)
        
        self.stats_list = QListWidget()
        self.stats_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.stats_list.customContextMenuRequested.connect(self._show_stats_context_menu)
        self.stats_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.stats_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.stats_list.setWordWrap(True)
        
        # Initial placeholder
        placeholder_item = QListWidgetItem("Select a task to view history")
        placeholder_item.setFlags(Qt.ItemFlag.NoItemFlags)
        placeholder_item.setSizeHint(QSize(200, 40))  # Will be updated when list is resized
        self.stats_list.addItem(placeholder_item)
        
        stats_layout.addWidget(self.stats_list)
        
        splitter.addWidget(stats_widget)
        
        # Set splitter proportions (50% tasks, 50% statistics)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([250, 250])
        
        # Add splitter to layout - it will take remaining space
        layout.addWidget(splitter)
        
        # Populate task list
        self._refresh_tasks_list()
        
        return view
    
    def _create_statistics_view(self):
        """Create the Statistics view."""
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Title
        title = QLabel("Statistics")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont("Segoe UI", 24, QFont.Weight.Bold)
        title.setFont(font)
        layout.addWidget(title)
        
        layout.addStretch()
        
        # Total Focus Time
        self.total_focus_label = QLabel("Total Focus Time: 0h 0m")
        self.total_focus_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        focus_font = QFont("Segoe UI", 16, QFont.Weight.Bold)
        self.total_focus_label.setFont(focus_font)
        layout.addWidget(self.total_focus_label)
        
        layout.addSpacing(30)
        
        # Completed Tasks
        self.completed_tasks_label = QLabel("Completed Tasks: 0")
        self.completed_tasks_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        completed_font = QFont("Segoe UI", 14)
        self.completed_tasks_label.setFont(completed_font)
        layout.addWidget(self.completed_tasks_label)
        
        layout.addSpacing(20)
        
        # Unfinished Tasks
        self.unfinished_tasks_label = QLabel("Unfinished Tasks: 0")
        self.unfinished_tasks_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        unfinished_font = QFont("Segoe UI", 14)
        self.unfinished_tasks_label.setFont(unfinished_font)
        layout.addWidget(self.unfinished_tasks_label)
        
        layout.addStretch()
        
        return view
    
    def _update_statistics_display(self):
        """Update the statistics display with current data."""
        if not hasattr(self, 'total_focus_label'):
            return
        
        # Calculate total focus time across all tasks
        total_seconds = 0
        completed_count = 0
        unfinished_count = 0
        
        for task_name, stats in self._task_statistics.items():
            total_seconds += stats.get("total_time", 0)
            sessions = stats.get("sessions", [])
            for session in sessions:
                if session.get("completed", False):
                    completed_count += 1
                else:
                    unfinished_count += 1
        
        # Format total time
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        
        if hours > 0:
            self.total_focus_label.setText(f"Total Focus Time: {hours}h {minutes}m")
        else:
            self.total_focus_label.setText(f"Total Focus Time: {minutes}m")
        
        # Update completed and unfinished counts
        self.completed_tasks_label.setText(f"Completed Tasks: {completed_count}")
        self.unfinished_tasks_label.setText(f"Unfinished Tasks: {unfinished_count}")
    
    def _show_main_menu(self):
        """Show or hide the main menu with Focus, Tasks, Statistics options."""
        # Check flag first - if menu is marked as open, close it
        if self._main_menu_open and self._main_menu:
            self._main_menu.close()
            self._main_menu_open = False
            return
        
        # Create menu if it doesn't exist
        if self._main_menu is None:
            self._main_menu = QMenu(self)
            
            # Menu items
            focus_action = self._main_menu.addAction("Focus")
            tasks_action = self._main_menu.addAction("Tasks")
            statistics_action = self._main_menu.addAction("Statistics")
            
            # Connect actions
            focus_action.triggered.connect(lambda: self._switch_view("Focus"))
            tasks_action.triggered.connect(lambda: self._switch_view("Tasks"))
            statistics_action.triggered.connect(lambda: self._switch_view("Statistics"))
            
            # Connect menu close signal to reset flag
            def on_menu_closed():
                self._main_menu_open = False
            self._main_menu.aboutToHide.connect(on_menu_closed)
        
        # Show menu below the button
        button_pos = self.menu_button.mapToGlobal(self.menu_button.rect().bottomLeft())
        self._main_menu_open = True
        self._main_menu.popup(button_pos)
    
    def _switch_view(self, view_name):
        """Switch between different views."""
        self._current_view = view_name
        
        if view_name == "Focus":
            self.stacked_widget.setCurrentWidget(self.focus_view)
        elif view_name == "Tasks":
            self.stacked_widget.setCurrentWidget(self.tasks_view)
            # Refresh tasks list when switching to Tasks view
            if hasattr(self, 'tasks_list'):
                self._refresh_tasks_list()
        elif view_name == "Statistics":
            self.stacked_widget.setCurrentWidget(self.statistics_view)
            # Update statistics display when switching to Statistics view
            self._update_statistics_display()
    
    def _create_play_icon(self):
        """Create a white play icon."""
        icon_color = QColor(Qt.GlobalColor.white)
        
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(icon_color))
        
        # Draw play triangle (pointing right)
        path = QPainterPath()
        path.moveTo(5, 3)
        path.lineTo(5, 13)
        path.lineTo(13, 8)
        path.closeSubpath()
        painter.drawPath(path)
        
        painter.end()
        return QIcon(pixmap)
    
    def _create_pause_icon(self):
        """Create a white pause icon."""
        icon_color = QColor(Qt.GlobalColor.white)
        
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(icon_color))
        
        # Draw pause bars (two vertical rectangles)
        painter.drawRect(5, 3, 2, 10)  # Left bar
        painter.drawRect(9, 3, 2, 10)  # Right bar
        
        painter.end()
        return QIcon(pixmap)
    
    def _apply_theme(self):
        """Apply current theme to the window."""
        theme = self._theme_manager.get_theme()
        
        # Window background
        bg_color = QColor(theme.get("window_bg", "#f5f5f5"))
        bg_opacity = theme.get("window_bg_opacity", 240)
        bg_color.setAlpha(bg_opacity)
        
        # Button styles
        accent_color = theme.get("accent_color", "#0078d7")
        button_bg = theme.get("button_bg", "#f0f0f0")
        button_text = theme.get("button_text", "#000000")
        button_hover = theme.get("button_hover", "#e0e0e0")
        button_border = theme.get("button_border", "#c8c8c8")
        border_radius = theme.get("border_radius", 12)
        
        button_style = f"""
            QPushButton {{
                background-color: {button_bg};
                color: {button_text};
                border: 1px solid {button_border};
                border-radius: {border_radius}px;
                padding: 8px 16px;
                font-family: {theme.get("font_family", "Segoe UI")};
                font-size: {theme.get("font_size", 11)}pt;
            }}
            QPushButton:hover {{
                background-color: {button_hover};
            }}
            QPushButton:pressed {{
                background-color: {accent_color};
                color: white;
            }}
        """
        
        self.start_pause_btn.setStyleSheet(button_style)
        self.continue_btn.setStyleSheet(button_style)
        self.stop_btn.setStyleSheet(button_style)
        self.task_button.setStyleSheet(button_style)
        
        # Style tasks list if it exists
        if hasattr(self, 'tasks_list'):
            list_style = f"""
                QListWidget {{
                    background-color: {button_bg};
                    color: {button_text};
                    border: 1px solid {button_border};
                    border-radius: {border_radius}px;
                    padding: 5px;
                    font-family: {theme.get("font_family", "Segoe UI")};
                    font-size: {theme.get("font_size", 11)}pt;
                }}
                QListWidget::item {{
                    padding: 8px;
                    border-radius: {border_radius - 2}px;
                }}
                QListWidget::item:hover {{
                    background-color: {button_hover};
                }}
                QListWidget::item:selected {{
                    background-color: {accent_color};
                    color: white;
                }}
            """
            self.tasks_list.setStyleSheet(list_style)
        
        # Style statistics list if it exists
        if hasattr(self, 'stats_list'):
            stats_list_style = f"""
                QListWidget {{
                    background-color: {button_bg};
                    color: {button_text};
                    border: 1px solid {button_border};
                    border-radius: {border_radius}px;
                    padding: 5px;
                    font-family: {theme.get("font_family", "Segoe UI")};
                    font-size: {int(theme.get("font_size", 11) * 0.85)}pt;
                }}
                QListWidget::item {{
                    padding: 6px;
                    border-radius: {border_radius - 2}px;
                    min-height: 40px;
                }}
                QListWidget::item:hover {{
                    background-color: {button_hover};
                }}
                QListWidget::item:selected {{
                    background-color: {accent_color};
                    color: white;
                }}
                QScrollBar:vertical {{
                    width: 8px;
                }}
            """
            self.stats_list.setStyleSheet(stats_list_style)
        
        # Update icons with theme colors based on current state
        if self._is_running and not self._is_paused:
            # Timer is running - show pause icon
            pause_icon = self._create_pause_icon()
            self.start_pause_btn.setIcon(pause_icon)
        else:
            # Timer is stopped or paused - show play icon
            play_icon = self._create_play_icon()
            self.start_pause_btn.setIcon(play_icon)
        
        self.update()
    
    def _show_time_settings_dialog(self, position):
        """Show dialog to set custom timer duration."""
        if self._is_running:
            # Don't allow changing time while timer is running
            return
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Set Timer Duration")
        dialog.setMinimumWidth(300)
        
        layout = QVBoxLayout(dialog)
        
        # Instructions
        instructions = QLabel("Enter time in format HH:MM:SS or MM:SS")
        instructions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(instructions)
        
        # Time input
        time_input = QLineEdit()
        # Format current time
        hours = self._default_timer_seconds // 3600
        minutes = (self._default_timer_seconds % 3600) // 60
        seconds = self._default_timer_seconds % 60
        if hours > 0:
            time_input.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
        else:
            time_input.setText(f"{minutes:02d}:{seconds:02d}")
        time_input.setPlaceholderText("00:00:00")
        layout.addWidget(time_input)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            time_str = time_input.text().strip()
            # Parse time string (HH:MM:SS or MM:SS)
            try:
                parts = time_str.split(":")
                if len(parts) == 2:
                    # MM:SS format
                    minutes = int(parts[0])
                    seconds = int(parts[1])
                    total_seconds = minutes * 60 + seconds
                elif len(parts) == 3:
                    # HH:MM:SS format
                    hours = int(parts[0])
                    minutes = int(parts[1])
                    seconds = int(parts[2])
                    total_seconds = hours * 3600 + minutes * 60 + seconds
                else:
                    raise ValueError("Invalid format")
                
                if total_seconds <= 0:
                    raise ValueError("Time must be greater than 0")
                
                # Update timer duration
                self._default_timer_seconds = total_seconds
                self._remaining_seconds = total_seconds
                self.timer_widget.set_total_seconds(total_seconds)
                self.timer_widget.set_remaining_seconds(total_seconds)
            except (ValueError, IndexError):
                # Show error message
                QMessageBox.warning(self, "Invalid Time", "Please enter time in format HH:MM:SS or MM:SS")
    
    def _show_break_dialog(self):
        """Show dialog to select break duration after focus timer ends."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Focus Complete!")
        dialog.setMinimumWidth(350)
        dialog.setMinimumHeight(200)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(15)
        
        # Congratulations message
        congrats_label = QLabel("🎉 Focus session complete!")
        congrats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        congrats_font = QFont("Segoe UI", 14, QFont.Weight.Bold)
        congrats_label.setFont(congrats_font)
        layout.addWidget(congrats_label)
        
        # Break options label
        break_label = QLabel("Take a break:")
        break_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(break_label)
        
        # Break duration buttons
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(10)
        
        # 5 minute break
        btn_5min = QPushButton("5 minutes")
        btn_5min.clicked.connect(lambda: self._start_break(5 * 60, dialog))
        buttons_layout.addWidget(btn_5min)
        
        # 10 minute break
        btn_10min = QPushButton("10 minutes")
        btn_10min.clicked.connect(lambda: self._start_break(10 * 60, dialog))
        buttons_layout.addWidget(btn_10min)
        
        # 15 minute break
        btn_15min = QPushButton("15 minutes")
        btn_15min.clicked.connect(lambda: self._start_break(15 * 60, dialog))
        buttons_layout.addWidget(btn_15min)
        
        # Custom break
        btn_custom = QPushButton("Custom break time")
        btn_custom.clicked.connect(lambda: self._show_custom_break_dialog(dialog))
        buttons_layout.addWidget(btn_custom)
        
        layout.addLayout(buttons_layout)
        
        # Finish button
        finish_btn = QPushButton("Finish (No break)")
        finish_btn.clicked.connect(dialog.accept)
        layout.addWidget(finish_btn)
        
        # Apply theme to buttons
        theme = self._theme_manager.get_theme()
        button_bg = theme.get("button_bg", "#f0f0f0")
        button_text = theme.get("button_text", "#000000")
        button_hover = theme.get("button_hover", "#e0e0e0")
        button_border = theme.get("button_border", "#c8c8c8")
        accent_color = theme.get("accent_color", "#0078d7")
        border_radius = theme.get("border_radius", 12)
        
        button_style = f"""
            QPushButton {{
                background-color: {button_bg};
                color: {button_text};
                border: 1px solid {button_border};
                border-radius: {border_radius}px;
                padding: 10px;
                font-family: {theme.get("font_family", "Segoe UI")};
                font-size: {theme.get("font_size", 11)}pt;
            }}
            QPushButton:hover {{
                background-color: {button_hover};
            }}
            QPushButton:pressed {{
                background-color: {accent_color};
                color: white;
            }}
        """
        
        for btn in [btn_5min, btn_10min, btn_15min, btn_custom, finish_btn]:
            btn.setStyleSheet(button_style)
        
        dialog.exec()
    
    def _show_custom_break_dialog(self, parent_dialog):
        """Show dialog to set custom break duration."""
        parent_dialog.accept()  # Close the break selection dialog first
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Custom Break Time")
        dialog.setMinimumWidth(300)
        
        layout = QVBoxLayout(dialog)
        
        # Instructions
        instructions = QLabel("Enter break time in format HH:MM:SS or MM:SS")
        instructions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(instructions)
        
        # Time input
        time_input = QLineEdit()
        time_input.setPlaceholderText("00:05:00")
        layout.addWidget(time_input)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            time_str = time_input.text().strip()
            # Parse time string (HH:MM:SS or MM:SS)
            try:
                parts = time_str.split(":")
                if len(parts) == 2:
                    # MM:SS format
                    minutes = int(parts[0])
                    seconds = int(parts[1])
                    total_seconds = minutes * 60 + seconds
                elif len(parts) == 3:
                    # HH:MM:SS format
                    hours = int(parts[0])
                    minutes = int(parts[1])
                    seconds = int(parts[2])
                    total_seconds = hours * 3600 + minutes * 60 + seconds
                else:
                    raise ValueError("Invalid format")
                
                if total_seconds <= 0:
                    raise ValueError("Time must be greater than 0")
                
                self._start_break(total_seconds, None)
            except (ValueError, IndexError):
                # Show error message
                QMessageBox.warning(self, "Invalid Time", "Please enter time in format HH:MM:SS or MM:SS")
                # Reopen break dialog
                self._show_break_dialog()
    
    def _start_break(self, break_seconds, dialog=None):
        """Start a break timer."""
        if dialog:
            dialog.accept()
        
        self._is_break_mode = True
        self._break_seconds = break_seconds
        self._remaining_seconds = break_seconds
        self.timer_widget.set_total_seconds(break_seconds)
        self.timer_widget.set_remaining_seconds(break_seconds)
        
        # Update button text
        self.start_pause_btn.setText("Start Break")
        play_icon = self._create_play_icon()
        self.start_pause_btn.setIcon(play_icon)
        
        # Auto-start the break timer
        self._start_timer()
    
    def _show_task_menu(self):
        """Show or hide the task selection menu."""
        # Check flag first - if menu is marked as open, close it
        if self._task_menu_open and self._task_menu:
            self._task_menu.close()
            self._task_menu_open = False
            return
        
        # Create menu if it doesn't exist
        if self._task_menu is None:
            self._task_menu = QMenu(self)
            
            # Set menu width to match button width
            self._task_menu.setMinimumWidth(self.task_button.width())
            self._task_menu.setMaximumWidth(self.task_button.width())
            
            # Connect menu close signal to reset flag
            def on_menu_closed():
                self._task_menu_open = False
            self._task_menu.aboutToHide.connect(on_menu_closed)
        
        # Rebuild menu items (in case custom tasks were added)
        self._task_menu.clear()
        
        # Add default tasks
        for task in self._default_tasks:
            action = self._task_menu.addAction(task)
            action.triggered.connect(lambda checked, t=task: self._on_task_selected(t))
        
        # Add separator if there are custom tasks
        if self._custom_tasks:
            self._task_menu.addSeparator()
            # Add custom tasks
            for task in self._custom_tasks:
                action = self._task_menu.addAction(task)
                action.triggered.connect(lambda checked, t=task: self._on_task_selected(t))
        
        # Add separator before "Custom Task..."
        self._task_menu.addSeparator()
        
        # Add "Custom Task..." option
        custom_action = self._task_menu.addAction("Custom Task...")
        custom_action.triggered.connect(self._create_custom_task)
        
        # Show menu below the button
        button_pos = self.task_button.mapToGlobal(self.task_button.rect().bottomLeft())
        self._task_menu_open = True
        self._task_menu.popup(button_pos)
    
    def _create_custom_task(self):
        """Show dialog to create a new custom task."""
        text, ok = QInputDialog.getText(
            self,
            "New Task",
            "Enter task name:",
            text=""
        )
        
        if ok and text.strip():
            task_name = text.strip()
            # Add to custom tasks if not already there
            if task_name not in self._custom_tasks and task_name not in self._default_tasks:
                self._custom_tasks.append(task_name)
                # Select the newly created task
                self._on_task_selected(task_name)
                # Refresh tasks list if we're on Tasks view
                if hasattr(self, 'tasks_list'):
                    self._refresh_tasks_list()
                # Refresh tasks list if we're on Tasks view
                if hasattr(self, 'tasks_list'):
                    self._refresh_tasks_list()
    
    def _on_task_selected(self, task_name):
        """Handle task selection from menu."""
        self._selected_task = task_name
        self.task_button.setText(task_name)
        # Refresh tasks list if we're on Tasks view
        if hasattr(self, 'tasks_list'):
            self._refresh_tasks_list()
    
    def _refresh_tasks_list(self):
        """Refresh the tasks list in Tasks view."""
        if not hasattr(self, 'tasks_list'):
            return
        
        self.tasks_list.clear()
        
        # Add default tasks
        for task in self._default_tasks:
            item = QListWidgetItem(task)
            item.setData(Qt.ItemDataRole.UserRole, "default")
            self.tasks_list.addItem(item)
        
        # Add custom tasks
        for task in self._custom_tasks:
            item = QListWidgetItem(task)
            item.setData(Qt.ItemDataRole.UserRole, "custom")
            self.tasks_list.addItem(item)
        
        # Add "Not Specified" if it has statistics
        if "Not Specified" in self._task_statistics:
            item = QListWidgetItem("Not Specified")
            item.setData(Qt.ItemDataRole.UserRole, "default")
            self.tasks_list.addItem(item)
    
    def _on_task_selected_in_list(self, item):
        """Handle task selection in the tasks list."""
        task_name = item.text()
        self._update_task_statistics_display(task_name)
    
    def _update_task_statistics_display(self, task_name):
        """Update the statistics display for the selected task."""
        if not hasattr(self, 'stats_list'):
            return
        
        self.stats_list.clear()
        
        stats = self._task_statistics.get(task_name, {"sessions": [], "total_time": 0, "events": []})
        sessions = stats.get("sessions", [])
        events = stats.get("events", [])
        
        # Get font metrics for height calculation
        theme_manager = ThemeManager.get_instance()
        theme = theme_manager.get_theme()
        font_size = int(theme.get("font_size", 11) * 0.85)
        font = QFont(theme.get("font_family", "Segoe UI"), font_size)
        metrics = QFontMetrics(font)
        
        # Get available width (list width minus padding and scrollbar)
        list_width = max(200, self.stats_list.width() - 20)  # Account for padding and scrollbar, minimum 200
        
        if not sessions and not events:
            item = QListWidgetItem("No sessions yet")
            item.setFlags(Qt.ItemFlag.NoItemFlags)  # Make it non-selectable
            item.setSizeHint(QSize(list_width, 40))
            self.stats_list.addItem(item)
            return
        
        # Display all events first (in chronological order)
        if events:
            events_text = "All Timer Events:\n"
            for event in events:
                event_type = event.get("type", "unknown").capitalize()
                event_time = event.get("time", datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
                events_text += f"{event_type}: {event_time}\n"
            
            item = QListWidgetItem(events_text.strip())
            item.setFlags(Qt.ItemFlag.NoItemFlags)  # Make it non-selectable
            wrapped_rect = metrics.boundingRect(0, 0, list_width, 0, 
                                                Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap, 
                                                events_text)
            item_height = max(40, wrapped_rect.height() + 12)
            item.setSizeHint(QSize(list_width, item_height))
            self.stats_list.addItem(item)
            
            # Add separator if there are also sessions
            if sessions:
                separator = QListWidgetItem("─" * 30)
                separator.setFlags(Qt.ItemFlag.NoItemFlags)
                separator.setSizeHint(QSize(list_width, 20))
                self.stats_list.addItem(separator)
        
        # Display sessions in reverse order (newest first)
        for i, session in enumerate(reversed(sessions)):
            start_time = session["start"].strftime("%Y-%m-%d %H:%M:%S")
            end_time = session.get("end", session["start"]).strftime("%Y-%m-%d %H:%M:%S")
            duration_sec = session.get("duration", 0)
            minutes = duration_sec // 60
            seconds = duration_sec % 60
            
            # Build session text
            session_text = f"Session {len(sessions) - i}\n"
            session_text += f"Start: {start_time}\n"
            
            # Add pause/resume times
            pauses = session.get("pauses", [])
            if pauses:
                session_text += "Pauses:\n"
                for pause_start, pause_end in pauses:
                    pause_str = pause_start.strftime("%H:%M:%S")
                    resume_str = pause_end.strftime("%H:%M:%S")
                    session_text += f"  Paused: {pause_str} → Resumed: {resume_str}\n"
            
            session_text += f"End: {end_time}\n"
            session_text += f"Duration: {minutes}m {seconds}s"
            
            # Calculate required height for wrapped text
            wrapped_rect = metrics.boundingRect(0, 0, list_width, 0, 
                                                Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap, 
                                                session_text)
            item_height = max(40, wrapped_rect.height() + 12)  # Minimum 40px, add padding
            
            item = QListWidgetItem(session_text)
            item.setSizeHint(QSize(list_width, item_height))
            item.setData(Qt.ItemDataRole.UserRole, (task_name, len(sessions) - i - 1))  # Store task and session index
            self.stats_list.addItem(item)
    
    def _show_stats_context_menu(self, position):
        """Show context menu for statistics item."""
        item = self.stats_list.itemAt(position)
        if not item or not item.data(Qt.ItemDataRole.UserRole):
            return
        
        menu = QMenu(self)
        remove_action = menu.addAction("Remove")
        remove_action.triggered.connect(lambda: self._remove_session(item))
        
        if menu.actions():
            menu.exec(self.stats_list.mapToGlobal(position))
    
    def _remove_session(self, item):
        """Remove a session from statistics."""
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
        
        task_name, session_index = data
        if task_name not in self._task_statistics:
            return
        
        stats = self._task_statistics[task_name]
        sessions = stats.get("sessions", [])
        
        # Convert to reverse index (since we display in reverse)
        actual_index = len(sessions) - 1 - session_index
        
        if 0 <= actual_index < len(sessions):
            removed_session = sessions.pop(actual_index)
            # Update total time
            stats["total_time"] = max(0, stats["total_time"] - removed_session.get("duration", 0))
            
            # Refresh display
            self._update_task_statistics_display(task_name)
            
            # Update statistics view if we're on Statistics view
            if self._current_view == "Statistics":
                self._update_statistics_display()
    
    def _remove_session(self, item):
        """Remove a session from statistics."""
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
        
        task_name, session_index = data
        if task_name not in self._task_statistics:
            return
        
        stats = self._task_statistics[task_name]
        sessions = stats.get("sessions", [])
        
        # Convert to reverse index (since we display in reverse)
        actual_index = len(sessions) - 1 - session_index
        
        if 0 <= actual_index < len(sessions):
            removed_session = sessions.pop(actual_index)
            # Update total time
            stats["total_time"] = max(0, stats["total_time"] - removed_session.get("duration", 0))
            
            # Refresh display
            self._update_task_statistics_display(task_name)
            
            # Update statistics view if we're on Statistics view
            if self._current_view == "Statistics":
                self._update_statistics_display()
    
    def _show_task_context_menu(self, position):
        """Show context menu for task item."""
        item = self.tasks_list.itemAt(position)
        if not item:
            return
        
        task_name = item.text()
        task_type = item.data(Qt.ItemDataRole.UserRole)
        
        menu = QMenu(self)
        
        # Only show edit/remove for custom tasks
        if task_type == "custom":
            edit_action = menu.addAction("Edit")
            edit_action.triggered.connect(lambda: self._edit_task(task_name))
            
            remove_action = menu.addAction("Remove")
            remove_action.triggered.connect(lambda: self._remove_task(task_name))
        
        if menu.actions():
            menu.exec(self.tasks_list.mapToGlobal(position))
    
    def _edit_task(self, old_name):
        """Edit/rename a custom task."""
        text, ok = QInputDialog.getText(
            self,
            "Edit Task",
            "Enter new task name:",
            text=old_name
        )
        
        if ok and text.strip():
            new_name = text.strip()
            if new_name != old_name:
                # Update in custom tasks list
                if old_name in self._custom_tasks:
                    index = self._custom_tasks.index(old_name)
                    self._custom_tasks[index] = new_name
                
                # Update statistics key
                if old_name in self._task_statistics:
                    self._task_statistics[new_name] = self._task_statistics.pop(old_name)
                
                # Update selected task if it's the current one
                if self._selected_task == old_name:
                    self._selected_task = new_name
                    self.task_button.setText(new_name)
                
                # Refresh lists
                self._refresh_tasks_list()
                if hasattr(self, 'stats_list'):
                    self._update_task_statistics_display(new_name)
    
    def _remove_task(self, task_name):
        """Remove a custom task."""
        if task_name in self._custom_tasks:
            self._custom_tasks.remove(task_name)
            
            # Remove statistics
            if task_name in self._task_statistics:
                del self._task_statistics[task_name]
            
            # Clear selection if it was the selected task
            if self._selected_task == task_name:
                self._selected_task = None
                self.task_button.setText("Please select a task...")
            
            # Refresh lists
            self._refresh_tasks_list()
            if hasattr(self, 'stats_list'):
                self.stats_list.clear()
                item = QListWidgetItem("Select a task to view history")
                item.setFlags(Qt.ItemFlag.NoItemFlags)
                self.stats_list.addItem(item)
    
    def _on_start_pause_clicked(self):
        """Handle start/pause button click."""
        if not self._is_running:
            self._start_timer()
        elif self._is_paused:
            self._resume_timer()
        else:
            self._pause_timer()
    
    def _start_timer(self):
        """Start the countdown timer."""
        self._is_running = True
        self._is_paused = False
        self.start_pause_btn.setText("Pause")
        pause_icon = self._create_pause_icon()
        self.start_pause_btn.setIcon(pause_icon)
        
        # Use "Not Specified" if no task is selected
        task_name = self._selected_task if self._selected_task else "Not Specified"
        
        # Record session start
        self._current_session = {
            "task": task_name,
            "start": datetime.now(),
            "pauses": [],
            "paused_at": None,
            "events": [{"type": "start", "time": datetime.now()}],
            "timer_duration": self._default_timer_seconds  # Store the timer duration for this session
        }
        
        # Record start event in statistics
        self._record_timer_event(task_name, "start")
        
        self._countdown_timer.start()
    
    def _pause_timer(self):
        """Pause the countdown timer and show Continue/Stop buttons."""
        self._is_paused = True
        self._countdown_timer.stop()
        
        # Record pause time
        if self._current_session:
            self._current_session["paused_at"] = datetime.now()
            self._current_session["events"].append({"type": "pause", "time": datetime.now()})
            
            # Record pause event in statistics
            self._record_timer_event(self._current_session["task"], "pause")
        
        self._animate_to_two_buttons()
    
    def _resume_timer(self):
        """Resume the countdown timer and show single Pause button."""
        self._is_paused = False
        
        # Record resume time
        if self._current_session and self._current_session.get("paused_at"):
            resume_time = datetime.now()
            self._current_session["pauses"].append((
                self._current_session["paused_at"],
                resume_time
            ))
            self._current_session["paused_at"] = None
            self._current_session["events"].append({"type": "resume", "time": resume_time})
            
            # Record resume event in statistics
            self._record_timer_event(self._current_session["task"], "resume")
        
        self._animate_to_single_button()
        self.start_pause_btn.setText("Pause")
        pause_icon = self._create_pause_icon()
        self.start_pause_btn.setIcon(pause_icon)
        self._countdown_timer.start()
    
    def _on_continue_clicked(self):
        """Handle Continue button click."""
        self._resume_timer()
    
    def _on_stop_clicked(self):
        """Handle Stop button click - reset timer."""
        # Only record session if not in break mode
        if not self._is_break_mode and self._current_session:
            self._current_session["events"].append({"type": "stop", "time": datetime.now()})
            self._record_timer_event(self._current_session["task"], "stop")
            # Record the session if it was running (marked as not completed)
            if self._is_running or self._is_paused:
                self._record_timer_session(self._current_session["task"], completed=False)
            self._current_session = None
        
        self._countdown_timer.stop()
        
        # Reset to focus mode
        self._is_break_mode = False
        self._remaining_seconds = self._default_timer_seconds
        self.timer_widget.set_total_seconds(self._default_timer_seconds)
        self._is_running = False
        self._is_paused = False
        self._animate_to_single_button()
        self.start_pause_btn.setText("Start to Focus")
        play_icon = self._create_play_icon()
        self.start_pause_btn.setIcon(play_icon)
        self.timer_widget.set_remaining_seconds(self._remaining_seconds)
    
    def _animate_to_two_buttons(self):
        """Animate transition from single button to two buttons (Continue/Stop)."""
        # Store original button width and position
        original_width = self.start_pause_btn.width()
        original_height = self.start_pause_btn.height()
        
        # Show the two buttons but make them invisible initially
        self.continue_btn.show()
        self.stop_btn.show()
        self.continue_btn.setFixedWidth(0)
        self.stop_btn.setFixedWidth(0)
        
        # Create opacity effect for smooth fade
        from PyQt6.QtWidgets import QGraphicsOpacityEffect
        start_opacity = QGraphicsOpacityEffect(self.start_pause_btn)
        self.start_pause_btn.setGraphicsEffect(start_opacity)
        
        continue_opacity = QGraphicsOpacityEffect(self.continue_btn)
        self.continue_btn.setGraphicsEffect(continue_opacity)
        continue_opacity.setOpacity(0.0)
        
        stop_opacity = QGraphicsOpacityEffect(self.stop_btn)
        self.stop_btn.setGraphicsEffect(stop_opacity)
        stop_opacity.setOpacity(0.0)
        
        # Create animations
        fade_out = QPropertyAnimation(start_opacity, b"opacity")
        fade_out.setDuration(200)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)
        
        width_out = QPropertyAnimation(self.start_pause_btn, b"minimumWidth")
        width_out.setDuration(200)
        width_out.setStartValue(original_width)
        width_out.setEndValue(0)
        
        width_out2 = QPropertyAnimation(self.start_pause_btn, b"maximumWidth")
        width_out2.setDuration(200)
        width_out2.setStartValue(original_width)
        width_out2.setEndValue(0)
        
        fade_in_continue = QPropertyAnimation(continue_opacity, b"opacity")
        fade_in_continue.setDuration(200)
        fade_in_continue.setStartValue(0.0)
        fade_in_continue.setEndValue(1.0)
        
        width_in_continue = QPropertyAnimation(self.continue_btn, b"minimumWidth")
        width_in_continue.setDuration(200)
        width_in_continue.setStartValue(0)
        width_in_continue.setEndValue(150)
        
        width_in_continue2 = QPropertyAnimation(self.continue_btn, b"maximumWidth")
        width_in_continue2.setDuration(200)
        width_in_continue2.setStartValue(0)
        width_in_continue2.setEndValue(150)
        
        fade_in_stop = QPropertyAnimation(stop_opacity, b"opacity")
        fade_in_stop.setDuration(200)
        fade_in_stop.setStartValue(0.0)
        fade_in_stop.setEndValue(1.0)
        
        width_in_stop = QPropertyAnimation(self.stop_btn, b"minimumWidth")
        width_in_stop.setDuration(200)
        width_in_stop.setStartValue(0)
        width_in_stop.setEndValue(150)
        
        width_in_stop2 = QPropertyAnimation(self.stop_btn, b"maximumWidth")
        width_in_stop2.setDuration(200)
        width_in_stop2.setStartValue(0)
        width_in_stop2.setEndValue(150)
        
        # Group animations
        self._button_animations = QParallelAnimationGroup()
        self._button_animations.addAnimation(fade_out)
        self._button_animations.addAnimation(width_out)
        self._button_animations.addAnimation(width_out2)
        self._button_animations.addAnimation(fade_in_continue)
        self._button_animations.addAnimation(width_in_continue)
        self._button_animations.addAnimation(width_in_continue2)
        self._button_animations.addAnimation(fade_in_stop)
        self._button_animations.addAnimation(width_in_stop)
        self._button_animations.addAnimation(width_in_stop2)
        
        def hide_start_button():
            self.start_pause_btn.hide()
            self.start_pause_btn.setGraphicsEffect(None)
            self.continue_btn.setFixedWidth(150)
            self.stop_btn.setFixedWidth(150)
        
        fade_out.finished.connect(hide_start_button)
        self._button_animations.start()
    
    def _animate_to_single_button(self):
        """Animate transition from two buttons back to single button."""
        # Store button widths
        continue_width = self.continue_btn.width()
        stop_width = self.stop_btn.width()
        target_width = 150
        
        # Show start button but make it invisible initially
        self.start_pause_btn.show()
        self.start_pause_btn.setFixedWidth(0)
        
        # Create opacity effects
        from PyQt6.QtWidgets import QGraphicsOpacityEffect
        continue_opacity = QGraphicsOpacityEffect(self.continue_btn)
        self.continue_btn.setGraphicsEffect(continue_opacity)
        
        stop_opacity = QGraphicsOpacityEffect(self.stop_btn)
        self.stop_btn.setGraphicsEffect(stop_opacity)
        
        start_opacity = QGraphicsOpacityEffect(self.start_pause_btn)
        self.start_pause_btn.setGraphicsEffect(start_opacity)
        start_opacity.setOpacity(0.0)
        
        # Create animations
        fade_out_continue = QPropertyAnimation(continue_opacity, b"opacity")
        fade_out_continue.setDuration(200)
        fade_out_continue.setStartValue(1.0)
        fade_out_continue.setEndValue(0.0)
        
        width_out_continue = QPropertyAnimation(self.continue_btn, b"minimumWidth")
        width_out_continue.setDuration(200)
        width_out_continue.setStartValue(continue_width)
        width_out_continue.setEndValue(0)
        
        width_out_continue2 = QPropertyAnimation(self.continue_btn, b"maximumWidth")
        width_out_continue2.setDuration(200)
        width_out_continue2.setStartValue(continue_width)
        width_out_continue2.setEndValue(0)
        
        fade_out_stop = QPropertyAnimation(stop_opacity, b"opacity")
        fade_out_stop.setDuration(200)
        fade_out_stop.setStartValue(1.0)
        fade_out_stop.setEndValue(0.0)
        
        width_out_stop = QPropertyAnimation(self.stop_btn, b"minimumWidth")
        width_out_stop.setDuration(200)
        width_out_stop.setStartValue(stop_width)
        width_out_stop.setEndValue(0)
        
        width_out_stop2 = QPropertyAnimation(self.stop_btn, b"maximumWidth")
        width_out_stop2.setDuration(200)
        width_out_stop2.setStartValue(stop_width)
        width_out_stop2.setEndValue(0)
        
        fade_in = QPropertyAnimation(start_opacity, b"opacity")
        fade_in.setDuration(200)
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)
        
        width_in = QPropertyAnimation(self.start_pause_btn, b"minimumWidth")
        width_in.setDuration(200)
        width_in.setStartValue(0)
        width_in.setEndValue(target_width)
        
        width_in2 = QPropertyAnimation(self.start_pause_btn, b"maximumWidth")
        width_in2.setDuration(200)
        width_in2.setStartValue(0)
        width_in2.setEndValue(target_width)
        
        # Group animations
        self._button_animations = QParallelAnimationGroup()
        self._button_animations.addAnimation(fade_out_continue)
        self._button_animations.addAnimation(width_out_continue)
        self._button_animations.addAnimation(width_out_continue2)
        self._button_animations.addAnimation(fade_out_stop)
        self._button_animations.addAnimation(width_out_stop)
        self._button_animations.addAnimation(width_out_stop2)
        self._button_animations.addAnimation(fade_in)
        self._button_animations.addAnimation(width_in)
        self._button_animations.addAnimation(width_in2)
        
        def hide_two_buttons():
            self.continue_btn.hide()
            self.stop_btn.hide()
            self.continue_btn.setGraphicsEffect(None)
            self.stop_btn.setGraphicsEffect(None)
            self.start_pause_btn.setGraphicsEffect(None)
            self.start_pause_btn.setFixedWidth(150)
        
        fade_out_continue.finished.connect(hide_two_buttons)
        fade_out_stop.finished.connect(hide_two_buttons)
        self._button_animations.start()
    
    def _update_timer(self):
        """Update the timer countdown."""
        if self._remaining_seconds > 0:
            self._remaining_seconds -= 1
            self.timer_widget.set_remaining_seconds(self._remaining_seconds)
        else:
            # Timer finished
            self._countdown_timer.stop()
            self._is_running = False
            self._is_paused = False
            
            if self._is_break_mode:
                # Break timer finished - return to focus mode
                self._is_break_mode = False
                self._remaining_seconds = self._default_timer_seconds
                self.timer_widget.set_total_seconds(self._default_timer_seconds)
                self.timer_widget.set_remaining_seconds(self._remaining_seconds)
                # Animate back to single button if two buttons are showing
                if self.continue_btn.isVisible() or self.stop_btn.isVisible():
                    self._animate_to_single_button()
                self.start_pause_btn.setText("Start to Focus")
                play_icon = self._create_play_icon()
                self.start_pause_btn.setIcon(play_icon)
            else:
                # Focus timer finished - record statistics
                if self._current_session:
                    self._current_session["events"].append({"type": "finished", "time": datetime.now()})
                    self._record_timer_event(self._current_session["task"], "finished")
                    self._record_timer_session(self._current_session["task"], completed=True)
                    self._current_session = None
                
                # Play sound notification
                self._play_completion_sound()
                
                # Show Windows notification
                self._show_focus_complete_notification()
                
                # Animate back to single button if two buttons are showing
                if self.continue_btn.isVisible() or self.stop_btn.isVisible():
                    self._animate_to_single_button()
                self.start_pause_btn.setText("Start to Focus")
                play_icon = self._create_play_icon()
                self.start_pause_btn.setIcon(play_icon)
    
    def _init_windows_notification(self):
        """Initialize Windows notification system."""
        try:
            # Use win10toast (simple and reliable)
            from win10toast import ToastNotifier
            self._toast_notifier = ToastNotifier()
            self._notifications_available = True
        except ImportError:
            # Fallback: Try Windows Runtime API if available
            try:
                import winrt.windows.ui.notifications as notifications
                self._notifications_available = True
            except ImportError:
                self._notifications_available = False
    
    def _play_completion_sound(self):
        """Play a sound when timer completes."""
        try:
            import winsound
            # Play Windows default notification sound (asterisk)
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except Exception:
            # If sound fails, continue silently
            pass
    
    def _show_focus_complete_notification(self):
        """Show Windows notification in notification center when focus timer completes."""
        if not self._notifications_available:
            return
        
        try:
            # Use win10toast (primary method - shows in notification center)
            try:
                from win10toast import ToastNotifier
                toaster = ToastNotifier()
                toaster.show_toast(
                    "Focus Time Complete!",
                    "Your focus session has ended. Time for a break!",
                    duration=5,
                    threaded=True
                )
            except ImportError:
                # Fallback: Try Windows Runtime API if win10toast not available
                try:
                    import winrt.windows.ui.notifications as notifications
                    import winrt.windows.data.xml.dom as dom
                    
                    # Create toast notification XML
                    toast_xml = notifications.ToastNotificationManager.get_template_content(
                        notifications.ToastTemplateType.TOAST_TEXT02
                    )
                    
                    # Set text
                    text_nodes = toast_xml.get_elements_by_tag_name("text")
                    if len(text_nodes) >= 2:
                        text_nodes[0].append_child(toast_xml.create_text_node("Focus Time Complete!"))
                        text_nodes[1].append_child(toast_xml.create_text_node("Your focus session has ended. Time for a break!"))
                    
                    # Create and show notification (this will appear in notification center)
                    toast = notifications.ToastNotification(toast_xml)
                    notifier = notifications.ToastNotificationManager.create_toast_notifier("Notely")
                    notifier.show(toast)
                except (ImportError, AttributeError):
                    pass
        except Exception:
            # If notification fails, continue silently
            pass
    
    def _record_timer_event(self, task_name, event_type):
        """Record a timer event (start, pause, resume, stop, finished) for a task."""
        if task_name not in self._task_statistics:
            self._task_statistics[task_name] = {"sessions": [], "total_time": 0, "events": []}
        
        stats = self._task_statistics[task_name]
        
        # Initialize events list if it doesn't exist
        if "events" not in stats:
            stats["events"] = []
        
        # Record the event
        stats["events"].append({
            "type": event_type,
            "time": datetime.now()
        })
        
        # Update statistics display if we're on Tasks view and this task is selected
        if hasattr(self, 'tasks_list') and self._current_view == "Tasks":
            current_item = self.tasks_list.currentItem()
            if current_item and current_item.text() == task_name:
                self._update_task_statistics_display(task_name)
    
    def _record_timer_session(self, task_name, completed=False):
        """Record a timer session for a task.
        
        Args:
            task_name: Name of the task
            completed: True if timer finished naturally, False if stopped early
        """
        if not self._current_session or self._current_session["task"] != task_name:
            return
        
        if task_name not in self._task_statistics:
            self._task_statistics[task_name] = {"sessions": [], "total_time": 0, "events": []}
        
        stats = self._task_statistics[task_name]
        
        # Calculate actual duration (25 minutes minus paused time, or actual time if stopped early)
        end_time = datetime.now()
        
        # Get the timer duration that was set when session started
        session_timer_duration = self._current_session.get("timer_duration", self._default_timer_seconds)
        
        # Check if session was completed (timer reached 0) or stopped early
        if completed:
            # Completed session - full timer duration minus paused time
            total_duration = session_timer_duration
        else:
            # Stopped early - calculate actual elapsed time
            elapsed = (end_time - self._current_session["start"]).total_seconds()
            total_duration = elapsed
        
        # Subtract paused time from total
        for pause_start, pause_end in self._current_session["pauses"]:
            pause_duration = (pause_end - pause_start).total_seconds()
            total_duration -= pause_duration
        
        # If currently paused, subtract current pause time
        if self._current_session.get("paused_at"):
            current_pause_duration = (end_time - self._current_session["paused_at"]).total_seconds()
            total_duration -= current_pause_duration
        
        # Ensure duration is not negative
        total_duration = max(0, int(total_duration))
        
        # Create session record
        session = {
            "start": self._current_session["start"],
            "end": end_time,
            "pauses": self._current_session["pauses"].copy(),
            "duration": total_duration,
            "events": self._current_session["events"].copy(),
            "completed": completed
        }
        
        # Add session to list
        if "sessions" not in stats:
            stats["sessions"] = []
        stats["sessions"].append(session)
        stats["total_time"] += total_duration
        
        # Clear current session
        self._current_session = None
        
        # Update statistics display if we're on Tasks view and this task is selected
        if hasattr(self, 'tasks_list') and self._current_view == "Tasks":
            current_item = self.tasks_list.currentItem()
            if current_item and current_item.text() == task_name:
                self._update_task_statistics_display(task_name)
        
        # Update statistics view if we're on Statistics view
        if self._current_view == "Statistics" and hasattr(self, 'statistics_view'):
            self._update_statistics_display()
    
    def _setup_shortcuts(self):
        """Setup keyboard shortcuts."""
        # Ctrl+Shift+R to reset all Pomodoro data (only in Tasks view)
        reset_shortcut = QShortcut(QKeySequence("Ctrl+Shift+R"), self)
        reset_shortcut.activated.connect(self._handle_reset_shortcut)
    
    def _handle_reset_shortcut(self):
        """Handle Ctrl+Shift+R shortcut - reset all data if in Tasks view."""
        if self._current_view == "Tasks":
            self._reset_all_pomodoro_data()
    
    def _reset_all_pomodoro_data(self):
        """Reset all Pomodoro data to default values."""
        # Show confirmation dialog
        reply = QMessageBox.question(
            self,
            "Reset All Data",
            "Are you sure you want to reset all Pomodoro data?\n\nThis will:\n"
            "- Clear all task statistics\n"
            "- Remove all custom tasks\n"
            "- Reset timer to default (25 minutes)\n"
            "- Clear current session\n\n"
            "This action cannot be undone!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Stop timer if running
            if self._is_running:
                self._countdown_timer.stop()
            
            # Reset timer state
            self._default_timer_seconds = 25 * 60
            self._remaining_seconds = self._default_timer_seconds
            self._is_running = False
            self._is_paused = False
            self._is_break_mode = False
            self._break_seconds = 0
            
            # Reset task management
            self._selected_task = None
            self._custom_tasks = []
            self._task_statistics = {}
            self._current_session = None
            
            # Update UI
            self.task_button.setText("Please select a task...")
            self.timer_widget.set_total_seconds(self._default_timer_seconds)
            self.timer_widget.set_remaining_seconds(self._remaining_seconds)
            
            # Reset button state
            if self.continue_btn.isVisible() or self.stop_btn.isVisible():
                self._animate_to_single_button()
            self.start_pause_btn.setText("Start to Focus")
            play_icon = self._create_play_icon()
            self.start_pause_btn.setIcon(play_icon)
            
            # Refresh tasks list if we're on Tasks view
            if hasattr(self, 'tasks_list'):
                self._refresh_tasks_list()
                # Clear statistics display
                if hasattr(self, 'stats_list'):
                    self.stats_list.clear()
                    placeholder_item = QListWidgetItem("Select a task to view history")
                    placeholder_item.setFlags(Qt.ItemFlag.NoItemFlags)
                    placeholder_item.setSizeHint(QSize(200, 40))
                    self.stats_list.addItem(placeholder_item)
            
            # Update statistics view if we're on Statistics view
            if self._current_view == "Statistics" and hasattr(self, 'statistics_view'):
                self._update_statistics_display()
            
            QMessageBox.information(
                self,
                "Reset Complete",
                "All Pomodoro data has been reset to default values."
            )
    
    def paintEvent(self, event):
        """Draw the window background with rounded corners."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        theme = self._theme_manager.get_theme()
        bg_color = QColor(theme.get("window_bg", "#f5f5f5"))
        bg_opacity = theme.get("window_bg_opacity", 240)
        bg_color.setAlpha(bg_opacity)
        border_color = QColor(theme.get("window_border_color", "#c8c8c8"))
        border_radius = theme.get("border_radius", 12)
        
        # Draw rounded rectangle background
        rect = QRectF(self.rect())
        path = QPainterPath()
        path.addRoundedRect(rect, border_radius, border_radius)
        
        painter.fillPath(path, QBrush(bg_color))
        painter.setPen(QPen(border_color, 1))
        painter.drawPath(path)

