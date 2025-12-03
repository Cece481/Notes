"""
Configuration settings for the Notes Overlay application.
"""
import os
from pathlib import Path

# Application settings
APP_NAME = "Notes Overlay"
APP_VERSION = "1.0.0"

# Window settings
BUTTON_WIDTH = 30
BUTTON_HEIGHT = 100
BUTTON_TOP_MARGIN = 120  # Distance from top of screen
NOTES_WINDOW_WIDTH = 400
NOTES_WINDOW_HEIGHT = 500
NOTES_WINDOW_MIN_WIDTH = 350
NOTES_WINDOW_MIN_HEIGHT = 400

# Animation settings
ANIMATION_DURATION = 350  # milliseconds
ANIMATION_EASING = "OutCubic"  # QEasingCurve type

# Button appearance
BUTTON_OPACITY = 0.75
BUTTON_HOVER_OPACITY = 0.90
BUTTON_BLUR_RADIUS = 20
BUTTON_SHADOW_OFFSET = 3
BUTTON_SHADOW_BLUR = 8

# Colors (Windows 11 theme)
COLOR_LIGHT_BG = (245, 245, 245, int(255 * BUTTON_OPACITY))
COLOR_DARK_BG = (32, 32, 32, int(255 * BUTTON_OPACITY))
COLOR_LIGHT_TEXT = (0, 0, 0, 255)
COLOR_DARK_TEXT = (255, 255, 255, 255)
COLOR_ACCENT = (0, 120, 215, 255)  # Windows 11 accent blue
COLOR_HOVER_GLOW = (0, 120, 215, 100)

# Data directory
DATA_DIR = Path.home() / ".notes_overlay"
NOTES_FILE = DATA_DIR / "notes.json"

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)

# Fullscreen detection
FULLSCREEN_CHECK_INTERVAL = 500  # milliseconds