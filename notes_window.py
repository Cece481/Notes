"""
Notes window with Windows 11 styling, tabs, and auto-save functionality.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
    QPushButton, QTabWidget, QMessageBox, QTabBar, QMenu, QInputDialog,
    QColorDialog, QToolButton, QComboBox, QStyledItemDelegate, QStyle, QFileDialog
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QRectF, QPropertyAnimation, QEasingCurve, QEvent, QParallelAnimationGroup, QSequentialAnimationGroup, QSize, QModelIndex, QObject, pyqtSlot, QPoint
from PyQt6.QtGui import QFont, QPainter, QPainterPath, QColor, QBrush, QPen, QKeyEvent, QTextCursor, QTextCharFormat, QTextFormat, QIcon, QPixmap, QFontMetrics, QTextObjectInterface, QTextDocument, QKeySequence, QShortcut
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QGraphicsOpacityEffect
import config
from theme_manager import ThemeManager
import re
import json


class CheckableTextEdit(QTextEdit):
    """Custom QTextEdit that handles embedded checkboxes."""
    
    checkbox_toggled = pyqtSignal(str, bool)  # checkbox_id, checked state
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._checkbox_data = {}  # {checkbox_id: (position, checked)}
        self._next_checkbox_id = 0
    
    def mousePressEvent(self, event):
        """Handle mouse clicks to toggle checkboxes."""
        if event.button() == Qt.MouseButton.LeftButton:
            cursor = self.cursorForPosition(event.pos())
            pos = cursor.position()
            
            # Check if click is on a checkbox
            for checkbox_id, (cb_pos, checked) in list(self._checkbox_data.items()):
                # Allow small tolerance for clicking
                if abs(cb_pos - pos) <= 1:
                    self._toggle_checkbox_at_position(cb_pos, checkbox_id, not checked)
                    event.accept()
                    return
        
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """Prevent selection of checkbox characters."""
        if event.buttons() & Qt.MouseButton.LeftButton:
            cursor = self.textCursor()
            if cursor.hasSelection():
                start = cursor.selectionStart()
                end = cursor.selectionEnd()
                
                # Check if selection includes any checkbox
                for checkbox_id, (cb_pos, checked) in self._checkbox_data.items():
                    if start <= cb_pos < end:
                        # Clear selection and move cursor away from checkbox
                        cursor.setPosition(end if end > cb_pos else start)
                        self.setTextCursor(cursor)
                        return
        
        super().mouseMoveEvent(event)
    
    def _toggle_checkbox_at_position(self, position, checkbox_id, new_checked):
        """Toggle checkbox at given position."""
        cursor = self.textCursor()
        cursor.setPosition(position)
        cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor)
        
        selected = cursor.selectedText()
        if selected in ['☐', '☑']:
            # Update the character
            new_char = '☑' if new_checked else '☐'
            
            # Apply formatting with animation effect
            fmt = cursor.charFormat()
            if new_checked:
                # Use white color for checked checkbox
                fmt.setForeground(QColor(Qt.GlobalColor.white))
                fmt.setFontWeight(QFont.Weight.Bold)
            else:
                try:
                    theme_manager = ThemeManager.get_instance()
                    theme = theme_manager.get_theme()
                    text_color = QColor(theme.get("text_primary", "#000000"))
                    fmt.setForeground(text_color)
                    fmt.setFontWeight(QFont.Weight.Normal)
                except:
                    fmt.setForeground(QColor("#000000"))
                    fmt.setFontWeight(QFont.Weight.Normal)
            
            cursor.setCharFormat(fmt)
            cursor.insertText(new_char)
            
            # Update stored data
            self._checkbox_data[checkbox_id] = (position, new_checked)
            self.checkbox_toggled.emit(checkbox_id, new_checked)
    
    def insert_checkbox(self, checked=False):
        """Insert a checkbox at current cursor position."""
        cursor = self.textCursor()
        position = cursor.position()
        
        checkbox_id = f"cb_{self._next_checkbox_id}"
        self._next_checkbox_id += 1
        
        # Create format
        fmt = QTextCharFormat()
        if checked:
            # Use white color for checked checkbox
            fmt.setForeground(QColor(Qt.GlobalColor.white))
            fmt.setFontWeight(QFont.Weight.Bold)
        
        cursor.setCharFormat(fmt)
        checkbox_char = '☑' if checked else '☐'
        cursor.insertText(checkbox_char)
        
        # Store checkbox data
        new_pos = cursor.position() - 1
        self._checkbox_data[checkbox_id] = (new_pos, checked)
        
        self.setTextCursor(cursor)
        return checkbox_id
    
    def get_checkbox_states(self):
        """Get all checkbox states for saving."""
        return {cb_id: checked for cb_id, (pos, checked) in self._checkbox_data.items()}
    
    def set_checkbox_states(self, states):
        """Restore checkbox states from saved data."""
        # Find checkboxes in text and update their states
        text = self.toPlainText()
        new_data = {}
        pos = 0
        
        for checkbox_id, checked in states.items():
            # Find next checkbox character
            cb_pos = text.find('☐', pos)
            if cb_pos == -1:
                cb_pos = text.find('☑', pos)
            
            if cb_pos >= 0:
                new_data[checkbox_id] = (cb_pos, checked)
                pos = cb_pos + 1
                
                # Apply formatting
                cursor = self.textCursor()
                cursor.setPosition(cb_pos)
                cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor)
                
                fmt = cursor.charFormat()
                if checked:
                    # Use white color for checked checkbox
                    fmt.setForeground(QColor(Qt.GlobalColor.white))
                    fmt.setFontWeight(QFont.Weight.Bold)
                    cursor.insertText('☑')
                else:
                    try:
                        theme_manager = ThemeManager.get_instance()
                        theme = theme_manager.get_theme()
                        text_color = QColor(theme.get("text_primary", "#000000"))
                        fmt.setForeground(text_color)
                        fmt.setFontWeight(QFont.Weight.Normal)
                    except:
                        fmt.setForeground(QColor("#000000"))
                        fmt.setFontWeight(QFont.Weight.Normal)
                    cursor.insertText('☐')
        
        self._checkbox_data = new_data


class AnimatedComboBox(QComboBox):
    """QComboBox with smooth dropdown animation."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._view = None
        self._animation = None
    
    def showPopup(self):
        """Override to add animation when showing popup."""
        super().showPopup()
        
        # Get the view (dropdown list)
        view = self.view()
        if view:
            # Set initial opacity
            view.setWindowOpacity(0.0)
            
            # Create fade-in animation
            if self._animation:
                self._animation.stop()
            
            self._animation = QPropertyAnimation(view, b"windowOpacity")
            self._animation.setDuration(200)  # 200ms animation
            self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._animation.setStartValue(0.0)
            self._animation.setEndValue(1.0)
            self._animation.start()


