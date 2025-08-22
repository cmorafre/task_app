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
    INTERVAL = 'interval'

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
    
    # Foreign keys (EXTENDED for Integration feature - NON-BREAKING)
    script_id = db.Column(db.Integer, db.ForeignKey('scripts.id'), nullable=True)  # Made nullable for Integration jobs
    integration_id = db.Column(db.Integer, db.ForeignKey('integrations.id'), nullable=True)  # NEW: Integration support
    
    # Relationships
    executions = db.relationship('Execution', backref='schedule', lazy=True)
    
    def __init__(self, name, frequency, schedule_config=None, description='', script_id=None, integration_id=None):
        """EXTENDED constructor for Integration support (BACKWARD COMPATIBLE)"""
        self.name = name
        self.frequency = frequency
        self.schedule_config = schedule_config
        self.description = description
        
        # Support both script and integration scheduling (NEW)
        if script_id and integration_id:
            raise ValueError("Cannot schedule both script and integration. Choose one.")
        if not script_id and not integration_id:
            raise ValueError("Must provide either script_id or integration_id")
            
        self.script_id = script_id
        self.integration_id = integration_id
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
        elif self.frequency == ScheduleFrequency.INTERVAL:
            interval_minutes = config.get('interval_minutes', 15)
            if interval_minutes == 60:
                return "Every hour"
            else:
                return f"Every {interval_minutes} minutes"
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
        
        elif self.frequency == ScheduleFrequency.INTERVAL:
            # Next execution based on interval minutes and start time
            interval_minutes = config.get('interval_minutes', 15)
            start_time = config.get('time', '09:00')
            start_date = config.get('start_date')
            
            try:
                interval_minutes = int(interval_minutes)
                if interval_minutes <= 0:
                    interval_minutes = 15
            except (ValueError, TypeError):
                interval_minutes = 15
            
            try:
                # Parse start time
                hour, minute = map(int, start_time.split(':'))
                
                # Determine the start datetime
                if start_date:
                    # Parse start date (format: YYYY-MM-DD)
                    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
                    first_run = start_date_obj.replace(hour=hour, minute=minute, second=0, microsecond=0)
                else:
                    # Use today with specified time
                    first_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                # If first run is in the past, calculate next interval-based execution
                if first_run <= now:
                    # Calculate how many intervals have passed since first_run
                    time_diff = now - first_run
                    intervals_passed = int(time_diff.total_seconds() // (interval_minutes * 60))
                    # Next execution is first_run + (intervals_passed + 1) * interval
                    return first_run + timedelta(minutes=(intervals_passed + 1) * interval_minutes)
                else:
                    # First run is in the future, use it
                    return first_run
                    
            except (ValueError, AttributeError):
                # Fallback to current time + interval if parsing fails
                return now + timedelta(minutes=interval_minutes)
        
        elif self.frequency == ScheduleFrequency.DAILY:
            # Parse time and start_date from config (format: "HH:MM")
            time_str = config.get('time', '00:00')
            start_date = config.get('start_date')
            
            try:
                hour, minute = map(int, time_str.split(':'))
                
                # Determine the start datetime
                if start_date:
                    # Parse start date (format: YYYY-MM-DD)
                    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
                    next_run = start_date_obj.replace(hour=hour, minute=minute, second=0, microsecond=0)
                else:
                    # Use today with specified time
                    next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                # If time has passed, schedule for next day
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
    
    # === NEW INTEGRATION FEATURE METHODS (NON-BREAKING ADDITIONS) ===
    
    @property
    def is_script_schedule(self):
        """Check if this schedule is for a script (NEW)"""
        return self.script_id is not None
    
    @property
    def is_integration_schedule(self):
        """Check if this schedule is for an integration (NEW)"""
        return self.integration_id is not None
    
    @property
    def schedule_type(self):
        """Get schedule type description (NEW)"""
        if self.is_script_schedule:
            return "Script"
        elif self.is_integration_schedule:
            return "Integration"
        else:
            return "Unknown"
    
    @property
    def scheduled_item(self):
        """Get the scheduled item (script or integration) (NEW)"""
        if self.is_script_schedule:
            try:
                from app.models.script import Script
                return Script.query.get(self.script_id)
            except ImportError:
                return None
        elif self.is_integration_schedule:
            try:
                from app.models.integration import Integration
                return Integration.query.get(self.integration_id)
            except ImportError:
                return None
        return None
    
    @property
    def scheduled_item_name(self):
        """Get name of scheduled item (NEW)"""
        item = self.scheduled_item
        return item.name if item else "Unknown"
    
    @property
    def scheduled_item_description(self):
        """Get description of scheduled item (NEW)"""
        item = self.scheduled_item
        return item.description if item else ""
    
    def get_execution_history(self, limit=10):
        """Get execution history for this schedule (NEW - supports both types)"""
        if self.is_script_schedule:
            from app.models.execution import Execution
            return Execution.query.filter_by(schedule_id=self.id)\
                                 .order_by(Execution.started_at.desc())\
                                 .limit(limit).all()
        elif self.is_integration_schedule:
            from app.models.integration_execution import IntegrationExecution
            return IntegrationExecution.query.filter_by(schedule_id=self.id)\
                                            .order_by(IntegrationExecution.started_at.desc())\
                                            .limit(limit).all()
        return []
    
    @property
    def last_execution_result(self):
        """Get last execution result (NEW - supports both types)"""
        history = self.get_execution_history(limit=1)
        if not history:
            return None
        
        last_exec = history[0]
        return {
            'id': last_exec.id,
            'status': last_exec.status,
            'started_at': last_exec.started_at,
            'completed_at': last_exec.completed_at,
            'duration': last_exec.formatted_duration,
            'success': last_exec.is_completed if hasattr(last_exec, 'is_completed') else (last_exec.status == 'completed')
        }
    
    @property
    def execution_statistics(self):
        """Get execution statistics (NEW - supports both types)"""
        history = self.get_execution_history(limit=50)  # Last 50 executions
        
        if not history:
            return {
                'total': 0,
                'successful': 0,
                'failed': 0,
                'success_rate': 0,
                'avg_duration': 0
            }
        
        total = len(history)
        successful = 0
        failed = 0
        total_duration = 0
        
        for exec_item in history:
            if hasattr(exec_item, 'is_completed'):
                if exec_item.is_completed:
                    successful += 1
                elif exec_item.is_failed:
                    failed += 1
            else:
                # Fallback for script executions
                if exec_item.status == 'completed':
                    successful += 1
                else:
                    failed += 1
            
            if exec_item.duration_seconds:
                total_duration += exec_item.duration_seconds
        
        success_rate = round((successful / total) * 100, 1) if total > 0 else 0
        avg_duration = round(total_duration / total, 2) if total > 0 else 0
        
        return {
            'total': total,
            'successful': successful,
            'failed': failed,
            'success_rate': success_rate,
            'avg_duration': avg_duration
        }
    
    def validate_for_integration(self):
        """Validate schedule configuration for integration use (NEW)"""
        errors = []
        
        if not self.is_integration_schedule:
            errors.append("This schedule is not configured for integrations")
            return errors
        
        item = self.scheduled_item
        if not item:
            errors.append("Integration not found")
            return errors
        
        if not item.is_active:
            errors.append("Integration is not active")
        
        # Validate data sources
        if not hasattr(item, 'source_datasource') or not item.source_datasource:
            errors.append("Integration source database not configured")
        
        if not hasattr(item, 'target_datasource') or not item.target_datasource:
            errors.append("Integration target database not configured")
        
        return errors
    
    # === END NEW INTEGRATION METHODS ===
    
    def __repr__(self):
        return f'<Schedule {self.name} - {self.frequency.value} ({self.schedule_type})>'