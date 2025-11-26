"""
Notes window with Windows 11 styling and auto-save functionality.
"""
from PyQt6.QtWidgets import QWidget, QTextEdit, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont
import config
from theme_manager import ThemeManager


class NotesWindow(QWidget):
    """Notepad window with modern Windows 11 styling."""
    
    content_changed = pyqtSignal(str)  # Emitted when content changes
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._save_timer = QTimer()
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._on_save_timeout)
        
        self._setup_ui()
        self._setup_styling()
    
    def _setup_ui(self):
        """Setup the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(0)
        
        # Text editor
        self.text_edit = QTextEdit(self)
        self.text_edit.setFont(QFont("Segoe UI", 11))
        self.text_edit.setPlaceholderText("Start typing your notes...")
        self.text_edit.textChanged.connect(self._on_text_changed)
        
        layout.addWidget(self.text_edit)
    
    def _setup_styling(self):
        """Apply Windows 11 styling with dark mode support."""
        # Set window properties
        self.setMinimumSize(config.NOTES_WINDOW_MIN_WIDTH, config.NOTES_WINDOW_MIN_HEIGHT)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Get theme colors
        is_dark = ThemeManager.is_dark_mode()
        
        if is_dark:
            # Dark mode stylesheet
            self.setStyleSheet("""
                QTextEdit {
                    background-color: rgba(32, 32, 32, 240);
                    border: 1px solid rgba(100, 100, 100, 150);
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
            """)
        else:
            # Light mode stylesheet
            self.setStyleSheet("""
                QTextEdit {
                    background-color: rgba(245, 245, 245, 240);
                    border: 1px solid rgba(200, 200, 200, 150);
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
            """)
    
    def _on_text_changed(self):
        """Handle text change with debouncing for auto-save."""
        content = self.text_edit.toPlainText()
        self.content_changed.emit(content)
        
        # Debounce save operation (save after 1 second of no typing)
        self._save_timer.stop()
        self._save_timer.start(1000)
    
    def _on_save_timeout(self):
        """Called when save timer expires."""
        # This will be handled by the main application
        pass
    
    def set_content(self, content: str):
        """Set the notes content."""
        # Temporarily disconnect to avoid triggering save
        self.text_edit.blockSignals(True)
        self.text_edit.setPlainText(content)
        self.text_edit.blockSignals(False)
    
    def get_content(self) -> str:
        """Get the current notes content."""
        return self.text_edit.toPlainText()
    
    def paintEvent(self, event):
        """Paint the window with rounded corners and blur effect."""
        from PyQt6.QtGui import QPainter, QPainterPath, QColor, QBrush
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Create rounded rectangle path
        path = QPainterPath()
        from PyQt6.QtCore import QRectF
        rect = QRectF(self.rect())  # Convert QRect to QRectF
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

