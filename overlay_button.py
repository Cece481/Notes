"""
Custom asymmetric button widget with Windows 11 styling.
"""
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QPoint, QRect, QPropertyAnimation, QEasingCurve, pyqtProperty, pyqtSignal
from PyQt6.QtGui import QPainter, QPainterPath, QColor, QPen, QBrush, QFont, QFontMetrics
import config
from theme_manager import ThemeManager


class OverlayButton(QWidget):
    """Signal emitted when button is clicked."""
    clicked = pyqtSignal()
    """
    Custom button widget with asymmetric design:
    - Rounded left side (semi-circle)
    - Flat right side (flush with screen edge)
    - Vertical "NOTES" text
    - Windows 11 acrylic blur effect
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._hover_opacity = config.BUTTON_OPACITY
        self._is_hovered = False
        self._is_pressed = False
        
        # Set widget properties
        self.setFixedSize(config.BUTTON_WIDTH, config.BUTTON_HEIGHT)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        
        # Enable mouse tracking for hover effects
        self.setMouseTracking(True)
        
        # Setup hover animation
        self._hover_animation = QPropertyAnimation(self, b"hoverOpacity")
        self._hover_animation.setDuration(200)
        self._hover_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
    def get_hover_opacity(self) -> float:
        """Get current hover opacity."""
        return self._hover_opacity
    
    def set_hover_opacity(self, opacity: float) -> None:
        """Set hover opacity and trigger repaint."""
        self._hover_opacity = opacity
        self.update()
    
    hoverOpacity = pyqtProperty(float, get_hover_opacity, set_hover_opacity)
    
    def enterEvent(self, event):
        """Handle mouse enter event."""
        self._is_hovered = True
        self._hover_animation.stop()
        self._hover_animation.setStartValue(self._hover_opacity)
        self._hover_animation.setEndValue(config.BUTTON_HOVER_OPACITY)
        self._hover_animation.start()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Handle mouse leave event."""
        self._is_hovered = False
        self._is_pressed = False
        self._hover_animation.stop()
        self._hover_animation.setStartValue(self._hover_opacity)
        self._hover_animation.setEndValue(config.BUTTON_OPACITY)
        self._hover_animation.start()
        super().leaveEvent(event)
    
    def mousePressEvent(self, event):
        """Handle mouse press event."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_pressed = True
            self.update()
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release event."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_pressed = False
            if self.rect().contains(event.pos()):
                self.clicked.emit()
            self.update()
        super().mouseReleaseEvent(event)
    
    def paintEvent(self, event):
        """Custom paint event to draw the asymmetric button (half rounded square/pill shape)."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        width = self.width()
        height = self.height()
        corner_radius = 12  # Radius for rounded corners on left side
        
        # Create the asymmetric path (rounded rectangle with flat right side)
        # This creates a "half pill" shape: rounded left, flat right
        path = QPainterPath()
        
        # Start from top-right corner (flat right side)
        path.moveTo(width, 0)
        
        # Draw straight line down the right side
        path.lineTo(width, height)
        
        # Draw rounded bottom-left corner
        path.arcTo(0, height - corner_radius * 2, corner_radius * 2, corner_radius * 2, 270, 90)
        
        # Draw straight line up the left side
        path.lineTo(0, corner_radius)
        
        # Draw rounded top-left corner
        path.arcTo(0, 0, corner_radius * 2, corner_radius * 2, 180, 90)
        
        # Close path back to top-right
        path.closeSubpath()
        
        # Draw shadow on left side only
        shadow_path = QPainterPath()
        shadow_path.moveTo(width, 0)
        shadow_path.lineTo(width, height)
        shadow_path.arcTo(0, height - corner_radius * 2, corner_radius * 2, corner_radius * 2, 270, 90)
        shadow_path.lineTo(0, corner_radius)
        shadow_path.arcTo(0, 0, corner_radius * 2, corner_radius * 2, 180, 90)
        shadow_path.closeSubpath()
        
        # Draw shadow
        shadow_color = QColor(0, 0, 0, 40)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(shadow_color))
        shadow_offset = config.BUTTON_SHADOW_OFFSET
        painter.translate(-shadow_offset, shadow_offset)
        painter.drawPath(shadow_path)
        painter.translate(shadow_offset, -shadow_offset)
        
        # Determine background color based on system theme
        bg_color_tuple = ThemeManager.get_bg_color()
        bg_color = QColor(*bg_color_tuple)
        bg_color.setAlpha(int(255 * self._hover_opacity))
        
        # Draw main background first
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(bg_color))
        painter.drawPath(path)
        
        # Add glow effect on hover (draw as border/outline)
        if self._is_hovered:
            glow_color = QColor(*config.COLOR_HOVER_GLOW)
            glow_color.setAlpha(int(150 * self._hover_opacity))
            painter.setPen(QPen(glow_color, 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path)
        
        # Draw border (subtle, theme-aware)
        border_color_tuple = ThemeManager.get_border_color(self._hover_opacity)
        border_color = QColor(*border_color_tuple)
        painter.setPen(QPen(border_color, 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)
        
        # Draw vertical "NOTES" text (theme-aware)
        text_color_tuple = ThemeManager.get_text_color()
        text_color = QColor(*text_color_tuple)
        text_color.setAlpha(int(255 * self._hover_opacity))
        painter.setPen(QPen(text_color))
        
        font = QFont("Segoe UI", 10, QFont.Weight.Bold)
        painter.setFont(font)
        
        letters = ["N", "O", "T", "E", "S"]
        letter_height = height / (len(letters) + 1)
        start_y = letter_height
        
        for i, letter in enumerate(letters):
            metrics = QFontMetrics(font)
            letter_width = metrics.horizontalAdvance(letter)
            x = (width - letter_width) / 2
            y = start_y + (i * letter_height)
            painter.drawText(int(x), int(y), letter)

