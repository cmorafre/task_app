"""
Script Executor Service - Handles safe execution of uploaded scripts
"""

import os
import subprocess
import tempfile
import threading
import time
from datetime import datetime
from flask import current_app

from app.models.execution import Execution, ExecutionStatus, ExecutionTrigger
from app.models.script import Script
from app.models import db

class ScriptExecutor:
    """Service for executing scripts safely with isolation and monitoring"""
    
    def __init__(self):
        self.running_processes = {}  # pid -> execution_id mapping
        self.max_concurrent = int(os.environ.get('MAX_CONCURRENT_SCRIPTS', 10))
        self.default_timeout = int(os.environ.get('SCRIPT_TIMEOUT', 300))  # 5 minutes
    
    def execute_script(self, script_id, user_id, trigger_type=ExecutionTrigger.MANUAL, schedule_id=None):
        """
        Execute a script asynchronously and return execution record
        
        Args:
            script_id: ID of script to execute
            user_id: ID of user executing the script
            trigger_type: How the execution was triggered
            schedule_id: Schedule ID if triggered by scheduler
            
        Returns:
            Execution: Created execution record
        """
        # Check concurrent execution limit
        if len(self.running_processes) >= self.max_concurrent:
            raise Exception(f"Maximum concurrent executions ({self.max_concurrent}) reached")
        
        # Get script
        script = Script.query.get(script_id)
        if not script:
            raise Exception(f"Script {script_id} not found")
        
        if not script.file_exists:
            raise Exception(f"Script file {script.filename} not found on disk")
        
        # Create execution record
        execution = Execution(
            script_id=script_id,
            user_id=user_id,
            trigger_type=trigger_type,
            schedule_id=schedule_id
        )
        
        db.session.add(execution)
        db.session.commit()
        
        # Start execution in background thread
        thread = threading.Thread(
            target=self._execute_script_thread,
            args=(execution.id, script.file_path, script.script_type)
        )
        thread.daemon = True
        thread.start()
        
        return execution
    
    def _execute_script_thread(self, execution_id, script_path, script_type):
        """Execute script in background thread with proper isolation"""
        
        execution = Execution.query.get(execution_id)
        if not execution:
            return
        
        try:
            # Create isolated working directory
            with tempfile.TemporaryDirectory() as temp_dir:
                # Prepare execution environment
                env = os.environ.copy()
                env['SCRIPTFLOW_EXECUTION_ID'] = str(execution_id)
                env['SCRIPTFLOW_WORKING_DIR'] = temp_dir
                
                # Build command based on script type
                if script_type == 'py':
                    python_executable = os.environ.get('PYTHON_EXECUTABLE', 'python3')
                    cmd = [python_executable, script_path]
                elif script_type == 'bat':
                    if os.name == 'nt':  # Windows
                        cmd = ['cmd', '/c', script_path]
                    else:  # Unix-like (with wine or direct execution)
                        cmd = ['bash', script_path]  # Treat as bash script on Unix
                else:
                    raise Exception(f"Unsupported script type: {script_type}")
                
                # Start process
                process = subprocess.Popen(
                    cmd,
                    cwd=temp_dir,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )
                
                # Update execution record with PID
                execution.start_execution(pid=process.pid)
                self.running_processes[process.pid] = execution_id
                
                try:
                    # Wait for completion with timeout
                    stdout, stderr = process.communicate(timeout=self.default_timeout)
                    
                    # Process completed normally
                    execution.complete_execution(
                        exit_code=process.returncode,
                        stdout=stdout,
                        stderr=stderr
                    )
                    
                except subprocess.TimeoutExpired:
                    # Process timed out
                    process.kill()
                    stdout, stderr = process.communicate()
                    
                    execution.timeout_execution()
                    execution.stdout = stdout
                    execution.stderr = stderr + f"\n\n[TIMEOUT] Process killed after {self.default_timeout} seconds"
                    db.session.commit()
                
                finally:
                    # Clean up process tracking
                    if process.pid in self.running_processes:
                        del self.running_processes[process.pid]
        
        except Exception as e:
            # Execution failed to start or crashed
            execution.status = ExecutionStatus.FAILED
            execution.completed_at = datetime.utcnow()
            execution.stderr = str(e)
            execution.exit_code = -1
            
            if execution.started_at:
                execution.duration_seconds = (execution.completed_at - execution.started_at).total_seconds()
            
            db.session.commit()
            
            # Clean up if process was registered
            for pid, exec_id in list(self.running_processes.items()):
                if exec_id == execution_id:
                    del self.running_processes[pid]
                    break
    
    def cancel_execution(self, execution_id):
        """
        Cancel a running execution
        
        Args:
            execution_id: ID of execution to cancel
            
        Returns:
            bool: True if cancelled, False if not running or not found
        """
        execution = Execution.query.get(execution_id)
        if not execution or not execution.is_running:
            return False
        
        # Find and kill process
        for pid, exec_id in list(self.running_processes.items()):
            if exec_id == execution_id:
                try:
                    # Kill process
                    if os.name == 'nt':  # Windows
                        subprocess.run(['taskkill', '/F', '/PID', str(pid)], check=False)
                    else:  # Unix-like
                        os.kill(pid, 9)  # SIGKILL
                    
                    # Update execution record
                    execution.cancel_execution()
                    
                    # Clean up tracking
                    del self.running_processes[pid]
                    return True
                
                except (OSError, ProcessLookupError):
                    # Process already dead
                    execution.cancel_execution()
                    del self.running_processes[pid]
                    return True
        
        return False
    
    def get_running_executions(self):
        """
        Get list of currently running executions
        
        Returns:
            list: List of execution IDs currently running
        """
        return list(self.running_processes.values())
    
    def cleanup_stale_processes(self):
        """Clean up any stale process tracking (for system restart recovery)"""
        for pid in list(self.running_processes.keys()):
            try:
                # Check if process still exists
                os.kill(pid, 0)  # Signal 0 just checks existence
            except (OSError, ProcessLookupError):
                # Process is dead, clean up
                execution_id = self.running_processes[pid]
                execution = Execution.query.get(execution_id)
                
                if execution and execution.is_running:
                    # Mark as failed due to system restart
                    execution.status = ExecutionStatus.FAILED
                    execution.completed_at = datetime.utcnow()
                    execution.stderr = "Execution interrupted by system restart"
                    execution.exit_code = -3
                    
                    if execution.started_at:
                        execution.duration_seconds = (execution.completed_at - execution.started_at).total_seconds()
                    
                    db.session.commit()
                
                del self.running_processes[pid]

# Global executor instance
script_executor = ScriptExecutor()