"""
Logs Routes - Execution history and log viewing
"""

from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import and_, or_

from app.models.execution import Execution, ExecutionStatus, ExecutionTrigger
from app.models.script import Script
from app.services.script_executor import script_executor
from app.models import db

logs_bp = Blueprint('logs', __name__)

@logs_bp.route('/')
@login_required
def index():
    """Execution logs list page"""
    
    # Get filters from query parameters
    script_id = request.args.get('script_id', type=int)
    status = request.args.get('status', '')
    trigger = request.args.get('trigger', '')
    from_date = request.args.get('from_date', '')
    to_date = request.args.get('to_date', '')
    search = request.args.get('search', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    # Build base query
    query = Execution.query.filter_by(user_id=current_user.id)
    
    # Apply filters
    if script_id:
        query = query.filter_by(script_id=script_id)
    
    if status and status in [s.value for s in ExecutionStatus]:
        query = query.filter_by(status=ExecutionStatus(status))
    
    if trigger and trigger in [t.value for t in ExecutionTrigger]:
        query = query.filter_by(trigger_type=ExecutionTrigger(trigger))
    
    # Date range filters
    if from_date:
        try:
            from_dt = datetime.strptime(from_date, '%Y-%m-%d')
            query = query.filter(Execution.started_at >= from_dt)
        except ValueError:
            pass
    
    if to_date:
        try:
            to_dt = datetime.strptime(to_date, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(Execution.started_at < to_dt)
        except ValueError:
            pass
    
    # Search in output
    if search:
        query = query.filter(
            or_(
                Execution.stdout.contains(search),
                Execution.stderr.contains(search)
            )
        )
    
    # Order by most recent first
    query = query.order_by(Execution.started_at.desc())
    
    # Paginate results
    executions = query.paginate(
        page=page, 
        per_page=per_page, 
        error_out=False
    )
    
    # Get user's scripts for filter dropdown
    user_scripts = Script.query.filter_by(user_id=current_user.id, is_active=True)\
        .order_by(Script.name).all()
    
    return render_template('logs/index.html',
                         executions=executions,
                         user_scripts=user_scripts,
                         filters={
                             'script_id': script_id,
                             'status': status,
                             'trigger': trigger,
                             'from_date': from_date,
                             'to_date': to_date,
                             'search': search
                         })

@logs_bp.route('/execution/<int:id>')
@login_required
def view_execution(id):
    """View detailed execution log"""
    
    execution = Execution.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    
    # Check if execution is currently running
    is_running = execution.id in script_executor.get_running_executions()
    
    return render_template('logs/execution_detail.html',
                         execution=execution,
                         is_running=is_running)

@logs_bp.route('/execution/<int:id>/cancel', methods=['POST'])
@login_required
def cancel_execution(id):
    """Cancel a running execution"""
    
    execution = Execution.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    
    if not execution.is_running:
        return jsonify({'success': False, 'message': 'Execution is not running'}), 400
    
    try:
        success = script_executor.cancel_execution(execution.id)
        
        if success:
            return jsonify({'success': True, 'message': 'Execution cancelled successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to cancel execution'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@logs_bp.route('/execution/<int:id>/output')
@login_required
def get_execution_output(id):
    """Get execution output (for AJAX updates)"""
    
    execution = Execution.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    
    return jsonify({
        'status': execution.status.value,
        'stdout': execution.stdout or '',
        'stderr': execution.stderr or '',
        'exit_code': execution.exit_code,
        'duration': execution.formatted_duration,
        'is_finished': execution.is_finished,
        'is_running': execution.id in script_executor.get_running_executions()
    })

@logs_bp.route('/stats')
@login_required
def stats():
    """Execution statistics page"""
    
    # Calculate various statistics
    now = datetime.utcnow()
    periods = {
        'last_24h': now - timedelta(days=1),
        'last_7d': now - timedelta(days=7),
        'last_30d': now - timedelta(days=30)
    }
    
    stats = {}
    
    for period_name, start_date in periods.items():
        period_executions = Execution.query.filter(
            Execution.user_id == current_user.id,
            Execution.started_at >= start_date
        )
        
        total = period_executions.count()
        successful = period_executions.filter(
            Execution.status == ExecutionStatus.COMPLETED,
            Execution.exit_code == 0
        ).count()
        
        failed = period_executions.filter(
            Execution.status.in_([
                ExecutionStatus.FAILED,
                ExecutionStatus.TIMEOUT,
                ExecutionStatus.CANCELLED
            ])
        ).count()
        
        success_rate = round((successful / total * 100) if total > 0 else 100, 1)
        
        stats[period_name] = {
            'total': total,
            'successful': successful,
            'failed': failed,
            'success_rate': success_rate
        }
    
    # Get execution trends by script
    script_stats = []
    user_scripts = Script.query.filter_by(user_id=current_user.id, is_active=True).all()
    
    for script in user_scripts:
        script_executions = Execution.query.filter(
            Execution.script_id == script.id,
            Execution.started_at >= periods['last_30d']
        )
        
        total = script_executions.count()
        successful = script_executions.filter(
            Execution.status == ExecutionStatus.COMPLETED,
            Execution.exit_code == 0
        ).count()
        
        if total > 0:
            script_stats.append({
                'script': script,
                'total_executions': total,
                'success_rate': round((successful / total * 100), 1),
                'avg_duration': calculate_avg_duration(script.id, periods['last_30d'])
            })
    
    return render_template('logs/stats.html',
                         stats=stats,
                         script_stats=script_stats)

def calculate_avg_duration(script_id, since_date):
    """Calculate average execution duration for a script"""
    
    from sqlalchemy import func
    
    result = db.session.query(func.avg(Execution.duration_seconds)).filter(
        Execution.script_id == script_id,
        Execution.started_at >= since_date,
        Execution.duration_seconds.isnot(None)
    ).scalar()
    
    if result:
        # Convert to human readable format
        avg_seconds = float(result)
        if avg_seconds < 60:
            return f"{avg_seconds:.1f}s"
        elif avg_seconds < 3600:
            return f"{avg_seconds/60:.1f}m"
        else:
            return f"{avg_seconds/3600:.1f}h"
    
    return "N/A"