"""
Logs Blueprint
Handles execution logs viewing and API endpoints
"""

from datetime import datetime
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user

# Create Blueprint
logs_bp = Blueprint('logs', __name__, url_prefix='/logs')

def init_logs_blueprint(db, Execution, apply_user_data_filter):
    """Initialize logs blueprint with dependencies"""
    
    @logs_bp.route('/')
    @login_required
    def list_logs():
        page = request.args.get('page', 1, type=int)
        executions_query = Execution.query.order_by(Execution.started_at.desc())
        executions_filtered = apply_user_data_filter(executions_query)
        executions = executions_filtered.paginate(page=page, per_page=20, error_out=False)
        
        return render_template('logs.html', executions=executions)

    @logs_bp.route('/<int:execution_id>')
    @login_required
    def view_execution(execution_id):
        execution_query = Execution.query.filter_by(id=execution_id)
        execution = apply_user_data_filter(execution_query).first_or_404()
        return render_template('execution_detail.html', execution=execution)

    return logs_bp


def init_api_blueprint(db, Execution, apply_user_data_filter):
    """Initialize API blueprint for logs-related endpoints"""
    api_bp = Blueprint('api', __name__, url_prefix='/api')

    @api_bp.route('/logs')
    @login_required
    def logs_api():
        """API endpoint to get execution logs for AJAX refresh"""
        page = request.args.get('page', 1, type=int)
        executions_query = Execution.query.order_by(Execution.started_at.desc())
        executions_filtered = apply_user_data_filter(executions_query)
        executions = executions_filtered.paginate(page=page, per_page=20, error_out=False)
        
        # Convert executions to JSON format
        executions_data = []
        for execution in executions.items:
            executions_data.append({
                'id': execution.id,
                'script_name': execution.script.name if execution.script else 'Unknown',
                'status': execution.status,
                'started_at': execution.started_at.strftime('%Y-%m-%d %H:%M:%S') if execution.started_at else None,
                'duration': execution.formatted_duration,
                'exit_code': execution.exit_code,
                'status_icon': execution.status_icon,
                'status_color': execution.status_color
            })
        
        return jsonify({
            'executions': executions_data,
            'has_running': any(ex.status in ['pending', 'running'] for ex in executions.items),
            'pagination': {
                'page': executions.page,
                'pages': executions.pages,
                'per_page': executions.per_page,
                'total': executions.total,
                'has_prev': executions.has_prev,
                'has_next': executions.has_next,
                'prev_num': executions.prev_num,
                'next_num': executions.next_num
            }
        })

    @api_bp.route('/execution/<int:execution_id>/status')
    @login_required
    def execution_status_api(execution_id):
        """API endpoint to get execution status without full page reload"""
        execution = Execution.query.filter_by(id=execution_id, user_id=current_user.id).first_or_404()
        
        return jsonify({
            'id': execution.id,
            'status': execution.status,
            'started_at': execution.started_at.strftime('%Y-%m-%d %H:%M:%S') if execution.started_at else None,
            'completed_at': execution.completed_at.strftime('%Y-%m-%d %H:%M:%S') if execution.completed_at else None,
            'duration': execution.formatted_duration,
            'exit_code': execution.exit_code,
            'stdout': execution.stdout,
            'stderr': execution.stderr,
            'is_running': execution.status in ['pending', 'running']
        })

    @api_bp.route('/execution/<int:execution_id>/stop', methods=['POST'])
    @login_required
    def stop_execution_api(execution_id):
        """API endpoint to stop/cancel a running execution"""
        execution = Execution.query.filter_by(id=execution_id, user_id=current_user.id).first_or_404()
        
        if execution.status not in ['pending', 'running']:
            return jsonify({
                'success': False,
                'message': f'Cannot stop execution with status: {execution.status}'
            }), 400
        
        # Update execution status to cancelled
        execution.status = 'cancelled'
        execution.completed_at = datetime.now()
        execution.stderr = (execution.stderr or '') + '\n[CANCELLED] Execution was stopped by user'
        execution.duration_seconds = (execution.completed_at - execution.started_at).total_seconds() if execution.started_at else 0
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Execution stopped successfully',
            'status': execution.status
        })

    return api_bp