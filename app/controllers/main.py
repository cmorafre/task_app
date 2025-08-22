"""
Main Blueprint
Handles main application routes: dashboard, settings, health, etc.
"""

import os
import socket
import subprocess
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta

# Create Blueprint
main_bp = Blueprint('main', __name__)

def init_main_blueprint(app, db, User, Script, Execution, Schedule, Settings, apply_user_data_filter):
    """Initialize main blueprint with dependencies"""
    
    @main_bp.route('/dashboard')
    @login_required
    def dashboard():
        # Get user's scripts (apply permission filter)
        scripts_query = Script.query.filter_by(is_active=True)
        user_scripts = apply_user_data_filter(scripts_query).all()
        
        # Get recent executions (apply permission filter)
        executions_query = Execution.query.order_by(Execution.started_at.desc())
        recent_executions = apply_user_data_filter(executions_query).limit(5).all()
        
        # Calculate stats for this user's data
        total_scripts = len(user_scripts)
        
        # 24h statistics
        since_24h = datetime.now() - timedelta(hours=24)
        executions_24h = apply_user_data_filter(
            Execution.query.filter(Execution.started_at >= since_24h)
        ).all()
        
        executions_24h_count = len(executions_24h)
        successful_24h = len([e for e in executions_24h if e.status == 'completed'])
        success_rate_24h = round((successful_24h / executions_24h_count * 100) if executions_24h_count > 0 else 0)
        
        # Running executions
        running_executions = apply_user_data_filter(
            Execution.query.filter(Execution.status.in_(['pending', 'running']))
        ).all()
        running_count = len(running_executions)
        
        stats = {
            'total_scripts': total_scripts,
            'executions_24h': executions_24h_count,
            'success_rate_24h': success_rate_24h,
            'running_count': running_count
        }
        
        return render_template('dashboard.html', 
                             stats=stats, 
                             scripts=user_scripts[:5],  # Show only first 5
                             recent_executions=recent_executions)

    @main_bp.route('/settings')
    @login_required
    def settings():
        """Application settings page"""
        # Get current settings
        python_executable = Settings.get_value('python_executable', app.config['PYTHON_EXECUTABLE'])
        python_env = Settings.get_value('python_env', app.config['PYTHON_ENV'])
        script_timeout = Settings.get_value('script_timeout', '300')
        max_concurrent = Settings.get_value('max_concurrent_scripts', '10')
        
        return render_template('settings.html',
                             python_executable=python_executable,
                             python_env=python_env,
                             script_timeout=script_timeout,
                             max_concurrent=max_concurrent)

    @main_bp.route('/settings/python', methods=['GET', 'POST'])
    @login_required
    def python_settings():
        """Python configuration settings"""
        if request.method == 'POST':
            python_executable = request.form.get('python_executable', '').strip()
            python_env = request.form.get('python_env', '').strip()
            
            if not python_executable:
                flash('Python executable path is required.', 'error')
                return redirect(request.url)
            
            try:
                # Test Python executable
                result = subprocess.run([python_executable, '--version'], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode != 0:
                    flash('Invalid Python executable path.', 'error')
                    return redirect(request.url)
                
                # Save settings
                Settings.set_value('python_executable', python_executable)
                Settings.set_value('python_env', python_env)
                
                flash('Python settings updated successfully!', 'success')
                return redirect(url_for('main.settings'))
                
            except Exception as e:
                flash(f'Error testing Python executable: {str(e)}', 'error')
                return redirect(request.url)
        
        # GET request
        python_executable = Settings.get_value('python_executable', app.config['PYTHON_EXECUTABLE'])
        python_env = Settings.get_value('python_env', app.config['PYTHON_ENV'])
        
        return render_template('python_settings.html',
                             python_executable=python_executable,
                             python_env=python_env)

    @main_bp.route('/settings/terminal')
    @login_required
    def terminal():
        """Web terminal interface"""
        return render_template('terminal.html')

    @main_bp.route('/api/terminal/execute', methods=['POST'])
    @login_required
    def terminal_execute():
        """Execute terminal command"""
        command = request.json.get('command', '').strip()
        
        if not command:
            return jsonify({'error': 'No command provided'}), 400
        
        # Security: limit allowed commands
        allowed_commands = ['ls', 'pwd', 'whoami', 'date', 'python', 'python3', 'pip', 'pip3']
        command_parts = command.split()
        if not command_parts or command_parts[0] not in allowed_commands:
            return jsonify({'error': 'Command not allowed'}), 403
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=os.getcwd()
            )
            
            return jsonify({
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            })
            
        except subprocess.TimeoutExpired:
            return jsonify({'error': 'Command timed out'}), 408
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @main_bp.route('/health')
    def health():
        """Health check endpoint"""
        return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

    @main_bp.route('/system/info')
    @login_required
    def system_info():
        """System information API"""
        try:
            import psutil
            
            # System info
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Database stats
            total_users = User.query.count()
            total_scripts = Script.query.filter_by(is_active=True).count()
            total_executions = Execution.query.count()
            total_schedules = Schedule.query.count()
            
            return jsonify({
                'system': {
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'memory_used_gb': round(memory.used / (1024**3), 2),
                    'memory_total_gb': round(memory.total / (1024**3), 2),
                    'disk_percent': (disk.used / disk.total) * 100,
                    'disk_used_gb': round(disk.used / (1024**3), 2),
                    'disk_total_gb': round(disk.total / (1024**3), 2)
                },
                'application': {
                    'total_users': total_users,
                    'total_scripts': total_scripts,
                    'total_executions': total_executions,
                    'total_schedules': total_schedules
                },
                'timestamp': datetime.now().isoformat()
            })
            
        except ImportError:
            # psutil not available
            return jsonify({
                'system': 'psutil not available',
                'application': {
                    'total_users': User.query.count(),
                    'total_scripts': Script.query.filter_by(is_active=True).count(),
                    'total_executions': Execution.query.count(),
                    'total_schedules': Schedule.query.count()
                }
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # Legacy preview routes (to be removed)
    @main_bp.route('/preview/modern-ui')
    @login_required
    def preview_modern_ui():
        return redirect(url_for('main.dashboard'))

    @main_bp.route('/preview/scripts')
    @login_required
    def preview_scripts():
        return redirect(url_for('scripts.list_scripts'))

    @main_bp.route('/preview/schedules')
    @login_required
    def preview_schedules():
        return redirect(url_for('schedules.list_schedules'))

    @main_bp.route('/preview/logs')
    @login_required
    def preview_logs():
        return redirect(url_for('logs.list_logs'))

    @main_bp.route('/preview/users')
    @login_required
    def preview_users():
        return redirect(url_for('admin.manage_users'))

    @main_bp.route('/preview/settings')
    @login_required
    def preview_settings():
        return redirect(url_for('main.settings'))

    @main_bp.route('/ui/toggle')
    @login_required
    def ui_toggle():
        """Legacy UI toggle - redirect to dashboard"""
        return redirect(url_for('main.dashboard'))

    @main_bp.route('/ui/test')
    @login_required
    def ui_test():
        """Legacy UI test - redirect to dashboard"""
        return redirect(url_for('main.dashboard'))
    
    return main_bp