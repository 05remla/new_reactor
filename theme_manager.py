import json
import os
import sys

def get_app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.realpath(__file__))

def load_theme():
    theme_file = os.path.join(get_app_dir(), "ui_files", "theme.json")
    try:
        with open(theme_file, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Failed to load theme from {theme_file}: {e}")
        return {}

def apply_theme_to_widget(widget, theme_dict):
    """
    Recursively apply the theme dict to the widget's stylesheet.
    Replaces occurrences of '@color_name' with the actual hex code.
    """
    if not theme_dict:
        return

    # 1. Apply to the current widget
    if hasattr(widget, "styleSheet") and hasattr(widget, "setStyleSheet"):
        current_style = widget.styleSheet()
        if current_style:
            new_style = current_style
            for key, val in theme_dict.items():
                target = f"@{key}"
                if target in new_style:
                    new_style = new_style.replace(target, val)
            
            if new_style != current_style:
                widget.setStyleSheet(new_style)

    # 2. Apply to all children
    for child in widget.children():
        apply_theme_to_widget(child, theme_dict)

def apply_theme(window):
    """
    Loads the theme.json and applies it to the given window.
    Call this right after setupUi(self).
    """
    theme = load_theme()
    apply_theme_to_widget(window, theme)
