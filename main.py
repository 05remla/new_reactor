import sys
import os
from PyQt5.QtWidgets import QApplication, QSplashScreen
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt

if getattr(sys, "frozen", False):
    app_dir = os.path.dirname(sys.executable)
else:
    app_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(f"{app_dir}/plugins")
sys.path.append(app_dir)

# Initialize App & Splash Screen IMMEDIATELY
QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)

# Optimizations
sys.argv.append("--disable-gpu")
sys.argv.append("--disable-software-rasterizer")
sys.argv.append("--limit-fps=30")

app = QApplication(sys.argv)
splash_image = os.path.join(app_dir, "ui_files", "images", "splash.jpg")
splash_pixmap = QPixmap(splash_image)
splash = QSplashScreen(splash_pixmap, Qt.WindowStaysOnTopHint)
splash.show()
app.processEvents()

# NOW import the rest of the application
import glob
import json
import requests
import re
import shutil
from string import Template
from datetime import datetime
from hybrid_shell.hs import time_stamp
from hybrid_shell.hs import stringx
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QFileDialog, QInputDialog, QMessageBox, QDockWidget, QListWidget, QTextEdit)
from PyQt5.QtCore import QThread, pyqtSignal, QEvent, QTimer, QFileSystemWatcher

# Import the UI components
from mainwindow import Ui_MainWindow
from settings import Ui_SettingsWindow
from subwindow import Ui_AddDataWindow
from mainwindow import MstyCloneApp

def load_and_start():
    try:
        import da_patch
        da_patch.apply_deepagents_patches()
        import langchain_openai
        import langchain_core
        import deepagents
        import transformers
        import torch
    except Exception:
        pass

    global window
    window = MstyCloneApp(config_filename=config_file)
    window.show()
    splash.finish(window)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Msty Clone App")
    parser.add_argument("--cfg-file", type=str, default="config.json", help="Path to the config file.")
    args, unknown = parser.parse_known_args()

    config_filename = args.cfg_file
    if config_filename == "config.json":
        config_file = os.path.join(app_dir, config_filename)
    else:
        config_file = os.path.abspath(config_filename)

    QTimer.singleShot(100, load_and_start)
    sys.exit(app.exec_())
