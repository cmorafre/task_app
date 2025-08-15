"""
Schedule Model - Script scheduling and automation
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from enum import Enum
import json

# Import db from models package
from app.models import db

class ScheduleFrequency(Enum):
    """Schedule frequency enumeration"""
    DAILY = 'daily'
    WEEKLY = 'weekly'
    MONTHLY = 'monthly'
    HOURLY = 'hourly'

class Schedule(db.Model):
    """Schedule model for managing automated script execution"""
    
    __tablename__ = 'schedules'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    frequency = db.Column(db.Enum(ScheduleFrequency), nullable=False)
    schedule_config = db.Column(db.Text)  # JSON config for complex schedules
    next_execution = db.Column(db.DateTime)
    last_execution = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Email notification settings
    notify_on_success = db.Column(db.Boolean, default=False)
    notify_on_failure = db.Column(db.Boolean, default=True)
    notification_emails = db.Column(db.Text)  # JSON array of email addresses
    
    # Foreign key
    script_id = db.Column(db.Integer, db.ForeignKey('scripts.id'), nullable=False)
    
    # Relationships
    executions = db.relationship('Execution', backref='schedule', lazy=True)
    
    def __init__(self, name, script_id, frequency, schedule_config=None, description=''):
        self.name = name
        self.script_id = script_id
        self.frequency = frequency
        self.schedule_config = schedule_config
        self.description = description
        self.next_execution = self.calculate_next_execution()
    
    @property
    def config_dict(self):
        """Get schedule configuration as dictionary"""
        if not self.schedule_config:
            return {}
        try:
            return json.loads(self.schedule_config)
        except json.JSONDecodeError:
            return {}
    
    @config_dict.setter
    def config_dict(self, value):
        """Set schedule configuration from dictionary"""
        self.schedule_config = json.dumps(value) if value else None
    
    @property
    def notification_email_list(self):
        """Get notification emails as list"""
        if not self.notification_emails:
            return []
        try:
            return json.loads(self.notification_emails)
        except json.JSONDecodeError:
            return []
    
    @notification_email_list.setter
    def notification_email_list(self, emails):
        """Set notification emails from list"""
        self.notification_emails = json.dumps(emails) if emails else None
    
    @property
    def recent_executions_count(self):
        """Get count of executions in last 30 days"""
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        return Execution.query.filter(
            Execution.schedule_id == self.id,
            Execution.started_at >= thirty_days_ago
        ).count()
    
    @property
    def success_rate(self):
        """Calculate success rate for this schedule"""
        total = self.recent_executions_count
        if total == 0:
            return 100  # No executions yet, assume will be successful
        
        successful = Execution.query.filter(
            Execution.schedule_id == self.id,
            Execution.status == 'completed',
            Execution.exit_code == 0
        ).count()
        
        return round((successful / total) * 100, 1)
    
    @property
    def status_icon(self):
        """Get status icon for UI display"""
        if not self.is_active:
            return '⏸️'
        
        if self.success_rate >= 90:
            return '✅'
        elif self.success_rate >= 70:
            return '⚠️'
        else:
            return '❌'
    
    @property
    def formatted_frequency(self):
        """Get human-readable frequency description"""
        config = self.config_dict
        
        if self.frequency == ScheduleFrequency.HOURLY:
            return "Every hour"
        elif self.frequency == ScheduleFrequency.DAILY:
            time = config.get('time', '00:00')
            return f"Daily at {time}"
        elif self.frequency == ScheduleFrequency.WEEKLY:
            days = config.get('days', ['Monday'])
            time = config.get('time', '00:00')
            days_str = ', '.join(days)
            return f"Weekly on {days_str} at {time}"
        elif self.frequency == ScheduleFrequency.MONTHLY:
            day = config.get('day', 1)
            time = config.get('time', '00:00')
            return f"Monthly on day {day} at {time}"
        
        return self.frequency.value.title()
    
    def calculate_next_execution(self):
        """Calculate next execution time based on frequency and config"""
        if not self.is_active:
            return None
        
        now = datetime.utcnow()
        config = self.config_dict
        
        if self.frequency == ScheduleFrequency.HOURLY:
            # Next hour
            return now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        
        elif self.frequency == ScheduleFrequency.DAILY:
            # Parse time from config (format: "HH:MM")
            time_str = config.get('time', '00:00')
            try:
                hour, minute = map(int, time_str.split(':'))
                next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                # If time has passed today, schedule for tomorrow
                if next_run <= now:
                    next_run += timedelta(days=1)
                
                return next_run
            except (ValueError, AttributeError):
                # Default to midnight if config is invalid
                return now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        
        elif self.frequency == ScheduleFrequency.WEEKLY:
            # Parse time and days from config
            time_str = config.get('time', '00:00')
            days = config.get('days', ['Monday'])
            
            # Map day names to weekday numbers (Monday=0, Sunday=6)
            day_map = {
                'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3,
                'Friday': 4, 'Saturday': 5, 'Sunday': 6
            }
            
            try:
                hour, minute = map(int, time_str.split(':'))
                target_weekdays = [day_map[day] for day in days if day in day_map]
                
                if not target_weekdays:
                    target_weekdays = [0]  # Default to Monday
                
                # Find next occurrence
                current_weekday = now.weekday()
                days_ahead = None
                
                for target_day in sorted(target_weekdays):
                    days_until = (target_day - current_weekday) % 7
                    candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    
                    if days_until == 0 and candidate <= now:
                        days_until = 7  # Next week
                    
                    if days_ahead is None or days_until < days_ahead:
                        days_ahead = days_until
                
                return now.replace(hour=hour, minute=minute, second=0, microsecond=0) + timedelta(days=days_ahead)
            
            except (ValueError, AttributeError):
                # Default to next Monday at midnight
                days_ahead = (0 - now.weekday()) % 7
                if days_ahead == 0:
                    days_ahead = 7
                return now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=days_ahead)
        
        elif self.frequency == ScheduleFrequency.MONTHLY:
            # Parse time and day from config
            time_str = config.get('time', '00:00')
            target_day = config.get('day', 1)
            
            try:
                hour, minute = map(int, time_str.split(':'))
                
                # Start with current month
                next_run = now.replace(day=target_day, hour=hour, minute=minute, second=0, microsecond=0)
                
                # If this month's date has passed, move to next month
                if next_run <= now:
                    if now.month == 12:
                        next_run = next_run.replace(year=now.year + 1, month=1)
                    else:
                        next_run = next_run.replace(month=now.month + 1)
                
                return next_run
            
            except (ValueError, AttributeError):
                # Default to 1st of next month at midnight
                if now.month == 12:
                    return now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
                else:
                    return now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
        
        return None
    
    def update_next_execution(self):
        """Update next execution time and save to database"""
        self.next_execution = self.calculate_next_execution()
        db.session.commit()
    
    def mark_executed(self):
        """Mark schedule as executed and calculate next run"""
        self.last_execution = datetime.utcnow()
        self.update_next_execution()
    
    def toggle_active(self):
        """Toggle schedule active status"""
        self.is_active = not self.is_active
        if self.is_active:
            self.update_next_execution()
        else:
            self.next_execution = None
        db.session.commit()
    
    def __repr__(self):
        return f'<Schedule {self.name} - {self.frequency.value}>'