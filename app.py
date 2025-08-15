from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Response, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
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
import json
import hashlib
import secrets
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(32)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///attendance.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/student_images'
app.config['TEACHER_IMAGES'] = 'static/teacher_images'

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

db = SQLAlchemy(app)

# Create upload directories if they don't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['TEACHER_IMAGES'], exist_ok=True)
os.makedirs('encodings', exist_ok=True)
os.makedirs('logs', exist_ok=True)

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), default='teacher')  # 'admin' or 'teacher'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    department = db.Column(db.String(100))
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
    location = db.Column(db.String(100))  # For future GPS tracking

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
    confidence_score = db.Column(db.Float)  # Face recognition confidence
    location = db.Column(db.String(100))  # For future GPS tracking

class Class(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    class_name = db.Column(db.String(50), unique=True, nullable=False)
    teacher_id = db.Column(db.String(20), db.ForeignKey('teacher.teacher_id'))
    schedule = db.Column(db.Text)  # JSON string for class schedule
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Global variables
known_face_encodings = []
known_face_names = []
known_face_types = []  # 'student' or 'teacher'
camera = None
last_attendance_time = {}  # Prevent duplicate attendance marking

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Admin access required!', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def load_known_faces():
    """Load all known face encodings from the database"""
    global known_face_encodings, known_face_names, known_face_types
    
    known_face_encodings = []
    known_face_names = []
    known_face_types = []
    
    # Load students
    students = Student.query.all()
    for student in students:
        if student.image_path and os.path.exists(student.image_path):
            try:
                image = face_recognition.load_image_file(student.image_path)
                encodings = face_recognition.face_encodings(image)
                if encodings:
                    known_face_encodings.append(encodings[0])
                    known_face_names.append(student.student_id)
                    known_face_types.append('student')
            except Exception as e:
                print(f"Error loading face for student {student.name}: {e}")
    
    # Load teachers
    teachers = Teacher.query.all()
    for teacher in teachers:
        if teacher.image_path and os.path.exists(teacher.image_path):
            try:
                image = face_recognition.load_image_file(teacher.image_path)
                encodings = face_recognition.face_encodings(image)
                if encodings:
                    known_face_encodings.append(encodings[0])
                    known_face_names.append(teacher.teacher_id)
                    known_face_types.append('teacher')
            except Exception as e:
                print(f"Error loading face for teacher {teacher.name}: {e}")

def mark_attendance(person_id, person_type='student'):
    """Mark attendance for a student or teacher with anti-duplicate protection"""
    today = date.today()
    current_time = datetime.now()
    
    # Anti-duplicate protection (5 minutes cooldown)
    if person_id in last_attendance_time:
        time_diff = current_time - last_attendance_time[person_id]
        if time_diff.total_seconds() < 300:  # 5 minutes
            return f"Attendance already marked recently for {person_id}"
    
    if person_type == 'student':
        # Check if already marked today
        existing_attendance = Attendance.query.filter_by(
            student_id=person_id, 
            date=today
        ).first()
        
        if existing_attendance:
            if not existing_attendance.time_out:
                # Mark time out
                existing_attendance.time_out = current_time
                existing_attendance.status = 'Complete'
                db.session.commit()
                last_attendance_time[person_id] = current_time
                return f"Time out marked for student {person_id}"
            else:
                return f"Attendance already complete for student {person_id}"
        else:
            # Mark time in
            new_attendance = Attendance(
                student_id=person_id,
                date=today,
                time_in=current_time,
                status='Present'
            )
            db.session.add(new_attendance)
            db.session.commit()
            last_attendance_time[person_id] = current_time
            return f"Time in marked for student {person_id}"
    
    elif person_type == 'teacher':
        # Check if already marked today
        existing_attendance = TeacherAttendance.query.filter_by(
            teacher_id=person_id, 
            date=today
        ).first()
        
        if existing_attendance:
            if not existing_attendance.time_out:
                # Mark time out
                existing_attendance.time_out = current_time
                existing_attendance.status = 'Complete'
                db.session.commit()
                last_attendance_time[person_id] = current_time
                return f"Time out marked for teacher {person_id}"
            else:
                return f"Attendance already complete for teacher {person_id}"
        else:
            # Mark time in
            new_attendance = TeacherAttendance(
                teacher_id=person_id,
                date=today,
                time_in=current_time,
                status='Present'
            )
            db.session.add(new_attendance)
            db.session.commit()
            last_attendance_time[person_id] = current_time
            return f"Time in marked for teacher {person_id}"

def detect_liveness(frame):
    """Basic liveness detection to prevent photo spoofing"""
    # Convert to grayscale
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Detect eyes
    eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
    eyes = eye_cascade.detectMultiScale(gray, 1.1, 5)
    
    # Basic liveness check: multiple eye detections over frames
    if len(eyes) >= 2:
        return True
    return False

def generate_frames():
    """Generate video frames for live feed with enhanced features"""
    global camera
    
    if camera is None:
        camera = cv2.VideoCapture(0)
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    frame_count = 0
    while True:
        success, frame = camera.read()
        if not success:
            break
        
        frame_count += 1
        
        # Resize frame for faster processing
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        rgb_small_frame = small_frame[:, :, ::-1]
        
        # Find faces and encodings
        face_locations = face_recognition.face_locations(rgb_small_frame)
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
        
        # Add timestamp and frame info
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, timestamp, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.putText(frame, f"Frame: {frame_count}", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        for face_encoding, face_location in zip(face_encodings, face_locations):
            # Check if face matches known faces
            matches = face_recognition.compare_faces(known_face_encodings, face_encoding, tolerance=0.6)
            name = "Unknown"
            person_type = "unknown"
            
            if True in matches:
                first_match_index = matches.index(True)
                name = known_face_names[first_match_index]
                person_type = known_face_types[first_match_index]
                
                # Calculate confidence score
                face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
                confidence = 1 - face_distances[first_match_index]
                
                # Mark attendance if confidence is high enough
                if confidence > 0.6:
                    result = mark_attendance(name, person_type)
                    print(result)
                
                # Color coding: Green for students, Blue for teachers
                color = (0, 255, 0) if person_type == 'student' else (255, 0, 0)
                label_color = (0, 255, 0) if person_type == 'student' else (255, 0, 0)
            else:
                color = (0, 0, 255)  # Red for unknown
                label_color = (0, 0, 255)
            
            # Scale back up face locations
            top, right, bottom, left = face_location
            top *= 4
            right *= 4
            bottom *= 4
            left *= 4
            
            # Draw rectangle and label
            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
            cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
            
            # Display name and type
            display_text = f"{name} ({person_type})" if person_type != "unknown" else "Unknown"
            cv2.putText(frame, display_text, (left + 6, bottom - 6), 
                       cv2.FONT_HERSHEY_DUPLEX, 0.6, (255, 255, 255), 1)
            
            # Add confidence score if known person
            if person_type != "unknown":
                confidence_text = f"Confidence: {confidence:.2f}" if 'confidence' in locals() else ""
                cv2.putText(frame, confidence_text, (left + 6, top - 10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, label_color, 1)
        
        # Encode frame to bytes
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

# Routes
@app.route('/')
@login_required
def index():
    # Get today's statistics
    today = date.today()
    
    # Student statistics
    total_students = Student.query.count()
    present_students = Attendance.query.filter_by(date=today, status='Present').count()
    absent_students = total_students - present_students
    
    # Teacher statistics
    total_teachers = Teacher.query.count()
    present_teachers = TeacherAttendance.query.filter_by(date=today, status='Present').count()
    
    # Recent attendance
    recent_attendance = db.session.query(Attendance, Student).join(Student).filter(
        Attendance.date == today
    ).order_by(Attendance.time_in.desc()).limit(10).all()
    
    # Recent teacher attendance
    recent_teacher_attendance = db.session.query(TeacherAttendance, Teacher).join(Teacher).filter(
        TeacherAttendance.date == today
    ).order_by(TeacherAttendance.time_in.desc()).limit(10).all()
    
    return render_template('index.html',
                         total_students=total_students,
                         present_students=present_students,
                         absent_students=absent_students,
                         total_teachers=total_teachers,
                         present_teachers=present_teachers,
                         recent_attendance=recent_attendance,
                         recent_teacher_attendance=recent_teacher_attendance)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        if user and user.password_hash == hashlib.sha256(password.encode()).hexdigest():
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password!', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/students')
@login_required
def students():
    all_students = Student.query.all()
    return render_template('students.html', students=all_students)

@app.route('/add_student', methods=['GET', 'POST'])
@login_required
@admin_required
def add_student():
    if request.method == 'POST':
        student_id = request.form['student_id']
        name = request.form['name']
        class_name = request.form['class_name']
        email = request.form.get('email', '')
        phone = request.form.get('phone', '')
        
        # Check if student already exists
        existing_student = Student.query.filter_by(student_id=student_id).first()
        if existing_student:
            flash('Student ID already exists!', 'error')
            return redirect(url_for('add_student'))
        
        # Handle image upload
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
            
            # Verify face can be detected
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
            
            # Create new student
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
            
            # Reload known faces
            load_known_faces()
            
            flash('Student added successfully!', 'success')
            return redirect(url_for('students'))
    
    return render_template('add_student.html')

@app.route('/attendance')
@login_required
def attendance():
    selected_date = request.args.get('date', date.today().strftime('%Y-%m-%d'))
    selected_class = request.args.get('class', '')
    
    query = db.session.query(Attendance, Student).join(Student)
    
    if selected_date:
        query = query.filter(Attendance.date == selected_date)
    
    if selected_class:
        query = query.filter(Student.class_name == selected_class)
    
    attendance_records = query.all()
    
    # Get all classes for filter dropdown
    classes = db.session.query(Student.class_name).distinct().all()
    classes = [c[0] for c in classes]
    
    return render_template('attendance.html', 
                         attendance_records=attendance_records,
                         selected_date=selected_date,
                         selected_class=selected_class,
                         classes=classes)

@app.route('/live_feed')
@login_required
def live_feed():
    return render_template('live_feed.html')

@app.route('/video_feed')
@login_required
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/export_attendance')
@login_required
def export_attendance():
    selected_date = request.args.get('date', date.today().strftime('%Y-%m-%d'))
    
    query = db.session.query(Attendance, Student).join(Student)
    query = query.filter(Attendance.date == selected_date)
    attendance_records = query.all()
    
    # Create DataFrame
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
    
    # Save to CSV
    filename = f"attendance_{selected_date}.csv"
    csv_path = os.path.join('static', filename)
    df.to_csv(csv_path, index=False)
    
    return redirect(url_for('static', filename=filename))

@app.route('/teachers')
@login_required
def teachers():
    all_teachers = Teacher.query.all()
    return render_template('teachers.html', teachers=all_teachers)

@app.route('/add_teacher', methods=['GET', 'POST'])
@login_required
@admin_required
def add_teacher():
    if request.method == 'POST':
        teacher_id = request.form['teacher_id']
        name = request.form['name']
        email = request.form['email']
        phone = request.form.get('phone', '')
        department = request.form.get('department', '')
        
        # Check if teacher already exists
        existing_teacher = Teacher.query.filter_by(teacher_id=teacher_id).first()
        if existing_teacher:
            flash('Teacher ID already exists!', 'error')
            return redirect(url_for('add_teacher'))
        
        # Handle image upload
        if 'image' not in request.files:
            flash('No image file provided!', 'error')
            return redirect(url_for('add_teacher'))
        
        file = request.files['image']
        if file.filename == '':
            flash('No image file selected!', 'error')
            return redirect(url_for('add_teacher'))
        
        if file:
            filename = secure_filename(f"{teacher_id}_{file.filename}")
            file_path = os.path.join(app.config['TEACHER_IMAGES'], filename)
            file.save(file_path)
            
            # Verify face can be detected
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
            
            # Create new teacher
            new_teacher = Teacher(
                teacher_id=teacher_id,
                name=name,
                email=email,
                phone=phone,
                department=department,
                image_path=file_path
            )
            
            db.session.add(new_teacher)
            db.session.commit()
            
            # Reload known faces
            load_known_faces()
            
            flash('Teacher added successfully!', 'success')
            return redirect(url_for('teachers'))
    
    return render_template('add_teacher.html')

@app.route('/teacher_attendance')
@login_required
def teacher_attendance():
    selected_date = request.args.get('date', date.today().strftime('%Y-%m-%d'))
    
    query = db.session.query(TeacherAttendance, Teacher).join(Teacher)
    
    if selected_date:
        query = query.filter(TeacherAttendance.date == selected_date)
    
    attendance_records = query.all()
    
    return render_template('teacher_attendance.html', 
                         attendance_records=attendance_records,
                         selected_date=selected_date)

@app.route('/analytics')
@login_required
def analytics():
    # Get date range for analytics
    end_date = date.today()
    start_date = end_date - timedelta(days=30)
    
    # Daily attendance trends
    daily_stats = []
    current_date = start_date
    while current_date <= end_date:
        student_count = Attendance.query.filter_by(date=current_date).count()
        teacher_count = TeacherAttendance.query.filter_by(date=current_date).count()
        
        daily_stats.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'students': student_count,
            'teachers': teacher_count
        })
        current_date += timedelta(days=1)
    
    # Class-wise attendance
    class_stats = db.session.query(
        Student.class_name,
        db.func.count(Student.id).label('total'),
        db.func.count(Attendance.id).label('present')
    ).outerjoin(Attendance, db.and_(
        Student.student_id == Attendance.student_id,
        Attendance.date == end_date
    )).group_by(Student.class_name).all()
    
    # Department-wise teacher attendance
    dept_stats = db.session.query(
        Teacher.department,
        db.func.count(Teacher.id).label('total'),
        db.func.count(TeacherAttendance.id).label('present')
    ).outerjoin(TeacherAttendance, db.and_(
        Teacher.teacher_id == TeacherAttendance.teacher_id,
        TeacherAttendance.date == end_date
    )).group_by(Teacher.department).all()
    
    return render_template('analytics.html',
                         daily_stats=daily_stats,
                         class_stats=class_stats,
                         dept_stats=dept_stats)

