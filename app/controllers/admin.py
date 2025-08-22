"""
Admin Blueprint
Handles admin-only operations: user management
"""

from functools import wraps
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, abort
from flask_login import login_required, current_user
from sqlalchemy import or_

# Create Blueprint
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    """Decorator to require admin access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)  # Forbidden
        return f(*args, **kwargs)
    return decorated_function

def init_admin_blueprint(db, User, Script, Execution, Schedule):
    """Initialize admin blueprint with dependencies"""
    
    @admin_bp.route('/users')
    @login_required
    @admin_required
    def manage_users():
        """User management page for admins"""
        users = User.query.order_by(User.created_at.desc()).all()
        return render_template('admin/users.html', users=users)

    @admin_bp.route('/users/create', methods=['GET', 'POST'])
    @login_required
    @admin_required
    def create_user():
        """Create new user (admin only)"""
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')
            is_admin = bool(request.form.get('is_admin'))
            can_view_all_data = bool(request.form.get('can_view_all_data'))
            
            # Validation
            if not username or not email or not password:
                flash('Please fill in all required fields.', 'error')
                return render_template('admin/create_user.html')
            
            if len(username) < 3:
                flash('Username must be at least 3 characters long.', 'error')
                return render_template('admin/create_user.html')
            
            if len(password) < 6:
                flash('Password must be at least 6 characters long.', 'error')
                return render_template('admin/create_user.html')
            
            # Check if username or email already exists
            existing_user = User.query.filter(
                or_(User.username == username, User.email == email)
            ).first()
            
            if existing_user:
                if existing_user.username == username:
                    flash('Username already exists. Please choose a different username.', 'error')
                else:
                    flash('Email already registered. Please use a different email.', 'error')
                return render_template('admin/create_user.html')
            
            # Create new user
            try:
                new_user = User(
                    username=username,
                    email=email,
                    is_admin=is_admin,
                    can_view_all_data=can_view_all_data
                )
                new_user.set_password(password)
                
                db.session.add(new_user)
                db.session.commit()
                
                flash(f'User "{username}" created successfully!', 'success')
                return redirect(url_for('admin.manage_users'))
                
            except Exception as e:
                db.session.rollback()
                print(f"User creation error: {e}")
                flash('An error occurred while creating the user. Please try again.', 'error')
        
        return render_template('admin/create_user.html')

    @admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
    @login_required
    @admin_required
    def edit_user(user_id):
        """Edit user (admin only)"""
        user = db.session.get(User, user_id) or abort(404)
        
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')
            is_admin = bool(request.form.get('is_admin'))
            can_view_all_data = bool(request.form.get('can_view_all_data'))
            
            # Validation
            if not username or not email:
                flash('Please fill in all required fields.', 'error')
                # Get admin count for template
                admin_count = User.query.filter_by(is_admin=True).count()
                return render_template('admin/edit_user.html', user=user, admin_count=admin_count)
            
            if len(username) < 3:
                flash('Username must be at least 3 characters long.', 'error')
                return render_template('admin/edit_user.html', user=user)
            
            # Check if username or email already exists (excluding current user)
            existing_user = User.query.filter(
                or_(User.username == username, User.email == email),
                User.id != user_id
            ).first()
            
            if existing_user:
                if existing_user.username == username:
                    flash('Username already exists. Please choose a different username.', 'error')
                else:
                    flash('Email already registered. Please use a different email.', 'error')
                return render_template('admin/edit_user.html', user=user)
            
            # Prevent removing admin status from last admin
            if user.is_admin and not is_admin:
                admin_count = User.query.filter_by(is_admin=True).count()
                if admin_count <= 1:
                    flash('Cannot remove admin status. At least one admin must exist.', 'error')
                    return render_template('admin/edit_user.html', user=user)
            
            # Update user
            try:
                user.username = username
                user.email = email
                user.is_admin = is_admin
                user.can_view_all_data = can_view_all_data
                
                # Update password if provided
                if password and len(password) >= 6:
                    user.set_password(password)
                elif password and len(password) < 6:
                    flash('Password must be at least 6 characters long if provided.', 'error')
                    return render_template('admin/edit_user.html', user=user)
                
                db.session.commit()
                
                flash(f'User "{username}" updated successfully!', 'success')
                return redirect(url_for('admin.manage_users'))
                
            except Exception as e:
                db.session.rollback()
                print(f"User update error: {e}")
                flash('An error occurred while updating the user. Please try again.', 'error')
        
        # Get admin count for template
        admin_count = User.query.filter_by(is_admin=True).count()
        return render_template('admin/edit_user.html', user=user, admin_count=admin_count)

    @admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
    @login_required
    @admin_required
    def delete_user(user_id):
        """Delete user (admin only)"""
        user = db.session.get(User, user_id) or abort(404)
        
        # Prevent deleting yourself
        if user.id == current_user.id:
            return jsonify({'success': False, 'message': 'Cannot delete your own account'}), 400
        
        # Prevent deleting last admin
        if user.is_admin:
            admin_count = User.query.filter_by(is_admin=True).count()
            if admin_count <= 1:
                return jsonify({'success': False, 'message': 'Cannot delete the last admin user'}), 400
        
        try:
            # Delete user's related data
            Script.query.filter_by(user_id=user_id).delete()
            Execution.query.filter_by(user_id=user_id).delete()
            Schedule.query.filter_by(user_id=user_id).delete()
            
            # Delete user
            db.session.delete(user)
            db.session.commit()
            
            return jsonify({'success': True, 'message': f'User "{user.username}" deleted successfully'})
            
        except Exception as e:
            db.session.rollback()
            print(f"User deletion error: {e}")
            return jsonify({'success': False, 'message': 'An error occurred while deleting the user'}), 500
    
    return admin_bp