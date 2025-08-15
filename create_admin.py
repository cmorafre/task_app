#!/usr/bin/env python3
"""
Create Admin User Script
"""

import os
import sys
from werkzeug.security import generate_password_hash
from getpass import getpass

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from app_simple import app, db, User
except ImportError:
    print("❌ Error: Could not import app components.")
    print("Make sure you're running this from the project root directory.")
    sys.exit(1)

def create_admin():
    """Create a new admin user"""
    
    print("🔧 ScriptFlow Admin User Creation")
    print("=" * 40)
    
    with app.app_context():
        # Check if admin already exists
        existing_admin = User.query.filter_by(username='admin').first()
        if existing_admin:
            overwrite = input("⚠️  Admin user already exists. Overwrite? (y/N): ").lower()
            if overwrite != 'y':
                print("❌ Cancelled.")
                return
            
            # Delete existing admin
            db.session.delete(existing_admin)
            db.session.commit()
            print("🗑️  Existing admin user deleted.")
        
        # Get user input
        username = input("👤 Username (default: admin): ").strip() or 'admin'
        email = input("📧 Email (default: admin@scriptflow.local): ").strip() or 'admin@scriptflow.local'
        
        # Get password
        while True:
            password = getpass("🔒 Password (default: admin123): ") or 'admin123'
            confirm_password = getpass("🔒 Confirm password: ") or 'admin123'
            
            if password == confirm_password:
                break
            else:
                print("❌ Passwords don't match. Please try again.")
        
        # Create user
        try:
            admin_user = User(
                username=username,
                email=email,
                password_hash=generate_password_hash(password)
            )
            
            db.session.add(admin_user)
            db.session.commit()
            
            print("✅ Admin user created successfully!")
            print(f"   Username: {username}")
            print(f"   Email: {email}")
            print("🚀 You can now start the application with: python app_simple.py")
            
        except Exception as e:
            print(f"❌ Error creating user: {e}")
            sys.exit(1)

if __name__ == '__main__':
    create_admin()