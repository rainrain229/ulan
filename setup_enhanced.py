#!/usr/bin/env python3
"""
Enhanced Smart Attendance System Setup Script
This script automates the setup process for the face recognition attendance system.
"""

import os
import sys
import subprocess
import platform
import sqlite3
from pathlib import Path

def print_banner():
    """Print the setup banner"""
    print("=" * 70)
    print("🎓 Enhanced Smart Attendance System - Setup Script")
    print("=" * 70)
    print("Setting up your face recognition attendance system...")
    print()

def check_python_version():
    """Check if Python version is compatible"""
    print("🔍 Checking Python version...")
    if sys.version_info < (3, 7):
        print("❌ Python 3.7 or higher is required!")
        print(f"Current version: {sys.version}")
        sys.exit(1)
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    print()

def install_system_dependencies():
    """Install system dependencies based on OS"""
    print("🔧 Installing system dependencies...")
    
    system = platform.system().lower()
    
    if system == "linux":
        try:
            # Ubuntu/Debian
            subprocess.run(["sudo", "apt-get", "update"], check=True, capture_output=True)
            packages = [
                "cmake", "libopenblas-dev", "liblapack-dev",
                "libx11-dev", "libgtk-3-dev", "python3-dev", "python3-pip"
            ]
            for package in packages:
                print(f"Installing {package}...")
                subprocess.run(["sudo", "apt-get", "install", "-y", package], 
                             check=True, capture_output=True)
            print("✅ System dependencies installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Warning: Could not install some system packages: {e}")
            print("You may need to install them manually")
    
    elif system == "darwin":  # macOS
        try:
            subprocess.run(["brew", "--version"], check=True, capture_output=True)
            packages = ["cmake", "openblas", "opencv"]
            for package in packages:
                print(f"Installing {package}...")
                subprocess.run(["brew", "install", package], check=True, capture_output=True)
            print("✅ System dependencies installed successfully")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("⚠️  Warning: Homebrew not found. Please install manually:")
            print("   /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"")
    
    elif system == "windows":
        print("⚠️  Windows detected. Please install the following manually:")
        print("   - Visual Studio Build Tools")
        print("   - CMake")
        print("   - OpenCV")
    
    print()

def create_virtual_environment():
    """Create and activate virtual environment"""
    print("🐍 Setting up virtual environment...")
    
    venv_path = Path("venv")
    if venv_path.exists():
        print("✅ Virtual environment already exists")
    else:
        try:
            subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
            print("✅ Virtual environment created")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to create virtual environment: {e}")
            sys.exit(1)
    
    print()

def install_python_dependencies():
    """Install Python dependencies"""
    print("📦 Installing Python dependencies...")
    
    # Determine pip path
    if platform.system().lower() == "windows":
        pip_path = "venv\\Scripts\\pip"
    else:
        pip_path = "venv/bin/pip"
    
    try:
        # Upgrade pip first
        subprocess.run([pip_path, "install", "--upgrade", "pip"], check=True, capture_output=True)
        
        # Install requirements
        if os.path.exists("requirements.txt"):
            subprocess.run([pip_path, "install", "-r", "requirements.txt"], check=True)
            print("✅ Python dependencies installed successfully")
        else:
            print("❌ requirements.txt not found!")
            sys.exit(1)
    
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install Python dependencies: {e}")
        sys.exit(1)
    
    print()

def create_directories():
    """Create necessary directories"""
    print("📁 Creating directories...")
    
    directories = [
        "static/student_images",
        "static/teacher_images",
        "encodings",
        "logs",
        "exports"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✅ Created: {directory}")
    
    print()

def setup_database():
    """Initialize the database"""
    print("🗄️  Setting up database...")
    
    try:
        # Import app and create database
        sys.path.insert(0, os.getcwd())
        from app import app, db, User
        
        with app.app_context():
            db.create_all()
            print("✅ Database tables created")
            
            # Check if admin user exists
            admin = User.query.filter_by(role='admin').first()
            if not admin:
                print("ℹ️  No admin user found. You'll need to create one at /setup_admin")
            else:
                print("✅ Admin user already exists")
    
    except Exception as e:
        print(f"⚠️  Warning: Could not initialize database: {e}")
        print("Database will be created when you first run the application")
    
    print()

def test_installation():
    """Test the installation"""
    print("🧪 Testing installation...")
    
    try:
        # Test imports
        import cv2
        print("✅ OpenCV imported successfully")
        
        import face_recognition
        print("✅ face_recognition imported successfully")
        
        import flask
        print("✅ Flask imported successfully")
        
        print("✅ All core dependencies working correctly")
    
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Please check your installation")
        return False
    
    print()

def print_next_steps():
    """Print next steps for the user"""
    print("🎉 Setup completed successfully!")
    print()
    print("📋 Next steps:")
    print("1. Activate virtual environment:")
    if platform.system().lower() == "windows":
        print("   venv\\Scripts\\activate")
    else:
        print("   source venv/bin/activate")
    
    print("2. Run the application:")
    print("   python app.py")
    
    print("3. Open your browser and go to:")
    print("   http://localhost:5000")
    
    print("4. Setup admin account:")
    print("   http://localhost:5000/setup_admin")
    print("   Default credentials: admin/admin123")
    
    print("5. Login and start using the system!")
    print()
    print("📚 For more information, see README_ENHANCED.md")
    print("🆘 For help, check the troubleshooting section in the README")

def main():
    """Main setup function"""
    print_banner()
    
    try:
        check_python_version()
        install_system_dependencies()
        create_virtual_environment()
        install_python_dependencies()
        create_directories()
        setup_database()
        test_installation()
        print_next_steps()
        
    except KeyboardInterrupt:
        print("\n\n❌ Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Setup failed: {e}")
        print("Please check the error messages above and try again")
        sys.exit(1)

if __name__ == "__main__":
    main()