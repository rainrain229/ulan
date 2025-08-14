## Face Recognition Attendance System (School)

Features:
- Face registration for students and teachers
- Teacher IN/OUT with liveness check
- Real-time recognition from webcam with liveness
- Attendance logs, class rosters, admin dashboard

Quick start
1) Create venv and install deps:
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
2) Run server:
```
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
3) Open `http://localhost:8000` in your browser.

Notes
- Uses OpenCV LBPH face recognizer and MediaPipe for liveness signals (eye blink/head pose heuristics).
- Models and data are stored under `data/`.