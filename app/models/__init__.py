# ScriptFlow Data Models
# This will be set by the main app
db = None

# Models are imported lazily to avoid circular imports
# Import them directly when needed, after db is initialized