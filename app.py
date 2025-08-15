from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Response
from flask_sqlalchemy import SQLAlchemy
import cv2
import face_recognition
import numpy as np
import os
import pickle
from datetime import datetime, date, timedelta
import pandas as pd
from werkzeug.utils import secure_filename
import base64
from io import BytesIO
from PIL import Image

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///attendance.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/student_images'

db = SQLAlchemy(app)

# Create upload directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('static/teacher_images', exist_ok=True)
os.makedirs('encodings', exist_ok=True)

# Database Models
class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    class_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    image_path = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    attendances = db.relationship('Attendance', backref='student', lazy=True)

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), db.ForeignKey('student.student_id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time_in = db.Column(db.DateTime)
    time_out = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='Present')

# --- New: Teacher models ---
class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(100))
    email = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    image_path = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    attendances = db.relationship('TeacherAttendance', backref='teacher', lazy=True)

class TeacherAttendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.String(20), db.ForeignKey('teacher.teacher_id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time_in = db.Column(db.DateTime)
    time_out = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='Present')

# Global variables
known_face_encodings = []
known_face_labels = []  # labels like "S:<student_id>" or "T:<teacher_id>"
id_to_student_name = {}
id_to_teacher_name = {}

camera = None

# Liveness detection resources
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')

# Last recognized cache for teacher controls
last_teacher_recognized = {
    'teacher_id': None,
    'name': None,
    'timestamp': None
}


def load_known_faces():
    """Load all known face encodings for students and teachers from the database"""
    global known_face_encodings, known_face_labels, id_to_student_name, id_to_teacher_name
    
    known_face_encodings = []
    known_face_labels = []
    id_to_student_name = {}
    id_to_teacher_name = {}
    
    # Students
    students = Student.query.all()
    for student in students:
        if student.image_path and os.path.exists(student.image_path):
            try:
                image = face_recognition.load_image_file(student.image_path)
                encodings = face_recognition.face_encodings(image)
                if encodings:
                    known_face_encodings.append(encodings[0])
                    known_face_labels.append(f"S:{student.student_id}")
                    id_to_student_name[student.student_id] = student.name
            except Exception as e:
                print(f"Error loading face for student {student.name}: {e}")

    # Teachers
    teachers = Teacher.query.all()
    for teacher in teachers:
        if teacher.image_path and os.path.exists(teacher.image_path):
            try:
                image = face_recognition.load_image_file(teacher.image_path)
                encodings = face_recognition.face_encodings(image)
                if encodings:
                    known_face_encodings.append(encodings[0])
                    known_face_labels.append(f"T:{teacher.teacher_id}")
                    id_to_teacher_name[teacher.teacher_id] = teacher.name
            except Exception as e:
                print(f"Error loading face for teacher {teacher.name}: {e}")


def mark_student_attendance(student_id):
    """Mark attendance for a student (time in/out toggle for the day)"""
    today = date.today()
    
    existing_attendance = Attendance.query.filter_by(
        student_id=student_id, 
        date=today
    ).first()
    
    if existing_attendance:
        if not existing_attendance.time_out:
            existing_attendance.time_out = datetime.now()
            db.session.commit()
            return f"Student time out marked for {student_id}"
        else:
            return f"Student attendance already complete for {student_id}"
    else:
        new_attendance = Attendance(
            student_id=student_id,
            date=today,
            time_in=datetime.now()
        )
        db.session.add(new_attendance)
        db.session.commit()
        return f"Student time in marked for {student_id}"

# --- New: Teacher IN/OUT helpers ---
def teacher_check_in(teacher_id: str):
    today = date.today()
    # If there is an open session (no time_out) for today, do nothing
    open_session = TeacherAttendance.query.filter_by(teacher_id=teacher_id, date=today, time_out=None).first()
    if open_session:
        return f"Teacher {teacher_id} already checked in"
    entry = TeacherAttendance(teacher_id=teacher_id, date=today, time_in=datetime.now())
    db.session.add(entry)
    db.session.commit()
    return f"Teacher {teacher_id} checked IN"


def teacher_check_out(teacher_id: str):
    today = date.today()
    open_session = TeacherAttendance.query.filter_by(teacher_id=teacher_id, date=today, time_out=None).order_by(TeacherAttendance.time_in.desc()).first()
    if not open_session:
        return f"No open IN session for teacher {teacher_id}"
    open_session.time_out = datetime.now()
    db.session.commit()
    return f"Teacher {teacher_id} checked OUT"


