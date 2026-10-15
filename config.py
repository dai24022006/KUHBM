import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

    # Use PostgreSQL on Render (DATABASE_URL env var), SQLite locally
    database_url = os.environ.get('DATABASE_URL', f'sqlite:///{os.path.join(BASE_DIR, "hotel.db")}')
    # Render gives postgres:// but SQLAlchemy needs postgresql://
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_DATABASE_URI = database_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
