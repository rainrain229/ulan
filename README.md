# 🎓 Face Recognition Attendance System for Schools

A modern, AI-powered attendance management system that uses real-time face recognition to automatically track student attendance. Built with Python, Flask, OpenCV, and modern web technologies.

## ✨ Features

### 🔍 **Advanced Face Recognition**
- Real-time face detection and recognition using OpenCV and dlib
- High accuracy face matching with machine learning algorithms
- Support for multiple faces in a single frame
- Automatic attendance marking when students are recognized

### 👥 **Student Management**
- Easy student registration with photo upload
- Student database with personal information
- Photo validation during registration
- Bulk student import/export capabilities

### 📊 **Attendance Tracking**
- Automatic time-in and time-out recording
- Real-time attendance monitoring
- Date and class-wise filtering
- Attendance statistics and analytics

### 🖥️ **Modern Web Interface**
- Beautiful, responsive web interface
- Real-time camera feed with live recognition
- Dashboard with attendance statistics
- Mobile-friendly design

### 📈 **Reporting & Analytics**
- Daily, weekly, and monthly attendance reports
- CSV export functionality
- Class-wise attendance analysis
- Individual student attendance history

## 🚀 Quick Start

### Prerequisites
- Python 3.7 or higher
- Webcam or camera device
- Linux/macOS/Windows operating system

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd face-recognition-attendance-system
   ```

2. **Run the setup script**
   ```bash
   python setup.py
   ```
   
   This will automatically:
   - Install system dependencies
   - Create necessary directories
   - Install Python packages
   - Initialize the database

3. **Start the application**
   ```bash
   python app.py
   ```

4. **Access the system**
   Open your browser and go to: `http://localhost:5000`

### Manual Installation (if setup script fails)

1. **Install system dependencies**
   
   **Ubuntu/Debian:**
   ```bash
   sudo apt-get update
   sudo apt-get install cmake libopenblas-dev liblapack-dev
   sudo apt-get install libx11-dev libgtk-3-dev
   sudo apt-get install python3-dev python3-pip
   ```
   
   **macOS:**
   ```bash
   brew install cmake openblas opencv
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**
   ```bash
   python app.py
   ```

## 📱 How to Use

### 1. **Add Students**
- Navigate to "Add Student" from the main menu
- Fill in student information (ID, name, class, contact details)
- Upload a clear, front-facing photo of the student
- The system will verify that a face is detected before saving

### 2. **Start Attendance**
- Go to "Live Feed" to start the camera
- Position students in front of the camera
- The system automatically detects and marks attendance
- Green rectangles appear around recognized faces
- Attendance is recorded with timestamps

### 3. **View Attendance**
- Check "Attendance Records" to view daily attendance
- Filter by date and class
- Export attendance data as CSV files
- Monitor attendance statistics on the dashboard

### 4. **Manage Students**
- View all registered students in the "Students" section
- Edit student information or remove students as needed
- The system automatically updates face recognition data

## 🛠️ Technical Details

### Architecture
- **Backend**: Flask (Python web framework)
- **Database**: SQLite (easily replaceable with PostgreSQL/MySQL)
- **Face Recognition**: OpenCV + dlib + face_recognition library
- **Frontend**: Bootstrap 5 + Custom CSS/JavaScript
- **Real-time Processing**: OpenCV video capture with frame processing

### Key Components

1. **Face Recognition Engine** (`app.py`)
   - Loads and encodes known faces from student photos
   - Processes video frames in real-time
   - Compares detected faces with known encodings
   - Automatically marks attendance when matches are found

2. **Database Models** (`app.py`)
   - Student model: Stores student information and photo paths
   - Attendance model: Records attendance with timestamps
   - Relationships between students and their attendance records

3. **Web Interface** (`templates/`)
   - Responsive design that works on desktop and mobile
   - Real-time video feed display
   - Interactive forms for student management
   - Dashboard with statistics and quick actions

### Security Features
- Input validation and sanitization
- Secure file upload handling
- SQL injection protection through SQLAlchemy ORM
- Face verification during student registration

## 🔧 Configuration

### Camera Settings
The system automatically detects the default camera (index 0). To use a different camera:

```python
# In app.py, modify the camera initialization
camera = cv2.VideoCapture(1)  # Use camera index 1
```

### Face Recognition Accuracy
Adjust recognition sensitivity in `app.py`:

```python
# Lower values = stricter matching, higher values = more lenient
matches = face_recognition.compare_faces(known_face_encodings, face_encoding, tolerance=0.6)
```

## 📊 Database Schema

### Students Table
- `id`: Primary key
- `student_id`: Unique student identifier
- `name`: Full name
- `class_name`: Class/grade
- `email`: Contact email
- `phone`: Contact phone
- `image_path`: Path to student photo
- `created_at`: Registration timestamp

### Attendance Table
- `id`: Primary key
- `student_id`: Foreign key to students
- `date`: Attendance date
- `time_in`: Entry time
- `time_out`: Exit time (optional)
- `status`: Attendance status

## 🚨 Troubleshooting

### Common Issues

1. **Camera not working**
   - Check camera permissions
   - Ensure no other applications are using the camera
   - Try different camera indices (0, 1, 2, etc.)

2. **Face recognition not accurate**
   - Ensure good lighting conditions
   - Use clear, front-facing photos during registration
   - Adjust recognition tolerance settings

3. **Installation errors**
   - Install system dependencies manually
   - Use virtual environment to avoid conflicts
   - Check Python version compatibility

### System Requirements
- **Minimum**: 2GB RAM, 1GHz processor, basic webcam
- **Recommended**: 4GB RAM, 2GHz processor, HD webcam
- **Storage**: 500MB for application + student photos

## 🔮 Future Enhancements

- [ ] Multi-camera support
- [ ] Advanced analytics and reporting
- [ ] Email notifications for attendance
- [ ] Mobile app for teachers
- [ ] Integration with school management systems
- [ ] Automated backup and cloud storage
- [ ] Advanced anti-spoofing measures
- [ ] Multi-language support

---

**Made with ❤️ for educational institutions**
