# telemetry/listener.py
import socket
import json
import time


#we will listen to this later on 

class TelemetryListener:
    def __init__(self, port=9996, out_queue=None):
        self.port = port
        self.out_queue = out_queue
        self.sock = None
        self.running = False

    def start(self):
        # create socket on start so restart works cleanly
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("0.0.0.0", self.port))
        self.sock.settimeout(0.5)  # timeout so we can check running flag
        self.running = True
        print(f"Listening on UDP port {self.port}...")
        while self.running:
            try:
                data, addr = self.sock.recvfrom(4096)
                txt = data.decode(errors="ignore")
                try:
                    payload = json.loads(txt)
                except Exception:
                    # if not JSON, ignore
                    continue
                # add timestamp if not present
                if "ts" not in payload:
                    payload["ts"] = time.time()
                if self.out_queue is not None:
                    try:
                        self.out_queue.put(payload)
                    except Exception:
                        pass
            except socket.timeout:
                continue
            except OSError:
                # socket closed from another thread
                break
        # cleanup
        try:
            self.sock.close()
        except Exception:
            pass
        self.sock = None
        self.running = False
        print("Listener stopped")

    def stop(self):
        self.running = False
        # closing the socket will unblock recvfrom
        try:
            if self.sock:
                self.sock.close()
        except Exception:
            pass