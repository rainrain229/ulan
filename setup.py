#!/usr/bin/env python3
"""
Setup script for Face Recognition Attendance System
This script installs system dependencies and sets up the environment
"""

import os
import sys
import subprocess
import platform

def run_command(command, description):
    """Run a system command with error handling"""
    print(f"\n{description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✓ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Error during {description}: {e}")
        print(f"Command output: {e.output}")
        return False

def install_system_dependencies():
    """Install system-level dependencies"""
    system = platform.system().lower()
    
    if system == 'linux':
        print("Installing Linux dependencies...")
        commands = [
            ("sudo apt-get update", "Updating package list"),
            ("sudo apt-get install -y cmake", "Installing CMake"),
            ("sudo apt-get install -y libopenblas-dev liblapack-dev", "Installing BLAS/LAPACK"),
            ("sudo apt-get install -y libx11-dev libgtk-3-dev", "Installing GUI libraries"),
            ("sudo apt-get install -y python3-dev python3-pip", "Installing Python development tools"),
            ("sudo apt-get install -y libopencv-dev python3-opencv", "Installing OpenCV"),
        ]
    elif system == 'darwin':  # macOS
        print("Installing macOS dependencies...")
        commands = [
            ("brew install cmake", "Installing CMake"),
            ("brew install openblas", "Installing OpenBLAS"),
            ("brew install opencv", "Installing OpenCV"),
        ]
    elif system == 'windows':
        print("Windows detected. Please install the following manually:")
        print("1. Visual Studio Build Tools")
        print("2. CMake")
        print("3. OpenCV")
        return True
    else:
        print(f"Unsupported system: {system}")
        return False
    
    success = True
    for command, description in commands:
        if not run_command(command, description):
            success = False
    
    return success

def install_python_dependencies():
    """Install Python dependencies"""
    print("\nInstalling Python dependencies...")
    
    # Upgrade pip first
    if not run_command(f"{sys.executable} -m pip install --upgrade pip", "Upgrading pip"):
        return False
    
    # Install requirements
    if not run_command(f"{sys.executable} -m pip install -r requirements.txt", "Installing Python packages"):
        return False
    
    return True

def create_directories():
    """Create necessary directories"""
    print("\nCreating necessary directories...")
    
    directories = [
        'static/student_images',
        'static/css',
        'static/js',
        'encodings',
        'logs'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✓ Created directory: {directory}")
    
    return True

def main():
    """Main setup function"""
    print("=" * 50)
    print("Face Recognition Attendance System Setup")
    print("=" * 50)
    
    success = True
    
    # Check Python version
    if sys.version_info < (3, 7):
        print("✗ Python 3.7 or higher is required")
        return False
    
    print(f"✓ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    
    # Install system dependencies
    if not install_system_dependencies():
        print("⚠ Some system dependencies failed to install. You may need to install them manually.")
        success = False
    
    # Create directories
    if not create_directories():
        success = False
    
    # Install Python dependencies
    if not install_python_dependencies():
        success = False
    
    print("\n" + "=" * 50)
    if success:
        print("✓ Setup completed successfully!")
        print("\nTo start the application, run:")
        print("python app.py")
        print("\nThen open your browser and go to: http://localhost:5000")
    else:
        print("⚠ Setup completed with some errors.")
        print("Please check the error messages above and resolve any issues.")
    print("=" * 50)
    
    return success

if __name__ == "__main__":
    main()
