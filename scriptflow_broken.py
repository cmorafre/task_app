#!/usr/bin/env python3
"""
ScriptFlow - Complete Working Application
Sistema completo de automação de scripts
"""

import os
import socket
from flask import Flask, render_template, request, flash, redirect, url_for, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from dotenv import load_dotenv
import subprocess
import tempfile
import threading
import json

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__, template_folder='app/templates', static_folder='app/static')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///scriptflow.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.environ.get('UPLOAD_FOLDER', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB max file size

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access ScriptFlow.'

# Models
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def update_last_login(self):
        self.last_login = datetime.utcnow()
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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    @property
    def file_exists(self):
        return os.path.exists(self.file_path)

class Execution(db.Model):
    __tablename__ = 'executions'
    id = db.Column(db.Integer, primary_key=True)
    started_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    completed_at = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='pending', nullable=False)  # pending, running, completed, failed, timeout
    exit_code = db.Column(db.Integer)
    stdout = db.Column(db.Text)
    stderr = db.Column(db.Text)
    duration_seconds = db.Column(db.Float)
    script_id = db.Column(db.Integer, db.ForeignKey('scripts.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
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
            'timeout': '⏰'
        }
        return icons.get(self.status, '❓')
    
    @property
    def status_color(self):
        colors = {
            'pending': 'secondary',
            'running': 'warning',
            'completed': 'success',
            'failed': 'danger',
            'timeout': 'warning'
        }
        return colors.get(self.status, 'secondary')

# User loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

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
            return render_template('auth/login.html')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user, remember=remember)
            user.update_last_login()
            flash(f'Welcome back, {user.username}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'error')
    
    return render_template('auth/login.html')

@app.route('/logout')
@login_required
def logout():
    username = current_user.username
    logout_user()
    flash(f'Goodbye, {username}!', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Get user's scripts
    user_scripts = Script.query.filter_by(user_id=current_user.id, is_active=True).all()
    
    # Get recent executions
    recent_executions = Execution.query.filter_by(user_id=current_user.id)\
        .order_by(Execution.started_at.desc())\
        .limit(5).all()
    
    # Calculate stats
    total_scripts = len(user_scripts)
    executions_24h = Execution.query.filter(
        Execution.user_id == current_user.id,
        Execution.started_at >= datetime.utcnow() - timedelta(days=1)
    ).count()
    
    successful_24h = Execution.query.filter(
        Execution.user_id == current_user.id,
        Execution.started_at >= datetime.utcnow() - timedelta(days=1),
        Execution.status == 'completed',
        Execution.exit_code == 0
    ).count()
    
    success_rate = round((successful_24h / executions_24h * 100) if executions_24h > 0 else 100, 1)
    
    stats = {
        'total_scripts': total_scripts,
        'executions_24h': executions_24h,
        'success_rate_24h': success_rate,
        'running_count': len(running_processes)
    }
    
    return render_template('dashboard/index.html',
                         scripts=user_scripts,
                         recent_executions=recent_executions,
                         stats=stats)

@app.route('/scripts')
@login_required
def scripts():
    user_scripts = Script.query.filter_by(user_id=current_user.id, is_active=True)\
        .order_by(Script.updated_at.desc()).all()
    return render_template('scripts/index.html', scripts=user_scripts)

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
    
    return render_template('scripts/upload.html')

@app.route('/scripts/<int:script_id>/execute', methods=['POST'])
@login_required
def execute_script(script_id):
    script = Script.query.filter_by(id=script_id, user_id=current_user.id, is_active=True).first_or_404()
    
    if not script.file_exists:
        flash('Script file not found.', 'error')
        return redirect(url_for('scripts'))
    
    # Create execution record
    execution = Execution(
        script_id=script.id,
        user_id=current_user.id,
        status='pending'
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
    execution = Execution.query.get(execution_id)
    if not execution:
        return
    
    try:
        # Update status to running
        execution.status = 'running'
        execution.started_at = datetime.utcnow()
        db.session.commit()
        
        # Create isolated working directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Build command
            if script_type == 'py':
                cmd = ['python3', script_path]
            elif script_type == 'bat':
                if os.name == 'nt':
                    cmd = ['cmd', '/c', script_path]
                else:
                    cmd = ['bash', script_path]
            else:
                raise Exception(f"Unsupported script type: {script_type}")
            
            # Run script
            start_time = datetime.utcnow()
            result = subprocess.run(
                cmd,
                cwd=temp_dir,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )
            end_time = datetime.utcnow()
            
            # Update execution record
            execution.completed_at = end_time
            execution.exit_code = result.returncode
            execution.stdout = result.stdout
            execution.stderr = result.stderr
            execution.duration_seconds = (end_time - start_time).total_seconds()
            execution.status = 'completed' if result.returncode == 0 else 'failed'
            
            db.session.commit()
    
    except subprocess.TimeoutExpired:
        execution.completed_at = datetime.utcnow()
        execution.status = 'timeout'
        execution.stderr = "Script execution timed out (5 minutes)"
        execution.duration_seconds = 300
        db.session.commit()
    
    except Exception as e:
        execution.completed_at = datetime.utcnow()
        execution.status = 'failed'
        execution.stderr = str(e)
        execution.exit_code = -1
        db.session.commit()

@app.route('/logs')
@login_required
def logs():
    page = request.args.get('page', 1, type=int)
    executions = Execution.query.filter_by(user_id=current_user.id)\
        .order_by(Execution.started_at.desc())\
        .paginate(page=page, per_page=20, error_out=False)
    
    return render_template('logs/index.html', executions=executions)

@app.route('/logs/<int:execution_id>')
@login_required
def view_execution(execution_id):
    execution = Execution.query.filter_by(id=execution_id, user_id=current_user.id).first_or_404()
    return render_template('logs/execution_detail.html', execution=execution)

@app.route('/health')
def health():
    return {'status': 'healthy', 'version': '1.0'}, 200

# Templates (inline para funcionar sem arquivos externos)
templates = {
    'login.html': '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ScriptFlow - Login</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background: linear-gradient(135deg, #2C3E50 0%, #34495E 100%); min-height: 100vh; display: flex; align-items: center; }
        .login-card { background: white; border-radius: 12px; padding: 2rem; box-shadow: 0 10px 30px rgba(0,0,0,0.1); width: 100%; max-width: 400px; }
        .login-header { text-align: center; margin-bottom: 2rem; }
        .login-header h1 { color: #2C3E50; font-weight: 700; margin-bottom: 0.5rem; }
    </style>
</head>
<body>
    <div class="container">
        <div class="row justify-content-center">
            <div class="col-md-6">
                {% with messages = get_flashed_messages(with_categories=true) %}
                    {% if messages %}
                        {% for category, message in messages %}
                            <div class="alert alert-{{ 'danger' if category == 'error' else category }} alert-dismissible fade show">
                                {{ message }}
                                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                            </div>
                        {% endfor %}
                    {% endif %}
                {% endwith %}
                
                <div class="login-card">
                    <div class="login-header">
                        <h1>🔧 ScriptFlow</h1>
                        <p class="text-muted">Automation Made Simple</p>
                    </div>
                    
                    <form method="POST">
                        <div class="mb-3">
                            <label for="username" class="form-label">Username</label>
                            <input type="text" class="form-control" id="username" name="username" required autofocus>
                        </div>
                        
                        <div class="mb-3">
                            <label for="password" class="form-label">Password</label>
                            <input type="password" class="form-control" id="password" name="password" required>
                        </div>
                        
                        <div class="mb-3 form-check">
                            <input type="checkbox" class="form-check-input" id="remember" name="remember">
                            <label class="form-check-label" for="remember">Remember me</label>
                        </div>
                        
                        <div class="d-grid">
                            <button type="submit" class="btn btn-primary btn-lg">Sign In</button>
                        </div>
                    </form>
                    
                    <div class="text-center mt-4">
                        <small class="text-muted">Default: admin / admin123</small>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
''',

    'dashboard.html': '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ScriptFlow - Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css" rel="stylesheet">
    <style>
        body { background-color: #f8f9fa; padding-top: 76px; }
        .navbar-brand { font-weight: 600; }
        .stats-card { background: white; border-radius: 8px; padding: 1.5rem; box-shadow: 0 2px 4px rgba(0,0,0,0.1); border-left: 4px solid #2C3E50; }
        .stats-number { font-size: 2rem; font-weight: 700; color: #2C3E50; margin: 0; }
        .stats-label { color: #7F8C8D; font-size: 0.875rem; margin: 0; }
        .card { border: none; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .status-success { color: #27AE60; }
        .status-warning { color: #F39C12; }
        .status-danger { color: #E74C3C; }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark fixed-top">
        <div class="container">
            <a class="navbar-brand" href="{{ url_for('dashboard') }}">
                <i class="bi bi-gear-fill me-2"></i>ScriptFlow
            </a>
            <div class="navbar-nav ms-auto">
                <div class="nav-item dropdown">
                    <a class="nav-link dropdown-toggle" href="#" role="button" data-bs-toggle="dropdown">
                        <i class="bi bi-person-circle me-1"></i>{{ current_user.username }}
                    </a>
                    <ul class="dropdown-menu">
                        <li><a class="dropdown-item" href="{{ url_for('logout') }}">
                            <i class="bi bi-box-arrow-right me-2"></i>Logout
                        </a></li>
                    </ul>
                </div>
            </div>
        </div>
    </nav>

    <main class="container mt-4">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ 'danger' if category == 'error' else category }} alert-dismissible fade show">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <div class="row mb-4">
            <div class="col">
                <h1><i class="bi bi-speedometer2 me-2"></i>Dashboard</h1>
                <p class="text-muted">Welcome back, {{ current_user.username }}!</p>
            </div>
            <div class="col-auto">
                <a href="{{ url_for('upload_script') }}" class="btn btn-primary">
                    <i class="bi bi-plus-circle me-2"></i>Upload Script
                </a>
            </div>
        </div>

        <!-- Stats -->
        <div class="row mb-4">
            <div class="col-md-3 mb-3">
                <div class="stats-card">
                    <p class="stats-number">{{ stats.total_scripts }}</p>
                    <p class="stats-label">Total Scripts</p>
                </div>
            </div>
            <div class="col-md-3 mb-3">
                <div class="stats-card">
                    <p class="stats-number">{{ stats.executions_24h }}</p>
                    <p class="stats-label">Executions (24h)</p>
                </div>
            </div>
            <div class="col-md-3 mb-3">
                <div class="stats-card">
                    <p class="stats-number">{{ stats.success_rate_24h }}%</p>
                    <p class="stats-label">Success Rate</p>
                </div>
            </div>
            <div class="col-md-3 mb-3">
                <div class="stats-card">
                    <p class="stats-number">{{ stats.running_count }}</p>
                    <p class="stats-label">Running Now</p>
                </div>
            </div>
        </div>

        <!-- Navigation -->
        <div class="row mb-4">
            <div class="col-md-8">
                <div class="card">
                    <div class="card-header bg-primary text-white">
                        <h5 class="mb-0"><i class="bi bi-lightning me-2"></i>Quick Actions</h5>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-6 mb-3">
                                <a href="{{ url_for('upload_script') }}" class="btn btn-outline-primary w-100">
                                    <i class="bi bi-upload me-2"></i>Upload Script
                                </a>
                            </div>
                            <div class="col-md-6 mb-3">
                                <a href="{{ url_for('scripts') }}" class="btn btn-outline-success w-100">
                                    <i class="bi bi-list me-2"></i>Manage Scripts
                                </a>
                            </div>
                            <div class="col-md-6">
                                <a href="{{ url_for('logs') }}" class="btn btn-outline-info w-100">
                                    <i class="bi bi-clock-history me-2"></i>View Logs
                                </a>
                            </div>
                            <div class="col-md-6">
                                <a href="#" class="btn btn-outline-secondary w-100">
                                    <i class="bi bi-calendar me-2"></i>Schedules
                                </a>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Recent Scripts -->
        <div class="row">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header bg-primary text-white d-flex justify-content-between">
                        <h5 class="mb-0"><i class="bi bi-file-code me-2"></i>Scripts</h5>
                        <a href="{{ url_for('scripts') }}" class="btn btn-sm btn-outline-light">View All</a>
                    </div>
                    <div class="card-body p-0">
                        {% if scripts %}
                            <div class="table-responsive">
                                <table class="table table-hover mb-0">
                                    <thead>
                                        <tr>
                                            <th>Name</th>
                                            <th>Type</th>
                                            <th>Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {% for script in scripts[:5] %}
                                        <tr>
                                            <td>{{ script.name }}</td>
                                            <td><span class="badge bg-secondary">{{ script.script_type.upper() }}</span></td>
                                            <td>
                                                <form method="POST" action="{{ url_for('execute_script', script_id=script.id) }}" class="d-inline">
                                                    <button type="submit" class="btn btn-sm btn-success" title="Execute">
                                                        <i class="bi bi-play"></i>
                                                    </button>
                                                </form>
                                            </td>
                                        </tr>
                                        {% endfor %}
                                    </tbody>
                                </table>
                            </div>
                        {% else %}
                            <div class="p-4 text-center">
                                <i class="bi bi-file-code text-muted" style="font-size: 3rem;"></i>
                                <p class="text-muted mt-2">No scripts yet</p>
                                <a href="{{ url_for('upload_script') }}" class="btn btn-primary">Upload First Script</a>
                            </div>
                        {% endif %}
                    </div>
                </div>
            </div>

            <div class="col-md-6">
                <div class="card">
                    <div class="card-header bg-primary text-white d-flex justify-content-between">
                        <h5 class="mb-0"><i class="bi bi-clock-history me-2"></i>Recent Executions</h5>
                        <a href="{{ url_for('logs') }}" class="btn btn-sm btn-outline-light">View All</a>
                    </div>
                    <div class="card-body p-0">
                        {% if recent_executions %}
                            <div class="table-responsive">
                                <table class="table table-hover mb-0">
                                    <thead>
                                        <tr>
                                            <th>Script</th>
                                            <th>Status</th>
                                            <th>Duration</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {% for execution in recent_executions %}
                                        <tr>
                                            <td>
                                                <a href="{{ url_for('view_execution', execution_id=execution.id) }}">
                                                    {{ execution.script.name if execution.script else 'Unknown' }}
                                                </a>
                                            </td>
                                            <td>
                                                <span class="status-{{ execution.status_color }}">
                                                    {{ execution.status_icon }} {{ execution.status.title() }}
                                                </span>
                                            </td>
                                            <td>{{ execution.formatted_duration }}</td>
                                        </tr>
                                        {% endfor %}
                                    </tbody>
                                </table>
                            </div>
                        {% else %}
                            <div class="p-4 text-center">
                                <i class="bi bi-clock-history text-muted" style="font-size: 3rem;"></i>
                                <p class="text-muted mt-2">No executions yet</p>
                            </div>
                        {% endif %}
                    </div>
                </div>
            </div>
        </div>
    </main>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
''',

    'scripts.html': '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ScriptFlow - Scripts</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css" rel="stylesheet">
    <style>
        body { background-color: #f8f9fa; padding-top: 76px; }
        .navbar-brand { font-weight: 600; }
        .card { border: none; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark fixed-top">
        <div class="container">
            <a class="navbar-brand" href="{{ url_for('dashboard') }}">
                <i class="bi bi-gear-fill me-2"></i>ScriptFlow
            </a>
            <div class="navbar-nav ms-auto">
                <a class="nav-link" href="{{ url_for('dashboard') }}">Dashboard</a>
                <a class="nav-link active" href="{{ url_for('scripts') }}">Scripts</a>
                <a class="nav-link" href="{{ url_for('logs') }}">Logs</a>
                <div class="nav-item dropdown">
                    <a class="nav-link dropdown-toggle" href="#" role="button" data-bs-toggle="dropdown">
                        {{ current_user.username }}
                    </a>
                    <ul class="dropdown-menu">
                        <li><a class="dropdown-item" href="{{ url_for('logout') }}">Logout</a></li>
                    </ul>
                </div>
            </div>
        </div>
    </nav>

    <main class="container mt-4">
        <div class="row mb-4">
            <div class="col">
                <h1><i class="bi bi-file-code me-2"></i>Scripts</h1>
            </div>
            <div class="col-auto">
                <a href="{{ url_for('upload_script') }}" class="btn btn-primary">
                    <i class="bi bi-plus-circle me-2"></i>Upload Script
                </a>
            </div>
        </div>

        <div class="card">
            <div class="card-body p-0">
                {% if scripts %}
                    <div class="table-responsive">
                        <table class="table table-hover mb-0">
                            <thead class="table-light">
                                <tr>
                                    <th>Name</th>
                                    <th>Type</th>
                                    <th>Size</th>
                                    <th>Created</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for script in scripts %}
                                <tr>
                                    <td>
                                        <strong>{{ script.name }}</strong>
                                        {% if script.description %}
                                            <br><small class="text-muted">{{ script.description[:50] }}{% if script.description|length > 50 %}...{% endif %}</small>
                                        {% endif %}
                                    </td>
                                    <td><span class="badge bg-secondary">{{ script.script_type.upper() }}</span></td>
                                    <td>{{ (script.file_size / 1024)|round(1) }} KB</td>
                                    <td>{{ script.created_at.strftime('%Y-%m-%d %H:%M') }}</td>
                                    <td>
                                        <form method="POST" action="{{ url_for('execute_script', script_id=script.id) }}" class="d-inline">
                                            <button type="submit" class="btn btn-sm btn-success" title="Execute">
                                                <i class="bi bi-play"></i>
                                            </button>
                                        </form>
                                    </td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                {% else %}
                    <div class="p-5 text-center">
                        <i class="bi bi-file-code text-muted" style="font-size: 4rem;"></i>
                        <h3 class="mt-3 text-muted">No Scripts Yet</h3>
                        <p class="text-muted">Upload your first Python or Batch script to get started with automation.</p>
                        <a href="{{ url_for('upload_script') }}" class="btn btn-primary btn-lg">
                            <i class="bi bi-upload me-2"></i>Upload First Script
                        </a>
                    </div>
                {% endif %}
            </div>
        </div>
    </main>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
''',

    'upload.html': '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ScriptFlow - Upload Script</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css" rel="stylesheet">
    <style>
        body { background-color: #f8f9fa; padding-top: 76px; }
        .navbar-brand { font-weight: 600; }
        .card { border: none; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark fixed-top">
        <div class="container">
            <a class="navbar-brand" href="{{ url_for('dashboard') }}">
                <i class="bi bi-gear-fill me-2"></i>ScriptFlow
            </a>
            <div class="navbar-nav ms-auto">
                <a class="nav-link" href="{{ url_for('dashboard') }}">Dashboard</a>
                <a class="nav-link" href="{{ url_for('scripts') }}">Scripts</a>
                <a class="nav-link" href="{{ url_for('logs') }}">Logs</a>
                <div class="nav-item dropdown">
                    <a class="nav-link dropdown-toggle" href="#" role="button" data-bs-toggle="dropdown">
                        {{ current_user.username }}
                    </a>
                    <ul class="dropdown-menu">
                        <li><a class="dropdown-item" href="{{ url_for('logout') }}">Logout</a></li>
                    </ul>
                </div>
            </div>
        </div>
    </nav>

    <main class="container mt-4">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ 'danger' if category == 'error' else category }} alert-dismissible fade show">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <div class="row justify-content-center">
            <div class="col-md-8">
                <div class="card">
                    <div class="card-header bg-primary text-white">
                        <h4 class="mb-0"><i class="bi bi-upload me-2"></i>Upload New Script</h4>
                    </div>
                    <div class="card-body">
                        <form method="POST" enctype="multipart/form-data">
                            <div class="mb-3">
                                <label for="file" class="form-label">Script File</label>
                                <input type="file" class="form-control" id="file" name="file" accept=".py,.bat" required>
                                <div class="form-text">Supported: .py (Python) and .bat (Batch) files. Max size: 10MB</div>
                            </div>

                            <div class="mb-3">
                                <label for="name" class="form-label">Script Name</label>
                                <input type="text" class="form-control" id="name" name="name" placeholder="Enter a descriptive name">
                                <div class="form-text">Leave blank to use filename</div>
                            </div>

                            <div class="mb-3">
                                <label for="description" class="form-label">Description (Optional)</label>
                                <textarea class="form-control" id="description" name="description" rows="3" placeholder="Describe what this script does..."></textarea>
                            </div>

                            <div class="d-flex justify-content-between">
                                <a href="{{ url_for('scripts') }}" class="btn btn-secondary">
                                    <i class="bi bi-arrow-left me-2"></i>Back to Scripts
                                </a>
                                <button type="submit" class="btn btn-primary">
                                    <i class="bi bi-upload me-2"></i>Upload Script
                                </button>
                            </div>
                        </form>
                    </div>
                </div>

                <div class="card mt-4">
                    <div class="card-header">
                        <h5 class="mb-0"><i class="bi bi-info-circle me-2"></i>Supported Script Types</h5>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-6">
                                <h6><i class="bi bi-file-code me-2"></i>Python Scripts (.py)</h6>
                                <ul>
                                    <li>Full Python 3 support</li>
                                    <li>Standard library available</li>
                                    <li>Isolated execution environment</li>
                                    <li>Captured stdout/stderr</li>
                                </ul>
                            </div>
                            <div class="col-md-6">
                                <h6><i class="bi bi-terminal me-2"></i>Batch Scripts (.bat)</h6>
                                <ul>
                                    <li>Windows batch commands</li>
                                    <li>Cross-platform execution</li>
                                    <li>Environment variable access</li>
                                    <li>Command chaining support</li>
                                </ul>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </main>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
''',

    'logs.html': '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ScriptFlow - Execution Logs</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css" rel="stylesheet">
    <style>
        body { background-color: #f8f9fa; padding-top: 76px; }
        .navbar-brand { font-weight: 600; }
        .card { border: none; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .status-success { color: #27AE60; }
        .status-warning { color: #F39C12; }
        .status-danger { color: #E74C3C; }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark fixed-top">
        <div class="container">
            <a class="navbar-brand" href="{{ url_for('dashboard') }}">
                <i class="bi bi-gear-fill me-2"></i>ScriptFlow
            </a>
            <div class="navbar-nav ms-auto">
                <a class="nav-link" href="{{ url_for('dashboard') }}">Dashboard</a>
                <a class="nav-link" href="{{ url_for('scripts') }}">Scripts</a>
                <a class="nav-link active" href="{{ url_for('logs') }}">Logs</a>
                <div class="nav-item dropdown">
                    <a class="nav-link dropdown-toggle" href="#" role="button" data-bs-toggle="dropdown">
                        {{ current_user.username }}
                    </a>
                    <ul class="dropdown-menu">
                        <li><a class="dropdown-item" href="{{ url_for('logout') }}">Logout</a></li>
                    </ul>
                </div>
            </div>
        </div>
    </nav>

    <main class="container mt-4">
        <div class="row mb-4">
            <div class="col">
                <h1><i class="bi bi-clock-history me-2"></i>Execution Logs</h1>
            </div>
        </div>

        <div class="card">
            <div class="card-body p-0">
                {% if executions.items %}
                    <div class="table-responsive">
                        <table class="table table-hover mb-0">
                            <thead class="table-light">
                                <tr>
                                    <th>Script</th>
                                    <th>Status</th>
                                    <th>Started</th>
                                    <th>Duration</th>
                                    <th>Exit Code</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for execution in executions.items %}
                                <tr>
                                    <td>
                                        <strong>{{ execution.script.name if execution.script else 'Unknown' }}</strong>
                                    </td>
                                    <td>
                                        <span class="status-{{ execution.status_color }}">
                                            {{ execution.status_icon }} {{ execution.status.title() }}
                                        </span>
                                    </td>
                                    <td>{{ execution.started_at.strftime('%Y-%m-%d %H:%M:%S') }}</td>
                                    <td>{{ execution.formatted_duration }}</td>
                                    <td>
                                        {% if execution.exit_code is not none %}
                                            <span class="badge bg-{{ 'success' if execution.exit_code == 0 else 'danger' }}">
                                                {{ execution.exit_code }}
                                            </span>
                                        {% else %}
                                            <span class="text-muted">-</span>
                                        {% endif %}
                                    </td>
                                    <td>
                                        <a href="{{ url_for('view_execution', execution_id=execution.id) }}" class="btn btn-sm btn-outline-primary">
                                            <i class="bi bi-eye me-1"></i>View
                                        </a>
                                    </td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>

                    <!-- Pagination -->
                    {% if executions.pages > 1 %}
                    <div class="card-footer">
                        <nav>
                            <ul class="pagination justify-content-center mb-0">
                                {% if executions.has_prev %}
                                    <li class="page-item">
                                        <a class="page-link" href="{{ url_for('logs', page=executions.prev_num) }}">Previous</a>
                                    </li>
                                {% endif %}
                                
                                {% for page_num in executions.iter_pages() %}
                                    {% if page_num %}
                                        {% if page_num != executions.page %}
                                            <li class="page-item">
                                                <a class="page-link" href="{{ url_for('logs', page=page_num) }}">{{ page_num }}</a>
                                            </li>
                                        {% else %}
                                            <li class="page-item active">
                                                <span class="page-link">{{ page_num }}</span>
                                            </li>
                                        {% endif %}
                                    {% else %}
                                        <li class="page-item disabled">
                                            <span class="page-link">...</span>
                                        </li>
                                    {% endif %}
                                {% endfor %}
                                
                                {% if executions.has_next %}
                                    <li class="page-item">
                                        <a class="page-link" href="{{ url_for('logs', page=executions.next_num) }}">Next</a>
                                    </li>
                                {% endif %}
                            </ul>
                        </nav>
                    </div>
                    {% endif %}
                {% else %}
                    <div class="p-5 text-center">
                        <i class="bi bi-clock-history text-muted" style="font-size: 4rem;"></i>
                        <h3 class="mt-3 text-muted">No Executions Yet</h3>
                        <p class="text-muted">Execute some scripts to see their logs here.</p>
                        <a href="{{ url_for('scripts') }}" class="btn btn-primary">
                            <i class="bi bi-file-code me-2"></i>Go to Scripts
                        </a>
                    </div>
                {% endif %}
            </div>
        </div>
    </main>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
''',

    'execution_detail.html': '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ScriptFlow - Execution Details</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css" rel="stylesheet">
    <style>
        body { background-color: #f8f9fa; padding-top: 76px; }
        .navbar-brand { font-weight: 600; }
        .card { border: none; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .log-output { background-color: #2d3748; color: #e2e8f0; padding: 1rem; border-radius: 6px; font-family: Monaco, monospace; font-size: 0.875rem; max-height: 400px; overflow-y: auto; white-space: pre-wrap; }
        .status-success { color: #27AE60; }
        .status-warning { color: #F39C12; }
        .status-danger { color: #E74C3C; }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark fixed-top">
        <div class="container">
            <a class="navbar-brand" href="{{ url_for('dashboard') }}">
                <i class="bi bi-gear-fill me-2"></i>ScriptFlow
            </a>
            <div class="navbar-nav ms-auto">
                <a class="nav-link" href="{{ url_for('dashboard') }}">Dashboard</a>
                <a class="nav-link" href="{{ url_for('scripts') }}">Scripts</a>
                <a class="nav-link" href="{{ url_for('logs') }}">Logs</a>
                <div class="nav-item dropdown">
                    <a class="nav-link dropdown-toggle" href="#" role="button" data-bs-toggle="dropdown">
                        {{ current_user.username }}
                    </a>
                    <ul class="dropdown-menu">
                        <li><a class="dropdown-item" href="{{ url_for('logout') }}">Logout</a></li>
                    </ul>
                </div>
            </div>
        </div>
    </nav>

    <main class="container mt-4">
        <div class="row mb-4">
            <div class="col">
                <nav aria-label="breadcrumb">
                    <ol class="breadcrumb">
                        <li class="breadcrumb-item"><a href="{{ url_for('logs') }}">Logs</a></li>
                        <li class="breadcrumb-item active">Execution #{{ execution.id }}</li>
                    </ol>
                </nav>
                <h1><i class="bi bi-file-play me-2"></i>Execution Details</h1>
            </div>
        </div>

        <!-- Execution Info -->
        <div class="card mb-4">
            <div class="card-header bg-primary text-white">
                <h5 class="mb-0">{{ execution.script.name if execution.script else 'Unknown Script' }}</h5>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-6">
                        <p><strong>Status:</strong> 
                            <span class="status-{{ execution.status_color }}">
                                {{ execution.status_icon }} {{ execution.status.title() }}
                            </span>
                        </p>
                        <p><strong>Started:</strong> {{ execution.started_at.strftime('%Y-%m-%d %H:%M:%S') }}</p>
                        {% if execution.completed_at %}
                            <p><strong>Completed:</strong> {{ execution.completed_at.strftime('%Y-%m-%d %H:%M:%S') }}</p>
                        {% endif %}
                        <p><strong>Duration:</strong> {{ execution.formatted_duration }}</p>
                    </div>
                    <div class="col-md-6">
                        {% if execution.exit_code is not none %}
                            <p><strong>Exit Code:</strong> 
                                <span class="badge bg-{{ 'success' if execution.exit_code == 0 else 'danger' }}">
                                    {{ execution.exit_code }}
                                </span>
                            </p>
                        {% endif %}
                        {% if execution.script %}
                            <p><strong>Script Type:</strong> {{ execution.script.script_type.upper() }}</p>
                            <p><strong>Script Size:</strong> {{ (execution.script.file_size / 1024)|round(1) }} KB</p>
                        {% endif %}
                    </div>
                </div>
            </div>
        </div>

        <!-- Output -->
        {% if execution.stdout %}
            <div class="card mb-4">
                <div class="card-header">
                    <h5 class="mb-0"><i class="bi bi-terminal me-2"></i>Standard Output</h5>
                </div>
                <div class="card-body">
                    <div class="log-output">{{ execution.stdout }}</div>
                </div>
            </div>
        {% endif %}

        {% if execution.stderr %}
            <div class="card mb-4">
                <div class="card-header bg-danger text-white">
                    <h5 class="mb-0"><i class="bi bi-exclamation-triangle me-2"></i>Error Output</h5>
                </div>
                <div class="card-body">
                    <div class="log-output">{{ execution.stderr }}</div>
                </div>
            </div>
        {% endif %}

        {% if not execution.stdout and not execution.stderr %}
            <div class="card">
                <div class="card-body text-center">
                    <i class="bi bi-info-circle text-muted" style="font-size: 3rem;"></i>
                    <h5 class="mt-3 text-muted">No Output</h5>
                    <p class="text-muted">This execution produced no output.</p>
                </div>
            </div>
        {% endif %}
    </main>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
'''
}

# Register templates
@app.context_processor
def inject_templates():
    return dict()

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

# # Create render_template function that uses inline templates
# original_render_template = app.jinja_env.get_template

# def custom_render_template(template_name, **context):
#     if template_name in templates:
#         template = app.jinja_env.from_string(templates[template_name])
#         return template.render(**context)
#     return original_render_template(template_name).render(**context)

# app.jinja_env.globals['render_template'] = custom_render_template

# # Override render_template
# import flask
# flask.render_template = custom_render_template

if __name__ == '__main__':
    # Setup database and directories
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    
    with app.app_context():
        db.create_all()
        
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
    
    # Find free port and start
    port = find_free_port()
    print(f"\n🚀 ScriptFlow Full System starting on http://localhost:{port}")
    print("👤 Default login: admin/admin123")
    print("🛑 Press Ctrl+C to stop\n")
    
    app.run(debug=True, host='0.0.0.0', port=port)