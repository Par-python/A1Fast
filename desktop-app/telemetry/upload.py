# telemetry/upload.py
"""
Upload session files to FastAPI backend.
"""
import os
import gzip
import json
import requests
from pathlib import Path
from typing import Optional, Dict, Any


def extract_session_metadata(session_path: str) -> Dict[str, Any]:
    """
    Extract metadata from a session file by reading the first and last samples.
    Returns dict with car, track, duration, and sample count.
    """
    metadata = {
        "car": "Unknown",
        "track": "Unknown",
        "duration": 0.0,
        "sample_count": 0,
        "first_ts": None,
        "last_ts": None,
    }
    
    try:
        with gzip.open(session_path, "rt", encoding="utf-8") as f:
            first = None
            last = None
            count = 0
            
            for line in f:
                try:
                    obj = json.loads(line)
                    if first is None:
                        first = obj
                    last = obj
                    count += 1
                except json.JSONDecodeError:
                    continue
            
            if first and last:
                metadata["car"] = first.get("car", last.get("car", "Unknown"))
                metadata["track"] = first.get("track", last.get("track", "Unknown"))
                metadata["sample_count"] = count
                
                first_ts = first.get("ts")
                last_ts = last.get("ts")
                if first_ts and last_ts:
                    metadata["first_ts"] = first_ts
                    metadata["last_ts"] = last_ts
                    metadata["duration"] = last_ts - first_ts
    
    except Exception as e:
        print(f"Error extracting metadata: {e}")
    
    return metadata


def upload_session(
    session_path: str,
    backend_url: str = "http://localhost:8000",
    driver_name: str = "Default Driver",
    timeout: int = 60
) -> Optional[Dict[str, Any]]:
    """
    Upload a session file to the FastAPI backend.
    
    Args:
        session_path: Path to the .jsonl.gz session file
        backend_url: Base URL of the FastAPI backend
        driver_name: Name of the driver
        timeout: Request timeout in seconds
    
    Returns:
        Response dict from the backend, or None on error
    """
    if not os.path.exists(session_path):
        raise FileNotFoundError(f"Session file not found: {session_path}")
    
    # Extract metadata from the session file
    metadata = extract_session_metadata(session_path)
    
    # Prepare the upload
    upload_url = f"{backend_url}/sessions/upload"
    
    try:
        with open(session_path, "rb") as f:
            files = {
                "file": (os.path.basename(session_path), f, "application/gzip")
            }
            data = {
                "driver_name": driver_name,
                "car": metadata["car"],
                "track": metadata["track"],
                "duration": metadata["duration"],
            }
            
            response = requests.post(
                upload_url,
                files=files,
                data=data,
                timeout=timeout
            )
            response.raise_for_status()
            return response.json()
    
    except requests.exceptions.RequestException as e:
        print(f"Upload failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                print(f"Response: {e.response.text}")
            except:
                pass
        return None
    except Exception as e:
        print(f"Unexpected error during upload: {e}")
        return None


def list_session_files(sessions_dir: str = "sessions") -> list:
    """
    List all session files in the sessions directory.
    Returns list of file paths sorted by modification time (newest first).
    """
    sessions_path = Path(sessions_dir)
    if not sessions_path.exists():
        return []
    
    files = sorted(
        sessions_path.glob("session_*.jsonl.gz"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    return [str(f) for f in files]

