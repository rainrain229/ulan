#!/usr/bin/env python3
"""
Test script to verify Face Recognition Attendance System installation
"""

import sys
import importlib
import subprocess
import os

def test_python_version():
    """Test Python version compatibility"""
    print("🐍 Testing Python version...")
    if sys.version_info < (3, 7):
        print("❌ Python 3.7 or higher required")
        return False
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    return True

def test_package_imports():
    """Test if required packages can be imported"""
    print("\n📦 Testing package imports...")
    
    required_packages = [
        ('flask', 'Flask'),
        ('cv2', 'OpenCV'),
        ('face_recognition', 'Face Recognition'),
        ('numpy', 'NumPy'),
        ('pandas', 'Pandas'),
        ('PIL', 'Pillow'),
        ('sqlalchemy', 'SQLAlchemy')
    ]
    
    success = True
    for package, name in required_packages:
        try:
            importlib.import_module(package)
            print(f"✅ {name}")
        except ImportError as e:
            print(f"❌ {name} - {e}")
            success = False
    
    return success

def test_camera_access():
    """Test camera accessibility"""
    print("\n📷 Testing camera access...")
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            ret, frame = cap.read()
            cap.release()
            if ret:
                print("✅ Camera accessible and working")
                return True
            else:
                print("⚠️ Camera detected but cannot read frames")
                return False
        else:
            print("❌ Cannot access camera")
            return False
    except Exception as e:
        print(f"❌ Camera test failed: {e}")
        return False

def test_face_recognition():
    """Test face recognition functionality"""
    print("\n👤 Testing face recognition...")
    try:
        import face_recognition
        import numpy as np
        
        # Create a dummy image
        dummy_image = np.zeros((100, 100, 3), dtype=np.uint8)
        
        # Test face detection (should find no faces in blank image)
        face_locations = face_recognition.face_locations(dummy_image)
        print(f"✅ Face detection working (found {len(face_locations)} faces in blank image)")
        return True
    except Exception as e:
        print(f"❌ Face recognition test failed: {e}")
        return False

def test_directories():
    """Test if necessary directories exist"""
    print("\n📁 Testing directory structure...")
    
    required_dirs = [
        'templates',
        'static',
        'static/student_images',
        'static/css',
        'static/js'
    ]
    
    success = True
    for directory in required_dirs:
        if os.path.exists(directory):
            print(f"✅ {directory}")
        else:
            print(f"❌ {directory} - missing")
            success = False
    
    return success

def test_files():
    """Test if required files exist"""
    print("\n📄 Testing required files...")
    
    required_files = [
        'app.py',
        'requirements.txt',
        'config.py',
        'templates/base.html',
        'templates/index.html',
        'templates/add_student.html',
        'templates/students.html',
        'templates/attendance.html',
        'templates/live_feed.html'
    ]
    
    success = True
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - missing")
            success = False
    
    return success

def test_database_connection():
    """Test database connectivity"""
    print("\n🗄️ Testing database connection...")
    try:
        from app import app, db
        with app.app_context():
            db.create_all()
            print("✅ Database connection successful")
            return True
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🎓 Face Recognition Attendance System - Installation Test")
    print("=" * 60)
    
    tests = [
        test_python_version,
        test_package_imports,
        test_directories,
        test_files,
        test_database_connection,
        test_camera_access,
        test_face_recognition
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    print("📊 Test Results Summary:")
    print(f"✅ Passed: {sum(results)}/{len(results)}")
    print(f"❌ Failed: {len(results) - sum(results)}/{len(results)}")
    
    if all(results):
        print("\n�� All tests passed! The system is ready to use.")
        print("🚀 Run 'python app.py' to start the application")
        return True
    else:
        print("\n⚠️ Some tests failed. Please check the installation.")
        print("💡 Try running 'python setup.py' to fix common issues")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