class AnimatedMenu(QMenu):
    """QMenu with smooth opening animation."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._animation = None
    
    def showEvent(self, event):
        """Override to add animation when showing menu."""
        # Set initial opacity
        self.setWindowOpacity(0.0)
        
        # Create fade-in animation
        if self._animation:
            self._animation.stop()
        
        # Fade animation
        fade_anim = QPropertyAnimation(self, b"windowOpacity")
        fade_anim.setDuration(200)
        fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        fade_anim.setStartValue(0.0)
        fade_anim.setEndValue(1.0)
        
        self._animation = fade_anim
        self._animation.start()
        
        super().showEvent(event)


class FontFamilyDelegate(QStyledItemDelegate):
    """Custom delegate to display font names in their respective fonts."""
    
    def paint(self, painter, option, index):
        """Paint the item with its font."""
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
            text_color = option.palette.highlightedText().color()
        else:
            text_color = option.palette.text().color()
        
        painter.setPen(text_color)
        
        font_name = index.data(Qt.ItemDataRole.DisplayRole)
        if font_name:
            font = QFont(font_name, 9)
            painter.setFont(font)
            
            available_width = option.rect.width() - 10
            metrics = QFontMetrics(font)
            elided_text = metrics.elidedText(font_name, Qt.TextElideMode.ElideRight, available_width)
            
            painter.drawText(option.rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, elided_text)
        else:
            super().paint(painter, option, index)
    
    def sizeHint(self, option, index):
        """Return size hint for the item."""
        font_name = index.data(Qt.ItemDataRole.DisplayRole)
        if font_name:
            font = QFont(font_name, 9)
            metrics = QFontMetrics(font)
            return QSize(metrics.horizontalAdvance(font_name) + 10, 20)
        return super().sizeHint(option, index)


class NotesWindow(QWidget):
    """Notepad window with modern Windows 11 styling and tabs support."""
    
    content_changed = pyqtSignal(str)  # Emitted when content changes
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._save_timer = QTimer()
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._on_save_timeout)
        self._plus_tab_index = -1  # Initialize plus tab index
        
        # Get theme manager and register for updates
        self._theme_manager = ThemeManager.get_instance()
        self._theme_manager.register_listener(self._apply_theme)
        self._theme_manager.theme_changed.connect(self._apply_theme)
        
        self._setup_ui()
        self._setup_styling()
        self._apply_theme()
    
    def _setup_ui(self):
        """Setup the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # Tab widget with custom tab bar
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        self.tab_widget.tabCloseRequested.connect(self._close_tab)
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
        
        # Connect to tab moved signal to update plus tab index
        self.tab_widget.tabBar().tabMoved.connect(self._on_tab_moved)
        
        # Enable context menu on tab bar
        self.tab_widget.tabBar().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tab_widget.tabBar().customContextMenuRequested.connect(self._show_tab_context_menu)
        
        layout.addWidget(self.tab_widget)
        
        # Create toolbar toggle button
        self.toolbar_toggle_btn = self._create_toolbar_toggle_button()
        layout.addWidget(self.toolbar_toggle_btn)
        
        # Create formatting toolbar
        self.formatting_toolbar = self._create_formatting_toolbar()
        layout.addWidget(self.formatting_toolbar)
        
        # Store toolbar visibility state
        self._toolbar_visible = True
        self._toolbar_animation = None
        self._toolbar_natural_height = None
        
        # Create initial tab (the + button will be added as a tab)
        self._add_new_tab()
        self._add_plus_tab()
        
        # Setup keyboard shortcuts
        self._setup_shortcuts()
    
    def _setup_shortcuts(self):
        """Setup keyboard shortcuts."""
        # Keyboard shortcuts can be added here in the future
        pass
    
    def _save_as_text_file(self):
        """Save current note tab as a text file."""
        text_edit = self._get_current_text_edit()
        if not text_edit:
            QMessageBox.warning(self, "No Note", "No note is currently open.")
            return
        
        # Get current tab name for default filename
        current_index = self.tab_widget.currentIndex()
        if current_index >= 0:
            tab_name = self.tab_widget.tabText(current_index)
            # Remove invalid filename characters
            import os
            invalid_chars = '<>:"/\\|?*'
            for char in invalid_chars:
                tab_name = tab_name.replace(char, '_')
            default_filename = f"{tab_name}.txt" if tab_name else "note.txt"
        else:
            default_filename = "note.txt"
        
        # Open file dialog
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Save Note as Text File",
            default_filename,
            "Text Files (*.txt);;All Files (*)"
        )
        
        if file_path:
            try:
                # Get plain text content (removes formatting)
                plain_text = text_edit.toPlainText()
                
                # Write to file
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(plain_text)
                
                QMessageBox.information(
                    self,
                    "Success",
                    f"Note saved successfully to:\n{file_path}"
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to save file:\n{str(e)}"
                )
    
    def _get_button_style(self):
        """Get button style based on theme."""
        is_dark = ThemeManager.is_dark_mode()
        if is_dark:
            return """
                QPushButton {
                    background-color: rgba(60, 60, 60, 200);
                    color: white;
                    border: 1px solid rgba(100, 100, 100, 150);
                    border-radius: 5px;
                    font-weight: bold;
                    font-size: 16px;
                }
                QPushButton:hover {
                    background-color: rgba(80, 80, 80, 220);
                    border: 1px solid rgba(0, 120, 215, 200);
                }
                QPushButton:pressed {
                    background-color: rgba(50, 50, 50, 240);
                }
            """
        else:
            return """
                QPushButton {
                    background-color: rgba(240, 240, 240, 200);
                    color: black;
                    border: 1px solid rgba(200, 200, 200, 150);
                    border-radius: 5px;
                    font-weight: bold;
                    font-size: 16px;
                }
                QPushButton:hover {
                    background-color: rgba(230, 230, 230, 220);
                    border: 1px solid rgba(0, 120, 215, 200);
                }
                QPushButton:pressed {
                    background-color: rgba(220, 220, 220, 240);
                }
            """
    
    def _setup_styling(self):
        """Apply Windows 11 styling with dark mode support."""
        # Set window properties
        self.setMinimumSize(config.NOTES_WINDOW_MIN_WIDTH, config.NOTES_WINDOW_MIN_HEIGHT)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    
    def _apply_theme(self):
        """Apply current theme to the notes window."""
        theme = self._theme_manager.get_theme()
        
        # Convert hex colors to rgba
        def hex_to_rgba(hex_color, alpha=255):
            color = QColor(hex_color)
            return f"rgba({color.red()}, {color.green()}, {color.blue()}, {alpha})"
        
        bg_color = theme["window_bg"]
        bg_opacity = theme.get("window_bg_opacity", 240)
        border_color = theme["border_color"]
        window_border_color = theme.get("window_border_color", border_color)
        text_color = theme["text_primary"]
        tab_active = theme["tab_bg_active"]
        tab_inactive = theme["tab_bg_inactive"]
        tab_text = theme["tab_text_color"]
        accent = theme["accent_color"]
        scrollbar = theme["scrollbar_color"]
        radius = theme.get("border_radius", 12)
        font_family = theme.get("font_family", "Segoe UI")
        font_size = theme.get("font_size", 11)
        
        # Window opacity
        window_opacity = theme.get("window_opacity", 95) / 100.0
        self.setWindowOpacity(window_opacity)
        
        # Generate stylesheet
        tab_style = f"""
            QTabWidget::pane {{
                border: 1px solid {hex_to_rgba(window_border_color, 150)};
                border-radius: {radius}px;
                background-color: {hex_to_rgba(bg_color, bg_opacity)};
                top: -1px;
            }}
            QTabBar::tab {{
                background-color: {hex_to_rgba(tab_inactive, 200)};
                color: {hex_to_rgba(tab_text, 200)};
                padding: 8px 15px;
                margin-right: 2px;
                border-top-left-radius: {radius - 2}px;
                border-top-right-radius: {radius - 2}px;
                border: 1px solid {hex_to_rgba(border_color, 150)};
            }}
            QTabBar::tab:selected {{
                background-color: {hex_to_rgba(tab_active, bg_opacity)};
                color: {tab_text};
                border-bottom: 1px solid {hex_to_rgba(tab_active, bg_opacity)};
            }}
            QTabBar::tab:hover {{
                background-color: {hex_to_rgba(tab_inactive, 220)};
            }}
            QTabBar::close-button {{
                image: none;
                subcontrol-position: right;
                margin: 2px;
            }}
            QTextEdit {{
                background-color: {hex_to_rgba(bg_color, bg_opacity)};
                border: none;
                border-radius: {radius}px;
                padding: 10px;
                color: {text_color};
                font-family: "{font_family}";
                font-size: {font_size}pt;
                selection-background-color: {hex_to_rgba(accent, 180)};
                selection-color: {text_color};
            }}
            QTextEdit:focus {{
                border: 1px solid {hex_to_rgba(accent, 200)};
            }}
            QScrollBar:vertical {{
                background-color: {hex_to_rgba(scrollbar, 200)};
                width: 12px;
                border: none;
                border-radius: 6px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background-color: {hex_to_rgba(scrollbar, 200)};
                border-radius: 6px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {hex_to_rgba(scrollbar, 255)};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """
        
        self.tab_widget.setStyleSheet(tab_style)
        
        # Update font for all text editors
        font = QFont(font_family, font_size)
        for i in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(i)
            if isinstance(widget, QTextEdit):
                widget.setFont(font)
        
        # Update toolbar styling if it exists
        if hasattr(self, 'formatting_toolbar'):
            self._apply_toolbar_theme()
        
        # Update toggle button styling if it exists
        if hasattr(self, 'toolbar_toggle_btn'):
            self._apply_toggle_button_theme()
        
        # Force repaint to update border color
        self.update()
    
    def _create_toolbar_toggle_button(self):
        """Create a button to toggle toolbar visibility."""
        toggle_btn = QPushButton("▼")
        toggle_btn.setCheckable(True)
        toggle_btn.setChecked(True)  # Toolbar visible by default
        toggle_btn.setToolTip("Show/Hide Formatting Toolbar")
        toggle_btn.clicked.connect(self._toggle_toolbar_visibility)
        toggle_btn.setFixedSize(20, 20)
        return toggle_btn
    
    def _toggle_toolbar_visibility(self):
        """Toggle the visibility of the formatting toolbar with smooth animation."""
        # Store natural height on first use
        if self._toolbar_natural_height is None:
            self.formatting_toolbar.show()
            self.formatting_toolbar.adjustSize()
            natural_h = self.formatting_toolbar.sizeHint().height()
            if natural_h <= 0:
                natural_h = self.formatting_toolbar.height()
            if natural_h <= 0:
                natural_h = 40  # Fallback default height
            self._toolbar_natural_height = natural_h
        
        # Stop any ongoing animation
        if self._toolbar_animation:
            self._toolbar_animation.stop()
            try:
                self._toolbar_animation.finished.disconnect()
            except:
                pass
        
        # Toggle visibility state
        self._toolbar_visible = not self._toolbar_visible
        
        # Create animation for smooth show/hide
        self._toolbar_animation = QPropertyAnimation(self.formatting_toolbar, b"maximumHeight")
        self._toolbar_animation.setDuration(250)  # 250ms animation
        self._toolbar_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        if self._toolbar_visible:
            # Show: animate from 0 to natural height
            self.formatting_toolbar.setVisible(True)
            current_max = self.formatting_toolbar.maximumHeight()
            if current_max == 16777215:  # QSizePolicy default
                current_max = 0
            self.formatting_toolbar.setMaximumHeight(current_max)
            self._toolbar_animation.setStartValue(current_max)
            self._toolbar_animation.setEndValue(self._toolbar_natural_height)
            
            def reset_max_height():
                self.formatting_toolbar.setMaximumHeight(16777215)
            
            self._toolbar_animation.finished.connect(reset_max_height)
            self.toolbar_toggle_btn.setText("▼")
        else:
            # Hide: animate from current height to 0
            current_height = self.formatting_toolbar.height()
            if current_height <= 0:
                current_height = self._toolbar_natural_height
            self.formatting_toolbar.setMaximumHeight(current_height)
            self._toolbar_animation.setStartValue(current_height)
            self._toolbar_animation.setEndValue(0)
            
            def hide_after_animation():
                self.formatting_toolbar.setVisible(False)
                self.formatting_toolbar.setMaximumHeight(16777215)
            
            self._toolbar_animation.finished.connect(hide_after_animation)
            self.toolbar_toggle_btn.setText("▲")
        
        # Start animation
        self._toolbar_animation.start()
    
    def _apply_toggle_button_theme(self):
        """Apply theme styling to the toolbar toggle button."""
        theme = self._theme_manager.get_theme()
        
        def hex_to_rgba(hex_color, alpha=255):
            color = QColor(hex_color)
            return f"rgba({color.red()}, {color.green()}, {color.blue()}, {alpha})"
        
        # Use theme colors
        button_bg = theme.get("button_bg", theme.get("window_bg", "#3c3c3c"))
        button_hover = theme.get("button_hover", button_bg)
        button_text = theme.get("button_text", theme.get("text_primary", "#ffffff"))
        border_color = theme.get("border_color", "#646464")
        
        # Minimalist styling with theme colors
        bg_color = hex_to_rgba(button_bg, 180)
        hover_bg = hex_to_rgba(button_hover, 220)
        text_color = hex_to_rgba(button_text, 255)
        border = hex_to_rgba(border_color, 100)
        
        toggle_style = f"""
            QPushButton {{
                background-color: {bg_color};
                color: {text_color};
                border: 1px solid {border};
                border-radius: 5px;
                padding: 0px;
                font-size: 10px;
                font-weight: normal;
            }}
            QPushButton:hover {{
                background-color: {hover_bg};
                border: 1px solid {border};
            }}
            QPushButton:pressed {{
                background-color: {bg_color};
            }}
        """
        
        self.toolbar_toggle_btn.setStyleSheet(toggle_style)
    
    def _create_formatting_toolbar(self):
        """Create the formatting toolbar with Material Symbols icons."""
        toolbar = QWidget()
        toolbar_layout = QVBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(3, 3, 3, 3)
        toolbar_layout.setSpacing(3)
        
        # First row
        first_row = QHBoxLayout()
        first_row.setSpacing(3)
        first_row.setContentsMargins(0, 0, 0, 0)
        
        # Bold button
        self.bold_btn = QToolButton()
        bold_icon = self._create_material_icon("format_bold")
        self.bold_btn.setIcon(bold_icon)
        self.bold_btn.setIconSize(QSize(18, 18))
        self.bold_btn.setCheckable(True)
        self.bold_btn.setToolTip("Bold (Ctrl+B)")
        self.bold_btn.clicked.connect(self._toggle_bold)
        first_row.addWidget(self.bold_btn)
        
        # Italic button
        self.italic_btn = QToolButton()
        italic_icon = self._create_material_icon("format_italic")
        self.italic_btn.setIcon(italic_icon)
        self.italic_btn.setIconSize(QSize(18, 18))
        self.italic_btn.setCheckable(True)
        self.italic_btn.setToolTip("Italic (Ctrl+I)")
        self.italic_btn.clicked.connect(self._toggle_italic)
        first_row.addWidget(self.italic_btn)
        
        # Separator
        first_row.addSpacing(5)
        
        # Text Color button
        self.text_color_btn = QToolButton()
        self.text_color_btn.setToolTip("Text Color")
        self.text_color_btn.clicked.connect(self._choose_text_color)
        color_icon = self._create_color_icon()  # Use theme color by default
        self.text_color_btn.setIcon(color_icon)
        self.text_color_btn.setIconSize(QSize(16, 16))
        first_row.addWidget(self.text_color_btn)
        
        # Separator
        first_row.addSpacing(5)
        
        # Bullet List button with dropdown menu
        self.bullet_list_btn = QToolButton()
        self.bullet_list_btn.setToolTip("Bullet List (Ctrl+Shift+L)")
        self.bullet_list_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        triangle_icon = self._create_triangle_icon()
        self.bullet_list_btn.setIcon(triangle_icon)
        self.bullet_list_btn.setIconSize(QSize(12, 12))
        bullet_menu = AnimatedMenu(self)
        bullet_menu.addAction("• Filled circle").triggered.connect(lambda: self._insert_bullet("•"))
        bullet_menu.addAction("- Dash").triggered.connect(lambda: self._insert_bullet("-"))
        bullet_menu.addAction("* Asterisk").triggered.connect(lambda: self._insert_bullet("*"))
        self.bullet_list_btn.setMenu(bullet_menu)
        first_row.addWidget(self.bullet_list_btn)
        
        # Numbered List button
        self.numbered_list_btn = QToolButton()
        self.numbered_list_btn.setText("1.")
        self.numbered_list_btn.setObjectName("numbered_list_btn")  # For styling
        self.numbered_list_btn.setToolTip("Numbered List (Ctrl+Shift+N)")
        self.numbered_list_btn.clicked.connect(self._insert_numbered_list)
        first_row.addWidget(self.numbered_list_btn)
        
        # Checkbox button
        self.checkbox_btn = QToolButton()
        checkbox_icon = self._create_checkbox_icon()
        self.checkbox_btn.setIcon(checkbox_icon)
        self.checkbox_btn.setIconSize(QSize(18, 18))
        self.checkbox_btn.setToolTip("Insert Checkbox")
        self.checkbox_btn.clicked.connect(self._insert_checkbox)
        first_row.addWidget(self.checkbox_btn)
        
        # Separator
        first_row.addSpacing(5)
        
        # Font Family dropdown
        self.font_family_combo = AnimatedComboBox()
        self.font_family_combo.setToolTip("Font Family")
        font_list = [
            "Arial", "Times New Roman", "Calibri", "Verdana", 
            "Comic Sans MS", "Courier New", "Georgia", "Segoe UI"
        ]
        self.font_family_combo.addItems(font_list)
        self.font_family_combo.setEditable(False)
        self.font_family_combo.currentTextChanged.connect(self._change_font_family)
        self.font_family_combo.setMinimumWidth(70)
        self.font_family_combo.setMaximumWidth(70)
        
        # Set custom delegate to show fonts in their own font
        font_delegate = FontFamilyDelegate(self.font_family_combo)
        self.font_family_combo.setItemDelegate(font_delegate)
        self.font_family_combo.currentIndexChanged.connect(self._update_font_combo_display)
        
        first_row.addWidget(self.font_family_combo)
        
        # Font Size dropdown
        self.font_size_combo = AnimatedComboBox()
        self.font_size_combo.setToolTip("Font Size")
        self.font_size_combo.addItems([
            "8", "9", "10", "11", "12", "14", "16", "18", 
            "20", "24", "28", "32", "36", "48", "72"
        ])
        self.font_size_combo.setEditable(True)
        self.font_size_combo.currentTextChanged.connect(self._change_font_size)
        self.font_size_combo.setMinimumWidth(45)
        self.font_size_combo.setMaximumWidth(45)
        first_row.addWidget(self.font_size_combo)
        
        first_row.addStretch()
        toolbar_layout.addLayout(first_row)
        
        # Store current text color
        self._current_text_color = QColor(Qt.GlobalColor.black)
        
        return toolbar
    
    def _create_material_icon(self, icon_name):
        """Create a Material Symbols icon."""
        pixmap = QPixmap(20, 20)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Get theme colors
        theme = self._theme_manager.get_theme()
        button_text = theme.get("button_text", theme.get("text_primary", "#ffffff"))
        text_color = QColor(button_text)
        painter.setPen(QPen(text_color))
        
        # Try Material Symbols Outlined font first
        material_font = QFont("Material Symbols Outlined", 18)
        metrics = QFontMetrics(material_font)
        
        # Material Symbols Unicode characters
        icon_chars = {
            "format_bold": "\uE238",
            "format_italic": "\uE23F",
            "format_list_bulleted": "\uE241",
            "format_list_numbered": "\uE242"
        }
        
        char = icon_chars.get(icon_name, "")
        
        # Check if Material Symbols font is available
        if not char or not metrics.inFont(char):
            # Try Material Icons as fallback
            material_font = QFont("Material Icons", 18)
            metrics = QFontMetrics(material_font)
            if not char or not metrics.inFont(char):
                # Final fallback - use text representation
                fallback_text = {
                    "format_bold": "B",
                    "format_italic": "I",
                    "format_list_bulleted": "•",
                    "format_list_numbered": "1."
                }
                char = fallback_text.get(icon_name, "")
                fallback_font = QFont("Segoe UI", 14, QFont.Weight.Bold)
                painter.setFont(fallback_font)
            else:
                painter.setFont(material_font)
        else:
            painter.setFont(material_font)
        
        painter.drawText(QRectF(0, 0, 20, 20), Qt.AlignmentFlag.AlignCenter, char)
        painter.end()
        return QIcon(pixmap)
    
    def _create_color_icon(self, color=None):
        """Create a brush icon from SVG for the text color button."""
        # If no color provided, use theme button_text color
        if color is None:
            theme = self._theme_manager.get_theme()
            button_text = theme.get("button_text", theme.get("text_primary", "#ffffff"))
            fill_color = button_text
        else:
            # Use the provided color (for showing selected text color)
            fill_color = color.name()
        
        svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 -960 960 960" width="24px" fill="{fill_color}">
            <path d="M240-120q-45 0-89-22t-71-58q26 0 53-20.5t27-59.5q0-50 35-85t85-35q50 0 85 35t35 85q0 66-47 113t-113 47Zm0-80q33 0 56.5-23.5T320-280q0-17-11.5-28.5T280-320q-17 0-28.5 11.5T240-280q0 23-5.5 42T220-202q5 2 10 2h10Zm230-160L360-470l358-358q11-11 27.5-11.5T774-828l54 54q12 12 12 28t-12 28L470-360Zm-190 80Z"/>
        </svg>"""
        
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        svg_renderer = QSvgRenderer(svg_content.encode('utf-8'))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        svg_renderer.render(painter)
        painter.end()
        
        return QIcon(pixmap)
    
    def _create_triangle_icon(self):
        """Create a triangle dropdown icon."""
        theme = self._theme_manager.get_theme()
        button_text = theme.get("button_text", theme.get("text_primary", "#ffffff"))
        text_color = QColor(button_text)
        
        pixmap = QPixmap(12, 12)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw a downward-pointing triangle
        painter.setPen(QPen(text_color, 1))
        painter.setBrush(QBrush(text_color))
        
        # Triangle points: top-left, top-right, bottom-center
        triangle = QPainterPath()
        triangle.moveTo(2, 4)  # Top-left
        triangle.lineTo(10, 4)  # Top-right
        triangle.lineTo(6, 10)  # Bottom-center
        triangle.closeSubpath()
        
        painter.drawPath(triangle)
        painter.end()
        return QIcon(pixmap)
    
    def _create_checkbox_icon(self):
        """Create a modern checkbox icon for the toolbar button."""
        theme = self._theme_manager.get_theme()
        # Use button_text color to match theme
        button_text = theme.get("button_text", theme.get("text_primary", "#ffffff"))
        text_color = QColor(button_text)
        
        pixmap = QPixmap(18, 18)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw modern unchecked checkbox (square with rounded corners)
        # Use button_text color to match theme
        checkbox_rect = QRectF(3, 3, 12, 12)
        painter.setPen(QPen(text_color, 1.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(checkbox_rect, 3, 3)
        
        painter.end()
        return QIcon(pixmap)
    
    def _insert_checkbox(self):
        """Insert a checkbox at the current cursor position."""
        text_edit = self._get_current_text_edit()
        if not text_edit or not isinstance(text_edit, CheckableTextEdit):
            return
        
        text_edit.insert_checkbox(checked=False)
    
    def _apply_toolbar_theme(self):
        """Apply theme styling to the formatting toolbar."""
        theme = self._theme_manager.get_theme()
        
        def hex_to_rgba(hex_color, alpha=255):
            color = QColor(hex_color)
            return f"rgba({color.red()}, {color.green()}, {color.blue()}, {alpha})"
        
        bg_color = theme["window_bg"]
        bg_opacity = theme.get("window_bg_opacity", 240)
        border_color = theme["border_color"]
        button_bg = theme.get("button_bg", bg_color)
        button_hover = theme.get("button_hover", button_bg)
        button_text = theme.get("button_text", theme["text_primary"])
        accent = theme["accent_color"]
        
        toolbar_style = f"""
            QToolButton {{
                background-color: {hex_to_rgba(button_bg, 200)};
                color: {button_text};
                border: 1px solid {hex_to_rgba(border_color, 150)};
                border-radius: 3px;
                padding: 2px 6px;
                min-width: 22px;
                max-width: 22px;
                min-height: 20px;
                max-height: 20px;
            }}
            QToolButton:hover {{
                background-color: {hex_to_rgba(button_hover, 220)};
                border: 1px solid {hex_to_rgba(accent, 200)};
            }}
            QToolButton:checked {{
                background-color: {hex_to_rgba(accent, 200)};
                color: white;
            }}
            QToolButton::menu-indicator {{
                image: none;
                width: 0px;
                height: 0px;
            }}
            QToolButton#numbered_list_btn {{
                font-weight: bold;
            }}
            QComboBox {{
                background-color: {hex_to_rgba(button_bg, 200)};
                color: {button_text};
                border: 1px solid {hex_to_rgba(border_color, 150)};
                border-radius: 3px;
                padding: 2px 4px;
                font-size: 9px;
                min-height: 20px;
                max-height: 20px;
            }}
            QComboBox:hover {{
                background-color: {hex_to_rgba(button_hover, 220)};
                border: 1px solid {hex_to_rgba(accent, 200)};
            }}
        """
        
        self.formatting_toolbar.setStyleSheet(toolbar_style)
        
        # Update all button icons when theme changes
        if hasattr(self, 'bold_btn'):
            bold_icon = self._create_material_icon("format_bold")
            self.bold_btn.setIcon(bold_icon)
        
        if hasattr(self, 'italic_btn'):
            italic_icon = self._create_material_icon("format_italic")
            self.italic_btn.setIcon(italic_icon)
        
        if hasattr(self, 'bullet_list_btn'):
            triangle_icon = self._create_triangle_icon()
            self.bullet_list_btn.setIcon(triangle_icon)
        
        if hasattr(self, 'checkbox_btn'):
            checkbox_icon = self._create_checkbox_icon()
            self.checkbox_btn.setIcon(checkbox_icon)
        
        # Update text color button icon - use theme color if no custom color selected
        if hasattr(self, 'text_color_btn'):
            # Only update to theme color if using default black
            # If user has selected a custom color, keep showing that color
            if not hasattr(self, '_current_text_color') or self._current_text_color == QColor(Qt.GlobalColor.black):
                color_icon = self._create_color_icon()  # Use theme color
                self.text_color_btn.setIcon(color_icon)
            else:
                # Keep the custom selected color
                color_icon = self._create_color_icon(self._current_text_color)
                self.text_color_btn.setIcon(color_icon)
    
    def _get_current_text_edit(self):
        """Get the current active text editor."""
        current_widget = self.tab_widget.currentWidget()
        if current_widget and isinstance(current_widget, (QTextEdit, CheckableTextEdit)):
            return current_widget
        return None
    
    def _toggle_bold(self):
        """Toggle bold formatting."""
        text_edit = self._get_current_text_edit()
        if not text_edit:
            return
        
        cursor = text_edit.textCursor()
        fmt = cursor.charFormat()
        fmt.setFontWeight(QFont.Weight.Bold if fmt.fontWeight() != QFont.Weight.Bold else QFont.Weight.Normal)
        cursor.mergeCharFormat(fmt)
        text_edit.setTextCursor(cursor)
        self._update_toolbar_state()
    
    def _toggle_italic(self):
        """Toggle italic formatting."""
        text_edit = self._get_current_text_edit()
        if not text_edit:
            return
        
        cursor = text_edit.textCursor()
        fmt = cursor.charFormat()
        fmt.setFontItalic(not fmt.fontItalic())
        cursor.mergeCharFormat(fmt)
        text_edit.setTextCursor(cursor)
        self._update_toolbar_state()
    
    def _choose_text_color(self):
        """Open color dialog to choose text color."""
        text_edit = self._get_current_text_edit()
        if not text_edit:
            return
        
        color = QColorDialog.getColor(self._current_text_color, self, "Choose Text Color")
        if color.isValid():
            self._current_text_color = color
            color_icon = self._create_color_icon(color)
            self.text_color_btn.setIcon(color_icon)
            
            cursor = text_edit.textCursor()
            fmt = cursor.charFormat()
            fmt.setForeground(color)
            cursor.mergeCharFormat(fmt)
            text_edit.setTextCursor(cursor)
            self._update_toolbar_state()
    
    def _update_font_combo_display(self):
        """Update the font combo box to display selected font in its own font."""
        if hasattr(self, 'font_family_combo'):
            current_font_name = self.font_family_combo.currentText()
            if current_font_name:
                font = QFont(current_font_name, 9)
                self.font_family_combo.setFont(font)
    
    def _change_font_family(self, family):
        """Change font family for selected text or new text."""
        text_edit = self._get_current_text_edit()
        if not text_edit:
            return
        
        cursor = text_edit.textCursor()
        fmt = cursor.charFormat()
        font = fmt.font()
        font.setFamily(family)
        fmt.setFont(font)
        cursor.mergeCharFormat(fmt)
        text_edit.setTextCursor(cursor)
        self._update_font_combo_display()
    
    def _change_font_size(self, size_text):
        """Change font size for selected text or new text."""
        text_edit = self._get_current_text_edit()
        if not text_edit:
            return
        
        try:
            size = int(size_text)
            if size < 1 or size > 1000:
                return
        except ValueError:
            return
        
        cursor = text_edit.textCursor()
        fmt = cursor.charFormat()
        font = fmt.font()
        font.setPointSize(size)
        fmt.setFont(font)
        cursor.mergeCharFormat(fmt)
        text_edit.setTextCursor(cursor)
    
    def _insert_bullet(self, bullet_char):
        """Insert a bullet point at the current cursor position."""
        text_edit = self._get_current_text_edit()
        if not text_edit:
            return
        
        cursor = text_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
        cursor.insertText(f"{bullet_char} ")
        text_edit.setTextCursor(cursor)
    
    def _insert_numbered_list(self):
        """Insert a numbered list item at the current cursor position."""
        text_edit = self._get_current_text_edit()
        if not text_edit:
            return
        
        cursor = text_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
        cursor.insertText("1. ")
        text_edit.setTextCursor(cursor)
    
    def _update_toolbar_state(self):
        """Update toolbar button states based on current cursor position/selection."""
        text_edit = self._get_current_text_edit()
        if not text_edit:
            if hasattr(self, 'bold_btn'):
                self.bold_btn.setChecked(False)
                self.italic_btn.setChecked(False)
            return
        
        cursor = text_edit.textCursor()
        fmt = cursor.charFormat()
        
        # Update button states
        self.bold_btn.setChecked(fmt.fontWeight() == QFont.Weight.Bold)
        self.italic_btn.setChecked(fmt.fontItalic())
        
        # Update color if set
        if fmt.hasProperty(QTextFormat.Property.ForegroundBrush):
            self._current_text_color = fmt.foreground().color()
        
        # Update font family and size combos
        current_font = fmt.font()
        font_family = current_font.family()
        font_size = current_font.pointSize()
        
        if hasattr(self, 'font_family_combo'):
            self.font_family_combo.blockSignals(True)
            index = self.font_family_combo.findText(font_family)
            if index >= 0:
                self.font_family_combo.setCurrentIndex(index)
            self.font_family_combo.blockSignals(False)
        
        if hasattr(self, 'font_size_combo'):
            self.font_size_combo.blockSignals(True)
            size_text = str(font_size)
            index = self.font_size_combo.findText(size_text)
            if index >= 0:
                self.font_size_combo.setCurrentIndex(index)
            else:
                self.font_size_combo.setCurrentText(size_text)
            self.font_size_combo.blockSignals(False)
    
    def _create_text_editor(self):
        """Create a new text editor widget."""
        text_edit = CheckableTextEdit()
        text_edit.setFont(QFont("Segoe UI", 11))
        text_edit.setPlaceholderText("Start typing your notes...")
        text_edit.setAcceptRichText(True)  # Enable rich text formatting
        
        # Connect text change signal
        text_edit.textChanged.connect(self._on_text_changed)
        
        # Connect cursor position change to update toolbar state
        text_edit.cursorPositionChanged.connect(lambda: self._update_toolbar_state())
        text_edit.selectionChanged.connect(lambda: self._update_toolbar_state())
        
        # Install event filter for automatic numbering
        text_edit.installEventFilter(self)
        
        return text_edit
    
    def _add_new_tab(self):
        """Add a new tab with a text editor and Windows 11 style animation."""
        text_edit = self._create_text_editor()
        
        # Find the next available "Note X" name
        tab_name = self._get_next_available_tab_name()
        
        # Insert new tab before the + tab (if it exists)
        if self._plus_tab_index >= 0:
            # Remove the + tab temporarily
            plus_widget = self.tab_widget.widget(self._plus_tab_index)
            self.tab_widget.removeTab(self._plus_tab_index)
            
            # Add the new note tab
            new_index = self.tab_widget.addTab(text_edit, tab_name)
            
            # Re-add the + tab at the end
            self._plus_tab_index = self.tab_widget.addTab(plus_widget, "+")
            
            # Make sure + tab has no close button
            self.tab_widget.tabBar().setTabButton(
                self._plus_tab_index,
                QTabBar.ButtonPosition.RightSide,
                None
            )
        else:
            # First tab - no + tab exists yet
            new_index = self.tab_widget.addTab(text_edit, tab_name)
        
        # Create custom close button
        close_btn = self._create_close_button()
        close_btn.clicked.connect(lambda checked=False, idx=new_index: self._close_tab_by_button(idx))
        
        self.tab_widget.tabBar().setTabButton(
            new_index,
            QTabBar.ButtonPosition.RightSide,
            close_btn
        )
        
        # Switch to new tab
        self.tab_widget.setCurrentIndex(new_index)
        
        # Create opacity effect for smooth fade animation
        opacity_effect = QGraphicsOpacityEffect(text_edit)
        opacity_effect.setOpacity(0.0)
        text_edit.setGraphicsEffect(opacity_effect)
        
        # Animate: fade in with bounce easing (350ms)
        fade_animation = QPropertyAnimation(opacity_effect, b"opacity")
        fade_animation.setDuration(350)
        fade_animation.setStartValue(0.0)
        fade_animation.setEndValue(1.0)
        fade_animation.setEasingCurve(QEasingCurve.Type.OutBack)  # Bounce effect
        
        # Clean up after animation
        def cleanup():
            text_edit.setGraphicsEffect(None)  # Remove effect for better performance
        
        fade_animation.finished.connect(cleanup)
        fade_animation.start()
        
        # Store animation to prevent garbage collection
        self._last_animation = fade_animation
        self._last_opacity_effect = opacity_effect
    
    def _get_next_available_tab_name(self):
        """Find the next available 'Note X' name that doesn't exist."""
        # Collect all existing tab names (excluding + tab)
        existing_names = []
        for i in range(self.tab_widget.count()):
            if self._plus_tab_index >= 0 and i == self._plus_tab_index:
                continue
            tab_name = self.tab_widget.tabText(i)
            # Only collect names, not empty strings
            if tab_name and tab_name != "+":
                existing_names.append(tab_name)
        
        # Try Note 1, Note 2, Note 3, etc. until we find one that doesn't exist
        counter = 1
        while counter < 1000:  # Safety limit to prevent infinite loop
            candidate_name = f"Note {counter}"
            if candidate_name not in existing_names:
                return candidate_name
            counter += 1
        
        # Fallback (should never reach here)
        return f"Note {len(existing_names) + 1}"
    
    def _create_close_button(self):
        """Create a custom close button for tabs."""
        close_btn = QPushButton("×")
        close_btn.setFixedSize(18, 18)
        
        is_dark = ThemeManager.is_dark_mode()
        if is_dark:
            close_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #bdc3c7;
                    border: none;
                    font-size: 16px;
                    font-weight: bold;
                    padding: 0px;
                    margin: 0px;
                }
                QPushButton:hover {
                    background-color: #e74c3c;
                    color: white;
                    border-radius: 3px;
                }
            """)
        else:
            close_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #7f8c8d;
                    border: none;
                    font-size: 16px;
                    font-weight: bold;
                    padding: 0px;
                    margin: 0px;
                }
                QPushButton:hover {
                    background-color: #e74c3c;
                    color: white;
                    border-radius: 3px;
                }
            """)
        return close_btn
    
    def _close_tab_by_button(self, index):
        """Close tab when close button is clicked."""
        # Get current index because tabs might have shifted
        for i in range(self.tab_widget.count()):
            btn = self.tab_widget.tabBar().tabButton(i, QTabBar.ButtonPosition.RightSide)
            if btn == self.sender():
                self._close_tab(i)
                return
    
    def _close_tab(self, index):
        """Close a tab with confirmation dialog."""
        # Don't allow closing the + tab
        if self._plus_tab_index >= 0 and index == self._plus_tab_index:
            return
        
        # Don't allow closing the last tab (excluding + tab)
        real_tab_count = self.tab_widget.count() - (1 if self._plus_tab_index >= 0 else 0)
        if real_tab_count <= 1:
            QMessageBox.warning(
                self,
                "Cannot Close Tab",
                "You must have at least one tab open.",
                QMessageBox.StandardButton.Ok
            )
            return
        
        # Get the text editor for this tab
        text_edit = self.tab_widget.widget(index)
        
        # Check if tab has content
        if text_edit and isinstance(text_edit, QTextEdit) and text_edit.toPlainText().strip():
            # Show confirmation dialog
            reply = QMessageBox.question(
                self,
                "Close Tab",
                f"Are you sure you want to close '{self.tab_widget.tabText(index)}'?\n\nThis will delete all content in this tab.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.No:
                return
        
        # Store the current tab index before removal
        current_index = self.tab_widget.currentIndex()
        
        # Animate tab close (shrink + fade out, 300ms)
        if text_edit and isinstance(text_edit, QTextEdit):
            # Create opacity effect for fade animation
            opacity_effect = QGraphicsOpacityEffect(text_edit)
            opacity_effect.setOpacity(1.0)
            text_edit.setGraphicsEffect(opacity_effect)
            
            # Fade out animation
            fade_animation = QPropertyAnimation(opacity_effect, b"opacity")
            fade_animation.setDuration(300)
            fade_animation.setStartValue(1.0)
            fade_animation.setEndValue(0.0)
            fade_animation.setEasingCurve(QEasingCurve.Type.InCubic)  # Accelerate out
            
            # Remove tab after animation
            def remove_tab():
                text_edit.setGraphicsEffect(None)  # Clean up
                self.tab_widget.removeTab(index)
                # Update plus tab index - find it again
                for i in range(self.tab_widget.count()):
                    if self.tab_widget.tabText(i) == "+":
                        self._plus_tab_index = i
                        break
                
                # Switch to a valid tab if we deleted the current one
                if current_index == index and self.tab_widget.count() > 1:
                    # Go to previous tab or first tab
                    new_current = max(0, min(index - 1, self.tab_widget.count() - 2))
                    self.tab_widget.setCurrentIndex(new_current)
                
                self._on_text_changed()
            
            fade_animation.finished.connect(remove_tab)
            fade_animation.start()
            
            # Store to prevent garbage collection
            self._last_animation = fade_animation
            self._last_opacity_effect = opacity_effect
        else:
            # If no animation needed, remove directly
            self.tab_widget.removeTab(index)
            # Update plus tab index
            for i in range(self.tab_widget.count()):
                if self.tab_widget.tabText(i) == "+":
                    self._plus_tab_index = i
                    break
            self._on_text_changed()
    
    def _add_plus_tab(self):
        """Add a permanent '+' tab at the end."""
        # Create an empty widget for the + tab
        plus_widget = QWidget()
        plus_index = self.tab_widget.addTab(plus_widget, "+")
        
        # Disable close button for the + tab
        self.tab_widget.tabBar().setTabButton(
            plus_index,
            QTabBar.ButtonPosition.RightSide,
            None
        )
        
        # Store the plus tab index
        self._plus_tab_index = plus_index
    
    def _show_tab_context_menu(self, position):
        """Show context menu when right-clicking on a tab."""
        # Get the tab index at the click position
        tab_index = self.tab_widget.tabBar().tabAt(position)
        
        # Don't show menu for the + tab or invalid index
        if tab_index < 0 or (self._plus_tab_index >= 0 and tab_index == self._plus_tab_index):
            return
        
        # Create context menu
        menu = QMenu(self)
        
        # Add "Rename" action
        rename_action = menu.addAction("Rename")
        rename_action.triggered.connect(lambda: self._rename_tab(tab_index))
        
        # Show the menu at the cursor position
        menu.exec(self.tab_widget.tabBar().mapToGlobal(position))
    
    def _rename_tab(self, index):
        """Rename a tab."""
        if index < 0 or index >= self.tab_widget.count():
            return
        
        # Don't allow renaming the + tab
        if self._plus_tab_index >= 0 and index == self._plus_tab_index:
            return
        
        # Get current tab name
        current_name = self.tab_widget.tabText(index)
        
        # Show input dialog
        new_name, ok = QInputDialog.getText(
            self,
            "Rename Tab",
            "Enter new name:",
            text=current_name
        )
        
        # If user clicked OK and entered a non-empty name
        if ok and new_name.strip():
            self.tab_widget.setTabText(index, new_name.strip())
            self._on_text_changed()  # Save the change
    
    def _on_tab_moved(self, from_index, to_index):
        """Handle tab being moved/dragged."""
        # Update the plus tab index after a tab is moved
        # Find which tab is the + tab
        for i in range(self.tab_widget.count()):
            if self.tab_widget.tabText(i) == "+":
                widget = self.tab_widget.widget(i)
                if widget and not isinstance(widget, QTextEdit):
                    self._plus_tab_index = i
                    break
        
        # If + tab is not at the end, move it there
        if self._plus_tab_index >= 0 and self._plus_tab_index != self.tab_widget.count() - 1:
            # Block signals to prevent recursion
            self.tab_widget.tabBar().blockSignals(True)
            
            # Get the + widget
            plus_widget = self.tab_widget.widget(self._plus_tab_index)
            
            # Remove it
            self.tab_widget.removeTab(self._plus_tab_index)
            
            # Add it back at the end
            self._plus_tab_index = self.tab_widget.addTab(plus_widget, "+")
            
            # Make sure + tab has no close button
            self.tab_widget.tabBar().setTabButton(
                self._plus_tab_index,
                QTabBar.ButtonPosition.RightSide,
                None
            )
            
            # Unblock signals
            self.tab_widget.tabBar().blockSignals(False)
    
    def _on_tab_changed(self, index):
        """Handle tab change with smooth crossfade animation."""
        # Check if user clicked on the + tab
        if self._plus_tab_index >= 0 and index == self._plus_tab_index:
            # Block signals temporarily
            self.tab_widget.blockSignals(True)
            
            # Switch back to the previous tab
            if self.tab_widget.count() > 1:
                # Go to the tab before the + tab
                self.tab_widget.setCurrentIndex(self._plus_tab_index - 1)
            
            # Unblock signals
            self.tab_widget.blockSignals(False)
            
            # Add new tab
            self._add_new_tab()
        elif index >= 0:
            # Animate tab content fade in (250ms)
            current_widget = self.tab_widget.widget(index)
            if current_widget and isinstance(current_widget, QTextEdit):
                # Create opacity effect
                opacity_effect = QGraphicsOpacityEffect(current_widget)
                opacity_effect.setOpacity(0.0)
                current_widget.setGraphicsEffect(opacity_effect)
                
                # Fade in animation
                fade_animation = QPropertyAnimation(opacity_effect, b"opacity")
                fade_animation.setDuration(250)
                fade_animation.setStartValue(0.0)
                fade_animation.setEndValue(1.0)
                fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
                
                # Clean up after animation
                def cleanup():
                    current_widget.setGraphicsEffect(None)
                
                fade_animation.finished.connect(cleanup)
                fade_animation.start()
                
                # Store to prevent garbage collection
                self._tab_switch_animation = fade_animation
                self._tab_switch_effect = opacity_effect
            
            self._on_text_changed()
    
    def _on_text_changed(self):
        """Handle text change with debouncing for auto-save."""
        content = self.get_all_content()
        self.content_changed.emit(content)
        
        # Debounce save operation (save after 1 second of no typing)
        self._save_timer.stop()
        self._save_timer.start(1000)
    
    def _on_save_timeout(self):
        """Called when save timer expires."""
        # This will be handled by the main application
        pass
    
    def eventFilter(self, obj, event):
        """Event filter for automatic numbering."""
        if isinstance(obj, QTextEdit) and event.type() == QEvent.Type.KeyPress:
            key_event = event
            
            # Handle Enter key press
            if key_event.key() == Qt.Key.Key_Return or key_event.key() == Qt.Key.Key_Enter:
                return self._handle_enter_key(obj)
        
        return super().eventFilter(obj, event)
    
    def _handle_enter_key(self, text_edit):
        """Handle Enter key press for automatic numbering."""
        cursor = text_edit.textCursor()
        
        # Get current line text
        cursor.select(QTextCursor.SelectionType.LineUnderCursor)
        current_line = cursor.selectedText().strip()
        
        # Move cursor to end of line before processing
        cursor.clearSelection()
        cursor.movePosition(QTextCursor.MoveOperation.EndOfLine)
        text_edit.setTextCursor(cursor)
        
        # Check if current line matches numbered list pattern (e.g., "1. ", "2. ", etc.)
        number_pattern = re.match(r'^(\d+)\.\s*(.*)$', current_line)
        
        if number_pattern:
            number = int(number_pattern.group(1))
            content = number_pattern.group(2).strip()
            
            # If the line has no content (just the number), remove the number
            if not content:
                # Remove the number from current line
                cursor.select(QTextCursor.SelectionType.LineUnderCursor)
                cursor.removeSelectedText()
                cursor.deletePreviousChar()  # Remove the newline if exists
                text_edit.setTextCursor(cursor)
                return True  # Event handled, don't process default Enter
            else:
                # Insert newline and next number
                cursor.insertText(f"\n{number + 1}. ")
                text_edit.setTextCursor(cursor)
                return True  # Event handled
        
        # Check for bullet points (-, *, •)
        bullet_pattern = re.match(r'^([-*•])\s*(.*)$', current_line)
        
        if bullet_pattern:
            bullet = bullet_pattern.group(1)
            content = bullet_pattern.group(2).strip()
            
            # If the line has no content (just the bullet), remove the bullet
            if not content:
                # Remove the bullet from current line
                cursor.select(QTextCursor.SelectionType.LineUnderCursor)
                cursor.removeSelectedText()
                cursor.deletePreviousChar()  # Remove the newline if exists
                text_edit.setTextCursor(cursor)
                return True  # Event handled
            else:
                # Insert newline and same bullet
                cursor.insertText(f"\n{bullet} ")
                text_edit.setTextCursor(cursor)
                return True  # Event handled
        
        # Default behavior for normal lines
        return False
    
    def get_content(self) -> str:
        """Get content from current tab (for compatibility)."""
        current_widget = self.tab_widget.currentWidget()
        if current_widget and isinstance(current_widget, QTextEdit):
            return current_widget.toHtml()
        return ""
    
    def get_all_content(self) -> str:
        """Get content from all tabs as a serialized string."""
        import json
        
        tabs_data = []
        for i in range(self.tab_widget.count()):
            # Skip the + tab
            if self._plus_tab_index >= 0 and i == self._plus_tab_index:
                continue
                
            text_edit = self.tab_widget.widget(i)
            tab_name = self.tab_widget.tabText(i)
            
            if text_edit and isinstance(text_edit, QTextEdit):
                tab_data = {
                    "name": tab_name,
                    "content": text_edit.toHtml(),
                    "format": "html"
                }
                
                # Save checkbox states if it's a CheckableTextEdit
                if isinstance(text_edit, CheckableTextEdit):
                    tab_data["checkbox_states"] = text_edit.get_checkbox_states()
                
                tabs_data.append(tab_data)
        
        return json.dumps(tabs_data)
    
    def set_content(self, content: str):
        """Set content from serialized string (restores all tabs)."""
        import json
        
        # Block signals during loading
        self.tab_widget.blockSignals(True)
        
        try:
            tabs_data = json.loads(content)
            
            # Clear existing tabs
            while self.tab_widget.count() > 0:
                self.tab_widget.removeTab(0)
            
            # Reset plus tab index
            self._plus_tab_index = -1
            
            # Restore tabs
            if tabs_data:
                for tab_data in tabs_data:
                    text_edit = self._create_text_editor()
                    text_edit.blockSignals(True)
                    content = tab_data.get("content", "")
                    if tab_data.get("format") == "html" or (content and content.strip().startswith("<")):
                        text_edit.setHtml(content)
                    else:
                        text_edit.setPlainText(content)
                    
                    # Restore checkbox states if available
                    if isinstance(text_edit, CheckableTextEdit) and "checkbox_states" in tab_data:
                        text_edit.set_checkbox_states(tab_data["checkbox_states"])
                    
                    text_edit.blockSignals(False)
                    
                    index = self.tab_widget.addTab(text_edit, tab_data.get("name", "Note"))
                    
                    # Add close button
                    close_btn = self._create_close_button()
                    close_btn.clicked.connect(lambda checked=False, idx=index: self._close_tab_by_button(idx))
                    
                    self.tab_widget.tabBar().setTabButton(
                        index,
                        QTabBar.ButtonPosition.RightSide,
                        close_btn
                    )
                
                # Add the + tab at the end
                self._add_plus_tab()
            else:
                # If no tabs, create a default one
                self._add_new_tab()
                self._add_plus_tab()
                
        except (json.JSONDecodeError, TypeError):
            # If content is not JSON (old format), treat as single tab
            while self.tab_widget.count() > 0:
                self.tab_widget.removeTab(0)
            
            self._plus_tab_index = -1
            
            text_edit = self._create_text_editor()
            text_edit.blockSignals(True)
            if content and content.strip().startswith("<"):
                text_edit.setHtml(content)
            else:
                text_edit.setPlainText(content)
            text_edit.blockSignals(False)
            
            index = self.tab_widget.addTab(text_edit, "Note 1")
            
            close_btn = self._create_close_button()
            close_btn.clicked.connect(lambda checked=False, idx=index: self._close_tab_by_button(idx))
            
            self.tab_widget.tabBar().setTabButton(
                0,
                QTabBar.ButtonPosition.RightSide,
                close_btn
            )
            
            # Add the + tab
            self._add_plus_tab()
        
        finally:
            self.tab_widget.blockSignals(False)
    
    def paintEvent(self, event):
        """Paint the window with rounded corners and blur effect."""
        theme = self._theme_manager.get_theme()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Get theme values
        bg_color = QColor(theme["window_bg"])
        bg_opacity = theme.get("window_bg_opacity", 240)
        bg_color.setAlpha(bg_opacity)
        radius = float(theme.get("border_radius", 12))
        shadow_intensity = theme.get("shadow_intensity", 3)
        
        # Create rounded rectangle path
        path = QPainterPath()
        rect = QRectF(self.rect())
        
        # Draw shadow if enabled
        if shadow_intensity > 0:
            shadow_path = QPainterPath()
            shadow_path.addRoundedRect(
                rect.adjusted(shadow_intensity, shadow_intensity, -shadow_intensity, -shadow_intensity),
                radius, radius
            )
            shadow_color = QColor(0, 0, 0, 40 * shadow_intensity)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(shadow_color))
            painter.drawPath(shadow_path)
        
        # Draw main background
        path.addRoundedRect(rect, radius, radius)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(bg_color))
        painter.drawPath(path)
        
        # Draw border
        window_border_color = theme.get("window_border_color", theme.get("border_color", "#646464"))
        border_color = QColor(window_border_color)
        border_color.setAlpha(150)
        painter.setPen(QPen(border_color, 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)