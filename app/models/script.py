"""
Script Model - Uploaded script management
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

# Import db from models package
from app.models import db

class Script(db.Model):
    """Script model for managing uploaded automation scripts"""
    
    __tablename__ = 'scripts'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    script_type = db.Column(db.String(10), nullable=False)  # 'py' or 'bat'
    file_size = db.Column(db.Integer)  # in bytes
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Foreign key
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Relationships
    executions = db.relationship('Execution', backref='script', lazy=True, cascade='all, delete-orphan')
    schedules = db.relationship('Schedule', backref='script', lazy=True, cascade='all, delete-orphan')
    
    def __init__(self, name, description, filename, file_path, script_type, user_id, file_size=None):
        self.name = name
        self.description = description
        self.filename = filename
        self.file_path = file_path
        self.script_type = script_type
        self.user_id = user_id
        self.file_size = file_size
    
    @property
    def file_exists(self):
        """Check if the script file still exists on disk"""
        return os.path.exists(self.file_path)
    
    @property
    def last_execution(self):
        """Get the most recent execution"""
        return Execution.query.filter_by(script_id=self.id).order_by(Execution.started_at.desc()).first()
    
    @property
    def active_schedule(self):
        """Get active schedule for this script"""
        return Schedule.query.filter_by(script_id=self.id, is_active=True).first()
    
    @property
    def execution_count(self):
        """Get total execution count"""
        return Execution.query.filter_by(script_id=self.id).count()
    
    @property
    def success_rate(self):
        """Calculate success rate percentage"""
        total = self.execution_count
        if total == 0:
            return 0
        successful = Execution.query.filter_by(
            script_id=self.id, 
            status='completed'
        ).count()
        return round((successful / total) * 100, 1)
    
    def get_formatted_size(self):
        """Get human-readable file size"""
        if not self.file_size:
            return "Unknown"
        
        for unit in ['B', 'KB', 'MB']:
            if self.file_size < 1024:
                return f"{self.file_size:.1f} {unit}"
            self.file_size /= 1024
        return f"{self.file_size:.1f} GB"
    
    def delete_file(self):
        """Delete the physical file from disk"""
        if self.file_exists:
            try:
                os.remove(self.file_path)
                return True
            except OSError:
                return False
        return True
    
    def __repr__(self):
        return f'<Script {self.name} ({self.script_type})>'