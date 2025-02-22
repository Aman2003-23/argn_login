import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key')
    
    # SQLAlchemy settings
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Adzuna API settings
    ADZUNA_APP_ID="8170f497"
    ADZUNA_APP_KEY="4239bfd964627f446100861685b70482"
    ADZUNA_COUNTRY="in"
    
    # Google Custom Search API settings
    GOOGLE_API_KEY="AIzaSyA_zJxfIFzPHTVc66CfnlVUm4ZBeRpsBK4"
    GOOGLE_CX="67c953448b2d541bc"