def _compute_liveness(frame_bgr, face_location):
    """Simple liveness based on sharpness + eye detection on face ROI."""
    try:
        top, right, bottom, left = face_location
        # Coordinates are on the downscaled image; scale up to original 1x frame used for drawing
        # In our pipeline, face_location values are from the small RGB frame; caller should pass scaled coords
        roi = frame_bgr[top:bottom, left:right]
        if roi.size == 0:
            return False
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        if lap_var < 30.0:
            return False
        h = gray.shape[0]
        upper = gray[: h // 2, :]
        eyes = eye_cascade.detectMultiScale(upper, scaleFactor=1.2, minNeighbors=5, minSize=(15, 15))
        return len(eyes) >= 1
    except Exception:
        return False


def generate_frames(mode='student'):
    """Generate video frames for live feed with recognition. Mode: 'student' or 'teacher'."""
    global camera, last_teacher_recognized
    
    if camera is None:
        camera = cv2.VideoCapture(0)
    
    while True:
        success, frame = camera.read()
        if not success:
            break
        
        # Resize frame for faster processing
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        rgb_small_frame = small_frame[:, :, ::-1]
        
        # Find faces and encodings
        face_locations = face_recognition.face_locations(rgb_small_frame)
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
        
        for face_encoding, face_location in zip(face_encodings, face_locations):
            matches = face_recognition.compare_faces(known_face_encodings, face_encoding, tolerance=0.6)
            name_label = "Unknown"
            label_role = None
            entity_id = None
            
            if True in matches:
                first_match_index = matches.index(True)
                name_label = known_face_labels[first_match_index]
                try:
                    label_role, entity_id = name_label.split(':', 1)
                except ValueError:
                    label_role, entity_id = None, None
                
                # Scale back up face locations for drawing and liveness ROI
                top, right, bottom, left = face_location
                top *= 4; right *= 4; bottom *= 4; left *= 4
                
                live_ok = _compute_liveness(frame, (top, right, bottom, left))
                overlay_name = name_label
                if label_role == 'S':
                    display = id_to_student_name.get(entity_id, entity_id)
                    overlay_name = f"Student: {display}"
                    if mode == 'student' and live_ok:
                        result = mark_student_attendance(entity_id)
                        print(result)
                elif label_role == 'T':
                    display = id_to_teacher_name.get(entity_id, entity_id)
                    overlay_name = f"Teacher: {display}{'' if live_ok else ' (liveness failed)'}"
                    if live_ok:
                        last_teacher_recognized = {
                            'teacher_id': entity_id,
                            'name': display,
                            'timestamp': datetime.utcnow()
                        }
                
                # Draw rectangle and label
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0) if name_label != 'Unknown' else (0, 0, 255), 2)
                cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 255, 0) if name_label != 'Unknown' else (0, 0, 255), cv2.FILLED)
                cv2.putText(frame, overlay_name, (left + 6, bottom - 8), cv2.FONT_HERSHEY_DUPLEX, 0.7, (255, 255, 255), 1)
            else:
                # Unknown face drawing
                top, right, bottom, left = face_location
                top *= 4; right *= 4; bottom *= 4; left *= 4
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
                cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)
                cv2.putText(frame, name_label, (left + 6, bottom - 8), cv2.FONT_HERSHEY_DUPLEX, 0.7, (255, 255, 255), 1)
        
        # Encode frame to bytes
        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/students')
def students():
    all_students = Student.query.all()
    return render_template('students.html', students=all_students)

@app.route('/add_student', methods=['GET', 'POST'])
def add_student():
    if request.method == 'POST':
        student_id = request.form['student_id']
        name = request.form['name']
        class_name = request.form['class_name']
        email = request.form.get('email', '')
        phone = request.form.get('phone', '')
        
        existing_student = Student.query.filter_by(student_id=student_id).first()
        if existing_student:
            flash('Student ID already exists!', 'error')
            return redirect(url_for('add_student'))
        
        if 'image' not in request.files:
            flash('No image file provided!', 'error')
            return redirect(url_for('add_student'))
        
        file = request.files['image']
        if file.filename == '':
            flash('No image file selected!', 'error')
            return redirect(url_for('add_student'))
        
        if file:
            filename = secure_filename(f"{student_id}_{file.filename}")
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            try:
                image = face_recognition.load_image_file(file_path)
                face_encodings = face_recognition.face_encodings(image)
                if not face_encodings:
                    os.remove(file_path)
                    flash('No face detected in the image! Please upload a clear photo.', 'error')
                    return redirect(url_for('add_student'))
            except Exception as e:
                if os.path.exists(file_path):
                    os.remove(file_path)
                flash(f'Error processing image: {e}', 'error')
                return redirect(url_for('add_student'))
            
            new_student = Student(
                student_id=student_id,
                name=name,
                class_name=class_name,
                email=email,
                phone=phone,
                image_path=file_path
            )
            
            db.session.add(new_student)
            db.session.commit()
            
            load_known_faces()
            
            flash('Student added successfully!', 'success')
            return redirect(url_for('students'))
    
    return render_template('add_student.html')

