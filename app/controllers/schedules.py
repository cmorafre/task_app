"""
Schedules Blueprint
Handles all schedule-related operations: list, create, edit, toggle, delete, run
"""

import json
import threading
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user

# Create Blueprint
schedules_bp = Blueprint('schedules', __name__, url_prefix='/schedules')

def init_schedules_blueprint(app, db, Schedule, Script, Execution, apply_user_data_filter, 
                            add_schedule_to_scheduler, remove_schedule_from_scheduler, 
                            execute_script_background):
    """Initialize schedules blueprint with dependencies"""
    
    @schedules_bp.route('/')
    @login_required
    def list_schedules():
        """Schedule management page"""
        # Get filters from query parameters
        search = request.args.get('search', '').strip()
        status_filter = request.args.get('status', '')
        frequency_filter = request.args.get('frequency', '')
        next_run_filter = request.args.get('next_run', '')
        sort_by = request.args.get('sort', 'updated')
        
        # Build query with user permission filter
        schedules_query = Schedule.query
        query = apply_user_data_filter(schedules_query)
        
        # Search filter
        if search:
            query = query.filter(Schedule.name.contains(search))
        
        # Status filter
        if status_filter:
            if status_filter == 'active':
                query = query.filter_by(is_active=True)
            elif status_filter == 'disabled':
                query = query.filter_by(is_active=False)
        
        # Frequency filter
        if frequency_filter:
            query = query.filter_by(frequency=frequency_filter)
        
        # Next run filter
        if next_run_filter:
            now = datetime.now()
            if next_run_filter == 'overdue':
                query = query.filter(Schedule.next_run_time < now, Schedule.is_active == True)
            elif next_run_filter == 'today':
                end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=999999)
                query = query.filter(Schedule.next_run_time >= now, Schedule.next_run_time <= end_of_day)
            elif next_run_filter == 'week':
                end_of_week = now + timedelta(days=7)
                query = query.filter(Schedule.next_run_time >= now, Schedule.next_run_time <= end_of_week)
            elif next_run_filter == 'none':
                query = query.filter(Schedule.next_run_time.is_(None))
        
        # Sorting
        if sort_by == 'name':
            query = query.order_by(Schedule.name.asc())
        elif sort_by == 'next_run':
            query = query.order_by(Schedule.next_run_time.asc().nullslast())
        elif sort_by == 'frequency':
            query = query.order_by(Schedule.frequency.asc())
        else:  # default to 'updated'
            query = query.order_by(Schedule.updated_at.desc())
        
        user_schedules = query.all()
        
        # Get stats (for all user schedules, not filtered)
        all_schedules = apply_user_data_filter(Schedule.query).all()
        active_schedules = sum(1 for s in all_schedules if s.is_active)
        disabled_schedules = len(all_schedules) - active_schedules
        
        # Next run time
        next_schedule = next((s for s in all_schedules if s.is_active and s.next_run_time), None)
        next_run_display = next_schedule.next_run_display if next_schedule else "No upcoming runs"
        
        stats = {
            'active': active_schedules,
            'disabled': disabled_schedules,
            'next_run': next_run_display,
            'avg_per_day': 0  # TODO: Calculate based on execution history
        }
        
        return render_template('schedules.html', 
                             schedules=user_schedules, 
                             stats=stats,
                             search=search,
                             status_filter=status_filter,
                             frequency_filter=frequency_filter,
                             next_run_filter=next_run_filter,
                             sort_by=sort_by)

    @schedules_bp.route('/create', methods=['GET', 'POST'])
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
            return redirect(url_for('schedules.list_schedules'))
        
        # GET request - show form
        user_scripts = Script.query.filter_by(user_id=current_user.id, is_active=True)\
            .order_by(Script.name).all()
        return render_template('create_schedule.html', scripts=user_scripts)

    @schedules_bp.route('/<int:schedule_id>/edit', methods=['GET', 'POST'])
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
            return redirect(url_for('schedules.list_schedules'))
        
        # GET request - show form
        user_scripts = Script.query.filter_by(user_id=current_user.id, is_active=True)\
            .order_by(Script.name).all()
        return render_template('edit_schedule.html', schedule=schedule, scripts=user_scripts)

    @schedules_bp.route('/<int:schedule_id>/toggle', methods=['POST'])
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
        
        return redirect(url_for('schedules.list_schedules'))

    @schedules_bp.route('/<int:schedule_id>/delete', methods=['POST'])
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
        return redirect(url_for('schedules.list_schedules'))

    @schedules_bp.route('/<int:schedule_id>/run', methods=['POST'])
    @login_required
    def run_schedule_now(schedule_id):
        """Run a schedule immediately"""
        schedule = Schedule.query.filter_by(id=schedule_id, user_id=current_user.id).first_or_404()
        
        if not schedule.script.file_exists:
            flash('Script file not found.', 'error')
            return redirect(url_for('schedules.list_schedules'))
        
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
        return redirect(url_for('logs.list_logs'))
    
    return schedules_bp