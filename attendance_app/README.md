## Face Recognition Attendance System (School)

Features:
- Face registration for students and teachers
- Teacher IN/OUT with liveness check
- Real-time recognition from webcam with liveness
- Attendance logs, class rosters, admin dashboard

Quick start
1) Install deps (system Python):
```
pip3 install --break-system-packages -r requirements.txt
```
2) Run server:
```
PYTHONPATH=./ python3 -m uvicorn attendance_app.app.main:app --reload --host 0.0.0.0 --port 8000
```
3) Open `http://localhost:8000` in your browser.

Docker
```
docker build -t attendance-app:latest .
docker run --rm -it -p 8000:8000 -v $(pwd)/app/data:/app/app/data attendance-app:latest
```

Docker Compose
```
docker compose up --build
```

Publish (GitHub)
```
cd attendance_app
git init
git add .
git commit -m "Initial commit: Face attendance app"
# Create new GitHub repo first, then:
git remote add origin https://github.com/<you>/<repo>.git
git branch -M main
git push -u origin main
```

CI (GitHub Actions)
- Workflow at `.github/workflows/docker-publish.yml` builds the Docker image on push to `main`.
- To push to a registry, configure secrets and set `push: true`.

Notes
- Uses OpenCV LBPH face recognizer and simple liveness (blur + eyes heuristic).
- Models and data are stored under `app/data/`.