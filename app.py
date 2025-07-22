from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Response
from flask_sqlalchemy import SQLAlchemy
import cv2
import face_recognition
import numpy as np
import os
import pickle
from datetime import datetime, date
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

# Global variables
known_face_encodings = []
known_face_names = []
camera = None

def load_known_faces():
    """Load all known face encodings from the database"""
    global known_face_encodings, known_face_names
    
    known_face_encodings = []
    known_face_names = []
    
    students = Student.query.all()
    for student in students:
        if student.image_path and os.path.exists(student.image_path):
            try:
                image = face_recognition.load_image_file(student.image_path)
                encodings = face_recognition.face_encodings(image)
                if encodings:
                    known_face_encodings.append(encodings[0])
                    known_face_names.append(student.student_id)
            except Exception as e:
                print(f"Error loading face for {student.name}: {e}")

def mark_attendance(student_id):
    """Mark attendance for a student"""
    today = date.today()
    
    # Check if already marked today
    existing_attendance = Attendance.query.filter_by(
        student_id=student_id, 
        date=today
    ).first()
    
    if existing_attendance:
        if not existing_attendance.time_out:
            # Mark time out
            existing_attendance.time_out = datetime.now()
            db.session.commit()
            return f"Time out marked for {student_id}"
        else:
            return f"Attendance already complete for {student_id}"
    else:
        # Mark time in
        new_attendance = Attendance(
            student_id=student_id,
            date=today,
            time_in=datetime.now()
        )
        db.session.add(new_attendance)
        db.session.commit()
        return f"Time in marked for {student_id}"

def generate_frames():
    """Generate video frames for live feed"""
    global camera
    
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
            # Check if face matches known faces
            matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
            name = "Unknown"
            
            if True in matches:
                first_match_index = matches.index(True)
                name = known_face_names[first_match_index]
                
                # Mark attendance
                result = mark_attendance(name)
                print(result)
            
            # Scale back up face locations
            top, right, bottom, left = face_location
            top *= 4
            right *= 4
            bottom *= 4
            left *= 4
            
            # Draw rectangle and label
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
            cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 255, 0), cv2.FILLED)
            cv2.putText(frame, name, (left + 6, bottom - 6), cv2.FONT_HERSHEY_DUPLEX, 0.8, (255, 255, 255), 1)
        
        # Encode frame to bytes
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

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
def live_feed():
    return render_template('live_feed.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/export_attendance')
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

@app.route('/delete_student/<student_id>')
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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        load_known_faces()
    app.run(debug=True, host='0.0.0.0', port=5000)