# --- New: Teacher CRUD ---
@app.route('/teachers')
def teachers():
    all_teachers = Teacher.query.all()
    return render_template('teachers.html', teachers=all_teachers)

@app.route('/add_teacher', methods=['GET', 'POST'])
def add_teacher():
    if request.method == 'POST':
        teacher_id = request.form['teacher_id']
        name = request.form['name']
        department = request.form.get('department', '')
        email = request.form.get('email', '')
        phone = request.form.get('phone', '')
        
        existing_teacher = Teacher.query.filter_by(teacher_id=teacher_id).first()
        if existing_teacher:
            flash('Teacher ID already exists!', 'error')
            return redirect(url_for('add_teacher'))
        
        if 'image' not in request.files:
            flash('No image file provided!', 'error')
            return redirect(url_for('add_teacher'))
        file = request.files['image']
        if file.filename == '':
            flash('No image file selected!', 'error')
            return redirect(url_for('add_teacher'))
        
        if file:
            filename = secure_filename(f"{teacher_id}_{file.filename}")
            save_dir = 'static/teacher_images'
            file_path = os.path.join(save_dir, filename)
            file.save(file_path)
            
            try:
                image = face_recognition.load_image_file(file_path)
                face_encodings = face_recognition.face_encodings(image)
                if not face_encodings:
                    os.remove(file_path)
                    flash('No face detected in the image! Please upload a clear photo.', 'error')
                    return redirect(url_for('add_teacher'))
            except Exception as e:
                if os.path.exists(file_path):
                    os.remove(file_path)
                flash(f'Error processing image: {e}', 'error')
                return redirect(url_for('add_teacher'))
            
            new_teacher = Teacher(
                teacher_id=teacher_id,
                name=name,
                department=department,
                email=email,
                phone=phone,
                image_path=file_path
            )
            db.session.add(new_teacher)
            db.session.commit()
            
            load_known_faces()
            
            flash('Teacher added successfully!', 'success')
            return redirect(url_for('teachers'))
    
    return render_template('add_teacher.html')

@app.route('/delete_teacher/<teacher_id>')
def delete_teacher(teacher_id):
    teacher = Teacher.query.filter_by(teacher_id=teacher_id).first()
    if teacher:
        if teacher.image_path and os.path.exists(teacher.image_path):
            os.remove(teacher.image_path)
        TeacherAttendance.query.filter_by(teacher_id=teacher_id).delete()
        db.session.delete(teacher)
        db.session.commit()
        load_known_faces()
        flash('Teacher deleted successfully!', 'success')
    else:
        flash('Teacher not found!', 'error')
    return redirect(url_for('teachers'))

# --- Existing attendance view remains for students ---
@app.route('/attendance')
def attendance():
    selected_date = request.args.get('date', date.today().strftime('%Y-%m-%d'))
    selected_class = request.args.get('class', '')
    
    query = db.session.query(Attendance, Student).join(Student)
    
    if selected_date:
        query = query.filter(Attendance.date == selected_date)
    
    if selected_class:
        query = query.filter(Student.class_name == selected_class)
    
    attendance_records = query.all()
    
    classes = db.session.query(Student.class_name).distinct().all()
    classes = [c[0] for c in classes]
    
    return render_template('attendance.html', 
                         attendance_records=attendance_records,
                         selected_date=selected_date,
                         selected_class=selected_class,
                         classes=classes)

# --- New: Teacher attendance views ---
@app.route('/teacher_attendance')
def teacher_attendance():
    selected_date = request.args.get('date', date.today().strftime('%Y-%m-%d'))
    selected_department = request.args.get('department', '')

    query = db.session.query(TeacherAttendance, Teacher).join(Teacher)
    if selected_date:
        query = query.filter(TeacherAttendance.date == selected_date)
    if selected_department:
        query = query.filter(Teacher.department == selected_department)
    attendance_records = query.all()

    departments = db.session.query(Teacher.department).distinct().all()
    departments = [d[0] for d in departments if d[0]]

    return render_template('teacher_attendance.html',
                           attendance_records=attendance_records,
                           selected_date=selected_date,
                           selected_department=selected_department,
                           departments=departments)

