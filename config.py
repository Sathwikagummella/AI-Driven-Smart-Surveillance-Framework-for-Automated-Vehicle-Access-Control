import os

# Get the absolute path of the current directory
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Security key for Flask sessions (e.g., keeping admins logged in)
    SECRET_KEY = 'pra-vigil-super-secure-key'
    
    # Define the SQLite database location
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'pra_vigil.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Folder to store uploaded images/videos for the ML model
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static/uploads')