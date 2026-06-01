import sys
import os
if getattr(sys, "frozen", False):
    app_dir = os.path.dirname(sys.executable)
else:
    app_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(f"{app_dir}/plugins")
sys.path.append(app_dir)

import da_patch
da_patch.apply_deepagents_patches()

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
    QApplication, QMainWindow, QWidget, QFileDialog, QInputDialog, QMessageBox, QDockWidget, QListWidget, QTextEdit)
from PyQt5.QtCore import QThread, pyqtSignal, QEvent, QTimer, Qt, QFileSystemWatcher

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, HumanMessagePromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_core.tools import StructuredTool
from deepagents.backends import FilesystemBackend
# from deepagents.backends import CompositeBackend
# from deepagents.backends import LocalShellBackend
# from deepagents.backends import StateBackend
import toolz
import parse_markdown_plugin

try:
    from deepagents import create_deep_agent
except ImportError:
    create_deep_agent = None

# High DPI and WebEngine config MUST be set before QWebEngineView imports
QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)

# Optimizations
sys.argv.append("--disable-gpu")
sys.argv.append("--disable-software-rasterizer") 
sys.argv.append("--limit-fps=30")

# from PyQt5.QtWebEngineWidgets import QWebEngineSettings
# settings = QWebEngineSettings.globalSettings()
# # Disable features you don't need
# settings.setAttribute(QWebEngineSettings.PluginsEnabled, False)
# settings.setAttribute(QWebEngineSettings.WebGLEnabled, False)
# settings.setAttribute(QWebEngineSettings.PlaybackRequiresUserGesture, True) # Stops auto-playing videos

# Import the UI components
from mainwindow import Ui_MainWindow
from settings import Ui_SettingsWindow
from subwindow import Ui_AddDataWindow


from mainwindow_app import MstyCloneApp

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

    app = QApplication(sys.argv)
    window = MstyCloneApp(config_filename=config_file)
    window.show()
    sys.exit(app.exec_())
