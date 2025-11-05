import socket
import json

class TelemetryListener:
    def __init__(self, port=9996):
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('0.0.0.0', self.port))
        self.running = False

    def start(self):
        self.running = True
        print(f"Listening on UDP port {self.port}...")
        while self.running:
            data, addr = self.sock.recvfrom(1024)  # Adjust buffer size
            try:
                telemetry = json.loads(data.decode())
                print("Telemetry:", telemetry)
                # TODO: save telemetry to file / database
            except json.JSONDecodeError:
                print("Received invalid JSON")

    def stop(self):
        self.running = False
        self.sock.close()
