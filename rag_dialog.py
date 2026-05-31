import os
import requests
from PyQt5.QtWidgets import QWidget, QFileDialog, QApplication
from PyQt5.QtCore import Qt, QTimer
from subwindow import Ui_AddDataWindow

class RAGDataDialog(QWidget):
    def __init__(self, parent_app):
        super().__init__()
        self.app = parent_app
        self.ui = Ui_AddDataWindow()
        self.ui.setupUi(self)
        self.setWindowFlags(Qt.WindowStaysOnTopHint)

        # signals
        self.ui.file_btn.clicked.connect(self.load_file)
        self.ui.submit_btn.clicked.connect(self.submit_to_lightrag)

    def load_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select File", "", "Text Files (*.txt *.md *.csv *.json);;All Files (*.*)")
        if path:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    self.ui.textbox.setPlainText(f.read())
                self.ui.submit_btn.setText(f"Process & Insert: {os.path.basename(path)}")
            except Exception as e:
                self.ui.textbox.setPlainText(f"Error reading file:\n{str(e)}")

    def submit_to_lightrag(self):
        text = self.ui.textbox.toPlainText().strip()
        if not text: return
        self.ui.submit_btn.setText("Indexing... (Please wait)")
        self.ui.submit_btn.setEnabled(False)
        QApplication.processEvents()

        try:
            base = self.app.config.get("lightrag_url", "").rstrip("/")
            key = self.app.config.get("lightrag_api_key", "").strip()
            headers = {"X-API-Key": key} if key else {}

            payload = {
                "text": text,
                "model": self.app.ui.rag_model_combo.currentText().strip()
            }
            res = requests.post(f"{base}/insert", json=payload, headers=headers, timeout=120)
            res.raise_for_status()

            self.ui.submit_btn.setText("Knowledge Successfully Added!")
            self.ui.submit_btn.setStyleSheet("background-color: #2ecc71; color: white;")
            QTimer.singleShot(1500, self.close)
        except Exception as e:
            self.ui.submit_btn.setText("Error! Ensure key/server is correct.")
            self.ui.submit_btn.setStyleSheet("background-color: #e74c3c; color: white;")
            self.ui.submit_btn.setEnabled(True)


