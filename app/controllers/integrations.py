"""
Integration Blueprint
Handles all integration-related operations: list, create, execute, edit, delete
Follows the same pattern as existing ScriptFlow controllers
"""

import os
import json
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func, desc

# Create Blueprint
integrations_bp = Blueprint('integrations', __name__, url_prefix='/integrations')

def init_integrations_blueprint(app, db, Integration, IntegrationExecution, DataSource, Script, Schedule, apply_user_data_filter):
    """Initialize integrations blueprint with dependencies - SAME PATTERN as existing controllers"""
    
    @integrations_bp.route('/')
    @login_required
    def list_integrations():
        """List all integrations - FOLLOWS scripts.list_scripts pattern"""
        
        # Get filters from query parameters
        search = request.args.get('search', '').strip()
        status_filter = request.args.get('status', '')
        source_filter = request.args.get('source', '')
        sort_by = request.args.get('sort', 'updated')
        
        # Build query with user permission filter
        integrations_query = Integration.query.filter_by(is_active=True)
        query = apply_user_data_filter(integrations_query)
        
        # Search filter
        if search:
            query = query.filter(Integration.name.contains(search))
        
        # Status filter (based on last execution)
        if status_filter:
            # This will be implemented with subqueries if needed
            pass
        
        # Source filter
        if source_filter:
            query = query.filter_by(source_id=source_filter)
        
        # Sorting
        if sort_by == 'name':
            query = query.order_by(Integration.name)
        elif sort_by == 'created':
            query = query.order_by(desc(Integration.created_at))
        else:  # default to updated
            query = query.order_by(desc(Integration.updated_at))
        
        integrations = query.all()
        
        # Get data sources for filter dropdown
        datasources_query = DataSource.query.filter_by(is_active=True)
        datasources = apply_user_data_filter(datasources_query).all()
        
        # Get statistics
        total_integrations = len(integrations)
        active_integrations = sum(1 for i in integrations if i.is_active)
        
        # Get recent executions count
        recent_executions = IntegrationExecution.query.filter(
            IntegrationExecution.started_at >= datetime.utcnow() - timedelta(days=7)
        ).count()
        
        return render_template('integrations/index.html',
                             integrations=integrations,
                             datasources=datasources,
                             total_integrations=total_integrations,
                             active_integrations=active_integrations,
                             recent_executions=recent_executions,
                             search=search,
                             status_filter=status_filter,
                             source_filter=source_filter,
                             sort_by=sort_by)
    
    @integrations_bp.route('/new')
    @login_required
    def new_integration():
        """Show form to create new integration - FOLLOWS scripts.upload pattern"""
        
        # Get available data sources
        datasources_query = DataSource.query.filter_by(is_active=True)
        datasources = apply_user_data_filter(datasources_query).all()
        
        # Get available Python scripts for transformation
        scripts_query = Script.query.filter_by(script_type='py', is_active=True)
        python_scripts = apply_user_data_filter(scripts_query).all()
        
        return render_template('integrations/form.html',
                             integration=None,
                             datasources=datasources,
                             python_scripts=python_scripts,
                             is_edit=False)
    
    @integrations_bp.route('/create', methods=['POST'])
    @login_required
    def create_integration():
        """Create new integration - FOLLOWS scripts.upload POST pattern"""
        
        try:
            # Get form data
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            source_id = request.form.get('source_id', type=int)
            target_id = request.form.get('target_id', type=int)
            extract_sql = request.form.get('extract_sql', '').strip()
            load_sql = request.form.get('load_sql', '').strip()
            python_script_id = request.form.get('python_script_id', type=int) or None
            
            # Validation
            if not all([name, source_id, target_id, extract_sql, load_sql]):
                flash('All required fields must be filled', 'error')
                return redirect(url_for('integrations.new_integration'))
            
            if source_id == target_id:
                flash('Source and target databases must be different', 'error')
                return redirect(url_for('integrations.new_integration'))
            
            # Verify data sources exist and user has access
            source_ds = apply_user_data_filter(DataSource.query).filter_by(id=source_id, is_active=True).first()
            target_ds = apply_user_data_filter(DataSource.query).filter_by(id=target_id, is_active=True).first()
            
            if not source_ds or not target_ds:
                flash('Invalid data source selection', 'error')
                return redirect(url_for('integrations.new_integration'))
            
            # Verify Python script if provided
            if python_script_id:
                script = apply_user_data_filter(Script.query).filter_by(
                    id=python_script_id, 
                    script_type='py', 
                    is_active=True
                ).first()
                if not script:
                    flash('Invalid Python script selection', 'error')
                    return redirect(url_for('integrations.new_integration'))
            
            # Create integration
            integration = Integration(
                name=name,
                description=description,
                extract_sql=extract_sql,
                load_sql=load_sql,
                source_id=source_id,
                target_id=target_id,
                user_id=current_user.id,
                python_script_id=python_script_id
            )
            
            # Validate SQL queries
            validation_errors = integration.validate_sql_queries()
            if validation_errors:
                flash(f'SQL validation failed: {"; ".join(validation_errors)}', 'error')
                return redirect(url_for('integrations.new_integration'))
            
            db.session.add(integration)
            db.session.commit()
            
            flash(f'Integration "{name}" created successfully', 'success')
            return redirect(url_for('integrations.view_integration', integration_id=integration.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating integration: {str(e)}', 'error')
            return redirect(url_for('integrations.new_integration'))
    
    @integrations_bp.route('/<int:integration_id>')
    @login_required
    def view_integration(integration_id):
        """View integration details - FOLLOWS scripts.view_script pattern"""
        
        # Get integration with user permission check
        integration = apply_user_data_filter(Integration.query).filter_by(id=integration_id).first()
        if not integration:
            flash('Integration not found', 'error')
            return redirect(url_for('integrations.list_integrations'))
        
        # Get recent executions
        executions_query = IntegrationExecution.query.filter_by(integration_id=integration_id)
        recent_executions = apply_user_data_filter(executions_query).order_by(
            desc(IntegrationExecution.started_at)
        ).limit(10).all()
        
        # Get statistics
        total_executions = apply_user_data_filter(executions_query).count()
        successful_executions = apply_user_data_filter(executions_query).filter_by(status='completed').count()
        
        return render_template('integrations/view.html',
                             integration=integration,
                             recent_executions=recent_executions,
                             total_executions=total_executions,
                             successful_executions=successful_executions)
    
    @integrations_bp.route('/<int:integration_id>/edit')
    @login_required
    def edit_integration(integration_id):
        """Edit integration form - FOLLOWS scripts.edit_script pattern"""
        
        # Get integration with user permission check
        integration = apply_user_data_filter(Integration.query).filter_by(id=integration_id).first()
        if not integration:
            flash('Integration not found', 'error')
            return redirect(url_for('integrations.list_integrations'))
        
        # Get available data sources
        datasources_query = DataSource.query.filter_by(is_active=True)
        datasources = apply_user_data_filter(datasources_query).all()
        
        # Get available Python scripts
        scripts_query = Script.query.filter_by(script_type='py', is_active=True)
        python_scripts = apply_user_data_filter(scripts_query).all()
        
        return render_template('integrations/form.html',
                             integration=integration,
                             datasources=datasources,
                             python_scripts=python_scripts,
                             is_edit=True)
    
    @integrations_bp.route('/<int:integration_id>/update', methods=['POST'])
    @login_required
    def update_integration(integration_id):
        """Update integration - FOLLOWS scripts.update_script pattern"""
        
        # Get integration with user permission check
        integration = apply_user_data_filter(Integration.query).filter_by(id=integration_id).first()
        if not integration:
            flash('Integration not found', 'error')
            return redirect(url_for('integrations.list_integrations'))
        
        try:
            # Update fields
            integration.name = request.form.get('name', '').strip()
            integration.description = request.form.get('description', '').strip()
            integration.extract_sql = request.form.get('extract_sql', '').strip()
            integration.load_sql = request.form.get('load_sql', '').strip()
            
            source_id = request.form.get('source_id', type=int)
            target_id = request.form.get('target_id', type=int)
            python_script_id = request.form.get('python_script_id', type=int) or None
            
            # Validation
            if not all([integration.name, source_id, target_id, integration.extract_sql, integration.load_sql]):
                flash('All required fields must be filled', 'error')
                return redirect(url_for('integrations.edit_integration', integration_id=integration_id))
            
            if source_id == target_id:
                flash('Source and target databases must be different', 'error')
                return redirect(url_for('integrations.edit_integration', integration_id=integration_id))
            
            # Verify data sources
            source_ds = apply_user_data_filter(DataSource.query).filter_by(id=source_id, is_active=True).first()
            target_ds = apply_user_data_filter(DataSource.query).filter_by(id=target_id, is_active=True).first()
            
            if not source_ds or not target_ds:
                flash('Invalid data source selection', 'error')
                return redirect(url_for('integrations.edit_integration', integration_id=integration_id))
            
            integration.source_id = source_id
            integration.target_id = target_id
            integration.python_script_id = python_script_id
            
            # Validate SQL
            validation_errors = integration.validate_sql_queries()
            if validation_errors:
                flash(f'SQL validation failed: {"; ".join(validation_errors)}', 'error')
                return redirect(url_for('integrations.edit_integration', integration_id=integration_id))
            
            integration.updated_at = datetime.utcnow()
            db.session.commit()
            
            flash(f'Integration "{integration.name}" updated successfully', 'success')
            return redirect(url_for('integrations.view_integration', integration_id=integration_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating integration: {str(e)}', 'error')
            return redirect(url_for('integrations.edit_integration', integration_id=integration_id))
    
    @integrations_bp.route('/<int:integration_id>/execute', methods=['POST'])
    @login_required
    def execute_integration(integration_id):
        """Execute integration manually - FOLLOWS scripts.execute_script pattern"""
        
        # Get integration with user permission check
        integration = apply_user_data_filter(Integration.query).filter_by(id=integration_id).first()
        if not integration:
            return jsonify({'success': False, 'message': 'Integration not found'}), 404
        
        try:
            # Import ETL executor
            from app.services.etl_executor import etl_executor
            from app.models.integration_execution import IntegrationExecutionTrigger
            
            # Execute integration
            execution = etl_executor.execute_integration(
                integration_id=integration_id,
                user_id=current_user.id,
                trigger_type=IntegrationExecutionTrigger.MANUAL
            )
            
            return jsonify({
                'success': True,
                'message': f'Integration "{integration.name}" execution started',
                'execution_id': execution.id
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Failed to start execution: {str(e)}'
            }), 500
    
    @integrations_bp.route('/<int:integration_id>/delete', methods=['POST'])
    @login_required
    def delete_integration(integration_id):
        """Delete integration - FOLLOWS scripts.delete_script pattern"""
        
        # Get integration with user permission check
        integration = apply_user_data_filter(Integration.query).filter_by(id=integration_id).first()
        if not integration:
            flash('Integration not found', 'error')
            return redirect(url_for('integrations.list_integrations'))
        
        try:
            integration_name = integration.name
            
            # Soft delete (set is_active = False)
            integration.is_active = False
            integration.updated_at = datetime.utcnow()
            db.session.commit()
            
            flash(f'Integration "{integration_name}" deleted successfully', 'success')
            return redirect(url_for('integrations.list_integrations'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error deleting integration: {str(e)}', 'error')
            return redirect(url_for('integrations.view_integration', integration_id=integration_id))
    
    @integrations_bp.route('/executions')
    @login_required
    def list_executions():
        """List all integration executions - FOLLOWS logs.list_logs pattern"""
        
        # Get filters
        integration_filter = request.args.get('integration', '')
        status_filter = request.args.get('status', '')
        date_filter = request.args.get('date', '')
        sort_by = request.args.get('sort', 'recent')
        
        # Build query with user permission filter
        executions_query = IntegrationExecution.query
        query = apply_user_data_filter(executions_query)
        
        # Integration filter
        if integration_filter:
            query = query.filter_by(integration_id=integration_filter)
        
        # Status filter
        if status_filter:
            query = query.filter_by(status=status_filter)
        
        # Date filter
        if date_filter:
            if date_filter == 'today':
                today = datetime.utcnow().date()
                query = query.filter(func.date(IntegrationExecution.started_at) == today)
            elif date_filter == 'week':
                week_ago = datetime.utcnow() - timedelta(days=7)
                query = query.filter(IntegrationExecution.started_at >= week_ago)
            elif date_filter == 'month':
                month_ago = datetime.utcnow() - timedelta(days=30)
                query = query.filter(IntegrationExecution.started_at >= month_ago)
        
        # Sorting
        if sort_by == 'oldest':
            query = query.order_by(IntegrationExecution.started_at)
        else:  # recent (default)
            query = query.order_by(desc(IntegrationExecution.started_at))
        
        # Pagination
        page = request.args.get('page', 1, type=int)
        per_page = 25
        executions = query.paginate(
            page=page, per_page=per_page, 
            error_out=False
        )
        
        # Get integrations for filter dropdown
        integrations_query = Integration.query.filter_by(is_active=True)
        integrations = apply_user_data_filter(integrations_query).all()
        
        return render_template('integrations/executions.html',
                             executions=executions,
                             integrations=integrations,
                             integration_filter=integration_filter,
                             status_filter=status_filter,
                             date_filter=date_filter,
                             sort_by=sort_by)
    
    @integrations_bp.route('/executions/<int:execution_id>')
    @login_required
    def view_execution(execution_id):
        """View execution details - FOLLOWS logs.execution_detail pattern"""
        
        # Get execution with user permission check
        execution = apply_user_data_filter(IntegrationExecution.query).filter_by(id=execution_id).first()
        if not execution:
            flash('Execution not found', 'error')
            return redirect(url_for('integrations.list_executions'))
        
        return render_template('integrations/execution_detail.html',
                             execution=execution)
    
    return integrations_bp