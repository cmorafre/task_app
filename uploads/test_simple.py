#!/usr/bin/env python3
"""
Script de teste simples para verificar execução
"""
import time
import sys
import os

print("=== TESTE DE EXECUÇÃO ===")
print(f"Python version: {sys.version}")
print(f"Current working directory: {os.getcwd()}")
print(f"Script path: {__file__}")

print("\nExecutando teste...")
for i in range(3):
    print(f"Step {i+1}/3 - OK")
    time.sleep(0.5)

print("\n✅ Teste executado com sucesso!")
print("Resultado: APROVADO")