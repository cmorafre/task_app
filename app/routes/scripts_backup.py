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

scripts_bp = Blueprint('scripts', __name__)

ALLOWED_EXTENSIONS = {'py', 'bat'}

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@scripts_bp.route('/')
@login_required
def index():
    """Scripts list page"""
    
    # Get filters from query parameters
    search = request.args.get('search', '').strip()
    script_type = request.args.get('type', '')
    status = request.args.get('status', '')
    
    # Build query
    query = Script.query.filter_by(user_id=current_user.id, is_active=True)
    
    if search:
        query = query.filter(Script.name.contains(search))
    
    if script_type and script_type in ALLOWED_EXTENSIONS:
        query = query.filter_by(script_type=script_type)
    
    # TODO: Add status filtering based on last execution
    
    scripts = query.order_by(Script.updated_at.desc()).all()
    
    return render_template('scripts/index.html', 
                         scripts=scripts,
                         search=search,
                         script_type=script_type,
                         status=status)

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
    
    return render_template('scripts/upload.html')

@scripts_bp.route('/<int:id>')
@login_required
def view(id):
    """View script details"""
    
    script = Script.query.filter_by(id=id, user_id=current_user.id, is_active=True).first_or_404()
    
    # Get recent executions
    recent_executions = Execution.query.filter_by(script_id=script.id)\
        .order_by(Execution.started_at.desc())\
        .limit(10).all()
    
    return render_template('scripts/view.html', 
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
        return redirect(url_for('scripts.view', id=script.id))\n\n@scripts_bp.route('/<int:id>/edit', methods=['GET', 'POST'])\n@login_required\ndef edit(id):\n    \"\"\"Edit script metadata\"\"\"\n    \n    script = Script.query.filter_by(id=id, user_id=current_user.id, is_active=True).first_or_404()\n    \n    if request.method == 'POST':\n        name = request.form.get('name', '').strip()\n        description = request.form.get('description', '').strip()\n        \n        # Validate name\n        if not name:\n            flash('Script name is required.', 'error')\n            return redirect(request.url)\n        \n        # Check for duplicate names (excluding current script)\n        existing = Script.query.filter(\n            Script.user_id == current_user.id,\n            Script.name == name,\n            Script.is_active == True,\n            Script.id != script.id\n        ).first()\n        \n        if existing:\n            flash(f'A script named \"{name}\" already exists.', 'error')\n            return redirect(request.url)\n        \n        # Update script\n        script.name = name\n        script.description = description\n        script.updated_at = datetime.utcnow()\n        \n        db.session.commit()\n        \n        flash(f'Script \"{name}\" updated successfully!', 'success')\n        return redirect(url_for('scripts.view', id=script.id))\n    \n    return render_template('scripts/edit.html', script=script)\n\n@scripts_bp.route('/<int:id>/delete', methods=['POST'])\n@login_required\ndef delete(id):\n    \"\"\"Delete script\"\"\"\n    \n    script = Script.query.filter_by(id=id, user_id=current_user.id, is_active=True).first_or_404()\n    \n    try:\n        # Deactivate script (soft delete)\n        script.is_active = False\n        script.updated_at = datetime.utcnow()\n        \n        # Deactivate any active schedules\n        for schedule in script.schedules:\n            if schedule.is_active:\n                schedule.is_active = False\n        \n        db.session.commit()\n        \n        # Optionally delete physical file\n        # script.delete_file()\n        \n        flash(f'Script \"{script.name}\" deleted successfully.', 'success')\n        return redirect(url_for('scripts.index'))\n        \n    except Exception as e:\n        flash(f'Error deleting script: {str(e)}', 'error')\n        return redirect(url_for('scripts.view', id=script.id))\n\n@scripts_bp.route('/<int:id>/download')\n@login_required\ndef download(id):\n    \"\"\"Download script file\"\"\"\n    \n    script = Script.query.filter_by(id=id, user_id=current_user.id, is_active=True).first_or_404()\n    \n    if not script.file_exists:\n        flash('Script file not found.', 'error')\n        return redirect(url_for('scripts.view', id=script.id))\n    \n    return send_file(\n        script.file_path,\n        as_attachment=True,\n        download_name=script.filename\n    )"