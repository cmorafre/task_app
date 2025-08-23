#!/usr/bin/env python3
"""
ScriptFlow - Modular Architecture
Sistema de automação de scripts Python e Batch - Versão Modular
"""

import os
import socket
import time
import json
import threading
import subprocess
import tempfile
import atexit
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, redirect, url_for, jsonify, abort
from flask_login import LoginManager, UserMixin, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.memory import MemoryJobStore

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///scriptflow.db')
app.instance_relative_config = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.environ.get('UPLOAD_FOLDER', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB max file size

# Python interpreter configuration
app.config['PYTHON_EXECUTABLE'] = os.environ.get('PYTHON_EXECUTABLE', 'python3')
app.config['PYTHON_ENV'] = os.environ.get('PYTHON_ENV', None)

# Initialize extensions
db = SQLAlchemy(app)

# Set db for models package (CRITICAL: must be done before importing models)
# Note: models are now defined directly in this file, so this is not needed
# import app.models
# app.models.db = db

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access ScriptFlow.'

# Initialize scheduler
scheduler = None

# Template context processors
@app.context_processor
def inject_ui_version():
    """Inject UI version info into all templates - V2 only now"""
    return {
        'ui_info': {'current_version': 'v2', 'is_modern': True},
        'ui_version': 'v2',
        'is_modern_ui': True
    }

# Models
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    can_view_all_data = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    last_login = db.Column(db.DateTime)
    
    def set_password(self, password):
        """Set password hash for the user"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if provided password matches the stored hash"""
        return check_password_hash(self.password_hash, password)
    
    def update_last_login(self):
        """Update the last login timestamp"""
        self.last_login = datetime.now()
        db.session.commit()

class Script(db.Model):
    __tablename__ = 'scripts'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    script_type = db.Column(db.String(10), nullable=False)  # 'py' or 'bat'
    file_size = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    is_active = db.Column(db.Boolean, default=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    @property
    def file_exists(self):
        return os.path.exists(self.file_path)

class Execution(db.Model):
    __tablename__ = 'executions'
    id = db.Column(db.Integer, primary_key=True)
    started_at = db.Column(db.DateTime, default=datetime.now, nullable=False)
    completed_at = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='pending', nullable=False)  # pending, running, completed, failed, timeout
    exit_code = db.Column(db.Integer)
    stdout = db.Column(db.Text)
    stderr = db.Column(db.Text)
    duration_seconds = db.Column(db.Float)
    trigger_type = db.Column(db.String(20), default='manual', nullable=False)  # manual, scheduled, api
    script_id = db.Column(db.Integer, db.ForeignKey('scripts.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Relationship
    script = db.relationship('Script', backref='executions')
    
    @property
    def formatted_duration(self):
        if not self.duration_seconds:
            return "N/A"
        if self.duration_seconds < 60:
            return f"{self.duration_seconds:.1f}s"
        else:
            minutes = int(self.duration_seconds // 60)
            seconds = int(self.duration_seconds % 60)
            return f"{minutes}m {seconds}s"
    
    @property
    def status_icon(self):
        icons = {
            'pending': '⏳',
            'running': '🔄',
            'completed': '✅',
            'failed': '❌',
            'timeout': '⏰',
            'cancelled': '🛑'
        }
        return icons.get(self.status, '❓')
    
    @property
    def status_color(self):
        colors = {
            'pending': 'secondary',
            'running': 'running',
            'completed': 'success',
            'failed': 'danger',
            'timeout': 'warning',
            'cancelled': 'danger'
        }
        return colors.get(self.status, 'secondary')

class Settings(db.Model):
    __tablename__ = 'settings'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    description = db.Column(db.String(255))
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    @staticmethod
    def get_value(key, default=None):
        """Get setting value by key"""
        setting = Settings.query.filter_by(key=key).first()
        return setting.value if setting else default
    
    @staticmethod
    def set_value(key, value, description=None, user_id=1):
        """Set setting value by key"""
        setting = Settings.query.filter_by(key=key).first()
        if setting:
            setting.value = value
            setting.updated_by = user_id
            if description:
                setting.description = description
        else:
            setting = Settings(key=key, value=value, description=description, updated_by=user_id)
            db.session.add(setting)
        db.session.commit()
        return setting

class Schedule(db.Model):
    __tablename__ = 'schedules'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    frequency = db.Column(db.String(20), nullable=False)  # daily, weekly, monthly, custom
    time_config = db.Column(db.Text)  # JSON string with time configuration
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    next_run_time = db.Column(db.DateTime)
    last_execution_id = db.Column(db.Integer, db.ForeignKey('executions.id'))
    script_id = db.Column(db.Integer, db.ForeignKey('scripts.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Relationships
    script = db.relationship('Script', backref='schedules')
    user = db.relationship('User', backref='schedules')
    last_execution = db.relationship('Execution', foreign_keys=[last_execution_id])
    
    @property
    def time_config_json(self):
        """Parse time configuration JSON"""
        if self.time_config:
            try:
                return json.loads(self.time_config)
            except:
                return {}
        return {}
    
    @property
    def next_run_display(self):
        """Human readable next run time"""
        if not self.next_run_time:
            return "Not scheduled"
        
        now = datetime.now()
        delta = self.next_run_time - now
        
        if delta.total_seconds() < 0:
            return "Overdue"
        elif delta.total_seconds() < 3600:  # Less than 1 hour
            minutes = int(delta.total_seconds() / 60)
            return f"in {minutes}m"
        elif delta.total_seconds() < 86400:  # Less than 1 day
            hours = int(delta.total_seconds() / 3600)
            minutes = int((delta.total_seconds() % 3600) / 60)
            return f"in {hours}h {minutes}m"
        else:
            days = int(delta.total_seconds() / 86400)
            return f"in {days} days"
    
    @property
    def frequency_display(self):
        """Human readable frequency"""
        if self.frequency == 'daily':
            config = self.time_config_json
            if config.get('time'):
                return f"Daily at {config['time']}"
            return "Daily"
        elif self.frequency == 'weekly':
            config = self.time_config_json
            days = config.get('days', ['monday'])
            time = config.get('time', '09:00')
            if len(days) == 1:
                return f"{days[0].capitalize()} at {time}"
            return f"Weekly ({len(days)} days) at {time}"
        elif self.frequency == 'monthly':
            config = self.time_config_json
            day = config.get('day', 1)
            time = config.get('time', '09:00')
            return f"Monthly (day {day}) at {time}"
        elif self.frequency == 'custom':
            return "Custom schedule"
        return self.frequency.capitalize()
    
    def calculate_next_run(self):
        """Calculate next run time based on frequency and configuration"""
        config = self.time_config_json
        now = datetime.now()
        original_now = now
        
        # Check if we have a start date
        start_date_str = config.get('start_date')
        minimum_date = None
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
                if start_date.date() >= now.date():
                    minimum_date = start_date.date()
            except ValueError:
                pass
        
        if self.frequency == 'daily':
            time_str = config.get('time', '09:00')
            hour, minute = map(int, time_str.split(':'))
            
            if minimum_date and minimum_date > now.date():
                next_run = datetime.combine(minimum_date, datetime.min.time())
                next_run = next_run.replace(hour=hour, minute=minute, second=0, microsecond=0)
            else:
                next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if next_run <= original_now:
                    next_run += timedelta(days=1)
                
        elif self.frequency == 'weekly':
            time_str = config.get('time', '09:00')
            hour, minute = map(int, time_str.split(':'))
            days = config.get('days', ['monday'])
            
            # Map day names to numbers (0=Monday)
            day_map = {'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3, 
                      'friday': 4, 'saturday': 5, 'sunday': 6}
            
            # Find next occurrence
            current_weekday = original_now.weekday()
            target_days = [day_map[day.lower()] for day in days if day.lower() in day_map]
            target_days.sort()
            
            next_run = None
            for target_day in target_days:
                days_ahead = target_day - current_weekday
                if days_ahead < 0:
                    days_ahead += 7
                elif days_ahead == 0:
                    candidate = original_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    if candidate > original_now:
                        next_run = candidate
                        break
                    else:
                        days_ahead = 7
                
                candidate = original_now.replace(hour=hour, minute=minute, second=0, microsecond=0) + timedelta(days=days_ahead)
                if not next_run or candidate < next_run:
                    next_run = candidate
            
            if minimum_date and next_run and next_run.date() < minimum_date:
                while next_run.date() < minimum_date:
                    next_run += timedelta(days=7)
                    
        elif self.frequency == 'monthly':
            time_str = config.get('time', '09:00')
            hour, minute = map(int, time_str.split(':'))
            target_day = config.get('day', 1)
            
            try:
                next_run = original_now.replace(day=target_day, hour=hour, minute=minute, second=0, microsecond=0)
                if next_run <= original_now:
                    raise ValueError("Time passed")
            except (ValueError, OverflowError):
                if original_now.month == 12:
                    next_year = original_now.year + 1
                    next_month = 1
                else:
                    next_year = original_now.year
                    next_month = original_now.month + 1
                
                next_run = original_now.replace(year=next_year, month=next_month, day=min(target_day, 28), 
                                     hour=hour, minute=minute, second=0, microsecond=0)
            
            if minimum_date and next_run.date() < minimum_date:
                while next_run.date() < minimum_date:
                    if next_run.month == 12:
                        next_run = next_run.replace(year=next_run.year + 1, month=1)
                    else:
                        next_run = next_run.replace(month=next_run.month + 1)
        elif self.frequency == 'interval':
            interval_minutes = config.get('interval_minutes', 15)
            start_time = config.get('time', '09:00')
            
            try:
                interval_minutes = int(interval_minutes)
                if interval_minutes <= 0:
                    interval_minutes = 15
            except (ValueError, TypeError):
                interval_minutes = 15
            
            try:
                hour, minute = map(int, start_time.split(':'))
                
                if minimum_date and minimum_date > now.date():
                    first_run = datetime.combine(minimum_date, datetime.min.time())
                    first_run = first_run.replace(hour=hour, minute=minute, second=0, microsecond=0)
                else:
                    first_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                if first_run <= now:
                    time_diff = now - first_run
                    intervals_passed = int(time_diff.total_seconds() // (interval_minutes * 60))
                    next_run = first_run + timedelta(minutes=(intervals_passed + 1) * interval_minutes)
                else:
                    next_run = first_run
                    
            except (ValueError, AttributeError):
                next_run = now + timedelta(minutes=interval_minutes)
        else:
            # Default to daily at 9 AM for unknown frequencies
            next_run = original_now.replace(hour=9, minute=0, second=0, microsecond=0)
            if next_run <= original_now:
                next_run += timedelta(days=1)
            
            if minimum_date and next_run.date() < minimum_date:
                next_run = datetime.combine(minimum_date, next_run.time())
        
        self.next_run_time = next_run
        return next_run

# === NEW INTEGRATION FEATURE MODELS (NON-BREAKING ADDITION) ===

class DataSource(db.Model):
    """DataSource model for managing database connections in Integration feature"""
    
    __tablename__ = 'datasources'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    db_type = db.Column(db.String(20), nullable=False)  # 'oracle' or 'postgres'
    host = db.Column(db.String(255), nullable=False)
    port = db.Column(db.Integer, nullable=False)
    database = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(100), nullable=False)
    encrypted_password = db.Column(db.Text, nullable=False)  # Encrypted password
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    def set_password(self, password):
        """Encrypt and store password"""
        from cryptography.fernet import Fernet
        encryption_key = self._get_encryption_key()
        f = Fernet(encryption_key)
        self.encrypted_password = f.encrypt(password.encode()).decode()
    
    def get_password(self):
        """Decrypt and return password"""
        from cryptography.fernet import Fernet
        encryption_key = self._get_encryption_key()
        f = Fernet(encryption_key)
        return f.decrypt(self.encrypted_password.encode()).decode()
    
    def _get_encryption_key(self):
        """Get or create encryption key"""
        key = Settings.get_value('datasource_encryption_key')
        if not key:
            from cryptography.fernet import Fernet
            key = Fernet.generate_key().decode()
            Settings.set_value('datasource_encryption_key', key, 'Encryption key for datasource passwords')
        return key.encode() if isinstance(key, str) else key
    
    @property
    def connection_string(self):
        """Generate connection string based on db_type"""
        if self.db_type == 'oracle':
            return f"oracle+cx_oracle://{self.username}:{self.get_password()}@{self.host}:{self.port}/{self.database}"
        elif self.db_type == 'postgres':
            return f"postgresql+psycopg2://{self.username}:{self.get_password()}@{self.host}:{self.port}/{self.database}"
        else:
            raise ValueError(f"Unsupported database type: {self.db_type}")
    
    @property
    def display_connection(self):
        """Safe connection string for display (without password)"""
        return f"{self.db_type}://{self.username}@{self.host}:{self.port}/{self.database}"
    
    def test_connection(self):
        """Test database connection"""
        try:
            from sqlalchemy import create_engine, text
            
            # Configure connection args based on database type
            if self.db_type == 'postgres':
                connect_args = {'connect_timeout': 10}
            else:  # oracle
                connect_args = {'timeout': 10}
            
            engine = create_engine(self.connection_string, connect_args=connect_args)
            
            with engine.connect() as conn:
                if self.db_type == 'oracle':
                    result = conn.execute(text("SELECT 1 FROM DUAL"))
                else:  # postgres
                    result = conn.execute(text("SELECT 1"))
                
                result.fetchone()
                return True, "Connection successful"
                
        except Exception as e:
            return False, str(e)
    
    # Relationship properties - added after Integration model definition
    @property
    def integrations_as_source(self):
        """Get integrations where this datasource is used as source"""
        # Import here to avoid circular imports
        Integration = globals().get('Integration')
        if Integration:
            return Integration.query.filter_by(source_id=self.id).all()
        return []
    
    @property
    def integrations_as_target(self):
        """Get integrations where this datasource is used as target"""
        # Import here to avoid circular imports
        Integration = globals().get('Integration')
        if Integration:
            return Integration.query.filter_by(target_id=self.id).all()
        return []

class Integration(db.Model):
    """Integration model for managing ETL jobs (Extract-Transform-Load)"""
    
    __tablename__ = 'integrations'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    extract_sql = db.Column(db.Text, nullable=False)  # SQL query for data extraction
    load_sql = db.Column(db.Text, nullable=False)     # SQL query for data loading
    python_script_id = db.Column(db.Integer, db.ForeignKey('scripts.id'), nullable=True)
    source_id = db.Column(db.Integer, db.ForeignKey('datasources.id'), nullable=False)
    target_id = db.Column(db.Integer, db.ForeignKey('datasources.id'), nullable=False)
    config_json = db.Column(db.Text)  # Additional configuration as JSON
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Relationships
    source_datasource = db.relationship('DataSource', foreign_keys=[source_id])
    target_datasource = db.relationship('DataSource', foreign_keys=[target_id])
    python_script = db.relationship('Script', backref='integrations_using_script')
    
    @property
    def has_python_transformation(self):
        """Check if integration has Python transformation script"""
        return self.python_script_id is not None
    
    @property
    def etl_type(self):
        """Get ETL type description"""
        if self.has_python_transformation:
            return "Extract → Transform (Python) → Load"
        else:
            return "Extract → Load (Direct)"
    
    @property
    def last_execution(self):
        """Get the most recent execution"""
        return IntegrationExecution.query.filter_by(integration_id=self.id)\
                                        .order_by(IntegrationExecution.started_at.desc())\
                                        .first()
    
    @property
    def execution_count(self):
        """Get total execution count"""
        return IntegrationExecution.query.filter_by(integration_id=self.id).count()
    
    @property
    def success_rate(self):
        """Calculate success rate percentage"""
        total = self.execution_count
        if total == 0:
            return 0
        
        successful = IntegrationExecution.query.filter_by(
            integration_id=self.id,
            status='completed'
        ).count()
        return round((successful / total) * 100, 1)
    
    @property
    def status_summary(self):
        """Get status summary for dashboard"""
        last_exec = self.last_execution
        
        if not last_exec:
            return {'status': 'never_run', 'message': 'Never executed', 'color': 'secondary'}
        
        status_map = {
            'completed': {'message': 'Last run successful', 'color': 'success'},
            'failed': {'message': 'Last run failed', 'color': 'danger'},
            'running': {'message': 'Currently running', 'color': 'running'},
            'timeout': {'message': 'Last run timed out', 'color': 'warning'},
            'cancelled': {'message': 'Last run cancelled', 'color': 'warning'}
        }
        
        status_info = status_map.get(last_exec.status, {'message': 'Unknown status', 'color': 'secondary'})
        
        return {
            'status': last_exec.status,
            'message': status_info['message'],
            'color': status_info['color'],
            'last_run': last_exec.started_at
        }
    
    def validate_sql_queries(self):
        """Validate SQL queries (basic validation)"""
        errors = []
        
        # Basic validation for extract query (should be SELECT only)
        extract_sql_clean = self.extract_sql.strip().upper()
        if not extract_sql_clean.startswith('SELECT'):
            errors.append("Extract SQL must be a SELECT query")
        
        # Check for dangerous operations in extract query
        dangerous_keywords = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'CREATE', 'ALTER', 'TRUNCATE']
        for keyword in dangerous_keywords:
            if keyword in extract_sql_clean:
                errors.append(f"Extract SQL cannot contain {keyword} operations")
        
        # Basic validation for load query
        load_sql_clean = self.load_sql.strip().upper()
        if not (load_sql_clean.startswith('INSERT') or load_sql_clean.startswith('UPDATE') or 
                load_sql_clean.startswith('MERGE') or load_sql_clean.startswith('UPSERT')):
            errors.append("Load SQL must be an INSERT, UPDATE, MERGE, or UPSERT query")
        
        return errors

class IntegrationExecution(db.Model):
    """IntegrationExecution model for tracking ETL job execution history"""
    
    __tablename__ = 'integration_executions'
    
    id = db.Column(db.Integer, primary_key=True)
    started_at = db.Column(db.DateTime, default=datetime.now, nullable=False)
    completed_at = db.Column(db.DateTime)
    duration_seconds = db.Column(db.Float)
    status = db.Column(db.String(20), default='pending', nullable=False)  # pending, running, completed, failed, timeout, cancelled
    exit_code = db.Column(db.Integer)
    records_extracted = db.Column(db.Integer, default=0)
    records_loaded = db.Column(db.Integer, default=0)
    records_failed = db.Column(db.Integer, default=0)
    extract_output = db.Column(db.Text)  # Output from extract phase
    transform_output = db.Column(db.Text)  # Output from transform phase (Python script)
    load_output = db.Column(db.Text)  # Output from load phase
    error_message = db.Column(db.Text)  # Error details if failed
    logs = db.Column(db.Text)  # Detailed execution logs
    trigger_type = db.Column(db.String(20), default='manual', nullable=False)  # manual, scheduled, api
    integration_id = db.Column(db.Integer, db.ForeignKey('integrations.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    schedule_id = db.Column(db.Integer, db.ForeignKey('schedules.id'), nullable=True)
    
    # Relationships
    integration = db.relationship('Integration', backref='executions')
    
    @property
    def is_running(self):
        """Check if execution is currently running"""
        return self.status == 'running'
    
    @property
    def is_completed(self):
        """Check if execution completed successfully"""
        return self.status == 'completed'
    
    @property
    def is_failed(self):
        """Check if execution failed"""
        return self.status in ['failed', 'timeout', 'cancelled']
    
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
        """Get status icon"""
        icons = {
            'pending': '⏳',
            'running': '🔄',
            'completed': '✅',
            'failed': '❌',
            'timeout': '⏰',
            'cancelled': '🛑'
        }
        return icons.get(self.status, '❓')
    
    @property
    def status_color(self):
        """Get status color for UI"""
        colors = {
            'pending': 'secondary',
            'running': 'running',
            'completed': 'success',
            'failed': 'danger',
            'timeout': 'warning',
            'cancelled': 'danger'
        }
        return colors.get(self.status, 'secondary')

# === END NEW INTEGRATION MODELS ===

# User loader
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Helper function to apply data filters based on user permissions
def apply_user_data_filter(query):
    """Apply data filter based on user permissions"""
    if current_user.can_view_all_data:
        return query  # Can see all data
    else:
        return query.filter_by(user_id=current_user.id)  # Only own data

# Global variables for script execution
running_processes = {}

# Scheduler functions
def init_scheduler():
    """Initialize APScheduler if not already initialized"""
    global scheduler
    if scheduler is None:
        try:
            if os.environ.get('WERKZEUG_RUN_MAIN'):
                jobstores = {
                    'default': MemoryJobStore()
                }
                scheduler = BackgroundScheduler(jobstores=jobstores)
                scheduler.start()
                atexit.register(lambda: scheduler.shutdown())
                print(f"✅ Scheduler initialized (main process)")
                
                reload_active_schedules()
            else:
                print("ℹ️ Scheduler not initialized (reloader process)")
        except Exception as e:
            print(f"❌ Error initializing scheduler: {e}")
            raise

def reload_active_schedules():
    """Reload all active schedules into the scheduler (for MemoryJobStore)"""
    global scheduler
    
    if scheduler is None:
        return
    
    existing_jobs = scheduler.get_jobs()
    if existing_jobs:
        print(f"ℹ️ Scheduler already has {len(existing_jobs)} jobs, skipping reload")
        return
    
    try:
        active_schedules = Schedule.query.filter_by(is_active=True).all()
        
        loaded_count = 0
        for schedule in active_schedules:
            if schedule.next_run_time:
                try:
                    add_schedule_to_scheduler(schedule)
                    loaded_count += 1
                except Exception as e:
                    print(f"⚠️ Failed to reload schedule {schedule.name}: {e}")
        
        print(f"✅ Loaded {loaded_count} active schedules into scheduler")
    except Exception as e:
        print(f"❌ Error reloading schedules: {e}")

def add_schedule_to_scheduler(schedule):
    """Add schedule to APScheduler"""
    global scheduler
    
    if scheduler is None:
        init_scheduler()
    
    job_id = f"schedule_{schedule.id}"
    
    try:
        existing_job = scheduler.get_job(job_id)
        if existing_job and existing_job.next_run_time == schedule.next_run_time:
            print(f"🔄 Job {job_id} already scheduled for {schedule.next_run_time}, skipping")
            return
    except:
        pass
    
    try:
        scheduler.remove_job(job_id)
    except:
        pass
    
    if not schedule.is_active or not schedule.next_run_time:
        return
    
    scheduler.add_job(
        id=job_id,
        func=execute_scheduled_script,
        args=[schedule.id],
        trigger='date',
        run_date=schedule.next_run_time,
        replace_existing=True
    )
    print(f"➕ Added job {job_id} scheduled for {schedule.next_run_time}")

def remove_schedule_from_scheduler(schedule_id):
    """Remove schedule from APScheduler"""
    global scheduler
    
    if scheduler is None:
        init_scheduler()
    
    job_id = f"schedule_{schedule_id}"
    try:
        scheduler.remove_job(job_id)
        print(f"🗑️ Removed job {job_id} from scheduler")
    except Exception as e:
        from apscheduler.jobstores.base import JobLookupError
        
        if isinstance(e, JobLookupError):
            print(f"ℹ️ Job {job_id} was already removed or not found in scheduler")
        else:
            print(f"⚠️ Unexpected error removing job {job_id}: {e}")
        pass

def execute_script_background(execution_id, script_path, script_type):
    """Execute script in background thread"""
    with app.app_context():
        execution = db.session.get(Execution, execution_id)
        if not execution:
            return
        
        try:
            # Update status to running
            execution.status = 'running'
            execution.started_at = datetime.now()
            db.session.commit()
            
            # Make sure script_path is absolute
            if not os.path.isabs(script_path):
                script_path = os.path.abspath(script_path)
            
            script_dir = os.path.dirname(script_path)
            
            # Build command with configured Python interpreter
            if script_type == 'py':
                python_exec = Settings.get_value('python_executable', app.config['PYTHON_EXECUTABLE'])
                python_env = Settings.get_value('python_env', app.config['PYTHON_ENV'])
                
                if python_env:
                    python_exec = os.path.join(python_env, 'bin', 'python')
                    if not os.path.exists(python_exec):
                        python_exec = os.path.join(python_env, 'Scripts', 'python.exe')
                
                cmd = [python_exec, script_path]
            elif script_type == 'bat':
                if os.name == 'nt':
                    cmd = ['cmd', '/c', script_path]
                else:
                    cmd = ['bash', script_path]
            else:
                raise Exception(f"Unsupported script type: {script_type}")
            
            start_time = datetime.now()
            result = subprocess.run(
                cmd,
                cwd=script_dir,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )
            end_time = datetime.now()
            
            # Update execution record
            execution.completed_at = end_time
            execution.exit_code = result.returncode
            execution.stdout = result.stdout
            execution.stderr = result.stderr
            execution.duration_seconds = (end_time - start_time).total_seconds()
            execution.status = 'completed' if result.returncode == 0 else 'failed'
            
            db.session.commit()

        except subprocess.TimeoutExpired:
            execution.completed_at = datetime.now()
            execution.status = 'timeout'
            execution.stderr = "Script execution timed out (5 minutes)"
            execution.duration_seconds = 300
            db.session.commit()
        
        except Exception as e:
            execution.completed_at = datetime.now()
            execution.status = 'failed'
            execution.stderr = str(e)
            execution.exit_code = -1
            db.session.commit()

def execute_scheduled_script(schedule_id):
    """Execute script from schedule (called by APScheduler)"""
    with app.app_context():
        try:
            schedule = db.session.get(Schedule, schedule_id)
            if not schedule or not schedule.is_active:
                print(f"❌ Schedule {schedule_id} not found or inactive")
                return
            
            script = schedule.script
            if not script or not script.file_exists:
                print(f"❌ Script not found or file missing for schedule {schedule.name}")
                return
            
            print(f"🚀 Executing scheduled script: {schedule.name}")
            
            # Create execution record
            execution = Execution(
                script_id=script.id,
                user_id=schedule.user_id,
                status='pending',
                trigger_type='scheduled'
            )
            db.session.add(execution)
            db.session.commit()
            print(f"💾 Execution record created with ID: {execution.id}")
            
            # Update schedule's last execution
            schedule.last_execution_id = execution.id
            
            schedule_id_safe = schedule.id
            schedule_name_safe = schedule.name
            
            try:
                remove_schedule_from_scheduler(schedule_id_safe)
                
                with db.session.no_autoflush:
                    old_next_run = schedule.next_run_time
                    print(f"📅 Schedule {schedule_name_safe}: Calculating next run from {old_next_run}")
                    
                    schedule.calculate_next_run()
                    new_next_run = schedule.next_run_time
                    
                    print(f"📅 Schedule {schedule_name_safe}: Updated next run to {new_next_run}")
                
                max_retries = 3
                for retry in range(max_retries):
                    try:
                        db.session.commit()
                        break
                    except Exception as e:
                        if retry < max_retries - 1:
                            print(f"⚠️ Database commit failed (retry {retry + 1}/{max_retries}): {e}")
                            time.sleep(0.1 * (retry + 1))
                            db.session.rollback()
                        else:
                            print(f"❌ Database commit failed after {max_retries} retries: {e}")
                            db.session.rollback()
                            raise
            except Exception as e:
                print(f"❌ Error in schedule update process: {e}")
                db.session.rollback()
                raise
            print(f"💾 Schedule updated with last_execution_id: {execution.id}")
            
            if schedule.next_run_time and schedule.is_active:
                add_schedule_to_scheduler(schedule)
                print(f"✅ Schedule {schedule.name} re-scheduled for {schedule.next_run_time}")
            else:
                print(f"❌ Schedule {schedule.name} not re-scheduled (active: {schedule.is_active}, next_run: {schedule.next_run_time})")
            
            # Execute script in background
            thread = threading.Thread(target=execute_script_background, args=(execution.id, script.file_path, script.script_type))
            thread.daemon = True
            thread.start()
            print(f"🔄 Script execution started in background for {schedule.name}")
            
        except Exception as e:
            print(f"❌ Error in execute_scheduled_script for schedule {schedule_id}: {str(e)}")
            import traceback
            traceback.print_exc()
            try:
                db.session.rollback()
            except:
                pass

# Register Blueprints
def register_blueprints():
    """Register all application blueprints"""
    
    # Import blueprints
    from app.controllers.auth import init_auth_blueprint
    from app.controllers.main import init_main_blueprint
    from app.controllers.scripts import init_scripts_blueprint
    from app.controllers.schedules import init_schedules_blueprint
    from app.controllers.logs import init_logs_blueprint, init_api_blueprint
    from app.controllers.admin import init_admin_blueprint
    
    # NEW: Integration feature blueprints (NON-BREAKING ADDITION)
    from app.controllers.integrations import init_integrations_blueprint
    from app.controllers.datasources import init_datasources_blueprint
    
    # Initialize and register blueprints
    auth_bp = init_auth_blueprint(db, User)
    main_bp = init_main_blueprint(app, db, User, Script, Execution, Schedule, Settings, apply_user_data_filter)
    scripts_bp = init_scripts_blueprint(app, db, Script, Execution, Settings, apply_user_data_filter)
    schedules_bp = init_schedules_blueprint(app, db, Schedule, Script, Execution, apply_user_data_filter, 
                                          add_schedule_to_scheduler, remove_schedule_from_scheduler, 
                                          execute_script_background)
    logs_bp = init_logs_blueprint(db, Execution, apply_user_data_filter)
    api_bp = init_api_blueprint(db, Execution, apply_user_data_filter)
    admin_bp = init_admin_blueprint(db, User, Script, Execution, Schedule)
    
    # NEW: Initialize Integration feature blueprints (NON-BREAKING ADDITION)
    integrations_bp = init_integrations_blueprint(app, db, Integration, IntegrationExecution, DataSource, Script, Schedule, apply_user_data_filter)
    datasources_bp = init_datasources_blueprint(app, db, DataSource, apply_user_data_filter)
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(scripts_bp)
    app.register_blueprint(schedules_bp)
    app.register_blueprint(logs_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(admin_bp)
    
    # NEW: Register Integration feature blueprints (NON-BREAKING ADDITION)
    app.register_blueprint(integrations_bp)
    app.register_blueprint(datasources_bp)
    
    # Initialize connection manager with DataSource model
    from app.services.connection_manager import connection_manager
    connection_manager.set_datasource_model(DataSource)
    
    print("✅ All blueprints registered successfully (including Integration feature)")

# Root route
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))

def find_free_port(start_port=8000):
    """Find a free port starting from start_port"""
    for port in range(start_port, start_port + 100):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return port
        except OSError:
            continue
    return 8000

if __name__ == '__main__':
    # Setup database and directories
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    
    with app.app_context():
        db.create_all()
        
        # Initialize scheduler after database is ready
        init_scheduler()
        
        # Create default admin user if none exists
        if not User.query.filter_by(username='admin').first():
            admin_user = User(
                username='admin',
                email='admin@scriptflow.local',
                is_admin=True,
                can_view_all_data=True
            )
            admin_user.set_password('admin123')
            db.session.add(admin_user)
            db.session.commit()
            print("✅ Created default admin user: admin/admin123")
    
    # Register blueprints
    register_blueprints()
    
    # Find free port and start
    port = find_free_port()
    print(f"\n🚀 ScriptFlow (Modular) starting on http://localhost:{port}")
    print("👤 Default login: admin/admin123")
    print("🛑 Press Ctrl+C to stop\n")
    
    app.run(debug=True, host='0.0.0.0', port=port)