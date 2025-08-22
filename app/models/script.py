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
    script_type = db.Column(db.String(10), nullable=False)  # 'py', 'bat', or 'sql'
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
    
    # === NEW INTEGRATION FEATURE METHODS (NON-BREAKING ADDITIONS) ===
    
    @property
    def is_sql_script(self):
        """Check if script is SQL type (NEW - Integration feature)"""
        return self.script_type == 'sql'
    
    @property
    def is_python_script(self):
        """Check if script is Python type (NEW - Integration feature)"""
        return self.script_type == 'py'
    
    @property
    def is_batch_script(self):
        """Check if script is Batch type (NEW - Integration feature)"""
        return self.script_type == 'bat'
    
    @property
    def can_be_used_in_integration(self):
        """Check if script can be used in Integration ETL jobs (NEW)"""
        return self.script_type in ['py', 'sql'] and self.is_active
    
    def get_script_content(self):
        """Get script file content (NEW - Integration feature)"""
        if not self.file_exists:
            return None
        
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except (IOError, UnicodeDecodeError):
            try:
                # Try with different encoding
                with open(self.file_path, 'r', encoding='latin-1') as f:
                    return f.read()
            except (IOError, UnicodeDecodeError):
                return None
    
    def validate_sql_content(self):
        """Validate SQL script content for Integration use (NEW)"""
        if not self.is_sql_script:
            return [], []  # No errors, no warnings
        
        content = self.get_script_content()
        if not content:
            return ["Cannot read script content"], []
        
        errors = []
        warnings = []
        content_upper = content.upper()
        
        # Check for dangerous SQL operations
        dangerous_ops = ['DROP', 'DELETE', 'TRUNCATE', 'CREATE', 'ALTER']
        for op in dangerous_ops:
            if op in content_upper:
                errors.append(f"SQL script contains potentially dangerous operation: {op}")
        
        # Check for common SQL patterns
        if 'SELECT' not in content_upper:
            warnings.append("SQL script does not contain SELECT statement")
        
        if ';' not in content:
            warnings.append("SQL script should end with semicolon")
        
        return errors, warnings
    
    @property
    def integration_usage_count(self):
        """Count how many integrations use this script (NEW)"""
        try:
            # Import here to avoid circular imports
            from app.models.integration import Integration
            return Integration.query.filter_by(python_script_id=self.id).count()
        except ImportError:
            return 0
    
    @property
    def is_used_in_integrations(self):
        """Check if script is used in any integrations (NEW)"""
        return self.integration_usage_count > 0
    
    def get_integration_usage(self):
        """Get list of integrations using this script (NEW)"""
        try:
            # Import here to avoid circular imports
            from app.models.integration import Integration
            return Integration.query.filter_by(python_script_id=self.id).all()
        except ImportError:
            return []
    
    # === END NEW INTEGRATION METHODS ===
    
    def __repr__(self):
        return f'<Script {self.name} ({self.script_type})>'