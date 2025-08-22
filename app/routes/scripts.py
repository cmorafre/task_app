"""
Scripts Routes - Script upload, management, and execution
"""

import os
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, current_app, send_file
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime

from app.models.script import Script
from app.models.execution import Execution, ExecutionTrigger
from app.services.script_executor import script_executor
from app.models import db
# UI Version Manager removed - using V2 templates only

scripts_bp = Blueprint('scripts', __name__)

ALLOWED_EXTENSIONS = {'py', 'bat'}

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@scripts_bp.route('/')
@login_required
def index():
    """Scripts list page"""
    from datetime import datetime, timedelta
    from sqlalchemy import desc, asc, func
    
    # Get filters from query parameters
    search = request.args.get('search', '').strip()
    script_type = request.args.get('type', '')
    size_filter = request.args.get('size', '')
    date_filter = request.args.get('date', '')
    sort_by = request.args.get('sort', 'updated')
    
    # Build query
    query = Script.query.filter_by(user_id=current_user.id, is_active=True)
    
    # Search filter
    if search:
        query = query.filter(Script.name.contains(search))
    
    # Type filter
    if script_type and script_type in ALLOWED_EXTENSIONS:
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
        query = query.order_by(asc(Script.name))
    elif sort_by == 'size':
        query = query.order_by(desc(Script.file_size))
    elif sort_by == 'executions':
        # Join with executions to count
        query = query.outerjoin(Execution).group_by(Script.id).order_by(desc(func.count(Execution.id)))
    else:  # default to 'updated'
        query = query.order_by(desc(Script.updated_at))
    
    scripts = query.all()
    
    return render_template('scripts.html', 
                         scripts=scripts,
                         search=search,
                         script_type=script_type,
                         size_filter=size_filter,
                         date_filter=date_filter,
                         sort_by=sort_by)

@scripts_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    """Script upload page"""
    
    if request.method == 'POST':
        # Check if file is in request
        if 'file' not in request.files:
            flash('No file selected.', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        
        # Validate file
        if file.filename == '':
            flash('No file selected.', 'error')
            return redirect(request.url)
        
        if not allowed_file(file.filename):
            flash('Only .py and .bat files are allowed.', 'error')
            return redirect(request.url)
        
        # Validate name
        if not name:
            name = file.filename.rsplit('.', 1)[0]  # Use filename without extension
        
        # Check for duplicate names
        existing = Script.query.filter_by(user_id=current_user.id, name=name, is_active=True).first()
        if existing:
            flash(f'A script named "{name}" already exists.', 'error')
            return redirect(request.url)
        
        # Secure filename
        filename = secure_filename(file.filename)
        script_type = filename.rsplit('.', 1)[1].lower()
        
        # Create unique filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{current_user.id}_{timestamp}_{filename}"
        
        # Ensure upload directory exists
        upload_dir = current_app.config['UPLOAD_FOLDER']
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, unique_filename)
        
        try:
            # Save file
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
            return redirect(url_for('scripts.view', id=script.id))
            
        except Exception as e:
            # Clean up file if database save failed
            if os.path.exists(file_path):
                os.remove(file_path)
            
            flash(f'Error uploading script: {str(e)}', 'error')
            return redirect(request.url)
    
    return render_template('upload.html')

@scripts_bp.route('/<int:id>')
@login_required
def view(id):
    """View script details"""
    
    script = Script.query.filter_by(id=id, user_id=current_user.id, is_active=True).first_or_404()
    
    # Get recent executions
    recent_executions = Execution.query.filter_by(script_id=script.id)\
        .order_by(Execution.started_at.desc())\
        .limit(10).all()
    
    return render_template('view_script.html', 
                         script=script,
                         recent_executions=recent_executions)

@scripts_bp.route('/<int:id>/execute', methods=['POST'])
@login_required
def execute(id):
    """Execute script manually"""
    
    script = Script.query.filter_by(id=id, user_id=current_user.id, is_active=True).first_or_404()
    
    try:
        execution = script_executor.execute_script(
            script_id=script.id,
            user_id=current_user.id,
            trigger_type=ExecutionTrigger.MANUAL
        )
        
        flash(f'Script "{script.name}" started successfully!', 'success')
        return redirect(url_for('logs.view_execution', id=execution.id))
        
    except Exception as e:
        flash(f'Error starting script: {str(e)}', 'error')
        return redirect(url_for('scripts.view', id=script.id))

@scripts_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    """Edit script metadata"""
    
    script = Script.query.filter_by(id=id, user_id=current_user.id, is_active=True).first_or_404()
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        
        # Validate name
        if not name:
            flash('Script name is required.', 'error')
            return redirect(request.url)
        
        # Check for duplicate names (excluding current script)
        existing = Script.query.filter(
            Script.user_id == current_user.id,
            Script.name == name,
            Script.is_active == True,
            Script.id != script.id
        ).first()
        
        if existing:
            flash(f'A script named "{name}" already exists.', 'error')
            return redirect(request.url)
        
        # Update script
        script.name = name
        script.description = description
        script.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        flash(f'Script "{name}" updated successfully!', 'success')
        return redirect(url_for('scripts.view', id=script.id))
    
    return render_template('edit_script.html', script=script)

@scripts_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    """Delete script"""
    
    script = Script.query.filter_by(id=id, user_id=current_user.id, is_active=True).first_or_404()
    
    try:
        # Deactivate script (soft delete)
        script.is_active = False
        script.updated_at = datetime.utcnow()
        
        # Deactivate any active schedules
        for schedule in script.schedules:
            if schedule.is_active:
                schedule.is_active = False
        
        db.session.commit()
        
        # Optionally delete physical file
        # script.delete_file()
        
        flash(f'Script "{script.name}" deleted successfully.', 'success')
        return redirect(url_for('scripts.index'))
        
    except Exception as e:
        flash(f'Error deleting script: {str(e)}', 'error')
        return redirect(url_for('scripts.view', id=script.id))

@scripts_bp.route('/<int:id>/download')
@login_required
def download(id):
    """Download script file"""
    
    script = Script.query.filter_by(id=id, user_id=current_user.id, is_active=True).first_or_404()
    
    if not script.file_exists:
        flash('Script file not found.', 'error')
        return redirect(url_for('scripts.view', id=script.id))
    
    return send_file(
        script.file_path,
        as_attachment=True,
        download_name=script.filename
    )