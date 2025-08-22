"""
ETL Executor Service - Orchestrates Extract-Transform-Load operations for Integration feature
"""

import logging
import threading
import time
import json
import tempfile
import os
import subprocess
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
from contextlib import contextmanager

from app.models import db
from app.models.integration import Integration
from app.models.integration_execution import IntegrationExecution, IntegrationExecutionStatus, IntegrationExecutionTrigger
from app.models.script import Script
from app.models.datasource import DataSource
from app.services.connection_manager import connection_manager
from app.services.script_executor import script_executor

# Set up logging
logger = logging.getLogger(__name__)

class ETLExecutor:
    """Service for executing Integration ETL jobs with full orchestration"""
    
    def __init__(self):
        self.running_executions = {}  # execution_id -> thread mapping
        self.max_concurrent = int(os.environ.get('MAX_CONCURRENT_INTEGRATIONS', 5))
        self.default_timeout = int(os.environ.get('INTEGRATION_TIMEOUT', 600))  # 10 minutes
        
    def execute_integration(self, integration_id: int, user_id: int, 
                           trigger_type=IntegrationExecutionTrigger.MANUAL, 
                           schedule_id: Optional[int] = None) -> IntegrationExecution:
        """
        Execute an Integration ETL job asynchronously
        
        Args:
            integration_id: Integration ID to execute
            user_id: User executing the integration
            trigger_type: How execution was triggered
            schedule_id: Schedule ID if triggered by scheduler
            
        Returns:
            IntegrationExecution: Created execution record
        """
        # Check concurrent execution limit
        if len(self.running_executions) >= self.max_concurrent:
            raise Exception(f"Maximum concurrent integrations ({self.max_concurrent}) reached")
        
        # Get integration
        integration = Integration.query.get(integration_id)
        if not integration:
            raise Exception(f"Integration {integration_id} not found")
        
        if not integration.is_active:
            raise Exception(f"Integration '{integration.name}' is not active")
        
        # Validate integration configuration
        validation_errors = integration.validate_sql_queries()
        if validation_errors:
            raise Exception(f"Integration validation failed: {'; '.join(validation_errors)}")
        
        # Create execution record
        execution = IntegrationExecution(
            integration_id=integration_id,
            user_id=user_id,
            trigger_type=trigger_type,
            schedule_id=schedule_id
        )
        
        db.session.add(execution)
        db.session.commit()
        
        logger.info(f"Created IntegrationExecution {execution.id} for Integration '{integration.name}'")
        
        # Start execution in background thread
        thread = threading.Thread(
            target=self._execute_integration_thread,
            args=(execution.id,),
            name=f"IntegrationExecution-{execution.id}"
        )
        thread.daemon = True
        thread.start()
        
        # Track running execution
        self.running_executions[execution.id] = thread
        
        return execution
    
    def _execute_integration_thread(self, execution_id: int):
        """Execute integration in background thread with full ETL orchestration"""
        
        execution = IntegrationExecution.query.get(execution_id)
        if not execution:
            logger.error(f"IntegrationExecution {execution_id} not found")
            return
        
        integration = execution.integration
        if not integration:
            logger.error(f"Integration not found for execution {execution_id}")
            execution.fail_execution("Integration not found")
            return
        
        logger.info(f"Starting ETL execution for Integration '{integration.name}' (ID: {execution_id})")
        
        try:
            # Mark execution as started
            execution.start_execution()
            execution.add_log("ETL execution started", "INFO")
            
            # Execute ETL phases
            extracted_data = self._execute_extract_phase(execution, integration)
            transformed_data = self._execute_transform_phase(execution, integration, extracted_data)
            loaded_records = self._execute_load_phase(execution, integration, transformed_data)
            
            # Complete execution successfully
            execution.complete_execution(
                records_extracted=len(extracted_data) if extracted_data else 0,
                records_loaded=loaded_records,
                records_failed=max(0, (len(extracted_data) if extracted_data else 0) - loaded_records),
                logs=execution.logs + f"\n[{datetime.utcnow()}] INFO: ETL execution completed successfully"
            )
            
            logger.info(f"ETL execution {execution_id} completed successfully: {len(extracted_data) if extracted_data else 0} extracted, {loaded_records} loaded")
            
        except Exception as e:
            # Execution failed
            error_msg = str(e)
            logger.error(f"ETL execution {execution_id} failed: {error_msg}")
            execution.fail_execution(error_msg)
            
        finally:
            # Clean up tracking
            if execution_id in self.running_executions:
                del self.running_executions[execution_id]
    
    def _execute_extract_phase(self, execution: IntegrationExecution, integration: Integration) -> list:
        """Execute Extract phase - pull data from source database"""
        
        execution.add_log("Starting Extract phase", "INFO")
        logger.info(f"Extract phase starting for execution {execution.id}")
        
        try:
            # Validate extract query
            is_valid, errors = connection_manager.validate_query(integration.extract_sql, 'extract')
            if not is_valid:
                raise Exception(f"Extract query validation failed: {'; '.join(errors)}")
            
            # Test source connection
            success, message = connection_manager.test_connection(integration.source_id)
            if not success:
                raise Exception(f"Source database connection failed: {message}")
            
            # Execute extract query
            start_time = time.time()
            results, row_count = connection_manager.execute_query(
                integration.source_id, 
                integration.extract_sql
            )
            
            execution_time = time.time() - start_time
            
            # Log results
            log_msg = f"Extract completed: {row_count} records in {execution_time:.2f}s"
            execution.add_log(log_msg, "INFO")
            logger.info(f"Extract phase completed for execution {execution.id}: {row_count} records")
            
            # Store extract output summary
            extract_summary = {
                'records_count': row_count,
                'execution_time': execution_time,
                'query': integration.extract_sql[:200] + '...' if len(integration.extract_sql) > 200 else integration.extract_sql
            }
            execution.extract_output = json.dumps(extract_summary)
            db.session.commit()
            
            return results
            
        except Exception as e:
            error_msg = f"Extract phase failed: {str(e)}"
            execution.add_log(error_msg, "ERROR")
            logger.error(f"Extract phase failed for execution {execution.id}: {e}")
            raise Exception(error_msg)
    
    def _execute_transform_phase(self, execution: IntegrationExecution, integration: Integration, data: list) -> list:
        """Execute Transform phase - process data with Python script (if configured)"""
        
        if not integration.has_python_transformation:
            execution.add_log("Transform phase skipped (no Python script configured)", "INFO")
            logger.info(f"Transform phase skipped for execution {execution.id} - no script configured")
            return data
        
        execution.add_log("Starting Transform phase", "INFO")
        logger.info(f"Transform phase starting for execution {execution.id}")
        
        try:
            python_script = integration.python_script
            if not python_script or not python_script.file_exists:
                raise Exception("Python transformation script not found or file missing")
            
            if not python_script.is_active:
                raise Exception("Python transformation script is not active")
            
            # Create temporary files for data exchange
            with tempfile.TemporaryDirectory() as temp_dir:
                # Write input data to JSON file
                input_file = os.path.join(temp_dir, 'input_data.json')
                output_file = os.path.join(temp_dir, 'output_data.json')
                
                with open(input_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, default=str, indent=2)
                
                # Execute Python script with data files
                start_time = time.time()
                success, result_data = self._execute_python_transformation(
                    python_script.file_path,
                    input_file,
                    output_file,
                    temp_dir
                )
                
                execution_time = time.time() - start_time
                
                if not success:
                    raise Exception(f"Python transformation failed: {result_data}")
                
                # Read transformed data
                if os.path.exists(output_file):
                    with open(output_file, 'r', encoding='utf-8') as f:
                        transformed_data = json.load(f)
                else:
                    # If no output file, assume data passed through unchanged
                    transformed_data = data
                
                # Log results
                log_msg = f"Transform completed: {len(transformed_data)} records in {execution_time:.2f}s"
                execution.add_log(log_msg, "INFO")
                logger.info(f"Transform phase completed for execution {execution.id}: {len(transformed_data)} records")
                
                # Store transform output summary
                transform_summary = {
                    'input_records': len(data),
                    'output_records': len(transformed_data),
                    'execution_time': execution_time,
                    'script_name': python_script.name,
                    'stdout': result_data.get('stdout', '')[:500]  # First 500 chars
                }
                execution.transform_output = json.dumps(transform_summary)
                db.session.commit()
                
                return transformed_data
                
        except Exception as e:
            error_msg = f"Transform phase failed: {str(e)}"
            execution.add_log(error_msg, "ERROR")
            logger.error(f"Transform phase failed for execution {execution.id}: {e}")
            raise Exception(error_msg)
    
    def _execute_python_transformation(self, script_path: str, input_file: str, 
                                     output_file: str, work_dir: str) -> Tuple[bool, Dict[str, Any]]:
        """Execute Python transformation script with data files"""
        
        try:
            # Prepare environment
            env = os.environ.copy()
            env['SCRIPTFLOW_INPUT_FILE'] = input_file
            env['SCRIPTFLOW_OUTPUT_FILE'] = output_file
            env['SCRIPTFLOW_WORK_DIR'] = work_dir
            
            # Get Python executable
            python_executable = os.environ.get('PYTHON_EXECUTABLE', 'python3')
            
            # Execute script
            result = subprocess.run(
                [python_executable, script_path],
                cwd=work_dir,
                env=env,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout for transformation
            )
            
            return result.returncode == 0, {
                'exit_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
            
        except subprocess.TimeoutExpired:
            return False, {
                'exit_code': -1,
                'stdout': '',
                'stderr': 'Python transformation script timed out (5 minutes)'
            }
        except Exception as e:
            return False, {
                'exit_code': -1,
                'stdout': '',
                'stderr': str(e)
            }
    
    def _execute_load_phase(self, execution: IntegrationExecution, integration: Integration, data: list) -> int:
        """Execute Load phase - insert data into target database"""
        
        execution.add_log("Starting Load phase", "INFO")
        logger.info(f"Load phase starting for execution {execution.id}")
        
        try:
            # Validate load query
            is_valid, errors = connection_manager.validate_query(integration.load_sql, 'load')
            if not is_valid:
                raise Exception(f"Load query validation failed: {'; '.join(errors)}")
            
            # Test target connection
            success, message = connection_manager.test_connection(integration.target_id)
            if not success:
                raise Exception(f"Target database connection failed: {message}")
            
            if not data:
                execution.add_log("Load phase: No data to load", "WARNING")
                return 0
            
            # Execute load operations
            start_time = time.time()
            loaded_count = 0
            failed_count = 0
            
            # Process data in batches (for large datasets)
            batch_size = 100
            total_batches = (len(data) + batch_size - 1) // batch_size
            
            for batch_num in range(total_batches):
                start_idx = batch_num * batch_size
                end_idx = min(start_idx + batch_size, len(data))
                batch_data = data[start_idx:end_idx]
                
                try:
                    batch_loaded = self._load_data_batch(integration, batch_data)
                    loaded_count += batch_loaded
                    
                    # Log progress for large datasets
                    if total_batches > 1:
                        execution.add_log(f"Load progress: Batch {batch_num + 1}/{total_batches} - {batch_loaded} records", "INFO")
                        
                except Exception as e:
                    failed_count += len(batch_data)
                    logger.warning(f"Load batch {batch_num + 1} failed: {e}")
                    execution.add_log(f"Load batch {batch_num + 1} failed: {str(e)}", "WARNING")
            
            execution_time = time.time() - start_time
            
            # Log final results
            log_msg = f"Load completed: {loaded_count} records loaded, {failed_count} failed in {execution_time:.2f}s"
            execution.add_log(log_msg, "INFO")
            logger.info(f"Load phase completed for execution {execution.id}: {loaded_count} loaded, {failed_count} failed")
            
            # Store load output summary
            load_summary = {
                'records_loaded': loaded_count,
                'records_failed': failed_count,
                'execution_time': execution_time,
                'batch_count': total_batches,
                'query': integration.load_sql[:200] + '...' if len(integration.load_sql) > 200 else integration.load_sql
            }
            execution.load_output = json.dumps(load_summary)
            db.session.commit()
            
            return loaded_count
            
        except Exception as e:
            error_msg = f"Load phase failed: {str(e)}"
            execution.add_log(error_msg, "ERROR")
            logger.error(f"Load phase failed for execution {execution.id}: {e}")
            raise Exception(error_msg)
    
    def _load_data_batch(self, integration: Integration, batch_data: list) -> int:
        """Load a batch of data into target database"""
        
        if not batch_data:
            return 0
        
        # For now, execute load query for each record
        # TODO: Implement bulk insert optimization
        loaded_count = 0
        
        for record in batch_data:
            try:
                # Execute load query with record data as parameters
                _, affected_rows = connection_manager.execute_query(
                    integration.target_id,
                    integration.load_sql,
                    record
                )
                
                loaded_count += affected_rows
                
            except Exception as e:
                logger.warning(f"Failed to load record: {e}")
                # Continue with other records
                continue
        
        return loaded_count
    
    def cancel_execution(self, execution_id: int) -> bool:
        """Cancel a running integration execution"""
        
        execution = IntegrationExecution.query.get(execution_id)
        if not execution or not execution.is_running:
            return False
        
        # Cancel the execution
        execution.cancel_execution()
        
        # Clean up tracking
        if execution_id in self.running_executions:
            del self.running_executions[execution_id]
        
        logger.info(f"Integration execution {execution_id} cancelled")
        return True
    
    def get_running_executions(self) -> list:
        """Get list of currently running integration executions"""
        return list(self.running_executions.keys())
    
    def get_execution_status(self, execution_id: int) -> Dict[str, Any]:
        """Get detailed status of an integration execution"""
        
        execution = IntegrationExecution.query.get(execution_id)
        if not execution:
            return {'error': 'Execution not found'}
        
        return {
            'id': execution.id,
            'integration_name': execution.integration.name if execution.integration else 'Unknown',
            'status': execution.status,
            'started_at': execution.started_at.isoformat() if execution.started_at else None,
            'completed_at': execution.completed_at.isoformat() if execution.completed_at else None,
            'duration': execution.formatted_duration,
            'records_extracted': execution.records_extracted,
            'records_loaded': execution.records_loaded,
            'records_failed': execution.records_failed,
            'efficiency_rate': execution.efficiency_rate,
            'error_message': execution.error_message,
            'is_running': execution.is_running,
            'phase_summary': execution.get_phase_summary()
        }

# Global ETL executor instance
etl_executor = ETLExecutor()