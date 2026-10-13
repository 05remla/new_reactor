"""
voice_plugin.py

Provides Voice Agent capabilities (Speech-to-Text via AssemblyAI and Text-to-Speech via Cartesia).
Requires: pip install websockets pyaudio
          sudo apt-get install python3-pyaudio
          sudo apt-get install portaudio19-dev python3-dev
"""

from PyQt5.QtWidgets import QPushButton, QMessageBox, QWidget, QFormLayout, QLineEdit, QLabel
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QIcon
import json
import base64
import asyncio

try:
    import websockets
    import pyaudio
except ImportError:
    websockets = None
    pyaudio = None

PLUGIN_META = {
    "name": "Voice Agent",
    "version": "1.0",
    "description": "Adds Dictate (STT) and Read Aloud (TTS) capabilities using AssemblyAI and Cartesia.",
    "author": "ITReactor"
}

class STTThread(QThread):
    transcript_updated = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, api_key):
        super().__init__()
        self.api_key = api_key
        self.is_recording = True

    def run(self):
        if not websockets or not pyaudio:
            self.error_occurred.emit("Missing dependencies. Please run: pip install websockets pyaudio")
            return
            
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.record_and_send())
        loop.close()

    async def record_and_send(self):
        try:
            url = "wss://streaming.assemblyai.com/v2/ws?sample_rate=16000"
            
            p = pyaudio.PyAudio()
            stream = p.open(format=pyaudio.paInt16,
                            channels=1,
                            rate=16000,
                            input=True,
                            frames_per_buffer=3200)

            async with websockets.connect(url, additional_headers={"Authorization": self.api_key}) as ws:
                
                async def send():
                    while self.is_recording:
                        data = stream.read(3200, exception_on_overflow=False)
                        payload = {"audio_data": base64.b64encode(data).decode("utf-8")}
                        await ws.send(json.dumps(payload))
                        await asyncio.sleep(0.01)
                    
                    # Terminate
                    await ws.send(json.dumps({"terminate_session": True}))
                
                async def receive():
                    while True:
                        try:
                            msg = await ws.recv()
                            data = json.loads(msg)
                            if data.get("message_type") == "FinalTranscript":
                                text = data.get("text", "")
                                if text:
                                    self.transcript_updated.emit(text + " ")
                            elif data.get("message_type") == "SessionTerminated":
                                break
                        except Exception:
                            break

                await asyncio.gather(send(), receive())
                
                stream.stop_stream()
                stream.close()
                p.terminate()
        except Exception as e:
            self.error_occurred.emit(str(e))

class TTSThread(QThread):
    error_occurred = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, api_key, voice_id, model_id, text):
        super().__init__()
        self.api_key = api_key
        self.voice_id = voice_id
        self.model_id = model_id
        self.text = text

    def run(self):
        if not websockets or not pyaudio:
            self.error_occurred.emit("Missing dependencies. Please run: pip install websockets pyaudio")
            return
            
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.synthesize_and_play())
        loop.close()
        
    async def synthesize_and_play(self):
        import uuid
        try:
            url = f"wss://api.cartesia.ai/tts/websocket?api_key={self.api_key}&cartesia_version=2024-06-10"
            async with websockets.connect(url) as ws:
                payload = {
                    "model_id": self.model_id,
                    "transcript": self.text,
                    "voice": {
                        "mode": "id",
                        "id": self.voice_id,
                    },
                    "output_format": {
                        "container": "raw",
                        "encoding": "pcm_s16le",
                        "sample_rate": 24000,
                    },
                    "language": "en",
                    "context_id": f"ctx_{uuid.uuid4().hex}",
                }
                await ws.send(json.dumps(payload))
                
                p = pyaudio.PyAudio()
                stream = p.open(format=pyaudio.paInt16,
                                channels=1,
                                rate=24000,
                                output=True)
                
                while True:
                    try:
                        raw_message = await asyncio.wait_for(ws.recv(), timeout=10.0)
                        message = json.loads(raw_message)
                        
                        
                        if "error" in message:
                            raise Exception(f"API Error: {message['error']}")
                        if message.get("type") == "error":
                            raise Exception(f"API Error: {message}")
                            
                        if "data" in message and message["data"]:
                            audio_chunk = base64.b64decode(message["data"])
                            if audio_chunk:
                                stream.write(audio_chunk)
                        
                        if message.get("done") or message.get("type") == "done":
                            break
                    except asyncio.TimeoutError:
                        raise Exception("Timeout waiting for audio data from API.")
                    except websockets.exceptions.ConnectionClosed as cc:
                        raise Exception(f"Connection closed by server: {cc.code} - {cc.reason}")
                        
                stream.stop_stream()
                stream.close()
                p.terminate()
                self.finished.emit()
        except Exception as e:
            err_msg = str(e) or repr(e)
            self.error_occurred.emit(err_msg)

