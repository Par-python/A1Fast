from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from sqlmodel import Session as DBSession, select
from datetime import datetime
import shutil
from pathlib import Path
from ..models import Session
from ..schemas import SessionCreate
from ..db import engine

router = APIRouter()

# Directory to store uploaded session files
UPLOAD_DIR = Path("uploads/sessions")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/upload")
async def upload_session(
    file: UploadFile = File(...),
    driver_name: str = Form(...),
    car: str = Form(...),
    track: str = Form(...),
    duration: float = Form(...)
):
    """
    Upload a session file and store metadata in the database.
    The file is saved locally (can be extended to S3 later).
    """
    try:
        # Validate file extension
        if not file.filename or not file.filename.endswith(('.jsonl.gz', '.gz')):
            raise HTTPException(status_code=400, detail="File must be a .jsonl.gz file")
        
        # Generate unique filename with timestamp
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{driver_name.replace(' ', '_')}_{timestamp}_{file.filename}"
        file_path = UPLOAD_DIR / safe_filename
        
        # Save the file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Store metadata in database
        session_record = Session(
            driver_name=driver_name,
            car=car,
            track=track,
            duration=duration,
            upload_time=datetime.utcnow()
        )
        
        with DBSession(engine) as db:
            db.add(session_record)
            db.commit()
            db.refresh(session_record)
        
        return {
            "id": session_record.id,
            "filename": safe_filename,
            "file_path": str(file_path),
            "driver_name": driver_name,
            "car": car,
            "track": track,
            "duration": duration,
            "upload_time": session_record.upload_time.isoformat(),
            "message": "Session uploaded successfully"
        }
    
    except Exception as e:
        # Clean up file if database insert failed
        if 'file_path' in locals() and file_path.exists():
            try:
                file_path.unlink()
            except:
                pass
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/")
async def list_sessions():
    """List all uploaded sessions."""
    with DBSession(engine) as db:
        statement = select(Session)
        sessions = db.exec(statement).all()
        return [
            {
                "id": s.id,
                "driver_name": s.driver_name,
                "car": s.car,
                "track": s.track,
                "duration": s.duration,
                "upload_time": s.upload_time.isoformat() if s.upload_time else None,
            }
            for s in sessions
        ]


@router.get("/{session_id}")
async def get_session(session_id: int):
    """Get a specific session by ID."""
    with DBSession(engine) as db:
        session = db.get(Session, session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return {
            "id": session.id,
            "driver_name": session.driver_name,
            "car": session.car,
            "track": session.track,
            "duration": session.duration,
            "upload_time": session.upload_time.isoformat() if session.upload_time else None,
        }
