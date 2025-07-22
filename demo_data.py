#!/usr/bin/env python3
"""
Demo data generator for Face Recognition Attendance System
Creates sample students and attendance records for demonstration
"""

import os
import sys
from datetime import datetime, date, timedelta
from PIL import Image, ImageDraw, ImageFont
import random

# Add the current directory to the path to import app modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def create_sample_image(name, student_id, size=(200, 200)):
    """Create a sample student image with text overlay"""
    # Create a colorful background
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F']
    bg_color = random.choice(colors)
    
    # Create image
    img = Image.new('RGB', size, bg_color)
    draw = ImageDraw.Draw(img)
    
    # Try to use a font, fall back to default if not available
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
        small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    except:
        try:
            font = ImageFont.truetype("arial.ttf", 20)
            small_font = ImageFont.truetype("arial.ttf", 16)
        except:
            font = ImageFont.load_default()
            small_font = ImageFont.load_default()
    
    # Draw a simple face
    face_center = (size[0]//2, size[1]//2 - 20)
    face_radius = 40
    
    # Face circle
    draw.ellipse([
        face_center[0] - face_radius, face_center[1] - face_radius,
        face_center[0] + face_radius, face_center[1] + face_radius
    ], fill='#FDBCB4', outline='#E17B47', width=2)
    
    # Eyes
    eye_y = face_center[1] - 10
    draw.ellipse([face_center[0] - 20, eye_y - 5, face_center[0] - 10, eye_y + 5], fill='#2C3E50')
    draw.ellipse([face_center[0] + 10, eye_y - 5, face_center[0] + 20, eye_y + 5], fill='#2C3E50')
    
    # Smile
    smile_y = face_center[1] + 10
    draw.arc([
        face_center[0] - 15, smile_y - 10,
        face_center[0] + 15, smile_y + 10
    ], 0, 180, fill='#E74C3C', width=3)
    
    # Add name and ID text
    text_y = face_center[1] + face_radius + 20
    
    # Name
    name_bbox = draw.textbbox((0, 0), name, font=font)
    name_width = name_bbox[2] - name_bbox[0]
    draw.text((size[0]//2 - name_width//2, text_y), name, fill='white', font=font)
    
    # Student ID
    id_bbox = draw.textbbox((0, 0), student_id, font=small_font)
    id_width = id_bbox[2] - id_bbox[0]
    draw.text((size[0]//2 - id_width//2, text_y + 30), student_id, fill='white', font=small_font)
    
    return img

def create_demo_students():
    """Create sample students with generated images"""
    from app import app, db, Student
    
    students_data = [
        {'student_id': 'STU001', 'name': 'Alice Johnson', 'class_name': 'Grade 10A', 'email': 'alice.johnson@school.edu', 'phone': '+1-555-0101'},
        {'student_id': 'STU002', 'name': 'Bob Smith', 'class_name': 'Grade 10A', 'email': 'bob.smith@school.edu', 'phone': '+1-555-0102'},
        {'student_id': 'STU003', 'name': 'Carol Davis', 'class_name': 'Grade 10B', 'email': 'carol.davis@school.edu', 'phone': '+1-555-0103'},
        {'student_id': 'STU004', 'name': 'David Wilson', 'class_name': 'Grade 10B', 'email': 'david.wilson@school.edu', 'phone': '+1-555-0104'},
        {'student_id': 'STU005', 'name': 'Emma Brown', 'class_name': 'Grade 11A', 'email': 'emma.brown@school.edu', 'phone': '+1-555-0105'},
        {'student_id': 'STU006', 'name': 'Frank Miller', 'class_name': 'Grade 11A', 'email': 'frank.miller@school.edu', 'phone': '+1-555-0106'},
        {'student_id': 'STU007', 'name': 'Grace Lee', 'class_name': 'Grade 11B', 'email': 'grace.lee@school.edu', 'phone': '+1-555-0107'},
        {'student_id': 'STU008', 'name': 'Henry Taylor', 'class_name': 'Grade 11B', 'email': 'henry.taylor@school.edu', 'phone': '+1-555-0108'},
    ]
    
    with app.app_context():
        # Clear existing demo students
        for student_data in students_data:
            existing = Student.query.filter_by(student_id=student_data['student_id']).first()
            if existing:
                db.session.delete(existing)
        db.session.commit()
        
        print("👥 Creating demo students...")
        
        for student_data in students_data:
            # Create sample image
            img = create_sample_image(student_data['name'], student_data['student_id'])
            
            # Save image
            image_filename = f"{student_data['student_id']}_demo.png"
            image_path = os.path.join('static/student_images', image_filename)
            img.save(image_path)
            
            # Create student record
            student = Student(
                student_id=student_data['student_id'],
                name=student_data['name'],
                class_name=student_data['class_name'],
                email=student_data['email'],
                phone=student_data['phone'],
                image_path=image_path
            )
            
            db.session.add(student)
            print(f"✅ Created student: {student_data['name']} ({student_data['student_id']})")
        
        db.session.commit()
        print(f"🎉 Successfully created {len(students_data)} demo students!")

def create_demo_attendance():
    """Create sample attendance records"""
    from app import app, db, Student, Attendance
    
    with app.app_context():
        students = Student.query.all()
        if not students:
            print("❌ No students found. Create students first.")
            return
        
        print("📅 Creating demo attendance records...")
        
        # Generate attendance for the last 7 days
        for days_ago in range(7):
            attendance_date = date.today() - timedelta(days=days_ago)
            
            # Randomly select students who attended (80% attendance rate)
            attending_students = random.sample(students, k=int(len(students) * 0.8))
            
            for student in attending_students:
                # Random time in (8:00 AM - 9:00 AM)
                time_in_hour = random.randint(8, 8)
                time_in_minute = random.randint(0, 59)
                time_in = datetime.combine(attendance_date, datetime.min.time().replace(hour=time_in_hour, minute=time_in_minute))
                
                # Random time out (3:00 PM - 4:00 PM) - only for past days
                time_out = None
                if days_ago > 0:  # Only past days have time out
                    time_out_hour = random.randint(15, 16)
                    time_out_minute = random.randint(0, 59)
                    time_out = datetime.combine(attendance_date, datetime.min.time().replace(hour=time_out_hour, minute=time_out_minute))
                
                # Check if attendance already exists
                existing = Attendance.query.filter_by(
                    student_id=student.student_id,
                    date=attendance_date
                ).first()
                
                if not existing:
                    attendance = Attendance(
                        student_id=student.student_id,
                        date=attendance_date,
                        time_in=time_in,
                        time_out=time_out,
                        status='Present'
                    )
                    db.session.add(attendance)
        
        db.session.commit()
        print("🎉 Successfully created demo attendance records!")

def main():
    """Main function to create all demo data"""
    print("🎭 Face Recognition Attendance System - Demo Data Generator")
    print("=" * 60)
    
    # Ensure directories exist
    os.makedirs('static/student_images', exist_ok=True)
    
    try:
        create_demo_students()
        create_demo_attendance()
        
        print("\n✅ Demo data creation completed successfully!")
        print("\n🚀 You can now:")
        print("1. Run 'python app.py' to start the application")
        print("2. Go to http://localhost:5000 to see the demo data")
        print("3. Test the live feed with the sample student images")
        print("\n💡 Note: The sample images are generated programmatically.")
        print("   For real face recognition, upload actual photos of students.")
        
    except Exception as e:
        print(f"❌ Error creating demo data: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