def enable_plugin(main_window):
    if getattr(main_window, '_voice_plugin_installed', False):
        return
    main_window._voice_plugin_installed = True

    # -- UI INJECTION --
    
    # 1. Dictate Button (STT)
    dictate_btn = QPushButton("🎙️ Dictate")
    dictate_btn.setCheckable(True)
    dictate_btn.setStyleSheet("""
        QPushButton { font-weight: bold; padding: 4px 8px; border-radius: 4px; }
        QPushButton:checked { background-color: #e74c3c; color: white; }
    """)
    main_window.ui.dictate_btn = dictate_btn
    main_window.ui.horizontalLayout_4.insertWidget(0, dictate_btn) # Near the Send button

    def toggle_dictation(checked):
        if checked:
            api_key = main_window.config.get("assemblyai_api_key", "")
            if not api_key:
                QMessageBox.warning(main_window, "Missing Key", "Please set ASSEMBLYAI_API_KEY in Settings -> Voice Plugin.")
                dictate_btn.setChecked(False)
                return
            
            dictate_btn.setText("🛑 Stop Dictating")
            main_window._stt_thread = STTThread(api_key)
            
            def append_text(t):
                current = main_window.ui.input_box.toPlainText()
                main_window.ui.input_box.setPlainText(current + t)
                main_window.ui.input_box.moveCursor(main_window.ui.input_box.textCursor().End)
                
            def stt_error(err):
                QMessageBox.warning(main_window, "Dictation Error", f"[STT Error] {err}")
                dictate_btn.setChecked(False)
                
            main_window._stt_thread.transcript_updated.connect(append_text)
            main_window._stt_thread.error_occurred.connect(stt_error)
            main_window._stt_thread.start()
        else:
            dictate_btn.setText("🎙️ Dictate")
            if hasattr(main_window, '_stt_thread') and main_window._stt_thread:
                main_window._stt_thread.is_recording = False

    dictate_btn.toggled.connect(toggle_dictation)

    # 2. Read Last Button (TTS)
    read_btn = QPushButton("🔊 Read Last")
    read_btn.setStyleSheet("font-weight: bold; padding: 4px 8px; border-radius: 4px;")
    main_window.ui.read_btn = read_btn
    main_window.ui.horizontalLayout_2.insertWidget(2, read_btn) # Top bar

    def read_last_message():
        api_key = main_window.config.get("cartesia_api_key", "")
        if not api_key:
            QMessageBox.warning(main_window, "Missing Key", "Please set CARTESIA_API_KEY in Settings -> Voice Plugin.")
            return

        last_agent_msg = ""
        for msg in reversed(main_window.messages):
            if msg.get("role") == "assistant":
                last_agent_msg = msg.get("content", "")
                break
                
        if not last_agent_msg:
            return

        voice_id = main_window.config.get("cartesia_voice_id", "f6ff7c0c-e396-40a9-a70b-f7607edb6937")
        model_id = main_window.config.get("cartesia_model_id", "sonic-english")

        read_btn.setEnabled(False)
        read_btn.setText("🔊 Playing...")
        
        main_window._tts_thread = TTSThread(api_key, voice_id, model_id, last_agent_msg)
        
        def tts_finished():
            read_btn.setEnabled(True)
            read_btn.setText("🔊 Read Last")
            
        def tts_error(err):
            QMessageBox.warning(main_window, "Read Aloud Error", f"[TTS Error] {err}")
            tts_finished()
            
        main_window._tts_thread.finished.connect(tts_finished)
        main_window._tts_thread.error_occurred.connect(tts_error)
        main_window._tts_thread.start()

    read_btn.clicked.connect(read_last_message)

    # -- SETTINGS INJECTION --
    main_window._original_open_settings_voice = main_window.open_settings_window

    def patched_open_settings():
        main_window._original_open_settings_voice()
        settings_win = getattr(main_window, 'settings_win', None)
        if not settings_win: return

        tab_widget = settings_win.findChild(QWidget, "tabWidget")
        if not tab_widget: return

        voice_tab = QWidget()
        layout = QFormLayout(voice_tab)

        aai_edit = QLineEdit(main_window.config.get("assemblyai_api_key", ""))
        layout.addRow("AssemblyAI API Key (STT):", aai_edit)

        cartesia_edit = QLineEdit(main_window.config.get("cartesia_api_key", ""))
        layout.addRow("Cartesia API Key (TTS):", cartesia_edit)

        cartesia_voice_edit = QLineEdit(main_window.config.get("cartesia_voice_id", "f6ff7c0c-e396-40a9-a70b-f7607edb6937"))
        layout.addRow("Cartesia Voice ID:", cartesia_voice_edit)

        cartesia_model_edit = QLineEdit(main_window.config.get("cartesia_model_id", "sonic-english"))
        layout.addRow("Cartesia Model ID:", cartesia_model_edit)

        def save_settings(*args):
            main_window.config["assemblyai_api_key"] = aai_edit.text()
            main_window.config["cartesia_api_key"] = cartesia_edit.text()
            main_window.config["cartesia_voice_id"] = cartesia_voice_edit.text()
            main_window.config["cartesia_model_id"] = cartesia_model_edit.text()
            
            if hasattr(settings_win, '_push_save'):
                settings_win._push_save()

        aai_edit.textChanged.connect(save_settings)
        cartesia_edit.textChanged.connect(save_settings)
        cartesia_voice_edit.textChanged.connect(save_settings)
        cartesia_model_edit.textChanged.connect(save_settings)

        tab_widget.addTab(voice_tab, "Voice Plugin")

    main_window.open_settings_window = patched_open_settings
    if hasattr(main_window.ui, 'actionSettings_2'):
        try:
            main_window.ui.actionSettings_2.disconnect()
        except Exception:
            pass
        main_window.ui.actionSettings_2.triggered.connect(main_window.open_settings_window)

def disable_plugin(main_window):
    if not getattr(main_window, '_voice_plugin_installed', False):
        return

    # Clean up UI
    if hasattr(main_window.ui, 'dictate_btn'):
        main_window.ui.horizontalLayout_4.removeWidget(main_window.ui.dictate_btn)
        main_window.ui.dictate_btn.deleteLater()
        del main_window.ui.dictate_btn

    if hasattr(main_window.ui, 'read_btn'):
        main_window.ui.horizontalLayout_2.removeWidget(main_window.ui.read_btn)
        main_window.ui.read_btn.deleteLater()
        del main_window.ui.read_btn

    # Restore Settings
    if hasattr(main_window, '_original_open_settings_voice'):
        main_window.open_settings_window = main_window._original_open_settings_voice
        del main_window._original_open_settings_voice
        if hasattr(main_window.ui, 'actionSettings_2'):
            try:
                main_window.ui.actionSettings_2.disconnect()
            except Exception:
                pass
            main_window.ui.actionSettings_2.triggered.connect(main_window.open_settings_window)

    main_window._voice_plugin_installed = False
