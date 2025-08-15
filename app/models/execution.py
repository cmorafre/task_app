"""
Execution Model - Script execution tracking and logging
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from enum import Enum

# Import db from models package
from app.models import db

class ExecutionStatus(Enum):
    """Execution status enumeration"""
    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    TIMEOUT = 'timeout'
    CANCELLED = 'cancelled'

class ExecutionTrigger(Enum):
    """Execution trigger type enumeration"""
    MANUAL = 'manual'
    SCHEDULED = 'scheduled'
    API = 'api'

class Execution(db.Model):
    """Execution model for tracking script runs and their results"""
    
    __tablename__ = 'executions'
    
    id = db.Column(db.Integer, primary_key=True)
    started_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    completed_at = db.Column(db.DateTime)
    status = db.Column(db.Enum(ExecutionStatus), default=ExecutionStatus.PENDING, nullable=False)
    trigger_type = db.Column(db.Enum(ExecutionTrigger), default=ExecutionTrigger.MANUAL, nullable=False)
    exit_code = db.Column(db.Integer)
    stdout = db.Column(db.Text)
    stderr = db.Column(db.Text)
    duration_seconds = db.Column(db.Float)
    pid = db.Column(db.Integer)  # Process ID when running
    
    # Foreign keys
    script_id = db.Column(db.Integer, db.ForeignKey('scripts.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    schedule_id = db.Column(db.Integer, db.ForeignKey('schedules.id'))  # Only for scheduled executions
    
    def __init__(self, script_id, user_id, trigger_type=ExecutionTrigger.MANUAL, schedule_id=None):
        self.script_id = script_id
        self.user_id = user_id
        self.trigger_type = trigger_type
        self.schedule_id = schedule_id
    
    @property
    def is_running(self):
        """Check if execution is currently running"""
        return self.status == ExecutionStatus.RUNNING
    
    @property
    def is_finished(self):
        """Check if execution is finished (success or failure)"""
        return self.status in [
            ExecutionStatus.COMPLETED, 
            ExecutionStatus.FAILED, 
            ExecutionStatus.TIMEOUT,
            ExecutionStatus.CANCELLED
        ]
    
    @property
    def is_successful(self):
        """Check if execution completed successfully"""
        return self.status == ExecutionStatus.COMPLETED and self.exit_code == 0
    
    @property
    def formatted_duration(self):
        """Get human-readable duration"""
        if not self.duration_seconds:
            return "N/A"
        
        if self.duration_seconds < 60:
            return f"{self.duration_seconds:.1f}s"
        elif self.duration_seconds < 3600:
            minutes = int(self.duration_seconds // 60)
            seconds = int(self.duration_seconds % 60)
            return f"{minutes}m {seconds}s"
        else:
            hours = int(self.duration_seconds // 3600)
            minutes = int((self.duration_seconds % 3600) // 60)
            return f"{hours}h {minutes}m"
    
    @property
    def status_icon(self):
        """Get status icon for UI display"""
        icons = {
            ExecutionStatus.PENDING: '⏳',
            ExecutionStatus.RUNNING: '🔄',
            ExecutionStatus.COMPLETED: '✅',
            ExecutionStatus.FAILED: '❌',
            ExecutionStatus.TIMEOUT: '⏰',
            ExecutionStatus.CANCELLED: '🛑'
        }
        return icons.get(self.status, '❓')
    
    @property
    def status_color(self):
        """Get Bootstrap color class for status"""
        colors = {
            ExecutionStatus.PENDING: 'secondary',
            ExecutionStatus.RUNNING: 'warning',
            ExecutionStatus.COMPLETED: 'success',
            ExecutionStatus.FAILED: 'danger',
            ExecutionStatus.TIMEOUT: 'warning',
            ExecutionStatus.CANCELLED: 'secondary'
        }
        return colors.get(self.status, 'secondary')
    
    def start_execution(self, pid=None):
        """Mark execution as started"""
        self.status = ExecutionStatus.RUNNING
        self.started_at = datetime.utcnow()
        self.pid = pid
        db.session.commit()
    
    def complete_execution(self, exit_code, stdout='', stderr=''):
        """Mark execution as completed"""
        self.completed_at = datetime.utcnow()
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        self.status = ExecutionStatus.COMPLETED if exit_code == 0 else ExecutionStatus.FAILED
        
        if self.started_at:
            self.duration_seconds = (self.completed_at - self.started_at).total_seconds()
        
        db.session.commit()
    
    def timeout_execution(self):
        """Mark execution as timed out"""
        self.completed_at = datetime.utcnow()
        self.status = ExecutionStatus.TIMEOUT
        self.exit_code = -1
        
        if self.started_at:
            self.duration_seconds = (self.completed_at - self.started_at).total_seconds()
        
        db.session.commit()
    
    def cancel_execution(self):
        """Mark execution as cancelled"""
        self.completed_at = datetime.utcnow()
        self.status = ExecutionStatus.CANCELLED
        self.exit_code = -2
        
        if self.started_at:
            self.duration_seconds = (self.completed_at - self.started_at).total_seconds()
        
        db.session.commit()
    
    def get_output_preview(self, max_lines=10):
        """Get a preview of the output (first and last lines)"""
        output = self.stdout or ''
        if not output:
            return "No output"
        
        lines = output.split('\n')
        if len(lines) <= max_lines:
            return output
        
        preview_lines = lines[:max_lines//2] + ['...'] + lines[-max_lines//2:]
        return '\n'.join(preview_lines)
    
    def __repr__(self):
        return f'<Execution {self.id} - {self.status.value}>'