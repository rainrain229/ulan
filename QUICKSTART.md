# 🚀 Quick Start Guide

Get your Face Recognition Attendance System up and running in minutes!

## Option 1: Automated Setup (Recommended)

```bash
# 1. Run the automated setup
python setup.py

# 2. Start the application
python app.py
```

## Option 2: Quick Launch Script

```bash
# Use the launch script (creates virtual environment)
./run.sh
```

## Option 3: Manual Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Create directories
mkdir -p static/student_images static/css static/js encodings logs

# 3. Start the application
python app.py
```

## 🧪 Test Your Installation

```bash
# Run the test script to verify everything works
python test_installation.py
```

## 🎭 Add Demo Data

```bash
# Generate sample students and attendance (optional)
python demo_data.py
```

## 🌐 Access the System

1. Open your browser
2. Go to: `http://localhost:5000`
3. Start adding students and taking attendance!

## 📱 Basic Usage

### Adding Your First Student
1. Click "Add Student" in the navigation
2. Fill in student details
3. Upload a clear, front-facing photo
4. Click "Add Student"

### Taking Attendance
1. Click "Live Feed" to start the camera
2. Have students look at the camera
3. Attendance is marked automatically when faces are recognized
4. View attendance in "Attendance Records"

## 🆘 Troubleshooting

### Camera Issues
- Ensure no other apps are using the camera
- Check camera permissions
- Try different camera indices (0, 1, 2) in `app.py`

### Installation Issues
- Install system dependencies manually (see README.md)
- Use a virtual environment
- Check Python version (3.7+ required)

### Face Recognition Not Working
- Ensure good lighting
- Use clear, front-facing photos
- Adjust recognition tolerance in `config.py`

## 🔧 Quick Configuration

Edit `config.py` to customize:
- Camera settings
- Recognition sensitivity
- Database location
- File upload limits

## 📞 Need Help?

1. Check the full README.md for detailed instructions
2. Run `python test_installation.py` to diagnose issues
3. Ensure all dependencies are installed correctly

---

**Happy attendance tracking! 🎓✨**
