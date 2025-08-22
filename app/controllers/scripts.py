"""
Scripts Blueprint
Handles all script-related operations: list, upload, execute, edit, delete
"""

import os
import threading
import subprocess
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, flash, redirect, url_for, send_file
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from sqlalchemy import func

# Create Blueprint
scripts_bp = Blueprint('scripts', __name__, url_prefix='/scripts')

def init_scripts_blueprint(app, db, Script, Execution, Settings, apply_user_data_filter):
    """Initialize scripts blueprint with dependencies"""
    
    @scripts_bp.route('/')
    @login_required
    def list_scripts():
        # Get filters from query parameters
        search = request.args.get('search', '').strip()
        script_type = request.args.get('type', '')
        size_filter = request.args.get('size', '')
        date_filter = request.args.get('date', '')
        sort_by = request.args.get('sort', 'updated')
        
        # Build query with user permission filter
        scripts_query = Script.query.filter_by(is_active=True)
        query = apply_user_data_filter(scripts_query)
        
        # Search filter
        if search:
            query = query.filter(Script.name.contains(search))
        
        # Type filter
        if script_type and script_type in ['py', 'bat']:
            query = query.filter_by(script_type=script_type)
        
        # Size filter
        if size_filter:
            if size_filter == 'small':
                query = query.filter(Script.file_size < 1024)  # < 1KB
            elif size_filter == 'medium':
                query = query.filter(Script.file_size >= 1024, Script.file_size <= 10240)  # 1KB - 10KB
            elif size_filter == 'large':
                query = query.filter(Script.file_size > 10240)  # > 10KB
        
        # Date filter
        if date_filter:
            now = datetime.now()
            if date_filter == 'today':
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
                query = query.filter(Script.updated_at >= start_date)
            elif date_filter == 'week':
                start_date = now - timedelta(days=7)
                query = query.filter(Script.updated_at >= start_date)
            elif date_filter == 'month':
                start_date = now - timedelta(days=30)
                query = query.filter(Script.updated_at >= start_date)
        
        # Sorting
        if sort_by == 'name':
            query = query.order_by(Script.name.asc())
        elif sort_by == 'size':
            query = query.order_by(Script.file_size.desc())
        elif sort_by == 'executions':
            # Join with executions to count
            query = query.outerjoin(Execution).group_by(Script.id).order_by(func.count(Execution.id).desc())
        else:  # default to 'updated'
            query = query.order_by(Script.updated_at.desc())
        
        user_scripts = query.all()
        
        return render_template('scripts.html', 
                             scripts=user_scripts,
                             search=search,
                             script_type=script_type,
                             size_filter=size_filter,
                             date_filter=date_filter,
                             sort_by=sort_by)

    @scripts_bp.route('/upload', methods=['GET', 'POST'])
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
                return redirect(url_for('scripts.list_scripts'))
                
            except Exception as e:
                if os.path.exists(file_path):
                    os.remove(file_path)
                flash(f'Error uploading script: {str(e)}', 'error')
                return redirect(request.url)
        
        return render_template('upload.html')

    @scripts_bp.route('/<int:script_id>/execute', methods=['GET', 'POST'])
    @login_required
    def execute_script(script_id):
        script = Script.query.filter_by(id=script_id, user_id=current_user.id, is_active=True).first_or_404()
        
        if not script.file_exists:
            flash('Script file not found.', 'error')
            return redirect(url_for('scripts.list_scripts'))
        
        if request.method == 'GET':
            # Show execution page with recent executions
            recent_executions = Execution.query.filter_by(script_id=script.id)\
                .order_by(Execution.started_at.desc())\
                .limit(10).all()
            
            return render_template('execute_script.html', 
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
        return redirect(url_for('logs.list_logs'))

    @scripts_bp.route('/<int:script_id>/view')
    @login_required
    def view_script(script_id):
        """View script content"""
        script = Script.query.filter_by(id=script_id, user_id=current_user.id, is_active=True).first_or_404()
        
        try:
            with open(script.file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            flash(f'Error reading script file: {str(e)}', 'error')
            return redirect(url_for('scripts.list_scripts'))
        
        return render_template('view_script.html', script=script, content=content)

    @scripts_bp.route('/<int:script_id>/edit', methods=['GET', 'POST'])
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
                return redirect(url_for('scripts.list_scripts'))
            except Exception as e:
                flash(f'Error saving script: {str(e)}', 'error')
        
        # GET request - load current content
        try:
            with open(script.file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            flash(f'Error reading script file: {str(e)}', 'error')
            return redirect(url_for('scripts.list_scripts'))
        
        return render_template('edit_script.html', script=script, content=content)

    @scripts_bp.route('/<int:script_id>/download')
    @login_required
    def download_script(script_id):
        """Download script file"""
        script = Script.query.filter_by(id=script_id, user_id=current_user.id, is_active=True).first_or_404()
        
        if not script.file_exists:
            flash('Script file not found.', 'error')
            return redirect(url_for('scripts.list_scripts'))
        
        try:
            return send_file(
                script.file_path,
                as_attachment=True,
                download_name=f"{script.name}.{script.script_type}"
            )
        except Exception as e:
            flash(f'Error downloading script: {str(e)}', 'error')
            return redirect(url_for('scripts.list_scripts'))

    @scripts_bp.route('/<int:script_id>/delete', methods=['POST'])
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
        
        return redirect(url_for('scripts.list_scripts'))

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
    
    return scripts_bp