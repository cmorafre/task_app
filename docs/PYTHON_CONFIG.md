# Python Interpreter Configuration

## Current Configuration

**Default**: Uses `python3` from system PATH (currently Anaconda Python 3.12.7)

## Available Configuration Options

### Environment Variables

```bash
# Set custom Python executable
export PYTHON_EXECUTABLE="/usr/bin/python3.11"

# Use specific virtual environment  
export PYTHON_ENV="/path/to/venv"

# Example: Start application with custom Python
PYTHON_EXECUTABLE="/usr/bin/python3" python3 scriptflow.py
```

### Virtual Environment Support

```bash
# Create virtual environment for scripts
python3 -m venv /path/to/scriptflow-env
source /path/to/scriptflow-env/bin/activate
pip install speedtest-cli pandas openpyxl

# Configure ScriptFlow to use this environment
export PYTHON_ENV="/path/to/scriptflow-env"
python3 scriptflow.py
```

## Testing Configuration

```bash
# Test current configuration
python3 test_config.py

# Check system info via API (requires login)
curl http://192.168.1.60:8000/system/info
```

## Available Python Interpreters

- **System Python**: `/usr/bin/python3`
- **Anaconda Python**: `/opt/anaconda3/bin/python3` (default)
- **Custom paths**: Configure via `PYTHON_EXECUTABLE`

## Dependencies for Scripts

Common packages needed for uploaded scripts:

```bash
pip install speedtest-cli pandas openpyxl requests numpy matplotlib
```

## Production Recommendations

1. **Use virtual environment**: Isolate script dependencies
2. **Set explicit paths**: Don't rely on PATH resolution
3. **Test configuration**: Verify before deploying
4. **Monitor dependencies**: Check if required packages are installed

## Examples

### Using System Python
```bash
export PYTHON_EXECUTABLE="/usr/bin/python3"
python3 scriptflow.py
```

### Using Virtual Environment
```bash
python3 -m venv ./script-env
source ./script-env/bin/activate
pip install speedtest-cli pandas
export PYTHON_ENV="$(pwd)/script-env"
python3 scriptflow.py
```

### Using Conda Environment
```bash
conda create -n scriptflow python=3.11
conda activate scriptflow
conda install pandas openpyxl
pip install speedtest-cli
export PYTHON_ENV="$CONDA_PREFIX"
python3 scriptflow.py
```