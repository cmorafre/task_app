"""
Authentication Blueprint
Handles login, logout, and registration routes
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import or_

# Create Blueprint
auth_bp = Blueprint('auth', __name__)

def init_auth_blueprint(db, User):
    """Initialize auth blueprint with database dependencies"""
    
    @auth_bp.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('main.dashboard'))
        return redirect(url_for('auth.login'))

    @auth_bp.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('main.dashboard'))
        
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            remember = bool(request.form.get('remember'))
            
            if not username or not password:
                flash('Please enter both username and password.', 'error')
                return render_template('login.html')
            
            user = User.query.filter_by(username=username).first()
            
            if user and user.check_password(password):
                login_user(user, remember=remember)
                user.update_last_login()
                flash(f'Welcome back, {user.username}!', 'success')
                return redirect(url_for('main.dashboard'))
            else:
                flash('Invalid username or password.', 'error')
        
        return render_template('login.html')

    @auth_bp.route('/register', methods=['GET', 'POST'])
    def register():
        """User registration page"""
        if current_user.is_authenticated:
            return redirect(url_for('main.dashboard'))
        
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')
            
            # Validation
            if not username or not email or not password:
                flash('Please fill in all required fields.', 'error')
                return render_template('register.html')
            
            if len(username) < 3:
                flash('Username must be at least 3 characters long.', 'error')
                return render_template('register.html')
            
            if len(password) < 6:
                flash('Password must be at least 6 characters long.', 'error')
                return render_template('register.html')
            
            if password != confirm_password:
                flash('Passwords do not match.', 'error')
                return render_template('register.html')
            
            # Check if username or email already exists
            existing_user = User.query.filter(
                or_(User.username == username, User.email == email)
            ).first()
            
            if existing_user:
                if existing_user.username == username:
                    flash('Username already exists. Please choose a different username.', 'error')
                else:
                    flash('Email already registered. Please use a different email.', 'error')
                return render_template('register.html')
            
            # Create new user
            try:
                new_user = User(
                    username=username,
                    email=email
                )
                new_user.set_password(password)
                
                db.session.add(new_user)
                db.session.commit()
                
                flash(f'Account created successfully! Welcome, {username}!', 'success')
                
                # Auto-login the new user
                login_user(new_user)
                return redirect(url_for('main.dashboard'))
                
            except Exception as e:
                db.session.rollback()
                import traceback
                error_details = traceback.format_exc()
                print(f"Registration error: {e}")
                print(f"Full traceback: {error_details}")
                flash('An error occurred while creating your account. Please try again.', 'error')
        
        return render_template('register.html')

    @auth_bp.route('/logout')
    @login_required
    def logout():
        username = current_user.username
        logout_user()
        flash(f'Goodbye, {username}!', 'info')
        return redirect(url_for('auth.login'))
    
    return auth_bp