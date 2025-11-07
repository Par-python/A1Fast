# tools/upload_session.py
"""
CLI tool to upload session files to the FastAPI backend.
"""
import sys
import argparse
from pathlib import Path

# Fix import path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from telemetry.upload import upload_session, list_session_files


def main():
    parser = argparse.ArgumentParser(description="Upload telemetry session files to backend")
    parser.add_argument(
        "session_file",
        nargs="?",
        help="Path to session file (.jsonl.gz). If not provided, uploads the latest session."
    )
    parser.add_argument(
        "--driver",
        default="Default Driver",
        help="Driver name (default: 'Default Driver')"
    )
    parser.add_argument(
        "--backend",
        default="http://localhost:8000",
        help="Backend URL (default: http://localhost:8000)"
    )
    
    args = parser.parse_args()
    
    # Determine session file
    if args.session_file:
        session_path = args.session_file
        if not Path(session_path).exists():
            print(f"Error: Session file not found: {session_path}")
            sys.exit(1)
    else:
        # Find latest session
        sessions = list_session_files()
        if not sessions:
            print("Error: No session files found. Please provide a session file path.")
            sys.exit(1)
        session_path = sessions[0]
        print(f"Using latest session: {session_path}")
    
    # Upload
    print(f"Uploading session to {args.backend}...")
    print(f"Driver: {args.driver}")
    print(f"File: {session_path}")
    
    result = upload_session(
        session_path=session_path,
        backend_url=args.backend,
        driver_name=args.driver
    )
    
    if result:
        print("\n✓ Upload successful!")
        print(f"  Session ID: {result.get('id', 'N/A')}")
        print(f"  Driver: {result.get('driver_name', 'N/A')}")
        print(f"  Car: {result.get('car', 'N/A')}")
        print(f"  Track: {result.get('track', 'N/A')}")
        print(f"  Duration: {result.get('duration', 'N/A'):.2f}s")
    else:
        print("\n✗ Upload failed. Check backend connection and try again.")
        sys.exit(1)


if __name__ == "__main__":
    main()

