# Testing Guide

This guide explains how to test the new features: **Upload Function** and **Lap Timing/Realism**.

## Quick Test

Run the automated test script:

```bash
cd desktop-app
python tools/test_features.py
```

This will test:
1. Simulator features (sectors, pitlane, curves)
2. Session recording
3. Upload functionality (optional, requires backend)

## Manual Testing

### 1. Test Simulator Features (Sectors, Pitlane, Curves)

#### Option A: Using the Desktop App UI

1. Start the desktop app:
   ```bash
   cd desktop-app
   python main.py
   ```

2. Click "Start Listener"
3. Click "Start ACC Simulator"
4. Click "Start Session Recording"
5. Let it run for a few seconds, then click "Stop Session Recording"
6. Check the session file in `desktop-app/sessions/` - it should contain:
   - `sector` (1, 2, or 3)
   - `sector_time_s`
   - `best_lap_time_s`
   - `best_sector_1_s`, `best_sector_2_s`, `best_sector_3_s`
   - `in_pitlane` (boolean)
   - `is_curve` (boolean)

#### Option B: Using Command Line

```bash
cd desktop-app
python tools/run_sim_and_listener.py 10  # Run for 10 seconds
```

Then inspect the session:
```bash
python tools/inspect_session.py
```

You should see telemetry data with the new fields.

### 2. Test Upload Function

#### Prerequisites

1. **Start the Backend:**
   ```bash
   cd backend
   
   # Make sure you have a .env file or set DATABASE_URL
   # For SQLite (simpler for testing):
   # DATABASE_URL=sqlite:///./telemetry.db
   
   uvicorn app.main:app --reload
   ```

2. The backend should be running at `http://localhost:8000`

#### Option A: Using the Desktop App UI

1. Record a session (see above)
2. In the UI, enter:
   - Driver Name: "Test Driver"
   - Backend URL: "http://localhost:8000"
3. Click "Upload Last Session"
4. You should see a success message with session details

#### Option B: Using Command Line

```bash
cd desktop-app

# Upload the latest session
python tools/upload_session.py

# Or upload a specific session
python tools/upload_session.py sessions/session_20251106_112903.jsonl.gz --driver "My Name"

# Or specify a different backend
python tools/upload_session.py --backend http://localhost:8000 --driver "Test Driver"
```

#### Verify Upload

1. **Check Backend Response:**
   ```bash
   curl http://localhost:8000/sessions/
   ```

2. **Or visit in browser:**
   ```
   http://localhost:8000/sessions/
   ```

3. **Check uploaded files:**
   ```bash
   ls backend/uploads/sessions/
   ```

### 3. Test Backend Endpoints

#### List all sessions:
```bash
curl http://localhost:8000/sessions/
```

#### Get specific session:
```bash
curl http://localhost:8000/sessions/1
```

#### Upload via curl:
```bash
curl -X POST "http://localhost:8000/sessions/upload" \
  -F "file=@desktop-app/sessions/session_20251106_112903.jsonl.gz" \
  -F "driver_name=Test Driver" \
  -F "car=Porsche GT3 RS" \
  -F "track=Monza" \
  -F "duration=10.5"
```

## Expected Results

### Simulator Telemetry Should Include:

```json
{
  "source": "SIM",
  "car": "Porsche GT3 RS",
  "track": "Monza",
  "lap": 1,
  "segment": "Rettifilo",
  "sector": 1,
  "position_m": 123.45,
  "lap_time_s": 45.123,
  "sector_time_s": 15.456,
  "best_lap_time_s": null,
  "best_sector_1_s": null,
  "best_sector_2_s": null,
  "best_sector_3_s": null,
  "speed": 250.5,
  "rpm": 7500,
  "throttle": 85.2,
  "brake": 0.0,
  "gear": 5,
  "steer": 0.05,
  "in_pitlane": false,
  "is_curve": false,
  "ts": 1699123456.789
}
```

### Upload Response Should Include:

```json
{
  "id": 1,
  "filename": "Test_Driver_20251106_120000_session_20251106_112903.jsonl.gz",
  "file_path": "uploads/sessions/...",
  "driver_name": "Test Driver",
  "car": "Porsche GT3 RS",
  "track": "Monza",
  "duration": 10.5,
  "upload_time": "2025-11-06T12:00:00",
  "message": "Session uploaded successfully"
}
```

## Troubleshooting

### Backend won't start:
- Check database connection in `.env` file
- For quick testing, use SQLite: `DATABASE_URL=sqlite:///./telemetry.db`
- Make sure port 8000 is not in use

### Upload fails:
- Verify backend is running: `curl http://localhost:8000/`
- Check backend logs for errors
- Verify file path is correct
- Check network connectivity

### Simulator not producing new fields:
- Make sure you're using the updated `simulator.py`
- Check that you're reading from a new session file (old files won't have new fields)
- Verify the simulator is actually running

### Database errors:
- Make sure database is initialized: backend should auto-create tables on startup
- Check `DATABASE_URL` in `.env` or `config.py`
- For PostgreSQL, ensure database exists: `createdb telemetry`

## Next Steps

Once testing is complete:
1. Record longer sessions to see sector times improve
2. Test pitlane entry (currently random, can be triggered manually)
3. Upload multiple sessions and view them via the backend API
4. Integrate with frontend to visualize the data

