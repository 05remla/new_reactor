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

def edit(config):
    pass

def start(config):
    cmd = f"/home/leo/.pyvirtenvs/new_reactor/bin/python /home/leo/.pyvirtenvs/new_reactor/main.py --cfg-file {config}"
    sx(cmd, wait=False)
    quit()

def signals_and_slots():
    ui.pushButton.clicked.connect(lambda: edit(ui.listWidget.currentItem().text()))
    ui.pushButton_2.clicked.connect(lambda: start(ui.listWidget.currentItem().text()))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    populate()
    signals_and_slots()
    MainWindow.show()
    sys.exit(app.exec_())
