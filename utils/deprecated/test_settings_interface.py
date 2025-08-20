#!/usr/bin/env python3
"""
Script para testar a interface de configurações via browser
"""

import subprocess
import time

def test_settings_interface():
    """Test settings interface via browser"""
    
    print("🧪 Testing Settings Interface...")
    print("📍 Application running at: http://192.168.1.60:8000")
    print()
    
    # Test URLs to check
    urls = [
        "http://192.168.1.60:8000/settings",
        "http://192.168.1.60:8000/settings/python", 
        "http://192.168.1.60:8000/settings/terminal"
    ]
    
    print("🔗 URLs to test (after login):")
    for url in urls:
        print(f"   - {url}")
    
    print()
    print("📝 Login credentials:")
    print("   Username: admin")
    print("   Password: admin123")
    
    print()
    print("✅ Features to test:")
    print("   1. Navigate to Settings from navbar")
    print("   2. Configure Python interpreter")
    print("   3. Test configuration")
    print("   4. Use web terminal to install packages")
    print("   5. Run 'pip install speedtest-cli' in terminal")
    print("   6. Execute speed test script")
    
    print()
    print("🚀 Open browser and test the interface!")

if __name__ == "__main__":
    test_settings_interface()