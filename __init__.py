from flask import Flask
from app.routes import main
from app.config import Config
from app.models import db, bcrypt

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialize extensions
    db.init_app(app)
    bcrypt.init_app(app)
    
    # Register blueprints
    app.register_blueprint(main)
    
    # Create tables (for development; consider using migrations in production)
    with app.app_context():
        db.create_all()
    
    return app
