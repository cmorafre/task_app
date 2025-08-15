#!/usr/bin/env python3
"""
Teste simples de script Python
"""

import time
import sys

print("Iniciando script de teste...")
print(f"Python version: {sys.version}")
print("Executando operações...")

for i in range(3):
    print(f"Step {i+1}/3")
    time.sleep(1)

print("Script executado com sucesso!")
print("Final result: OK")