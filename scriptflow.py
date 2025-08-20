#!/usr/bin/env python3
"""
ScriptFlow - Aplicação Completa e Autocontida
Sistema de automação de scripts Python e Batch
"""

import os
import socket
import time
from flask import Flask, render_template, request, flash, redirect, url_for, jsonify, abort, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import subprocess
import tempfile
import threading
import json
from functools import wraps
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.memory import MemoryJobStore
import atexit

# Import UI Version Manager
from config.ui_version import UIVersionManager

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
# Configure Flask to use instance folder for database
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///scriptflow.db')
app.instance_relative_config = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.environ.get('UPLOAD_FOLDER', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB max file size

# Python interpreter configuration
app.config['PYTHON_EXECUTABLE'] = os.environ.get('PYTHON_EXECUTABLE', 'python3')
app.config['PYTHON_ENV'] = os.environ.get('PYTHON_ENV', None)  # Optional virtual environment path

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access ScriptFlow.'

# Initialize scheduler (will be configured later after database is ready)
scheduler = None

# Template context processors
@app.context_processor
def inject_ui_version():
    """Inject UI version info into all templates"""
    try:
        return {
            'ui_info': UIVersionManager.get_ui_display_info(),
            'ui_version': UIVersionManager.get_ui_version(),
            'is_modern_ui': UIVersionManager.is_modern_ui()
        }
    except:
        # Fallback if there are any issues
        return {
            'ui_info': {},
            'ui_version': 'v1',
            'is_modern_ui': False
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
            'running': '🔄',  # Emoji simples que funciona bem
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
            'running': 'running',  # Usar classe CSS personalizada com animação
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
        
        now = datetime.now()  # Use local time instead of UTC
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
        now = datetime.now()  # Use local time instead of UTC
        original_now = now  # Keep original time for comparison
        
        # Check if we have a start date
        start_date_str = config.get('start_date')
        minimum_date = None
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
                # If start date is today or in the future, use it as the minimum date
                if start_date.date() >= now.date():
                    minimum_date = start_date.date()
            except ValueError:
                pass
        
        if self.frequency == 'daily':
            time_str = config.get('time', '09:00')
            hour, minute = map(int, time_str.split(':'))
            
            if minimum_date and minimum_date > now.date():
                # If we have a future start date, use it
                next_run = datetime.combine(minimum_date, datetime.min.time())
                next_run = next_run.replace(hour=hour, minute=minute, second=0, microsecond=0)
            else:
                # Start with today's time
                next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                # If time has passed today, schedule for tomorrow
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
                if days_ahead < 0:  # Target day already happened this week
                    days_ahead += 7
                elif days_ahead == 0:  # Today
                    candidate = original_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    if candidate > original_now:
                        next_run = candidate
                        break
                    else:
                        days_ahead = 7
                
                candidate = original_now.replace(hour=hour, minute=minute, second=0, microsecond=0) + timedelta(days=days_ahead)
                if not next_run or candidate < next_run:
                    next_run = candidate
            
            # Apply minimum date if specified
            if minimum_date and next_run and next_run.date() < minimum_date:
                # Find the first occurrence on or after minimum_date
                while next_run.date() < minimum_date:
                    next_run += timedelta(days=7)
                    
        elif self.frequency == 'monthly':
            time_str = config.get('time', '09:00')
            hour, minute = map(int, time_str.split(':'))
            target_day = config.get('day', 1)
            
            # Try current month first
            try:
                next_run = original_now.replace(day=target_day, hour=hour, minute=minute, second=0, microsecond=0)
                if next_run <= original_now:
                    raise ValueError("Time passed")
            except (ValueError, OverflowError):
                # Move to next month
                if original_now.month == 12:
                    next_year = original_now.year + 1
                    next_month = 1
                else:
                    next_year = original_now.year
                    next_month = original_now.month + 1
                
                next_run = original_now.replace(year=next_year, month=next_month, day=min(target_day, 28), 
                                     hour=hour, minute=minute, second=0, microsecond=0)
            
            # Apply minimum date if specified
            if minimum_date and next_run.date() < minimum_date:
                # Find the first monthly occurrence on or after minimum_date
                while next_run.date() < minimum_date:
                    if next_run.month == 12:
                        next_run = next_run.replace(year=next_run.year + 1, month=1)
                    else:
                        next_run = next_run.replace(month=next_run.month + 1)
        elif self.frequency == 'interval':
            # Handle interval frequency
            interval_minutes = config.get('interval_minutes', 15)
            start_time = config.get('time', '09:00')
            
            try:
                interval_minutes = int(interval_minutes)
                if interval_minutes <= 0:
                    interval_minutes = 15
            except (ValueError, TypeError):
                interval_minutes = 15
            
            try:
                # Parse start time
                hour, minute = map(int, start_time.split(':'))
                
                # Determine the start datetime
                if minimum_date and minimum_date > now.date():
                    # Future start date
                    first_run = datetime.combine(minimum_date, datetime.min.time())
                    first_run = first_run.replace(hour=hour, minute=minute, second=0, microsecond=0)
                else:
                    # Use today with specified time
                    first_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                # If first run is in the past, calculate next interval-based execution
                if first_run <= now:
                    # Calculate how many intervals have passed since first_run
                    time_diff = now - first_run
                    intervals_passed = int(time_diff.total_seconds() // (interval_minutes * 60))
                    # Next execution is first_run + (intervals_passed + 1) * interval
                    next_run = first_run + timedelta(minutes=(intervals_passed + 1) * interval_minutes)
                else:
                    # First run is in the future, use it
                    next_run = first_run
                    
            except (ValueError, AttributeError):
                # Fallback to current time + interval if parsing fails
                next_run = now + timedelta(minutes=interval_minutes)
        else:
            # Default to daily at 9 AM for unknown frequencies
            next_run = original_now.replace(hour=9, minute=0, second=0, microsecond=0)
            if next_run <= original_now:
                next_run += timedelta(days=1)
            
            # Apply minimum date if specified
            if minimum_date and next_run.date() < minimum_date:
                next_run = datetime.combine(minimum_date, next_run.time())
        
        self.next_run_time = next_run
        return next_run

# User loader
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Admin decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)  # Forbidden
        return f(*args, **kwargs)
    return decorated_function

# Helper function to apply data filters based on user permissions
def apply_user_data_filter(query):
    """Apply data filter based on user permissions"""
    if current_user.can_view_all_data:
        return query  # Can see all data
    else:
        return query.filter_by(user_id=current_user.id)  # Only own data

# Global variables for script execution
running_processes = {}

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))
        
        if not username or not password:
            flash('Please enter both username and password.', 'error')
            return render_template(UIVersionManager.get_template_path('login.html'))
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user, remember=remember)
            user.update_last_login()
            flash(f'Welcome back, {user.username}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'error')
    
    return render_template(UIVersionManager.get_template_path('login.html'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validation
        if not username or not email or not password:
            flash('Please fill in all required fields.', 'error')
            return render_template(UIVersionManager.get_template_path('register.html'))
        
        if len(username) < 3:
            flash('Username must be at least 3 characters long.', 'error')
            return render_template(UIVersionManager.get_template_path('register.html'))
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return render_template(UIVersionManager.get_template_path('register.html'))
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template(UIVersionManager.get_template_path('register.html'))
        
        # Check if username or email already exists
        existing_user = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()
        
        if existing_user:
            if existing_user.username == username:
                flash('Username already exists. Please choose a different username.', 'error')
            else:
                flash('Email already registered. Please use a different email.', 'error')
            return render_template(UIVersionManager.get_template_path('register.html'))
        
        # Create new user
        try:
            new_user = User(
                username=username,
                email=email
            )
            new_user.set_password(password)
            
            db.session.add(new_user)
            db.session.commit()
            
            flash(f'Account created successfully! Welcome, {username}!', 'success')
            
            # Auto-login the new user
            login_user(new_user)
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            db.session.rollback()
            import traceback
            error_details = traceback.format_exc()
            print(f"Registration error: {e}")
            print(f"Full traceback: {error_details}")
            flash('An error occurred while creating your account. Please try again.', 'error')
    
    return render_template(UIVersionManager.get_template_path('register.html'))

@app.route('/logout')
@login_required
def logout():
    username = current_user.username
    logout_user()
    flash(f'Goodbye, {username}!', 'info')
    return redirect(url_for('login'))

# User Management Routes (Admin Only)
@app.route('/admin/users')
@login_required
@admin_required
def manage_users():
    """User management page for admins"""
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template(UIVersionManager.get_template_path('admin/users.html'), users=users)

@app.route('/admin/users/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_user():
    """Create new user (admin only)"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        is_admin = bool(request.form.get('is_admin'))
        can_view_all_data = bool(request.form.get('can_view_all_data'))
        
        # Validation
        if not username or not email or not password:
            flash('Please fill in all required fields.', 'error')
            return render_template(UIVersionManager.get_template_path('admin/create_user.html'))
        
        if len(username) < 3:
            flash('Username must be at least 3 characters long.', 'error')
            return render_template(UIVersionManager.get_template_path('admin/create_user.html'))
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return render_template(UIVersionManager.get_template_path('admin/create_user.html'))
        
        # Check if username or email already exists
        existing_user = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()
        
        if existing_user:
            if existing_user.username == username:
                flash('Username already exists. Please choose a different username.', 'error')
            else:
                flash('Email already registered. Please use a different email.', 'error')
            return render_template(UIVersionManager.get_template_path('admin/create_user.html'))
        
        # Create new user
        try:
            new_user = User(
                username=username,
                email=email,
                is_admin=is_admin,
                can_view_all_data=can_view_all_data
            )
            new_user.set_password(password)
            
            db.session.add(new_user)
            db.session.commit()
            
            flash(f'User "{username}" created successfully!', 'success')
            return redirect(url_for('manage_users'))
            
        except Exception as e:
            db.session.rollback()
            print(f"User creation error: {e}")
            flash('An error occurred while creating the user. Please try again.', 'error')
    
    return render_template(UIVersionManager.get_template_path('admin/create_user.html'))

@app.route('/admin/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    """Edit user (admin only)"""
    user = db.session.get(User, user_id) or abort(404)
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        is_admin = bool(request.form.get('is_admin'))
        can_view_all_data = bool(request.form.get('can_view_all_data'))
        
        # Validation
        if not username or not email:
            flash('Please fill in all required fields.', 'error')
            # Get admin count for template
            admin_count = User.query.filter_by(is_admin=True).count()
            return render_template(UIVersionManager.get_template_path('admin/edit_user.html'), user=user, admin_count=admin_count)
        
        if len(username) < 3:
            flash('Username must be at least 3 characters long.', 'error')
            return render_template(UIVersionManager.get_template_path('admin/edit_user.html'), user=user)
        
        # Check if username or email already exists (excluding current user)
        existing_user = User.query.filter(
            (User.username == username) | (User.email == email),
            User.id != user_id
        ).first()
        
        if existing_user:
            if existing_user.username == username:
                flash('Username already exists. Please choose a different username.', 'error')
            else:
                flash('Email already registered. Please use a different email.', 'error')
            return render_template(UIVersionManager.get_template_path('admin/edit_user.html'), user=user)
        
        # Prevent removing admin status from last admin
        if user.is_admin and not is_admin:
            admin_count = User.query.filter_by(is_admin=True).count()
            if admin_count <= 1:
                flash('Cannot remove admin status. At least one admin must exist.', 'error')
                return render_template(UIVersionManager.get_template_path('admin/edit_user.html'), user=user)
        
        # Update user
        try:
            user.username = username
            user.email = email
            user.is_admin = is_admin
            user.can_view_all_data = can_view_all_data
            
            # Update password if provided
            if password and len(password) >= 6:
                user.set_password(password)
            elif password and len(password) < 6:
                flash('Password must be at least 6 characters long if provided.', 'error')
                return render_template(UIVersionManager.get_template_path('admin/edit_user.html'), user=user)
            
            db.session.commit()
            
            flash(f'User "{username}" updated successfully!', 'success')
            return redirect(url_for('manage_users'))
            
        except Exception as e:
            db.session.rollback()
            print(f"User update error: {e}")
            flash('An error occurred while updating the user. Please try again.', 'error')
    
    # Get admin count for template
    admin_count = User.query.filter_by(is_admin=True).count()
    return render_template(UIVersionManager.get_template_path('admin/edit_user.html'), user=user, admin_count=admin_count)

@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """Delete user (admin only)"""
    user = db.session.get(User, user_id) or abort(404)
    
    # Prevent deleting yourself
    if user.id == current_user.id:
        return jsonify({'success': False, 'message': 'Cannot delete your own account'}), 400
    
    # Prevent deleting last admin
    if user.is_admin:
        admin_count = User.query.filter_by(is_admin=True).count()
        if admin_count <= 1:
            return jsonify({'success': False, 'message': 'Cannot delete the last admin user'}), 400
    
    try:
        # Delete user's related data
        Script.query.filter_by(user_id=user_id).delete()
        Execution.query.filter_by(user_id=user_id).delete()
        Schedule.query.filter_by(user_id=user_id).delete()
        
        # Delete user
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'User "{user.username}" deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        print(f"User deletion error: {e}")
        return jsonify({'success': False, 'message': 'An error occurred while deleting the user'}), 500

@app.route('/dashboard')
@login_required
def dashboard():
    # Get user's scripts (apply permission filter)
    scripts_query = Script.query.filter_by(is_active=True)
    user_scripts = apply_user_data_filter(scripts_query).all()
    
    # Get recent executions (apply permission filter)
    executions_query = Execution.query
    recent_executions = apply_user_data_filter(executions_query)\
        .order_by(Execution.started_at.desc())\
        .limit(5).all()
    
    # Calculate stats
    total_scripts = len(user_scripts)
    # 24h executions with permission filter
    executions_24h_query = Execution.query.filter(
        Execution.started_at >= datetime.now() - timedelta(days=1)
    )
    executions_24h = apply_user_data_filter(executions_24h_query).count()
    
    # Successful executions with permission filter
    successful_24h_query = Execution.query.filter(
        Execution.started_at >= datetime.now() - timedelta(days=1),
        Execution.status == 'completed',
        Execution.exit_code == 0
    )
    successful_24h = apply_user_data_filter(successful_24h_query).count()
    
    success_rate = round((successful_24h / executions_24h * 100) if executions_24h > 0 else 100, 1)
    
    stats = {
        'total_scripts': total_scripts,
        'executions_24h': executions_24h,
        'success_rate_24h': success_rate,
        'running_count': len(running_processes)
    }
    
    return render_template(UIVersionManager.get_template_path('dashboard.html'),
                         scripts=user_scripts,
                         recent_executions=recent_executions,
                         stats=stats)

@app.route('/scripts')
@login_required
def scripts():
    scripts_query = Script.query.filter_by(is_active=True).order_by(Script.updated_at.desc())
    user_scripts = apply_user_data_filter(scripts_query).all()
    return render_template(UIVersionManager.get_template_path('scripts.html'), scripts=user_scripts)

@app.route('/scripts/upload', methods=['GET', 'POST'])
@login_required
def upload_script():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected.', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        
        if file.filename == '':
            flash('No file selected.', 'error')
            return redirect(request.url)
        
        # Check file extension
        if not file.filename.lower().endswith(('.py', '.bat')):
            flash('Only .py and .bat files are allowed.', 'error')
            return redirect(request.url)
        
        if not name:
            name = file.filename.rsplit('.', 1)[0]
        
        # Check for duplicate names
        existing = Script.query.filter_by(user_id=current_user.id, name=name, is_active=True).first()
        if existing:
            flash(f'A script named "{name}" already exists.', 'error')
            return redirect(request.url)
        
        # Save file
        filename = secure_filename(file.filename)
        script_type = filename.rsplit('.', 1)[1].lower()
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{current_user.id}_{timestamp}_{filename}"
        
        upload_dir = app.config['UPLOAD_FOLDER']
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, unique_filename)
        
        try:
            file.save(file_path)
            file_size = os.path.getsize(file_path)
            
            # Create script record
            script = Script(
                name=name,
                description=description,
                filename=filename,
                file_path=file_path,
                script_type=script_type,
                user_id=current_user.id,
                file_size=file_size
            )
            
            db.session.add(script)
            db.session.commit()
            
            flash(f'Script "{name}" uploaded successfully!', 'success')
            return redirect(url_for('scripts'))
            
        except Exception as e:
            if os.path.exists(file_path):
                os.remove(file_path)
            flash(f'Error uploading script: {str(e)}', 'error')
            return redirect(request.url)
    
    return render_template(UIVersionManager.get_template_path('upload.html'))

@app.route('/scripts/<int:script_id>/execute', methods=['GET', 'POST'])
@login_required
def execute_script(script_id):
    script = Script.query.filter_by(id=script_id, user_id=current_user.id, is_active=True).first_or_404()
    
    if not script.file_exists:
        flash('Script file not found.', 'error')
        return redirect(url_for('scripts'))
    
    if request.method == 'GET':
        # Show execution page with recent executions
        recent_executions = Execution.query.filter_by(script_id=script.id)\
            .order_by(Execution.started_at.desc())\
            .limit(10).all()
        
        return render_template(UIVersionManager.get_template_path('execute_script.html'), 
                             script=script,
                             recent_executions=recent_executions)
    
    # POST method - actually execute the script
    # Create execution record
    execution = Execution(
        script_id=script.id,
        user_id=current_user.id,
        status='pending',
        trigger_type='manual'
    )
    db.session.add(execution)
    db.session.commit()
    
    # Start execution in background
    thread = threading.Thread(target=execute_script_background, args=(execution.id, script.file_path, script.script_type))
    thread.daemon = True
    thread.start()
    
    flash(f'Script "{script.name}" started successfully!', 'success')
    return redirect(url_for('logs'))

def execute_script_background(execution_id, script_path, script_type):
    """Execute script in background thread"""
    with app.app_context():  # *** AQUI ESTAVA O PROBLEMA - FALTAVA CONTEXTO ***
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
                # Get Python config from database first, fallback to app config
                python_exec = Settings.get_value('python_executable', app.config['PYTHON_EXECUTABLE'])
                python_env = Settings.get_value('python_env', app.config['PYTHON_ENV'])
                
                # If virtual environment is specified, use it
                if python_env:
                    python_exec = os.path.join(python_env, 'bin', 'python')
                    if not os.path.exists(python_exec):
                        # Try Windows path structure
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
                cwd=script_dir,  # Execute in the directory where script is located
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

@app.route('/scripts/<int:script_id>/view')
@login_required
def view_script(script_id):
    """View script content"""
    script = Script.query.filter_by(id=script_id, user_id=current_user.id, is_active=True).first_or_404()
    
    try:
        with open(script.file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        flash(f'Error reading script file: {str(e)}', 'error')
        return redirect(url_for('scripts'))
    
    return render_template(UIVersionManager.get_template_path('view_script.html'), script=script, content=content)

@app.route('/scripts/<int:script_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_script(script_id):
    """Edit script content and metadata"""
    script = Script.query.filter_by(id=script_id, user_id=current_user.id, is_active=True).first_or_404()
    
    if request.method == 'POST':
        # Update metadata
        script.name = request.form.get('name', '').strip()
        script.description = request.form.get('description', '').strip()
        
        # Update file content
        new_content = request.form.get('content', '')
        try:
            with open(script.file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            script.updated_at = datetime.now()
            db.session.commit()
            flash(f'Script "{script.name}" updated successfully!', 'success')
            return redirect(url_for('scripts'))
        except Exception as e:
            flash(f'Error saving script: {str(e)}', 'error')
    
    # GET request - load current content
    try:
        with open(script.file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        flash(f'Error reading script file: {str(e)}', 'error')
        return redirect(url_for('scripts'))
    
    return render_template(UIVersionManager.get_template_path('edit_script.html'), script=script, content=content)

@app.route('/scripts/<int:script_id>/download')
@login_required
def download_script(script_id):
    """Download script file"""
    from flask import send_file
    script = Script.query.filter_by(id=script_id, user_id=current_user.id, is_active=True).first_or_404()
    
    if not script.file_exists:
        flash('Script file not found.', 'error')
        return redirect(url_for('scripts'))
    
    try:
        return send_file(
            script.file_path,
            as_attachment=True,
            download_name=f"{script.name}.{script.script_type}"
        )
    except Exception as e:
        flash(f'Error downloading script: {str(e)}', 'error')
        return redirect(url_for('scripts'))

@app.route('/scripts/<int:script_id>/delete', methods=['POST'])
@login_required
def delete_script(script_id):
    """Delete script and its file"""
    script = Script.query.filter_by(id=script_id, user_id=current_user.id, is_active=True).first_or_404()
    
    try:
        # Delete physical file
        if script.file_exists:
            os.remove(script.file_path)
        
        # Mark as inactive instead of deleting from database
        script.is_active = False
        script.updated_at = datetime.now()
        db.session.commit()
        
        flash(f'Script "{script.name}" deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting script: {str(e)}', 'error')
    
    return redirect(url_for('scripts'))

@app.route('/logs')
@login_required
def logs():
    page = request.args.get('page', 1, type=int)
    executions_query = Execution.query.order_by(Execution.started_at.desc())
    executions_filtered = apply_user_data_filter(executions_query)
    executions = executions_filtered.paginate(page=page, per_page=20, error_out=False)
    
    return render_template(UIVersionManager.get_template_path('logs.html'), executions=executions)

@app.route('/logs/<int:execution_id>')
@login_required
def view_execution(execution_id):
    execution_query = Execution.query.filter_by(id=execution_id)
    execution = apply_user_data_filter(execution_query).first_or_404()
    return render_template(UIVersionManager.get_template_path('execution_detail.html'), execution=execution)

@app.route('/api/logs')
@login_required
def logs_api():
    """API endpoint to get execution logs for AJAX refresh"""
    page = request.args.get('page', 1, type=int)
    executions_query = Execution.query.order_by(Execution.started_at.desc())
    executions_filtered = apply_user_data_filter(executions_query)
    executions = executions_filtered.paginate(page=page, per_page=20, error_out=False)
    
    # Convert executions to JSON format
    executions_data = []
    for execution in executions.items:
        executions_data.append({
            'id': execution.id,
            'script_name': execution.script.name if execution.script else 'Unknown',
            'status': execution.status,
            'started_at': execution.started_at.strftime('%Y-%m-%d %H:%M:%S') if execution.started_at else None,
            'duration': execution.formatted_duration,
            'exit_code': execution.exit_code,
            'status_icon': execution.status_icon,
            'status_color': execution.status_color
        })
    
    return jsonify({
        'executions': executions_data,
        'has_running': any(ex.status in ['pending', 'running'] for ex in executions.items),
        'pagination': {
            'page': executions.page,
            'pages': executions.pages,
            'per_page': executions.per_page,
            'total': executions.total,
            'has_prev': executions.has_prev,
            'has_next': executions.has_next,
            'prev_num': executions.prev_num,
            'next_num': executions.next_num
        }
    })

@app.route('/api/execution/<int:execution_id>/status')
@login_required
def execution_status_api(execution_id):
    """API endpoint to get execution status without full page reload"""
    execution = Execution.query.filter_by(id=execution_id, user_id=current_user.id).first_or_404()
    
    return jsonify({
        'id': execution.id,
        'status': execution.status,
        'started_at': execution.started_at.strftime('%Y-%m-%d %H:%M:%S') if execution.started_at else None,
        'completed_at': execution.completed_at.strftime('%Y-%m-%d %H:%M:%S') if execution.completed_at else None,
        'duration': execution.formatted_duration,
        'exit_code': execution.exit_code,
        'stdout': execution.stdout,
        'stderr': execution.stderr,
        'is_running': execution.status in ['pending', 'running']
    })

@app.route('/api/execution/<int:execution_id>/stop', methods=['POST'])
@login_required
def stop_execution_api(execution_id):
    """API endpoint to stop/cancel a running execution"""
    execution = Execution.query.filter_by(id=execution_id, user_id=current_user.id).first_or_404()
    
    if execution.status not in ['pending', 'running']:
        return jsonify({
            'success': False,
            'message': f'Cannot stop execution with status: {execution.status}'
        }), 400
    
    # Update execution status to cancelled
    execution.status = 'cancelled'
    execution.completed_at = datetime.now()
    execution.stderr = (execution.stderr or '') + '\n[CANCELLED] Execution was stopped by user'
    execution.duration_seconds = (execution.completed_at - execution.started_at).total_seconds() if execution.started_at else 0
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Execution stopped successfully',
        'status': execution.status
    })

@app.route('/health')
def health():
    return {'status': 'healthy', 'version': '1.0'}, 200

@app.route('/system/info')
@login_required  
def system_info():
    """System information endpoint"""
    import sys
    import shutil
    
    python_exec = app.config['PYTHON_EXECUTABLE']
    python_env = app.config['PYTHON_ENV']
    
    # Get actual Python path that would be used
    if python_env:
        actual_python = os.path.join(python_env, 'bin', 'python')
        if not os.path.exists(actual_python):
            actual_python = os.path.join(python_env, 'Scripts', 'python.exe')
    else:
        actual_python = shutil.which(python_exec) or python_exec
    
    try:
        # Test the configured Python
        import subprocess
        result = subprocess.run([actual_python, '--version'], capture_output=True, text=True, timeout=5)
        python_version = result.stdout.strip() if result.returncode == 0 else f"Error: {result.stderr.strip()}"
    except Exception as e:
        python_version = f"Error testing Python: {str(e)}"
    
    return jsonify({
        'system': {
            'current_app_python': sys.executable,
            'current_app_version': sys.version,
            'configured_python_executable': python_exec,
            'configured_python_env': python_env,
            'resolved_python_path': actual_python,
            'resolved_python_version': python_version,
            'platform': sys.platform,
            'cwd': os.getcwd()
        },
        'config': {
            'upload_folder': app.config['UPLOAD_FOLDER'],
            'database_uri': app.config['SQLALCHEMY_DATABASE_URI'],
            'max_content_length': app.config['MAX_CONTENT_LENGTH']
        }
    })

@app.route('/settings')
@login_required
def settings():
    """Settings configuration page"""
    return render_template(UIVersionManager.get_template_path('settings.html'))

def detect_python_interpreters():
    """Detect available Python interpreters on the system"""
    interpreters = []
    common_paths = [
        'python3', 'python', 'python3.9', 'python3.10', 'python3.11', 'python3.12',
        '/usr/bin/python3', '/usr/bin/python', '/usr/local/bin/python3',
        '/opt/homebrew/bin/python3', '/System/Library/Frameworks/Python.framework/Versions/Current/bin/python3'
    ]
    
    for path in common_paths:
        try:
            result = subprocess.run([path, '--version'], 
                                  capture_output=True, text=True, timeout=3)
            if result.returncode == 0:
                version = result.stdout.strip() or result.stderr.strip()
                interpreters.append({
                    'path': path,
                    'version': version,
                    'display': f"{path} ({version})"
                })
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            continue
    
    # Remove duplicates based on version
    seen_versions = set()
    unique_interpreters = []
    for interp in interpreters:
        if interp['version'] not in seen_versions:
            seen_versions.add(interp['version'])
            unique_interpreters.append(interp)
    
    return unique_interpreters

@app.route('/settings/python', methods=['GET', 'POST'])
@login_required
def python_settings():
    """Python interpreter settings"""
    if request.method == 'POST':
        python_exec = request.form.get('python_executable', '').strip()
        python_env = request.form.get('python_env', '').strip()
        
        if python_exec:
            Settings.set_value('python_executable', python_exec, 
                             'Python executable path', current_user.id)
        
        if python_env:
            Settings.set_value('python_env', python_env,
                             'Python virtual environment path', current_user.id)
        elif 'python_env' in request.form:  # Empty but present = clear setting
            Settings.set_value('python_env', '',
                             'Python virtual environment path', current_user.id)
        
        flash('Python settings updated successfully!', 'success')
        return redirect(url_for('python_settings'))
    
    # GET request - show current settings and available interpreters
    current_python_exec = Settings.get_value('python_executable', app.config['PYTHON_EXECUTABLE'])
    current_python_env = Settings.get_value('python_env', app.config['PYTHON_ENV']) or ''
    available_interpreters = detect_python_interpreters()
    
    return render_template(UIVersionManager.get_template_path('python_settings.html'), 
                                python_executable=current_python_exec,
                                python_env=current_python_env,
                                available_interpreters=available_interpreters)

@app.route('/schedules')
@login_required
def schedules():
    """Schedule management page"""
    schedules_query = Schedule.query.order_by(Schedule.next_run_time.asc())
    user_schedules = apply_user_data_filter(schedules_query).all()
    
    # Get stats
    active_schedules = sum(1 for s in user_schedules if s.is_active)
    disabled_schedules = len(user_schedules) - active_schedules
    
    # Next run time
    next_schedule = next((s for s in user_schedules if s.is_active and s.next_run_time), None)
    next_run_display = next_schedule.next_run_display if next_schedule else "No upcoming runs"
    
    stats = {
        'active': active_schedules,
        'disabled': disabled_schedules,
        'next_run': next_run_display,
        'avg_per_day': 0  # TODO: Calculate based on execution history
    }
    
    return render_template(UIVersionManager.get_template_path('schedules.html'), schedules=user_schedules, stats=stats)

@app.route('/schedules/create', methods=['GET', 'POST'])
@login_required
def create_schedule():
    """Create new schedule"""
    if request.method == 'POST':
        script_id = request.form.get('script_id', type=int)
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        frequency = request.form.get('frequency', '')
        time = request.form.get('time', '09:00')
        start_date = request.form.get('start_date', '')
        is_active = bool(request.form.get('is_active'))
        
        if not script_id or not name or not frequency:
            flash('Please fill all required fields.', 'error')
            return redirect(request.url)
        
        # Verify script belongs to user
        script = Script.query.filter_by(id=script_id, user_id=current_user.id, is_active=True).first()
        if not script:
            flash('Invalid script selected.', 'error')
            return redirect(request.url)
        
        # Build time configuration
        time_config = {'time': time}
        
        # Add start date if specified
        if start_date:
            time_config['start_date'] = start_date
        
        if frequency == 'weekly':
            days = request.form.getlist('days')
            if not days:
                days = ['monday']
            time_config['days'] = days
        elif frequency == 'monthly':
            day = request.form.get('day', 1, type=int)
            time_config['day'] = max(1, min(28, day))
        elif frequency == 'interval':
            interval_minutes = request.form.get('interval_minutes', '15')
            try:
                interval_minutes = int(interval_minutes)
                if interval_minutes <= 0:
                    interval_minutes = 15
            except (ValueError, TypeError):
                interval_minutes = 15
            time_config['interval_minutes'] = interval_minutes
        
        # Create schedule
        schedule = Schedule(
            name=name,
            description=description,
            frequency=frequency,
            time_config=json.dumps(time_config),
            is_active=is_active,
            script_id=script_id,
            user_id=current_user.id
        )
        
        # Calculate next run
        schedule.calculate_next_run()
        
        db.session.add(schedule)
        db.session.commit()
        
        # Add to APScheduler if active
        if is_active:
            add_schedule_to_scheduler(schedule)
        
        flash(f'Schedule "{name}" created successfully!', 'success')
        return redirect(url_for('schedules'))
    
    # GET request - show form
    user_scripts = Script.query.filter_by(user_id=current_user.id, is_active=True)\
        .order_by(Script.name).all()
    return render_template(UIVersionManager.get_template_path('create_schedule.html'), scripts=user_scripts)

@app.route('/schedules/<int:schedule_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_schedule(schedule_id):
    """Edit existing schedule"""
    schedule = Schedule.query.filter_by(id=schedule_id, user_id=current_user.id).first_or_404()
    
    if request.method == 'POST':
        schedule.name = request.form.get('name', '').strip()
        schedule.description = request.form.get('description', '').strip()
        schedule.frequency = request.form.get('frequency', '')
        time = request.form.get('time', '09:00')
        start_date = request.form.get('start_date', '')
        was_active = schedule.is_active
        schedule.is_active = bool(request.form.get('is_active'))
        
        # Build time configuration
        time_config = {'time': time}
        
        # Add start date if specified
        if start_date:
            time_config['start_date'] = start_date
        
        if schedule.frequency == 'weekly':
            days = request.form.getlist('days')
            if not days:
                days = ['monday']
            time_config['days'] = days
        elif schedule.frequency == 'monthly':
            day = request.form.get('day', 1, type=int)
            time_config['day'] = max(1, min(28, day))
        elif schedule.frequency == 'interval':
            interval_minutes = request.form.get('interval_minutes', '15')
            try:
                interval_minutes = int(interval_minutes)
                if interval_minutes <= 0:
                    interval_minutes = 15
            except (ValueError, TypeError):
                interval_minutes = 15
            time_config['interval_minutes'] = interval_minutes
        
        schedule.time_config = json.dumps(time_config)
        schedule.updated_at = datetime.now()
        
        # Recalculate next run
        schedule.calculate_next_run()
        
        # Update APScheduler
        if was_active:
            remove_schedule_from_scheduler(schedule.id)
        
        if schedule.is_active:
            add_schedule_to_scheduler(schedule)
        
        db.session.commit()
        
        flash(f'Schedule "{schedule.name}" updated successfully!', 'success')
        return redirect(url_for('schedules'))
    
    # GET request - show form
    user_scripts = Script.query.filter_by(user_id=current_user.id, is_active=True)\
        .order_by(Script.name).all()
    return render_template(UIVersionManager.get_template_path('edit_schedule.html'), schedule=schedule, scripts=user_scripts)

@app.route('/schedules/<int:schedule_id>/toggle', methods=['POST'])
@login_required
def toggle_schedule(schedule_id):
    """Toggle schedule active status"""
    schedule = Schedule.query.filter_by(id=schedule_id, user_id=current_user.id).first_or_404()
    
    was_active = schedule.is_active
    schedule.is_active = not schedule.is_active
    schedule.updated_at = datetime.now()
    
    # Update APScheduler
    if was_active:
        remove_schedule_from_scheduler(schedule.id)
    
    if schedule.is_active:
        schedule.calculate_next_run()
        add_schedule_to_scheduler(schedule)
    
    db.session.commit()
    
    status = "activated" if schedule.is_active else "deactivated"
    flash(f'Schedule "{schedule.name}" {status} successfully!', 'success')
    
    return redirect(url_for('schedules'))

@app.route('/schedules/<int:schedule_id>/delete', methods=['POST'])
@login_required
def delete_schedule(schedule_id):
    """Delete schedule"""
    schedule = Schedule.query.filter_by(id=schedule_id, user_id=current_user.id).first_or_404()
    
    # Remove from APScheduler
    remove_schedule_from_scheduler(schedule.id)
    
    schedule_name = schedule.name
    db.session.delete(schedule)
    db.session.commit()
    
    flash(f'Schedule "{schedule_name}" deleted successfully!', 'success')
    return redirect(url_for('schedules'))

@app.route('/schedules/<int:schedule_id>/run', methods=['POST'])
@login_required
def run_schedule_now(schedule_id):
    """Run a schedule immediately"""
    schedule = Schedule.query.filter_by(id=schedule_id, user_id=current_user.id).first_or_404()
    
    if not schedule.script.file_exists:
        flash('Script file not found.', 'error')
        return redirect(url_for('schedules'))
    
    # Create execution record
    execution = Execution(
        script_id=schedule.script_id,
        user_id=current_user.id,
        status='pending',
        trigger_type='scheduled'
    )
    db.session.add(execution)
    db.session.commit()
    
    # Start execution in background
    thread = threading.Thread(target=execute_script_background, args=(execution.id, schedule.script.file_path, schedule.script.script_type))
    thread.daemon = True
    thread.start()
    
    flash(f'Schedule "{schedule.name}" executed manually!', 'success')
    return redirect(url_for('logs'))

def init_scheduler():
    """Initialize APScheduler if not already initialized"""
    global scheduler
    if scheduler is None:
        try:
            # Only initialize scheduler in main process (not in reloader process)
            if os.environ.get('WERKZEUG_RUN_MAIN'):
                # Use MemoryJobStore to avoid SQLite locking conflicts
                jobstores = {
                    'default': MemoryJobStore()
                }
                scheduler = BackgroundScheduler(jobstores=jobstores)
                scheduler.start()
                atexit.register(lambda: scheduler.shutdown())
                print(f"✅ Scheduler initialized (main process)")
                
                # Reload all active schedules since MemoryJobStore doesn't persist
                reload_active_schedules()
            else:
                print("ℹ️ Scheduler not initialized (reloader process)")
        except Exception as e:
            print(f"❌ Error initializing scheduler: {e}")
            raise

def reload_active_schedules():
    """Reload all active schedules into the scheduler (for MemoryJobStore)"""
    global scheduler
    
    # Avoid double loading in debug mode - check if we already have jobs loaded
    if scheduler is None:
        return
    
    # Prevent duplicate loading by checking if jobs already exist
    existing_jobs = scheduler.get_jobs()
    if existing_jobs:
        print(f"ℹ️ Scheduler already has {len(existing_jobs)} jobs, skipping reload")
        return
    
    try:
        # Get all active schedules that should be running
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
    
    # Initialize scheduler if not ready
    if scheduler is None:
        init_scheduler()
    
    job_id = f"schedule_{schedule.id}"
    
    # Check if job already exists and has same run_date to avoid duplicates
    try:
        existing_job = scheduler.get_job(job_id)
        if existing_job and existing_job.next_run_time == schedule.next_run_time:
            print(f"🔄 Job {job_id} already scheduled for {schedule.next_run_time}, skipping")
            return
    except:
        pass
    
    # Remove existing job if exists
    try:
        scheduler.remove_job(job_id)
    except:
        pass
    
    if not schedule.is_active or not schedule.next_run_time:
        return
    
    # Add new job
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
    
    # Initialize scheduler if not ready
    if scheduler is None:
        init_scheduler()
    
    job_id = f"schedule_{schedule_id}"
    try:
        scheduler.remove_job(job_id)
        print(f"🗑️ Removed job {job_id} from scheduler")
    except Exception as e:
        # Import here to avoid circular imports
        from apscheduler.jobstores.base import JobLookupError
        
        if isinstance(e, JobLookupError):
            # Job might already be gone or never existed - this is OK
            print(f"ℹ️ Job {job_id} was already removed or not found in scheduler")
        else:
            # Other errors should be reported
            print(f"⚠️ Unexpected error removing job {job_id}: {e}")
        pass

def execute_scheduled_script(schedule_id):
    """Execute script from schedule (called by APScheduler)"""
    with app.app_context():
        try:
            # Get fresh schedule object from database
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
            db.session.commit()  # Commit execution first to get the ID
            print(f"💾 Execution record created with ID: {execution.id}")
            
            # Update schedule's last execution
            schedule.last_execution_id = execution.id
            
            # Store schedule_id before any database operations to avoid autoflush
            schedule_id_safe = schedule.id
            schedule_name_safe = schedule.name
            
            try:
                # Remove current job from scheduler (since it just executed)
                remove_schedule_from_scheduler(schedule_id_safe)
                
                # Calculate and schedule next run with autoflush disabled
                with db.session.no_autoflush:
                    old_next_run = schedule.next_run_time
                    print(f"📅 Schedule {schedule_name_safe}: Calculating next run from {old_next_run}")
                    
                    schedule.calculate_next_run()
                    new_next_run = schedule.next_run_time
                    
                    print(f"📅 Schedule {schedule_name_safe}: Updated next run to {new_next_run}")
                
                # Commit schedule changes with retry logic
                max_retries = 3
                for retry in range(max_retries):
                    try:
                        db.session.commit()
                        break
                    except Exception as e:
                        if retry < max_retries - 1:
                            print(f"⚠️ Database commit failed (retry {retry + 1}/{max_retries}): {e}")
                            time.sleep(0.1 * (retry + 1))  # Exponential backoff
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
            
            # Add next job to scheduler if there's a next run time
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
            # Try to rollback if there were database changes
            try:
                db.session.rollback()
            except:
                pass

@app.route('/settings/terminal')
@login_required  
def terminal():
    """Web terminal for package installation"""
    return render_template(UIVersionManager.get_template_path('terminal.html'))

@app.route('/api/terminal/execute', methods=['POST'])
@login_required
def terminal_execute():
    """Execute terminal command"""
    data = request.get_json()
    command = data.get('command', '').strip()
    
    if not command:
        return jsonify({'error': 'No command provided'}), 400
    
    # Security: Only allow specific safe commands
    allowed_commands = ['pip', 'python', 'which', 'ls', 'pwd']
    cmd_parts = command.split()
    
    if not cmd_parts or cmd_parts[0] not in allowed_commands:
        return jsonify({'error': 'Command not allowed'}), 403
    
    try:
        # Get configured Python for pip commands
        if cmd_parts[0] == 'pip':
            python_exec = Settings.get_value('python_executable', app.config['PYTHON_EXECUTABLE'])
            python_env = Settings.get_value('python_env', app.config['PYTHON_ENV'])
            
            if python_env:
                pip_exec = os.path.join(python_env, 'bin', 'pip')
                if not os.path.exists(pip_exec):
                    pip_exec = os.path.join(python_env, 'Scripts', 'pip.exe')
            else:
                pip_exec = 'pip3'
            
            cmd_parts[0] = pip_exec
        
        # Execute command
        result = subprocess.run(cmd_parts, capture_output=True, text=True, timeout=30)
        
        return jsonify({
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode,
            'command': ' '.join(cmd_parts)
        })
        
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Command timed out'}), 408
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/preview/modern-ui')
@login_required  
def modern_ui_preview():
    """Preview of modern UI design - Dashboard"""
    return render_template('modern_preview_dashboard.html')

@app.route('/preview/scripts')
@login_required  
def modern_scripts_preview():
    """Preview of modern UI design - Scripts"""
    return render_template('modern_preview_scripts.html')

@app.route('/preview/schedules')
@login_required  
def modern_schedules_preview():
    """Preview of modern UI design - Schedules"""
    return render_template('modern_preview_schedules.html')

@app.route('/preview/logs')
@login_required  
def modern_logs_preview():
    """Preview of modern UI design - Logs"""
    return render_template('modern_preview_logs.html')

@app.route('/preview/users')
@login_required  
def modern_users_preview():
    """Preview of modern UI design - User Management"""
    return render_template('modern_preview_users.html')

@app.route('/preview/settings')
@login_required  
def modern_settings_preview():
    """Preview of modern UI design - Settings"""
    return render_template('modern_preview_settings.html')

@app.route('/ui/toggle')
@login_required
def toggle_ui_version():
    """Toggle between UI versions"""
    new_version = UIVersionManager.toggle_version()
    flash(f'Switched to UI version {new_version}', 'info')
    return redirect(request.referrer or url_for('dashboard'))

@app.route('/ui/test')
@login_required
def test_ui_version():
    """Test UI version management"""
    current_version = UIVersionManager.get_ui_version()
    is_modern = UIVersionManager.is_modern_ui()
    template_path = UIVersionManager.get_template_path('dashboard.html')
    
    return jsonify({
        'current_version': current_version,
        'is_modern_ui': is_modern,
        'template_path': template_path,
        'url_params': dict(request.args),
        'session_version': session.get('ui_version'),
        'env_version': os.environ.get('UI_VERSION')
    })

# Templates removed - now using separate .html files

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
                password_hash=generate_password_hash('admin123')
            )
            db.session.add(admin_user)
            db.session.commit()
            print("✅ Created default admin user: admin/admin123")
        
        # Schedules are loaded in init_scheduler() via reload_active_schedules()
        # to avoid duplicate loading in debug mode
        pass
    
    # Find free port and start
    port = find_free_port()
    print(f"\n🚀 ScriptFlow starting on http://localhost:{port}")
    print("👤 Default login: admin/admin123")
    print("🛑 Press Ctrl+C to stop\n")
    
    app.run(debug=True, host='0.0.0.0', port=port)