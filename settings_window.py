"""
Settings window for theme customization with live preview.
"""
import json
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QCheckBox,
    QSlider, QSpinBox, QComboBox, QGroupBox, QScrollArea, QFileDialog,
    QMessageBox, QFrame, QSizePolicy, QLineEdit, QGridLayout
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QBrush, QPen
from theme_manager import ThemeManager
import config


class ColorPickerButton(QPushButton):
    """Button that shows a color and opens a color picker dialog."""
    
    color_changed = pyqtSignal(str)  # Emits hex color string
    
    def __init__(self, initial_color: str = "#000000", parent=None):
        super().__init__(parent)
        self._color = QColor(initial_color)
        self._setup_ui()
        self.clicked.connect(self._show_color_dialog)
    
    def _setup_ui(self):
        """Setup the button appearance."""
        self.setFixedSize(60, 30)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_button_color()
    
    def _update_button_color(self):
        """Update button background to show current color."""
        style = f"""
            QPushButton {{
                background-color: {self._color.name()};
                border: 2px solid #888888;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                border: 2px solid #0078d7;
            }}
        """
        self.setStyleSheet(style)
    
    def _show_color_dialog(self):
        """Show color picker dialog."""
        from PyQt6.QtWidgets import QColorDialog
        color = QColorDialog.getColor(
            self._color,
            self,
            "Select Color",
            QColorDialog.ColorDialogOption.ShowAlphaChannel
        )
        if color.isValid():
            self.set_color(color.name(QColor.NameFormat.HexArgb))
    
    def set_color(self, hex_color: str):
        """Set the color from hex string."""
        self._color = QColor(hex_color)
        self._update_button_color()
        self.color_changed.emit(hex_color)
    
    def get_color(self) -> str:
        """Get current color as hex string."""
        return self._color.name(QColor.NameFormat.HexArgb)


