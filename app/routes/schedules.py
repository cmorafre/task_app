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
            email_list = []
            if notification_emails:
                email_list = [email.strip() for email in notification_emails.split(',') if email.strip()]
            
            # Create schedule
            schedule = Schedule(
                name=name,
                script_id=target_script_id,
                frequency=ScheduleFrequency(frequency),
                schedule_config=json.dumps(schedule_config) if schedule_config else None,
                description=description
            )
            
            schedule.notify_on_success = notify_on_success
            schedule.notify_on_failure = notify_on_failure
            schedule.notification_email_list = email_list
            
            db.session.add(schedule)
            db.session.commit()
            
            flash(f'Schedule "{name}" created successfully!', 'success')
            return redirect(url_for('schedules.view', id=schedule.id))
            
        except ValueError as e:
            flash(f'Invalid form data: {str(e)}', 'error')
            return redirect(request.url)
        except Exception as e:
            flash(f'Error creating schedule: {str(e)}', 'error')
            return redirect(request.url)
    
    return render_template('schedules/create.html',
                         user_scripts=user_scripts,
                         selected_script=selected_script)

@schedules_bp.route('/<int:id>')
@login_required
def view(id):
    """View schedule details"""
    
    schedule = Schedule.query.join(Script).filter(
        Schedule.id == id,
        Script.user_id == current_user.id
    ).first_or_404()
    
    # Get recent executions for this schedule
    recent_executions = schedule.executions[:10]  # Last 10 executions
    
    return render_template('schedules/view.html',
                         schedule=schedule,
                         recent_executions=recent_executions)

@schedules_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    """Edit schedule"""
    
    schedule = Schedule.query.join(Script).filter(
        Schedule.id == id,
        Script.user_id == current_user.id
    ).first_or_404()
    
    if request.method == 'POST':
        try:
            # Update basic info
            schedule.name = request.form.get('name', '').strip()
            schedule.description = request.form.get('description', '').strip()
            
            # Update frequency and config
            frequency = request.form.get('frequency')
            if frequency and frequency in [f.value for f in ScheduleFrequency]:
                schedule.frequency = ScheduleFrequency(frequency)
                schedule_config = build_schedule_config(frequency, request.form)
                schedule.config_dict = schedule_config
            
            # Update notification settings
            schedule.notify_on_success = bool(request.form.get('notify_on_success'))
            schedule.notify_on_failure = bool(request.form.get('notify_on_failure'))
            
            notification_emails = request.form.get('notification_emails', '').strip()
            if notification_emails:
                email_list = [email.strip() for email in notification_emails.split(',') if email.strip()]
                schedule.notification_email_list = email_list
            else:
                schedule.notification_email_list = []
            
            # Recalculate next execution
            schedule.update_next_execution()
            
            flash(f'Schedule "{schedule.name}" updated successfully!', 'success')
            return redirect(url_for('schedules.view', id=schedule.id))
            
        except Exception as e:
            flash(f'Error updating schedule: {str(e)}', 'error')
            return redirect(request.url)
    
    return render_template('schedules/edit.html', schedule=schedule)

@schedules_bp.route('/<int:id>/toggle', methods=['POST'])
@login_required
def toggle_active(id):
    """Toggle schedule active status"""
    
    schedule = Schedule.query.join(Script).filter(
        Schedule.id == id,
        Script.user_id == current_user.id
    ).first_or_404()
    
    try:
        schedule.toggle_active()
        
        status = "activated" if schedule.is_active else "deactivated"
        flash(f'Schedule "{schedule.name}" {status} successfully!', 'success')
        
    except Exception as e:
        flash(f'Error toggling schedule: {str(e)}', 'error')
    
    return redirect(url_for('schedules.view', id=schedule.id))

@schedules_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    """Delete schedule"""
    
    schedule = Schedule.query.join(Script).filter(
        Schedule.id == id,
        Script.user_id == current_user.id
    ).first_or_404()
    
    try:
        schedule_name = schedule.name
        db.session.delete(schedule)
        db.session.commit()
        
        flash(f'Schedule "{schedule_name}" deleted successfully.', 'success')
        
    except Exception as e:
        flash(f'Error deleting schedule: {str(e)}', 'error')
    
    return redirect(url_for('schedules.index'))

def build_schedule_config(frequency, form_data):
    """Build schedule configuration dictionary from form data"""
    
    config = {}
    
    if frequency == ScheduleFrequency.DAILY.value:
        time = form_data.get('time', '00:00')
        start_date = form_data.get('start_date', '')
        config['time'] = time
        if start_date:
            config['start_date'] = start_date
        
    elif frequency == ScheduleFrequency.WEEKLY.value:
        time = form_data.get('time', '00:00')
        start_date = form_data.get('start_date', '')
        days = form_data.getlist('days')
        
        # Validate days
        valid_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        selected_days = [day for day in days if day in valid_days]
        
        if not selected_days:
            selected_days = ['Monday']  # Default to Monday
        
        config['time'] = time
        config['days'] = selected_days
        if start_date:
            config['start_date'] = start_date
        
    elif frequency == ScheduleFrequency.MONTHLY.value:
        time = form_data.get('time', '00:00')
        start_date = form_data.get('start_date', '')
        day = int(form_data.get('day', 1))
        
        # Validate day (1-31)
        if day < 1 or day > 31:
            day = 1
        
        config['time'] = time
        config['day'] = day
        if start_date:
            config['start_date'] = start_date
        
    elif frequency == ScheduleFrequency.INTERVAL.value:
        interval_minutes = form_data.get('interval_minutes', '15')
        time = form_data.get('time', '09:00')
        start_date = form_data.get('start_date', '')
        
        # Validate interval minutes
        try:
            interval_minutes = int(interval_minutes)
            if interval_minutes <= 0:
                interval_minutes = 15
        except (ValueError, TypeError):
            interval_minutes = 15
        
        config['interval_minutes'] = interval_minutes
        config['time'] = time
        if start_date:
            config['start_date'] = start_date
    
    # Hourly doesn't need additional config
    
    return config