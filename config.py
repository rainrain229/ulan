"""
Configuration settings for Face Recognition Attendance System
"""

import os
from datetime import timedelta

class Config:
    """Base configuration class"""
    
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-change-this-in-production'
    
    # Database settings
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///attendance.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # File upload settings
    UPLOAD_FOLDER = 'static/student_images'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    
    # Face recognition settings
    FACE_RECOGNITION_TOLERANCE = 0.6  # Lower = stricter matching
    FACE_DETECTION_MODEL = 'hog'  # 'hog' or 'cnn' (cnn is more accurate but slower)
    
    # Camera settings
    CAMERA_INDEX = 0  # Default camera
    FRAME_RATE = 30
    FRAME_WIDTH = 640
    FRAME_HEIGHT = 480
    
    # Attendance settings
    ATTENDANCE_TIME_WINDOW = timedelta(hours=12)  # Time window for same-day attendance
    AUTO_TIMEOUT_HOURS = 8  # Automatically mark timeout after X hours
    
    # Logging settings
    LOG_LEVEL = 'INFO'
    LOG_FILE = 'logs/attendance_system.log'
    
    # Email settings (for future notifications)
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    
    # Security settings
    SESSION_TIMEOUT = timedelta(hours=24)
    CSRF_ENABLED = True
    
    # Performance settings
    FACE_ENCODING_CACHE_SIZE = 100  # Number of face encodings to cache
    VIDEO_PROCESSING_THREADS = 2
    
    @staticmethod
    def allowed_file(filename):
        """Check if file extension is allowed"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    FACE_DETECTION_MODEL = 'hog'  # Faster for development

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    FACE_DETECTION_MODEL = 'cnn'  # More accurate for production
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'generate-a-real-secret-key'

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///test_attendance.db'
    WTF_CSRF_ENABLED = False

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
