#!/bin/bash

# ScriptFlow Startup Script
# Simple deployment script for Digital Ocean VPS

set -e

echo "🚀 Starting ScriptFlow..."

# Check Python version
python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
echo "🐍 Python version: $python_version"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies
echo "📋 Installing dependencies..."
pip install -r requirements.txt

# Create necessary directories
mkdir -p uploads logs

# Set permissions
chmod 755 uploads logs

# Initialize database if not exists
if [ ! -f "scriptflow.db" ]; then
    echo "🗄️  Initializing database..."
    python -c "from app_simple import app, db; app.app_context().push(); db.create_all()"
fi

# Check if admin user exists
admin_exists=$(python -c "
from app_simple import app, User
with app.app_context():
    admin = User.query.filter_by(username='admin').first()
    print('yes' if admin else 'no')
" 2>/dev/null || echo "no")

if [ "$admin_exists" = "no" ]; then
    echo "👤 Creating default admin user..."
    python -c "
from app_simple import app, db, User
from werkzeug.security import generate_password_hash
with app.app_context():
    admin = User(
        username='admin',
        email='admin@scriptflow.local',
        password_hash=generate_password_hash('admin123')
    )
    db.session.add(admin)
    db.session.commit()
    print('✅ Admin user created: admin/admin123')
"
fi

# Start application
echo "🌟 Starting ScriptFlow application..."
echo "📍 Access at: http://localhost:8000"
echo "👤 Default login: admin/admin123"
echo ""
echo "Press Ctrl+C to stop"

# Run in production mode
export FLASK_ENV=production
python app_simple.py