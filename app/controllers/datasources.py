"""
Data Sources Blueprint
Handles database connection management for Integration feature
Follows the same pattern as existing ScriptFlow controllers
"""

import json
from datetime import datetime
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from sqlalchemy import desc

# Create Blueprint
datasources_bp = Blueprint('datasources', __name__, url_prefix='/integrations/sources')

def init_datasources_blueprint(app, db, DataSource, apply_user_data_filter):
    """Initialize datasources blueprint with dependencies - SAME PATTERN as existing controllers"""
    
    @datasources_bp.route('/')
    @login_required
    def list_datasources():
        """List all data sources - FOLLOWS existing list patterns"""
        
        # Get filters from query parameters
        search = request.args.get('search', '').strip()
        db_type_filter = request.args.get('db_type', '')
        sort_by = request.args.get('sort', 'updated')
        
        # Build query with user permission filter
        datasources_query = DataSource.query.filter_by(is_active=True)
        query = apply_user_data_filter(datasources_query)
        
        # Search filter
        if search:
            query = query.filter(DataSource.name.contains(search))
        
        # Database type filter
        if db_type_filter and db_type_filter in ['oracle', 'postgres']:
            query = query.filter_by(db_type=db_type_filter)
        
        # Sorting
        if sort_by == 'name':
            query = query.order_by(DataSource.name)
        elif sort_by == 'created':
            query = query.order_by(desc(DataSource.created_at))
        elif sort_by == 'db_type':
            query = query.order_by(DataSource.db_type, DataSource.name)
        else:  # default to updated
            query = query.order_by(desc(DataSource.updated_at))
        
        datasources = query.all()
        
        # Get statistics
        total_datasources = len(datasources)
        oracle_count = sum(1 for ds in datasources if ds.db_type == 'oracle')
        postgres_count = sum(1 for ds in datasources if ds.db_type == 'postgres')
        
        return render_template('integrations/sources/index.html',
                             datasources=datasources,
                             total_datasources=total_datasources,
                             oracle_count=oracle_count,
                             postgres_count=postgres_count,
                             search=search,
                             db_type_filter=db_type_filter,
                             sort_by=sort_by)
    
    @datasources_bp.route('/new')
    @login_required
    def new_datasource():
        """Show form to create new data source"""
        return render_template('integrations/sources/form.html',
                             datasource=None,
                             is_edit=False)
    
    @datasources_bp.route('/create', methods=['POST'])
    @login_required
    def create_datasource():
        """Create new data source"""
        
        try:
            # Get form data
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            db_type = request.form.get('db_type', '').strip()
            host = request.form.get('host', '').strip()
            port = request.form.get('port', type=int)
            database = request.form.get('database', '').strip()
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '').strip()
            
            # Validation
            if not all([name, db_type, host, port, database, username, password]):
                flash('All fields are required', 'error')
                return redirect(url_for('datasources.new_datasource'))
            
            if db_type not in ['oracle', 'postgres']:
                flash('Invalid database type', 'error')
                return redirect(url_for('datasources.new_datasource'))
            
            if port < 1 or port > 65535:
                flash('Port must be between 1 and 65535', 'error')
                return redirect(url_for('datasources.new_datasource'))
            
            # Check for duplicate name
            existing = apply_user_data_filter(DataSource.query).filter_by(name=name, is_active=True).first()
            if existing:
                flash(f'Data source with name "{name}" already exists', 'error')
                return redirect(url_for('datasources.new_datasource'))
            
            # Create data source
            datasource = DataSource(
                name=name,
                description=description,
                db_type=db_type,
                host=host,
                port=port,
                database=database,
                username=username,
                password=password,  # Will be encrypted in the model
                user_id=current_user.id
            )
            
            db.session.add(datasource)
            db.session.commit()
            
            flash(f'Data source "{name}" created successfully', 'success')
            return redirect(url_for('datasources.list_datasources'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating data source: {str(e)}', 'error')
            return redirect(url_for('datasources.new_datasource'))
    
    @datasources_bp.route('/<int:datasource_id>')
    @login_required
    def view_datasource(datasource_id):
        """View data source details"""
        
        # Get datasource with user permission check
        datasource = apply_user_data_filter(DataSource.query).filter_by(id=datasource_id).first()
        if not datasource:
            flash('Data source not found', 'error')
            return redirect(url_for('datasources.list_datasources'))
        
        # Get usage statistics
        integrations_as_source = len(datasource.integrations_as_source)
        integrations_as_target = len(datasource.integrations_as_target)
        total_usage = integrations_as_source + integrations_as_target
        
        return render_template('integrations/sources/view.html',
                             datasource=datasource,
                             integrations_as_source=integrations_as_source,
                             integrations_as_target=integrations_as_target,
                             total_usage=total_usage)
    
    @datasources_bp.route('/<int:datasource_id>/edit')
    @login_required
    def edit_datasource(datasource_id):
        """Edit data source form"""
        
        # Get datasource with user permission check
        datasource = apply_user_data_filter(DataSource.query).filter_by(id=datasource_id).first()
        if not datasource:
            flash('Data source not found', 'error')
            return redirect(url_for('datasources.list_datasources'))
        
        return render_template('integrations/sources/form.html',
                             datasource=datasource,
                             is_edit=True)
    
    @datasources_bp.route('/<int:datasource_id>/update', methods=['POST'])
    @login_required
    def update_datasource(datasource_id):
        """Update data source"""
        
        # Get datasource with user permission check
        datasource = apply_user_data_filter(DataSource.query).filter_by(id=datasource_id).first()
        if not datasource:
            flash('Data source not found', 'error')
            return redirect(url_for('datasources.list_datasources'))
        
        try:
            # Update fields
            datasource.name = request.form.get('name', '').strip()
            datasource.description = request.form.get('description', '').strip()
            datasource.db_type = request.form.get('db_type', '').strip()
            datasource.host = request.form.get('host', '').strip()
            datasource.port = request.form.get('port', type=int)
            datasource.database = request.form.get('database', '').strip()
            datasource.username = request.form.get('username', '').strip()
            
            # Update password only if provided
            new_password = request.form.get('password', '').strip()
            if new_password:
                datasource.set_password(new_password)
            
            # Validation
            if not all([datasource.name, datasource.db_type, datasource.host, 
                       datasource.port, datasource.database, datasource.username]):
                flash('All required fields must be filled', 'error')
                return redirect(url_for('datasources.edit_datasource', datasource_id=datasource_id))
            
            if datasource.db_type not in ['oracle', 'postgres']:
                flash('Invalid database type', 'error')
                return redirect(url_for('datasources.edit_datasource', datasource_id=datasource_id))
            
            if datasource.port < 1 or datasource.port > 65535:
                flash('Port must be between 1 and 65535', 'error')
                return redirect(url_for('datasources.edit_datasource', datasource_id=datasource_id))
            
            # Check for duplicate name (excluding current datasource)
            existing = apply_user_data_filter(DataSource.query).filter(
                DataSource.name == datasource.name,
                DataSource.id != datasource_id,
                DataSource.is_active == True
            ).first()
            if existing:
                flash(f'Data source with name "{datasource.name}" already exists', 'error')
                return redirect(url_for('datasources.edit_datasource', datasource_id=datasource_id))
            
            datasource.updated_at = datetime.utcnow()
            db.session.commit()
            
            flash(f'Data source "{datasource.name}" updated successfully', 'success')
            return redirect(url_for('datasources.view_datasource', datasource_id=datasource_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating data source: {str(e)}', 'error')
            return redirect(url_for('datasources.edit_datasource', datasource_id=datasource_id))
    
    @datasources_bp.route('/<int:datasource_id>/test', methods=['POST'])
    @login_required
    def test_connection(datasource_id):
        """Test database connection - AJAX endpoint"""
        
        # Get datasource with user permission check
        datasource = apply_user_data_filter(DataSource.query).filter_by(id=datasource_id).first()
        if not datasource:
            return jsonify({'success': False, 'message': 'Data source not found'}), 404
        
        try:
            # Import connection manager
            from app.services.connection_manager import connection_manager
            
            # Test connection
            success, message = connection_manager.test_connection(datasource_id)
            
            return jsonify({
                'success': success,
                'message': message,
                'tested_at': datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Connection test failed: {str(e)}'
            }), 500
    
    @datasources_bp.route('/test-form', methods=['POST'])
    @login_required
    def test_form_connection():
        """Test connection with form data (before saving) - AJAX endpoint"""
        
        try:
            # Get form data
            db_type = request.json.get('db_type', '').strip()
            host = request.json.get('host', '').strip()
            port = request.json.get('port', type=int)
            database = request.json.get('database', '').strip()
            username = request.json.get('username', '').strip()
            password = request.json.get('password', '').strip()
            
            # Validation
            if not all([db_type, host, port, database, username, password]):
                return jsonify({'success': False, 'message': 'All fields are required'}), 400
            
            if db_type not in ['oracle', 'postgres']:
                return jsonify({'success': False, 'message': 'Invalid database type'}), 400
            
            # Create temporary datasource for testing (not saved to DB)
            temp_datasource = DataSource(
                name='temp_test',
                description='Temporary for testing',
                db_type=db_type,
                host=host,
                port=port,
                database=database,
                username=username,
                password=password,
                user_id=current_user.id
            )
            
            # Test connection using connection string
            from sqlalchemy import create_engine, text
            
            engine = create_engine(
                temp_datasource.connection_string,
                connect_args={'timeout': 10}
            )
            
            with engine.connect() as conn:
                if db_type == 'oracle':
                    conn.execute(text("SELECT 1 FROM DUAL"))
                else:  # postgres
                    conn.execute(text("SELECT 1"))
            
            return jsonify({
                'success': True,
                'message': 'Connection successful',
                'tested_at': datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Connection failed: {str(e)}'
            }), 500
    
    @datasources_bp.route('/<int:datasource_id>/delete', methods=['POST'])
    @login_required
    def delete_datasource(datasource_id):
        """Delete data source (soft delete)"""
        
        # Get datasource with user permission check
        datasource = apply_user_data_filter(DataSource.query).filter_by(id=datasource_id).first()
        if not datasource:
            flash('Data source not found', 'error')
            return redirect(url_for('datasources.list_datasources'))
        
        # Check if datasource is being used
        total_usage = len(datasource.integrations_as_source) + len(datasource.integrations_as_target)
        if total_usage > 0:
            flash(f'Cannot delete data source "{datasource.name}" - it is being used by {total_usage} integration(s)', 'error')
            return redirect(url_for('datasources.view_datasource', datasource_id=datasource_id))
        
        try:
            datasource_name = datasource.name
            
            # Soft delete
            datasource.is_active = False
            datasource.updated_at = datetime.utcnow()
            db.session.commit()
            
            flash(f'Data source "{datasource_name}" deleted successfully', 'success')
            return redirect(url_for('datasources.list_datasources'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error deleting data source: {str(e)}', 'error')
            return redirect(url_for('datasources.view_datasource', datasource_id=datasource_id))
    
    return datasources_bp