#!/usr/bin/env python3
"""
Setup script for Advanced Face Recognition Attendance System
This script will install dependencies and set up the system
"""

import os
import sys
import subprocess
import platform
import shutil

def print_banner():
    """Print the system banner"""
    print("=" * 60)
    print("🎓 Advanced Face Recognition Attendance System")
    print("=" * 60)
    print("Setting up your attendance management system...")
    print()

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 7):
        print("❌ Error: Python 3.7 or higher is required")
        print(f"Current version: {sys.version}")
        sys.exit(1)
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")

def install_pip():
    """Ensure pip is available"""
    try:
        import pip
        print("✅ pip is available")
    except ImportError:
        print("❌ pip not found. Installing...")
        try:
            subprocess.check_call([sys.executable, "-m", "ensurepip", "--upgrade"])
            print("✅ pip installed successfully")
        except subprocess.CalledProcessError:
            print("❌ Failed to install pip. Please install manually.")
            sys.exit(1)

def install_requirements():
    """Install Python requirements"""
    print("📦 Installing Python dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Python dependencies installed successfully")
    except subprocess.CalledProcessError:
        print("❌ Failed to install Python dependencies")
        print("Please run: pip install -r requirements.txt")
        sys.exit(1)

def create_directories():
    """Create necessary directories"""
    print("📁 Creating directories...")
    directories = [
        "static/student_images",
        "static/teacher_images", 
        "encodings",
        "logs"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✅ Created: {directory}")

def check_system_dependencies():
    """Check and install system dependencies based on OS"""
    system = platform.system().lower()
    print(f"🖥️  Detected OS: {platform.system()} {platform.release()}")
    
    if system == "linux":
        install_linux_dependencies()
    elif system == "darwin":  # macOS
        install_macos_dependencies()
    elif system == "windows":
        install_windows_dependencies()
    else:
        print(f"⚠️  Unsupported OS: {system}")
        print("Please install dependencies manually")

def install_linux_dependencies():
    """Install Linux system dependencies"""
    print("🐧 Installing Linux dependencies...")
    
    # Check if we have sudo access
    if os.geteuid() == 0:
        print("✅ Running as root, installing system packages...")
        packages = [
            "cmake", "libopenblas-dev", "liblapack-dev",
            "libx11-dev", "libgtk-3-dev", "python3-dev"
        ]
        
        try:
            subprocess.check_call(["apt-get", "update"])
            subprocess.check_call(["apt-get", "install", "-y"] + packages)
            print("✅ Linux dependencies installed successfully")
        except subprocess.CalledProcessError:
            print("❌ Failed to install Linux dependencies")
            print("Please run: sudo apt-get install cmake libopenblas-dev liblapack-dev libx11-dev libgtk-3-dev python3-dev")
    else:
        print("⚠️  Not running as root. Please run with sudo or install manually:")
        print("sudo apt-get install cmake libopenblas-dev liblapack-dev libx11-dev libgtk-3-dev python3-dev")

def install_macos_dependencies():
    """Install macOS system dependencies"""
    print("🍎 Installing macOS dependencies...")
    
    # Check if Homebrew is available
    if shutil.which("brew"):
        try:
            subprocess.check_call(["brew", "install", "cmake", "openblas", "opencv"])
            print("✅ macOS dependencies installed successfully")
        except subprocess.CalledProcessError:
            print("❌ Failed to install macOS dependencies")
            print("Please run: brew install cmake openblas opencv")
    else:
        print("⚠️  Homebrew not found. Please install Homebrew first:")
        print("Visit: https://brew.sh/")

def install_windows_dependencies():
    """Install Windows system dependencies"""
    print("🪟 Windows detected...")
    print("⚠️  For Windows, please install the following manually:")
    print("1. Visual Studio Build Tools")
    print("2. CMake: https://cmake.org/download/")
    print("3. OpenCV: pip install opencv-python")
    print("4. dlib: pip install dlib")

def test_installation():
    """Test if the installation was successful"""
    print("🧪 Testing installation...")
    
    try:
        # Test basic imports
        import cv2
        print("✅ OpenCV imported successfully")
        
        import face_recognition
        print("✅ face_recognition imported successfully")
        
        import flask
        print("✅ Flask imported successfully")
        
        print("✅ All core dependencies working correctly!")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Please check your installation")

def create_startup_script():
    """Create a startup script"""
    print("🚀 Creating startup script...")
    
    if platform.system().lower() == "windows":
        script_content = """@echo off
echo Starting Face Recognition Attendance System...
python app.py
pause
"""
        script_name = "start_attendance.bat"
    else:
        script_content = """#!/bin/bash
echo "Starting Face Recognition Attendance System..."
python3 app.py
"""
        script_name = "start_attendance.sh"
        # Make executable
        os.chmod(script_name, 0o755)
    
    with open(script_name, "w") as f:
        f.write(script_content)
    
    print(f"✅ Created startup script: {script_name}")

def print_next_steps():
    """Print next steps for the user"""
    print("\n" + "=" * 60)
    print("🎉 Setup Complete! Here's what to do next:")
    print("=" * 60)
    print()
    print("1. 🚀 Start the system:")
    if platform.system().lower() == "windows":
        print("   Double-click: start_attendance.bat")
    else:
        print("   Run: ./start_attendance.sh")
    print()
    print("2. 🌐 Open your browser and go to:")
    print("   http://localhost:5000/setup_admin")
    print()
    print("3. 🔐 Create admin account:")
    print("   Username: admin")
    print("   Password: admin123")
    print()
    print("4. 📱 Login at:")
    print("   http://localhost:5000/login")
    print()
    print("5. 🔒 Change default password after first login")
    print()
    print("📚 For more information, see README.md")
    print("=" * 60)

def main():
    """Main setup function"""
    print_banner()
    
    try:
        check_python_version()
        install_pip()
        install_requirements()
        create_directories()
        check_system_dependencies()
        test_installation()
        create_startup_script()
        print_next_steps()
        
    except KeyboardInterrupt:
        print("\n\n❌ Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        print("Please check the error and try again")
        sys.exit(1)

if __name__ == "__main__":
    main()
