# ui/main_window.py
import os
import time
from PyQt6.QtWidgets import (
    QMainWindow, QPushButton, QVBoxLayout, QWidget, QLabel, QHBoxLayout, QComboBox,
    QLineEdit, QMessageBox
)
from PyQt6.QtCore import QTimer
from telemetry.listener import TelemetryListener
from telemetry.simulator import TrackSimulator
from telemetry.storage import SessionWriter
from telemetry.upload import upload_session
import threading
import queue

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Telemetry App (simulator + listener)")
        self.resize(420, 200)

        self.queue = queue.Queue()
        self.listener = TelemetryListener(port=9996, out_queue=self.queue)
        self.listener_thread = None

        self.sim = TrackSimulator(target_host="127.0.0.1", target_port=9996, rate_hz=20)
        self.sim.set_track("Monza")
        self.sim.set_car("Porsche GT3 RS")
        self.sim_thread = None

        self.session_writer = None
        self.current_session_path = None

        # UI widgets
        self.speed_label = QLabel("Speed: — km/h")
        self.rpm_label = QLabel("RPM: —")
        self.throttle_label = QLabel("Throttle: — %")
        self.status_label = QLabel("Status: stopped")

        # Buttons
        self.start_listen_btn = QPushButton("Start Listener")
        self.start_listen_btn.clicked.connect(self.start_listener)
        self.stop_listen_btn = QPushButton("Stop Listener")
        self.stop_listen_btn.clicked.connect(self.stop_listener)
        self.stop_listen_btn.setEnabled(False)

        self.start_acc_sim_btn = QPushButton("Start ACC Simulator")
        self.start_acc_sim_btn.clicked.connect(self.start_acc_sim)
        self.stop_acc_sim_btn = QPushButton("Stop Simulator")
        self.stop_acc_sim_btn.clicked.connect(self.stop_simulator)
        self.stop_acc_sim_btn.setEnabled(False)

        self.save_session_btn = QPushButton("Start Session Recording")
        self.save_session_btn.clicked.connect(self.start_session)
        self.stop_session_btn = QPushButton("Stop Session Recording")
        self.stop_session_btn.clicked.connect(self.stop_session)
        self.stop_session_btn.setEnabled(False)
        
        # Upload functionality
        self.driver_name_input = QLineEdit()
        self.driver_name_input.setPlaceholderText("Driver Name")
        self.driver_name_input.setText("Default Driver")
        
        self.backend_url_input = QLineEdit()
        self.backend_url_input.setPlaceholderText("Backend URL")
        self.backend_url_input.setText("http://localhost:8000")
        
        self.upload_btn = QPushButton("Upload Last Session")
        self.upload_btn.clicked.connect(self.upload_last_session)

        # layout
        v = QVBoxLayout()
        v.addWidget(self.speed_label)
        v.addWidget(self.rpm_label)
        v.addWidget(self.throttle_label)
        v.addWidget(self.status_label)

        h = QHBoxLayout()
        h.addWidget(self.start_listen_btn)
        h.addWidget(self.stop_listen_btn)
        v.addLayout(h)

        h2 = QHBoxLayout()
        h2.addWidget(self.start_acc_sim_btn)
        h2.addWidget(self.stop_acc_sim_btn)
        v.addLayout(h2)

        h3 = QHBoxLayout()
        h3.addWidget(self.save_session_btn)
        h3.addWidget(self.stop_session_btn)
        v.addLayout(h3)
        
        v.addWidget(QLabel("Upload to Backend:"))
        v.addWidget(self.driver_name_input)
        v.addWidget(self.backend_url_input)
        v.addWidget(self.upload_btn)

        container = QWidget()
        container.setLayout(v)
        self.setCentralWidget(container)

        # Timer to poll queue and update UI
        self.timer = QTimer()
        self.timer.setInterval(100)  # ms
        self.timer.timeout.connect(self.poll_queue)
        self.timer.start()

    def start_listener(self):
        if self.listener_thread and self.listener_thread.is_alive():
            return
        self.listener_thread = threading.Thread(target=self.listener.start, daemon=True)
        self.listener_thread.start()
        self.status_label.setText("Status: listening on UDP 9996")
        self.start_listen_btn.setEnabled(False)
        self.stop_listen_btn.setEnabled(True)

    def stop_listener(self):
        self.listener.stop()
        self.status_label.setText("Status: stopped listener")
        self.start_listen_btn.setEnabled(True)
        self.stop_listen_btn.setEnabled(False)

    def start_acc_sim(self):
        if self.sim_thread and self.sim_thread.is_alive():
            return
        # sim is already configured to Monza + Porsche GT3 RS
        self.sim_thread = threading.Thread(target=self.sim.run, daemon=True)
        self.sim_thread.start()
        self.status_label.setText("Status: Monza simulator running -> sending UDP to 127.0.0.1:9996")
        self.start_acc_sim_btn.setEnabled(False)
        self.stop_acc_sim_btn.setEnabled(True)


    def stop_simulator(self):
        self.sim.stop()
        self.status_label.setText("Status: simulator stopped")
        self.start_acc_sim_btn.setEnabled(True)
        self.stop_acc_sim_btn.setEnabled(False)

    def start_session(self):
        # create sessions directory
        os.makedirs("sessions", exist_ok=True)
        fname = time.strftime("sessions/session_%Y%m%d_%H%M%S.jsonl.gz")
        self.session_writer = SessionWriter(fname)
        self.current_session_path = fname
        self.save_session_btn.setEnabled(False)
        self.stop_session_btn.setEnabled(True)
        self.status_label.setText(f"Status: recording -> {fname}")

    def stop_session(self):
        if self.session_writer:
            self.session_writer.close()
            self.session_writer = None
            self.status_label.setText(f"Status: saved session -> {self.current_session_path}")
            self.current_session_path = None
        self.save_session_btn.setEnabled(True)
        self.stop_session_btn.setEnabled(False)

    def poll_queue(self):
        # Pop latest item from queue (if any)
        popped = None
        try:
            while True:
                popped = self.queue.get_nowait()
                # keep consuming to show the latest
        except Exception:
            pass

        if popped:
            # popped is a dict with telemetry fields
            speed = popped.get("speed", "—")
            rpm = popped.get("rpm", "—")
            throttle = popped.get("throttle", "—")
            self.speed_label.setText(f"Speed: {speed} km/h")
            self.rpm_label.setText(f"RPM: {rpm}")
            self.throttle_label.setText(f"Throttle: {throttle} %")

            # write to session if active
            if self.session_writer:
                self.session_writer.write(popped)
    
    def upload_last_session(self):
        """Upload the most recent session file to the backend."""
        if not self.current_session_path:
            # Try to find the latest session file
            from pathlib import Path
            sessions_dir = Path("sessions")
            if not sessions_dir.exists():
                QMessageBox.warning(self, "No Session", "No session files found. Please record a session first.")
                return
            
            session_files = sorted(
                sessions_dir.glob("session_*.jsonl.gz"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            if not session_files:
                QMessageBox.warning(self, "No Session", "No session files found. Please record a session first.")
                return
            session_path = str(session_files[0])
        else:
            session_path = self.current_session_path
        
        driver_name = self.driver_name_input.text() or "Default Driver"
        backend_url = self.backend_url_input.text() or "http://localhost:8000"
        
        self.upload_btn.setEnabled(False)
        self.upload_btn.setText("Uploading...")
        
        def do_upload():
            try:
                result = upload_session(
                    session_path=session_path,
                    backend_url=backend_url,
                    driver_name=driver_name
                )
                if result:
                    QMessageBox.information(
                        self,
                        "Upload Success",
                        f"Session uploaded successfully!\n\n"
                        f"ID: {result.get('id', 'N/A')}\n"
                        f"Driver: {result.get('driver_name', 'N/A')}\n"
                        f"Car: {result.get('car', 'N/A')}\n"
                        f"Track: {result.get('track', 'N/A')}"
                    )
                else:
                    QMessageBox.warning(self, "Upload Failed", "Failed to upload session. Check backend connection.")
            except Exception as e:
                QMessageBox.critical(self, "Upload Error", f"Error during upload:\n{str(e)}")
            finally:
                self.upload_btn.setEnabled(True)
                self.upload_btn.setText("Upload Last Session")
        
        # Run upload in a separate thread to avoid blocking UI
        upload_thread = threading.Thread(target=do_upload, daemon=True)
        upload_thread.start()
