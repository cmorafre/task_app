"""
Dashboard Routes - Main dashboard and overview
"""

from flask import Blueprint, render_template
from flask_login import login_required, current_user
from sqlalchemy import func
from datetime import datetime, timedelta

from app.models.script import Script
from app.models.execution import Execution, ExecutionStatus
from app.models.schedule import Schedule
from app.services.script_executor import script_executor

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
def index():
    """Main dashboard page"""
    
    # Get user's scripts
    user_scripts = Script.query.filter_by(user_id=current_user.id, is_active=True).all()
    
    # Get recent executions (last 10)
    recent_executions = Execution.query.filter_by(user_id=current_user.id)\
        .order_by(Execution.started_at.desc())\
        .limit(10).all()
    
    # Get active schedules
    active_schedules = Schedule.query.join(Script)\
        .filter(Script.user_id == current_user.id, Schedule.is_active == True)\
        .order_by(Schedule.next_execution).all()
    
    # Calculate statistics
    stats = calculate_dashboard_stats(current_user.id)
    
    # Get currently running executions
    running_executions = get_running_executions(current_user.id)
    
    # Get system status
    system_status = {
        'total_running': len(script_executor.get_running_executions()),
        'max_concurrent': script_executor.max_concurrent,
        'next_scheduled': get_next_scheduled_execution()
    }
    
    return render_template('dashboard/index.html',
                         scripts=user_scripts,
                         recent_executions=recent_executions,
                         active_schedules=active_schedules,
                         stats=stats,
                         running_executions=running_executions,
                         system_status=system_status)

def calculate_dashboard_stats(user_id):
    """Calculate dashboard statistics for user"""
    
    # Time periods
    now = datetime.utcnow()
    last_24h = now - timedelta(days=1)
    last_7d = now - timedelta(days=7)
    last_30d = now - timedelta(days=30)
    
    # Basic counts
    total_scripts = Script.query.filter_by(user_id=user_id, is_active=True).count()
    active_schedules = Schedule.query.join(Script)\
        .filter(Script.user_id == user_id, Schedule.is_active == True).count()
    
    # Execution stats for last 24 hours
    executions_24h = Execution.query.filter(
        Execution.user_id == user_id,
        Execution.started_at >= last_24h
    ).count()
    
    successful_24h = Execution.query.filter(
        Execution.user_id == user_id,
        Execution.started_at >= last_24h,
        Execution.status == ExecutionStatus.COMPLETED,
        Execution.exit_code == 0
    ).count()
    
    failed_24h = Execution.query.filter(
        Execution.user_id == user_id,
        Execution.started_at >= last_24h,
        Execution.status.in_([ExecutionStatus.FAILED, ExecutionStatus.TIMEOUT])
    ).count()
    
    # Success rate
    success_rate_24h = round((successful_24h / executions_24h * 100) if executions_24h > 0 else 100, 1)
    
    return {
        'total_scripts': total_scripts,
        'active_schedules': active_schedules,
        'executions_24h': executions_24h,
        'successful_24h': successful_24h,
        'failed_24h': failed_24h,
        'success_rate_24h': success_rate_24h
    }

def get_running_executions(user_id):
    """Get currently running executions for user"""
    running_execution_ids = script_executor.get_running_executions()
    
    if not running_execution_ids:
        return []
    
    return Execution.query.filter(
        Execution.id.in_(running_execution_ids),
        Execution.user_id == user_id
    ).all()

def get_next_scheduled_execution():
    """Get the next scheduled execution across all users"""
    next_schedule = Schedule.query.filter(
        Schedule.is_active == True,
        Schedule.next_execution.isnot(None)
    ).order_by(Schedule.next_execution).first()
    
    return next_schedule.next_execution if next_schedule else None