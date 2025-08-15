"""
User Model - Authentication and user management
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

# Import db from models package
from app.models import db

class User(UserMixin, db.Model):
    """User model for authentication and user management"""
    
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    scripts = db.relationship('Script', backref='owner', lazy=True)
    executions = db.relationship('Execution', backref='user', lazy=True)
    
    def __init__(self, username, email, password):
        self.username = username
        self.email = email
        self.set_password(password)
    
    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if provided password is correct"""
        return check_password_hash(self.password_hash, password)
    
    def update_last_login(self):
        """Update last login timestamp"""
        self.last_login = datetime.utcnow()
        db.session.commit()
    
    def get_scripts_count(self):
        """Get count of user's scripts"""
        return Script.query.filter_by(user_id=self.id).count()
    
    def get_active_schedules_count(self):
        """Get count of user's active schedules"""
        return Schedule.query.join(Script).filter(
            Script.user_id == self.id,
            Schedule.is_active == True
        ).count()
    
    def __repr__(self):
        return f'<User {self.username}>'