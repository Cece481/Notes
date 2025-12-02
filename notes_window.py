"""
Notes window with Windows 11 styling, tabs, and auto-save functionality.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
    QPushButton, QTabWidget, QMessageBox, QTabBar, QMenu, QInputDialog
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QRectF, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QPainter, QPainterPath, QColor, QBrush
import config
from theme_manager import ThemeManager


class NotesWindow(QWidget):
    """Notepad window with modern Windows 11 styling and tabs support."""
    
    content_changed = pyqtSignal(str)  # Emitted when content changes
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._save_timer = QTimer()
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._on_save_timeout)
        self._plus_tab_index = -1  # Initialize plus tab index
        
        self._setup_ui()
        self._setup_styling()
    
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
        
        # Create initial tab (the + button will be added as a tab)
        self._add_new_tab()
        self._add_plus_tab()
    
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
        
        # Get theme colors
        is_dark = ThemeManager.is_dark_mode()
        
        if is_dark:
            # Dark mode stylesheet
            tab_style = """
                QTabWidget::pane {
                    border: 1px solid rgba(100, 100, 100, 150);
                    border-radius: 8px;
                    background-color: rgba(32, 32, 32, 240);
                    top: -1px;
                }
                QTabBar::tab {
                    background-color: rgba(50, 50, 50, 200);
                    color: rgba(255, 255, 255, 200);
                    padding: 8px 15px;
                    margin-right: 2px;
                    border-top-left-radius: 6px;
                    border-top-right-radius: 6px;
                    border: 1px solid rgba(80, 80, 80, 150);
                }
                QTabBar::tab:selected {
                    background-color: rgba(32, 32, 32, 240);
                    color: rgb(255, 255, 255);
                    border-bottom: 1px solid rgba(32, 32, 32, 240);
                }
                QTabBar::tab:hover {
                    background-color: rgba(70, 70, 70, 220);
                }
                QTabBar::close-button {
                    image: none;
                    subcontrol-position: right;
                    margin: 2px;
                }
                QTextEdit {
                    background-color: rgba(32, 32, 32, 240);
                    border: none;
                    border-radius: 8px;
                    padding: 10px;
                    color: rgb(255, 255, 255);
                    selection-background-color: rgba(0, 120, 215, 180);
                    selection-color: rgb(255, 255, 255);
                }
                QTextEdit:focus {
                    border: 1px solid rgba(0, 120, 215, 200);
                }
                QScrollBar:vertical {
                    background-color: rgba(40, 40, 40, 200);
                    width: 12px;
                    border: none;
                    border-radius: 6px;
                    margin: 0;
                }
                QScrollBar::handle:vertical {
                    background-color: rgba(100, 100, 100, 200);
                    border-radius: 6px;
                    min-height: 30px;
                }
                QScrollBar::handle:vertical:hover {
                    background-color: rgba(130, 130, 130, 200);
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    height: 0px;
                }
            """
        else:
            # Light mode stylesheet
            tab_style = """
                QTabWidget::pane {
                    border: 1px solid rgba(200, 200, 200, 150);
                    border-radius: 8px;
                    background-color: rgba(245, 245, 245, 240);
                    top: -1px;
                }
                QTabBar::tab {
                    background-color: rgba(230, 230, 230, 200);
                    color: rgba(0, 0, 0, 200);
                    padding: 8px 15px;
                    margin-right: 2px;
                    border-top-left-radius: 6px;
                    border-top-right-radius: 6px;
                    border: 1px solid rgba(200, 200, 200, 150);
                }
                QTabBar::tab:selected {
                    background-color: rgba(245, 245, 245, 240);
                    color: rgb(0, 0, 0);
                    border-bottom: 1px solid rgba(245, 245, 245, 240);
                }
                QTabBar::tab:hover {
                    background-color: rgba(220, 220, 220, 220);
                }
                QTabBar::close-button {
                    image: none;
                    subcontrol-position: right;
                    margin: 2px;
                }
                QTextEdit {
                    background-color: rgba(245, 245, 245, 240);
                    border: none;
                    border-radius: 8px;
                    padding: 10px;
                    color: rgb(0, 0, 0);
                    selection-background-color: rgba(0, 120, 215, 180);
                    selection-color: rgb(255, 255, 255);
                }
                QTextEdit:focus {
                    border: 1px solid rgba(0, 120, 215, 200);
                }
                QScrollBar:vertical {
                    background-color: rgba(240, 240, 240, 200);
                    width: 12px;
                    border: none;
                    border-radius: 6px;
                    margin: 0;
                }
                QScrollBar::handle:vertical {
                    background-color: rgba(180, 180, 180, 200);
                    border-radius: 6px;
                    min-height: 30px;
                }
                QScrollBar::handle:vertical:hover {
                    background-color: rgba(150, 150, 150, 200);
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    height: 0px;
                }
            """
        
        self.tab_widget.setStyleSheet(tab_style)
    
    def _create_text_editor(self):
        """Create a new text editor widget."""
        text_edit = QTextEdit()
        text_edit.setFont(QFont("Segoe UI", 11))
        text_edit.setPlaceholderText("Start typing your notes...")
        text_edit.setAcceptRichText(False)
        
        # Connect text change signal
        text_edit.textChanged.connect(self._on_text_changed)
        
        return text_edit
    
    def _add_new_tab(self):
        """Add a new tab with a text editor and animation."""
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
        
        # Switch to new tab with animation
        self.tab_widget.setCurrentIndex(new_index)
        
        # Animate the new tab (fade in effect on the text editor)
        text_edit.setStyleSheet("QTextEdit { opacity: 0; }")
        animation = QPropertyAnimation(text_edit, b"windowOpacity")
        animation.setDuration(300)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Reset stylesheet after animation
        def reset_style():
            text_edit.setStyleSheet("")
            self._setup_styling()
        
        animation.finished.connect(reset_style)
        animation.start()
        
        # Store animation to prevent garbage collection
        self._last_animation = animation
    
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
        
        # Animate tab close (fade out)
        if text_edit and isinstance(text_edit, QTextEdit):
            animation = QPropertyAnimation(text_edit, b"windowOpacity")
            animation.setDuration(200)
            animation.setStartValue(1.0)
            animation.setEndValue(0.0)
            animation.setEasingCurve(QEasingCurve.Type.InCubic)
            
            # Remove tab after animation
            def remove_tab():
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
            
            animation.finished.connect(remove_tab)
            animation.start()
            
            # Store animation to prevent garbage collection
            self._last_animation = animation
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
        """Handle tab change."""
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
    
    def get_content(self) -> str:
        """Get content from current tab (for compatibility)."""
        current_widget = self.tab_widget.currentWidget()
        if current_widget and isinstance(current_widget, QTextEdit):
            return current_widget.toPlainText()
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
                tabs_data.append({
                    "name": tab_name,
                    "content": text_edit.toPlainText()
                })
        
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
                    text_edit.setPlainText(tab_data.get("content", ""))
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
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Create rounded rectangle path
        path = QPainterPath()
        rect = QRectF(self.rect())
        radius = 12.0
        path.addRoundedRect(rect, radius, radius)
        
        # Draw background with transparency (theme-aware)
        bg_color_tuple = ThemeManager.get_bg_color()
        bg_color = QColor(*bg_color_tuple)
        bg_color.setAlpha(245)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(bg_color))
        painter.drawPath(path)
        
        # Draw subtle border (theme-aware)
        border_color_tuple = ThemeManager.get_border_color(1.0)
        border_color = QColor(*border_color_tuple)
        border_color.setAlpha(200)
        painter.setPen(border_color)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)