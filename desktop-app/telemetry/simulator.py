# telemetry/simulator.py
"""
Monza + Porsche GT3 RS telemetry simulator.

Usage:
    from telemetry.simulator import TrackSimulator
    sim = TrackSimulator(target_host="127.0.0.1", target_port=9996, rate_hz=20)
    sim.set_track("Monza")
    sim.set_car("Porsche GT3 RS")
    # run in a background thread:
    # threading.Thread(target=sim.run, daemon=True).start()
    # to stop: sim.stop()
"""

import socket
import time
import json
import random
import math
from typing import Optional

# Monza official length ~5.793 km (5793 m)
MONZA_LENGTH_M = 5793.0

# Simplified Monza segments (name, length_m, target_speed_kmh, sector, is_pitlane, is_curve)
# Sectors: 1, 2, 3
# is_pitlane: True if this segment is part of pitlane
# is_curve: True if this is a curve/corner
MONZA_SEGMENTS = [
    ("Rettifilo", 1200, 320, 1, False, False),
    ("Variante del Rettifilo", 200, 90, 1, False, True),
    ("Curva Grande", 900, 170, 1, False, True),
    ("Lesmo 1", 300, 120, 2, False, True),
    ("Lesmo 2", 300, 120, 2, False, True),
    ("Variante della Roggia", 200, 100, 2, False, True),
    ("Back Straight", 900, 320, 2, False, False),
    ("Parabolica", 600, 140, 3, False, True),
    ("Ascari-ish/Approach", 893, 220, 3, False, True),
]

# Pitlane entry/exit positions (in meters from start)
PITLANE_ENTRY_M = 100.0  # Just after start/finish
PITLANE_EXIT_M = 200.0   # Before first corner
PITLANE_LENGTH_M = 400.0  # Total pitlane length

CAR_PRESETS = {
    "Porsche GT3 RS": {
        "mass_kg": 1420,
        "max_speed_kmh": 315,
        "max_rpm": 9000,
        "redline_rpm": 8800,
        "idle_rpm": 900,
        "gears": 6,
        "gear_speed_kmh": [0, 60, 110, 160, 220, 275, 330],
        "accel_m_s2": 6.5,
        "brake_m_s2": 10.0,
        "power_curve": 1.0,
    }
}


def clamp(x, a, b):
    return max(a, min(b, x))


