# ui/main_window.py
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget
from telemetry.listener import TelemetryListener
import threading

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Telemetry App")
        self.listener = TelemetryListener()
        self.listener_thread = None

        layout = QVBoxLayout()
        start_btn = QPushButton("Start")
        start_btn.clicked.connect(self.start_listener)
        stop_btn = QPushButton("Stop")
        stop_btn.clicked.connect(self.stop_listener)

        layout.addWidget(start_btn)
        layout.addWidget(stop_btn)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def start_listener(self):
        self.listener_thread = threading.Thread(target=self.listener.start, daemon=True)
        self.listener_thread.start()

    def stop_listener(self):
        self.listener.stop()
        if self.listener_thread:
            self.listener_thread.join()