@app.route('/delete_student/<student_id>')
@login_required
@admin_required
def delete_student(student_id):
    student = Student.query.filter_by(student_id=student_id).first()
    if student:
        # Delete image file
        if student.image_path and os.path.exists(student.image_path):
            os.remove(student.image_path)
        
        # Delete attendance records
        Attendance.query.filter_by(student_id=student_id).delete()
        
        # Delete student
        db.session.delete(student)
        db.session.commit()
        
        # Reload known faces
        load_known_faces()
        
        flash('Student deleted successfully!', 'success')
    else:
        flash('Student not found!', 'error')
    
    return redirect(url_for('students'))

@app.route('/delete_teacher/<teacher_id>')
@login_required
@admin_required
def delete_teacher(teacher_id):
    teacher = Teacher.query.filter_by(teacher_id=teacher_id).first()
    if teacher:
        # Delete image file
        if teacher.image_path and os.path.exists(teacher.image_path):
            os.remove(teacher.image_path)
        
        # Delete attendance records
        TeacherAttendance.query.filter_by(teacher_id=teacher_id).delete()
        
        # Delete teacher
        db.session.delete(teacher)
        db.session.commit()
        
        # Reload known faces
        load_known_faces()
        
        flash('Teacher deleted successfully!', 'success')
    else:
        flash('Teacher not found!', 'error')
    
    return redirect(url_for('teachers'))

