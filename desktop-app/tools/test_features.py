# tools/test_features.py
"""
Test script to verify upload and simulator features work correctly.
"""
import sys
import time
import threading
from pathlib import Path

# Fix import path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from telemetry.simulator import TrackSimulator
from telemetry.listener import TelemetryListener
from telemetry.storage import SessionWriter
from telemetry.upload import upload_session, extract_session_metadata
import queue


def test_simulator_features():
    """Test that simulator produces sector, pitlane, and curve data."""
    print("=" * 60)
    print("Testing Simulator Features (Sectors, Pitlane, Curves)")
    print("=" * 60)
    
    q = queue.Queue()
    listener = TelemetryListener(port=9996, out_queue=q)
    listener_thread = threading.Thread(target=listener.start, daemon=True)
    listener_thread.start()
    time.sleep(0.2)
    
    sim = TrackSimulator(target_host="127.0.0.1", target_port=9996, rate_hz=20)
    sim.set_track("Monza")
    sim.set_car("Porsche GT3 RS")
    
    sim_thread = threading.Thread(target=sim.run, daemon=True)
    sim_thread.start()
    
    print("\nCollecting telemetry samples for 5 seconds...")
    samples = []
    start_time = time.time()
    
    while time.time() - start_time < 5:
        try:
            payload = q.get(timeout=1.0)
            if isinstance(payload, dict):
                samples.append(payload)
        except queue.Empty:
            continue
    
    sim.stop()
    listener.stop()
    time.sleep(0.5)
    
    if not samples:
        print("❌ ERROR: No samples received!")
        return False
    
    print(f"\n✓ Collected {len(samples)} samples")
    
    # Check for new fields
    checks = {
        "sector": False,
        "sector_time_s": False,
        "best_lap_time_s": False,
        "best_sector_1_s": False,
        "in_pitlane": False,
        "is_curve": False,
    }
    
    for sample in samples:
        if "sector" in sample:
            checks["sector"] = True
        if "sector_time_s" in sample:
            checks["sector_time_s"] = True
        if "best_lap_time_s" in sample:
            checks["best_lap_time_s"] = True
        if "best_sector_1_s" in sample:
            checks["best_sector_1_s"] = True
        if "in_pitlane" in sample:
            checks["in_pitlane"] = True
        if "is_curve" in sample:
            checks["is_curve"] = True
    
    print("\nChecking for new telemetry fields:")
    all_passed = True
    for field, found in checks.items():
        status = "✓" if found else "❌"
        print(f"  {status} {field}: {found}")
        if not found:
            all_passed = False
    
    # Show sample data
    print("\nSample telemetry data:")
    sample = samples[-1]
    print(f"  Sector: {sample.get('sector', 'N/A')}")
    print(f"  Sector Time: {sample.get('sector_time_s', 'N/A')}s")
    print(f"  Best Lap: {sample.get('best_lap_time_s', 'N/A')}s")
    print(f"  In Pitlane: {sample.get('in_pitlane', 'N/A')}")
    print(f"  Is Curve: {sample.get('is_curve', 'N/A')}")
    print(f"  Speed: {sample.get('speed', 'N/A')} km/h")
    
    return all_passed


