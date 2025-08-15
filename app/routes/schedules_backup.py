"""
Schedules Routes - Schedule management and configuration
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from datetime import datetime
import json

from app.models.script import Script
from app.models.schedule import Schedule, ScheduleFrequency
from app.models import db

schedules_bp = Blueprint('schedules', __name__)

@schedules_bp.route('/')
@login_required
def index():
    """Schedules list page"""
    
    # Get user's schedules with script information
    schedules = Schedule.query.join(Script).filter(
        Script.user_id == current_user.id
    ).order_by(Schedule.next_execution.asc()).all()
    
    # Separate active and inactive schedules
    active_schedules = [s for s in schedules if s.is_active]
    inactive_schedules = [s for s in schedules if not s.is_active]
    
    return render_template('schedules/index.html',
                         active_schedules=active_schedules,
                         inactive_schedules=inactive_schedules)

@schedules_bp.route('/create', methods=['GET', 'POST'])
@schedules_bp.route('/create/<int:script_id>', methods=['GET', 'POST'])
@login_required
def create(script_id=None):
    """Create new schedule"""
    
    # Get user's scripts for dropdown
    user_scripts = Script.query.filter_by(user_id=current_user.id, is_active=True)\
        .order_by(Script.name).all()
    
    if not user_scripts:
        flash('You must upload at least one script before creating a schedule.', 'warning')
        return redirect(url_for('scripts.upload'))
    
    # If script_id provided, validate it belongs to user
    selected_script = None
    if script_id:
        selected_script = Script.query.filter_by(
            id=script_id, 
            user_id=current_user.id, 
            is_active=True
        ).first()
        if not selected_script:
            flash('Script not found.', 'error')
            return redirect(url_for('schedules.index'))
    
    if request.method == 'POST':
        try:
            # Get form data
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            target_script_id = int(request.form.get('script_id'))
            frequency = request.form.get('frequency')
            
            # Validate required fields
            if not name:
                flash('Schedule name is required.', 'error')
                return redirect(request.url)
            
            if not frequency or frequency not in [f.value for f in ScheduleFrequency]:
                flash('Valid frequency is required.', 'error')
                return redirect(request.url)
            
            # Validate script ownership
            target_script = Script.query.filter_by(
                id=target_script_id,
                user_id=current_user.id,
                is_active=True
            ).first()
            
            if not target_script:
                flash('Selected script not found.', 'error')
                return redirect(request.url)
            
            # Check for existing active schedule on this script
            existing_schedule = Schedule.query.filter_by(
                script_id=target_script_id,
                is_active=True
            ).first()
            
            if existing_schedule:
                flash(f'Script "{target_script.name}" already has an active schedule.', 'warning')
                return redirect(request.url)
            
            # Build schedule configuration
            schedule_config = build_schedule_config(frequency, request.form)
            
            # Get notification settings
            notify_on_success = bool(request.form.get('notify_on_success'))
            notify_on_failure = bool(request.form.get('notify_on_failure'))
            notification_emails = request.form.get('notification_emails', '').strip()
            
            # Parse email list
            email_list = []\n            if notification_emails:\n                email_list = [email.strip() for email in notification_emails.split(',') if email.strip()]\n            \n            # Create schedule\n            schedule = Schedule(\n                name=name,\n                script_id=target_script_id,\n                frequency=ScheduleFrequency(frequency),\n                schedule_config=json.dumps(schedule_config) if schedule_config else None,\n                description=description\n            )\n            \n            schedule.notify_on_success = notify_on_success\n            schedule.notify_on_failure = notify_on_failure\n            schedule.notification_email_list = email_list\n            \n            db.session.add(schedule)\n            db.session.commit()\n            \n            flash(f'Schedule \"{name}\" created successfully!', 'success')\n            return redirect(url_for('schedules.view', id=schedule.id))\n            \n        except ValueError as e:\n            flash(f'Invalid form data: {str(e)}', 'error')\n            return redirect(request.url)\n        except Exception as e:\n            flash(f'Error creating schedule: {str(e)}', 'error')\n            return redirect(request.url)\n    \n    return render_template('schedules/create.html',\n                         user_scripts=user_scripts,\n                         selected_script=selected_script)\n\n@schedules_bp.route('/<int:id>')\n@login_required\ndef view(id):\n    \"\"\"View schedule details\"\"\"\n    \n    schedule = Schedule.query.join(Script).filter(\n        Schedule.id == id,\n        Script.user_id == current_user.id\n    ).first_or_404()\n    \n    # Get recent executions for this schedule\n    recent_executions = schedule.executions[:10]  # Last 10 executions\n    \n    return render_template('schedules/view.html',\n                         schedule=schedule,\n                         recent_executions=recent_executions)\n\n@schedules_bp.route('/<int:id>/edit', methods=['GET', 'POST'])\n@login_required\ndef edit(id):\n    \"\"\"Edit schedule\"\"\"\n    \n    schedule = Schedule.query.join(Script).filter(\n        Schedule.id == id,\n        Script.user_id == current_user.id\n    ).first_or_404()\n    \n    if request.method == 'POST':\n        try:\n            # Update basic info\n            schedule.name = request.form.get('name', '').strip()\n            schedule.description = request.form.get('description', '').strip()\n            \n            # Update frequency and config\n            frequency = request.form.get('frequency')\n            if frequency and frequency in [f.value for f in ScheduleFrequency]:\n                schedule.frequency = ScheduleFrequency(frequency)\n                schedule_config = build_schedule_config(frequency, request.form)\n                schedule.config_dict = schedule_config\n            \n            # Update notification settings\n            schedule.notify_on_success = bool(request.form.get('notify_on_success'))\n            schedule.notify_on_failure = bool(request.form.get('notify_on_failure'))\n            \n            notification_emails = request.form.get('notification_emails', '').strip()\n            if notification_emails:\n                email_list = [email.strip() for email in notification_emails.split(',') if email.strip()]\n                schedule.notification_email_list = email_list\n            else:\n                schedule.notification_email_list = []\n            \n            # Recalculate next execution\n            schedule.update_next_execution()\n            \n            flash(f'Schedule \"{schedule.name}\" updated successfully!', 'success')\n            return redirect(url_for('schedules.view', id=schedule.id))\n            \n        except Exception as e:\n            flash(f'Error updating schedule: {str(e)}', 'error')\n            return redirect(request.url)\n    \n    return render_template('schedules/edit.html', schedule=schedule)\n\n@schedules_bp.route('/<int:id>/toggle', methods=['POST'])\n@login_required\ndef toggle_active(id):\n    \"\"\"Toggle schedule active status\"\"\"\n    \n    schedule = Schedule.query.join(Script).filter(\n        Schedule.id == id,\n        Script.user_id == current_user.id\n    ).first_or_404()\n    \n    try:\n        schedule.toggle_active()\n        \n        status = \"activated\" if schedule.is_active else \"deactivated\"\n        flash(f'Schedule \"{schedule.name}\" {status} successfully!', 'success')\n        \n    except Exception as e:\n        flash(f'Error toggling schedule: {str(e)}', 'error')\n    \n    return redirect(url_for('schedules.view', id=schedule.id))\n\n@schedules_bp.route('/<int:id>/delete', methods=['POST'])\n@login_required\ndef delete(id):\n    \"\"\"Delete schedule\"\"\"\n    \n    schedule = Schedule.query.join(Script).filter(\n        Schedule.id == id,\n        Script.user_id == current_user.id\n    ).first_or_404()\n    \n    try:\n        schedule_name = schedule.name\n        db.session.delete(schedule)\n        db.session.commit()\n        \n        flash(f'Schedule \"{schedule_name}\" deleted successfully.', 'success')\n        \n    except Exception as e:\n        flash(f'Error deleting schedule: {str(e)}', 'error')\n    \n    return redirect(url_for('schedules.index'))\n\ndef build_schedule_config(frequency, form_data):\n    \"\"\"Build schedule configuration dictionary from form data\"\"\"\n    \n    config = {}\n    \n    if frequency == ScheduleFrequency.DAILY.value:\n        time = form_data.get('daily_time', '00:00')\n        config['time'] = time\n        \n    elif frequency == ScheduleFrequency.WEEKLY.value:\n        time = form_data.get('weekly_time', '00:00')\n        days = form_data.getlist('weekly_days')\n        \n        # Validate days\n        valid_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']\n        selected_days = [day for day in days if day in valid_days]\n        \n        if not selected_days:\n            selected_days = ['Monday']  # Default to Monday\n        \n        config['time'] = time\n        config['days'] = selected_days\n        \n    elif frequency == ScheduleFrequency.MONTHLY.value:\n        time = form_data.get('monthly_time', '00:00')\n        day = int(form_data.get('monthly_day', 1))\n        \n        # Validate day (1-31)\n        if day < 1 or day > 31:\n            day = 1\n        \n        config['time'] = time\n        config['day'] = day\n    \n    # Hourly doesn't need additional config\n    \n    return config"