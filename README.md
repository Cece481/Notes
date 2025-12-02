# Notes Overlay - Windows 11 Style Desktop Application

A modern, elegant notes application that appears as a persistent overlay on your Windows desktop. Features a unique asymmetric button design that expands into a full notepad with smooth animations.

## Features

- **Persistent Overlay**: Stays on top of all windows (except fullscreen applications)
- **Asymmetric Button Design**: Custom-shaped button with rounded left side and flat right side
- **Smooth Animations**: Windows 11-style transitions with fade and slide effects
- **Auto-Hide on Fullscreen**: Automatically hides when fullscreen applications are detected
- **Auto-Save**: Notes are automatically saved as you type
- **Windows 11 Aesthetic**: Modern UI with acrylic blur effects and rounded corners
- **Always Accessible**: Quick access button positioned on the right edge of your screen

## Installation

1. **Install Python 3.8 or higher**

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```bash
   python main.py
   ```

## Usage

- **Click the "NOTES" button** on the right side of your screen to expand the notepad
- **Click again** to collapse it back to the button
- **Click and drag the button vertically** to reposition it along the screen edge
- **Press `Ctrl + Alt + N`** to hide or unhide the overlay button at any time
- **Type your notes** - they are automatically saved
- The overlay will **automatically hide** when you open a fullscreen application
- The overlay will **reappear** when you exit fullscreen mode

## Design

The button features a unique asymmetric design:
- **Left side**: Rounded/curved (semi-circle shape)
- **Right side**: Completely flat (sits flush against screen edge)
- **Text**: "NOTES" displayed vertically (one letter per line)
- **Styling**: Windows 11 acrylic blur effect with semi-transparent background

## Project Structure

```
NoteApp/
├── main.py                 # Main application entry point
├── overlay_button.py       # Custom asymmetric button widget
├── notes_window.py         # Notepad window component
├── fullscreen_detector.py  # Fullscreen application detection
├── notes_manager.py        # Note persistence (save/load)
├── config.py              # Configuration settings
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## Configuration

You can modify settings in `config.py`:
- Button size and position
- Animation duration and easing
- Colors and opacity
- Window dimensions

## Notes Storage

Notes are automatically saved to:
```
%USERPROFILE%\.notes_overlay\notes.json
```

## Requirements

- Windows 10/11
- Python 3.8+
- PyQt6
- pywin32 (for fullscreen detection)

## License

This project is provided as-is for personal use.

