#!/home/leo/.pyvirtenvs/new_reactor/bin/python
import sys
import os
from hybrid_shell.hs import stringx as sx
from threading import Thread
from time import sleep

app_dir = "/home/leo/.pyvirtenvs/new_reactor"
sys.path.append(app_dir)

from PyQt5 import QtCore, QtGui, QtWidgets
from config_selector_ui import *

def populate():
    dirs = os.listdir(os.path.join(app_dir, "workspaces"))
    for d in dirs:
        files = os.listdir(os.path.join(app_dir, "workspaces", d))
        for f in files:
            if '.json' in f:
                name = os.path.join(app_dir, "workspaces", d, f)
                ui.listWidget.insertItem(0, name)

workspace_mgr_window = None

def refresh_list():
    ui.listWidget.clear()
    populate()

def edit():
    global workspace_mgr_window
    import workspace_manager
    workspace_mgr_window = workspace_manager.WorkspaceManager()
    workspace_mgr_window.setAttribute(QtCore.Qt.WA_DeleteOnClose)
    workspace_mgr_window.destroyed.connect(refresh_list)
    workspace_mgr_window.show()

def start(config):
    cmd = f"/home/leo/.pyvirtenvs/new_reactor/bin/python /home/leo/.pyvirtenvs/new_reactor/main.py --cfg-file {config}"
    sx(cmd, wait=False)
    quit()

def signals_and_slots():
    ui.pushButton.clicked.connect(edit)
    ui.pushButton_2.clicked.connect(lambda: start(ui.listWidget.currentItem().text()) if ui.listWidget.currentItem() else None)
    ui.listWidget.itemDoubleClicked.connect(lambda item: start(item.text()))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    import theme_manager
    theme_manager.apply_theme(MainWindow)
    populate()
    signals_and_slots()
    MainWindow.show()
    sys.exit(app.exec_())
