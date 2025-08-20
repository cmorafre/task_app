#!/usr/bin/env python3
"""
Script para testar a detecção de interpretadores Python
"""

import subprocess

def detect_python_interpreters():
    """Detect available Python interpreters on the system"""
    interpreters = []
    common_paths = [
        'python3', 'python', 'python3.9', 'python3.10', 'python3.11', 'python3.12',
        '/usr/bin/python3', '/usr/bin/python', '/usr/local/bin/python3',
        '/opt/homebrew/bin/python3', '/System/Library/Frameworks/Python.framework/Versions/Current/bin/python3'
    ]
    
    print("🔍 Detecting Python interpreters...")
    
    for path in common_paths:
        try:
            result = subprocess.run([path, '--version'], 
                                  capture_output=True, text=True, timeout=3)
            if result.returncode == 0:
                version = result.stdout.strip() or result.stderr.strip()
                interpreters.append({
                    'path': path,
                    'version': version,
                    'display': f"{path} ({version})"
                })
                print(f"✅ Found: {path} ({version})")
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            print(f"❌ Not found: {path}")
            continue
    
    # Remove duplicates based on version
    seen_versions = set()
    unique_interpreters = []
    for interp in interpreters:
        if interp['version'] not in seen_versions:
            seen_versions.add(interp['version'])
            unique_interpreters.append(interp)
    
    print(f"\n📊 Summary: Found {len(unique_interpreters)} unique Python interpreters")
    for interp in unique_interpreters:
        print(f"   - {interp['display']}")
    
    return unique_interpreters

if __name__ == "__main__":
    detect_python_interpreters()