# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Application Commands

### Development
- **Start app (recommended)**: `python3 scriptflow.py` - Main application file
- **Quick start**: `python3 app_simple.py` - Simplified version for testing
- **Auto setup**: `./deploy/run.sh` - Complete setup with dependencies and database

### Dependencies
- **Install**: `pip install -r requirements.txt`
- **Core dependencies**: Flask, Flask-SQLAlchemy, Flask-Login, APScheduler

### Database
- **Initialize**: Database auto-creates on first run
- **Default admin**: username=`admin`, password=`admin123`
- **Location**: SQLite database at `instance/scriptflow.db`

### Testing
- **Test files**: Various `test_*.py` files in root directory
- **Run tests**: No specific test runner configured - use `python test_filename.py`

## Architecture Overview

### Technology Stack
- **Backend**: Flask web framework with SQLAlchemy ORM
- **Database**: SQLite (development), PostgreSQL migration path planned
- **Frontend**: Jinja2 templates with Bootstrap 5.3 CSS framework
- **Scheduler**: APScheduler for background job execution
- **Authentication**: Flask-Login with session-based auth

### Application Structure
This is a monolithic Flask application with modular organization:

```
app/
├── models/          # Database models (User, Script, Execution, Schedule)
├── routes/          # Blueprint controllers (auth, dashboard, scripts, logs, schedules)  
├── services/        # Business logic (script_executor for safe script execution)
├── templates/       # Jinja2 HTML templates with Bootstrap styling
└── static/          # CSS/JS assets
```

### Key Components

**Script Execution Engine** (`app/services/script_executor.py`):
- Executes Python (.py) and Batch (.bat) scripts in isolated subprocesses
- Configurable timeouts (default 5 minutes)
- Concurrent execution limits (default 10)
- Captures stdout/stderr with timestamps

**Scheduling System**:
- APScheduler integration for automated script execution
- Supports hourly, daily, weekly, monthly frequencies
- Persistent job storage in SQLite
- Background execution without blocking web interface

**Security Features**:
- File upload validation (only .py/.bat, 10MB limit)
- Subprocess isolation for script execution
- Working directory separation
- Session-based authentication

### Database Models
- **User**: Authentication and user management
- **Script**: Uploaded script files with metadata
- **Execution**: Script execution history and logs
- **Schedule**: Automated execution scheduling

### Configuration
Environment variables (see `.env.example`):
- `SECRET_KEY`: Flask secret key
- `DATABASE_URL`: Database connection string
- `UPLOAD_FOLDER`: Script storage directory
- `PYTHON_EXECUTABLE`: Python interpreter path
- `MAX_CONCURRENT_SCRIPTS`: Execution limit (default 10)
- `SCRIPT_TIMEOUT`: Execution timeout in seconds (default 300)

## Design Standards

All UI components follow consistent design patterns defined in `DESIGN_STANDARDS.md`:
- **Buttons**: 6px border-radius, 600 font-weight, 0.3s transitions
- **Cards**: 8px border-radius with subtle shadows
- **Status indicators**: Color-coded (green=success, red=failure, orange=running)
- **Forms**: 6px border-radius with Bootstrap styling

## Development Notes

### Code Organization
- **Blueprint pattern**: Routes organized by feature area
- **Service layer**: Business logic separated from controllers
- **Repository pattern**: Database access through SQLAlchemy models
- **Template inheritance**: Base layout with feature-specific templates

### Script Execution Flow
1. File upload → validation → secure storage
2. Script metadata saved to database
3. Execution request → ScriptExecutor service
4. Subprocess creation with isolation
5. Output capture and logging
6. Status updates in real-time

### Common Tasks
- **Add new route**: Create in appropriate blueprint in `app/routes/`
- **Database changes**: Modify models in `app/models/`
- **Script execution logic**: Update `app/services/script_executor.py`
- **UI changes**: Edit templates in `app/templates/` following design standards
- **Static assets**: Place in `app/static/css/` or `app/static/js/`

### Testing Approach
- Test files exist for various components
- No formal test framework configured
- Manual testing workflow documented in PRD
- Integration tests cover critical script execution flows

## Integration Feature (NEW)

### ETL Functionality
- **Extract-Transform-Load**: Full ETL pipeline support
- **Data Sources**: Oracle and PostgreSQL connections
- **Python Transformation**: Optional data processing scripts
- **Scheduling**: Automated ETL job execution

### New Components
- **DataSource Model**: Encrypted database connections
- **Integration Model**: ETL job definitions
- **IntegrationExecution Model**: ETL execution history
- **ConnectionManager Service**: Database connection pooling
- **ETLExecutor Service**: ETL orchestration engine

### Integration Pages
- `/integrations` - Main Integration dashboard
- `/integrations/new` - Create new ETL job
- `/integrations/{id}` - View Integration details
- `/integrations/sources` - Manage database connections
- `/integrations/executions` - ETL execution logs

### Database Support
- **Oracle**: cx_Oracle connector with connection pooling
- **PostgreSQL**: psycopg2 connector with connection pooling
- **Encryption**: Credentials encrypted using Fernet (cryptography)
- **Security**: SQL validation, injection prevention, subprocess isolation