class TrackSimulator:
    def __init__(self, target_host="127.0.0.1", target_port=9996, rate_hz=20, random_seed=None):
        self.host = target_host
        self.port = target_port
        self.rate_hz = rate_hz
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.running = False

        self.track_name = "Monza"
        self.track_segments = MONZA_SEGMENTS
        self.track_length_m = MONZA_LENGTH_M

        self.car_name = "Porsche GT3 RS"
        self.car = CAR_PRESETS[self.car_name].copy()

        self.random = random.Random(random_seed)

        self.lap = 0
        self.position_m = 0.0
        self.speed_ms = 0.0
        self.gear = 1
        
        # Sector timing
        self.sector = 1
        self.sector_start_time = None
        self.sector_times = []  # List of sector times for current lap
        self.lap_sector_times = []  # List of lists: [[s1, s2, s3], ...] per lap
        
        # Pitlane state
        self.in_pitlane = False
        self.pitlane_entry_time = None
        self.pitlane_exit_time = None
        
        # Lap timing
        self.lap_start_time = None
        self.best_lap_time = None
        self.current_lap_time = 0.0

    def set_track(self, name: str):
        if name.lower() == "monza":
            self.track_name = "Monza"
            self.track_segments = MONZA_SEGMENTS
            self.track_length_m = MONZA_LENGTH_M
        else:
            raise ValueError("Unknown track")

    def set_car(self, name: str):
        if name in CAR_PRESETS:
            self.car_name = name
            self.car = CAR_PRESETS[name].copy()
        else:
            raise ValueError("Unknown car preset")

    def stop(self):
        self.running = False

    def run(self):
        """Blocking run; call stop() to exit (or use in a thread)."""
        self.running = True
        t0 = time.time()
        self.lap_start_time = t0
        self.lap = 1
        self.position_m = 0.0
        self.speed_ms = 0.0
        self.gear = 1
        self.sector = 1
        self.sector_start_time = t0
        self.sector_times = []
        self.lap_sector_times = []
        self.in_pitlane = False

        tick_dt = 1.0 / self.rate_hz
        while self.running:
            loop_start = time.time()

            seg_name, seg_len, target_kmh, seg_sector, is_pitlane_seg, is_curve = self._segment_for_position(self.position_m)
            
            # Check for pitlane entry/exit
            self._check_pitlane_transitions()
            
            # Adjust target speed if in pitlane
            if self.in_pitlane:
                target_kmh = 60.0  # Pitlane speed limit
            target_ms = (target_kmh / 3.6)
            
            # Update sector if changed
            if seg_sector != self.sector:
                self._on_sector_change(seg_sector, time.time())

            speed_error = target_ms - self.speed_ms
            if speed_error > 0:
                desired_acc = clamp(speed_error * 0.7 + self.random.gauss(0, 0.2), -self.car["brake_m_s2"], self.car["accel_m_s2"])
            else:
                desired_acc = clamp(speed_error * 0.9 + self.random.gauss(0, 0.5), -self.car["brake_m_s2"], self.car["accel_m_s2"])

            speed_kmh = self.speed_ms * 3.6
            drag_acc = -0.0005 * (speed_kmh ** 2) / self.car["mass_kg"]
            net_acc = desired_acc + drag_acc

            self.speed_ms += net_acc * tick_dt
            if self.speed_ms < 0:
                self.speed_ms = 0.0

            self.position_m += self.speed_ms * tick_dt

            if self.position_m >= self.track_length_m:
                self.position_m -= self.track_length_m
                self._on_lap_complete(time.time())
                self.lap += 1
                self.lap_start_time = time.time()
                self.sector = 1
                self.sector_start_time = time.time()
                self.sector_times = []

            self.gear = self._gear_for_speed(speed_kmh)

            gear_ratio_factor = 60
            rpm = int(clamp(self.speed_ms * 3.6 * gear_ratio_factor / max(1, self.gear), self.car["idle_rpm"], self.car["max_rpm"]))
            rpm += int(self.random.gauss(0, 50))

            throttle_pct = 0.0
            brake_pct = 0.0
            if net_acc >= 0.1:
                throttle_pct = clamp(100 * (net_acc / (self.car["accel_m_s2"] + 0.001)), 0, 100)
                throttle_pct = round(throttle_pct * self.random.uniform(0.9, 1.05), 1)
            elif net_acc < -0.5:
                brake_pct = clamp(100 * (-net_acc / (self.car["brake_m_s2"] + 0.001)), 0, 100)
                brake_pct = round(brake_pct * self.random.uniform(0.9, 1.05), 1)

            steer = self._steer_for_segment(seg_name, self.position_m)
            current_time = time.time()
            lap_time = current_time - self.lap_start_time if self.lap_start_time else 0.0
            self.current_lap_time = lap_time

            # Calculate sector time
            sector_time = current_time - self.sector_start_time if self.sector_start_time else 0.0
            
            # Get best sector times
            best_s1 = self._get_best_sector_time(1)
            best_s2 = self._get_best_sector_time(2)
            best_s3 = self._get_best_sector_time(3)
            
            payload = {
                "source": "SIM",
                "car": self.car_name,
                "track": self.track_name,
                "lap": self.lap,
                "segment": seg_name,
                "sector": self.sector,
                "position_m": round(self.position_m, 2),
                "lap_time_s": round(lap_time, 3),
                "sector_time_s": round(sector_time, 3),
                "best_lap_time_s": round(self.best_lap_time, 3) if self.best_lap_time else None,
                "best_sector_1_s": round(best_s1, 3) if best_s1 else None,
                "best_sector_2_s": round(best_s2, 3) if best_s2 else None,
                "best_sector_3_s": round(best_s3, 3) if best_s3 else None,
                "speed": round(self.speed_ms * 3.6, 2),
                "rpm": rpm,
                "throttle": throttle_pct,
                "brake": brake_pct,
                "gear": int(self.gear),
                "steer": round(steer, 3),
                "in_pitlane": self.in_pitlane,
                "is_curve": is_curve,
                "ts": current_time
            }

            try:
                self.sock.sendto(json.dumps(payload).encode("utf-8"), (self.host, self.port))
            except Exception:
                pass

            elapsed = time.time() - loop_start
            to_sleep = tick_dt - elapsed
            if to_sleep > 0:
                time.sleep(to_sleep)

        try:
            self.sock.close()
        except Exception:
            pass

    def _segment_for_position(self, pos_m):
        p = pos_m % self.track_length_m
        acc = 0.0
        for seg in self.track_segments:
            name, length, speed, sector, is_pitlane, is_curve = seg
            if acc <= p < acc + length:
                return name, length, speed, sector, is_pitlane, is_curve
            acc += length
        # Return last segment if position is beyond all segments
        last = self.track_segments[-1]
        return last[0], last[1], last[2], last[3], last[4], last[5]

    def _gear_for_speed(self, speed_kmh):
        thresholds = self.car.get("gear_speed_kmh", [])
        gear = 1
        for g in range(1, min(len(thresholds), self.car["gears"] + 1)):
            if speed_kmh >= thresholds[g]:
                gear = g
        return clamp(gear, 1, self.car["gears"])

    def _steer_for_segment(self, seg_name, pos_m):
        corner_keywords = ["Variante", "Lesmo", "Parabolica", "Curva", "Roggio", "Approach", "Ascari", "Lesmo"]
        base = 0.0
        for kw in corner_keywords:
            if kw.lower() in seg_name.lower():
                seg_start = self._segment_start_position(seg_name)
                seg_length = self._segment_length_by_name(seg_name)
                if seg_length <= 0:
                    return 0.0
                rel = ((pos_m - seg_start) % self.track_length_m) / seg_length
                steer_peak = math.sin(math.pi * clamp(rel, 0.0, 1.0))
                base = steer_peak * self.random.uniform(0.4, 0.85)
                if self.random.random() < 0.5:
                    base = -base
                return base
        return round(self.random.gauss(0.0, 0.005), 3)

    def _segment_start_position(self, seg_name):
        acc = 0.0
        for seg in self.track_segments:
            name = seg[0]
            if name == seg_name:
                return acc
            acc += seg[1]  # length is at index 1
        return 0.0

    def _segment_length_by_name(self, seg_name):
        for seg in self.track_segments:
            name = seg[0]
            if name == seg_name:
                return seg[1]
        return 0.0
    
    def _check_pitlane_transitions(self):
        """Check if we're entering or exiting the pitlane."""
        current_time = time.time()
        p = self.position_m % self.track_length_m
        
        # Enter pitlane (simplified: near start/finish line)
        if not self.in_pitlane and PITLANE_ENTRY_M - 10 <= p <= PITLANE_ENTRY_M + 10:
            # Random chance to enter pitlane (for realism, could be triggered by user)
            if self.random.random() < 0.01:  # 1% chance per check
                self.in_pitlane = True
                self.pitlane_entry_time = current_time
        
        # Exit pitlane
        if self.in_pitlane and PITLANE_EXIT_M - 10 <= p <= PITLANE_EXIT_M + 10:
            self.in_pitlane = False
            self.pitlane_exit_time = current_time
    
    def _on_sector_change(self, new_sector: int, current_time: float):
        """Called when entering a new sector."""
        if self.sector_start_time is not None:
            sector_time = current_time - self.sector_start_time
            self.sector_times.append(sector_time)
        
        self.sector = new_sector
        self.sector_start_time = current_time
    
    def _on_lap_complete(self, current_time: float):
        """Called when completing a lap."""
        # Record final sector time
        if self.sector_start_time is not None:
            sector_time = current_time - self.sector_start_time
            self.sector_times.append(sector_time)
        
        # Store sector times for this lap
        if len(self.sector_times) >= 3:
            self.lap_sector_times.append(self.sector_times.copy())
        
        # Calculate lap time
        if self.lap_start_time is not None:
            lap_time = current_time - self.lap_start_time
            if self.best_lap_time is None or lap_time < self.best_lap_time:
                self.best_lap_time = lap_time
        
        # Reset for next lap
        self.sector_times = []
        self.sector = 1
    
    def _get_best_sector_time(self, sector_num: int) -> Optional[float]:
        """Get the best time for a specific sector across all laps."""
        if sector_num < 1 or sector_num > 3:
            return None
        
        best = None
        for lap_sectors in self.lap_sector_times:
            if len(lap_sectors) >= sector_num:
                sector_time = lap_sectors[sector_num - 1]
                if best is None or sector_time < best:
                    best = sector_time
        
        return best
    
    def enter_pitlane(self):
        """Manually trigger pitlane entry (for testing/realism)."""
        if not self.in_pitlane:
            self.in_pitlane = True
            self.pitlane_entry_time = time.time()
    
    def exit_pitlane(self):
        """Manually trigger pitlane exit."""
        if self.in_pitlane:
            self.in_pitlane = False
            self.pitlane_exit_time = time.time()