@app.route('/export_teacher_attendance')
def export_teacher_attendance():
    selected_date = request.args.get('date', date.today().strftime('%Y-%m-%d'))
    query = db.session.query(TeacherAttendance, Teacher).join(Teacher)
    query = query.filter(TeacherAttendance.date == selected_date)
    attendance_records = query.all()

    data = []
    for attendance_row, teacher in attendance_records:
        data.append({
            'Teacher ID': teacher.teacher_id,
            'Name': teacher.name,
            'Department': teacher.department or '',
            'Date': attendance_row.date,
            'Time In': attendance_row.time_in.strftime('%H:%M:%S') if attendance_row.time_in else '',
            'Time Out': attendance_row.time_out.strftime('%H:%M:%S') if attendance_row.time_out else '',
            'Status': attendance_row.status
        })
    df = pd.DataFrame(data)
    filename = f"teacher_attendance_{selected_date}.csv"
    csv_path = os.path.join('static', filename)
    df.to_csv(csv_path, index=False)
    return redirect(url_for('static', filename=filename))

@app.route('/live_feed')
def live_feed():
    return render_template('live_feed.html')

@app.route('/video_feed')
def video_feed():
    mode = request.args.get('mode', 'student')
    return Response(generate_frames(mode),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# --- New: Teacher IN/OUT API ---
@app.route('/api/teacher_in', methods=['POST'])
def api_teacher_in():
    teacher_id = request.form.get('teacher_id')
    if not teacher_id:
        # fallback to last recognized within 10 seconds
        if last_teacher_recognized['teacher_id'] and last_teacher_recognized['timestamp'] and \
           datetime.utcnow() - last_teacher_recognized['timestamp'] < timedelta(seconds=10):
            teacher_id = last_teacher_recognized['teacher_id']
    if not teacher_id:
        return jsonify({'ok': False, 'error': 'No teacher identified'}), 400
    msg = teacher_check_in(teacher_id)
    return jsonify({'ok': True, 'message': msg})

@app.route('/api/teacher_out', methods=['POST'])
def api_teacher_out():
    teacher_id = request.form.get('teacher_id')
    if not teacher_id:
        if last_teacher_recognized['teacher_id'] and last_teacher_recognized['timestamp'] and \
           datetime.utcnow() - last_teacher_recognized['timestamp'] < timedelta(seconds=10):
            teacher_id = last_teacher_recognized['teacher_id']
    if not teacher_id:
        return jsonify({'ok': False, 'error': 'No teacher identified'}), 400
    msg = teacher_check_out(teacher_id)
    return jsonify({'ok': True, 'message': msg})

@app.route('/api/last_recognized_teacher')
def api_last_recognized_teacher():
    if last_teacher_recognized['teacher_id'] and last_teacher_recognized['timestamp'] and \
       datetime.utcnow() - last_teacher_recognized['timestamp'] < timedelta(seconds=10):
        return jsonify({
            'ok': True,
            'teacher_id': last_teacher_recognized['teacher_id'],
            'name': last_teacher_recognized['name'],
            'seen_at': last_teacher_recognized['timestamp'].isoformat()
        })
    return jsonify({'ok': False})

@app.route('/export_attendance')
def export_attendance():
    selected_date = request.args.get('date', date.today().strftime('%Y-%m-%d'))
    
    query = db.session.query(Attendance, Student).join(Student)
    query = query.filter(Attendance.date == selected_date)
    attendance_records = query.all()
    
    data = []
    for attendance, student in attendance_records:
        data.append({
            'Student ID': student.student_id,
            'Name': student.name,
            'Class': student.class_name,
            'Date': attendance.date,
            'Time In': attendance.time_in.strftime('%H:%M:%S') if attendance.time_in else '',
            'Time Out': attendance.time_out.strftime('%H:%M:%S') if attendance.time_out else '',
            'Status': attendance.status
        })
    
    df = pd.DataFrame(data)
    
    filename = f"attendance_{selected_date}.csv"
    csv_path = os.path.join('static', filename)
    df.to_csv(csv_path, index=False)
    
    return redirect(url_for('static', filename=filename))

@app.route('/delete_student/<student_id>')
def delete_student(student_id):
    student = Student.query.filter_by(student_id=student_id).first()
    if student:
        if student.image_path and os.path.exists(student.image_path):
            os.remove(student.image_path)
        Attendance.query.filter_by(student_id=student_id).delete()
        db.session.delete(student)
        db.session.commit()
        load_known_faces()
        flash('Student deleted successfully!', 'success')
    else:
        flash('Student not found!', 'error')
    
    return redirect(url_for('students'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        load_known_faces()
    app.run(debug=True, host='0.0.0.0', port=5000)