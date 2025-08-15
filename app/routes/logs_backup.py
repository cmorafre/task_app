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
        )\n    \n    # Order by most recent first\n    query = query.order_by(Execution.started_at.desc())\n    \n    # Paginate results\n    executions = query.paginate(\n        page=page, \n        per_page=per_page, \n        error_out=False\n    )\n    \n    # Get user's scripts for filter dropdown\n    user_scripts = Script.query.filter_by(user_id=current_user.id, is_active=True)\\\n        .order_by(Script.name).all()\n    \n    return render_template('logs/index.html',\n                         executions=executions,\n                         user_scripts=user_scripts,\n                         filters={\n                             'script_id': script_id,\n                             'status': status,\n                             'trigger': trigger,\n                             'from_date': from_date,\n                             'to_date': to_date,\n                             'search': search\n                         })\n\n@logs_bp.route('/execution/<int:id>')\n@login_required\ndef view_execution(id):\n    \"\"\"View detailed execution log\"\"\"\n    \n    execution = Execution.query.filter_by(id=id, user_id=current_user.id).first_or_404()\n    \n    # Check if execution is currently running\n    is_running = execution.id in script_executor.get_running_executions()\n    \n    return render_template('logs/execution_detail.html',\n                         execution=execution,\n                         is_running=is_running)\n\n@logs_bp.route('/execution/<int:id>/cancel', methods=['POST'])\n@login_required\ndef cancel_execution(id):\n    \"\"\"Cancel a running execution\"\"\"\n    \n    execution = Execution.query.filter_by(id=id, user_id=current_user.id).first_or_404()\n    \n    if not execution.is_running:\n        return jsonify({'success': False, 'message': 'Execution is not running'}), 400\n    \n    try:\n        success = script_executor.cancel_execution(execution.id)\n        \n        if success:\n            return jsonify({'success': True, 'message': 'Execution cancelled successfully'})\n        else:\n            return jsonify({'success': False, 'message': 'Failed to cancel execution'}), 500\n            \n    except Exception as e:\n        return jsonify({'success': False, 'message': str(e)}), 500\n\n@logs_bp.route('/execution/<int:id>/output')\n@login_required\ndef get_execution_output(id):\n    \"\"\"Get execution output (for AJAX updates)\"\"\"\n    \n    execution = Execution.query.filter_by(id=id, user_id=current_user.id).first_or_404()\n    \n    return jsonify({\n        'status': execution.status.value,\n        'stdout': execution.stdout or '',\n        'stderr': execution.stderr or '',\n        'exit_code': execution.exit_code,\n        'duration': execution.formatted_duration,\n        'is_finished': execution.is_finished,\n        'is_running': execution.id in script_executor.get_running_executions()\n    })\n\n@logs_bp.route('/stats')\n@login_required\ndef stats():\n    \"\"\"Execution statistics page\"\"\"\n    \n    # Calculate various statistics\n    now = datetime.utcnow()\n    periods = {\n        'last_24h': now - timedelta(days=1),\n        'last_7d': now - timedelta(days=7),\n        'last_30d': now - timedelta(days=30)\n    }\n    \n    stats = {}\n    \n    for period_name, start_date in periods.items():\n        period_executions = Execution.query.filter(\n            Execution.user_id == current_user.id,\n            Execution.started_at >= start_date\n        )\n        \n        total = period_executions.count()\n        successful = period_executions.filter(\n            Execution.status == ExecutionStatus.COMPLETED,\n            Execution.exit_code == 0\n        ).count()\n        \n        failed = period_executions.filter(\n            Execution.status.in_([\n                ExecutionStatus.FAILED,\n                ExecutionStatus.TIMEOUT,\n                ExecutionStatus.CANCELLED\n            ])\n        ).count()\n        \n        success_rate = round((successful / total * 100) if total > 0 else 100, 1)\n        \n        stats[period_name] = {\n            'total': total,\n            'successful': successful,\n            'failed': failed,\n            'success_rate': success_rate\n        }\n    \n    # Get execution trends by script\n    script_stats = []\n    user_scripts = Script.query.filter_by(user_id=current_user.id, is_active=True).all()\n    \n    for script in user_scripts:\n        script_executions = Execution.query.filter(\n            Execution.script_id == script.id,\n            Execution.started_at >= periods['last_30d']\n        )\n        \n        total = script_executions.count()\n        successful = script_executions.filter(\n            Execution.status == ExecutionStatus.COMPLETED,\n            Execution.exit_code == 0\n        ).count()\n        \n        if total > 0:\n            script_stats.append({\n                'script': script,\n                'total_executions': total,\n                'success_rate': round((successful / total * 100), 1),\n                'avg_duration': calculate_avg_duration(script.id, periods['last_30d'])\n            })\n    \n    return render_template('logs/stats.html',\n                         stats=stats,\n                         script_stats=script_stats)\n\ndef calculate_avg_duration(script_id, since_date):\n    \"\"\"Calculate average execution duration for a script\"\"\"\n    \n    from sqlalchemy import func\n    \n    result = db.session.query(func.avg(Execution.duration_seconds)).filter(\n        Execution.script_id == script_id,\n        Execution.started_at >= since_date,\n        Execution.duration_seconds.isnot(None)\n    ).scalar()\n    \n    if result:\n        # Convert to human readable format\n        avg_seconds = float(result)\n        if avg_seconds < 60:\n            return f\"{avg_seconds:.1f}s\"\n        elif avg_seconds < 3600:\n            return f\"{avg_seconds/60:.1f}m\"\n        else:\n            return f\"{avg_seconds/3600:.1f}h\"\n    \n    return \"N/A\""