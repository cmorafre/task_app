#!/usr/bin/env python3
"""
Script para testar configurações de Python em diferentes ambientes
"""

import os
import subprocess
import sys
from scriptflow import app

def test_python_config():
    """Test the current Python configuration"""
    with app.app_context():
        print("=== PYTHON INTERPRETER CONFIGURATION TEST ===")
        print(f"App Python executable config: {app.config['PYTHON_EXECUTABLE']}")
        print(f"App Python environment config: {app.config['PYTHON_ENV']}")
        print(f"Current app Python: {sys.executable}")
        print(f"Current app version: {sys.version}")
        
        # Test actual resolved path
        python_exec = app.config['PYTHON_EXECUTABLE'] 
        python_env = app.config['PYTHON_ENV']
        
        if python_env:
            actual_python = os.path.join(python_env, 'bin', 'python')
            if not os.path.exists(actual_python):
                actual_python = os.path.join(python_env, 'Scripts', 'python.exe')
        else:
            import shutil
            actual_python = shutil.which(python_exec) or python_exec
            
        print(f"Resolved Python path: {actual_python}")
        
        # Test the Python that would be used for scripts
        try:
            result = subprocess.run([actual_python, '--version'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print(f"Script Python version: {result.stdout.strip()}")
            else:
                print(f"Error testing Python: {result.stderr.strip()}")
                
            # Test if speedtest is available in this Python
            result = subprocess.run([actual_python, '-c', 'import speedtest; print("speedtest-cli: OK")'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print(f"Dependencies check: {result.stdout.strip()}")
            else:
                print(f"Dependencies missing: speedtest-cli not installed")
                
        except Exception as e:
            print(f"Error testing Python: {str(e)}")

if __name__ == "__main__":
    test_python_config()