# Face Attendance System

FastAPI-based face recognition attendance for schools. Uses InsightFace for recognition and MediaPipe Face Mesh for basic liveness (blink/mouth variation).

## Features
- Registration: capture multiple images from webcam in browser and enroll a student
- Live recognition: continuous frame capture from webcam, cosine-similarity matching
- Attendance sessions: group recognitions by session code
- Liveness check: simple blink/mouth movement heuristic to prevent static photo spoofing

## Requirements
- Python 3.10+
- System packages for OpenCV if running locally: `libgl1`, `libglib2.0-0`

## Setup (local)
```
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Open `http://localhost:8000` in your browser.

If you get errors creating the venv on Debian/Ubuntu, install:
```
sudo apt-get update && sudo apt-get install -y python3-venv python3-pip libgl1 libglib2.0-0 build-essential
```

## Docker (optional)
Create a `Dockerfile` similar to:
```
FROM python:3.11-slim
RUN apt-get update && apt-get install -y libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```
Then build and run:
```
docker build -t face-attendance .
docker run --rm -p 8000:8000 face-attendance
```

## Notes
- First run will download InsightFace models; ensure internet access.
- Similarity threshold is set to 0.45; adjust in `app/main.py` based on your environment and enrollment quality.
- For production, add authentication, HTTPS, and a more robust liveness check.