def test_session_recording():
    """Test recording a session with new features."""
    print("\n" + "=" * 60)
    print("Testing Session Recording")
    print("=" * 60)
    
    q = queue.Queue()
    listener = TelemetryListener(port=9997, out_queue=q)
    listener_thread = threading.Thread(target=listener.start, daemon=True)
    listener_thread.start()
    time.sleep(0.2)
    
    sim = TrackSimulator(target_host="127.0.0.1", target_port=9997, rate_hz=20)
    sim.set_track("Monza")
    sim.set_car("Porsche GT3 RS")
    
    sim_thread = threading.Thread(target=sim.run, daemon=True)
    sim_thread.start()
    
    # Record session
    Path("sessions").mkdir(exist_ok=True)
    fname = time.strftime("sessions/test_session_%Y%m%d_%H%M%S.jsonl.gz")
    writer = SessionWriter(fname)
    
    print(f"\nRecording session to {fname}...")
    start_time = time.time()
    sample_count = 0
    
    while time.time() - start_time < 3:
        try:
            payload = q.get(timeout=1.0)
            if isinstance(payload, dict):
                writer.write(payload)
                sample_count += 1
        except queue.Empty:
            continue
    
    writer.close()
    sim.stop()
    listener.stop()
    time.sleep(0.5)
    
    print(f"✓ Recorded {sample_count} samples")
    
    # Verify file exists and has data
    if not Path(fname).exists():
        print(f"❌ ERROR: Session file not created: {fname}")
        return False, None
    
    file_size = Path(fname).stat().st_size
    if file_size == 0:
        print(f"❌ ERROR: Session file is empty")
        return False, None
    
    print(f"✓ Session file created ({file_size} bytes)")
    
    # Extract metadata
    metadata = extract_session_metadata(fname)
    print(f"\nExtracted metadata:")
    print(f"  Car: {metadata['car']}")
    print(f"  Track: {metadata['track']}")
    print(f"  Duration: {metadata['duration']:.2f}s")
    print(f"  Sample count: {metadata['sample_count']}")
    
    return True, fname


def test_upload(backend_url="http://localhost:8000"):
    """Test uploading a session to the backend."""
    print("\n" + "=" * 60)
    print("Testing Upload Function")
    print("=" * 60)
    
    # First, create a test session
    success, session_path = test_session_recording()
    if not success:
        print("❌ Cannot test upload - session recording failed")
        return False
    
    print(f"\nAttempting to upload {session_path} to {backend_url}...")
    
    try:
        result = upload_session(
            session_path=session_path,
            backend_url=backend_url,
            driver_name="Test Driver"
        )
        
        if result:
            print("✓ Upload successful!")
            print(f"  Session ID: {result.get('id', 'N/A')}")
            print(f"  Driver: {result.get('driver_name', 'N/A')}")
            print(f"  Car: {result.get('car', 'N/A')}")
            print(f"  Track: {result.get('track', 'N/A')}")
            print(f"  Duration: {result.get('duration', 'N/A'):.2f}s")
            return True
        else:
            print("❌ Upload failed - no response from backend")
            print("  Make sure the backend is running:")
            print(f"    cd backend && uvicorn app.main:app --reload")
            return False
    
    except Exception as e:
        print(f"❌ Upload error: {e}")
        print("\n  Make sure:")
        print("  1. Backend is running (uvicorn app.main:app)")
        print("  2. Database is configured correctly")
        print("  3. Backend URL is correct")
        return False


def main():
    print("\n" + "=" * 60)
    print("Telemetry App Feature Tests")
    print("=" * 60)
    
    results = {}
    
    # Test 1: Simulator features
    results["simulator"] = test_simulator_features()
    
    # Test 2: Session recording
    results["recording"] = test_session_recording()[0]
    
    # Test 3: Upload (optional - requires backend)
    print("\n" + "=" * 60)
    print("Upload Test (requires backend running)")
    print("=" * 60)
    print("\nTo test upload, make sure backend is running:")
    print("  cd backend")
    print("  uvicorn app.main:app --reload")
    print("\nThen run this test again or test manually with:")
    print("  python tools/upload_session.py")
    
    response = input("\nDo you want to test upload now? (y/n): ").strip().lower()
    if response == 'y':
        backend_url = input("Backend URL (default: http://localhost:8000): ").strip()
        if not backend_url:
            backend_url = "http://localhost:8000"
        results["upload"] = test_upload(backend_url)
    else:
        results["upload"] = None
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    for test_name, result in results.items():
        if result is None:
            status = "⏭️  Skipped"
        elif result:
            status = "✓ PASSED"
        else:
            status = "❌ FAILED"
        print(f"  {test_name:20s}: {status}")
    
    all_passed = all(r for r in results.values() if r is not None)
    if all_passed:
        print("\n✓ All tests passed!")
    else:
        print("\n⚠️  Some tests failed. Check the output above.")


if __name__ == "__main__":
    main()