class SettingsWindow(QWidget):
    """Settings window for theme customization."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._theme_manager = ThemeManager.get_instance()
        self._color_pickers: dict = {}
        self._updating = False
        
        self._setup_window()
        self._setup_ui()
        self._load_current_theme()
        
        # Connect theme changes
        self._theme_manager.theme_changed.connect(self._on_theme_changed)
        self._theme_manager.register_listener(self._apply_theme_to_ui)
    
    def _setup_window(self):
        """Setup window properties."""
        self.setWindowTitle("Settings - Notes Overlay")
        self.setMinimumSize(700, 800)
        self.resize(750, 900)
        
        # Apply current theme to window
        self._apply_theme_to_ui()
    
    def _setup_ui(self):
        """Setup the UI layout."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Scroll area for all settings
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(20)
        
        # Appearance Section
        appearance_group = self._create_appearance_section()
        content_layout.addWidget(appearance_group)
        
        # Colors Section
        colors_group = self._create_colors_section()
        content_layout.addWidget(colors_group)
        
        # Effects Section
        effects_group = self._create_effects_section()
        content_layout.addWidget(effects_group)
        
        # Typography Section
        typography_group = self._create_typography_section()
        content_layout.addWidget(typography_group)
        
        # Advanced Section
        advanced_group = self._create_advanced_section()
        content_layout.addWidget(advanced_group)
        
        content_layout.addStretch()
        
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)
        
        # Close button at bottom
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        close_btn.setMinimumWidth(100)
        button_layout.addWidget(close_btn)
        main_layout.addLayout(button_layout)
    
    def _create_appearance_section(self) -> QGroupBox:
        """Create appearance settings section."""
        group = QGroupBox("Appearance")
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        # Follow System Theme checkbox
        self.follow_system_checkbox = QCheckBox("Follow System Theme")
        self.follow_system_checkbox.setChecked(self._theme_manager._follow_system_theme)
        self.follow_system_checkbox.toggled.connect(self._on_follow_system_toggled)
        layout.addWidget(self.follow_system_checkbox)
        
        # Quick Theme Switcher
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel("Theme:"))
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light", "Dark", "Custom"])
        self.theme_combo.currentTextChanged.connect(self._on_theme_changed_combo)
        theme_layout.addWidget(self.theme_combo)
        theme_layout.addStretch()
        
        layout.addLayout(theme_layout)
        
        group.setLayout(layout)
        return group
    
    def _create_colors_section(self) -> QGroupBox:
        """Create colors customization section."""
        group = QGroupBox("Colors")
        layout = QGridLayout()
        layout.setSpacing(10)
        
        # Window Colors
        row = 0
        layout.addWidget(QLabel("Window Background:"), row, 0)
        picker = ColorPickerButton()
        picker.color_changed.connect(lambda c: self._on_color_changed("window_bg", c))
        self._color_pickers["window_bg"] = picker
        layout.addWidget(picker, row, 1)
        
        row += 1
        layout.addWidget(QLabel("Text (Primary):"), row, 0)
        picker = ColorPickerButton()
        picker.color_changed.connect(lambda c: self._on_color_changed("text_primary", c))
        self._color_pickers["text_primary"] = picker
        layout.addWidget(picker, row, 1)
        
        row += 1
        layout.addWidget(QLabel("Text (Secondary):"), row, 0)
        picker = ColorPickerButton()
        picker.color_changed.connect(lambda c: self._on_color_changed("text_secondary", c))
        self._color_pickers["text_secondary"] = picker
        layout.addWidget(picker, row, 1)
        
        row += 1
        layout.addWidget(QLabel("Border Color:"), row, 0)
        picker = ColorPickerButton()
        picker.color_changed.connect(lambda c: self._on_color_changed("border_color", c))
        self._color_pickers["border_color"] = picker
        layout.addWidget(picker, row, 1)
        
        row += 1
        layout.addWidget(QLabel("Window Border:"), row, 0)
        picker = ColorPickerButton()
        picker.color_changed.connect(lambda c: self._on_color_changed("window_border_color", c))
        self._color_pickers["window_border_color"] = picker
        layout.addWidget(picker, row, 1)
        
        row += 1
        layout.addWidget(QLabel("Accent Color:"), row, 0)
        picker = ColorPickerButton()
        picker.color_changed.connect(lambda c: self._on_color_changed("accent_color", c))
        self._color_pickers["accent_color"] = picker
        layout.addWidget(picker, row, 1)
        
        row += 1
        layout.addWidget(QLabel("Title Bar:"), row, 0)
        picker = ColorPickerButton()
        picker.color_changed.connect(lambda c: self._on_color_changed("title_bar_color", c))
        self._color_pickers["title_bar_color"] = picker
        layout.addWidget(picker, row, 1)
        
        # Tab Colors
        row += 1
        layout.addWidget(QLabel("Tab (Active):"), row, 0)
        picker = ColorPickerButton()
        picker.color_changed.connect(lambda c: self._on_color_changed("tab_bg_active", c))
        self._color_pickers["tab_bg_active"] = picker
        layout.addWidget(picker, row, 1)
        
        row += 1
        layout.addWidget(QLabel("Tab (Inactive):"), row, 0)
        picker = ColorPickerButton()
        picker.color_changed.connect(lambda c: self._on_color_changed("tab_bg_inactive", c))
        self._color_pickers["tab_bg_inactive"] = picker
        layout.addWidget(picker, row, 1)
        
        row += 1
        layout.addWidget(QLabel("Tab Text:"), row, 0)
        picker = ColorPickerButton()
        picker.color_changed.connect(lambda c: self._on_color_changed("tab_text_color", c))
        self._color_pickers["tab_text_color"] = picker
        layout.addWidget(picker, row, 1)
        
        row += 1
        layout.addWidget(QLabel("Scrollbar:"), row, 0)
        picker = ColorPickerButton()
        picker.color_changed.connect(lambda c: self._on_color_changed("scrollbar_color", c))
        self._color_pickers["scrollbar_color"] = picker
        layout.addWidget(picker, row, 1)
        
        # Button Colors
        row += 1
        layout.addWidget(QLabel("Button Background:"), row, 0)
        picker = ColorPickerButton()
        picker.color_changed.connect(lambda c: self._on_color_changed("button_bg", c))
        self._color_pickers["button_bg"] = picker
        layout.addWidget(picker, row, 1)
        
        row += 1
        layout.addWidget(QLabel("Button Text:"), row, 0)
        picker = ColorPickerButton()
        picker.color_changed.connect(lambda c: self._on_color_changed("button_text", c))
        self._color_pickers["button_text"] = picker
        layout.addWidget(picker, row, 1)
        
        row += 1
        layout.addWidget(QLabel("Button Hover:"), row, 0)
        picker = ColorPickerButton()
        picker.color_changed.connect(lambda c: self._on_color_changed("button_hover", c))
        self._color_pickers["button_hover"] = picker
        layout.addWidget(picker, row, 1)
        
        row += 1
        layout.addWidget(QLabel("Button Border:"), row, 0)
        picker = ColorPickerButton()
        picker.color_changed.connect(lambda c: self._on_color_changed("button_border", c))
        self._color_pickers["button_border"] = picker
        layout.addWidget(picker, row, 1)
        
        group.setLayout(layout)
        return group
    
    def _create_effects_section(self) -> QGroupBox:
        """Create effects settings section."""
        group = QGroupBox("Window Effects")
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # Window Opacity
        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(QLabel("Window Opacity:"))
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(20, 100)
        self.opacity_slider.setValue(95)
        self.opacity_slider.valueChanged.connect(self._on_opacity_changed)
        opacity_layout.addWidget(self.opacity_slider)
        self.opacity_label = QLabel("95%")
        self.opacity_label.setMinimumWidth(40)
        opacity_layout.addWidget(self.opacity_label)
        layout.addLayout(opacity_layout)
        
        # Window Background Opacity
        bg_opacity_layout = QHBoxLayout()
        bg_opacity_layout.addWidget(QLabel("Background Opacity:"))
        self.bg_opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.bg_opacity_slider.setRange(0, 255)
        self.bg_opacity_slider.setValue(240)
        self.bg_opacity_slider.valueChanged.connect(self._on_bg_opacity_changed)
        bg_opacity_layout.addWidget(self.bg_opacity_slider)
        self.bg_opacity_label = QLabel("240")
        self.bg_opacity_label.setMinimumWidth(40)
        bg_opacity_layout.addWidget(self.bg_opacity_label)
        layout.addLayout(bg_opacity_layout)
        
        # Blur Effect
        blur_layout = QHBoxLayout()
        self.blur_checkbox = QCheckBox("Enable Blur Effect")
        self.blur_checkbox.setChecked(True)
        self.blur_checkbox.toggled.connect(self._on_blur_toggled)
        blur_layout.addWidget(self.blur_checkbox)
        blur_layout.addStretch()
        layout.addLayout(blur_layout)
        
        blur_intensity_layout = QHBoxLayout()
        blur_intensity_layout.addWidget(QLabel("Blur Intensity:"))
        self.blur_slider = QSlider(Qt.Orientation.Horizontal)
        self.blur_slider.setRange(0, 30)
        self.blur_slider.setValue(10)
        self.blur_slider.valueChanged.connect(self._on_blur_intensity_changed)
        blur_intensity_layout.addWidget(self.blur_slider)
        self.blur_label = QLabel("10")
        self.blur_label.setMinimumWidth(40)
        blur_intensity_layout.addWidget(self.blur_label)
        layout.addLayout(blur_intensity_layout)
        
        # Shadow Intensity
        shadow_layout = QHBoxLayout()
        shadow_layout.addWidget(QLabel("Shadow Intensity:"))
        self.shadow_slider = QSlider(Qt.Orientation.Horizontal)
        self.shadow_slider.setRange(0, 10)
        self.shadow_slider.setValue(3)
        self.shadow_slider.valueChanged.connect(self._on_shadow_changed)
        shadow_layout.addWidget(self.shadow_slider)
        self.shadow_label = QLabel("3")
        self.shadow_label.setMinimumWidth(40)
        shadow_layout.addWidget(self.shadow_label)
        layout.addLayout(shadow_layout)
        
        # Border Radius
        radius_layout = QHBoxLayout()
        radius_layout.addWidget(QLabel("Border Radius:"))
        self.radius_slider = QSlider(Qt.Orientation.Horizontal)
        self.radius_slider.setRange(0, 30)
        self.radius_slider.setValue(12)
        self.radius_slider.valueChanged.connect(self._on_radius_changed)
        radius_layout.addWidget(self.radius_slider)
        self.radius_label = QLabel("12")
        self.radius_label.setMinimumWidth(40)
        radius_layout.addWidget(self.radius_label)
        layout.addLayout(radius_layout)
        
        group.setLayout(layout)
        return group
    
    def _create_typography_section(self) -> QGroupBox:
        """Create typography settings section."""
        group = QGroupBox("Typography")
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # Font Family
        font_layout = QHBoxLayout()
        font_layout.addWidget(QLabel("Font Family:"))
        self.font_combo = QComboBox()
        # Add common fonts
        fonts = ["Segoe UI", "Arial", "Calibri", "Consolas", "Courier New", 
                 "Georgia", "Helvetica", "Times New Roman", "Verdana"]
        self.font_combo.addItems(fonts)
        self.font_combo.currentTextChanged.connect(self._on_font_family_changed)
        font_layout.addWidget(self.font_combo)
        font_layout.addStretch()
        layout.addLayout(font_layout)
        
        # Font Size
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("Font Size:"))
        self.font_size_slider = QSlider(Qt.Orientation.Horizontal)
        self.font_size_slider.setRange(8, 20)
        self.font_size_slider.setValue(11)
        self.font_size_slider.valueChanged.connect(self._on_font_size_changed)
        size_layout.addWidget(self.font_size_slider)
        self.font_size_label = QLabel("11")
        self.font_size_label.setMinimumWidth(40)
        size_layout.addWidget(self.font_size_label)
        layout.addLayout(size_layout)
        
        group.setLayout(layout)
        return group
    
    def _create_advanced_section(self) -> QGroupBox:
        """Create advanced settings section."""
        group = QGroupBox("Advanced")
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        # Import/Export buttons
        import_export_layout = QHBoxLayout()
        
        import_btn = QPushButton("Import Theme")
        import_btn.clicked.connect(self._import_theme)
        import_export_layout.addWidget(import_btn)
        
        export_btn = QPushButton("Export Theme")
        export_btn.clicked.connect(self._export_theme)
        import_export_layout.addWidget(export_btn)
        
        import_export_layout.addStretch()
        layout.addLayout(import_export_layout)
        
        # Reset button
        reset_layout = QHBoxLayout()
        reset_btn = QPushButton("Reset to Default")
        reset_btn.clicked.connect(self._reset_theme)
        reset_btn.setStyleSheet("QPushButton { background-color: #d32f2f; color: white; }")
        reset_layout.addWidget(reset_btn)
        reset_layout.addStretch()
        layout.addLayout(reset_layout)
        
        group.setLayout(layout)
        return group
    
    def _load_current_theme(self):
        """Load current theme values into UI."""
        self._updating = True
        theme = self._theme_manager.get_theme()
        
        # Update color pickers
        for key, picker in self._color_pickers.items():
            if key in theme:
                picker.set_color(theme[key])
            elif key == "window_border_color" and "border_color" in theme:
                # Fallback: use border_color if window_border_color doesn't exist
                picker.set_color(theme["border_color"])
        
        # Update sliders and controls
        if "window_opacity" in theme:
            self.opacity_slider.setValue(theme["window_opacity"])
            self.opacity_label.setText(f"{theme['window_opacity']}%")
        
        if "window_bg_opacity" in theme:
            self.bg_opacity_slider.setValue(theme["window_bg_opacity"])
            self.bg_opacity_label.setText(str(theme["window_bg_opacity"]))
        
        if "blur_enabled" in theme:
            self.blur_checkbox.setChecked(theme["blur_enabled"])
        
        if "blur_intensity" in theme:
            self.blur_slider.setValue(theme["blur_intensity"])
            self.blur_label.setText(str(theme["blur_intensity"]))
        
        if "shadow_intensity" in theme:
            self.shadow_slider.setValue(theme["shadow_intensity"])
            self.shadow_label.setText(str(theme["shadow_intensity"]))
        
        if "border_radius" in theme:
            self.radius_slider.setValue(theme["border_radius"])
            self.radius_label.setText(str(theme["border_radius"]))
        
        if "font_family" in theme:
            index = self.font_combo.findText(theme["font_family"])
            if index >= 0:
                self.font_combo.setCurrentIndex(index)
        
        if "font_size" in theme:
            self.font_size_slider.setValue(theme["font_size"])
            self.font_size_label.setText(str(theme["font_size"]))
        
        # Update theme mode combo
        mode = self._theme_manager._current_theme_mode
        if mode == "light":
            self.theme_combo.setCurrentIndex(0)
        elif mode == "dark":
            self.theme_combo.setCurrentIndex(1)
        else:
            self.theme_combo.setCurrentIndex(2)
        
        self._updating = False
    
    def _on_color_changed(self, key: str, color: str):
        """Handle color picker change."""
        if self._updating:
            return
        self._theme_manager.set_theme_property(key, color)
        self._theme_manager.save_theme()
    
    def _on_opacity_changed(self, value: int):
        """Handle window opacity change."""
        if self._updating:
            return
        self.opacity_label.setText(f"{value}%")
        self._theme_manager.set_theme_property("window_opacity", value)
        self._theme_manager.save_theme()
    
    def _on_bg_opacity_changed(self, value: int):
        """Handle background opacity change."""
        if self._updating:
            return
        self.bg_opacity_label.setText(str(value))
        self._theme_manager.set_theme_property("window_bg_opacity", value)
        self._theme_manager.save_theme()
    
    def _on_blur_toggled(self, checked: bool):
        """Handle blur checkbox toggle."""
        if self._updating:
            return
        self._theme_manager.set_theme_property("blur_enabled", checked)
        self._theme_manager.save_theme()
    
    def _on_blur_intensity_changed(self, value: int):
        """Handle blur intensity change."""
        if self._updating:
            return
        self.blur_label.setText(str(value))
        self._theme_manager.set_theme_property("blur_intensity", value)
        self._theme_manager.save_theme()
    
    def _on_shadow_changed(self, value: int):
        """Handle shadow intensity change."""
        if self._updating:
            return
        self.shadow_label.setText(str(value))
        self._theme_manager.set_theme_property("shadow_intensity", value)
        self._theme_manager.save_theme()
    
    def _on_radius_changed(self, value: int):
        """Handle border radius change."""
        if self._updating:
            return
        self.radius_label.setText(str(value))
        self._theme_manager.set_theme_property("border_radius", value)
        self._theme_manager.save_theme()
    
    def _on_font_family_changed(self, font: str):
        """Handle font family change."""
        if self._updating:
            return
        self._theme_manager.set_theme_property("font_family", font)
        self._theme_manager.save_theme()
    
    def _on_font_size_changed(self, value: int):
        """Handle font size change."""
        if self._updating:
            return
        self.font_size_label.setText(str(value))
        self._theme_manager.set_theme_property("font_size", value)
        self._theme_manager.save_theme()
    
    def _on_follow_system_toggled(self, checked: bool):
        """Handle follow system theme toggle."""
        if self._updating:
            return
        self._theme_manager.set_follow_system_theme(checked)
        if checked:
            self._load_current_theme()
    
    def _on_theme_changed_combo(self, text: str):
        """Handle theme combo box change."""
        if self._updating:
            return
        if text == "Light":
            self._theme_manager.set_theme_mode("light")
            self.follow_system_checkbox.setChecked(False)
        elif text == "Dark":
            self._theme_manager.set_theme_mode("dark")
            self.follow_system_checkbox.setChecked(False)
        else:  # Custom
            self._theme_manager.set_theme_mode("custom")
            self.follow_system_checkbox.setChecked(False)
        self._load_current_theme()
    
    def _on_theme_changed(self):
        """Handle external theme change."""
        self._load_current_theme()
    
    def _export_theme(self):
        """Export current theme to file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Theme",
            str(Path.home() / "theme.json"),
            "JSON Files (*.json);;All Files (*)"
        )
        if file_path:
            if self._theme_manager.export_theme(file_path):
                QMessageBox.information(self, "Success", "Theme exported successfully!")
            else:
                QMessageBox.warning(self, "Error", "Failed to export theme.")
    
    def _import_theme(self):
        """Import theme from file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Theme",
            str(Path.home()),
            "JSON Files (*.json);;All Files (*)"
        )
        if file_path:
            if self._theme_manager.import_theme(file_path):
                QMessageBox.information(self, "Success", "Theme imported successfully!")
                self._load_current_theme()
                self.follow_system_checkbox.setChecked(False)
                self.theme_combo.setCurrentIndex(2)  # Set to Custom
            else:
                QMessageBox.warning(self, "Error", "Failed to import theme. File may be invalid.")
    
    def _reset_theme(self):
        """Reset theme to default."""
        reply = QMessageBox.question(
            self,
            "Reset Theme",
            "Are you sure you want to reset to the default theme?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._theme_manager.reset_to_default()
            self._load_current_theme()
    
    def _apply_theme_to_ui(self):
        """Apply current theme to this settings window."""
        theme = self._theme_manager.get_theme()
        is_dark = ThemeManager.is_dark_mode()
        
        bg_color = theme["window_bg"]
        text_color = theme["text_primary"]
        border_color = theme["border_color"]
        
        stylesheet = f"""
            QWidget {{
                background-color: {bg_color};
                color: {text_color};
            }}
            QGroupBox {{
                border: 2px solid {border_color};
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
            QLabel {{
                color: {text_color};
            }}
            QPushButton {{
                background-color: {theme['button_bg']};
                color: {theme['button_text']};
                border: 1px solid {theme['button_border']};
                border-radius: 4px;
                padding: 5px 15px;
            }}
            QPushButton:hover {{
                background-color: {theme['button_hover']};
            }}
            QCheckBox {{
                color: {text_color};
            }}
            QComboBox {{
                background-color: {theme['button_bg']};
                color: {theme['button_text']};
                border: 1px solid {theme['button_border']};
                border-radius: 4px;
                padding: 3px;
            }}
            QSlider::groove:horizontal {{
                border: 1px solid {border_color};
                height: 6px;
                background: {bg_color};
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: {theme['accent_color']};
                border: 1px solid {border_color};
                width: 18px;
                margin: -2px 0;
                border-radius: 9px;
            }}
            QScrollArea {{
                border: none;
                background-color: {bg_color};
            }}
        """
        self.setStyleSheet(stylesheet)
    
    def closeEvent(self, event):
        """Handle window close event."""
        self._theme_manager.unregister_listener(self._apply_theme_to_ui)
        event.accept()