@app.route('/export_teacher_attendance')
@login_required
def export_teacher_attendance():
    selected_date = request.args.get('date', date.today().strftime('%Y-%m-%d'))
    
    query = db.session.query(TeacherAttendance, Teacher).join(Teacher)
    query = query.filter(TeacherAttendance.date == selected_date)
    attendance_records = query.all()
    
    # Create DataFrame
    data = []
    for attendance, teacher in attendance_records:
        data.append({
            'Teacher ID': teacher.teacher_id,
            'Name': teacher.name,
            'Department': teacher.department,
            'Date': attendance.date,
            'Time In': attendance.time_in.strftime('%H:%M:%S') if attendance.time_in else '',
            'Time Out': attendance.time_out.strftime('%H:%M:%S') if attendance.time_out else '',
            'Status': attendance.status
        })
    
    df = pd.DataFrame(data)
    
    # Save to CSV
    filename = f"teacher_attendance_{selected_date}.csv"
    csv_path = os.path.join('static', filename)
    df.to_csv(csv_path, index=False)
    
    return redirect(url_for('static', filename=filename))

@app.route('/api/attendance_stats')
@login_required
def attendance_stats():
    """API endpoint for real-time attendance statistics"""
    today = date.today()
    
    # Student stats
    total_students = Student.query.count()
    present_students = Attendance.query.filter_by(date=today, status='Present').count()
    absent_students = total_students - present_students
    
    # Teacher stats
    total_teachers = Teacher.query.count()
    present_teachers = TeacherAttendance.query.filter_by(date=today, status='Present').count()
    
    # Class-wise stats
    class_stats = db.session.query(
        Student.class_name,
        db.func.count(Student.id).label('total'),
        db.func.count(Attendance.id).label('present')
    ).outerjoin(Attendance, db.and_(
        Student.student_id == Attendance.student_id,
        Attendance.date == today
    )).group_by(Student.class_name).all()
    
    class_data = [{
        'class': stat.class_name,
        'total': stat.total,
        'present': stat.present,
        'absent': stat.total - stat.present,
        'percentage': round((stat.present / stat.total * 100) if stat.total > 0 else 0, 2)
    } for stat in class_stats]
    
    return jsonify({
        'students': {
            'total': total_students,
            'present': present_students,
            'absent': absent_students,
            'percentage': round((present_students / total_students * 100) if total_students > 0 else 0, 2)
        },
        'teachers': {
            'total': total_teachers,
            'present': present_teachers,
            'absent': total_teachers - present_teachers,
            'percentage': round((present_teachers / total_teachers * 100) if total_teachers > 0 else 0, 2)
        },
        'classes': class_data,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/setup_admin')
def setup_admin():
    """Setup initial admin user"""
    # Check if admin already exists
    admin = User.query.filter_by(role='admin').first()
    if admin:
        flash('Admin user already exists!', 'error')
        return redirect(url_for('login'))
    
    # Create admin user
    admin_password = 'admin123'  # Change this in production
    admin_hash = hashlib.sha256(admin_password.encode()).hexdigest()
    
    admin_user = User(
        username='admin',
        password_hash=admin_hash,
        role='admin'
    )
    
    db.session.add(admin_user)
    db.session.commit()
    
    flash('Admin user created! Username: admin, Password: admin123', 'success')
    return redirect(url_for('login'))

@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        
        # Verify current password
        if current_user.password_hash != hashlib.sha256(current_password.encode()).hexdigest():
            flash('Current password is incorrect!', 'error')
            return redirect(url_for('change_password'))
        
        # Check if new passwords match
        if new_password != confirm_password:
            flash('New passwords do not match!', 'error')
            return redirect(url_for('change_password'))
        
        # Update password
        current_user.password_hash = hashlib.sha256(new_password.encode()).hexdigest()
        db.session.commit()
        
        flash('Password changed successfully!', 'success')
        return redirect(url_for('index'))
    
    return render_template('change_password.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        load_known_faces()
        
        # Create admin user if none exists
        admin = User.query.filter_by(role='admin').first()
        if not admin:
            print("No admin user found. Run /setup_admin to create one.")
            print("Default credentials: admin/admin123")
    
    app.run(debug=True, host='0.0.0.0', port=5000)